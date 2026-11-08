"""Paint the rock kit's shared colour texture (tools/blender/rock_kit.py): the painted look worked out per texel on the 3D
surface, so edges and cracks run continuously across UV seams. Light is baked in as painted bands, top light to teal shadow.

  python tools/art/paint_rock_kit.py      art/kit/rocks/bake.npz -> art/kit/rocks/RockKit_<sheet>_Color.png and _Moss.png, 1024 each

Layers: value bands from facing, height and big soft mottling, each plane nudged lighter or darker; colour layers (cool darks, cool and
warm sides, stroke patches; COLOUR scales them); a teal foot where the rock meets the ground; dark crevices between lumps; a few thin
cracks with a lit side; a light painted edge along every bevel, wobbling and breaking. RockKit_Moss.png adds moss on upward faces.
Numbers are at the top. No Painter needed; in Roblox this is the SurfaceAppearance ColorMap.
"""

import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", sys.argv[sys.argv.index("--kit") + 1] if "--kit" in sys.argv else "rocks")  # --kit rocks_natural paints the other kit
FINAL = 1024  # Roblox cuts textures to this
SIZE = FINAL * 2

RAMP = [(0.0, "5d6c6c"), (0.34, "8b918b"), (0.67, "b6b5a8"), (1.0, "dcd9ca")]  # shadow to lit: cool grey to warm pale stone
BANDS = 5  # soft value steps: painted planes of tone, not a smooth gradient
EDGE = "f5f2e6"
EDGE_WIDTH = 0.2  # studs, past the bevel
FOOT = "566a68"
CREVICE = "4f605f"
CRACK = "5e6b68"
CRACK_LIT = "ebe8da"
# colour layers over the value bands, after the frog video's recipe: darks and sides shift in hue instead of only going grey
COLOUR = 1.0  # all colour layers together: 0 gives the plain grey version
SHADE_COOL = "66798e"  # blue slate, in the bands' darks
SIDE_COOL = "8195a8"  # planes facing away from the light
SIDE_WARM = "d2c6a4"  # planes facing it
SPOT_TEAL = "6f8c8a"  # stroke patches
SPOT_OCHRE = "b5a982"
SPOT_SLATE = "7c8798"
CREVICE_DEEP = "38505f"
MOSS = "349f4c"  # matched to the terrain grass as lit in Studio
MOSS_LIT = "4fb65f"
MOSS_DARK = "2b7a4a"  # the edge, darker where it meets the stone
FINE = 0.16  # small strokes, the detail that the sharper sheets can now hold
SUPER = 2  # paint at this many times the final 1024, then shrink


def hexc(h):
	return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def smooth(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


GRIDS = {}


def noise3(p, scale, seed, octaves=3):
	"""fractal value noise in 3D, about -1..1"""
	if seed not in GRIDS:
		GRIDS[seed] = np.random.RandomState(seed).uniform(-1, 1, (48, 48, 48)).astype(np.float32)
	out, amp, norm = 0.0, 1.0, 0.0
	for o in range(octaves):
		q = (p / scale * 2**o + o * 7.3).T
		out = out + ndimage.map_coordinates(GRIDS[seed], q, order=1, mode="grid-wrap") * amp
		norm += amp
		amp *= 0.5
	return out / norm * 1.6


def strokes(p, scale, seed, balance, contrast=7.0):
	"""the spot + Blur Slope chain, done on the 3D surface so it crosses UV seams: patches smeared by a second noise and stretched down the rock"""
	q = p * np.array([1.0, 1.0, 0.42], np.float32)
	warp = np.stack([noise3(q, scale * 1.2, seed + i, 2) for i in (20, 21, 22)], -1) * scale * 0.55
	v = noise3(q + warp, scale, seed, 3)
	return np.clip((v - balance) * contrast + 0.5, 0, 1)


def rasterise(d):
	"""for every texel inside a triangle: its triangle, and its point on the surface"""
	tri = np.full((SIZE, SIZE), -1, np.int32)
	pos = np.zeros((SIZE, SIZE, 3), np.float32)
	uv = d["uv"] * [SIZE, SIZE]
	uv[..., 1] = SIZE - uv[..., 1]
	for k in range(len(uv)):
		a, b, c = uv[k]
		x0, y0 = np.floor(np.minimum.reduce([a, b, c]) - 1).astype(int)
		x1, y1 = np.ceil(np.maximum.reduce([a, b, c]) + 1).astype(int)
		x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, SIZE), min(y1, SIZE)
		if x1 <= x0 or y1 <= y0:
			continue
		X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
		den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
		if abs(den) < 1e-9:
			continue
		w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
		w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
		w2 = 1 - w0 - w1
		m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)  # a hair over, so seams have no gaps
		t = tri[y0:y1, x0:x1]
		t[m] = k
		P = d["pos"][k]
		for ax in range(3):
			pos[y0:y1, x0:x1, ax][m] = (w0 * P[0, ax] + w1 * P[1, ax] + w2 * P[2, ax])[m]
	return tri, pos


