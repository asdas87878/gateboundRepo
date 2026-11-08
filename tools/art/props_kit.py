"""Small props kit (docs/style/art-style.md), system Python: barrels, crates, a farm cart and signposts on one painted 1024 sheet.
Paint comes from the approved fence painter (paint_strip in tools/art/fence_kit.py, loaded without running its main), so wood matches the fence.
Every part is checked: closed, consistently wound and positive volume, because Roblox hides back faces.
Origin of each prop: ground centre; the foot sinks below y=0. +z is the front. Studs; the player is 5.2 tall.

  python tools/art/props_kit.py art/kit/props [--look crisp|soft|none]   parts, Props_Color_Raw.png, Props_Color.png (after the crisp pass), OBJs, kit.json
  python tools/art/props_kit.py art/kit/props --sheet    only the comparison sheet from the Blender renders
"""
import copy
import json
import math
import os
import sys
from contextlib import contextmanager

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, rotate

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/props")
FENCE_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fence_kit.py")


def load_painter():
	argv, sys.argv = sys.argv, [FENCE_PY, OUT]
	src = open(FENCE_PY, encoding="utf-8").read()
	ns = {"__name__": "fence_painter", "__file__": FENCE_PY}
	exec(compile(src[: src.rindex("main()")], FENCE_PY, "exec"), ns)
	sys.argv = argv
	return ns


T = 50  # texels per stud, as the fence
CRISP_LOOK = sys.argv[sys.argv.index("--look") + 1] if "--look" in sys.argv else "soft"  # the user's pick; crisp, soft or none
CRISP_STRENGTH = 1.0
SHEET = 1024
IRON = {"BASE": (98, 86, 96), "LIGHT": (103, 91, 101), "WARM": (102, 88, 95), "DUSK": (84, 74, 90), "COOL": (88, 84, 104), "GRAIN": (70, 60, 76)}
PANEL = {"BASE": (106, 73, 58), "LIGHT": (113, 79, 62), "WARM": (112, 76, 58), "DUSK": (96, 67, 56), "COOL": (99, 71, 62), "GRAIN": (72, 49, 44)}
BOARD = {"BASE": (140, 100, 72), "LIGHT": (149, 108, 78), "WARM": (147, 103, 72), "DUSK": (127, 91, 68), "COOL": (129, 97, 76), "GRAIN": (92, 64, 50)}
WATER = np.array((84, 128, 136), float)
WATER_LIGHT = np.array((150, 192, 186), float)
INTERIOR = np.array((58, 40, 50), float)
INTERIOR_LIT = np.array((82, 56, 56), float)


class Skyline:
	"""a tighter packer than the fence's shelves: long strips and tall barrels share a sheet"""

	def __init__(self):
		self.h = np.zeros(SHEET, int)
		self.gap = 8

	def place(self, w, h):
		best = None
		for x in range(self.gap, SHEET - w - self.gap, 4):
			y = int(self.h[x : x + w + self.gap].max())
			if y + h + self.gap <= SHEET and (best is None or y < best[1]):
				best = (x, y)
		if best is None:
			raise RuntimeError(f"sheet full placing {w}x{h}")
		x, y = best
		y = max(y, self.gap)
		self.h[x : x + w + self.gap] = y + h + self.gap
		return x, y

	def used(self):
		return int(self.h.max())


def key(p):
	return (round(float(p[0]), 4), round(float(p[1]), 4), round(float(p[2]), 4))


class Piece:
	"""triangles in soup form: three corners each with a position, sheet uv (px) and a smoothing group (None = flat)"""

	def __init__(self, name):
		self.name = name
		self.tris = []
		self.normals = None

	def tri(self, a, b, c, ua, ub, uc, g=None):
		self.tris.append((np.array(a, float), np.array(b, float), np.array(c, float), ua, ub, uc, g))

	def quad(self, a, b, c, d, ua, ub, uc, ud, g=None):
		self.tri(a, b, c, ua, ub, uc, g)
		self.tri(a, c, d, ua, uc, ud, g)

	def quad_facing(self, want, a, b, c, d, ua, ub, uc, ud, g=None):
		"""a quad wound so its normal faces along want"""
		n = np.cross(np.array(c, float) - a, np.array(d, float) - np.array(b, float))
		if np.dot(n, want) < 0:
			b, d, ub, ud = d, b, ud, ub
		self.quad(a, b, c, d, ua, ub, uc, ud, g)

	def tri_facing(self, want, a, b, c, ua, ub, uc, g=None):
		if np.dot(np.cross(np.array(b, float) - a, np.array(c, float) - np.array(a, float)), want) < 0:
			b, c, ub, uc = c, b, uc, ub
		self.tri(a, b, c, ua, ub, uc, g)

	def volume(self):
		return sum(np.dot(t[0], np.cross(t[1], t[2])) for t in self.tris) / 6

	def done(self):
		"""wind outward, check the surface is closed and consistent, then smooth normals per group"""
		if self.volume() < 0:
			self.tris = [(a, c, b, ua, uc, ub, g) for a, b, c, ua, ub, uc, g in self.tris]
		edges = {}
		for a, b, c, *_ in self.tris:
			for p, q in ((a, b), (b, c), (c, a)):
				e = (key(p), key(q))
				edges[e] = edges.get(e, 0) + 1
		bad = [e for e, n in edges.items() if edges.get((e[1], e[0]), 0) != n]
		assert not bad, f"{self.name}: open or badly wound surface, {len(bad)} edges, e.g. {bad[0]}"
		assert self.volume() > 0, f"{self.name}: inside out"
		acc = {}
		face_n = []
		for a, b, c, _u, _v, _w, g in self.tris:
			n = np.cross(b - a, c - a)
			face_n.append(n)
			if g is not None:
				for p in (a, b, c):
					k = (g, key(p))
					acc[k] = acc.get(k, 0) + n
		self.normals = []
		for (a, b, c, _u, _v, _w, g), n in zip(self.tris, face_n):
			ns_ = [n if g is None else acc[(g, key(p))] for p in (a, b, c)]
			self.normals.append([v / (np.linalg.norm(v) + 1e-9) for v in ns_])
		return self

	def moved(self, o=(0, 0, 0), M=None):
		"""a copy under a rotation (and uniform scale) then an offset. Never a mirror: that would turn it inside out"""
		M = np.eye(3) if M is None else np.array(M, float)
		assert np.linalg.det(M) > 0
		o = np.array(o, float)
		out = Piece(self.name)
		out.tris = [(o + M @ a, o + M @ b, o + M @ c, ua, ub, uc, g) for a, b, c, ua, ub, uc, g in self.tris]
		out.normals = [[M @ n / (np.linalg.norm(M @ n) + 1e-9) for n in tri] for tri in self.normals]
		return out


def rx(deg):
	c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
	return np.array(((1, 0, 0), (0, c, -s), (0, s, c)))


def ry(deg):
	c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
	return np.array(((c, 0, s), (0, 1, 0), (-s, 0, c)))


def rz(deg):
	c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
	return np.array(((c, -s, 0), (s, c, 0), (0, 0, 1)))


def group(pieces, o=(0, 0, 0), M=None):
	return [p.moved(o, M) for p in pieces]


def unit(v):
	v = np.array(v, float)
	return v / np.linalg.norm(v)


class Strip:
	"""a beam's unrolled sides on the sheet, with the fence's 8 bands. Parts of many sizes can share one."""

	def __init__(self, P, sheet, name, length, w, h, ch, rng, pal=None, post=None, **paint):
		pts, kinds = P["beam_section"](w, h, ch)
		perim = [math.dist(pts[i], pts[(i + 1) % 8]) for i in range(8)]
		self.bands = [(max(4 if kinds[i] == "edge" else 6, int(round(perim[i] * T))), kinds[i]) for i in range(8)]
		self.H = sum(b[0] for b in self.bands)
		self.L = int(length * T)
		self.x, self.y = sheet.place(self.L, self.H)
		self.w, self.h, self.ch = w, h, ch
		with palette(P, pal):
			img = strip_paint(P, self.L, self.bands, rng, **paint)
		if post:
			img = post(img, self)
		sheet.img[self.y * P["SS"] : (self.y + self.H) * P["SS"], self.x * P["SS"] : (self.x + self.L) * P["SS"]] = img
		self.rows = [0]
		for b in self.bands:
			self.rows.append(self.rows[-1] + b[0])
		self.mids = [(self.rows[2 * j + 1] + self.rows[2 * j + 2]) / 2 for j in range(4)]

	def uv(self, f, row):
		return (self.x + f * self.L, self.y + row)


@contextmanager
def palette(P, pal):
	saved = {}
	if pal:
		for k, v in pal.items():
			saved[k] = P[k]
			P[k] = np.array(v, float)
	yield
	P.update(saved)


