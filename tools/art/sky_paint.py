"""Paint a sky as an equirectangular image (docs/look-passes.md): a vertical gradient, a warm side toward the sun, soft
wispy clouds and a sun disc with layered glow. Blender's convention: u = 0.5 - atan2(y, x) / 2pi (centre = +X, +Y at a
quarter), v = 0.5 + asin(z) / pi (top row = straight up). The same painting can later be cut into Roblox's six skybox faces.

paint(sky) returns linear-light float32 rows top to bottom; tools/blender/look_match.py loads it straight into a float
image. Run alone it writes an 8-bit preview:
  python tools/art/sky_paint.py <spec.json> <out.png>
"""

import json
import math
import sys

import numpy as np

from noise2d import fbm


def hex_rgb(h):
	return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def to_lin(c):
	return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(c):
	c = np.clip(c, 0, None)
	return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def smoothstep(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def _blur(a, r):
	"""soft blur (two box passes per axis via running sums), edges clamped; r in pixels"""
	if r < 1:
		return a
	for ax in (0, 1):
		for _ in range(2):
			pad = [(0, 0)] * a.ndim
			pad[ax] = (r + 1, r)
			c = np.cumsum(np.pad(a, pad, mode="edge"), axis=ax, dtype=np.float64)
			hi = np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax)
			lo = np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)
			a = ((hi - lo) / (2 * r + 1)).astype(np.float32)
	return a


def _up2(a, shape):
	"""double an array's resolution (rows and columns) with a smooth tent filter, cropped to shape"""
	a = np.repeat(np.repeat(a, 2, 0), 2, 1)
	b = a.copy()
	b[1:-1] = (a[:-2] + 2 * a[1:-1] + a[2:]) / 4
	c = b.copy()
	c[:, 1:-1] = (b[:, :-2] + 2 * b[:, 1:-1] + b[:, 2:]) / 4
	return c[: shape[0], : shape[1]]


