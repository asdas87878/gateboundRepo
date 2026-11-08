"""Builds a large Land from its spec (art/lands/land1_v2/spec.json), system Python, no Blender: big landforms, a lake and falling river, graded roads with bridges,
placed sites, enemy camps, groves and rocks. Writes into the spec's folder:
  terrain_<i>_<j>.png  height + material tiles, at most 1024 px a side, one pixel per 4-stud column (R,G = (h + 40) * 50, B = material; water columns hold the bed, surface = h + 6)
  objects.png          every block as 4 pixels (see write_objects)
  tiles.json, labels.json, report.json, plan.png, views.jpg

  python tools/art/land_v2.py art/lands/land1_v2/spec.json
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noise2d  # noqa: E402

SPEC = os.path.abspath(sys.argv[1])
OUT = os.path.dirname(SPEC)
S = json.load(open(SPEC, encoding="utf-8"))
W, H = S["Size"]
BORDER = S["Border"]
STEP = 4
WALK = 16.0
BED = 6.0
MAX_GRADE = 0.3
ROCK_SLOPE = 0.85
MATS = {"grass": 0, "dark": 1, "dry": 2, "pale": 3, "rock": 4, "sand": 5, "path": 6, "water": 7, "town": 8}
MAT_COLOUR = {0: (112, 158, 86), 1: (58, 104, 80), 2: (176, 150, 98), 3: (186, 182, 162), 4: (128, 126, 122), 5: (214, 200, 150), 6: (168, 142, 104), 7: (70, 130, 165), 8: (160, 158, 150)}
KINDS = ["Stone", "Roof", "Wood", "Enemy", "Boss", "Ink", "Rock", "TreeMeadow", "TreeHill", "TreeDark", "TreeDry", "Glow", "FightCircle", "Bridge", "Waystone", "Crop", "Giant", "Material", "Rescue", "Secret", "Dungeon", "Lock", "Plot", "ArchOpen"]
KIND_COLOUR = {
	"Stone": (190, 188, 180), "Roof": (120, 124, 136), "Wood": (130, 112, 92), "Enemy": (190, 60, 55), "Boss": (120, 30, 30), "Ink": (35, 32, 42), "Rock": (118, 116, 112),
	"TreeMeadow": (96, 140, 84), "TreeHill": (88, 124, 92), "TreeDark": (46, 78, 62), "TreeDry": (120, 118, 84), "Glow": (160, 235, 255), "FightCircle": (190, 60, 55),
	"Bridge": (130, 112, 92), "Waystone": (95, 180, 200), "Crop": (190, 170, 90), "Giant": (70, 58, 48),
	"Material": (235, 165, 40), "Rescue": (230, 80, 200), "Secret": (250, 225, 90), "Dungeon": (110, 70, 170), "Lock": (235, 50, 50), "Plot": (170, 160, 130), "ArchOpen": (120, 235, 255),
}
PREFIX = {"Spot": "Farm: ", "Material": "Material: ", "Rescue": "Rescue: ", "FieldBoss": "Boss: ", "Secret": "Secret: ", "Dungeon": "Dungeon: ", "Lock": "LOCKED: "}
MAX_CLIMB = math.tan(math.radians(52))  # the slope a character can walk up; the blockout's Humanoid.MaxSlopeAngle matches


def smoothstep(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def seg_param(X, Y, a, b):
	dx, dy = b[0] - a[0], b[1] - a[1]
	t = np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / max(dx * dx + dy * dy, 1e-6), 0, 1)
	return np.hypot(X - a[0] - dx * t, Y - a[1] - dy * t), t


def line_dist(X, Y, pts):
	best = np.full(X.shape, 1e9, np.float32)
	for a, b in zip(pts, pts[1:]):
		best = np.minimum(best, seg_param(X, Y, a, b)[0])
	return best


xs = np.arange(-BORDER, W + BORDER + 1, STEP, dtype=np.float32)
ys = np.arange(-BORDER, H + BORDER + 1, STEP, dtype=np.float32)
X, Y = np.meshgrid(xs, ys)
# bend coordinates so landforms don't have perfect outlines
WX = X + noise2d.fbm(X / 420, Y / 420, 21, 3) * 130 + noise2d.fbm(X / 110, Y / 110, 22, 2) * 22
WY = Y + noise2d.fbm(X / 420, Y / 420, 23, 3) * 130 + noise2d.fbm(X / 110, Y / 110, 24, 2) * 22


def ellipse(z_at, r, x=WX, y=WY):
	return np.hypot((x - z_at[0]) / r[0], (y - z_at[1]) / r[1])


def heights():
	Z = 12 + noise2d.fbm(X / 900, Y / 900, 1, 3) * 10
	for f in S["Forms"]:
		k = f["Kind"]
		if k == "plateau":
			Z += f["Height"] * smoothstep(1.0, 1 - f["Edge"], ellipse(f["At"], f["Radius"]))
		elif k == "cone":
			Z += f["Height"] * np.clip(1 - ellipse(f["At"], f["Radius"]), 0, 1) ** f.get("Power", 1.2)
		elif k == "ridge":
			d = line_dist(WX, WY, f["Line"])
			Z += f["Height"] * smoothstep(f["Width"], f["Width"] * f["Edge"], d)
		elif k == "flat":
			d = np.hypot(WX - f["At"][0], WY - f["At"][1]) / 1.0
			t = smoothstep(f["Radius"] + f["Slope"], f["Radius"], d)
			Z = Z * (1 - t) + f["Level"] * t
		elif k == "wall":
			# a cliff band on a line, for routes that must really be shut; roads cut through it, and each crossing has a Lock
			d = line_dist(X, Y, f["Line"]) + noise2d.fbm(X / 70, Y / 70, 26, 2) * 6
			Z += f["Height"] * smoothstep(f["Width"], f["Width"] * 0.55, d)
		elif k == "canyon":
			d = line_dist(X, Y, f["Line"])
			t = smoothstep(f["Width"] / 2 + f["Slope"], f["Width"] / 2, d)
			Z = Z * (1 - t) + np.minimum(Z, f["Level"]) * t
	zone = np.full(X.shape, -1, np.int8)
	best = np.zeros(X.shape, np.float32)
	for n, z in enumerate(S["Zones"]):
		d = ellipse(z["At"], z["Radius"])
		w = smoothstep(1.2, 0.8, d)
		amp, scale, kind = z["Noise"]
		if kind == "ridged":
			Z += (noise2d.ridged(X / scale, Y / scale, 30 + n, 4, 0.5, 1.8, warp=0.4) - 0.3) * amp * w
		else:
			Z += noise2d.fbm(X / scale, Y / scale, 30 + n, 4) * amp * w
		if "Terrace" in z:
			step, amount = z["Terrace"]
			q = Z / step
			fr = q - np.floor(q)
			ter = (np.floor(q) + smoothstep(0.72, 1.0, fr)) * step
			Z = Z * (1 - amount * w) + ter * amount * w
		better = (w > best) & (w > 0.2)
		zone[better] = n
		best = np.maximum(best, w)
	# the mountains shutting the Land in
	r = S["Rim"]
	edge = np.minimum.reduce([WX, W - WX, WY, H - WY])
	p = smoothstep(r["From"], -r["To"], edge)
	m = noise2d.ridged(X / r["Scale"], Y / r["Scale"], r["Seed"], 5, 0.5, 1.6, warp=0.45)
	big = noise2d.fbm(X / 2600, Y / 2600, r["Seed"] + 40, 2) * 0.5 + 0.5
	Z += r["Wall"] * p ** 1.2 * (r["Low"] + r["Peak"] * m) * (0.75 + 0.5 * big)
	Z += noise2d.ridged(X / 320, Y / 320, r["Seed"] + 70, 4, 0.5, 2.0, warp=0.4) * r["Foothills"] * smoothstep(r["FootIn"], 60, edge) * smoothstep(-200, 60, edge)
	# river, with its falls
	surf = np.full(X.shape, np.nan, np.float32)
	pts = S["River"]["Points"]
	rd = np.full(X.shape, 1e9, np.float32)
	level = np.zeros(X.shape, np.float32)
	for a, b in zip(pts, pts[1:]):
		d, t = seg_param(X, Y, a, b)
		closer = d < rd
		rd[closer] = d[closer]
		level[closer] = (a[2] + (b[2] - a[2]) * t)[closer]
	hw = S["River"]["Width"] / 2
	wob = noise2d.fbm(X / 160, Y / 160, 50, 3) * hw * 0.35
	bank = smoothstep(hw + 70, hw + 4, rd + wob)
	Z = Z * (1 - bank) + np.minimum(Z, level + 3) * bank
	river = rd + wob < hw
	Z[river] = level[river] - BED
	surf[river] = level[river]
	# the lake, and Brightwater's rock
	hub = S["Hub"]
	dl = ellipse(hub["At"], hub["Lake"])
	shore = smoothstep(1.28, 1.0, dl)
	Z = Z * (1 - shore) + (1.5) * shore
	lake = dl < 1
	Z[lake] = -BED
	surf[lake] = 0
	di = np.hypot(X - hub["At"][0], Y - hub["At"][1])
	isl = di < hub["Island"]
	cl = smoothstep(hub["Island"], hub["Island"] - 26, di)
	Z[isl] = (-BED * (1 - cl) + hub["Height"] * cl)[isl]
	Z += 34 * smoothstep(120, 40, np.hypot(X - hub["Keep"][0], Y - hub["Keep"][1])) * isl
	surf[isl & (Z >= 0.5)] = np.nan
	return Z, zone, surf


def sample(path, every):
	out = []
	for a, b in zip(path, path[1:]):
		L = math.dist(a, b)
		n = max(1, int(L / every))
		out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n)]
	out.append(tuple(path[-1]))
	return out


def road_points(r):
	if "Points" in r:
		return [tuple(p) for p in r["Points"]]
	s = r["Spiral"]
	cx, cy = s["At"]
	pts = [tuple(s["From"])]
	n = 40
	for i in range(n + 1):
		f = i / n
		a = math.radians(s["StartDeg"]) + f * s["Turns"] * math.tau
		rad = s["R0"] + (s["R1"] - s["R0"]) * f
		pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
	pts.append(tuple(s["End"]))
	return pts


def cell(x, y):
	return int(np.clip(round((y + BORDER) / STEP), 0, X.shape[0] - 1)), int(np.clip(round((x + BORDER) / STEP), 0, X.shape[1] - 1))


def lay_roads(Z, surf):
	"""each road's height profile is limited to MAX_GRADE, then stamped in: cuttings going through hills, embankments over dips. Over water it stays as a bridge."""
	wmax = np.zeros(Z.shape, np.float32)
	target = np.zeros(Z.shape, np.float32)
	paved = np.zeros(Z.shape, bool)
	water = ~np.isnan(surf)
	bridges, stats, profiles = [], [], []
	smooth = Z.copy()
	for _ in range(6):
		smooth = (smooth + np.roll(smooth, 1, 0) + np.roll(smooth, -1, 0) + np.roll(smooth, 1, 1) + np.roll(smooth, -1, 1)) / 5
	for r in S["Roads"]:
		pts = road_points(r)
		ps = sample(pts, STEP)
		raw = np.zeros(len(ps))
		wet = np.zeros(len(ps), bool)
		for i, (x, y) in enumerate(ps):
			j, k = cell(x, y)
			wet[i] = water[j, k]
			raw[i] = surf[j, k] + 3 if wet[i] else smooth[j, k]
		h = np.convolve(np.pad(raw, 8, mode="edge"), np.ones(17) / 17, "valid")
		g = MAX_GRADE * STEP
		for _ in range(2):
			for i in range(1, len(h)):
				h[i] = np.clip(h[i], h[i - 1] - g, h[i - 1] + g)
			for i in range(len(h) - 2, -1, -1):
				h[i] = np.clip(h[i], h[i + 1] - g, h[i + 1] + g)
		half = r["Width"] / 2
		blend = half + 24
		rad = int(blend / STEP) + 1
		for i, (x, y) in enumerate(ps):
			j, k = cell(x, y)
			if wet[i]:
				continue
			j0, j1 = max(j - rad, 0), min(j + rad + 1, Z.shape[0])
			k0, k1 = max(k - rad, 0), min(k + rad + 1, Z.shape[1])
			d = np.hypot(X[j0:j1, k0:k1] - x, Y[j0:j1, k0:k1] - y)
			t = smoothstep(blend, half + 1, d)
			m = t > wmax[j0:j1, k0:k1]
			wmax[j0:j1, k0:k1][m] = t[m]
			target[j0:j1, k0:k1][m] = h[i] - 0.3
			paved[j0:j1, k0:k1] |= d < half
		# bridges over each wet run
		i = 0
		while i < len(ps):
			if wet[i]:
				e = i
				while e + 1 < len(ps) and wet[e + 1]:
					e += 1
				a, b = max(i - 3, 0), min(e + 3, len(ps) - 1)
				dx, dy = ps[b][0] - ps[a][0], ps[b][1] - ps[a][1]
				steps = [(ps[q][0], ps[q][1], float(h[q])) for q in range(a, b + 1, 2)]
				bridges.append({"Road": r["Name"], "Yaw": math.atan2(dy, dx), "Steps": steps, "Width": r["Width"] + 2})
				i = e + 1
			else:
				i += 1
		length = STEP * (len(ps) - 1)
		stats.append({"Name": r["Name"], "Length": round(length), "Seconds": round(length / WALK), "MaxGrade": round(float(np.max(np.abs(np.diff(h))) / STEP), 2), "Climb": round(float(h.max() - h.min()))})
		profiles.append((r["Name"], ps, h))
	Z2 = np.where(water, Z, Z * (1 - wmax) + target * wmax)
	paved &= ~water
	return Z2, paved, bridges, stats, profiles