class Tile:
	def __init__(self, sheet, w, h):
		self.w, self.h = w, h
		self.x, self.y = sheet.place(w, h)

	def put(self, P, sheet, img):
		sheet.img[self.y * P["SS"] : (self.y + self.h) * P["SS"], self.x * P["SS"] : (self.x + self.w) * P["SS"]] = img

	def uv(self, fx, fy):
		return (self.x + fx * self.w, self.y + fy * self.h)


def beam(strip, end, length, w0, h0, w1=None, h1=None, ch=None, rings=2, bend=0.03, rng=None, jitter=0.012, tip=0.0, scales=None, box=False, u=(0.0, 1.0), name="beam"):
	"""local axes: x along, y up the face, z out of the front, as the fence's Part. box=True is 4 sides: hard edges, half the triangles, on the same strip."""
	w1, h1 = w1 or w0, h1 or h0
	mw, mh = max(w0, w1), max(h0, h1)
	if scales is None:
		scales = [(i / (rings - 1), (w0 + (w1 - w0) * i / (rings - 1)) / mw, (h0 + (h1 - h0) * i / (rings - 1)) / mh) for i in range(rings)]
	ch = strip.ch if ch is None else ch
	if box:
		pts = [(-mw / 2, mh / 2), (mw / 2, mh / 2), (mw / 2, -mh / 2), (-mw / 2, -mh / 2)]
		v_rows = [(0, strip.mids[0]), (strip.mids[0], strip.mids[1]), (strip.mids[1], strip.mids[2]), (strip.mids[2], strip.mids[3])]
	else:
		pts = [(-mw / 2 + ch, mh / 2), (mw / 2 - ch, mh / 2), (mw / 2, mh / 2 - ch), (mw / 2, -mh / 2 + ch), (mw / 2 - ch, -mh / 2), (-mw / 2 + ch, -mh / 2), (-mw / 2, -mh / 2 + ch), (-mw / 2, mh / 2 - ch)]
		v_rows = [(strip.rows[k], strip.rows[k + 1]) for k in range(8)]
	K = len(pts)
	R = len(scales)
	wob = rng.normal(0, 1, (R, 2)) * bend
	wob[0] *= 0.3
	ring = []
	for i, (f, sw, sh) in enumerate(scales):
		jit = rng.normal(0, jitter, (K, 2))
		rp = []
		for k, (a, b) in enumerate(pts):
			snap = rng.uniform(-tip, tip) if i == R - 1 else 0
			rp.append((length * f + snap, b * sh + wob[i, 0] + jit[k, 0], a * sw + wob[i, 1] + jit[k, 1]))
		ring.append(rp)
	p = Piece(name)
	for i in range(R - 1):
		u0 = u[0] + (u[1] - u[0]) * scales[i][0]
		u1 = u[0] + (u[1] - u[0]) * scales[i + 1][0]
		for k in range(K):
			a, b, c, d = ring[i][k], ring[i + 1][k], ring[i + 1][(k + 1) % K], ring[i][(k + 1) % K]
			v0, v1 = v_rows[k]
			p.quad(a, b, c, d, strip.uv(u0, v0), strip.uv(u1, v0), strip.uv(u1, v1), strip.uv(u0, v1), g=(k if box else 0))

	def cap_uv(pt):
		return end.uv(0.5 + 0.48 * pt[1] / mh * 1.0 + 0.0, 0.5 + 0.48 * pt[0] / mw)

	for side, r in ((0, ring[0]), (1, ring[-1])):
		loc = [pts[k] for k in range(K)]
		for k in range(1, K - 1):
			ids = (0, k, k + 1) if side == 0 else (0, k + 1, k)
			p.tri(r[ids[0]], r[ids[1]], r[ids[2]], cap_uv(loc[ids[0]]), cap_uv(loc[ids[1]]), cap_uv(loc[ids[2]]), None)
	return p.done()


def bar(strip, end, p0, p1, w, h, front=(0, 0, 1), **kw):
	"""a beam placed from p0 to p1 with its front face turned toward front"""
	p0, p1 = np.array(p0, float), np.array(p1, float)
	length = float(np.linalg.norm(p1 - p0))
	ax = unit(p1 - p0)
	az = np.array(front, float) - ax * np.dot(front, ax)
	az = unit(az)
	ay = np.cross(az, ax)
	return beam(strip, end, length, w, h, **kw).moved(p0, np.column_stack((ax, ay, az)))


# ---------------------------------------------------------------- barrels


def barrel_profile(H, R, sink):
	"""rows up the barrel: (y, radius, kind). Hoops stand proud of the belly."""
	body = lambda y: R * (0.80 + 0.20 * math.sin(math.pi * np.clip((y + sink * 0.3) / H, 0, 1)))
	hw = 0.42
	low, high = H * 0.17, H * 0.72
	rows = [(-sink, body(-sink) * 0.97, "body")]
	for y0 in (low, high):
		rows.append((y0, body(y0) + 0.08, "hoop"))
		rows.append((y0 + hw, body(y0 + hw) + 0.08, "body"))
	rows.append((H, body(H) + 0.03, "lip"))
	rows.append((H - 0.02, body(H) - 0.16, "well"))
	rows.append((H - 0.3, body(H) - 0.2, "cap"))
	return rows


