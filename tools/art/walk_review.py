"""Numbers for the landscape reviews (docs/style/landscape-review.md): a pass's walk views against reference frames from the
gitignored research/ folder. How much sky; near-ground contrast at tuft, clump and big-mass scale; near-black share; road
against grass; the trail mesh's line against the painted line; how much terrain a walking player can see over; what casts
the big shadows; how the road meets the bridges.

  blender --background --python tools/blender/dump_heights.py -- art/lands/land1/map.json art/lands/land1/beauty/_cache/heights.npz
  python tools/art/walk_review.py [<pass> ...]     (passes under art/lands/land1/beauty; the last is the one looked at closely)
"""

import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
R = os.path.join(ROOT, "research")
B = os.path.join(ROOT, "art", "lands", "land1", "beauty")
PASSES = sys.argv[1:] or ["w09"]
LAST = PASSES[-1]
M = json.load(open(os.path.join(ROOT, "art", "lands", "land1", "map.json"), encoding="utf-8"))
WALKS = ["walk_road", "walk_meadow", "walk_gate_road", "walk_ruins"]


def lab(rgb):
	c = rgb / 255.0
	c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
	x = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
	x = x / np.array([0.9505, 1.0, 1.089])
	f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
	return 116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])


def frame(path):
	"""skyline (median, from the top), near-ground contrast at three scales, share of detail in the busiest fifth of rows,
	near-black share. Near ground = the lower third; the character's box in the middle is left out of everything but the sky.
	The sky test reads pale rock as sky, so ignore the skyline for frames with no sky (Lonely Mountains)."""
	im = Image.open(path).convert("RGB")
	W = 640
	H = int(W * im.height / im.width)
	L, a, b = lab(np.asarray(im.resize((W, H)), np.float64))
	lbl, _ = ndimage.label((L > 50) & (b < 10) & (np.abs(a) < 14))
	top = set(np.unique(lbl[0])) - {0}
	sky = np.isin(lbl, list(top)) if top else np.zeros(L.shape, bool)
	skyline = np.array([np.max(np.where(sky[:, x])[0]) + 1 if sky[:, x].any() else 0 for x in range(W)])
	line = float(np.median(skyline)) / H
	mask = np.ones(L.shape, bool)
	mask[int(H * 0.45) :, int(W * 0.36) : int(W * 0.64)] = False
	near = np.zeros(L.shape, bool)
	near[int(H * 0.68) :, :] = True
	near &= mask
	g1, g6, g30 = (ndimage.gaussian_filter(L, s) for s in (1, 6, 30))
	rows = (np.abs(g1 - g6) * mask).sum(1)
	k = int(H * 0.2)
	band = float(np.convolve(rows, np.ones(k), "valid").max() / max(rows.sum(), 1e-6))
	black = float(((L < 15) & mask).sum() / mask.sum())
	return [line, float((g1 - g6)[near].std()), float((g6 - g30)[near].std()), float(g30[near].std()), band, black]


def row(name, files):
	m = np.mean([frame(f) for f in files], 0)
	print(f"| {name} | {len(files)} | {m[0] * 100:.0f}% | {m[1]:.1f} | {m[2]:.1f} | {m[3]:.1f} | {m[4] * 100:.0f}% | {m[5] * 100:.1f}% |")


def pick(folder, listfile):
	keep = [ln.strip() for ln in open(listfile, encoding="utf-8") if ln.strip() and not ln.startswith("#")]
	return [os.path.join(folder, k + ".jpg") for k in keep if os.path.exists(os.path.join(folder, k + ".jpg"))]