class Objects:
	def __init__(self):
		self.items = []
		self.Z = None
		self.road = None  # no block may stand on a road, unless it clears a walker's head
		self.persist = 0  # landmarks stay loaded however far away the player is
		self.dropped = 0

	def ground(self, x, y):
		j, k = cell(x, y)
		return float(self.Z[j, k])

	def box(self, kind, x, y, w, h, d, yaw=0.0, lift=0.0, base=None):
		g = self.ground(x, y) if base is None else base
		if kind not in ("Bridge", "Glow", "FightCircle", "Waystone", "Lock") and lift < 9 and base is None:
			ex, ey = (w + d) / 4, (w + d) / 4
			j0, k0 = cell(x - ex, y - ey)
			j1, k1 = cell(x + ex, y + ey)
			if self.road[j0 : j1 + 1, k0 : k1 + 1].any():
				self.dropped += 1
				return
		self.items.append((KINDS.index(kind), x, y, g + lift + h / 2, w, h, d, yaw, self.persist))


def build_site(o, p, rng):
	x, y = p["At"]
	k = p["Kind"]
	n = p.get("Size", 6)
	if k == "circle":
		for i in range(10):
			a = i * math.tau / 10
			o.box("Stone", x + math.cos(a) * 30, y + math.sin(a) * 30, 5, 16, 4, -a)
		o.box("Glow", x, y, 6, 1, 6)
	elif k == "lookout":
		o.box("Wood", x, y, 22, 2, 22, lift=4)
		for a in (0.8, 2.4, 3.9, 5.5):
			o.box("Wood", x + math.cos(a) * 12, y + math.sin(a) * 12, 2, 8, 2)
	elif k == "hamlet":
		for _ in range(n):
			a, d = rng.uniform(0, math.tau), rng.uniform(16, 22 + n * 6)
			hx, hy, hh = x + math.cos(a) * d, y + math.sin(a) * d, rng.uniform(9, 14)
			yaw = rng.uniform(0, 3.14)
			o.box("Stone", hx, hy, rng.uniform(12, 20), hh, rng.uniform(10, 15), yaw)
			o.box("Roof", hx, hy, rng.uniform(14, 22), 5, rng.uniform(12, 17), yaw, hh)
		o.box("Stone", x, y, 7, 4, 7)
	elif k == "inn":
		o.box("Stone", x, y, 34, 18, 24)
		o.box("Roof", x, y, 38, 7, 28, 0, 18)
		o.box("Stone", x + 34, y + 12, 16, 11, 14)
		o.box("Wood", x - 26, y - 14, 3, 18, 3)
	elif k == "windmill":
		o.box("Stone", x, y, 18, 42, 18)
		o.box("Roof", x, y, 20, 7, 20, 0, 42)
		for a in (0.3, 1.87, 3.44, 5.01):
			o.items.append((KINDS.index("Wood"), x + math.cos(a) * 20, y + 11, o.ground(x, y) + 40 + math.sin(a) * 20, 40 * abs(math.cos(a)) + 3, 40 * abs(math.sin(a)) + 3, 2, 0, o.persist))
	elif k == "monoliths":
		for i in range(n):
			a, d = rng.uniform(0, math.tau), rng.uniform(10, 40 + n * 8)
			o.box("Rock", x + math.cos(a) * d, y + math.sin(a) * d, rng.uniform(6, 11), rng.uniform(18, 44), rng.uniform(4, 8), rng.uniform(0, 3.14), -2)
	elif k == "farms":
		for i in range(7):
			fx, fy = x + (i % 3 - 1) * 170 + rng.uniform(-20, 20), y + (i // 3 - 1) * 110 + rng.uniform(-20, 20)
			o.box("Crop", fx, fy, rng.uniform(100, 150), 2.5, rng.uniform(60, 90), rng.uniform(-0.3, 0.3))
		o.box("Wood", x + 10, y - 15, 30, 16, 20)
		o.box("Roof", x + 10, y - 15, 33, 6, 23, 0, 16)
	elif k == "gatehouse":
		yaw = p.get("Yaw", 0.0)
		cx, sx = math.cos(yaw), math.sin(yaw)
		o.box("Stone", x - 34 * cx, y - 34 * sx, 22, 62, 22, -yaw)
		o.box("Stone", x + 34 * cx, y + 34 * sx, 22, 74, 22, -yaw)
		o.box("Stone", x, y, 50, 10, 12, -yaw, 44)
		for i in range(5):
			u, v = (i - 2) * 46 + rng.uniform(-6, 6), rng.uniform(40, 80)
			o.box("Stone", x + u * cx - v * sx, y + u * sx + v * cx, 26, rng.uniform(6, 20), 4, -yaw + rng.uniform(-0.3, 0.3))
	elif k == "ruins":
		for i in range(n):
			a, d = rng.uniform(0, math.tau), rng.uniform(8, 20 + n * 7)
			o.box("Stone", x + math.cos(a) * d, y + math.sin(a) * d, rng.uniform(12, 30), rng.uniform(6, 26), 4, rng.uniform(0, 3.14), -1)
		o.box("Stone", x, y, 9, 34, 9, 0, -1)
	elif k == "quarry":
		for i in range(14):
			o.box("Stone", x + rng.uniform(-120, 120), y + rng.uniform(-90, 90), rng.uniform(12, 30), rng.uniform(5, 14), rng.uniform(8, 20), rng.uniform(0, 3.14), -1)
		o.box("Wood", x, y - 40, 5, 30, 5)
		o.box("Wood", x + 14, y - 40, 34, 3, 3, 0, 28)
	elif k == "foundry":
		o.box("Stone", x, y, 70, 30, 50)
		o.box("Ink", x, y + 26, 18, 18, 4)
		for a in (0.4, 2.0, 3.6, 5.2):
			o.box("Stone", x + math.cos(a) * 70, y + math.sin(a) * 55, 12, 46, 12)
		o.box("Glow", x, y, 10, 2, 10, 0, 30)
	elif k == "campsite":
		for i in range(5):
			a = i * math.tau / 5
			o.box("Wood", x + math.cos(a) * 16, y + math.sin(a) * 16, 8, 5, 6, -a)
		o.box("Glow", x, y, 3, 1, 3)
	elif k == "elder":
		# the giant tree above Rootdeep: a landmark over the whole wood
		base = o.ground(x, y)
		o.box("Giant", x, y, 70, 200, 70, base=base - 4)
		for i in range(6):
			a = i * math.tau / 6
			o.box("Giant", x + math.cos(a) * 52, y + math.sin(a) * 52, 22, 60, 22, a, base=base - 4)
		for i, (w, hh, up) in enumerate(((240, 40, 195), (190, 50, 230), (120, 60, 275))):
			o.box("TreeDark", x, y, w, hh, w, i * 0.5, base=base + up)
		o.box("Ink", x, y + 37, 24, 22, 8, base=base)
		o.box("Glow", x, y + 42, 18, 16, 3, base=base)
	elif k == "mere":
		for i in range(9):
			a = i * math.tau / 9
			o.box("Glow", x + math.cos(a) * 60, y + math.sin(a) * 45, 2, 5, 2, lift=1)
		o.box("Rock", x, y, 30, 12, 20)
	elif k == "ring":
		for i in range(14):
			a = i * math.tau / 14
			o.box("Glow", x + math.cos(a) * 44, y + math.sin(a) * 44, 8, 3 + i % 3, 8, 0, 3)
			o.box("Giant", x + math.cos(a) * 44, y + math.sin(a) * 44, 3, 3, 3)
	elif k == "shrine":
		o.box("Stone", x, y, 16, 20, 16)
		o.box("Glow", x, y, 4, 4, 4, 0, 20)
	elif k == "ropebridge":
		o.box("Bridge", x, y, 8, 1.5, 700, 0.1, base=172)
		for d in (-345, 345):
			o.box("Wood", x + d * math.sin(0.1), y + d * math.cos(0.1), 12, 26, 12, 0, 0, base=165)
	elif k == "fort":
		for i in range(8):
			a = i * math.tau / 8
			o.box("Wood", x + math.cos(a) * 130, y + math.sin(a) * 130, 75, 18, 5, -a + math.pi / 2)
		for i in range(4):
			a = i * math.tau / 4 + 0.4
			o.box("Wood", x + math.cos(a) * 130, y + math.sin(a) * 130, 14, 44, 14)
		for i in range(12):
			a, d = rng.uniform(0, math.tau), rng.uniform(20, 100)
			o.box("Wood", x + math.cos(a) * d, y + math.sin(a) * d, rng.uniform(10, 20), rng.uniform(6, 13), rng.uniform(8, 15), a)
	elif k == "towers":
		for i in range(5):
			o.box("Wood", x + rng.uniform(-170, 170), y + (i - 2) * 150, 12, rng.uniform(36, 58), 12)
	elif k == "bell":
		o.box("Stone", x, y, 24, 90, 24)
		o.box("Roof", x, y, 28, 14, 28, 0, 90)
	elif k == "label":
		pass
	elif k == "boss":
		o.box("Boss", x, y, 18, 26, 18)
		o.box("FightCircle", x, y, 170, 0.4, 170)
	elif k == "gate":
		base = o.ground(x, y)
		o.box("Stone", x - 72, y, 42, 170, 42, base=base - 2)
		o.box("Stone", x + 72, y, 48, 200, 48, base=base - 2)
		o.box("Stone", x, y, 200, 32, 34, 0, 150, base=base)
		o.box("Glow", x, y, 9, 2000, 9, base=base + 182)
		for i in range(9):
			a = i * math.tau / 9
			o.box("Stone", x + math.cos(a) * 225, y + 90 + math.sin(a) * 200, 22, rng.uniform(30, 70), 22)
	elif k == "town":
		hub = S["Hub"]
		kx, ky = hub["Keep"]
		base = o.ground(kx, ky)
		o.box("Stone", kx, ky, 70, 120, 70, base=base - 2)
		o.box("Roof", kx, ky, 76, 12, 76, base=base + 118)
		o.box("Roof", kx, ky, 18, 70, 18, base=base + 130)
		for i in range(4):
			a = i * math.pi / 2 + 0.4
			o.box("Stone", kx + math.cos(a) * 54, ky + math.sin(a) * 54, 20, 86, 20, base=base - 2)
		count = 0
		while count < 130:
			a, d = rng.uniform(0, math.tau), rng.uniform(30, 208)
			hx, hy = x + math.cos(a) * d, y + math.sin(a) * d
			if math.hypot(hx - kx, hy - ky) < 80 or abs(hx - x) < 12 or abs(hy - y) < 12:
				continue
			hh, yaw = rng.uniform(9, 17), rng.choice((0, 1.57)) + rng.uniform(-0.2, 0.2)
			o.box("Stone", hx, hy, rng.uniform(12, 22), hh, rng.uniform(11, 17), yaw)
			o.box("Roof", hx, hy, rng.uniform(14, 24), 6, rng.uniform(13, 19), yaw, hh)
			count += 1
		o.box("Stone", x, y + 16, 22, 4, 22)
		for i in range(40):
			a = i * math.tau / 40
			if min(abs(math.degrees(a) - d) for d in (0, 90, 180, 270, 360)) < 5:
				continue
			o.box("Stone", x + math.cos(a) * 222, y + math.sin(a) * 222, 36, 16, 5, -a - math.pi / 2)


def road_direction(x, y):
	best, angle = 1e18, 0.0
	for r in S["Roads"]:
		pts = road_points(r)
		for a, b in zip(pts, pts[1:]):
			d = float(seg_param(np.float32(x), np.float32(y), a, b)[0])
			if d < best:
				best, angle = d, math.atan2(b[1] - a[1], b[0] - a[0])
	return angle


def build_content(o, rng):
	"""each zone's parts, as readable markers: farming spots, material sources, rescues, field bosses, secrets, the dungeon door, locked routes"""
	for c in S.get("Content", []):
		k, (x, y) = c["Kind"], c["At"]
		if k == "Spot":
			r = c["Radius"]
			o.box("FightCircle", x, y, r * 2, 0.4, r * 2)
			for p in range(c["Packs"]):
				a = p * math.tau / c["Packs"] + rng.uniform(-0.3, 0.3)
				d = rng.uniform(0.45, 0.85) * r
				px, py = x + math.cos(a) * d, y + math.sin(a) * d
				for i in range(4):
					b, e = i * math.tau / 4 + rng.uniform(-0.5, 0.5), rng.uniform(5, 12)
					o.box("Enemy", px + math.cos(b) * e, py + math.sin(b) * e, 3, 5, 3)
		elif k == "Material":
			for i in range(7):
				a, d = i * 2.4, 6 + i * 6
				o.box("Material", x + math.cos(a) * d, y + math.sin(a) * d, 6, rng.uniform(6, 14), 6, rng.uniform(0, 3))
		elif k == "Rescue":
			o.box("Rescue", x, y, 4, 6, 4)
			for a in (0.8, 2.4, 3.9, 5.5):
				o.box("Wood", x + math.cos(a) * 9, y + math.sin(a) * 9, 1.5, 11, 1.5)
			o.box("Wood", x, y, 16, 1.5, 16, 0, 11)
		elif k == "FieldBoss":
			o.box("Boss", x, y, 18, 26, 18)
			o.box("FightCircle", x, y, 170, 0.4, 170)
		elif k == "Secret":
			o.box("Secret", x, y, 7, 5, 5)
			o.box("Glow", x, y, 1, 30, 1, 0, 5)
		elif k == "Dungeon":
			o.box("Dungeon", x - 22, y, 12, 36, 12)
			o.box("Dungeon", x + 22, y, 12, 36, 12)
			o.box("Dungeon", x, y, 56, 10, 12, 0, 36)
			o.box("Ink", x, y, 32, 36, 3)
		elif k == "Lock":
			o.box("Lock", x, y, c["Width"], 34, 4, -(road_direction(x, y) + math.pi / 2), -4)


def build_home(o, rng):
	"""the player's plot: Gate Court in the middle of the star, one arch per Land, and the building plots"""
	h = S["Home"]
	hx, hy = h["At"]
	base = h["Level"]
	cx, cy = h["Court"]
	o.box("Stone", cx, cy, 120, 1, 120, base=base)
	for arch in h["Arches"]:
		a = math.radians(arch["Dir"])
		ax, ay = cx + math.cos(a) * 56, cy + math.sin(a) * 56
		ux, uy = -math.sin(a), math.cos(a)
		o.box("Stone", ax - ux * 15, ay - uy * 15, 7, 30, 7, -a, base=base)
		o.box("Stone", ax + ux * 15, ay + uy * 15, 7, 30, 7, -a, base=base)
		o.box("Stone", ax, ay, 7, 6, 38, -a, base=base + 30)
		o.box("ArchOpen" if arch.get("Open") else "Ink", ax, ay, 2, 28, 22, -a, base=base + 1)
	for name, dx, dy in h["Plots"]:
		px, py = hx + dx, hy + dy
		o.box("Plot", px, py, 54, 1, 54, base=base)
		# a ruin waiting to be rebuilt
		for i in range(3):
			a, d = rng.uniform(0, math.tau), rng.uniform(6, 18)
			o.box("Stone", px + math.cos(a) * d, py + math.sin(a) * d, rng.uniform(8, 18), rng.uniform(3, 8), 3, rng.uniform(0, 3), base=base)
	sx, sy = h["Spawn"]
	for i in range(5):
		a = i * math.tau / 5
		o.box("Wood", sx + math.cos(a) * 11, sy + math.sin(a) * 11, 6, 2, 3, -a, base=base)
	o.box("Glow", sx, sy, 3, 1, 3, base=base)


def scatter(o, Z, zone, paved, surf, slope, rng):
	"""camps, then rocks and groves. Camps gather in patches near roads, so the map has busy stretches and calm ones."""
	places = [p["At"] for p in S["Places"]] + S["Waystones"] + [c["At"] for c in S.get("Content", [])]
	water = ~np.isnan(surf)
	road_d = np.ones(Z.shape, bool)
	road_near = paved.copy()
	# widen the road mask (no scipy dependency needed: repeated rolls)
	for _ in range(8):
		road_near = road_near | np.roll(road_near, 1, 0) | np.roll(road_near, -1, 0) | np.roll(road_near, 1, 1) | np.roll(road_near, -1, 1)
	cluster = noise2d.fbm(X / 340, Y / 340, 60, 3)
	camps, counts = [], {}
	for n, z in enumerate(S["Zones"]):
		js, ks = np.where((zone == n) & ~water & ~road_near & (slope < 0.45) & (cluster > -0.12))
		order = np.random.RandomState(100 + n).permutation(len(js))
		placed = 0
		for q in order:
			x, y = float(xs[ks[q]]), float(ys[js[q]])
			if placed >= z["Camps"]:
				break
			if any((x - a) ** 2 + (y - b) ** 2 < 70**2 for a, b in places):
				continue
			if any((x - a) ** 2 + (y - b) ** 2 < 110**2 for a, b, _ in camps):
				continue
			camps.append((x, y, n))
			placed += 1
		counts[z["Name"]] = placed
	for x, y, n in camps:
		o.box("FightCircle", x, y, 56, 0.4, 56)
		for i in range(4):
			a, d = i * math.tau / 4 + rng.uniform(-0.5, 0.5), rng.uniform(6, 14)
			o.box("Enemy", x + math.cos(a) * d, y + math.sin(a) * d, 3, 5, 3)
	# boulders and groves
	groves = noise2d.fbm(X / 260, Y / 260, 61, 4)
	glades = noise2d.fbm(X / 180, Y / 180, 62, 3)
	tree_count = rock_count = 0
	gx = np.arange(0, W, 24.0)
	gy = np.arange(0, H, 24.0)
	for x0 in gx:
		for y0 in gy:
			x, y = x0 + rng.uniform(-11, 11), y0 + rng.uniform(-11, 11)
			j, k = cell(x, y)
			n = zone[j, k]
			if n < 0 or water[j, k] or road_near[j, k] or slope[j, k] > 0.75:
				continue
			z = S["Zones"][n]
			if any((x - a) ** 2 + (y - b) ** 2 < 42**2 for a, b in places):
				continue
			kind, dens = z["Tree"]
			gv = groves[j, k]
			p = dens * 1.2 if dens > 0.5 and glades[j, k] > -0.28 else (0 if dens > 0.5 else (dens * 4 if gv > 0.3 else dens * 0.15))
			if rng.random() < p:
				s = rng.uniform(0.7, 1.3)
				if dens > 0.5 and rng.random() < 0.05:
					o.box("Giant", x, y, 13, 80, 13, 0, -1)
					o.box(kind, x, y, 46, 34, 46, rng.uniform(0, 3), 72)
				else:
					o.box(kind, x, y, 8 * s, 34 * s, 8 * s, rng.uniform(0, 3), -1)
				tree_count += 1
			elif rng.random() < z["Rock"] * 0.16:
				s = rng.uniform(0.6, 1) ** 2 * 26 + 3
				o.box("Rock", x, y, s * rng.uniform(0.8, 1.4), s * rng.uniform(0.5, 1.0), s, rng.uniform(0, 3), -s * 0.18)
				rock_count += 1
	return camps, counts, tree_count, rock_count


def write_objects(o):
	"""4 pixels an object: [x hi, x lo, kind] [y hi, y lo, yaw] [z hi, z lo, persist] [w, h, d]. x, y, z: (value + 1024) * 2. Yaw: 0-255 over half a turn. Sizes: (byte / 16) ^ 2 studs, so 254 at most; bigger things are built from several blocks."""
	rows = int(math.ceil(math.sqrt(len(o.items) * 4)))
	rows += -rows % 4
	img = np.zeros((rows, rows, 4), np.uint8)
	img[..., 3] = 255

	def enc(v):
		i = int(np.clip(round((v + 1024) * 2), 0, 65535))  # half-stud positions, up to 31 744 studs
		return i >> 8, i & 255

	def size(v):
		return int(np.clip(round(math.sqrt(max(v, 0)) * 16), 1, 255))

	flat = img.reshape(-1, 4)
	for i, (kind, x, y, z, w, h, d, yaw, persist) in enumerate(o.items):
		flat[i * 4][:3] = (*enc(x), kind)
		flat[i * 4 + 1][:3] = (*enc(y), int(round((yaw % math.pi) / math.pi * 255)))
		flat[i * 4 + 2][:3] = (*enc(z), persist)
		flat[i * 4 + 3][:3] = (size(w), size(h), size(d))
	Image.fromarray(img, "RGBA").save(os.path.join(OUT, "objects.png"))
	return rows


def object_grid(o, Z):
	"""a rough height and colour map of the blocks, for the clay views"""
	H2 = Z.copy()
	C = np.zeros((*Z.shape, 3), np.uint8)
	has = np.zeros(Z.shape, bool)
	for kind, x, y, z, w, h, d, yaw, _ in o.items:
		name = KINDS[kind]
		if name in ("FightCircle",) or h > 1000:
			continue
		ca, sa = abs(math.cos(yaw)), abs(math.sin(yaw))
		ex, ey = (w * ca + d * sa) / 2, (w * sa + d * ca) / 2
		j0, k0 = cell(x - ex, y - ey)
		j1, k1 = cell(x + ex, y + ey)
		top = z + h / 2
		sl = H2[j0 : j1 + 1, k0 : k1 + 1]
		m = top > sl
		sl[m] = top
		C[j0 : j1 + 1, k0 : k1 + 1][m] = KIND_COLOUR[name]
		has[j0 : j1 + 1, k0 : k1 + 1][m] = True
	return H2, C, has


def shaded(Hh, colour):
	gy, gx = np.gradient(Hh, STEP)
	n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
	n /= np.linalg.norm(n, axis=-1, keepdims=True)
	light = np.array([-0.5, -0.55, 0.67])
	return np.clip(colour * (0.48 + 0.72 * np.clip((n * light).sum(-1), 0, 1))[..., None], 0, 255)


def font(size):
	for f in ("arialbd.ttf", "arial.ttf"):
		try:
			return ImageFont.truetype(f, size)
		except OSError:
			pass
	return ImageFont.load_default()


def plan(shade, profiles, camps):
	scale = 3
	im = Image.fromarray(shade.astype(np.uint8)).resize((shade.shape[1] // (scale - 1) * (2 if "Content" in S else 1), shade.shape[0] // (scale - 1) * (2 if "Content" in S else 1)), Image.LANCZOS)
	d = ImageDraw.Draw(im)
	k = im.width / (W + 2 * BORDER)

	def P(x, y):
		return ((x + BORDER) * k, (y + BORDER) * k)

	for n, z in enumerate(S["Zones"]):
		x, y = P(*z["At"])
		d.text((x, y), f"{z['Name']}\nLv {z['Levels']}", fill=(255, 255, 255), font=font(30), anchor="mm", align="center", stroke_width=3, stroke_fill=(0, 0, 0))
	for p in S["Places"]:
		x, y = P(*p["At"])
		c = (255, 150, 130) if p["Kind"] == "boss" else (255, 235, 170)
		d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=c, outline=(0, 0, 0))
		if "Content" not in S:
			d.text((x + 7, y), p.get("Boss", p["Name"]), fill=c, font=font(15), anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
	for x, y, _ in camps:
		a, b = P(x, y)
		d.ellipse((a - 2, b - 2, a + 2, b + 2), fill=(200, 50, 45))
	for w in S["Waystones"]:
		a, b = P(*w)
		d.rectangle((a - 3, b - 3, a + 3, b + 3), fill=(95, 200, 225), outline=(0, 0, 0))
	marks = {"Spot": (255, 70, 60), "Material": KIND_COLOUR["Material"], "Rescue": KIND_COLOUR["Rescue"], "FieldBoss": (255, 150, 130), "Secret": KIND_COLOUR["Secret"], "Dungeon": (190, 150, 255), "Lock": (255, 40, 40)}
	for c in S.get("Content", []):
		x, y = P(*c["At"])
		col = marks[c["Kind"]]
		if c["Kind"] == "Spot":
			r = c["Radius"] * k
			d.ellipse((x - r, y - r, x + r, y + r), outline=col, width=3)
		elif c["Kind"] == "Lock":
			d.rectangle((x - 9, y - 9, x + 9, y + 9), fill=col, outline=(255, 255, 255), width=2)
		else:
			d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=col, outline=(0, 0, 0), width=2)
		d.text((x + 11, y), c["Name"].split(" (")[0], fill=col, font=font(15), anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
	# 1 minute of walking
	x0, y0 = P(W - 1300, H + 150)
	d.line((x0, y0, x0 + 960 * k, y0), fill=(255, 255, 255), width=4)
	d.text((x0, y0 - 6), "1 minute's walk (960 studs)", fill=(255, 255, 255), font=font(18), anchor="lb", stroke_width=2, stroke_fill=(0, 0, 0))
	im.save(os.path.join(OUT, "plan.png"))


def eye_view(view, Hh, colour, sw=800, sh=450):
	"""voxel-space renderer over the height map, Roblox's FieldOfView 70 (vertical), clay only"""
	fx, fy = view["From"]
	tx, ty = view["To"]
	j, k = cell(fx, fy)
	eye = float(Hh[j, k]) + view.get("Up", 6)
	yaw = math.atan2(ty - fy, tx - fx)
	focal = (sh / 2) / math.tan(math.radians(35))
	j2, k2 = cell(tx, ty)
	pitch = 0.0
	horizon = sh * 0.56
	img = np.zeros((sh, sw, 3), np.float32)
	for r in range(sh):
		t = r / sh
		img[r, :] = np.array((120, 170, 215)) * (1 - t) + np.array((205, 222, 228)) * t
	ybuf = np.full(sw, sh, np.int32)
	u = (np.arange(sw) - sw / 2) / focal
	dirx = np.cos(yaw) - u * np.sin(yaw)
	diry = np.sin(yaw) + u * np.cos(yaw)
	dist, ds = 3.0, 2.0
	haze = np.array((192, 212, 224), np.float32)
	while dist < 9000:
		px, py = fx + dirx * dist, fy + diry * dist
		ks = np.clip(((px + BORDER) / STEP).astype(np.int32), 0, Hh.shape[1] - 1)
		js = np.clip(((py + BORDER) / STEP).astype(np.int32), 0, Hh.shape[0] - 1)
		hh = Hh[js, ks]
		ytop = (horizon - (hh - eye) / dist * focal).astype(np.int32)
		ytop = np.clip(ytop, 0, sh)
		fog = 1 - math.exp(-dist / 6500)
		for c in np.where(ytop < ybuf)[0]:
			img[ytop[c] : ybuf[c], c] = colour[js[c], ks[c]] * (1 - fog) + haze * fog
			ybuf[c] = ytop[c]
		dist += ds
		ds = min(ds * 1.006, 12)
	return np.clip(img, 0, 255).astype(np.uint8)


def views(Hh, colour):
	vs = S["Views"]
	cols = 2
	rows = math.ceil(len(vs) / cols)
	sw, sh = 800, 450
	sheet = Image.new("RGB", (sw * cols, sh * rows))
	d = ImageDraw.Draw(sheet)
	for i, v in enumerate(vs):
		im = Image.fromarray(eye_view(v, Hh, colour, sw, sh))
		x, y = (i % cols) * sw, (i // cols) * sh
		sheet.paste(im, (x, y))
		d.text((x + 10, y + 8), v["Name"], fill=(255, 255, 255), font=font(22), stroke_width=2, stroke_fill=(0, 0, 0))
	sheet.save(os.path.join(OUT, "views.jpg"), quality=88)


def reachability(Z, surf):
	"""can a character really get there? A flood from the start over the 4-stud grid: uphill onto a surface steeper than MAX_CLIMB is blocked, downhill never does, water can be swum, and shut Locks block.
	Returns, per progression stage, how much is reachable and which content items aren't where the spec says."""
	from scipy.sparse import csr_matrix
	from scipy.sparse.csgraph import breadth_first_order

	ground = np.where(np.isnan(surf), Z, surf).astype(np.float32)
	n, m = ground.shape
	ids = np.arange(n * m).reshape(n, m)
	# Humanoid.MaxSlopeAngle looks at the surface, not the walking direction, so a cliff can't be crept up at an angle: moving uphill onto a steep cell is blocked.
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
	froms, tos = np.concatenate(froms), np.concatenate(tos)
	locks = {c["Name"]: c for c in S["Content"] if c["Kind"] == "Lock"}
	sj, sk = cell(*S["Story"][0][1:])
	stages, leaks = [], []
	first = {c["Name"]: None for c in S["Content"] if c["Kind"] != "Lock"}
	inside = (X >= 0) & (X <= W) & (Y >= 0) & (Y <= H)
	for si, stage in enumerate(S["Progression"]):
		blocked = np.zeros(n * m, bool)
		for name, c in locks.items():
			if name not in stage["Open"]:
				blocked |= (np.hypot(X - c["At"][0], Y - c["At"][1]) < c["Radius"]).ravel()
		keep = ~blocked[froms] & ~blocked[tos]
		g = csr_matrix((np.ones(int(keep.sum()), np.bool_), (froms[keep], tos[keep])), shape=(n * m, n * m))
		order, pred = breadth_first_order(g, int(ids[sj, sk]), directed=True, return_predecessors=True)
		wanted = [c for c in S["Content"] if c["Kind"] != "Lock" and c.get("Stage") is not None and c["Stage"] > si]
		for c in wanted:
			j, k = cell(*c["At"])
			if pred[ids[j, k]] >= 0:
				# how a too-early item is reached: the route's corner points, to find a leak in the walls
				q, path = int(ids[j, k]), []
				while q >= 0 and q != int(ids[sj, sk]):
					path.append(q)
					q = int(pred[q])
				path = path[::-1][::60]
				leaks.append({"Stage": si, "Item": c["Name"], "Route": [[int(xs[v % m]), int(ys[v // m])] for v in path]})
				break
		seen = np.zeros(n * m, bool)
		seen[order] = True
		seen = seen.reshape(n, m)
		for c in S["Content"]:
			if c["Kind"] != "Lock" and first[c["Name"]] is None:
				j, k = cell(*c["At"])
				if seen[max(j - 3, 0) : j + 4, max(k - 3, 0) : k + 4].any():
					first[c["Name"]] = si
		stages.append({"Name": stage["Name"], "ShareOfMap": round(float((seen & inside).sum() / inside.sum()), 3)})
		Image.fromarray((seen * 255).astype(np.uint8)).resize((m // 3, n // 3)).save(os.path.join(OUT, f"reach_{si}.png"))
	wrong = {c["Name"]: {"Expected": c["Stage"], "Actual": first[c["Name"]]} for c in S["Content"] if c["Kind"] != "Lock" and first[c["Name"]] != c["Stage"]}
	return {"Stages": stages, "WrongStage": wrong, "Leaks": leaks}


def main():
	rng = random.Random(11)
	Z, zone, surf = heights()
	Z, paved, bridges, road_stats, profiles = lay_roads(Z, surf)
	water = ~np.isnan(surf)
	gy, gx = np.gradient(Z, STEP)
	slope = np.hypot(gx, gy)
	mat = np.zeros(Z.shape, np.uint8)
	for n, z in enumerate(S["Zones"]):
		mat[zone == n] = z["Mat"]
	mat[(zone == -1)] = 0
	mat[slope > ROCK_SLOPE] = MATS["rock"]
	hub = S["Hub"]
	near_water = (ellipse(hub["At"], hub["Lake"]) < 1.14) & (Z < 4)
	mat[near_water] = MATS["sand"]
	mat[(np.hypot(X - hub["At"][0], Y - hub["At"][1]) < hub["Island"]) & ~water] = MATS["town"]
	mat[paved] = MATS["path"]
	mat[water] = MATS["water"]

	o = Objects()
	o.Z = Z
	o.road = paved | np.roll(paved, 1, 0) | np.roll(paved, -1, 0) | np.roll(paved, 1, 1) | np.roll(paved, -1, 1)
	for p in S["Places"]:
		o.persist = 1 if p["Kind"] in ("gate", "elder", "town", "bell", "windmill") else 0
		build_site(o, p, rng)
	o.persist = 0
	build_content(o, rng)
	if "Home" in S:
		build_home(o, rng)
	camps, camp_counts, trees, rocks = scatter(o, Z, zone, paved, surf, slope, rng)
	for w in S["Waystones"]:
		o.box("Waystone", w[0], w[1], 6, 16, 6)
	for b in bridges:  # short steps, each a walkable rise, following the road's own grade
		for x, y, top in b["Steps"]:
			o.box("Bridge", x, y, 9, 3, b["Width"], -b["Yaw"], base=top - 3)

	# tiles
	enc = np.clip(np.round((Z + 40) * 50), 0, 65535).astype(np.uint32)
	img = np.zeros((*Z.shape, 4), np.uint8)
	img[..., 0], img[..., 1], img[..., 2], img[..., 3] = enc >> 8, enc & 255, mat, 255
	TILE = 1024
	tiles = []
	for jt, j0 in enumerate(range(0, Z.shape[0], TILE)):
		for it, i0 in enumerate(range(0, Z.shape[1], TILE)):
			name = f"terrain_{it}_{jt}.png"
			Image.fromarray(img[j0 : j0 + TILE, i0 : i0 + TILE], "RGBA").save(os.path.join(OUT, name))
			tiles.append({"File": name, "I0": i0, "J0": j0, "W": int(min(TILE, Z.shape[1] - i0)), "H": int(min(TILE, Z.shape[0] - j0))})
	rows = write_objects(o)
	json.dump({"Tiles": tiles, "Border": BORDER, "Step": STEP, "Objects": len(o.items), "ObjectRows": rows, "Kinds": KINDS}, open(os.path.join(OUT, "tiles.json"), "w"), indent=1)
	labels = [{"T": f"{z['Name']}  Lv {z['Levels']}", "X": z["At"][0], "Y": z["At"][1], "Up": 90, "Big": True} for z in S["Zones"]]
	labels += [{"T": p.get("Boss", p["Name"]), "X": p["At"][0], "Y": p["At"][1], "Up": 44} for p in S["Places"]]
	for c in S.get("Content", []):
		labels.append({"T": PREFIX[c["Kind"]] + c["Name"], "X": c["At"][0], "Y": c["At"][1], "Up": 30, "Kind": c["Kind"]})
	if "Home" in S:
		h = S["Home"]
		for name, dx, dy in h["Plots"]:
			labels.append({"T": "Plot: " + name, "X": h["At"][0] + dx, "Y": h["At"][1] + dy, "Up": 22, "Kind": "Plot"})
		for arch in h["Arches"]:
			a = math.radians(arch["Dir"])
			labels.append({"T": arch["Name"], "X": h["Court"][0] + math.cos(a) * 56, "Y": h["Court"][1] + math.sin(a) * 56, "Up": 44, "Kind": "Plot"})
	json.dump(labels, open(os.path.join(OUT, "labels.json"), "w"), indent=0)

	# images
	base = np.zeros((*Z.shape, 3), np.float32)
	for m, c in MAT_COLOUR.items():
		base[mat == m] = c
	high = smoothstep(240, 420, Z)[..., None]
	base = base * (1 - high) + np.array((205, 205, 212)) * high
	Hh, C, has = object_grid(o, Z)
	base[has] = C[has]
	shade = shaded(Hh, base)
	plan(shade, profiles, camps)
	views(Hh, shade)

	reach = reachability(Z, surf) if "Progression" in S else None

	# measurements
	report = {"BlocksDroppedOffRoads": o.dropped, "Map": [W, H], "Columns": list(Z.shape), "Heights": [round(float(Z.min()), 1), round(float(Z.max()), 1)], "Objects": len(o.items), "Trees": trees, "Rocks": rocks, "Camps": camp_counts, "CampsTotal": len(camps), "Bridges": len(bridges), "Roads": road_stats}

	def ray_clear(a, b, eye=6.0, target=None):
		ja, ka = cell(*a)
		ha = float(Z[ja, ka]) + eye
		jb, kb = cell(*b)
		hb = float(Z[jb, kb]) + (target if target is not None else eye)
		n = int(math.dist(a, b) / 12)
		for i in range(1, n):
			f = i / n
			j, k = cell(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
			if Z[j, k] > ha + (hb - ha) * f:
				return False
		return True

	gate = S["Gate"]["At"]
	report["GateSeenFrom"] = {p["Name"]: ray_clear(p["At"], gate, target=200) for p in S["Places"] if p["Kind"] != "gate"}
	# the longest stretch of road with nothing beside it (a site, or a camp, within 180 studs)
	sights = [tuple(p["At"]) for p in S["Places"]] + [(c[0], c[1]) for c in camps]
	sights_a = np.array(sights)
	gaps = {}
	for name, ps, h in profiles:
		ps_a = np.array(ps)[::8]
		near = np.min(np.hypot(ps_a[:, None, 0] - sights_a[:, 0], ps_a[:, None, 1] - sights_a[:, 1]), 1) < 180
		best = run = 0
		for v in near:
			run = 0 if v else run + 1
			best = max(best, run)
		gaps[name] = round(best * 32 / WALK)
	report["QuietestStretchSeconds"] = gaps
	# story route: straight-line-free lengths along road graph
	nodes = {}
	for name, ps, h in profiles:
		pts = [(round(p[0] / 8), round(p[1] / 8)) for p in ps[::2]]
		for a, b in zip(pts, pts[1:]):
			nodes.setdefault(a, {})[b] = math.dist(a, b) * 8
			nodes.setdefault(b, {})[a] = math.dist(a, b) * 8
	for a in list(nodes):  # join road ends that meet, and the hub's roads across town
		for dx in range(-2, 3):
			for dy in range(-2, 3):
				b = (a[0] + dx, a[1] + dy)
				if b in nodes and b != a:
					nodes[a][b] = math.dist(a, b) * 8
	hx, hy = hub["At"]
	hub_nodes = [n for n in nodes if math.hypot(n[0] * 8 - hx, n[1] * 8 - hy) < 300]
	for a in hub_nodes:
		for b in hub_nodes:
			if a != b:
				nodes[a][b] = math.dist(a, b) * 8

	def route(a, b):
		import heapq

		sa = min(nodes, key=lambda n: (n[0] * 8 - a[0]) ** 2 + (n[1] * 8 - a[1]) ** 2)
		sb = min(nodes, key=lambda n: (n[0] * 8 - b[0]) ** 2 + (n[1] * 8 - b[1]) ** 2)
		dist = {sa: 0.0}
		q = [(0.0, sa)]
		while q:
			d, u = heapq.heappop(q)
			if u == sb:
				return d
			if d > dist.get(u, 1e18):
				continue
			for v, w in nodes[u].items():
				if d + w < dist.get(v, 1e18):
					dist[v] = d + w
					heapq.heappush(q, (d + w, v))
		return float("inf")

	story = []
	total = 0
	st = S["Story"]
	for (na, ax, ay), (nb, bx, by) in zip(st, st[1:]):
		d = route((ax, ay), (bx, by))
		total += d
		story.append({"From": na, "To": nb, "Seconds": round(d / WALK)})
	report["Story"] = story
	report["StoryMinutes"] = round(total / WALK / 60, 1)
	start = st[0][1:]
	report["WalkFromStartToZoneSeconds"] = {}
	for z in S["Zones"]:
		report["WalkFromStartToZoneSeconds"][z["Name"]] = round(route(start, z["At"]) / WALK)
	if reach:
		report["Progression"] = reach
		parts = {}
		for z_i, z in enumerate(S["Zones"]):
			kinds = [c["Kind"] for c in S["Content"] if c["Zone"] == z_i]
			parts[z["Name"]] = {k: kinds.count(k) for k in ("Spot", "Material", "Rescue", "FieldBoss", "Secret", "Dungeon", "Lock")}
		report["ZoneParts"] = parts
		report["EnemyBlocks"] = sum(1 for it in o.items if KINDS[it[0]] == "Enemy")
		far = {}
		for c in S["Content"]:
			far[c["Name"]] = round(min(math.dist(c["At"], w) for w in S["Waystones"]) / WALK)
		report["SecondsToNearestWaystone"] = dict(sorted(far.items(), key=lambda kv: -kv[1])[:8])
		ground = {}
		for c in S["Content"]:
			j, k = cell(*c["At"])
			ground[c["Name"]] = {"H": round(float(Z[j, k])), "Slope": round(float(slope[j, k]), 2), "Water": bool(water[j, k])}
		report["ContentGround"] = ground
		report["BadGround"] = [n for n, g in ground.items() if g["Water"] or g["Slope"] > 0.6]
	json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
	print(json.dumps(report, indent=0))


main()
