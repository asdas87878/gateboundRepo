"""A small hand-composed Land from its spec (art/lands/<land>/spec.json), system Python, no Blender. Everything is placed by hand in the spec:
terraces (polygons with cliff edges), a river with falls, graded paths, bridge decks, pads and fields, future buildings as grey boxes, fences, woods, framing trees.
Writes beside the spec: terrain.png (R,G = (h + 40) * 50, B = material; water columns hold the bed, surface = h + BED), data.json (objects for the Studio builder), plan.png, views.jpg, report.json.

  python tools/art/land_small.py art/lands/verdant_vale/spec.json
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noise2d  # noqa: E402

SPEC = os.path.abspath(sys.argv[1])
OUT = os.path.dirname(SPEC)
S = json.load(open(SPEC, encoding="utf-8"))
W, H = S["Size"]
BORDER = S["Border"]
STEP = 4
BED = 5.0
WALK = 16.0
MAX_GRADE = 0.35
ROCK_SLOPE = 0.85
MAX_CLIMB = math.tan(math.radians(52))
MAT = {"grass": 0, "sand": 1, "path": 2, "rock": 3, "worn": 4, "field": 5, "water": 7}
MAT_COLOUR = {0: (86, 168, 84), 1: (240, 222, 150), 2: (176, 150, 128), 3: (138, 142, 138), 4: (160, 190, 100), 5: (196, 176, 96), 7: (70, 215, 200)}

xs = np.arange(-BORDER, W + BORDER + 1, STEP, dtype=np.float32)
ys = np.arange(-BORDER, H + BORDER + 1, STEP, dtype=np.float32)
X, Y = np.meshgrid(xs, ys)


def ss(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def seg(px, py, a, b):
	dx, dy = b[0] - a[0], b[1] - a[1]
	t = np.clip(((px - a[0]) * dx + (py - a[1]) * dy) / max(dx * dx + dy * dy, 1e-6), 0, 1)
	return np.hypot(px - a[0] - dx * t, py - a[1] - dy * t), t


def signed_dist(poly):
	"""negative inside"""
	d = np.full(X.shape, 1e9, np.float32)
	inside = np.zeros(X.shape, bool)
	n = len(poly)
	for i in range(n):
		a, b = poly[i], poly[(i + 1) % n]
		d = np.minimum(d, seg(X, Y, a, b)[0])
		cross = ((a[1] > Y) != (b[1] > Y)) & (X < (b[0] - a[0]) * (Y - a[1]) / (b[1] - a[1] + 1e-9) + a[0])
		inside ^= cross
	return np.where(inside, -d, d)


def cell(x, y):
	return int(np.clip(round((y + BORDER) / STEP), 0, X.shape[0] - 1)), int(np.clip(round((x + BORDER) / STEP), 0, X.shape[1] - 1))


def sample_line(pts, every):
	out = []
	for a, b in zip(pts, pts[1:]):
		L = math.dist(a[:2], b[:2])
		n = max(1, int(L / every))
		out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n)]
	out.append(tuple(pts[-1][:2]))
	return out


def smooth_corners(pts, passes=3):
	"""rounds a hand-placed polyline (keeps its ends and any pinned heights' ends)"""
	p = [list(q[:2]) for q in pts]
	for _ in range(passes):
		o = [p[0]]
		for a, b in zip(p, p[1:]):
			o.append([a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25])
			o.append([a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75])
		o.append(p[-1])
		p = o
	return p


def terrain():
	Z = 22 + noise2d.fbm(X / 380, Y / 380, 1, 3) * 5 + noise2d.fbm(X / 90, Y / 90, 2, 2) * 1.2
	wob = noise2d.fbm(X / 58, Y / 58, 3, 3) * 15 + noise2d.fbm(X / 19, Y / 19, 4, 2) * 3
	for t in S["Terraces"]:
		sd = signed_dist(t["Poly"]) + wob
		top = t["Height"] + noise2d.fbm(X / 120, Y / 120, 5, 3) * 3.5
		if "Step" in t:
			# a ledge partway down: the outer cliff climbs to a shelf, the inner cliff to the top
			shelf = t["Height"] * 0.56 + noise2d.fbm(X / 80, Y / 80, 12, 2) * 2
			k = ss(0, t["Edge"], -sd)
			Z = Z * (1 - k) + np.maximum(Z, shelf) * k
			step_wob = noise2d.fbm(X / 44, Y / 44, 13, 3) * t["Step"] * 0.6
			k = ss(t["Step"], t["Step"] + t["Edge"], -sd + step_wob)
			Z = Z * (1 - k) + top * k
		else:
			k = ss(0, t["Edge"], -sd)
			Z = Z * (1 - k) + top * k
	# the mountains shutting the Land in
	# rounded corners, so the land isn't a box
	R = 620.0
	qx, qy = np.maximum(np.abs(X - W / 2) - (W / 2 - R), 0), np.maximum(np.abs(Y - H / 2) - (H / 2 - R), 0)
	edge = R - np.hypot(qx, qy) + noise2d.fbm(X / 210, Y / 210, 6, 3) * 70
	p = ss(70, -240, edge)
	Z += 300 * p**1.25 * (0.55 + 0.8 * noise2d.ridged(X / 360, Y / 360, 7, 4, 0.5, 1.7, warp=0.4))
	# pads and fields, before the river and paths
	mat = np.full(X.shape, MAT["grass"], np.uint8)
	for pad in S["Pads"]:
		if "Poly" in pad:
			sd = signed_dist(pad["Poly"])
			cx = sum(q[0] for q in pad["Poly"]) / len(pad["Poly"])
			cy = sum(q[1] for q in pad["Poly"]) / len(pad["Poly"])
		else:
			cx, cy = pad["At"]
			sd = np.hypot(X - cx, Y - cy) - pad["Radius"]
		j, k = cell(cx, cy)
		level = float(Z[j, k])
		t = ss(16, 0, sd)
		Z = Z * (1 - t) + level * t
		if pad.get("Mat"):
			mat[sd < 0] = MAT[pad["Mat"]]
	# river
	r = S["River"]
	pts = smooth_corners_keep(r)
	rd = np.full(X.shape, 1e9, np.float32)
	level = np.zeros(X.shape, np.float32)
	width = np.zeros(X.shape, np.float32)
	bank = np.zeros(X.shape, np.float32)
	for a, b in zip(pts, pts[1:]):
		d, t = seg(X, Y, a, b)
		m = d < rd
		rd[m] = d[m]
		level[m] = (a[2] + (b[2] - a[2]) * t)[m]
		width[m] = (a[3] + (b[3] - a[3]) * t)[m]
		bank[m] = (a[4] + (b[4] - a[4]) * t)[m]
	wobble = noise2d.fbm(X / 70, Y / 70, 8, 3) * 7 * np.clip(bank / 20, 0.3, 1)
	d = rd + wobble - width / 2
	shore = level + 2.5 + 7 * ss(0, bank, d)
	k = ss(bank + 26, bank * 0.8, d)
	Z = Z * (1 - k) + np.minimum(Z, shore) * k + np.minimum(0, 0) * k
	river = d < 0
	Z[river] = (level - BED)[river]
	surf = np.full(X.shape, np.nan, np.float32)
	surf[river] = level[river]
	sand = (d < bank * 0.8) & (Z < level + 5) & ~river & (level < 20)
	mat[sand] = MAT["sand"]
	return Z, surf, mat


def smooth_corners_keep(r):
	"""river points with level, width and bank, rounded except around a drop"""
	raw = [[q["At"][0], q["At"][1], q["Level"], q["Width"], q["Bank"]] for q in r]
	for _ in range(2):
		o = [raw[0]]
		for a, b in zip(raw, raw[1:]):
			if abs(a[2] - b[2]) > 5:
				o.append(b)
				continue
			o.append([a[i] * 0.75 + b[i] * 0.25 for i in range(5)])
			o.append([a[i] * 0.25 + b[i] * 0.75 for i in range(5)])
		o.append(raw[-1])
		raw = o
	return raw


def lay_paths(Z, surf, mat):
	blur = Z.copy()
	for _ in range(5):
		blur = (blur + np.roll(blur, 1, 0) + np.roll(blur, -1, 0) + np.roll(blur, 1, 1) + np.roll(blur, -1, 1)) / 5
	wmax = np.zeros(Z.shape, np.float32)
	target = np.zeros(Z.shape, np.float32)
	paved = np.zeros(Z.shape, bool)
	water = ~np.isnan(surf)
	stats = []
	lines = {}
	for p in S["Paths"]:
		raw = p["Points"]
		line = smooth_corners(raw, 2)
		ps = sample_line(line, STEP)
		h = np.array([float(blur[cell(*q)]) for q in ps])
		h = np.convolve(np.pad(h, 6, mode="edge"), np.ones(13) / 13, "valid")
		pinned = {}
		for q in raw:
			if len(q) > 2:
				i = int(np.argmin([math.dist(q[:2], e) for e in ps]))
				pinned[i] = q[2]
		g = MAX_GRADE * STEP
		for i, v in pinned.items():
			h[i] = v
		for _ in range(3):
			for i in range(1, len(h)):
				if i not in pinned:
					h[i] = np.clip(h[i], h[i - 1] - g, h[i - 1] + g)
			for i in range(len(h) - 2, -1, -1):
				if i not in pinned:
					h[i] = np.clip(h[i], h[i + 1] - g, h[i + 1] + g)
		half = p["Width"] / 2
		blend = half + 16
		rad = int(blend / STEP) + 1
		for i, (x, y) in enumerate(ps):
			j, k = cell(x, y)
			j0, j1, k0, k1 = max(j - rad, 0), j + rad + 1, max(k - rad, 0), k + rad + 1
			d = np.hypot(X[j0:j1, k0:k1] - x, Y[j0:j1, k0:k1] - y)
			t = ss(blend, half + 1, d)
			m = t > wmax[j0:j1, k0:k1]
			wmax[j0:j1, k0:k1][m] = t[m]
			target[j0:j1, k0:k1][m] = h[i] - 0.2
			paved[j0:j1, k0:k1] |= d < half
		length = STEP * (len(ps) - 1)
		stats.append({"Name": p["Name"], "Length": round(length), "Seconds": round(length / WALK), "MaxGrade": round(float(np.max(np.abs(np.diff(h))) / STEP), 2)})
		lines[p["Name"]] = list(zip(ps, h.tolist()))
	Z2 = np.where(water, Z, Z * (1 - wmax) + target * wmax)
	mat = mat.copy()
	mat[paved & ~water] = MAT["path"]
	return Z2, mat, paved, stats, lines


def inside_poly(x, y, poly):
	c = False
	n = len(poly)
	for i in range(n):
		a, b = poly[i], poly[(i + 1) % n]
		if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
			c = not c
	return c


def objects(Z, surf, paved, slope, rng):
	water = ~np.isnan(surf)
	road = paved.copy()
	for _ in range(4):
		road = road | np.roll(road, 1, 0) | np.roll(road, -1, 0) | np.roll(road, 1, 1) | np.roll(road, -1, 1)

	def g(x, y):
		j, k = cell(x, y)
		return float(Z[j, k])

	def clear(x, y, r):
		j0, k0 = cell(x - r, y - r)
		j1, k1 = cell(x + r, y + r)
		return not (road[j0 : j1 + 1, k0 : k1 + 1].any() or water[j0 : j1 + 1, k0 : k1 + 1].any())

	taken = [(*p["At"], p["Size"][0] * 0.9) for p in S["Planned"]] + [(c["At"][0], c["At"][1], 14) for c in S["Content"] if c["Kind"] != "Spot"] + [(w[0], w[1], 12) for w in S["Waystones"]]
	taken += [(sum(q[0] for q in p["Poly"]) / 4, sum(q[1] for q in p["Poly"]) / 4, 70) for p in S["Pads"] if "Poly" in p]

	def free(x, y, r):
		return all((x - a) ** 2 + (y - b) ** 2 > (r + c) ** 2 for a, b, c in taken)

	data = {"Blocks": [], "Trees": [], "Bushes": [], "Rocks": [], "Labels": [], "Waystones": []}

	def block(kind, x, y, w, h, d, yaw=0.0, base=None, lift=0.0):
		data["Blocks"].append([kind, round(x, 1), round(y, 1), round((g(x, y) if base is None else base) + lift + h / 2, 2), round(w, 1), round(h, 2), round(d, 1), round(yaw, 3)])

	for p in S["Planned"]:
		x, y = p["At"]
		w, h, d = p["Size"]
		base = g(x, y) - 1
		block("Planned", x, y, w, h, d, p["Yaw"], base=base)
		if p.get("Roof"):
			block("PlannedRoof", x, y, w + 3, h * 0.35, d + 3, p["Yaw"], base=base + h)
		data["Labels"].append({"T": "Planned: " + p["Name"], "X": x, "Y": y, "Up": h + 14, "Kind": "Planned"})
	# fences: real posts and two rails, with gaps
	for line in S["Fences"]:
		for a, b in zip(line, line[1:]):
			L = math.dist(a, b)
			n = max(1, int(L / 12))
			yaw = -math.atan2(b[1] - a[1], b[0] - a[0])
			for i in range(n):
				x0, y0 = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
				x1, y1 = a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n
				mx, my = (x0 + x1) / 2, (y0 + y1) / 2
				if not clear(mx, my, 3) or rng.random() < 0.12:
					continue
				h0, h1 = g(x0, y0), g(x1, y1)
				block("Fence", x0, y0, 1.2, 4.5, 1.2, yaw, base=h0 - 0.5)
				base = (h0 + h1) / 2
				block("Fence", mx, my, L / n, 0.6, 0.5, yaw, base=base + 2.0)
				block("Fence", mx, my, L / n, 0.6, 0.5, yaw, base=base + 3.4)
	# bridge decks: real and walkable
	for deck in S["Decks"]:
		a, b = deck["From"], deck["To"]
		L = math.dist(a, b)
		yaw = -math.atan2(b[1] - a[1], b[0] - a[0])
		n = max(5, int(L / 8))
		for i in range(n):
			f = (i + 0.5) / n
			x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
			top = deck["Level"] + deck["Arch"] * math.sin(f * math.pi)
			kind = "BridgeStone" if deck["Kind"] == "stone" else "BridgeLog"
			block(kind, x, y, L / n + 1, 3, deck["Width"], yaw, base=top - 3)
			if deck["Kind"] == "stone":
				ux, uy = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
				for side in (-1, 1):
					block(kind, x + ux * side * (deck["Width"] / 2 - 0.8), y + uy * side * (deck["Width"] / 2 - 0.8), L / n + 1, 2.6, 1.6, yaw, base=top)
		if deck["Kind"] == "stone":
			# piers, so it reads as a stone bridge from the river
			for f in (0.27, 0.73):
				x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
				block("BridgeStone", x, y, 10, deck["Level"] - 2, deck["Width"] - 1, yaw, base=2)
		data["Labels"].append({"T": deck["Name"], "X": (a[0] + b[0]) / 2, "Y": (a[1] + b[1]) / 2, "Up": 22, "Kind": "Planned"})
	# content markers
	for c in S["Content"]:
		x, y = c["At"]
		k = c["Kind"]
		if k == "Spot":
			block("FightCircle", x, y, c["Radius"] * 2, 0.4, c["Radius"] * 2)
			for p in range(c["Packs"]):
				a = p * math.tau / c["Packs"] + rng.uniform(-0.3, 0.3)
				d = rng.uniform(0.35, 0.7) * c["Radius"]
				px, py = x + math.cos(a) * d, y + math.sin(a) * d
				for i in range(3):
					b, e = i * math.tau / 3 + rng.uniform(-0.5, 0.5), rng.uniform(4, 9)
					block("Enemy", px + math.cos(b) * e, py + math.sin(b) * e, 3, 5, 3)
			prefix = "Farm: "
		elif k == "Material":
			for i in range(6):
				a, d = i * 2.4, 4 + i * 4
				block("Material", x + math.cos(a) * d, y + math.sin(a) * d, 4, rng.uniform(4, 9), 4, rng.uniform(0, 3))
			prefix = "Material: "
		elif k == "Rescue":
			block("Rescue", x, y, 4, 6, 4)
			prefix = "Rescue: "
		elif k == "FieldBoss":
			block("Boss", x, y, 22, 26, 34)
			block("FightCircle", x, y, S["BossRadius"] * 2, 0.4, S["BossRadius"] * 2)
			prefix = "Boss: "
		elif k == "Secret":
			block("Secret", x, y, 7, 5, 5)
			prefix = "Secret: "
		elif k == "Drop":
			block("Secret", x, y, 16, 0.6, 8, 0)
			prefix = ""
		data["Labels"].append({"T": prefix + c["Name"], "X": x, "Y": y, "Up": 20, "Kind": k})
	for w in S["Waystones"]:
		data["Waystones"].append([w[0], w[1], round(g(*w), 1)])
	# trees: hand-placed framing trees first (full look), then the woods by spacing, with clearings
	for x, y, s in S["FrameTrees"]:
		data["Trees"].append([x, y, round(g(x, y) - 0.5, 1), s, round(rng.uniform(0, 6.28), 2), 1])
		taken.append((x, y, 20))
	clearings = noise2d.fbm(X / 95, Y / 95, 11, 3)
	for wood in S["Woods"]:
		sp = wood["Spacing"]
		for gx in np.arange(0, W, sp):
			for gy in np.arange(0, H, sp):
				x = float(gx + rng.uniform(-sp * 0.42, sp * 0.42))
				y = float(gy + rng.uniform(-sp * 0.42, sp * 0.42))
				if not inside_poly(x, y, wood["Poly"]):
					continue
				j, k = cell(x, y)
				if clearings[j, k] < wood["Clear"] - 0.42 or slope[j, k] > 0.6 or not clear(x, y, 9) or not free(x, y, 14):
					continue
				s = rng.choice((0.7, 0.85, 1.0, 1.0, 1.15, 1.35))
				data["Trees"].append([round(x, 1), round(y, 1), round(g(x, y) - 0.5, 1), s, round(rng.uniform(0, 6.28), 2), 0])
				if rng.random() < 0.45:
					a, d = rng.uniform(0, 6.28), rng.uniform(9, 16)
					bx, by = x + math.cos(a) * d, y + math.sin(a) * d
					if clear(bx, by, 4):
						data["Bushes"].append([round(bx, 1), round(by, 1), round(g(bx, by) - 0.5, 1), round(rng.uniform(0.8, 1.3), 2), round(rng.uniform(0, 6.28), 2)])
	for x, y in S["Bushes"]:
		data["Bushes"].append([x, y, round(g(x, y) - 0.5, 1), round(rng.uniform(0.9, 1.4), 2), round(rng.uniform(0, 6.28), 2)])
	# rocks: only at chosen edges, with gaps. Big walls where a cliff faces a view; foot stones at their base; stones on the river's bends
	cliff = slope > 1.1
	near_cliff = cliff.copy()
	for _ in range(3):
		near_cliff = near_cliff | np.roll(near_cliff, 1, 0) | np.roll(near_cliff, -1, 0) | np.roll(near_cliff, 1, 1) | np.roll(near_cliff, -1, 1)
	used = []
	for t in S["Terraces"]:
		if t["Name"] not in ("Arrival bluff", "High Wood", "Falls plateau", "Orchard spur", "Pasture knoll"):
			continue
		poly = t["Poly"] + [t["Poly"][0]]
		for x, y in sample_line(poly, 30):
			if not (0 <= x <= W and 0 <= y <= H) or rng.random() < 0.3:
				continue
			# slide to the steep face nearby
			best, bd = None, 1e9
			for _ in range(16):
				a, d = rng.uniform(0, 6.28), rng.uniform(0, 34)
				qx, qy = x + math.cos(a) * d, y + math.sin(a) * d
				j, k = cell(qx, qy)
				if cliff[j, k] and d < bd:
					best, bd = (qx, qy), d
			if not best or not clear(best[0], best[1], 12) or any((best[0] - a) ** 2 + (best[1] - b) ** 2 < 26**2 for a, b in used):
				continue
			used.append(best)
			j, k = cell(*best)
			j0, j1, k0, k1 = max(j - 5, 0), j + 6, max(k - 5, 0), k + 6
			low = float(Z[j0:j1, k0:k1].min())
			up = float(Z[j0:j1, k0:k1].max())
			name = rng.choice(("WallMid", "WallWide", "WallLong", "CliffWide", "WallStep")) if up - low > 22 else rng.choice(("BlockChunk", "Block", "BoulderWide", "WallStep"))
			face = math.atan2(*np.array(np.gradient(Z[j0:j1, k0:k1], STEP))[:, 5, 5])
			data["Rocks"].append([name, round(best[0], 1), round(best[1], 1), round(low - 1.5, 1), round(rng.uniform(0.9, 1.3), 2), round(face + rng.uniform(-0.35, 0.35), 2)])
	river_line = smooth_corners_keep(S["River"])
	for a, b in zip(river_line, river_line[1:]):
		if a[2] > 20 or rng.random() < 0.72:
			continue
		ux, uy = -(b[1] - a[1]), b[0] - a[0]
		L = math.hypot(ux, uy) or 1
		side = rng.choice((-1, 1))
		off = a[3] / 2 + rng.uniform(0, 10)
		cx, cy = a[0] + ux / L * off * side, a[1] + uy / L * off * side
		for i in range(rng.choice((1, 3, 3, 5))):
			x, y = cx + rng.uniform(-11, 11), cy + rng.uniform(-11, 11)
			if 0 <= x <= W and 0 <= y <= H and clear(x, y, 2) or water[cell(x, y)]:
				data["Rocks"].append([rng.choice(("BoulderSmall", "Slab", "SlabSmall", "Stone", "SlabBroken")), round(x, 1), round(y, 1), round(g(x, y) - 0.8, 1), round(rng.uniform(0.8, 1.5), 2), round(rng.uniform(0, 6.28), 2)])
	# the landmark seen from arrival: an old dead giant tree on the boss hill, kept loaded from anywhere
	bx, by = S["Landmark"]
	base = g(bx, by) - 3
	block("Landmark", bx, by, 30, 150, 30, 0.2, base=base)
	for i, (w, up, lean) in enumerate(((110, 140, 0.25), (80, 165, 1.4), (70, 120, 2.5), (58, 150, 3.7))):
		ca, sa = math.cos(lean), math.sin(lean)
		block("Landmark", bx + ca * w * 0.45, by + sa * w * 0.45, w, 9, 9, -lean, base=base + up)
	data["Labels"].append({"T": "Landmark: the Old Stump, where Old Tusk lives", "X": bx, "Y": by, "Up": 175, "Kind": "Planned"})
	for b in S["Beats"]:
		data["Labels"].append({"T": b["Name"], "X": b["At"][0], "Y": b["At"][1], "Up": 46, "Big": True})
	data["Arrival"] = S["Arrival"]
	data["Offset"] = S["Offset"]
	data["Border"] = BORDER
	data["Bed"] = BED
	return data


def object_height(data, Z, colour):
	Hh = Z.copy()
	C = colour.copy()
	KIND = {"Planned": (190, 188, 180), "PlannedRoof": (150, 90, 75), "Fence": (130, 95, 65), "BridgeStone": (170, 168, 162), "BridgeLog": (130, 95, 65), "Landmark": (84, 66, 54)}

	def stamp(x, y, rx, ry, top, col):
		j0, k0 = cell(x - rx, y - ry)
		j1, k1 = cell(x + rx, y + ry)
		sl = Hh[j0 : j1 + 1, k0 : k1 + 1]
		m = top > sl
		sl[m] = top
		C[j0 : j1 + 1, k0 : k1 + 1][m] = col

	for b in data["Blocks"]:
		if b[0] in KIND:
			stamp(b[1], b[2], b[4] / 2, b[6] / 2, b[3] + b[5] / 2, KIND[b[0]])
	for t in data["Trees"]:
		s = t[3]
		stamp(t[0], t[1], 11 * s, 11 * s, t[2] + 42 * s, (52, 150, 96))
		stamp(t[0], t[1], 6 * s, 6 * s, t[2] + 54 * s, (72, 178, 104))
	for r in data["Rocks"]:
		stamp(r[1], r[2], 7 * r[4], 7 * r[4], r[3] + 12 * r[4], (170, 172, 176))
	return Hh, C


def shade(Hh, colour):
	gy, gx = np.gradient(Hh, STEP)
	n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
	n /= np.linalg.norm(n, axis=-1, keepdims=True)
	light = np.array([-0.5, -0.55, 0.67])
	return np.clip(colour * (0.5 + 0.7 * np.clip((n * light).sum(-1), 0, 1))[..., None], 0, 255)


def font(size):
	for f in ("arialbd.ttf", "arial.ttf"):
		try:
			return ImageFont.truetype(f, size)
		except OSError:
			pass
	return ImageFont.load_default()


def plan_image(sh, data, stats):
	scale = 1.0
	im = Image.fromarray(sh.astype(np.uint8)).resize((int(sh.shape[1] * 2 * scale), int(sh.shape[0] * 2 * scale)), Image.LANCZOS)
	d = ImageDraw.Draw(im)
	k = im.width / (W + 2 * BORDER)

	def P(x, y):
		return (x + BORDER) * k, (y + BORDER) * k

	col = {"Spot": (255, 70, 60), "Material": (235, 165, 40), "Rescue": (230, 80, 200), "FieldBoss": (255, 150, 130), "Secret": (250, 225, 90), "Drop": (255, 255, 255)}
	for p in S["Paths"]:
		line = smooth_corners(p["Points"], 2)
		d.line([P(*q) for q in line], fill=(255, 240, 200), width=2)
	for c in S["Content"]:
		x, y = P(*c["At"])
		if c["Kind"] == "Spot":
			r = c["Radius"] * k
			d.ellipse((x - r, y - r, x + r, y + r), outline=col["Spot"], width=3)
		else:
			d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=col[c["Kind"]], outline=(0, 0, 0), width=2)
		d.text((x + 11, y), c["Name"], fill=col[c["Kind"]], font=font(16), anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
	for p in S["Planned"]:
		x, y = P(*p["At"])
		d.text((x, y - 12), p["Name"], fill=(235, 235, 235), font=font(14), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
	for b in S["Beats"]:
		x, y = P(*b["At"])
		n = b["Name"].split(" ")[0]
		d.ellipse((x - 15, y - 15, x + 15, y + 15), fill=(255, 255, 255), outline=(0, 0, 0), width=2)
		d.text((x, y), n, fill=(0, 0, 0), font=font(20), anchor="mm")
	for w in S["Waystones"]:
		x, y = P(*w)
		d.rectangle((x - 5, y - 5, x + 5, y + 5), fill=(95, 200, 225), outline=(0, 0, 0))
	x0, y0 = P(W - 480, H + 90)
	d.line((x0, y0, x0 + 480 * k, y0), fill=(255, 255, 255), width=4)
	d.text((x0, y0 - 6), "30 seconds' walk", fill=(255, 255, 255), font=font(18), anchor="lb", stroke_width=2, stroke_fill=(0, 0, 0))
	im.save(os.path.join(OUT, "plan.png"))


def eye_view(view, Hh, colour, sw=800, sh=450):
	fx, fy = view["From"]
	tx, ty = view["To"]
	j, k = cell(fx, fy)
	eye = float(Hh[j, k]) + view.get("Up", 7)
	yaw = math.atan2(ty - fy, tx - fx)
	focal = (sh / 2) / math.tan(math.radians(35))
	horizon = sh * 0.56
	img = np.zeros((sh, sw, 3), np.float32)
	for r in range(sh):
		t = r / sh
		img[r, :] = np.array((40, 150, 225)) * (1 - t) + np.array((190, 225, 235)) * t
	ybuf = np.full(sw, sh, np.int32)
	u = (np.arange(sw) - sw / 2) / focal
	dirx = np.cos(yaw) - u * np.sin(yaw)
	diry = np.sin(yaw) + u * np.cos(yaw)
	dist, ds = 3.0, 1.5
	haze = np.array((150, 225, 215), np.float32)
	while dist < 2400:
		px, py = fx + dirx * dist, fy + diry * dist
		ks = np.clip(((px + BORDER) / STEP).astype(np.int32), 0, Hh.shape[1] - 1)
		js = np.clip(((py + BORDER) / STEP).astype(np.int32), 0, Hh.shape[0] - 1)
		ytop = np.clip((horizon - (Hh[js, ks] - eye) / dist * focal).astype(np.int32), 0, sh)
		fog = 1 - math.exp(-dist / 1900)
		for c in np.where(ytop < ybuf)[0]:
			img[ytop[c] : ybuf[c], c] = colour[js[c], ks[c]] * (1 - fog) + haze * fog
			ybuf[c] = ytop[c]
		dist += ds
		ds = min(ds * 1.008, 8)
	return np.clip(img, 0, 255).astype(np.uint8)


def views(Hh, colour):
	vs = S["Views"]
	cols, sw, sh = 2, 800, 450
	sheet = Image.new("RGB", (sw * cols, sh * math.ceil(len(vs) / cols)))
	d = ImageDraw.Draw(sheet)
	for i, v in enumerate(vs):
		x, y = (i % cols) * sw, (i // cols) * sh
		sheet.paste(Image.fromarray(eye_view(v, Hh, colour, sw, sh)), (x, y))
		d.text((x + 10, y + 8), v["Name"], fill=(255, 255, 255), font=font(22), stroke_width=2, stroke_fill=(0, 0, 0))
	sheet.save(os.path.join(OUT, "views.jpg"), quality=88)


def reach(Z, surf, decks=True):
	ground = np.where(np.isnan(surf), Z, surf).astype(np.float32)
	# bridge decks count as ground
	for deck in S["Decks"] if decks else []:
		for x, y in sample_line([deck["From"], deck["To"]], 2):
			for ox in range(-4, 5, 2):
				for oy in range(-4, 5, 2):
					j, k = cell(x + ox, y + oy)
					ground[j, k] = deck["Level"]
	n, m = ground.shape
	ids = np.arange(n * m).reshape(n, m)
	gy, gx = np.gradient(ground, STEP)
	steep = np.hypot(gx, gy) > MAX_CLIMB
	froms, tos = [], []
	for a, b, ga, gb, sa, sb in (
		(ids[:, :-1], ids[:, 1:], ground[:, :-1], ground[:, 1:], steep[:, :-1], steep[:, 1:]),
		(ids[:-1, :], ids[1:, :], ground[:-1, :], ground[1:, :], steep[:-1, :], steep[1:, :]),
	):
		ok = (gb <= ga) | ~sb
		froms.append(a[ok]), tos.append(b[ok])
		ok = (ga <= gb) | ~sa
		froms.append(b[ok]), tos.append(a[ok])
	g = csr_matrix((np.ones(sum(len(f) for f in froms), np.bool_), (np.concatenate(froms), np.concatenate(tos))), shape=(n * m, n * m))

	def from_point(p):
		j, k = cell(*p)
		o = breadth_first_order(g, int(ids[j, k]), directed=True, return_predecessors=False)
		seen = np.zeros(n * m, bool)
		seen[o] = True
		return seen.reshape(n, m)

	seen = from_point(S["Arrival"])
	names = {c["Name"]: c["At"] for c in S["Content"]}
	out = {}
	for name in S["ReachCheck"]:
		j, k = cell(*names[name])
		out[name] = bool(seen[max(j - 3, 0) : j + 4, max(k - 3, 0) : k + 4].any())
	inside = (X >= 0) & (X <= W) & (Y >= 0) & (Y <= H)
	result = {"Reachable": out, "ShareOfLand": round(float((seen & inside).sum() / inside.sum()), 3)}
	if not decks and out.get("High Wood shrine"):
		# the shrine must need the log bridge: if not, the route shows where the cliffs leak
		j, k = cell(*S["Arrival"])
		_, pred = breadth_first_order(g, int(ids[j, k]), directed=True, return_predecessors=True)
		tj, tk = cell(*names["High Wood shrine"])
		q, path = int(ids[tj, tk]), []
		while q >= 0 and q != int(ids[j, k]):
			path.append(q)
			q = int(pred[q])
		result["LeakRoute"] = [[int(xs[v % m]), int(ys[v // m]), round(float(ground[v // m, v % m]))] for v in path[::-1][::24]]
	return result


def main():
	rng = random.Random(7)
	Z, surf, mat = terrain()
	Z, mat, paved, stats, lines = lay_paths(Z, surf, mat)
	water = ~np.isnan(surf)
	gy, gx = np.gradient(Z, STEP)
	slope = np.hypot(gx, gy)
	mat[(slope > ROCK_SLOPE) & ~paved & ~water] = MAT["rock"]
	mat[water] = MAT["water"]
	data = objects(Z, surf, paved, slope, rng)
	enc = np.clip(np.round((Z + 40) * 50), 0, 65535).astype(np.uint32)
	img = np.zeros((*Z.shape, 4), np.uint8)
	img[..., 0], img[..., 1], img[..., 2], img[..., 3] = enc >> 8, enc & 255, mat, 255
	Image.fromarray(img, "RGBA").save(os.path.join(OUT, "terrain.png"))
	json.dump(data, open(os.path.join(OUT, "data.json"), "w"), separators=(",", ":"))
	base = np.zeros((*Z.shape, 3), np.float32)
	for m, c in MAT_COLOUR.items():
		base[mat == m] = c
	Hh, C = object_height(data, Z, base.astype(np.uint8))
	sh = shade(Hh, C.astype(np.float32))
	plan_image(sh, data, stats)
	views(Hh, sh)
	route = ["Arrival lane", "Pasture road", "Camp road", "Thornwood road", "Falls climb", "Boss road"]
	secs = {s["Name"]: s for s in stats}
	report = {
		"Pixels": list(Z.shape), "Heights": [round(float(Z.min()), 1), round(float(Z.max()), 1)],
		"Blocks": len(data["Blocks"]), "Trees": len(data["Trees"]), "Bushes": len(data["Bushes"]), "Rocks": len(data["Rocks"]),
		"EnemyBlocks": sum(1 for b in data["Blocks"] if b[0] == "Enemy"),
		"Paths": stats,
		"WalkArrivalToBossSeconds": round(sum(secs[n]["Seconds"] for n in route) + 8),
		"Reach": reach(Z, surf),
		"ReachWithoutBridges": reach(Z, surf, False),
		"DataKB": round(os.path.getsize(os.path.join(OUT, "data.json")) / 1024),
	}
	json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
	print(json.dumps({k: report[k] for k in report if k != "Paths"}, indent=0))
	print([(s["Name"], s["Seconds"], s["MaxGrade"]) for s in stats])


main()
