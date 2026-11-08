"""Paint the cobble kit's sheets (tools/blender/cobble_kit.py) and the tiling paving texture for paved Part areas.

  python tools/art/paint_cobble_kit.py [--only Pebble,Sett] [--no-paving]
    art/kit/cobbles/Cobble_<Style>_Color.png and _Moss.png (1024 each), Paving_Color.png (one 16-stud tile, 1024, seamless)

Painted per texel on the 3D surface, as the rock kit is (its helpers are reused): light baked in as soft value bands, top light to
cool shade; each stone its own tone, so a run reads as separate stones; dark joints where stones meet one another and the ground;
a painted light edge (bevels on Chisel and Sett, the rounded shoulder on Pebble). Moss sheets add moss on top and in the joints.
Palettes and amounts per style are in STYLES.
"""

import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paint_rock_kit as rp  # noqa: E402  (noise3, strokes, surface_points)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "cobbles")
FINAL = 1024
SIZE = FINAL * 2

# shadow to lit ramps, then accents. Pebble: the reference's blue-grey slate. Chisel: the rock kit's pale stone. Sett: warm grey.
STYLES = {
	"Pebble": {"Ramp": [(0.0, "5a6482"), (0.4, "8590ac"), (0.72, "b3bbcd"), (1.0, "dde2ea")], "Bands": 4, "Soft": (0.34, 0.66), "Tone": 0.1,
			   "Warm": "d6ccb6", "Cool": "6a7ca4", "Crevice": "3f4a64", "Foot": "4f5c70", "Edge": "f2f4f6", "EdgeMode": "shoulder", "Spots": 0.36, "EdgeAmt": 0.95},
	"Chisel": {"Ramp": [(0.0, "5d6c6c"), (0.34, "8b918b"), (0.67, "b6b5a8"), (1.0, "dcd9ca")], "Bands": 5, "Soft": (0.32, 0.68), "Tone": 0.07,
			   "Warm": "d2c6a4", "Cool": "66798e", "Crevice": "38505f", "Foot": "566a68", "Edge": "f5f2e6", "EdgeMode": "bevel", "Spots": 0.3, "Cracks": 0.15},
	# the border stones: fitted tight, so the joints are narrow; more varied stone to stone; cracks in about half
	"Sett": {"Ramp": [(0.0, "6c655e"), (0.4, "9c9284"), (0.72, "c4baa6"), (1.0, "e6ddca")], "Bands": 4, "Soft": (0.25, 0.75), "Tone": 0.15,
			 "Warm": "d8c8a6", "Cool": "7a7f92", "Crevice": "4a4038", "Foot": "564c44", "Edge": "f4ecda", "EdgeMode": "bevel", "Spots": 0.18,
			 "Joint": 0.12, "Nudge": 0.15, "Cracks": 0.5},
	# the same stones in blue-grey, to go with the pebbles (one mesh, two colour maps)
	"SettCool": {"Ramp": [(0.0, "566074"), (0.4, "7a849b"), (0.72, "9fa8bb"), (1.0, "c6cdd9")], "Bands": 4, "Soft": (0.25, 0.75), "Tone": 0.15,
				 "Warm": "cfc6b2", "Cool": "687a9c", "Crevice": "39425a", "Foot": "4a5568", "Edge": "eef0f4", "EdgeMode": "bevel", "Spots": 0.18,
				 "Joint": 0.12, "Nudge": 0.15, "Cracks": 0.5},
}
# the user's pick to try (2026-11-08): Chisel's painting (crisp bands on flat planes, lit bevels, cracks) in Pebble's blue-grey
STYLES["ChiselSlate"] = dict(STYLES["Chisel"], **{k: STYLES["Pebble"][k] for k in ("Ramp", "Warm", "Cool", "Crevice", "Foot", "Edge")})
ATLAS_OF = {"SettCool": "Sett", "ChiselSlate": "Chisel"}  # a colourway painted on another style's pieces
EDGE_WIDTH = 0.11  # studs
MOSS, MOSS_LIT, MOSS_DARK = "349f4c", "4fb65f", "2b7a4a"  # the rock kit's, matched to the terrain grass in Studio
LIGHT = np.array([0.6, -0.4, 0.0], np.float32)  # the rock kit's painted light direction in plan (sun from +x, -y)


def hexc(h):
	return rp.hexc(h)


def smooth(a, b, x):
	return rp.smooth(a, b, x)