def cloud_layer(cl, az, el, sd):
	"""a field of clouds over the land, seen in perspective: big overhead, small and packed toward the horizon.

	Flat layers (no "Thickness": cirrus) are one slice. With "Thickness" the cloud is a slab marched in "Slices" from its
	base up: each slice needs a little more density (domed tops), light grows with height in the cloud (flat dark bases,
	bright tops), and a sample toward the sun lights the sun side. Front-to-back blending. Worked out at half resolution
	(clouds are soft) and doubled. Returns (cover, colour) for the whole image."""
	H_, W_ = len(el), len(az)
	top_el = cl["Top"][1] if "Top" in cl else 89.0
	rows = np.where((el > math.radians(cl.get("MinElevation", 0.4))) & (el < math.radians(top_el)))[0]
	if len(rows) == 0:
		return np.zeros((H_, W_), np.float32), np.zeros((H_, W_, 3), np.float32)
	r0, r1 = rows[0], rows[-1] + 1
	e = el[r0:r1:2][:, None]
	a_ = az[::2][None, :]
	wa = math.radians(cl.get("Wind", 30.0))
	st = cl.get("Stretch", 2.0)
	sc = cl["Scale"]
	seed, octs, gain = cl.get("Seed", 4), cl.get("Octaves", 5), cl.get("Gain", 0.5)
	thr, soft, clump = cl.get("Threshold", 0.1), cl.get("Soft", 0.12), cl.get("Clump", 0.6)
	s_az = math.atan2(sd[1], sd[0])
	off = cl.get("LightOffset", 0.35)
	sx_ = (math.cos(s_az) * math.cos(wa) + math.sin(s_az) * math.sin(wa)) * off / st
	sy_ = (-math.cos(s_az) * math.sin(wa) + math.sin(s_az) * math.cos(wa)) * off
	h0, T = cl.get("Height", 1.0), cl.get("Thickness", 0.0)
	K = cl.get("Slices", 6) if T > 0 else 1
	alpha = cl.get("SliceAlpha", 0.5) if T > 0 else 1.0
	col_lit, col_shade = to_lin(hex_rgb(cl["Colour"])), to_lin(hex_rgb(cl["Shade"]))
	acc_c = np.zeros(e.shape[:1] + a_.shape[1:] + (3,), np.float32)
	acc_a = np.zeros(e.shape[:1] + a_.shape[1:], np.float32)
	tan_e = np.tan(e)
	jit = np.random.RandomState(seed + 99).rand(*acc_a.shape).astype(np.float32)  # per-pixel slice offset: no stripes
	# seen from below, a cloud shows its flat base; only toward the horizon do we see its sides. Thinning the slab with
	# elevation keeps the columns of the 2D field from smearing into vertical streaks at mid elevations.
	fl = cl.get("Flatten")
	Te = T * np.clip(1 - (np.degrees(e) - fl[0]) / (fl[1] - fl[0]), fl[2], 1) if fl and T > 0 else T
	for k in range(K):
		t = (k + jit) / K if K > 1 else 0.5
		d = np.minimum((h0 + t * Te) / tan_e, cl.get("MaxDistance", 60.0))  # where the view ray crosses this slice
		u, v = d * np.cos(a_), d * np.sin(a_)
		x = (u * math.cos(wa) + v * math.sin(wa)) / (sc * st)
		y = (-u * math.sin(wa) + v * math.cos(wa)) / sc
		far = d / sc

		def fade(o, far=far):  # drop fine octaves far away, where they would only alias
			return np.clip(1.6 - far * (2**o) * cl.get("Detail", 0.012), 0, 1)

		taper = cl.get("Dome", 0.25) * t * t  # higher slices need denser cloud: rounded tops
		dens = fbm(x, y, seed, octs, gain, fade) + fbm(x * 0.23, y * 0.23, seed + 50, 2) * clump - thr - taper
		a = smoothstep(0.0, soft, dens) * alpha
		dens_s = fbm(x + sx_, y + sy_, seed, octs, gain, fade) + fbm((x + sx_) * 0.23, (y + sy_) * 0.23, seed + 50, 2) * clump - thr - taper
		side = np.clip(0.5 + (dens - dens_s) * cl.get("LightGain", 3.0), 0, 1)
		thin = 1 - smoothstep(0.0, cl.get("Core", 0.35), dens)  # thin edges catch light
		if T > 0:
			lit = cl.get("Base", 0.15) + cl.get("Rise", 0.6) * t + 0.5 * (side - 0.5) + 0.25 * thin
		else:
			lit = side * 0.75 + thin * 0.35
		lit = np.clip(lit, 0, 1)
		steps = cl.get("Steps", 0)
		if steps:  # soft toon bands
			q = lit * steps
			lit = (np.floor(q) + smoothstep(0.35, 0.65, q - np.floor(q))) / steps
		c = col_shade * (1 - lit[..., None]) + col_lit * lit[..., None]
		w = ((1 - acc_a) * a)[..., None]
		acc_c += w * c
		acc_a += (1 - acc_a) * a
	ccol = acc_c / np.maximum(acc_a, 1e-4)[..., None]
	br = cl.get("Blur", 0)  # smooths the slice jitter into soft painted edges
	if br:
		acc_a = _blur(acc_a, br)
		ccol = _blur(ccol, br)
	eld = np.degrees(e)
	cover = acc_a * cl.get("Opacity", 1.0) * smoothstep(cl.get("FadeLow", 1.0), cl.get("FadeHigh", 6.0), eld)
	if "Top" in cl:  # thin out toward the zenith
		cover = cover * smoothstep(cl["Top"][1], cl["Top"][0], eld)
	full_c = np.zeros((H_, W_), np.float32)
	full_col = np.zeros((H_, W_, 3), np.float32)
	n_r = r1 - r0
	full_c[r0:r1] = _up2(cover, (n_r, W_))
	full_col[r0:r1] = np.stack([_up2(ccol[..., i], (n_r, W_)) for i in range(3)], -1)
	return full_c, full_col


