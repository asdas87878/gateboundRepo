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
				blob = np.clip(1.15 - np.hypot(dx, dy), 0, 1) ** 0.7 * op
				blob *= np.clip((el[j0:j1][:, None] - base) / (pr * 0.25) + 1, 0, 1)  # flat underside
				sub = cover[j0:j1][:, ii]
				cover[j0:j1, ii] = np.maximum(sub, blob)
				facing = np.clip(0.55 + 0.45 * (-dy * 0.8 + dx * math.cos(p_az - sun_az) * 0.4), 0, 1)
				ls = lit[j0:j1][:, ii]
				lit[j0:j1, ii] = np.where(blob > sub, facing, ls)
		cover *= smoothstep(cu.get("FadeLow", 1), cu.get("FadeHigh", 5), eld)
		cl_lit, cl_shade = to_lin(hex_rgb(cu["Colour"])), to_lin(hex_rgb(cu["Shade"]))
		ccol = cl_shade * (1 - lit[..., None]) + cl_lit * lit[..., None]
		col = col * (1 - cover[..., None]) + ccol * cover[..., None]
		del cover, lit, ccol

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