def composition():
	print("| Set | Frames | Skyline | Near ground: tuft | clump | big masses | Detail in busiest fifth of rows | Near-black |")
	print("|---|---|---|---|---|---|---|---|")
	for p in PASSES:
		row(f"Ours ({p})", [os.path.join(B, p, v, "final.png") for v in WALKS])
	row("GPT-6.2 game", pick(os.path.join(R, "gpt62", "game"), os.path.join(R, "gpt62", "pick.txt")))
	row("Genshin fields", pick(os.path.join(R, "genshin", "frames"), os.path.join(R, "genshin", "pick_fields.txt")))
	row("BotW fields", pick(os.path.join(R, "botw", "frames"), os.path.join(R, "botw", "pick_fields.txt")))
	row("Valheim meadows", pick(os.path.join(R, "valheim", "frames"), os.path.join(R, "valheim", "pick_meadows.txt")))
	row("Lonely Mountains", pick(os.path.join(R, "lmd", "frames"), os.path.join(R, "lmd", "pick_trails.txt")))
	print(f"\n{LAST} per view: skyline, near ground tuft / clump / big masses, near-black")
	for v in WALKS[:2] + ["walk_forest"] + WALKS[2:] + ["walk_bridge"]:
		m = frame(os.path.join(B, LAST, v, "final.png"))
		print(f"  {v:15s} {m[0] * 100:3.0f}%  {m[1]:.1f} / {m[2]:.1f} / {m[3]:.1f}  {m[5] * 100:.1f}%")


def road_vs_grass():
	"""mean colour in boxes (x0, y0, x1, y1 as fractions of the frame) picked by eye on the sheets: road, then grass"""
	print("\nRoad vs grass:")
	boxes = {
		"ours walk_road": (os.path.join(B, LAST, "walk_road", "final.png"), (0.26, 0.93, 0.36, 0.995), (0.60, 0.80, 0.85, 0.99)),
		"ours walk_gate_road": (os.path.join(B, LAST, "walk_gate_road", "final.png"), (0.20, 0.90, 0.40, 0.99), (0.03, 0.72, 0.20, 0.85)),
		"Genshin path": (os.path.join(R, "genshin", "frames", "G_00240_0002.jpg"), (0.10, 0.50, 0.38, 0.90), (0.72, 0.55, 0.95, 0.90)),
		"GPT-6.2 road": (os.path.join(R, "gpt62", "game", "g_145.jpg"), (0.26, 0.55, 0.38, 0.72), (0.56, 0.72, 0.70, 0.86)),
		"BotW dirt": (os.path.join(R, "botw", "frames", "D_00180_0050.jpg"), (0.16, 0.60, 0.38, 0.90), (0.72, 0.45, 0.96, 0.70)),
	}
	for name, (f, rb, gb) in boxes.items():
		im = np.asarray(Image.open(f).convert("RGB"), np.float64)
		h, w = im.shape[:2]
		out = []
		for x0, y0, x1, y1 in (rb, gb):
			Lc, ac, bc = lab(im[int(y0 * h) : int(y1 * h), int(x0 * w) : int(x1 * w)])
			out.append((Lc.mean(), ac.mean(), bc.mean()))
		print(f"  {name:22s} road L {out[0][0]:5.1f} (a {out[0][1]:5.1f} b {out[0][2]:5.1f})   grass L {out[1][0]:5.1f}   road-grass {out[0][0] - out[1][0]:+5.1f}")


def chaikin(pts, it=3):
	"""the same smoothing as vale_beauty.smooth_line"""
	p = [np.array(q, float) for q in pts]
	for _ in range(it):
		q = [p[0]]
		for a, b in zip(p, p[1:]):
			q += [a + (b - a) * 0.25, a + (b - a) * 0.75]
		q.append(p[-1])
		p = q
	return p


def seg_d(q, pts):
	best = 1e9
	for a, b in zip(pts, pts[1:]):
		ab = b - a
		t = np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
		best = min(best, float(np.linalg.norm(q - (a + ab * t))))
	return best


def trail_lines():
	"""the trail mesh follows the smoothed line; the ground paint, terrain flattening and grass clearing use the raw path"""
	print("\nTrail mesh vs painted line:")
	half = M["Beauty"]["Ground"].get("PathHalf", 3.2)
	for k, line in enumerate(M["Paths"]):
		raw = [np.array(p, float) for p in line]
		sm = chaikin(line)
		dense = []
		for a, b in zip(sm, sm[1:]):
			n = max(1, int(np.linalg.norm(b - a) / 2))
			dense += [a + (b - a) * (t / n) for t in range(n)]
		dev = np.array([seg_d(q, raw) for q in dense])
		print(f"  path {k}: max off {dev.max():5.1f} studs, off by more than the road's half width on {100 * (dev > half).mean():3.0f}% of its length")