def arcs(rows):
	lens = [0.0]
	for a, b in zip(rows, rows[1:]):
		lens.append(lens[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
	return lens


# the painted light: not just lighter and darker, the colour moves too. Lit surfaces lean gold, undersides plum, multiplied so the grain stays.
LIT_TINT = np.array((1.07, 1.03, 0.9))
UNDER_TINT = np.array((0.76, 0.67, 0.76))
TOP_TINT = np.array((1.13, 1.08, 0.93))  # faces looking straight up
GRAD_CURVE = 1.3
GRAD_PLANK = 0.5  # gentler than a whole face: at full strength a flat board rounds off like a log


def darken(t):
	"""multiplier for t, 0 at the lit top of a face and 1 at its underside"""
	t = np.clip(t, 0, 1)[..., None]
	return 1 + (LIT_TINT - 1) * (1 - t) ** 1.5 + (UNDER_TINT - 1) * t**GRAD_CURVE


# shadow shapes: what makes it read as anime rather than a soft render. A shape with a clean, slightly cut edge, plum, painted over the grain, instead of a smooth fade.
SHADE_TINT = np.array((0.7, 0.6, 0.74))
SHADE_RNG = np.random.default_rng(29)


def cut_edge(n, base, amp, knots):
	"""a hand-cut line: straight runs between a few points, rather than noise"""
	return np.interp(np.arange(n), np.linspace(0, n, knots), base + SHADE_RNG.uniform(-amp, amp, knots))


def shade(P, img, mask, amount=1.0):
	m = gaussian_filter(mask.astype(np.float32), 0.45 * P["SS"])[..., None] * amount
	return img * (1 - m * (1 - SHADE_TINT))


# corner darkening: small plum shadows painted where pieces meet, framing the shape. Sparse: only some corners get one. Own random stream, so tuning it never moves the shapes.
AO_ALPHA = 0.58
AO_REACH = 0.42  # studs, along the grain; across it is about half
AO_CHANCE = 0.55
AO_RNG = np.random.default_rng(7)


def ao_spots(P, img, spots):
	"""spots: (x, y, rx, ry, strength) in painted pixels"""
	H, L = img.shape[:2]
	m = np.zeros((H, L), np.float32)
	for x, y, rx, ry, st in spots:
		x0, x1 = max(int(x - rx * 3), 0), min(int(x + rx * 3) + 1, L)
		y0, y1 = max(int(y - ry * 3), 0), min(int(y + ry * 3) + 1, H)
		if x1 <= x0 or y1 <= y0:
			continue
		yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
		m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], np.exp(-(((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2)) * st)
	return P["over"](img, P["SHADOW"], m * AO_ALPHA)


STUDIO_LIFT = np.array((1.12, 1.16, 1.06))  # on top of the fence's grade. Measured in Studio: barrels sat about 15% darker and more purple than the fence rails beside them
EDGE_LINE = np.array((206, 172, 134), float)  # warm pale wood, quieter than the fence's cream
EDGE_ALPHA = 0.6
EDGE_HALF = 1.0  # half width of the line in sheet pixels


def strip_paint(P, length, bands, rng, levels=None, ao_ends=(True, True), grad="across", **kw):
	"""the fence's wood paint without its highlights (the user, on the props: too blurry, too random), then one crisp thin line per chosen edge.
	levels: strength per edge band in order. Default: only the two edges that meet the top face, where light really lands. The line fades slowly and never breaks."""
	SS = P["SS"]
	img = P["paint_strip"](length, [(px, "chamfer" if k == "edge" else k) for px, k in bands], rng, **kw)
	edges = []
	y = 0
	for px, k in bands:
		if k == "edge":
			edges.append((y, px))
		# across: a plank's front runs top to bottom down the strip, its back the other way. along: an upright, with its foot at x=0
		if grad == "across" and k in ("front", "back"):
			t = (np.arange(px * SS) + 0.5) / (px * SS)
			# gentler than a whole face: at full strength a flat board rounds off like a log
			img[y * SS : (y + px) * SS] *= 1 - (1 - darken(t if k == "front" else 1 - t)[:, None, :]) * GRAD_PLANK
		if grad == "across" and k in ("front", "back") and px >= 16:  # boards only: on an upright this would be a stripe from nowhere
			edge = cut_edge(img.shape[1], 0.68, 0.07, max(4, length // 60)) * px * SS
			rows = np.arange(px * SS)[:, None]
			m = rows > edge[None, :] if k == "front" else rows < (px * SS - edge)[None, :]
			img[y * SS : (y + px) * SS] = shade(P, img[y * SS : (y + px) * SS], m, 0.45)
		y += px
	if grad == "along":
		img *= darken(1 - (np.arange(img.shape[1]) + 0.5) / img.shape[1])[None, :, :]
	if levels is None:
		levels = (1.0, 0, 0, 1.0) if len(edges) == 4 else (1.0,) + (0,) * (len(edges) - 1)
	L = length * SS
	yy = np.arange(img.shape[0])[:, None]
	line = np.zeros(img.shape[:2], np.float32)
	for (y0, px), level in zip(edges, levels):
		if level <= 0:
			continue
		slow = gaussian_filter(rng.normal(0, 1, L + 400 * SS), 40 * SS)[200 * SS : 200 * SS + L]
		slow = slow / (np.abs(slow).max() + 1e-6)
		half = min(EDGE_HALF, px / 2) * SS
		d = np.abs(yy - (y0 + px / 2) * SS)
		line = np.maximum(line, np.clip(half + 0.5 - d, 0, 1) * ((0.78 + 0.22 * slow) * level)[None, :])
	img = P["over"](img, EDGE_LINE, line * EDGE_ALPHA)
	# corners at the piece's ends, on the two big faces only, each by chance
	spots = []
	stud = T * SS
	y = 0
	for px, k in bands:
		if k in ("front", "back"):
			for end, on in ((0, ao_ends[0]), (L, ao_ends[1])):
				for row in (y, y + px):
					if on and AO_RNG.random() < AO_CHANCE:
						r = AO_RNG.uniform(0.7, 1.15) * AO_REACH * stud
						spots.append((end, row * SS, r, min(r * 0.5, px * SS * 0.45), AO_RNG.uniform(0.6, 1)))
		y += px
	# the strip wraps round the beam, so a spot near its top or bottom row carries on at the other side
	wrap = lambda items: items + [(x_, y_ + d, rx, ry, st) for x_, y_, rx, ry, st in items for d in (-img.shape[0], img.shape[0])]
	return ao_spots(P, img, wrap(spots))


def paint_barrel_strip(P, sheet, name, H, R, sink, M, rng):
	SS, over = P["SS"], P["over"]
	rows = barrel_profile(H, R, sink)
	arc = arcs(rows)
	L = int(arc[-1] * T)
	stave = int(round(2 * math.pi * R * 0.96 * T / M))
	seam, edge = 2, 3
	bands = []
	for k in range(M):
		bands += [(edge, "seam"), (stave, "front"), (seam, "seam")]
	x, y = sheet.place(L, (stave + seam + edge) * M)
	CH = (stave + seam + edge) * M
	frac = [a / arc[-1] for a in arc]
	contacts = [(frac[1], 7), (frac[2], 8), (frac[3], 7), (frac[4], 8)]
	img = P["paint_strip"](L, bands, rng, contacts=contacts, foot=True, knots=2)
	col = (stave + seam + edge) * SS
	# each stave a little its own, the paint varying by plank rather than by blotch
	for k in range(M):
		img[k * col : (k + 1) * col] *= rng.uniform(0.93, 1.07)
	yy = np.arange(CH * SS)[:, None]
	xx = np.arange(L * SS)[None, :]
	# seams between staves: thin, brown, sharp
	seam_mask = np.zeros((CH * SS, L * SS), np.float32)
	for k in range(M):
		seam_mask[(k + 1) * col - seam * SS : (k + 1) * col] = 1
	img = over(img, P["GRAIN"] * 0.82, gaussian_filter(seam_mask, 0.25 * SS) * 0.92)
	# painted light: dark at the foot, brightest high on the belly, shadow pooling under the top hoop
	t = xx / (L * SS)
	img = img * (0.86 + 0.26 * np.clip(t / frac[4], 0, 1))[..., None]
	# hoops: iron, painted in place with the same edge recipe, the top edge carrying the light
	for i0, i1 in ((1, 2), (3, 4)):
		x0, x1 = int(frac[i0] * L), int(frac[i1] * L)
		hw = x1 - x0
		with palette(P, IRON):
			hoop = strip_paint(P, CH, [(3, "edge"), (hw - 6, "front"), (3, "edge")], rng, levels=(1.0, 0), ao_ends=(False, False), grad=None, knots=0, nails=((rng.uniform(0.1, 0.3), 0.5), (rng.uniform(0.6, 0.85), 0.5)))
		img[:, x0 * SS : x1 * SS] = np.rot90(hoop, k=-1)
	# shadow shapes: a band under each hoop. Only shadows something visibly casts: a shade down one side came from nowhere
	W_ = L * SS
	mask = np.zeros((CH * SS, W_), bool)
	for i0 in (1, 3):
		x0 = int(frac[i0] * L) * SS
		depth = cut_edge(CH * SS, 0.2 * T * SS, 0.05 * T * SS, M * 2)
		mask |= (xx >= x0 - depth[:, None]) & (xx < x0)
	img = shade(P, img, mask, 0.8)
	# the lip: pale end grain with its own broken highlight; below it, the inside of the staves going dark
	xl, xw = int(frac[-3] * L) * SS, int(frac[-2] * L) * SS
	pale = P["LIGHT"] * 1.16
	img[:, xl:xw] = pale * (0.94 + 0.12 * gaussian_filter(rng.normal(0, 1, (CH * SS, xw - xl)), (10 * SS, 1 * SS)) * 8)[..., None]
	lip_seam = np.zeros((CH * SS, xw - xl), np.float32)
	for k in range(M):
		lip_seam[(k + 1) * col - seam * SS : (k + 1) * col] = 1
	img[:, xl:xw] = over(img[:, xl:xw], P["GRAIN"], lip_seam * 0.8)
	img[:, xw:] = over(img[:, xw:], INTERIOR, np.full((CH * SS, L * SS - xw), 0.85, np.float32))
	xt = (np.arange(xl) + 0.5) / xl
	img[:, :xl] *= darken(1 - xt)[None, :, :]
	spots = []
	for k in range(M):
		for f, chance in ((frac[1], 0.3), (frac[2], 0.45), (frac[3], 0.45), (frac[4], 0.3), (frac[-3], 0.5)):
			if AO_RNG.random() < chance:
				r = AO_RNG.uniform(0.7, 1.1) * AO_REACH * T * SS
				spots.append((f * L * SS, (k + 1) * col, r * 0.9, r * 0.55, AO_RNG.uniform(0.6, 1)))
	img = ao_spots(P, img, spots)
	sheet.img[y * SS : (y + CH) * SS, x * SS : (x + L) * SS] = np.clip(img, 0, 255)
	return {"x": x, "y": y, "L": L, "col": col / SS, "M": M, "rows": rows, "frac": frac}


def paint_lid(P, sheet, size, rng, water=False):
	SS, over = P["SS"], P["over"]
	tile = Tile(sheet, size, size)
	n = size * SS
	yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
	d = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
	if water:
		img = np.zeros((n, n, 3), float) + WATER
		band = gaussian_filter(rng.normal(0, 1, (n, n)).astype(np.float32), (3 * SS, 14 * SS))
		band = np.clip((band - band.mean()) / band.std() * 0.5, 0, 1)
		img = over(img, WATER_LIGHT, gaussian_filter((band > 0.72).astype(np.float32), 0.8 * SS) * 0.75)
		img = over(img, np.array((58, 92, 110), float), np.clip((d - 0.55) / 0.4, 0, 1) ** 1.5 * 0.8)
	else:
		planks = 4
		pl = (size - 2 * planks) // planks
		bands = []
		for _ in range(planks):
			bands += [(pl, "top"), (2, "seam")]
		extra = size - sum(b[0] for b in bands)
		bands[-2] = (pl + extra, "top")
		# paint_strip needs a face band for knots; none asked for
		img = P["paint_strip"](size, bands, rng, knots=0)
		mask = np.zeros((n, n), np.float32)
		y0 = 0
		for px, kind in bands:
			if kind == "seam":
				mask[y0 * SS : (y0 + px) * SS] = 1
			y0 += px
		img = over(img, P["GRAIN"] * 0.8, gaussian_filter(mask, 0.25 * SS) * 0.9)
		img = img * 1.12
		img = over(img, P["SHADOW"], np.clip((d - 0.62) / 0.33, 0, 1) ** 1.6 * 0.85)
	tile.put(P, sheet, np.clip(img, 0, 255))
	return tile


def barrel(st, lid, H, R, sink, rng, lean=0.03, name="Barrel", base=(3.8, 1.46)):
	"""a lathe of M staves. Hoops and lip are rows in one closed shell, so 156 or so triangles carry a readable barrel."""
	M = st["M"]
	# the strip is painted once for the base shape; other sizes stretch the same rows over it, so hoops always land on painted hoops
	rows = [(y * H / base[0], r * R / base[1], k) for y, r, k in barrel_profile(base[0], base[1], sink)]
	frac = st["frac"]
	per_stave = rng.normal(0, 0.02, M)
	top_jag = rng.normal(0, 0.035, M)
	warp = rng.normal(0, 0.012, (len(rows), 2))
	lx, lz = rng.uniform(-lean, lean), rng.uniform(-lean, lean)
	ring = []
	for i, (y, r, kind) in enumerate(rows):
		rp = []
		is_top = i >= len(rows) - 3
		for k in range(M):
			a = 2 * math.pi * k / M + 0.2
			rr = r + per_stave[k]
			yy = y + (top_jag[k] if is_top else 0)
			rp.append((rr * math.cos(a) + warp[i, 0] + lx * y, yy, rr * math.sin(a) + warp[i, 1] + lz * y))
		ring.append(rp)
	p = Piece(name)
	sx, sy, L, col = st["x"], st["y"], st["L"], st["col"]
	for i in range(len(rows) - 1):
		u0, u1 = sx + frac[i] * L, sx + frac[i + 1] * L
		g = 0 if rows[i][2] in ("body", "hoop") else 1
		for k in range(M):
			j = (k + 1) % M
			v0, v1 = sy + k * col, sy + (k + 1) * col
			p.quad(ring[i][k], ring[i + 1][k], ring[i + 1][j], ring[i][j], (u0, v0), (u1, v0), (u1, v1), (u0, v1), g=g)
	top_r = rows[-1][1] + 0.05

	def luv(pt):
		return lid.uv(0.5 + 0.48 * (pt[0] - lx * rows[-1][0]) / top_r, 0.5 + 0.48 * (pt[2] - lz * rows[-1][0]) / top_r)

	for r, side in ((ring[0], 0), (ring[-1], 1)):
		for k in range(1, M - 1):
			ids = (0, k, k + 1) if side == 0 else (0, k + 1, k)
			p.tri(r[ids[0]], r[ids[1]], r[ids[2]], luv(r[ids[0]]), luv(r[ids[1]]), luv(r[ids[2]]), None)
	return p.done()


# ---------------------------------------------------------------- crates


class CrateTile(Tile):
	"""one painted face. Layout from the outside in: margin (the chamfer), frame slats, a dark wall band, then the panel."""

	def __init__(self, sheet, w_st, h_st, c, f):
		self.m = max(4, int(round(c * T)))
		self.f = int(round(f * T))
		self.wall = 6
		super().__init__(sheet, int(w_st * T) + self.m * 2, int(h_st * T) + self.m * 2)

	def outer(self, sx, ty):
		"""sx, ty in -1..1 over the face's flat rectangle"""
		return (self.x + self.m + (sx + 1) / 2 * (self.w - 2 * self.m), self.y + self.m + (1 - ty) / 2 * (self.h - 2 * self.m))

	def inner(self, sx, ty, extra=0):
		d = self.f + extra
		return (self.x + self.m + d + (sx + 1) / 2 * (self.w - 2 * self.m - 2 * d), self.y + self.m + d + (1 - ty) / 2 * (self.h - 2 * self.m - 2 * d))


def paint_crate_tile(P, sheet, W, H, rng, c=0.1, f=0.62, brace=None, top=False, hole=False, foot=False, planks=3):
	SS, over = P["SS"], P["over"]
	tile = CrateTile(sheet, W, H, c, f)
	tw, th = tile.w, tile.h
	m, fp, wall = tile.m, tile.f, tile.wall
	xa, xb, ya, yb = m + fp, tw - m - fp, m + fp, th - m - fp
	# panel: vertical planks, grain up the face
	if hole:
		yy, xx = np.mgrid[0 : th * SS, 0 : tw * SS].astype(np.float32)
		img = np.zeros((th * SS, tw * SS, 3), float) + INTERIOR
		g = np.exp(-(((yy / SS - th * 0.75) / (th * 0.35)) ** 2))
		img = over(img, INTERIOR_LIT, g.astype(np.float32) * 0.75)
	else:
		pw = tw // planks
		bands = []
		for _ in range(planks - 1):
			bands += [(pw - 3, "front"), (3, "seam")]
		bands.append((tw - sum(b[0] for b in bands), "front"))
		with palette(P, PANEL):
			img = np.rot90(P["paint_strip"](th, bands, rng, knots=int(rng.integers(1, 3))), k=-1).copy()
		seam = np.zeros((th * SS, tw * SS), np.float32)
		yrun = 0
		for px, kind in reversed(bands):
			if kind == "seam":
				seam[:, yrun * SS : (yrun + px) * SS] = 1
			yrun += px
		img = over(img, PANEL_GRAIN(P) * 0.85, gaussian_filter(seam, 0.25 * SS) * 0.92)
	if brace and not hole:
		dx, dy = (xb - xa), (yb - ya)
		ln = int(math.hypot(dx, dy)) + 40
		bw = int(0.62 * T)
		st = strip_paint(P, ln, [(4, "edge"), (bw - 8, "front"), (4, "edge")], rng, levels=(0.7, 0), ao_ends=(False, False), grad=None, knots=0, nails=((0.3, 0.5), (0.7, 0.5)))
		angle = math.degrees(math.atan2(dy, dx)) * (1 if brace > 0 else -1)
		canvas = np.zeros((th * SS, tw * SS, 3), np.float32)
		mask = np.zeros((th * SS, tw * SS), np.float32)
		cy, cx = th * SS // 2, tw * SS // 2
		sh, sl, _ = st.shape
		top_y, left_x = cy - sh // 2, cx - sl // 2
		# pasted into a big square first so the rotation has room, then cropped
		big = max(th, tw, ln) * SS + 8
		bc = np.zeros((big, big, 3), np.float32)
		bm = np.zeros((big, big), np.float32)
		by, bx = (big - sh) // 2, (big - sl) // 2
		bc[by : by + sh, bx : bx + sl] = st
		bm[by : by + sh, bx : bx + sl] = 1
		bc = rotate(bc, angle, reshape=False, order=1, axes=(1, 0))
		bm = rotate(bm, angle, reshape=False, order=1, axes=(1, 0))
		oy, ox = (big - th * SS) // 2, (big - tw * SS) // 2
		canvas = bc[oy : oy + th * SS, ox : ox + tw * SS]
		mask = bm[oy : oy + th * SS, ox : ox + tw * SS]
		safe = mask[..., None] > 0.5
		img = shade(P, img, np.roll(mask, 3 * SS, axis=0) > 0.5, 0.95)
		img = np.where(safe, canvas, img)
	yy, xx = np.mgrid[0 : th * SS, 0 : tw * SS].astype(np.float32)
	# painted light in the recess: the frame's shadow falls down onto the panel from the top slat, and in from the sides less
	in_panel = ((xx >= xa * SS) & (xx < xb * SS) & (yy >= ya * SS) & (yy < yb * SS)).astype(np.float32)
	if not hole:
		# the top slat's shadow falls on the panel, longer on the left, with the side slat's narrow one beside it
		drop = cut_edge(tw * SS, 0.62 * T * SS, 0.05 * T * SS, 4) * np.linspace(1.3, 0.62, tw * SS)
		fall = (yy < ya * SS + drop[None, :]) | (xx < (xa + 0.2 * T) * SS)
		img = shade(P, img, fall & (in_panel > 0.5), 1.0)
	# the frame: side slats first, top and bottom slats laid over them with a painted contact shadow and nails
	vert = [(0, m + fp), (tw - m - fp, tw)]
	for x0, x1 in vert:
		s = strip_paint(P, th, [(m, "edge"), (x1 - x0 - m * 2, "front"), (m, "edge")], rng, levels=(0, 0.45) if x0 == 0 else (0.45, 0), ao_ends=(False, False), grad=None, knots=0)
		img[:, x0 * SS : x1 * SS] = np.rot90(s, k=-1)[:, :: (1 if x0 == 0 else 1)]
	# the top slat also shades the side slats just under it
	under = cut_edge(tw * SS, (m + fp + 0.17 * T) * SS, 0.035 * T * SS, 6)
	img = shade(P, img, (yy < under[None, :]) & (in_panel < 0.5), 0.8)
	for y0, y1, upper in ((0, m + fp, True), (th - m - fp, th, False)):
		s = strip_paint(P, tw, [(m, "edge"), (y1 - y0 - m * 2, "front"), (m, "edge")], rng, levels=(1.0, 0) if upper else (0.55, 0), ao_ends=(False, False), grad=None, knots=0, nails=((0.09, 0.5), (0.91, 0.5)))
		img[y0 * SS : y1 * SS] = s if upper else s
	# the wall band is a dark ring just inside the frame; deep holes get darker ones
	wall_mask = ((xx >= xa * SS) & (xx < xb * SS) & (yy >= ya * SS) & (yy < yb * SS)).astype(np.float32)
	inner = ((xx >= (xa + wall) * SS) & (xx < (xb - wall) * SS) & (yy >= (ya + wall) * SS) & (yy < (yb - wall) * SS)).astype(np.float32)
	img = over(img, INTERIOR if hole else P["SHADOW"], (wall_mask - inner) * (0.92 if hole else 0.8))
	if not top:
		img = img * darken(yy / (th * SS))
	spots = []
	stud = T * SS
	# bottom corners are shared by faces painted on separate tiles, so nothing here is random: same centre, size and strength on every tile, or a spot would stop dead at the seam
	if not top:
		for cx in (m, tw - m):
			spots.append((cx * SS, (th - m) * SS, AO_REACH * 1.15 * stud, AO_REACH * 1.15 * stud, 0.75))
	for cx, cy in ((xa, ya), (xb, ya), (xa, yb), (xb, yb)):
		if AO_RNG.random() < AO_CHANCE:
			r = AO_RNG.uniform(0.7, 1.1) * AO_REACH * 0.8 * T * SS
			spots.append((cx * SS, cy * SS, r, r, AO_RNG.uniform(0.6, 1)))
	img = ao_spots(P, img, spots)
	if top:
		img = img * TOP_TINT
	if foot:
		reach = 0.72 * T
		wob = gaussian_filter(rng.normal(0, 1, tw * SS).astype(np.float32), 5 * SS, mode="wrap")
		wob = wob / (np.abs(wob).max() + 1e-6) * reach * 0.32 * SS
		dist = (th * SS - yy - wob[None, :]) / (reach * SS)
		img = over(img, P["SHADOW"], np.clip(1 - dist, 0, 1) ** 1.4 * 0.75)
	tile.put(P, sheet, np.clip(img, 0, 255))
	return tile


def PANEL_GRAIN(P):
	return np.array(PANEL["GRAIN"], float)


def crate(tiles, W, H, D, sink, rng, c=0.1, f=0.62, inset=0.17, deep=None, jit=0.05, name="Crate"):
	"""one closed shell: chamfered box with an inset panel on each face but the bottom. 124 triangles."""
	deep = deep or {}
	cy = H / 2 - sink
	centre = np.array((0, cy, 0.0))
	F = {
		"front": ((0, 0, 1), (1, 0, 0), (0, 1, 0), W / 2, H / 2, D / 2),
		"back": ((0, 0, -1), (-1, 0, 0), (0, 1, 0), W / 2, H / 2, D / 2),
		"right": ((1, 0, 0), (0, 0, -1), (0, 1, 0), D / 2, H / 2, W / 2),
		"left": ((-1, 0, 0), (0, 0, 1), (0, 1, 0), D / 2, H / 2, W / 2),
		"top": ((0, 1, 0), (1, 0, 0), (0, 0, -1), W / 2, D / 2, H / 2),
		"bottom": ((0, -1, 0), (1, 0, 0), (0, 0, 1), W / 2, D / 2, H / 2),
	}
	corners = {}
	for sx in (-1, 1):
		for sy in (-1, 1):
			for sz in (-1, 1):
				# the crate's own wonk: corners off true, the top a little narrower than the base
				o = rng.normal(0, jit, 3) * (0.5, 0.35, 0.5)
				if sy > 0:
					o = o + np.array((-sx, 0, -sz)) * 0.03
				corners[(sx, sy, sz)] = o
	F = {k: tuple(np.array(v, float) if i < 3 else v for i, v in enumerate(val)) for k, val in F.items()}

	def sign_of(n, u, v, si, ti):
		s = np.array(n) + np.array(u) * si + np.array(v) * ti
		return (int(np.sign(s[0])), int(np.sign(s[1])), int(np.sign(s[2])))

	def vert(name_, si, ti):
		n, u, v, a, b, d = F[name_]
		return centre + n * d + u * si * (a - c) + v * ti * (b - c) + corners[sign_of(n, u, v, si, ti)]

	p = Piece(name)
	for fi, (nm, (n, u, v, a, b, d)) in enumerate(F.items()):
		tile = tiles[nm]
		if nm == "bottom":
			pts = [vert(nm, si, ti) for si, ti in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
			uvs = [tile.outer(si, ti) for si, ti in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
			p.quad_facing(n, *pts, *uvs, g=None)
			continue
		fs, ft = 1 - f / (a - c), 1 - f / (b - c)
		wig = rng.normal(0, 0.012, (4, 2))
		idepth = deep.get(nm, inset)
		o_ = {}
		i_ = {}
		j_ = {}
		corner_order = ((-1, -1), (1, -1), (1, 1), (-1, 1))
		for idx, (si, ti) in enumerate(corner_order):
			o_[idx] = vert(nm, si, ti)
			base = o_[idx]
			# inner frame corner: pulled in from the outer one by the slat width
			i_[idx] = base - u * si * f - v * ti * f + u * wig[idx, 0] + v * wig[idx, 1]
			j_[idx] = i_[idx] - n * idepth - u * si * 0.02 - v * ti * 0.02
		for idx in range(4):
			nx = (idx + 1) % 4
			s0, t0 = corner_order[idx]
			s1, t1 = corner_order[nx]
			# frame slat
			p.quad_facing(n, o_[idx], o_[nx], i_[nx], i_[idx], tile.outer(s0, t0), tile.outer(s1, t1), tile.inner(s0, t0), tile.inner(s1, t1) if False else tile.inner(s1, t1), g=0) if False else p.quad_facing(n, o_[idx], o_[nx], i_[nx], i_[idx], tile.outer(s0, t0), tile.outer(s1, t1), tile.inner(s1, t1), tile.inner(s0, t0), g=0)
			# recess wall, facing the panel's middle
			mid_edge = (i_[idx] + i_[nx]) / 2
			panel_mid = sum(i_.values()) / 4
			want = panel_mid - mid_edge
			p.quad_facing(want, i_[idx], i_[nx], j_[nx], j_[idx], tile.inner(s0, t0), tile.inner(s1, t1), tile.inner(s1, t1, tile.wall), tile.inner(s0, t0, tile.wall), g=f"wall{fi}{idx}")
		p.quad_facing(n, j_[0], j_[1], j_[2], j_[3], tile.inner(-1, -1, tile.wall), tile.inner(1, -1, tile.wall), tile.inner(1, 1, tile.wall), tile.inner(-1, 1, tile.wall), g=None)
	# chamfers along the 12 edges, painted from the margin of the first face that owns them
	order = ["top", "front", "right", "back", "left", "bottom"]
	seen = set()
	for A in order:
		for B in order:
			if A == B or (B, A) in seen:
				continue
			nA, nB = F[A][0], F[B][0]
			if abs(np.dot(nA, nB)) > 0.5:
				continue
			seen.add((A, B))
			tile = tiles[A]
			uA, vA = F[A][1], F[A][2]
			out_s, out_t = float(np.dot(nB, uA)), float(np.dot(nB, vA))
			ends = []
			for other in (-1, 1):
				if abs(out_s) > 0.5:
					ends.append((out_s, other))
				else:
					ends.append((other, out_t))
			corners_sign = [sign_of(nA, uA, vA, si, ti) for si, ti in ends]
			qa, qb = [], []
			for sg in corners_sign:
				sg_v = np.array(sg, float)
				sa, ta = float(np.dot(sg_v, uA)), float(np.dot(sg_v, vA))
				sb, tb = float(np.dot(sg_v, F[B][1])), float(np.dot(sg_v, F[B][2]))
				qa.append(vert(A, sa, ta))
				qb.append(vert(B, sb, tb))
			(s0, t0), (s1, t1) = ends
			ua0, ua1 = tile.outer(s0, t0), tile.outer(s1, t1)
			dx, dy = out_s * tile.m, -out_t * tile.m
			ub0, ub1 = (ua0[0] + dx, ua0[1] + dy), (ua1[0] + dx, ua1[1] + dy)
			want = (qa[0] + qa[1] + qb[0] + qb[1]) / 4 - centre
			p.quad_facing(want, qa[0], qa[1], qb[1], qb[0], ua0, ua1, ub1, ub0, g=0)
	# the 8 little corner triangles
	for sg in corners:
		sg_v = np.array(sg, float)
		names = [k for k in order if np.dot(F[k][0], sg_v) > 0]
		pts = []
		for nm in names:
			pts.append(vert(nm, float(np.dot(sg_v, F[nm][1])), float(np.dot(sg_v, F[nm][2]))))
		tile = tiles[names[0]]
		uA, vA = F[names[0]][1], F[names[0]][2]
		s, t = float(np.dot(sg_v, uA)), float(np.dot(sg_v, vA))
		base = tile.outer(s, t)
		uvs = [base, (base[0] + s * tile.m, base[1]), (base[0], base[1] - t * tile.m)]
		want = (pts[0] + pts[1] + pts[2]) / 3 - centre
		p.tri_facing(want, pts[0], pts[1], pts[2], uvs[0], uvs[1], uvs[2], g=0)
	return p.done()


# ---------------------------------------------------------------- wheel and cart


def wheel(rim, spoke, hub, end, R, width, rng, segs=10, spokes=6):
	"""in the xy plane, axis along z, centred on the origin. About 180 triangles: rim 80, spokes 72, hub 28."""
	radial = 0.56
	t = width / 2
	rad = R + rng.normal(0, 0.035, segs)
	offs = rng.normal(0, 0.02, segs)
	sec = lambda r: ((r, -t), (r, t), (r - radial, t), (r - radial, -t))
	p = Piece("Rim")
	rows = (0, rim.mids[0]), (rim.mids[0], rim.mids[1]), (rim.mids[1], rim.mids[2]), (rim.mids[2], rim.mids[3])
	for i in range(segs):
		j = (i + 1) % segs
		a0, a1 = math.tau * i / segs, math.tau * (i + 1) / segs
		u0, u1 = i / segs, (i + 1) / segs
		s0, s1 = sec(rad[i]), sec(rad[j])
		for k in range(4):
			n = (k + 1) % 4
			v0, v1 = rows[k]
			A = (s0[k][0] * math.cos(a0), s0[k][0] * math.sin(a0), s0[k][1] + offs[i])
			B = (s1[k][0] * math.cos(a1), s1[k][0] * math.sin(a1), s1[k][1] + offs[j])
			C = (s1[n][0] * math.cos(a1), s1[n][0] * math.sin(a1), s1[n][1] + offs[j])
			D = (s0[n][0] * math.cos(a0), s0[n][0] * math.sin(a0), s0[n][1] + offs[i])
			p.quad(A, B, C, D, rim.uv(u0, v0), rim.uv(u1, v0), rim.uv(u1, v1), rim.uv(u0, v1), g=k)
	parts = [p.done()]
	hub_r = 0.62
	parts.append(bar(hub, end, (0, 0, -t - 0.22), (0.01, 0.01, t + 0.28), 2 * hub_r, 2 * hub_r, front=(0, 1, 0), bend=0.0, rng=rng, ch=0.36, name="Hub"))
	for s in range(spokes):
		a = math.tau * (s + rng.uniform(-0.05, 0.05)) / spokes + 0.26
		c_, s_ = math.cos(a), math.sin(a)
		parts.append(bar(spoke, end, (c_ * hub_r * 0.7, s_ * hub_r * 0.7, 0.02), (c_ * (R - radial + 0.08), s_ * (R - radial + 0.08), -0.02), 0.34, 0.4, h1=0.3, front=(0, 0, 1), box=True, bend=0.015, rng=rng, u=(rng.uniform(0, 0.2), rng.uniform(0.8, 1)), name="Spoke"))
	return parts


def cart_body(S, end, rng, broken=False):
	"""the bed and shafts in axle coordinates: origin on the axle, +x toward the handles"""
	parts = []
	X0, X1 = -4.7, 4.5
	# floor: three planks, front faces up
	for z, wid in ((-1.45, 1.42), (0.02, 1.5), (1.5, 1.4)):
		parts.append(bar(S["plank"], end, (X0 + rng.uniform(-0.1, 0.1), 0.42, z), (X1 + rng.uniform(-0.1, 0.1), 0.42 + rng.uniform(-0.03, 0.03), z), 0.3, wid, front=(0, 1, 0), bend=0.015, rng=rng, u=(rng.uniform(0, 0.08), rng.uniform(0.92, 1)), name="Floor"))
	# sides: two boards each with a gap you can see through
	for side in (-1, 1):
		zz = side * 2.42
		front = (0, 0, side)
		parts.append(bar(S["plank"], end, (X0 - 0.2, 1.08, zz), (X1 + 0.15, 1.04, zz + side * 0.03), 0.3, 1.2, h1=1.05, front=front, bend=0.018, rng=rng, name="SideLow"))
		if not (broken and side > 0):
			parts.append(bar(S["plank"], end, (X0 - 0.35, 2.36, zz + side * 0.03), (X1 + 0.28, 2.44, zz + side * 0.07), 0.3, 0.92, h1=1.06, front=front, bend=0.018, rng=rng, u=(0.04, 0.98), name="SideHigh"))
		else:
			parts.append(bar(S["plank"], end, (X0 - 0.35, 2.36, zz + side * 0.03), (0.5, 2.6, zz + side * 0.2), 0.3, 0.92, h1=0.6, front=front, bend=0.018, rng=rng, u=(0.04, 0.55), tip=0.42, name="SideHighBroken"))
		for x in (X0 + 0.5, X1 - 0.55):
			parts.append(bar(S["stake"], end, (x, 0.05, side * 2.72), (x + rng.uniform(-0.06, 0.06), 3.15 + rng.uniform(-0.15, 0.15), side * (2.72 + rng.uniform(0.02, 0.1))), 0.42, 0.46, front=(0, 0, side), box=True, bend=0.015, rng=rng, name="Stake"))
	# tail board: planks across the back
	parts.append(bar(S["plank"], end, (X0 - 0.2, 1.6, -2.55), (X0 - 0.2, 1.68, 2.55), 0.3, 1.5, front=(-1, 0, 0), bend=0.015, rng=rng, u=(0.1, 0.62), name="Tail"))
	parts.append(bar(S["plank"], end, (X1 + 0.12, 1.5, 2.55), (X1 + 0.12, 1.52, -2.55), 0.3, 1.32, front=(1, 0, 0), bend=0.015, rng=rng, u=(0.38, 0.92), name="Head"))
	# shafts run under the bed to the handles, which taper and rise a little at the tip
	for side in (-1, 1):
		parts.append(bar(S["shaft"], end, (X0 + 0.1, -0.08, side * 1.72), (9.9, -0.32, side * 1.62), 0.46, 0.6, w1=0.38, h1=0.42, rings=3, bend=0.04, rng=rng, name="Shaft"))
	parts.append(bar(S["stake"], end, (8.0, -0.05, -1.95), (8.02, -0.05, 1.95), 0.34, 0.34, front=(0, 1, 0), box=True, bend=0.012, rng=rng, name="Yoke"))
	parts.append(bar(S["stake"], end, (-0.1, -0.08, -3.3), (0.1, -0.05, 3.3), 0.5, 0.52, front=(0, 1, 0), box=True, bend=0.01, rng=rng, name="Axle"))
	return parts


# ---------------------------------------------------------------- the sign's carved marks


def carve(marks):
	"""a post-paint hook: short carved lines on the strip's front face, dark with a pale sliver under, so they read as cut wood. Marks only, no writing."""

	def post(img, strip):
		P = PAINTER
		SS = P["SS"]
		H, L, _ = img.shape
		rows = [0]
		for b in strip.bands:
			rows.append(rows[-1] + b[0])
		y0, y1 = rows[2] * SS, rows[3] * SS
		dark = np.zeros((H, L), np.float32)
		pale = np.zeros((H, L), np.float32)
		for (ax, ay), (bx, by) in marks:
			n = int(max(abs(bx - ax) * L, abs(by - ay) * (y1 - y0))) + 2
			for t in np.linspace(0, 1, n):
				x = int((ax + (bx - ax) * t) * L)
				y = int(y0 + (ay + (by - ay) * t) * (y1 - y0))
				r = SS + int(SS * 0.9 * math.sin(t * math.pi))
				dark[max(y - r, 0) : y + r, max(x - r, 0) : x + r] = 1
				pale[max(y + r, 0) : y + r + SS * 2, max(x - r, 0) : x + r] = 1
		pale = pale * (1 - dark)
		img = P["over"](img, P["EDGE_PALE"], gaussian_filter(pale, 0.4 * SS) * 0.55)
		return P["over"](img, P["GRAIN"] * 0.72, gaussian_filter(dark, 0.3 * SS) * 0.95)

	return post


PAINTER = None


def write_obj(path, name, parts):
	lines, faces = [f"o {name}"], []
	vi = 1
	for part in parts:
		for tri, nrm in zip(part.tris, part.normals):
			for p, uv, n in zip(tri[:3], tri[3:6], nrm):
				lines.append("v %.4f %.4f %.4f" % tuple(p))
				lines.append("vt %.5f %.5f" % (uv[0] / SHEET, 1 - uv[1] / SHEET))
				lines.append("vn %.4f %.4f %.4f" % tuple(n))
			faces.append(f"f {vi}/{vi}/{vi} {vi + 1}/{vi + 1}/{vi + 1} {vi + 2}/{vi + 2}/{vi + 2}")
			vi += 3
	open(path, "w").write("\n".join(lines + faces) + "\n")
	for part in parts:
		assert part.volume() > 0, f"{name}: {part.name} inside out"
	return sum(len(p.tris) for p in parts)


def finish_sheet(raw, mixed, keep):
	"""the crisp pass from the bridge (docs/style/crisp-paint.md), as the last step of every rebuild. Same layout, so the models don't change.
	Strips have their grain along x. Crate tiles mix directions, so marks there aren't tied to one. Water keeps its paint: wood marks don't belong on it."""
	if CRISP_LOOK == "none":
		return Image.fromarray(raw)
	sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
	from crisp_paint import LOOKS, crisp_sheet

	look = dict(LOOKS[CRISP_LOOK])
	look["sharpen_by"] = look.pop("sharpen")
	along, n = crisp_sheet(raw, np.random.default_rng(5), True, CRISP_STRENGTH, **look)
	free, _ = crisp_sheet(raw, np.random.default_rng(6), False, CRISP_STRENGTH, **look)
	out = along.copy()
	for t in mixed:
		out[t.y : t.y + t.h, t.x : t.x + t.w] = free[t.y : t.y + t.h, t.x : t.x + t.w]
	for t in keep:
		out[t.y : t.y + t.h, t.x : t.x + t.w] = raw[t.y : t.y + t.h, t.x : t.x + t.w]
	print("crisp pass:", CRISP_LOOK, "over", n, "islands")
	return Image.fromarray(out)


def build():
	global PAINTER
	P = load_painter()
	PAINTER = P
	assert P["SHEET"] == SHEET
	P["SHADOW"] = np.array((70, 48, 70), float)  # further into plum than the fence's (72, 54, 58)
	rng = np.random.default_rng(41)
	sheet = P["Sheet"]()
	sky = Skyline()
	sheet.place = sky.place
	SS = P["SS"]

	# strips: big first, so the shelves pack tightly
	bar_a = paint_barrel_strip(P, sheet, "BarrelA", 3.8, 1.46, 0.3, 10, rng)
	plank = Strip(P, sheet, "plank", 9.6, 0.3, 1.26, 0.08, rng, knots=2, nails=((0.03, 0.42), (0.97, 0.42), (0.3, 0.42)), scratch=True)
	rim = Strip(P, sheet, "rim", 11.0, 0.62, 0.56, 0.0, rng, ao_ends=(False, False), knots=2, contacts=tuple((i / 5, 3) for i in range(1, 5)), nails=tuple((i / 5 + 0.03, 0.42) for i in range(5)), post=None)
	shaft = Strip(P, sheet, "shaft", 11.0, 0.46, 0.6, 0.08, rng, knots=1)
	# no contact bands: they'd wrap the back of the post, where nothing casts them.
	# The bands used to draw from the shared rng, so the dropped paint still runs on it: everything after the post stays as uploaded and approved.
	post_args = dict(foot=True, knots=2, ao_ends=(False, True), grad="along")
	post_sign = Strip(P, sheet, "post", 8.6, 1.06, 1.06, 0.09, copy.deepcopy(rng), **post_args)
	strip_paint(P, post_sign.L, post_sign.bands, rng, contacts=((0.62, 11), (0.8, 10)), **post_args)
	stake = Strip(P, sheet, "stake", 4.0, 0.46, 0.46, 0.0, rng, grad="along", knots=0)
	spoke = Strip(P, sheet, "spoke", 2.2, 0.34, 0.4, 0.0, rng, grad=None, knots=0)
	hub = Strip(P, sheet, "hub", 1.2, 1.24, 1.24, 0.34, rng, grad=None, knots=0, pal=PANEL)
	board_a = Strip(P, sheet, "boardA", 4.6, 0.3, 1.3, 0.08, rng, ao_ends=(True, False), pal=BOARD, knots=1, nails=((0.08, 0.42),), post=carve((((0.22, 0.22), (0.56, 0.22)), ((0.22, 0.5), (0.48, 0.5)), ((0.22, 0.78), (0.6, 0.78)))))
	board_b = Strip(P, sheet, "boardB", 3.9, 0.3, 1.14, 0.08, rng, ao_ends=(True, False), pal=BOARD, knots=0, nails=((0.1, 0.42),), post=carve((((0.25, 0.28), (0.34, 0.74)), ((0.34, 0.74), (0.43, 0.28)), ((0.5, 0.5), (0.68, 0.5)))))
	end_tile = Tile(sheet, 60, 60)
	end_tile.put(P, sheet, P["paint_end"](60, rng))
	lid_a = paint_lid(P, sheet, 146, rng)
	water = paint_lid(P, sheet, 160, rng, water=True)
	W, Hc, D = 3.6, 3.3, 3.6
	side_a = paint_crate_tile(P, sheet, W, Hc, rng, foot=True, planks=3)
	side_b = paint_crate_tile(P, sheet, W, Hc, rng, foot=True, planks=3, brace=1)
	side_c = paint_crate_tile(P, sheet, D, Hc, rng, foot=True, planks=4, brace=-1)
	top_t = paint_crate_tile(P, sheet, W, D, rng, top=True, planks=3)
	hole_side = paint_crate_tile(P, sheet, W, Hc, rng, hole=True, foot=True)
	hole_top = paint_crate_tile(P, sheet, W, D, rng, hole=True, top=True)
	S = {"plank": plank, "stake": stake, "shaft": shaft}

	def plain_tiles():
		return {"front": side_b, "back": side_c, "right": side_a, "left": side_c, "top": top_t, "bottom": side_a}

	barrel_a = barrel(bar_a, lid_a, 3.8, 1.46, 0.3, rng, name="BarrelA")
	barrel_c = barrel(bar_a, lid_a, 3.8, 1.46, 0.3, rng, lean=0.05, name="BarrelC")
	barrel_b = barrel(bar_a, water, 3.3, 1.6, 0.3, rng, name="BarrelB")
	crate_a = crate(plain_tiles(), W, Hc, D, 0.25, rng, name="CrateA")
	crate_b = crate({"front": side_c, "back": side_a, "right": side_b, "left": side_a, "top": top_t, "bottom": side_a}, W, Hc, D, 0.25, rng, jit=0.09, name="CrateB")

	# the pieces of a crate that fell apart: the top and front open, planks left behind
	broken_shell = crate({"front": hole_side, "back": side_c, "right": side_a, "left": side_b, "top": hole_top, "bottom": side_a}, W, Hc, D, 0.25, rng, jit=0.2, deep={"front": 0.95, "top": 1.15}, name="CrateBrokenShell")
	crate_broken = [
		broken_shell.moved((0, 0, 0), rz(3.5) @ rx(-1.5)),
		bar(plank, end_tile, (-1.72, 2.95, -0.25), (0.9, 3.26, -0.5), 0.26, 0.9, h1=0.55, front=(0, 1, 0), bend=0.02, rng=rng, tip=0.3, u=(0.05, 0.33), name="TopPlank"),
		bar(plank, end_tile, (1.78, 3.1, 0.8), (-0.35, 3.14, 1.0), 0.26, 0.82, h1=0.5, front=(0.1, 1, 0.15), bend=0.02, rng=rng, tip=0.34, u=(0.4, 0.62), name="TopPlank"),
		bar(plank, end_tile, (-1.68, 1.2, 1.86), (0.42, 0.72, 2.0), 0.24, 0.72, h1=0.46, bend=0.02, rng=rng, tip=0.26, u=(0.65, 0.87), name="FrontPlank"),
		bar(plank, end_tile, (2.3, -0.12, 2.3), (0.7, 2.6, 1.95), 0.26, 0.92, h1=0.62, front=(0.2, 0.5, 1), bend=0.02, rng=rng, tip=0.22, u=(0.1, 0.42), name="Leaning"),
		bar(plank, end_tile, (-3.8, 0.1, 1.4), (-1.2, 0.17, 3.3), 0.26, 0.9, h1=0.54, front=(0, 1, 0), bend=0.02, rng=rng, tip=0.28, u=(0.5, 0.82), name="Ground"),
	]

	# piles: not a tidy stack. Things slipped, a barrel on its side
	barrel_pile = [
		barrel_a.moved((-1.9, 0, -0.5)),
		barrel_c.moved((1.2, 0, -1.3), ry(70)),
		barrel_a.moved((0.3, 1.27, 2.15), ry(-25) @ rx(90) @ ry(30) ),
		crate_a.moved((-3.2, 0, 2.3), ry(24) * 0.72),
	]
	crate_stack = [
		crate_a.moved((-1.3, 0, 0), ry(8)),
		crate_b.moved((2.45, 0, 0.5), ry(-19) * 0.82),
		crate_b.moved((-1.0, 3.06, 0.1), ry(-16) * 0.84),
		barrel_a.moved((-0.3, 0.1, 3.5), np.eye(3) * 0.82),
	]

	WR = 2.15
	wheels = wheel(rim, spoke, hub, end_tile, WR, 0.62, rng)
	body = cart_body(S, end_tile, rng)
	# parked: the bed swings forward about the axle until the shaft tips (9.9 out, 0.32 down) sit on the ground
	axle_y = WR - 0.08
	pitch = -math.degrees(math.asin((axle_y - 0.2 - 0.32) / 9.9))
	cart = group(body, (0, axle_y, 0), rz(pitch)) + group(wheels, (0, axle_y, 3.32), rz(14)) + group(wheels, (0, axle_y, -3.32), rz(200))
	# a wheel gone: the cart rolls over until the bare axle end (y -0.05, z 3.3) and the good wheel's rim (y -WR, z -3.32) both reach the ground
	roll_deg = math.degrees(math.atan2(WR - 0.05, 3.3 + 3.32))
	c_, s_ = math.cos(math.radians(roll_deg)), math.sin(math.radians(roll_deg))
	roll = rx(roll_deg)
	lift = np.array((0, WR * c_ - 3.32 * s_ - 0.1, 0))
	body_b = cart_body(S, end_tile, rng, broken=True)
	cart_broken = group(group(body_b, (0, 0, 0), rz(-0.5)) + group(wheels, (0, 0, -3.32), rz(70)), lift, roll)
	# the lost wheel, propped against the low side, and the piece of side board on the ground
	lean = -24
	cart_broken += group(wheels, (-3.3, WR * math.cos(math.radians(lean)) + 0.1, 4.25), rx(lean) @ rz(30))
	cart_broken += [bar(plank, end_tile, (2.9, 0.1, 4.7), (5.3, 0.14, 5.9), 0.26, 0.82, h1=0.5, front=(0, 1, 0), bend=0.02, rng=rng, tip=0.3, u=(0.58, 0.9), name="Dropped")]

	# signposts: a chunky post with pointed boards, each its own angle. Sized to the player, so the boards are at face height and above
	def post_at(lean_x, lean_z, height):
		foot = (0, -0.9, 0)
		top = (lean_x * height, height, lean_z * height)
		return bar(post_sign, end_tile, foot, top, 1.0, 1.0, w1=0.82, h1=0.8, rings=4, bend=0.05, rng=rng, tip=0.07, front=(0, 0, 1), u=(0, (height + 0.9) / 8.6), name="SignPost")

	def board(strip, y, z, length, h, yaw, tilt, right=True, tail=0.5):
		"""a board fixed across the post at height y, pointing along yaw, pointed at its far end"""
		dx, dz = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
		sgn = 1 if right else -1
		tilt_y = math.sin(math.radians(tilt)) * length
		p0 = np.array((-sgn * tail * dx, y, z - sgn * tail * dz))
		p1 = p0 + np.array((sgn * length * dx, tilt_y, sgn * length * dz))
		front = (-dz * sgn, 0, dx * sgn) if sgn > 0 else (dz, 0, -dx)
		front = np.array(front)
		if front[2] < 0:
			front = -front
		return bar(strip, end_tile, p0, p1, 0.3, h, front=tuple(front), bend=0.025, rng=rng, scales=[(0, 1, 1), (0.72, 1, 1), (1, 1, 0.1)], name="Board")

	sign = [
		post_at(-0.018, 0.012, 7.5),
		board(board_a, 5.45, 0.66, 4.6, 1.3, 6, 3, right=True),
		board(board_b, 3.95, 0.66, 3.9, 1.14, -8, -4, right=False),
	]
	# the leaning one: one good board, one slipped to hang off its last nail
	sign_lean = [
		post_at(0.17, 0.06, 6.7),
		board(board_b, 4.4, 0.66, 3.9, 1.14, 4, 8, right=False),
		bar(board_a, end_tile, (0.86, 3.75, 0.74), (0.98, 0.62, 0.95), 0.3, 1.24, front=(0.1, 0, 1), bend=0.025, rng=rng, scales=[(0, 1, 1), (0.72, 1, 1), (1, 1, 0.1)], name="HangingBoard"),
	]

	# an open barrel and small crate are their own props; a tipped barrel sits on its side
	props = {
		"BarrelA": [barrel_a],
		"BarrelOpen": [barrel_b],
		"BarrelPile": barrel_pile,
		"CrateA": [crate_a],
		"CrateSmall": [crate_b.moved((0, 0, 0), np.eye(3) * 0.72)],
		"CrateBroken": crate_broken,
		"CrateStack": crate_stack,
		"Cart": cart,
		"CartBroken": cart_broken,
		"SignPost": sign,
		"SignLean": sign_lean,
	}
	raw = Image.fromarray(np.clip(sheet.img * P["GRADE"] * STUDIO_LIFT, 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS)
	raw.save(os.path.join(OUT, "Props_Color_Raw.png"))
	finish_sheet(np.array(raw), [side_a, side_b, side_c, top_t, hole_side, hole_top], [water]).save(os.path.join(OUT, "Props_Color.png"))
	report = {}
	for name, parts in props.items():
		report[name] = write_obj(os.path.join(OUT, name + ".obj"), name, parts)
	json.dump({"Triangles": report, "SheetUsedToRow": sky.used()}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print(report, "sheet used to row", sky.used(), "of", SHEET)


def compare_sheet():
	r = os.path.join(OUT, "renders")
	font = ImageFont.truetype("arial.ttf", 22) if os.path.exists("C:/Windows/Fonts/arial.ttf") else ImageFont.load_default()
	rows = [
		(("lineup_a", "Beside the fence and a 5.2-stud player"),),
		(("lineup_b", "Cart and signposts"),),
		(("close_barrels", "Barrels, player height"), ("close_crates", "Crates, player height")),
		(("close_cart", "Cart"), ("close_broken_cart", "Broken cart")),
		(("close_signs", "Signposts"), ("close_stack", "Crate stack")),
		(("back_above", "Behind and above, back faces hidden as in Roblox"), ("back_above_b", "Cart and signs, same")),
		(("distance", "At 70 studs, player and fence for scale"),),
	]
	W = 1800
	out_rows = []
	for row in rows:
		cw = W // len(row)
		ims = []
		for name, label in row:
			im = Image.open(os.path.join(r, name + ".png")).convert("RGB")
			im = im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS)
			d = ImageDraw.Draw(im)
			d.rectangle((0, 0, min(cw, 16 + d.textlength(label, font=font)), 30), fill=(38, 30, 44))
			d.text((8, 3), label, fill=(240, 230, 210), font=font)
			ims.append(im)
		h = max(i.height for i in ims)
		canvas = Image.new("RGB", (W, h), (38, 30, 44))
		for i, im in enumerate(ims):
			canvas.paste(im, (i * cw, 0))
		out_rows.append(canvas)
	total = Image.new("RGB", (W, sum(c.height for c in out_rows)))
	y = 0
	for c in out_rows:
		total.paste(c, (0, y))
		y += c.height
	total.save(os.path.join(OUT, "compare_sheet.jpg"), quality=92)
	print("wrote", os.path.join(OUT, "compare_sheet.jpg"), total.size)


os.makedirs(OUT, exist_ok=True)
if "--sheet" in sys.argv:
	compare_sheet()
else:
	build()