def paint(sky, size=None):
	W, H = size or tuple(sky.get("Size", (4096, 2048)))
	az = ((0.5 - (np.arange(W, dtype=np.float32) + 0.5) / W) * 2 * math.pi).astype(np.float32)  # atan2(y, x)
	el = (((1 - (np.arange(H, dtype=np.float32) + 0.5) / H) - 0.5) * math.pi).astype(np.float32)
	eld = np.degrees(el)[:, None]  # (H, 1)

	# gradient by elevation: stops of [elevation degrees, colour], blended in linear light
	stops = sky["Gradient"]
	col = np.empty((H, 1, 3), np.float32)
	col[:] = to_lin(hex_rgb(stops[0][1]))
	for k in range(len(stops) - 1):
		t = smoothstep(stops[k][0], stops[k + 1][0], eld)[..., None]
		col = col * (1 - t) + to_lin(hex_rgb(stops[k + 1][1])) * t
	col = np.repeat(col, W, axis=1)

	# angle to the painted sun, per pixel
	sd = np.array(sky["SunDir"], np.float32)
	sd /= np.linalg.norm(sd)
	cos_el = np.cos(el)[:, None]
	cosang = cos_el * np.cos(az)[None, :] * sd[0] + cos_el * np.sin(az)[None, :] * sd[1] + np.sin(el)[:, None] * sd[2]
	ang = np.degrees(np.arccos(np.clip(cosang, -1, 1))).astype(np.float32)
	del cosang

	side = sky.get("SunSide")
	if side:
		w = (np.clip(1 - ang / side["Radius"], 0, 1) ** side.get("Power", 1.5) * side["Strength"])[..., None]
		col = col * (1 - w) + to_lin(hex_rgb(side["Colour"])) * w

	# clouds: soft horizontal wisps (stretched gaussians in azimuth/elevation), slightly bluish bellies
	cl = sky.get("Clouds")
	if cl:
		rng = np.random.RandomState(cl.get("Seed", 1))
		ccol, belly = to_lin(hex_rgb(cl["Colour"])), to_lin(hex_rgb(cl.get("Belly", cl["Colour"])))
		cover = np.zeros((H, W), np.float32)
		shade = np.zeros((H, W), np.float32)
		az_range = cl.get("Azimuth")  # optional [min, max] degrees (atan2(y, x)) to keep clouds where the camera looks
		for _ in range(cl["Count"]):
			c_az = math.radians(rng.uniform(*az_range)) if az_range else rng.uniform(-math.pi, math.pi)
			c_el = math.radians(rng.uniform(*cl["Elevation"]))
			wdt = math.radians(rng.uniform(*cl["Width"]))
			hgt = math.radians(rng.uniform(*cl["Height"]))
			op = rng.uniform(*cl["Opacity"])
			for _ in range(rng.randint(3, 8)):
				p_az = c_az + rng.uniform(-0.5, 0.5) * wdt
				p_el = c_el + rng.uniform(-0.35, 0.35) * hgt
				pw = wdt * rng.uniform(0.2, 0.55)
				ph = hgt * rng.uniform(0.25, 0.65)
				j0 = max(0, int((0.5 - (p_el + 3 * ph) / math.pi) * H))
				j1 = min(H, int((0.5 - (p_el - 3 * ph) / math.pi) * H) + 1)
				span = 3 * pw / max(0.2, math.cos(p_el))
				i0 = int((0.5 - (p_az + span) / (2 * math.pi)) * W)
				i1 = int((0.5 - (p_az - span) / (2 * math.pi)) * W) + 1
				if j1 <= j0 or i1 <= i0:
					continue
				ii = np.arange(i0, i1) % W
				daz = (az[ii][None, :] - p_az + math.pi) % (2 * math.pi) - math.pi
				dl = el[j0:j1][:, None] - p_el
				blob = np.exp(-0.5 * ((daz * math.cos(p_el) / pw) ** 2 + (dl / ph) ** 2)) * op
				sub = cover[j0:j1][:, ii]
				cover[j0:j1, ii] = 1 - (1 - sub) * (1 - blob)
				sh = shade[j0:j1][:, ii]
				shade[j0:j1, ii] = np.maximum(sh, blob * np.clip(-dl / ph, 0, 1))
		cover *= smoothstep(cl.get("FadeLow", 2), cl.get("FadeHigh", 8), eld)
		mixw = (shade * cl.get("BellyAmount", 0.6))[..., None]
		cc = ccol * (1 - mixw) + belly * mixw
		col = col * (1 - cover[..., None]) + cc * cover[..., None]
		del cover, shade, cc, mixw

	cu = sky.get("Cumulus")
	if cu:  # piled-up cumulus: clusters of round puffs over a flat base, lit tops, blue-grey bellies
		rng = np.random.RandomState(cu.get("Seed", 2))
		cover = np.zeros((H, W), np.float32)
		lit = np.zeros((H, W), np.float32)
		sun_az = math.atan2(sd[1], sd[0])
		for _ in range(cu["Count"]):
			az_range = cu.get("Azimuth")
			c_az = math.radians(rng.uniform(*az_range)) if az_range else rng.uniform(-math.pi, math.pi)
			base = math.radians(rng.uniform(*cu["Elevation"]))
			size = math.radians(rng.uniform(*cu["Size"]))
			op = rng.uniform(*cu.get("Opacity", (0.85, 1.0)))
			for _ in range(rng.randint(*cu.get("Puffs", (6, 14)))):
				p_az = c_az + rng.uniform(-1.0, 1.0) * size * 1.4
				pr = size * rng.uniform(0.25, 0.6)
				p_el = base + pr * rng.uniform(0.2, 1.4)  # puffs sit on the base and pile up
				j0 = max(0, int((0.5 - (p_el + 2.2 * pr) / math.pi) * H))
				j1 = min(H, int((0.5 - (base - 0.4 * pr) / math.pi) * H) + 1)
				span = 2.2 * pr / max(0.2, math.cos(p_el))
				i0 = int((0.5 - (p_az + span) / (2 * math.pi)) * W)
				i1 = int((0.5 - (p_az - span) / (2 * math.pi)) * W) + 1
				if j1 <= j0 or i1 <= i0:
					continue
				ii = np.arange(i0, i1) % W
				daz = (az[ii][None, :] - p_az + math.pi) % (2 * math.pi) - math.pi
				dl = el[j0:j1][:, None] - p_el
				dx, dy = daz * math.cos(p_el) / pr, dl / pr
				rr_ = np.hypot(dx, dy)
				blob = np.clip((1.05 - rr_) / 0.55, 0, 1) ** 1.6 * op  # soft edge, no bubble outline
				blob *= np.clip((el[j0:j1][:, None] - base) / (pr * 0.25) + 1, 0, 1)  # flat underside
				sub = cover[j0:j1][:, ii]
				cover[j0:j1, ii] = np.maximum(sub, blob)
				facing = np.clip(0.55 + 0.45 * (-dy * 0.8 + dx * math.cos(p_az - sun_az) * 0.4), 0, 1)
				ls = lit[j0:j1][:, ii]
				lit[j0:j1, ii] = np.maximum(ls, facing * np.clip(blob * 1.5, 0, 1))
		cover *= smoothstep(cu.get("FadeLow", 1), cu.get("FadeHigh", 5), eld)
		cl_lit, cl_shade = to_lin(hex_rgb(cu["Colour"])), to_lin(hex_rgb(cu["Shade"]))
		ccol = cl_shade * (1 - lit[..., None]) + cl_lit * lit[..., None]
		col = col * (1 - cover[..., None]) + ccol * cover[..., None]
		del cover, lit, ccol

	for layer in sky.get("Layers", []):  # noise cloud fields in perspective (cirrus first, then the cumulus banks)
		cov, ccol = cloud_layer(layer, az, el, sd)
		# toward the sun a cloud is backlit: a bright rim on thin parts, the haze glow shows through
		glow = np.clip(1 - ang / layer.get("BacklitRadius", 35.0), 0, 1)[..., None] ** 1.5 * layer.get("Backlit", 0.0)
		ccol = ccol * (1 - glow) + to_lin(hex_rgb(layer.get("BacklitColour", "fff4dc"))) * glow * (1 - cov[..., None] * 0.5)
		col = col * (1 - cov[..., None]) + ccol * cov[..., None]
		del cov, ccol

	sun = sky.get("Sun")
	if sun:
		disc = smoothstep(sun["Disc"] * 1.3, sun["Disc"] * 0.75, ang)[..., None]
		col = col * (1 - disc) + to_lin(hex_rgb(sun["DiscColour"])) * sun.get("DiscStrength", 1.5) * disc
		for gl in sun.get("Glow", []):
			w = (np.exp(-((ang / gl["Radius"]) ** gl.get("Power", 2))) * gl["Strength"])[..., None]
			col = col + to_lin(hex_rgb(gl["Colour"])) * w
	below = to_lin(hex_rgb(sky.get("Below", "b8c0b8")))
	t = smoothstep(0, -3, eld)[..., None]
	col = col * (1 - t) + below * t
	return col.astype(np.float32)


def main():
	from PIL import Image

	spec = json.load(open(sys.argv[1], encoding="utf-8"))
	col = paint(spec["Sky"], (2048, 1024))
	s = to_srgb(col)
	s = s + (np.random.RandomState(0).rand(*s.shape) - 0.5) / 255  # dither: no banding in the 8-bit preview
	Image.fromarray((np.clip(s, 0, 1) * 255 + 0.5).astype(np.uint8)).save(sys.argv[2])


if __name__ == "__main__":
	main()