d = np.load(os.path.join(B, "_cache", "heights.npz"))
xs, ys, Z = d["xs"], d["ys"], d["Z"]
step = float(xs[1] - xs[0])


def zat(x, y):
	i = np.clip(((np.asarray(x) - xs[0]) / step).astype(int), 0, len(xs) - 1)
	j = np.clip(((np.asarray(y) - ys[0]) / step).astype(int), 0, len(ys) - 1)
	return Z[j, i]


def terrain():
	print("\nTerrain from the player's camera (6.6 studs up), along each walk view, 100 degree wedge:")
	rr = np.arange(5, 400, 2.5)
	for v in M["Beauty"]["Views"]:
		if "Player" not in v:
			continue
		px, py = v["Player"]
		head = math.atan2(v["Facing"][1] - py, v["Facing"][0] - px)
		cz = float(zat(px, py)) + 6.6
		vis_near, tot_near, vis_all, tot_all = 0, 0, 0, 0
		rise = []
		for da in np.radians(np.arange(-50, 50.1, 1.0)):
			h = zat(px + np.cos(head + da) * rr, py + np.sin(head + da) * rr)
			ang = (h - cz) / rr
			visible = ang >= np.maximum.accumulate(np.concatenate([[-1e9], ang[:-1]]))
			sel = rr <= 150
			vis_all += visible.sum()
			tot_all += len(rr)
			vis_near += visible[sel].sum()
			tot_near += sel.sum()
			rise.append(h[sel].max() - h[sel].min())
		print(f"  {v['Name']:15s} ground visible to 150 studs {100 * vis_near / tot_near:3.0f}%, to 400 studs {100 * vis_all / tot_all:3.0f}%; height range within 150 studs: median {np.median(rise):4.1f} studs")


def big_shadow():
	sun = M["Beauty"]["Light"]["Sun"]
	az, el = np.radians(sun["Azimuth"]), np.radians(sun["Elevation"])
	dx, dy, dz = np.sin(az) * np.cos(el), -np.cos(az) * np.cos(el), np.sin(el)  # map coords: y runs south
	print("\nSun marched over the terrain from the Gate hill's east side:")
	for px, py in ((1175, 400), (1200, 380), (1230, 360), (1260, 340), (1120, 380)):
		h0 = float(zat(px, py)) + 0.5
		hit = None
		for t in np.arange(5, 2000, 2.5):
			qx, qy = px + dx * t, py + dy * t
			if float(zat(qx, qy)) > h0 + dz * t:
				hit = (qx, qy, float(zat(qx, qy)), t)
				break
		print(f"  ({px}, {py}) ground {h0 - 0.5:5.1f}: " + (f"shadowed by terrain at ({hit[0]:.0f}, {hit[1]:.0f}), height {hit[2]:.0f}, {hit[3]:.0f} studs away" if hit else "lit"))


def bridges():
	deck_end = M["Beauty"]["WaterLevel"] - 0.5 + 7.0  # stone_bridge(rise=7): the deck's ends sit at exactly the rise
	hub = next(p for p in M["Places"] if p["Icon"] == "castle")["At"]
	isl = M["Blockout"]["Island"]
	c = isl["Radius"] + isl["Moat"] / 2 + 4
	print(f"\nBridges: deck ends at height {deck_end:.1f}")
	for g in M["Beauty"]["Town"]["Gates"]:
		a = np.radians(g)
		for side, r in (("outer", c + 21), ("island", c - 21)):
			x, y = hub[0] + np.cos(a) * r, hub[1] + np.sin(a) * r
			print(f"  gate {g:3d} {side:6s} end at ({x:.0f}, {y:.0f}): ground {float(zat(x, y)):5.1f}, step up {deck_end - float(zat(x, y)):+5.1f} studs")


composition()
road_vs_grass()
trail_lines()
terrain()
big_shadow()
bridges()