def rasterise(d):
	"""every texel inside a triangle: its triangle, its point on the surface, and the interpolated smooth normal"""
	tri = np.full((SIZE, SIZE), -1, np.int32)
	pos = np.zeros((SIZE, SIZE, 3), np.float32)
	nor = np.zeros((SIZE, SIZE, 3), np.float32)
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
		m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
		tri[y0:y1, x0:x1][m] = k
		P, N = d["pos"][k], d["cnor"][k]
		for ax in range(3):
			pos[y0:y1, x0:x1, ax][m] = (w0 * P[0, ax] + w1 * P[1, ax] + w2 * P[2, ax])[m]
			nor[y0:y1, x0:x1, ax][m] = (w0 * N[0, ax] + w1 * N[1, ax] + w2 * N[2, ax])[m]
	return tri, pos, nor


def paint_sheet(d, style):
	S = STYLES[style]
	tri, pos, nor = rasterise(d)
	mask = tri >= 0
	k = tri[mask]
	p = pos[mask]
	n = nor[mask]
	n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
	piece, sub = d["piece"][k], d["sub"][k]
	stone = piece * 1000 + sub
	print(style, "texels", len(p), f"{100 * mask.mean():.0f}% of the sheet", flush=True)
	# each stone's height and centre, so light and the foot are judged per stone
	sid_all = d["piece"] * 1000 + d["sub"]
	tops = {s: d["pos"][sid_all == s][..., 2].max() for s in np.unique(sid_all)}
	h = np.array([tops[s] for s in stone], np.float32)
	rel = np.clip(p[:, 2] / np.maximum(h, 0.2), 0, 1)

	# value bands: facing the sky and the light, a little by height, a nudge per stone, soft mottling
	r = np.random.RandomState(7)
	ids = np.unique(sid_all)
	nudge_of = dict(zip(ids, r.uniform(-1, 1, len(ids))))
	nudge = np.array([nudge_of[s] for s in stone], np.float32)
	side = n @ LIGHT
	t = 0.16 + 0.5 * (n[:, 2] * 0.5 + 0.5) + 0.16 * side + 0.12 * rel + S.get("Nudge", 0.09) * nudge + 0.08 * rp.noise3(p, 2.5, 1)
	q = np.clip(t, 0, 1) * S["Bands"]
	t = (np.floor(q) + smooth(S["Soft"][0], S["Soft"][1], q - np.floor(q))) / S["Bands"]
	stops = np.array([s[0] for s in S["Ramp"]])
	cols = np.array([hexc(s[1]) for s in S["Ramp"]])
	col = np.stack([np.interp(t, stops, cols[:, c]) for c in range(3)], -1)
	col *= (1 + 0.02 * rp.noise3(p, 0.35, 2, 2))[:, None]

	over = lambda c, colour, amount: c * (1 - amount[:, None]) + hexc(colour) * amount[:, None]
	# each stone a little warmer or cooler than its neighbours, darks bluer, a few soft stroke patches
	hue_of = dict(zip(ids, r.uniform(-1, 1, len(ids))))
	hue = np.array([hue_of[s] for s in stone], np.float32)
	col = over(col, S["Warm"], np.clip(hue, 0, 1) * S["Tone"] * 2.2)
	col = over(col, S["Cool"], np.clip(-hue, 0, 1) * S["Tone"] * 2.2)
	col = over(col, S["Cool"], smooth(0.55, 0.12, t) * 0.5)
	col = over(col, S["Warm"], smooth(0.1, 0.7, side) * np.clip(n[:, 2], 0, 1) * 0.18)
	col = over(col, S["Cool"], rp.strokes(p, 1.6, 31, 0.2) * S["Spots"] * 0.6)
	col = over(col, S["Ramp"][3][1], rp.strokes(p, 0.7, 34, 0.3) * 0.1)

	# joints: dark where a stone nears its neighbours in the same piece, and where it meets the ground
	crevice = np.zeros(len(p), np.float32)
	for pi in np.unique(piece):
		in_piece = d["piece"] == pi
		subs = np.unique(d["sub"][in_piece])
		if len(subs) < 2:
			continue
		for sj in subs:
			sel = (piece == pi) & (sub == sj)
			if not sel.any():
				continue
			others = in_piece & (d["sub"] != sj)
			dist, _ = cKDTree(rp.surface_points(d["pos"][others], 0.01)).query(p[sel], workers=-1)
			crevice[sel] = smooth(S.get("Joint", 0.28), 0.03, dist + rp.noise3(p[sel], 0.6, 8) * 0.04)
	foot = smooth(0.2, 0.0, p[:, 2] + rp.noise3(p, 0.8, 3) * 0.05) * 0.75
	col = over(col, S["Foot"], foot)
	col = over(col, S["Crevice"], crevice * 0.78)

	# cracks: a few stones split by a thin wandering crack across their width, a dark line with a lit lip (the user: "little cracks
	# in them at points")
	if S.get("Cracks", 0) > 0:
		rr = np.random.RandomState(77)
		dark, lip = np.zeros(len(p), np.float32), np.zeros(len(p), np.float32)
		for s in ids:
			if rr.rand() > S["Cracks"]:
				continue
			sel = np.where(stone == s)[0]
			top = sel[n[sel, 2] > 0.7]
			if len(top) < 40:
				continue
			xy = p[top, :2] - p[top, :2].mean(0)
			_, _, vt = np.linalg.svd(xy, full_matrices=False)
			u = vt[0]  # the stone's long axis: the crack runs across it
			length = np.ptp(xy @ u)
			a = math.atan2(u[1], u[0]) + rr.uniform(-0.45, 0.45)
			nv = np.array([math.cos(a), math.sin(a), 0.0], np.float32)
			c = p[top].mean(0) + np.array([u[0], u[1], 0.0], np.float32) * rr.uniform(-0.28, 0.28) * length
			ps = p[sel]
			rel_c = ps - c
			dist = rel_c @ nv + rp.noise3(ps, 0.3, 60 + int(s) % 50, 3) * 0.07
			along = np.linalg.norm(rel_c - np.outer(rel_c @ nv, nv), axis=1)
			reach = rr.uniform(0.45, 1.3)  # some cross the whole stone, some stop partway
			fade = smooth(reach, reach * 0.55, along)
			w = rr.uniform(0.018, 0.03)
			dark[sel] = np.maximum(dark[sel], smooth(w, w * 0.4, np.abs(dist)) * fade)
			lip[sel] = np.maximum(lip[sel], smooth(w * 2.6, w * 1.2, np.abs(dist - w * 1.8)) * fade)
		col = over(col, S["Edge"], lip * 0.3)
		col = over(col, S["Crevice"], dark * 0.8)

	# the painted light: strokes on the few edges that face up into the light, as a painter dabs them, swelling and thinning,
	# left out in stretches; never a line round every edge and corner (the user: "from afar it looks like we've added edge lines")
	L3 = np.array([0.456, -0.304, 0.836], np.float32)
	width = EDGE_WIDTH * (0.5 + 1.3 * smooth(-0.7, 0.7, rp.noise3(p, 0.8, 51)))
	if S["EdgeMode"] == "bevel" and (d["bevel"] == 1).any():
		bev = np.where(d["bevel"] == 1)[0]
		pts, idx = rp.surface_points(d["pos"][bev], 0.002, with_index=True)
		edge_d, nn = cKDTree(pts).query(p, workers=-1)
		facing = d["nor"][bev[idx[nn]]] @ L3  # the bevel's own facing: only edges turned up toward the light
		e = smooth(width, width * 0.15, edge_d + rp.noise3(p, 0.5, 4, 3) * 0.03)
	else:
		# the shoulder of a rounded stone, where its top turns into its side
		facing = n @ L3
		e = np.exp(-(((n[:, 2] - 0.66) / 0.12) ** 2)) * (0.75 + 0.25 * rp.strokes(p, 0.45, 47, 0.0, 2.0))
	e *= smooth(0.5, 0.86, facing)
	e *= smooth(-0.2, 0.3, rp.noise3(p, 1.2, 52))  # whole stretches left unpainted
	e *= 0.6 + 0.4 * rp.strokes(p, 0.4, 53, 0.0, 2.5)  # a dry brush, not a clean line
	e *= smooth(0.2, 0.6, rel) * (1 - crevice)
	col = over(col, S["Edge"], e * S.get("EdgeAmt", 0.75))

	def save(colours, name):
		img = np.zeros((SIZE, SIZE, 3), np.float32)
		img[mask] = colours
		idx = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
		img = img[idx[0], idx[1]]
		Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((FINAL, FINAL), Image.LANCZOS).save(os.path.join(OUT, name))
		print("saved", name, flush=True)

	save(col, f"Cobble_{style}_Color.png")
	if not style.startswith("Sett"):
		# moss: on the tops and creeping up out of the joints, jagged edged, darker where it meets the stone
		jag = rp.strokes(p, 0.9, 41, 0.0, 1.2) * 0.34 - 0.17
		up = smooth(0.62, 0.9, n[:, 2] + jag) * smooth(0.35, 0.9, rel)
		up = np.maximum(up, smooth(0.35, 0.85, crevice + jag) * 0.8)
		body = smooth(0.25, 0.75, up)[:, None]
		moss = hexc(MOSS_DARK) * (1 - body) + hexc(MOSS) * body
		moss = col * (1 - up[:, None] * 0.9) + moss * up[:, None] * 0.9
		lit = up * rp.strokes(p, 0.8, 42, 0.1)
		moss = moss * (1 - lit[:, None] * 0.45) + hexc(MOSS_LIT) * lit[:, None] * 0.45
		save(moss, f"Cobble_{style}_Moss.png")