def surface_points(tris, per_point, with_index=False):
	"""random points over triangles, about one per per_point square studs (optionally each point's triangle index)"""
	r = np.random.RandomState(1)
	out, idx = [], []
	for k, (a, b, c) in enumerate(tris):
		area = np.linalg.norm(np.cross(b - a, c - a)) / 2
		u = r.rand(max(2, int(area / per_point)), 2)
		f = u.sum(1) > 1
		u[f] = 1 - u[f]
		out.append(a + (b - a) * u[:, :1] + (c - a) * u[:, 1:])
		idx.append(np.full(len(u), k))
	return (np.concatenate(out), np.concatenate(idx)) if with_index else np.concatenate(out)


def main():
	all_data = dict(np.load(os.path.join(OUT, "bake.npz")))
	names, atlas_of = all_data["names"], all_data["atlas"]
	for atlas in sorted(set(atlas_of.tolist())):
		ids = np.where(atlas_of == atlas)[0]
		keep = np.isin(all_data["piece"], ids)
		d = dict(all_data)
		for key in ("pos", "uv", "nor", "piece", "bevel", "face", "sub"):
			d[key] = all_data[key][keep]
		paint_sheet(d, atlas)


def paint_sheet(d, atlas):
	tri, pos = rasterise(d)
	mask = tri >= 0
	k = tri[mask]
	p = pos[mask]
	n = d["nor"][k]
	piece = d["piece"][k]
	height = d["height"][piece]
	rel = np.clip(p[:, 2] / height, 0, 1)
	print(atlas, "texels", len(p), f"{100 * mask.mean():.0f}% of the sheet", flush=True)

	# value bands: facing the sky is lighter, plus height, big soft mottling and a nudge per plane
	r = np.random.RandomState(5)
	nudge = r.uniform(-1, 1, d["face"].max() + 1)[d["face"][k]]
	t = 0.2 + 0.5 * (n[:, 2] * 0.5 + 0.5) + 0.17 * rel + 0.05 * (n[:, 0] * 0.6 - n[:, 1] * 0.4) + 0.1 * nudge + 0.17 * noise3(p, 5.0, 1)
	q = np.clip(t, 0, 1) * BANDS
	t = (np.floor(q) + smooth(0.32, 0.68, q - np.floor(q))) / BANDS
	stops = np.array([s[0] for s in RAMP])
	cols = np.array([hexc(s[1]) for s in RAMP])
	col = np.stack([np.interp(t, stops, cols[:, c]) for c in range(3)], -1)
	col *= (1 + 0.02 * noise3(p, 0.5, 2, 2))[:, None]  # faint brush grain

	# colour layers: hue changes on top of the value bands, each low-key
	over = lambda c, colour, amount: c * (1 - amount[:, None] * COLOUR) + hexc(colour) * amount[:, None] * COLOUR
	col = over(col, SHADE_COOL, smooth(0.62, 0.15, t) * 0.62)  # darks go blue, not just grey
	side = n[:, 0] * 0.6 - n[:, 1] * 0.4  # the same light direction as the bands
	col = over(col, SIDE_COOL, smooth(0.05, -0.65, side) * (1 - np.clip(n[:, 2], 0, 1)) * 0.45)
	col = over(col, SIDE_WARM, smooth(0.05, 0.7, side) * 0.3)
	col = over(col, SPOT_TEAL, strokes(p, 7.0, 31, 0.12) * 0.34)
	col = over(col, SPOT_OCHRE, strokes(p, 6.0, 32, 0.2) * 0.3)
	col = over(col, SPOT_SLATE, strokes(p, 3.2, 33, 0.16) * 0.26)
	col = over(col, RAMP[3][1], strokes(p, 1.1, 34, 0.26) * FINE)
	col = over(col, SHADE_COOL, strokes(p, 1.0, 35, 0.26) * FINE)

	# the foot: darker and tealer where it meets the ground, with a wobbling top
	foot = smooth(1.3, 0.1, p[:, 2] + noise3(p, 1.6, 3) * 0.5)[:, None] * 0.75
	col = col * (1 - foot) + hexc(FOOT) * foot

	# crevices: dark where one lump of a piece meets another
	sub = d["sub"][k]
	crevice = np.zeros(len(p), np.float32)
	for pi in np.unique(d["piece"][d["sub"] > 0]):
		for sj in np.unique(d["sub"][d["piece"] == pi]):
			others = np.where((d["piece"] == pi) & (d["sub"] != sj))[0]
			sel = (piece == pi) & (sub == sj)
			dist, _ = cKDTree(surface_points(d["pos"][others], 0.02)).query(p[sel], workers=-1)
			crevice[sel] = smooth(1.3, 0.08, dist + noise3(p[sel], 1.2, 8) * 0.25)
	col = col * (1 - crevice[:, None] * 0.8) + hexc(CRACK if COLOUR == 0 else CREVICE_DEEP) * crevice[:, None] * 0.8

	# cracks: thin wandering fractures across the bigger rocks, a dark line with a lit side
	for pi, name in enumerate(d["names"]):
		sel = piece == pi
		if not sel.any() or height[sel][0] < 2.0:
			continue
		pts = p[sel]
		rr = np.random.RandomState(100 + pi)
		size = pts.max(0) - pts.min(0)
		dark, lit = np.zeros(len(pts), np.float32), np.zeros(len(pts), np.float32)
		for _ in range(int(1 + np.sqrt(size.max()) * 0.5)):
			c = pts[rr.randint(len(pts))]
			a = rr.uniform(0, np.pi)
			nv = np.array([np.cos(a), np.sin(a), rr.uniform(-0.7, 0.7)])
			nv /= np.linalg.norm(nv)
			dist = (pts - c) @ nv + noise3(pts, 2.2, 7 + pi, 3) * 0.45
			reach = rr.uniform(0.25, 0.6) * size.max()
			fade = smooth(reach, reach * 0.55, np.linalg.norm(pts - c, axis=1))
			w = 0.03 + 0.03 * fade
			dark = np.maximum(dark, smooth(w, w * 0.45, np.abs(dist)) * fade)
			lit = np.maximum(lit, smooth(w * 2.4, w * 1.1, np.abs(dist - w * 1.6)) * fade)
		col[sel] = col[sel] * (1 - lit[:, None] * 0.3) + hexc(CRACK_LIT) * lit[:, None] * 0.3
		col[sel] = col[sel] * (1 - dark[:, None] * 0.7) + hexc(CRACK) * dark[:, None] * 0.7

	# the painted edge: light along every bevel and just past it, wobbling, breaking here and there, weaker facing down
	edge_d, _ = cKDTree(surface_points(d["pos"][d["bevel"] == 1], 0.004)).query(p, workers=-1)
	wob = noise3(p, 0.9, 4, 3) * 0.13
	e = smooth(EDGE_WIDTH, EDGE_WIDTH * 0.25, edge_d + wob)
	e *= smooth(-0.55, 0.05, noise3(p, 3.0, 6))
	e *= 0.35 + 0.65 * smooth(-0.5, 0.4, n[:, 2])
	e = (e * 0.9 * smooth(0.25, 0.9, p[:, 2]) * (1 - crevice))[:, None]
	col = col * (1 - e) + hexc(EDGE) * e

	def save(colours, name):
		img = np.zeros((SIZE, SIZE, 3), np.float32)
		img[mask] = colours
		idx = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)  # bleed past the islands
		img = img[idx[0], idx[1]]
		Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((FINAL, FINAL), Image.LANCZOS).save(os.path.join(OUT, name))
		print("saved", name, flush=True)

	save(col, f"RockKit_{atlas}_Color.png")
	# moss on upward faces (his light generator), with a jagged edge, under nothing: kept apart so a biome can leave it out
	jag = strokes(p, 2.0, 41, 0.0, 1.2) * 0.34 - 0.17
	up = smooth(0.55, 0.86, n[:, 2] + jag) * smooth(0.2, 1.0, p[:, 2])
	body = smooth(0.25, 0.75, up)[:, None]
	moss = hexc(MOSS_DARK) * (1 - body) + hexc(MOSS) * body  # dark at its edge, grass colour inside
	moss = col * (1 - up[:, None] * 0.92) + moss * up[:, None] * 0.92
	lit = up * strokes(p, 1.6, 42, 0.1)
	moss = moss * (1 - lit[:, None] * 0.5) + hexc(MOSS_LIT) * lit[:, None] * 0.5
	save(moss, f"RockKit_{atlas}_Moss.png")


if __name__ == "__main__":
	main()
