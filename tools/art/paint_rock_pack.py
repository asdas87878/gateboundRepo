"""Paint the rock pack (tools/blender/rock_pack.py): per texel on the 3D surface, so edges and cracks run across UV seams. Light is painted in.

  python tools/art/paint_rock_pack.py [--out <folder>] [--sheets A,B] [--workers 4]     Pack_<sheet>_Moss.png, Pack_<sheet>_Clean.png, 1024 each

Layers: one flat tone per plane, each lump lighter at its top and darker at its foot; low-key hewn facets drawn as shapes (not filtered noise); cool darks, warm and
cool sides; dark crevices where lumps meet; a few cracks; soft pale edge highlights with their own rhythm (strong runs, faint stretches, gaps, a little bleed); crisp
brush grain over all of it. Moss sits on top faces and hangs over the rims; Clean leaves it off and lifts the stone a touch. Colours are in PALETTES.
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from crisp_paint import crisp_pass  # noqa: E402
from paint_rock_kit import SIZE, FINAL, hexc, noise3, rasterise, smooth, strokes, surface_points  # noqa: E402

# Stone matches the earlier rocks and the bridge. The lilac in the reference shot is blue haze over pale grey, so it isn't a paint colour.
PALETTES = {
	"Stone": {
		"Ramp": [(0.0, "5f6c78"), (0.34, "8e949a"), (0.67, "b7b7b3"), (1.0, "dbdad3")],
		"Edge": "f7f4e8",
		"Foot": "566a6c",
		"Crevice": "3a4f63",
		"Crack": "5e6b6e",
		"CrackLit": "ebe8da",
		"ShadeCool": "66798e",
		"SideCool": "8195a8",
		"SideWarm": "d2c6a4",
		"SpotTeal": "6f8c8a",
		"SpotOchre": "b5a982",
		"SpotSlate": "7c8798",
		"Moss": "349f4c",
		"MossLit": "4fb65f",
		"MossDark": "2b7a4a",
	},
}
BANDS = 5
EDGE_WIDTH = 0.25  # studs, past the bevel, at about 20 texels a stud
CLEAN_LIFT = 1.05


def paint_sheet(job):
	"""one sheet. A separate process per sheet, as each takes a minute or so and most of a gigabyte"""
	out, sheet, palette_name = job
	all_data = np.load(os.path.join(out, "bake.npz"))
	all_data = {k: all_data[k] for k in all_data.files}
	ids = np.where(all_data["sheet"] == sheet)[0]
	keep = np.isin(all_data["piece"], ids)
	d = dict(all_data)
	for key in ("pos", "uv", "nor", "piece", "bevel", "face", "sub"):
		d[key] = all_data[key][keep]
	P = PALETTES[palette_name]
	tri, pos = rasterise(d)
	mask = tri >= 0
	k = tri[mask]
	p = pos[mask]
	n = d["nor"][k]
	piece = d["piece"][k]
	sub = d["sub"][k]
	height = d["height"][piece]
	# how detailed this sheet is: big pieces at low texels a stud get bigger strokes
	a3 = np.linalg.norm(np.cross(d["pos"][:, 1] - d["pos"][:, 0], d["pos"][:, 2] - d["pos"][:, 0]), axis=1).sum() / 2
	uv = d["uv"]
	a2 = np.abs(np.cross(uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0])).sum() / 2
	density = float(np.sqrt(a2 * FINAL * FINAL / a3))
	sc = float(np.clip(20 / density, 0.8, 2.6))
	print(sheet, f"{density:.1f} texels a stud, {100 * mask.mean():.0f}% of the sheet, {len(p)} texels", flush=True)

	# each lump's own height range, so every block in a cluster reads as its own block
	key = piece * 1000 + sub
	tri_key = d["piece"] * 1000 + d["sub"]
	lo, hi = {}, {}
	zs = d["pos"][:, :, 2]
	for tk in np.unique(tri_key):
		z = zs[tri_key == tk]
		lo[tk], hi[tk] = z.min(), z.max()
	zlo = np.vectorize(lo.get)(key).astype(np.float32)
	zhi = np.vectorize(hi.get)(key).astype(np.float32)
	rel_lump = np.clip((p[:, 2] - zlo) / np.maximum(zhi - zlo, 0.1), 0, 1)
	rel = np.clip(p[:, 2] / height, 0, 1)

	# the tone of each flat plane, with a nudge per plane; bevels take their neighbours' tone
	r = np.random.RandomState(5)
	nudge = r.uniform(-1, 1, d["face"].max() + 1)[d["face"][k]] * (1 - d["bevel"][k])
	side = n[:, 0] * 0.6 - n[:, 1] * 0.4
	t = 0.11 + 0.48 * (n[:, 2] * 0.5 + 0.5) + 0.18 * rel_lump + 0.05 * rel + 0.06 * side + 0.1 * nudge + 0.015 * noise3(p, 6.0 * sc, 1)
	# hewn facets: shapes drawn across the faces at a low key, the size of a big brush. Firm edges, wandering a little
	seeds = surface_points(d["pos"], 11.0 * sc * sc)
	warp = np.stack([noise3(p, 2.4 * sc, 60 + i, 2) for i in range(3)], -1) * 0.7 * sc
	_, cell = cKDTree(seeds).query(p + warp, workers=2)
	t += r.uniform(-0.02, 0.02, len(seeds))[cell]
	q = np.clip(t, 0, 1) * BANDS
	t = (np.floor(q) + smooth(0.34, 0.66, q - np.floor(q))) / BANDS
	stops = np.array([s[0] for s in P["Ramp"]])
	cols = np.array([hexc(s[1]) for s in P["Ramp"]])
	col = np.stack([np.interp(t, stops, cols[:, c]) for c in range(3)], -1)

	def over(c, colour, amount):
		return c * (1 - amount[:, None]) + hexc(colour) * amount[:, None]

	col = over(col, P["ShadeCool"], smooth(0.62, 0.15, t) * 0.62)
	col = over(col, P["SideCool"], smooth(0.05, -0.65, side) * (1 - np.clip(n[:, 2], 0, 1)) * 0.42)
	col = over(col, P["SideWarm"], smooth(0.05, 0.7, side) * 0.07)
	# close in hue and value: the stone stays one stone. Earlier paint read as camouflage with more of these
	col = over(col, P["SpotTeal"], strokes(p, 8.0 * sc, 31, 0.3) * 0.1)
	col = over(col, P["SpotOchre"], strokes(p, 7.0 * sc, 32, 0.4) * 0.05)
	col = over(col, P["SpotSlate"], strokes(p, 3.6 * sc, 33, 0.3) * 0.09)

	# the foot, where it meets the ground
	col = over(col, P["Foot"], smooth(1.3 * sc, 0.1, p[:, 2] + noise3(p, 1.6, 3) * 0.5) * 0.72)

	# crevices: dark where one lump meets another
	crevice = np.zeros(len(p), np.float32)
	reach = 0.85 * sc**0.5
	spacing = max(0.015, (reach * 0.13) ** 2)
	for pi in np.unique(d["piece"]):
		subs = np.unique(d["sub"][d["piece"] == pi])
		if len(subs) < 2:
			continue
		for sj in subs:
			others = np.where((d["piece"] == pi) & (d["sub"] != sj))[0]
			sel = (piece == pi) & (sub == sj)
			if not sel.any():
				continue
			pts_other, idx_other = surface_points(d["pos"][others], spacing, True)
			dist, near_other = cKDTree(pts_other).query(p[sel], workers=2)
			wobble = noise3(p[sel], 1.0 * sc, 8) * 0.2 * reach
			facing = np.abs((n[sel] * d["nor"][others][idx_other[near_other]]).sum(1))
			crevice[sel] = (smooth(reach * 0.5, reach * 0.34, dist + wobble) * 0.74 + smooth(reach * 1.5, 0.05, dist + wobble) * 0.26) * smooth(0.96, 0.78, facing)
	col = over(col, P["Crevice"], crevice * 0.86)

	# a few thin cracks, a dark line with a lit side
	for pi in np.unique(piece):
		sel = piece == pi
		if height[sel][0] < 3.0:
			continue
		pts = p[sel]
		rr = np.random.RandomState(100 + int(pi))
		size = pts.max(0) - pts.min(0)
		dark, lit = np.zeros(len(pts), np.float32), np.zeros(len(pts), np.float32)
		for _ in range(int(0.6 + np.sqrt(size.max()) * 0.32)):
			c = pts[rr.randint(len(pts))]
			a = rr.uniform(0, np.pi)
			nv = np.array([np.cos(a), np.sin(a), rr.uniform(-0.7, 0.7)])
			nv /= np.linalg.norm(nv)
			dist = (pts - c) @ nv + noise3(pts, 2.6 * sc, 7 + int(pi), 3) * 0.32 * sc
			far = rr.uniform(0.18, 0.42) * min(size.max(), 26)
			fade = smooth(far, far * 0.55, np.linalg.norm(pts - c, axis=1))
			w = (0.016 + 0.024 * fade) * sc
			dark = np.maximum(dark, smooth(w, w * 0.45, np.abs(dist)) * fade)
			lit = np.maximum(lit, smooth(w * 2.4, w * 1.1, np.abs(dist - w * 1.6)) * fade)
		col[sel] = col[sel] * (1 - lit[:, None] * 0.2) + hexc(P["CrackLit"]) * lit[:, None] * 0.2
		col[sel] = col[sel] * (1 - dark[:, None] * 0.62) + hexc(P["Crack"]) * dark[:, None] * 0.62

	# edge highlights: soft pale bands, each with its own rhythm
	bevel_tris = np.where(d["bevel"] == 1)[0]
	pts_edge, idx_edge = surface_points(d["pos"][bevel_tris], 0.006 * sc * sc, True)
	edge_d, near = cKDTree(pts_edge).query(p, workers=2)
	near_up = d["nor"][bevel_tris][idx_edge[near], 2]
	width = max(EDGE_WIDTH * sc**0.7, 1.7 / density)
	gaps = smooth(-0.72, 0.1, noise3(p, 10.0 * sc, 6))  # sparse gaps
	runs = 0.5 + 0.5 * smooth(-0.3, 0.4, noise3(p, 13.0 * sc, 16))  # strong runs and faint stretches
	w = width * (0.75 + 0.75 * smooth(-0.15, 0.7, noise3(p, 2.8 * sc, 26)))
	dist = edge_d + noise3(p, 1.9 * sc, 4, 2) * 0.06 * sc
	e = smooth(w, w * 0.22, dist)
	bleed = smooth(w * 4.5, w, dist) * strokes(p, 0.9 * sc, 46, 0.42) * 0.42
	e = np.maximum(e, bleed) * gaps * runs
	e *= 0.5 + 0.5 * smooth(-0.15, 0.55, near_up)  # upper edges catch more than undersides
	e *= 0.32 + 0.68 * smooth(-0.5, 0.35, n[:, 2])
	e = e * 0.96 * smooth(0.2, 0.9, p[:, 2]) * (1 - crevice)
	col = over(col, P["Edge"], e)

	def finish(colours, name):
		"""the crisp brush grain, island by island so it never crosses a seam, then shrink"""
		img = np.zeros((SIZE, SIZE, 3), np.float32)
		img[mask] = colours
		labels, count = ndimage.label(mask)
		rng = np.random.default_rng(7)
		for i, box in enumerate(ndimage.find_objects(labels)):
			y, x = box
			if y.stop - y.start < 24 or x.stop - x.start < 24:
				continue
			crop = img[box] * 255
			done = crisp_pass(crop, rng, 2, False, 1.0, (labels[box] == i + 1).astype(np.float32), shapes=0.3, marks=0.75, dark=0.35, sharpen_by=0.3, keep_brightness=True)
			img[box] = done / 255
		idx = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
		img = img[idx[0], idx[1]]
		Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((FINAL, FINAL), Image.LANCZOS).save(os.path.join(out, name))

	finish(np.clip(col * CLEAN_LIFT, 0, 1), f"Pack_{sheet}_Clean.png")

	# moss: drawn shapes on upward faces, some bare stone between, hanging over the rims in strands
	jag = strokes(p, 2.0 * sc, 41, 0.0, 1.2) * 0.34 - 0.17
	up = smooth(0.52, 0.84, n[:, 2] + jag) * smooth(0.2, 1.0, p[:, 2])
	up *= smooth(-0.8, -0.7, noise3(p, 7.0 * sc, 44) + jag * 0.5)
	tops = np.where((d["nor"][:, 2] > 0.72) & (d["bevel"] == 0) & (d["pos"][:, :, 2].mean(1) > 0.3))[0]
	if len(tops):
		pts_top = surface_points(d["pos"][tops], 0.03 * sc * sc)
		dist_top, which = cKDTree(pts_top).query(p, workers=2)
		strands = noise3(p * np.array([1, 1, 0.3], np.float32), 0.42 * sc, 48, 3)
		hang = (0.12 + 0.62 * smooth(-0.1, 0.8, strands)) * sc**0.5
		hang *= 0.35 + 0.65 * smooth(-0.4, 0.2, noise3(p, 4.0 * sc, 49))
		above = pts_top[which, 2] >= p[:, 2] - 0.02
		drape = smooth(hang, hang * 0.72, dist_top) * above * (n[:, 2] < 0.6) * (n[:, 2] > -0.3)
		up = np.maximum(up, drape)
	body = smooth(0.25, 0.75, up)[:, None]
	moss = hexc(P["MossDark"]) * (1 - body) + hexc(P["Moss"]) * body
	moss = moss * (1 + 0.05 * np.clip(rel_lump, 0, 1))[:, None]
	lit = strokes(p, 1.5 * sc, 42, 0.14)
	moss = moss * (1 - lit[:, None] * 0.5) + hexc(P["MossLit"]) * lit[:, None] * 0.5
	dark_clump = strokes(p, 1.1 * sc, 43, 0.3)
	moss = moss * (1 - dark_clump[:, None] * 0.3) + hexc(P["MossDark"]) * dark_clump[:, None] * 0.3
	finish(col * (1 - up[:, None] * 0.94) + moss * up[:, None] * 0.94, f"Pack_{sheet}_Moss.png")
	print("saved", sheet, flush=True)
	return sheet


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default=os.path.join("art", "kit", "rock_pack"))
	ap.add_argument("--sheets")
	ap.add_argument("--palette", default="Stone")
	ap.add_argument("--workers", type=int, default=4)
	args = ap.parse_args()
	out = os.path.join(ROOT, args.out)
	sheets = sorted(set(np.load(os.path.join(out, "bake.npz"))["sheet"].tolist()))
	if args.sheets:
		sheets = [s for s in sheets if s in args.sheets.split(",")]
	jobs = [(out, s, args.palette) for s in sheets]
	if args.workers <= 1 or len(jobs) == 1:
		for j in jobs:
			paint_sheet(j)
	else:
		with ProcessPoolExecutor(args.workers) as pool:
			for done in pool.map(paint_sheet, jobs):
				print("done", done, flush=True)


if __name__ == "__main__":
	main()