# ---------------------------------------------------------------------------------------------------------------- paving
PAVE = {"Tile": 16.0, "Grid": 7, "Joint": 0.1, "Rim": 0.3, "Base": ["cfc4b0", "c4b8a2", "d8cebc", "bcb19e", "cabfac"], "Joint_C": "8a8276", "Shade": "8f8a8e"}


def periodic_noise(X, Y, T, seed, terms=14, fmax=6):
	r = np.random.RandomState(seed)
	out = np.zeros_like(X)
	for _ in range(terms):
		kx, ky = r.randint(-fmax, fmax + 1), r.randint(1, fmax + 1)
		out += np.sin(2 * np.pi * (kx * X + ky * Y) / T + r.uniform(0, 2 * np.pi)) / math.hypot(kx, ky)
	return out / np.abs(out).max()


def paving():
	"""seamless flagstones for a paved Part (a MaterialVariant on Slate or Pavement, StudsPerTile = PAVE Tile): irregular stones from
	a jittered grid, each its own warm grey, dark joints, a lit rim on the edges facing the painted light and a shaded one opposite"""
	T, N = PAVE["Tile"], FINAL * 2
	r = np.random.RandomState(11)
	g = PAVE["Grid"]
	cells = np.array([((i + 0.5 + r.uniform(-0.38, 0.38)) * T / g, (j + 0.5 + r.uniform(-0.38, 0.38)) * T / g) for i in range(g) for j in range(g)])
	pts = np.concatenate([cells + [dx * T, dy * T] for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
	owner = np.tile(np.arange(len(cells)), 9)
	xs = (np.arange(N) + 0.5) / N * T
	X, Y = np.meshgrid(xs, xs)
	P = np.stack([X.ravel(), Y.ravel()], -1)
	dist, idx = cKDTree(pts).query(P, k=2, workers=-1)
	p1, p2 = pts[idx[:, 0]], pts[idx[:, 1]]
	# distance to the border between the two nearest stones
	mid = (p1 + p2) / 2
	nrm = (p2 - p1) / np.maximum(np.linalg.norm(p2 - p1, axis=1, keepdims=True), 1e-6)
	edge = np.abs(np.sum((mid - P) * nrm, axis=1)).reshape(N, N)
	cell = owner[idx[:, 0]].reshape(N, N)
	tone = r.uniform(-1, 1, len(cells))[cell]
	base = np.array([hexc(PAVE["Base"][c % len(PAVE["Base"])]) for c in range(len(cells))])[cell]
	col = base * (1 + 0.05 * tone[..., None])
	wob = periodic_noise(X, Y, T, 3) * 0.05
	col = col * (1 + 0.04 * periodic_noise(X, Y, T, 5, 20, 12)[..., None])
	light = np.array([-0.6, 0.6])  # image space: lit from the upper left
	facing = (nrm @ light).reshape(N, N)
	rim = smooth(PAVE["Rim"], 0.04, edge + wob)
	col = col * (1 + (0.2 * np.clip(facing, 0, 1) * rim)[..., None])
	col = col * (1 - (0.22 * np.clip(-facing, 0, 1) * rim)[..., None]) + hexc(PAVE["Shade"]) * (0.12 * np.clip(-facing, 0, 1) * rim)[..., None]
	joint = smooth(PAVE["Joint"], PAVE["Joint"] * 0.55, edge + wob * 0.6)
	col = col * (1 - joint[..., None] * 0.85) + hexc(PAVE["Joint_C"]) * joint[..., None] * 0.85
	Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((FINAL, FINAL), Image.LANCZOS).save(os.path.join(OUT, "Paving_Color.png"))
	print("saved Paving_Color.png", len(cells), "stones a tile", flush=True)


def main():
	only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else list(STYLES)
	all_data = dict(np.load(os.path.join(OUT, "bake.npz")))
	for style in only:
		ids = np.where(all_data["atlas"] == ATLAS_OF.get(style, style))[0]
		keep = np.isin(all_data["piece"], ids)
		d = dict(all_data)
		for key in ("pos", "uv", "nor", "cnor", "piece", "bevel", "face", "sub"):
			d[key] = all_data[key][keep]
		paint_sheet(d, style)
	if "--no-paving" not in sys.argv:
		paving()


if __name__ == "__main__":
	main()
