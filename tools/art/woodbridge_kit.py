"""Wooden bridges (docs/style/art-style.md), system Python: an arched footbridge, a flat trestle, a short plank crossing and a broken trestle, on one painted 1024 sheet.
Paint and parts come from the props kit (tools/art/props_kit.py, loaded without running its build), so the wood matches the props and the fence. Every part is checked closed and outward wound.
Origin of each bridge: the middle of its span, at bank level (y=0). x runs along the bridge, z across. Studs; the player is 5.2 tall.

  python tools/art/woodbridge_kit.py art/kit/woodbridge           parts, Woodbridge_Color_Raw.png, Woodbridge_Color.png, OBJs, kit.json
  python tools/art/woodbridge_kit.py art/kit/woodbridge --sheet   only the comparison sheet from the Blender renders
"""
import json
import math
import os
import sys
from contextlib import contextmanager

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

from crisp_paint import brushed_wash, chisel_marks, hewn_plane, jagged

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/woodbridge")
PROPS_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "props_kit.py")


def load_props():
	src = open(PROPS_PY, encoding="utf-8").read()
	ns = {"__name__": "props_painter", "__file__": PROPS_PY}
	exec(compile(src[: src.rindex("os.makedirs(OUT, exist_ok=True)")], PROPS_PY, "exec"), ns)
	return ns


PR = load_props()
SHEET, T, Strip, Tile, Piece, Skyline = PR["SHEET"], PR["T"], PR["Strip"], PR["Tile"], PR["Piece"], PR["Skyline"]
bar_raw, unit, write_obj, finish_sheet = PR["bar"], PR["unit"], PR["write_obj"], PR["finish_sheet"]
IRON, PANEL, BOARD = PR["IRON"], PR["PANEL"], PR["BOARD"]

RAIL_H = 3.3  # top of the rail above the deck: chest height on the 5.2-stud player
PLANK_T = 0.34
STRINGER_H = 1.2
STRINGER_L, PILE_L, BRACE_L, RAIL_L, PLANK_L, MID_L = 13.0, 10.5, 13.0, 7.0, 9.2, 7.0  # strip lengths, in studs: what fits the sheet. Struts fit the brace strip now, so nothing stretches
GRAIN_REF = 5.0  # paint_strip sizes its marks as fractions of the strip. Past this many studs they stay the size they'd be at this length, so a long beam isn't a short one stretched
HI_HALF = 1.3  # tapered highlights: half width at the swell, in sheet pixels
HI_GAIN, HI_ADD = np.array((1.42, 1.36, 1.22)), np.array((8, 6, 2), float)  # lightens the wood under it rather than painting one pale colour, so dark wood gets a quieter highlight
HI_RNG = np.random.default_rng(11)
DARK = {"BASE": (84, 58, 52), "LIGHT": (94, 65, 56), "WARM": (92, 62, 52), "DUSK": (72, 51, 50), "COOL": (74, 56, 56), "GRAIN": (50, 34, 37)}  # stained timber: posts, beams, struts, piles
BLACK_IRON = {"BASE": (62, 55, 66), "LIGHT": (72, 64, 74), "WARM": (68, 58, 64), "DUSK": (52, 47, 60), "COOL": (56, 55, 72), "GRAIN": (40, 35, 48)}
# slate for the footings: the stone bridge's method, darker and greyer than its pale walls, so it frames the wood. Painted to its final colour: stone needs less of the wood's lift
STONE = {"BASE": (126, 122, 128), "LIGHT": (152, 146, 144), "WARM": (142, 128, 116), "DUSK": (98, 95, 112), "COOL": (106, 112, 130)}
STONE_GRADE = np.array((1.0, 0.985, 0.92))
STONE_SHADOW = np.array((76, 70, 104), float)
STONE_WET = np.array((84, 92, 112), float)
ALGAE = np.array((88, 132, 112), float)
MOSS = np.array((118, 168, 84), float)
STONE_L = 4.6
WET_LINE = 0.51  # along the pile strip: below this the wood has been in the water
LANE = 0.1  # how much lighter feet have worn the middle of the deck


class Path:
	"""a deck line through the side view: y as a function of x, walked by arc length"""

	def __init__(self, fn, x0, x1):
		self.xs = np.linspace(x0, x1, 400)
		self.ys = np.array([fn(x) for x in self.xs])
		self.len = np.concatenate(([0], np.cumsum(np.hypot(np.diff(self.xs), np.diff(self.ys)))))
		self.total = float(self.len[-1])

	def at(self, s):
		"""position (x, y) and upward normal (nx, ny) at arc length s. Past either end it carries straight on."""
		over_end = s - np.clip(s, 0.06, self.total - 0.06)
		s = s - over_end
		x, y = float(np.interp(s, self.len, self.xs)), float(np.interp(s, self.len, self.ys))
		e = 0.05
		x2, y2 = float(np.interp(s + e, self.len, self.xs)), float(np.interp(s + e, self.len, self.ys))
		x1, y1 = float(np.interp(s - e, self.len, self.xs)), float(np.interp(s - e, self.len, self.ys))
		t = np.array((x2 - x1, y2 - y1))
		t = t / np.linalg.norm(t)
		return x + t[0] * over_end, y + t[1] * over_end, -t[1], t[0]

	def s_of(self, x):
		return float(np.interp(x, self.xs, self.len))

	def y_of(self, x):
		return float(np.interp(x, self.xs, self.ys))

	def line(self, s0, s1, n, off, z):
		"""points along the path, off along its normal, at z"""
		out = []
		for s in np.linspace(s0, s1, n):
			x, y, nx, ny = self.at(s)
			out.append((x + nx * off, y + ny * off, z))
		return np.array(out)


def sweep(strip, end, pts, w, h, front, rng, bend=0.02, jitter=0.012, ch=None, box=False, u=None, tile=False, name="sweep"):
	"""a beam following a line of points: props_kit.beam's section and uv, bent. Runs so its strip's top band faces up, wherever the line goes."""
	pts = np.array(pts, float)
	front = np.array(front, float)
	ax0 = unit(pts[-1] - pts[0])
	if np.cross(unit(front - ax0 * np.dot(front, ax0)), ax0)[1] < 0:
		pts = pts[::-1]
	R = len(pts)
	seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
	arc = np.concatenate(([0], np.cumsum(seg)))
	u = u or (0.0, min(1.0, arc[-1] / (strip.L / T)))
	frac = arc / arc[-1]
	ch = strip.ch if ch is None else ch
	if box:
		sec = [(-w / 2, h / 2), (w / 2, h / 2), (w / 2, -h / 2), (-w / 2, -h / 2)]
		v_rows = [(0, strip.mids[0]), (strip.mids[0], strip.mids[1]), (strip.mids[1], strip.mids[2]), (strip.mids[2], strip.mids[3])]
	else:
		sec = [(-w / 2 + ch, h / 2), (w / 2 - ch, h / 2), (w / 2, h / 2 - ch), (w / 2, -h / 2 + ch), (w / 2 - ch, -h / 2), (-w / 2 + ch, -h / 2), (-w / 2, -h / 2 + ch), (-w / 2, h / 2 - ch)]
		v_rows = [(strip.rows[k], strip.rows[k + 1]) for k in range(8)]
	K = len(sec)
	wob = rng.normal(0, 1, (R, 2)) * bend
	wob[0] *= 0.3
	wob[-1] *= 0.3
	ring = []
	for i in range(R):
		ax = unit(pts[min(i + 1, R - 1)] - pts[max(i - 1, 0)])
		az = unit(front - ax * np.dot(front, ax))
		ay = np.cross(az, ax)
		jit = rng.normal(0, jitter, (K, 2))
		ring.append([pts[i] + ay * (b + wob[i, 0] + jit[k, 0]) + az * (a + wob[i, 1] + jit[k, 1]) for k, (a, b) in enumerate(sec)])
	p = Piece(name)
	for i in range(R - 1):
		# tile: each segment runs the whole strip, for paint that repeats (rope)
		u0, u1 = (0.0, 1.0) if tile else (u[0] + (u[1] - u[0]) * frac[i], u[0] + (u[1] - u[0]) * frac[i + 1])
		for k in range(K):
			a, b, c, d = ring[i][k], ring[i + 1][k], ring[i + 1][(k + 1) % K], ring[i][(k + 1) % K]
			v0, v1 = v_rows[k]
			p.quad(a, b, c, d, strip.uv(u0, v0), strip.uv(u1, v0), strip.uv(u1, v1), strip.uv(u0, v1), g=(k if box else 0))

	def cap_uv(pt):
		return end.uv(0.5 + 0.48 * pt[1] / h, 0.5 + 0.48 * pt[0] / w)

	for side, r in ((0, ring[0]), (1, ring[-1])):
		for k in range(1, K - 1):
			ids = (0, k, k + 1) if side == 0 else (0, k + 1, k)
			p.tri(r[ids[0]], r[ids[1]], r[ids[2]], cap_uv(sec[ids[0]]), cap_uv(sec[ids[1]]), cap_uv(sec[ids[2]]), None)
	return p.done()


def bar(strip, end, p0, p1, w, h, front=(0, 0, 1), **kw):
	"""props_kit.bar, but a beam lying along the bridge always has its strip's top band up, whichever way it was drawn"""
	p0, p1 = np.array(p0, float), np.array(p1, float)
	ax = unit(p1 - p0)
	if abs(ax[1]) < 0.7 and np.cross(unit(np.array(front, float) - ax * np.dot(front, ax)), ax)[1] < 0:
		p0, p1 = p1, p0
	return bar_raw(strip, end, p0, p1, w, h, front=front, **kw)


def deck_paint(lane=True):
	"""a post-paint hook for deck planks. The face looking up takes the top light, with the middle worn paler by feet and the long edges darker where the gaps are."""

	def post(img, strip):
		SS = PR["PAINTER"]["SS"]
		H, L, _ = img.shape
		rows = np.cumsum([0] + [b[0] for b in strip.bands])
		y0, y1 = int(rows[2]) * SS, int(rows[3]) * SS
		face = img[y0:y1]
		t = (np.arange(y1 - y0) + 0.5) / (y1 - y0)
		gap = np.minimum(t, 1 - t) / 0.13
		face = face * PR["TOP_TINT"]
		face = PR["PAINTER"]["over"](face, PR["PAINTER"]["SHADOW"], (np.clip(1 - gap, 0, 1) ** 1.5 * 0.42)[:, None])
		if lane:
			u = (np.arange(L) + 0.5) / L
			wear = np.exp(-(((u - 0.5) / 0.2) ** 2)) * LANE
			face = face * (1 + wear[None, :, None])
		img[y0:y1] = face
		return img

	return post


def wet_foot(img, strip):
	"""piles: darker below the waterline, with a hand-cut edge. The water is what paints it."""
	P = PR["PAINTER"]
	SS = P["SS"]
	H, L, _ = img.shape
	edge = np.interp(np.arange(H), np.linspace(0, H, 9), WET_LINE + np.random.default_rng(3).uniform(-0.012, 0.012, 9)) * L
	xx = np.arange(L)[None, :]
	m = gaussian_filter(((xx < edge[:, None]) * 1.0).astype(np.float32), 0.5 * SS)
	return P["over"](img, P["SHADOW"] * 0.95, m * 0.5)


@contextmanager
def fixed_grain(P):
	"""paint_strip with its marks sized in studs on long strips, by wrapping the two functions it draws them with. The fence's own painter is untouched."""
	real_lines, real_stroke = P["paint_lines"], P["stroke"]
	stud = P["SS"] * T

	def lines(shape, count, length, half, rng, wander, xspan=(-0.1, 0.6)):
		k = max(1.0, shape[1] / (GRAIN_REF * stud))
		if k > 1:
			xspan = (-0.04, 0.98)
		return real_lines(shape, int(round(count * k)), (length[0] / k, length[1] / k), half, rng, wander, xspan)

	def stroke(m, x0, x1, y, half, colour, rng, **kw):
		H, L = m.shape[:2]
		k = max(1.0, L / (GRAIN_REF * stud))
		for _ in range(int(round(k))):
			a = rng.uniform(-0.08, 0.95) * L if k > 1 else x0
			real_stroke(m, a, a + (x1 - x0) / k, rng.uniform(0, H) if k > 1 else y, half, colour, rng, **kw)

	P["paint_lines"], P["stroke"] = lines, stroke
	yield
	P["paint_lines"], P["stroke"] = real_lines, real_stroke


def highlights(img, rows, edges, level, window, gaps, lengths):
	"""short strokes that swell and thin and wander a little, instead of one ruled line. Only on the edges asked for, and only in the window along the strip."""
	if not edges or level <= 0:
		return img
	SS = PR["PAINTER"]["SS"]
	stud = T * SS
	H, L = img.shape[:2]
	m = np.zeros((H, L), np.float32)
	for e in edges:
		cy = (rows[e] + rows[e + 1]) / 2
		x = HI_RNG.uniform(window[0], window[0] + 0.1 * (window[1] - window[0])) * L
		while x < window[1] * L:
			n = int(min(HI_RNG.uniform(*lengths) * stud, window[1] * L - x))
			if n > 0.4 * stud:
				t = (np.arange(n) + 0.5) / n
				half = HI_HALF * SS * np.sin(np.pi * t) ** 0.75 * (0.8 + 0.2 * np.sin(t * HI_RNG.uniform(4, 9) + HI_RNG.uniform(0, 6)))
				wob = np.sin(t * HI_RNG.uniform(2, 5) + HI_RNG.uniform(0, 6)) * 0.6 * SS
				y0, y1 = max(int(cy - 4 * SS), 0), min(int(cy + 4 * SS) + 1, H)
				v = np.clip(half[None, :] + 0.5 - np.abs(np.arange(y0, y1)[:, None] - cy - wob[None, :]), 0, 1) * HI_RNG.uniform(0.7, 1)
				xa = int(x)
				m[y0:y1, xa : xa + n] = np.maximum(m[y0:y1, xa : xa + n], v)
			x += n + HI_RNG.uniform(*gaps) * stud
	m = gaussian_filter(m, 0.25 * SS)[..., None] * level
	return img * (1 - m) + np.clip(img * HI_GAIN + HI_ADD, 0, 255) * m


def finish(extra=None, edges=(), level=0.0, window=(0.0, 1.0), gaps=(2.0, 4.0), lengths=(0.9, 2.4)):
	"""a Strip's post-paint hook: its own marks, a change of colour every few studs on long timber, then the highlights"""

	def post(img, strip):
		SS = PR["PAINTER"]["SS"]
		stud = T * SS
		if extra:
			img = extra(img, strip)
		L = img.shape[1]
		if L > 6 * stud:
			knots = int(L / (3.5 * stud)) + 2
			img = img * gaussian_filter(np.interp(np.arange(L), np.linspace(0, L, knots), HI_RNG.uniform(0.98, 1.02, knots)), 1.0 * stud)[None, :, None]
		rows = np.cumsum([0] + [b[0] for b in strip.bands]) * SS
		return highlights(img, rows, edges, level, window, gaps, lengths)

	return post


class StoneStrip:
	"""a block's unrolled sides, shaped as a Strip so props_kit's beam can use it. low: the courses at the waterline, wet and with algae at the foot."""

	def __init__(self, P, sheet, name, length, w, h, ch, rng, low=False):
		pts, kinds = P["beam_section"](w, h, ch)
		perim = [math.dist(pts[i], pts[(i + 1) % 8]) for i in range(8)]
		self.bands = [(max(6, int(round(perim[i] * T))), kinds[i]) for i in range(8)]
		self.H = sum(b[0] for b in self.bands)
		self.L = int(length * T)
		self.x, self.y = sheet.place(self.L, self.H)
		self.ch = ch
		self.rows = [0]
		for b in self.bands:
			self.rows.append(self.rows[-1] + b[0])
		self.mids = [(self.rows[2 * j + 1] + self.rows[2 * j + 2]) / 2 for j in range(4)]
		SS = P["SS"]
		sheet.img[self.y * SS : (self.y + self.H) * SS, self.x * SS : (self.x + self.L) * SS] = paint_stone(P, self.L * SS, self.rows, low, rng)
		self.rect = Rect(self.x, self.y, self.L, self.H)

	def uv(self, f, row):
		return (self.x + f * self.L, self.y + row)


class Rect:
	def __init__(self, x, y, w, h):
		self.x, self.y, self.w, self.h = x, y, w, h


def stone_colour(P, img):
	"""the sheet's wood grade is applied to everything at the end; this undoes it for stone and leaves the stone's own"""
	return img * STONE_GRADE / (P["GRADE"] * PR["STUDIO_LIFT"])


def stone_surface(P, H, L, rng):
	SS = P["SS"]
	c = {k: np.array(v, float) for k, v in STONE.items()}
	img = np.empty((H, L, 3), np.float32)
	img[:] = c["BASE"]
	for colour, n, strength in ((c["LIGHT"], 3, 0.3), (c["WARM"], 2, 0.24), (c["DUSK"], 2, 0.14), (c["COOL"], 2, 0.16)):
		for _ in range(n):
			img = brushed_wash(img, colour, strength, rng, SS)
	# no straight-edged planes: they read as shadows from nowhere. The rng still runs through them, because the bridges' shapes draw from the same stream
	for _ in range(2):
		hewn_plane(img, c["LIGHT"], 0.12, rng, SS)
	return chisel_marks(img, rng, c["DUSK"] * 0.92, c["LIGHT"] * 1.08, SS, 0.45), c


def paint_stone(P, L, rows, low, rng):
	"""the light is painted per side: the top catches it, sides fall away to lavender, the underside is dark. The bands run top, front, bottom, back, with a chamfer between each."""
	SS = P["SS"]
	over = P["over"]
	r = [v * SS for v in rows]
	H = r[-1]
	img, c = stone_surface(P, H, L, rng)
	img[r[0] : r[1]] *= np.array((1.14, 1.12, 1.06), np.float32)
	img[r[4] : r[5]] *= 0.68
	for a, b, down in ((r[2], r[3], True), (r[6], r[7], False)):
		t = (np.arange(b - a) + 0.5) / (b - a)
		t = t if down else 1 - t
		face = over(img[a:b], STONE_SHADOW, (t**1.5 * 0.42)[:, None])
		if low:
			face = over(face, STONE_WET, (np.clip((t - 0.2) / 0.8, 0, 1) * 0.5)[:, None])
			n = jagged(b - a, L, rng, 5 * SS) * 0.05
			face = over(face, ALGAE, np.clip((t[:, None] + n - 0.76) / 0.05, 0, 1) * 0.72)
		else:
			# a thin shape of cast shadow under the chamfer, cut clean
			n = jagged(b - a, L, rng, 5 * SS) * 0.02
			face = over(face, STONE_SHADOW, np.clip((0.07 - t[:, None] + n) / 0.02, 0, 1) * 0.2)
		img[a:b] = face
	if not low:
		# moss only on the top, in a couple of calm patches
		n = jagged(r[1] - r[0], L, rng, 4 * SS) * 0.2
		blob = gaussian_filter(rng.random((r[1] - r[0], L)).astype(np.float32), (10 * SS, 22 * SS))
		blob = (blob - blob.mean()) / blob.std() * 0.25 + 0.5
		img[r[0] : r[1]] = over(img[r[0] : r[1]], MOSS, np.clip((blob + n - 0.82) / 0.05, 0, 1) * 0.85)
	img = np.clip(img + (img - gaussian_filter(img, (1.1 * SS, 1.1 * SS, 0))) * 0.25, 0, 255)
	img = highlights(img, r, (1, 7), 0.75, (0.0, 1.0), (0.8, 1.8), (0.7, 1.7))
	return stone_colour(P, img)


def paint_stone_end(P, n, rng):
	img, _c = stone_surface(P, n, n, rng)
	return stone_colour(P, np.clip(img * 0.92, 0, 255))


class Kit:
	"""the painted strips, and the small parts every bridge is made of"""

	def __init__(self, P, sheet, rng):
		self.rng = rng
		nails = ((0.2, 0.33), (0.2, 0.43), (0.8, 0.33), (0.8, 0.43))
		off = (0, 0, 0, 0)  # props_kit's ruled line: off. Highlights are finish()'s strokes
		# no knots or scratches: planks share these strips and line up down the deck, so one mark repeats as a stripe
		pk = dict(ao_ends=(True, True), grad=None, nails=nails, knots=0, levels=off)
		deck = deck_paint()
		# in this order the packer gets everything on the sheet: found by trying orders
		with fixed_grain(P):
			self.mid_strip = Strip(P, sheet, "mid", MID_L, 0.26, 0.42, 0.0, rng, knots=0, levels=off, grad=None, ao_ends=(False, False), post=finish(edges=(1, 7), level=0.6, gaps=(2.0, 3.5)))
			self.rail = Strip(P, sheet, "rail", RAIL_L, 0.52, 0.56, 0.09, rng, knots=1, levels=off, ao_ends=(False, False), post=finish(edges=(1, 7), level=0.85, gaps=(1.2, 2.6)))
			self.pile = Strip(P, sheet, "pile", PILE_L, 1.1, 1.1, 0.3, rng, foot=True, knots=2, levels=off, grad="along", ao_ends=(False, True), pal=DARK, post=finish(extra=wet_foot, edges=(1, 7), level=0.5, window=(0.56, 0.86)))
			plank_b = Strip(P, sheet, "plankB", PLANK_L, PLANK_T, 1.4, 0.06, rng, pal=PANEL, post=finish(extra=deck), **pk)
			plank_a = Strip(P, sheet, "plankA", PLANK_L, PLANK_T, 1.4, 0.06, rng, post=finish(extra=deck, edges=(1,), level=0.5, gaps=(3.0, 5.0)), **pk)
			self.stone_low = StoneStrip(P, sheet, "stoneLow", STONE_L, 1.7, 1.5, 0.14, rng, low=True)
			self.post = Strip(P, sheet, "post", 5.2, 0.74, 0.74, 0.09, rng, knots=1, levels=off, grad="along", ao_ends=(False, True), pal=DARK, post=finish(edges=(1, 7), level=0.6, window=(0.62, 0.88), lengths=(0.6, 1.0), gaps=(0.5, 1.0)))
			plank_c = Strip(P, sheet, "plankC", PLANK_L, PLANK_T, 1.4, 0.06, rng, pal=BOARD, post=finish(extra=deck, edges=(3,), level=0.35, gaps=(3.0, 5.0)), **pk)
			self.planks = [plank_a, plank_b, plank_c]
			self.end = Tile(sheet, 60, 60)
			self.end.put(P, sheet, P["paint_end"](60, rng))
			self.brace = Strip(P, sheet, "brace", BRACE_L, 0.5, 0.64, 0.0, rng, knots=2, levels=off, grad=None, ao_ends=(False, False), pal=DARK, post=finish(edges=(1, 7), level=0.55))
			self.dend = Tile(sheet, 60, 60)
			with PR["palette"](P, DARK):
				self.dend.put(P, sheet, P["paint_end"](60, rng))
			self.send = Tile(sheet, 60, 60)
			self.send.put(P, sheet, paint_stone_end(P, 60 * P["SS"], rng))
			self.stone = StoneStrip(P, sheet, "stone", STONE_L, 1.7, 1.5, 0.14, rng)
			self.strap_strip = Strip(P, sheet, "strap", 1.0, 0.86, 1.38, 0.0, rng, knots=0, levels=off, grad=None, ao_ends=(False, False), pal=BLACK_IRON, nails=((0.5, 0.2), (0.5, 0.7)))
			self.stringer = Strip(P, sheet, "stringer", STRINGER_L, 0.7, STRINGER_H, 0.1, rng, knots=3, levels=off, ao_ends=(False, False), pal=DARK, post=finish(edges=(1, 7), level=0.6))
		self.stone_rects = [self.stone.rect, self.stone_low.rect, Rect(self.send.x, self.send.y, 60, 60)]

	def block(self, x, y, z, sx, sy, sz, low=False, yaw=0.0, tilt=0.0, roll=0.0):
		"""one chunky stone, centred on (x, y, z), a little off true. The strip's top band stays on top."""
		rng = self.rng
		strip = self.stone_low if low else self.stone
		L, w, along_x = (sx, sz, True) if sx >= sz else (sz, sx, False)
		u0 = rng.uniform(0, max(0.001, 1 - L / STONE_L))
		a, b = ((-L / 2, 0, 0), (L / 2, 0, 0)) if along_x else ((0, 0, -L / 2), (0, 0, L / 2))
		front = (0, 0, 1) if along_x else (1, 0, 0)
		part = bar(strip, self.send, a, b, w, sy, front=front, bend=0.03, jitter=0.035, tip=0.05, rng=rng, u=(u0, u0 + min(1, L / STONE_L)), name="Stone")
		M = PR["ry"](yaw + rng.uniform(-1.5, 1.5)) @ PR["rz"](tilt) @ PR["rx"](roll)
		return part.moved((x, y, z), M)

	def wall(self, x_face, sign, half, courses):
		"""courses of stone across the bridge's end, laid in a running bond. courses: (bottom y, height, depth, wet), with the face at x_face looking toward the water."""
		rng = self.rng
		parts = []
		for i, (y0, h, depth, face_at, low) in enumerate(courses):
			z = -half - (0 if i % 2 == 0 else rng.uniform(0.6, 1.2))
			while z < half:
				wd = rng.uniform(2.3, 3.9)
				if half - (z + wd) < 1.1:
					wd = max(half - z, 1.2)
				dp = depth + rng.uniform(-0.12, 0.12)
				parts.append(self.block(sign * (face_at + dp / 2) + rng.uniform(-0.05, 0.05), y0 + h / 2, z + wd / 2, dp, h - 0.04, wd - 0.05, low=low))
				z += wd
		return parts

	def gate_stones(self, x, half, y0, top):
		"""two stacked stones standing either side of the deck at the bank: the bit of stone you see from the road"""
		rng = self.rng
		parts = []
		for sign in (-1, 1):
			for side in (-1, 1):
				z = side * half
				cx = sign * x + rng.uniform(-0.1, 0.1)
				mid = y0 + (top - y0) * rng.uniform(0.56, 0.64)
				parts.append(self.block(cx, (y0 + mid) / 2, z, 2.4, mid - y0, 2.2, yaw=rng.uniform(-5, 5)))
				parts.append(self.block(cx + rng.uniform(-0.1, 0.1), (mid + top) / 2 - 0.02, z + rng.uniform(-0.1, 0.1), 1.9, top - mid, 1.75, yaw=rng.uniform(-9, 9)))
		return parts

	def pier(self, x, z, water=-6.0):
		"""a pile's foot: a wet stone at the waterline, a smaller dry one sitting on it"""
		rng = self.rng
		return [
			self.block(x + rng.uniform(-0.15, 0.15), water + 0.0, z, 3.0, 1.8, 2.8, low=True, yaw=rng.uniform(-10, 10)),
			self.block(x + rng.uniform(-0.1, 0.1), water + 1.3, z, 2.1, 0.9, 2.0, yaw=rng.uniform(-14, 14)),
		]

	def rail_band(self, path, x, z, side):
		"""dark iron round the top rail where it meets a post"""
		s0 = path.s_of(x)
		return sweep(self.strap_strip, self.end, path.line(s0 - 0.27, s0 + 0.27, 2, RAIL_H, z), 0.62, 0.68, (0, 0, side), self.rng, bend=0.0, jitter=0.0, box=True, u=(0.05, 0.95), name="RailBand")

	def plank(self, x, y, nx, ny, W, width=None, skew=0.12, length=None, name="Plank"):
		"""one deck plank across the bridge: its top face on the path at (x, y)"""
		rng = self.rng
		strip = self.planks[int(rng.choice(3, p=(0.5, 0.25, 0.25)))]
		wd = width or rng.uniform(1.26, 1.5)
		Lp = length or W + rng.uniform(-0.25, 0.7)
		off = rng.uniform(-0.2, 0.2)
		cx, cy = x - nx * PLANK_T / 2, y - ny * PLANK_T / 2
		dx, dy = rng.uniform(-skew, skew), rng.uniform(-0.035, 0.035)
		a, b = (cx - dx, cy - dy, off - Lp / 2), (cx + dx, cy + dy, off + Lp / 2)
		if rng.random() < 0.5:
			a, b = b, a
		u0 = 0.5 - Lp / 2 / PLANK_L + rng.uniform(-0.02, 0.02)
		return bar_raw(strip, self.end, a, b, PLANK_T, wd, front=(nx, ny, 0), bend=0.012, rng=rng, u=(u0, u0 + Lp / PLANK_L), name=name)

	def deck(self, path, W, s0=0.25, s1=None, keep=None):
		"""planks along the path, a little uneven. keep(x) leaves gaps."""
		rng = self.rng
		out = []
		s, s1 = s0, s1 or path.total - 0.25
		while s < s1:
			wd = rng.uniform(1.26, 1.5)
			x, y, nx, ny = path.at(s + wd / 2)
			if keep is None or keep(x):
				out.append(self.plank(x, y, nx, ny, W, wd))
			s += wd + rng.uniform(0.06, 0.16)
		return out

	def stringer_run(self, path, z, s0, s1, n=5, off=None, front=(0, 0, 1), name="Stringer"):
		off = off if off is not None else -PLANK_T - STRINGER_H / 2
		return sweep(self.stringer, self.dend, path.line(s0, s1, n, off, z), 0.7, STRINGER_H, front, self.rng, name=name)

	def posts_and_rails(self, path, W, xs, sides=(-1, 1), mid=True, skip=()):
		"""posts at xs on each side, with a top rail on them and a thin mid rail lapped on the inside. Rail lengths meet at posts, as they would be built."""
		rng = self.rng
		parts = []
		for side in sides:
			z = side * (W / 2 + 0.22)
			for i, x in enumerate(xs):
				y = path.y_of(x)
				lean = rng.uniform(-0.05, 0.05)
				if i % 2 == 0:
					parts.append(self.rail_band(path, x, z, side))
				parts.append(bar_raw(self.post, self.dend, (x, y - PLANK_T - 1.15, z), (x + lean, y + RAIL_H - 0.18, z + side * rng.uniform(0, 0.07)), 0.74, 0.74, w1=0.66, h1=0.66, front=(0, 0, side), bend=0.015, rng=rng, u=(0, (RAIL_H + PLANK_T + 1) / 5.2), tip=0.06, name="Post"))
			for a, b in zip(xs, xs[1:]):
				if (side, a) in skip:
					continue
				sa, sb = path.s_of(a) - 0.22, path.s_of(b) + 0.22
				n = max(2, int(abs(sb - sa) / 3.6) + 1)
				top = path.line(sa, sb, n, RAIL_H, z)
				parts.append(sweep(self.rail, self.end, top, 0.52, 0.56, (0, 0, side), rng, bend=0.025, name="TopRail"))
				if mid:
					low = path.line(sa + 0.1, sb - 0.1, n, 1.72, z - side * 0.46)
					parts.append(sweep(self.mid_strip, self.end, low, 0.26, 0.42, (0, 0, side), rng, bend=0.02, box=True, name="MidRail"))
		return parts

	def strap(self, path, s, z):
		"""an iron band round a joint in a beam"""
		s0, s1 = s - 0.34, s + 0.34
		pts = path.line(s0, s1, 2, -PLANK_T - STRINGER_H / 2, z)
		return sweep(self.strap_strip, self.end, pts, 0.86, 1.38, (0, 0, 1), self.rng, bend=0.0, jitter=0.0, box=True, u=(0.05, 0.95), name="Strap")

	def bent(self, x, top, W, rng_lean=0.25, pile_z=None, brace=True, foot=-11.0):
		"""a trestle frame: two piles leaning in, a cap beam across them, and an X of braces above the water"""
		rng = self.rng
		pz = pile_z or W / 2 - 0.5
		parts = []
		cap_h = 0.9
		pile_top = top - cap_h + 0.2
		strip_u = min(1.0, (pile_top - foot) / PILE_L)
		for side in (-1, 1):
			parts.append(bar_raw(self.pile, self.dend, (x + rng.uniform(-rng_lean, rng_lean), foot, side * (pz + 0.65)), (x + rng.uniform(-0.1, 0.1), pile_top, side * pz), 1.1, 1.1, front=(0, 0, side), rings=3, bend=0.05, rng=rng, u=(0, strip_u), name="Pile"))
		parts.append(bar(self.stringer, self.dend, (x + 0.05, top - cap_h / 2, -pz - 1.1), (x - 0.05, top - cap_h / 2 + rng.uniform(-0.06, 0.06), pz + 1.1), 0.9, cap_h, front=(1, 0, 0), bend=0.02, rng=rng, u=(0.1, 0.1 + (2 * pz + 2.2) / STRINGER_L), name="Cap"))
		if brace:
			y0, y1 = top - cap_h - 0.15, top - cap_h - 0.15 - 2 * pz * 0.5
			parts.append(bar(self.brace, self.dend, (x + 0.72, y0, -pz - 0.3), (x + 0.72, y1, pz + 0.55), 0.3, 0.6, front=(1, 0, 0), box=True, bend=0.02, rng=rng, u=(0.02, 0.02 + 2.3 * pz / BRACE_L), name="Brace"))
			parts.append(bar(self.brace, self.dend, (x - 0.72, y1, -pz - 0.55), (x - 0.72, y0, pz + 0.3), 0.3, 0.6, front=(-1, 0, 0), box=True, bend=0.02, rng=rng, u=(0.25, 0.25 + 2.3 * pz / BRACE_L), name="Brace"))
		return parts


# ---------------------------------------------------------------- the bridges


def arched(k):
	"""a humpbacked footbridge: curved beams under a stepped deck, propped from the banks by a fan of struts"""
	rng = k.rng
	W, RISE, HALF = 7.0, 4.6, 16.0
	R = (HALF**2 + RISE**2) / (2 * RISE)
	path = Path(lambda x: math.sqrt(R * R - x * x) - (R - RISE), -17.6, 17.6)
	top = lambda x: path.y_of(x)
	mid = path.s_of(0)
	parts = k.deck(path, W, s0=path.s_of(-16.7), s1=path.s_of(16.7))
	# each side three lengths of beam, lapped under iron bands: no single timber spans the river
	joints = (path.s_of(-5.6), path.s_of(5.8))
	for z in (-W / 2 + 0.95, W / 2 - 0.95):
		parts.append(k.stringer_run(path, z, 0.1, joints[0] + 0.7, n=5))
		parts.append(k.stringer_run(path, z + 0.1, joints[0] - 0.7, joints[1] + 0.7, n=5))
		parts.append(k.stringer_run(path, z, joints[1] - 0.7, path.total - 0.1, n=5))
		for j in joints:
			parts.append(k.strap(path, j, z))
	# the struts: from a stone ledge up to the beams, fanning out at the top
	LEDGE = -2.9
	for sign in (-1, 1):
		foot = (sign * 14.7, LEDGE + 0.15)
		for x in (6.0, 10.6):
			y = top(sign * x) - PLANK_T - STRINGER_H + 0.1
			for z in (-W / 2 + 0.95, W / 2 - 0.95):
				parts.append(bar(k.brace, k.dend, (foot[0], foot[1], z + 0.06), (sign * x, y, z - 0.03), 0.5, 0.64, front=(0, 0, 1 if z > 0 else -1), box=True, bend=0.025, rng=rng, u=(0.02, min(1, math.hypot(foot[0] - sign * x, foot[1] - y) / BRACE_L)), name="Strut"))
		# ties across, holding the two sides together where the struts land
		for x in (6.0, 10.6):
			y = top(sign * x) - PLANK_T - STRINGER_H - 0.25
			parts.append(bar(k.brace, k.dend, (sign * x, y, -W / 2 + 0.3), (sign * x + 0.08, y + 0.04, W / 2 - 0.3), 0.5, 0.64, front=(0, 1, 0), box=True, bend=0.015, rng=rng, u=(0.3, 0.3 + (W - 0.6) / BRACE_L), name="Tie"))
		# the sill the bridge sits on, bedded on the top course
		parts.append(bar(k.stringer, k.dend, (sign * 16.2, -0.55, -W / 2 - 1.5), (sign * 16.3, -0.5, W / 2 + 1.5), 1.1, 1.3, front=(0, 1, 0), bend=0.025, rng=rng, u=(0.1, 0.1 + (W + 3) / STRINGER_L), name="Sill"))
		parts += k.wall(14.0, sign, W / 2 + 2.0, ((-6.6, 1.9, 3.2, 14.0, True), (-4.7, 1.8, 3.0, 14.0, False), (-2.9, 1.8, 2.6, 14.9, False)))
	parts += k.gate_stones(17.3, W / 2 + 1.25, -0.6, 1.7)
	parts += k.posts_and_rails(path, W, (-16.4, -11, -5.4, 0.2, 5.6, 11.2, 16.4))
	return parts


def flat(k):
	"""a plain trestle on two frames: rails both sides, a little sag between them"""
	rng = k.rng
	W, HALF = 8.0, 13.5
	path = Path(lambda x: -0.2 * (1 - (x / HALF) ** 2) + 0.05 * math.sin(x * 0.7), -HALF, HALF)
	parts = k.deck(path, W)
	cap = -PLANK_T - STRINGER_H
	xs = (-6.2, 6.4)
	for x in xs:
		parts += k.bent(x, path.y_of(x) + cap + 0.05, W)
		for side in (-1, 1):
			parts += k.pier(x, side * (W / 2 + 0.15))
	for z in (-W / 2 + 1.0, 0.1, W / 2 - 1.0):
		a, b = path.s_of(xs[0]), path.s_of(xs[1])
		parts.append(k.stringer_run(path, z, 0.05, a + 0.6, n=3))
		parts.append(k.stringer_run(path, z + 0.1, a - 0.6, b + 0.6, n=4))
		parts.append(k.stringer_run(path, z, b - 0.6, path.total - 0.05, n=3))
	for sign in (-1, 1):
		parts.append(bar(k.stringer, k.dend, (sign * 12.9, -0.72, -W / 2 - 1.3), (sign * 13.0, -0.68, W / 2 + 1.3), 1.0, 1.2, front=(0, 1, 0), bend=0.025, rng=rng, u=(0.1, 0.1 + (W + 2.6) / STRINGER_L), name="Sill"))
		parts += k.wall(11.5, sign, W / 2 + 1.6, ((-6.6, 1.9, 2.9, 11.5, True), (-4.7, 1.7, 2.7, 11.5, False), (-3.0, 1.75, 2.5, 11.7, False)))
	parts += k.gate_stones(14.4, W / 2 + 1.25, -0.6, 1.6)
	parts += k.posts_and_rails(path, W, (-13.1, -6.5, -0.1, 6.6, 13.1))
	return parts


def plank_crossing(k):
	"""the quick way over a stream: two logs and whatever planks were to hand. No rails. One plank gone, one knocked askew."""
	rng = k.rng
	W, HALF = 6.2, 8.2
	path = Path(lambda x: 0.72 - 0.26 * (1 - (x / HALF) ** 2), -HALF, HALF)
	missing = 2.4
	parts = k.deck(path, W, keep=lambda x: abs(x - missing) > 0.72)
	for z, dip in ((-1.9, 0.0), (1.85, 0.05)):
		pts = [(x + (0 if abs(x) == HALF else rng.uniform(-0.05, 0.05)), path.y_of(x) - PLANK_T - 0.5 - dip, z + rng.uniform(-0.08, 0.08)) for x in np.linspace(-HALF - 0.7, HALF + 0.7, 5)]
		parts.append(sweep(k.stringer, k.dend, pts, 1.0, 1.0, (0, 0, 1 if z > 0 else -1), rng, bend=0.04, ch=0.27, name="Log"))
	x, y, nx, ny = path.at(path.s_of(-3.0))
	parts.append(k.plank(x, y + 0.2, nx, ny, W + 0.3, 1.34, skew=0.7, length=W + 1.2, name="Askew"))
	for sign in (-1, 1):
		parts += k.wall(6.1, sign, W / 2 + 0.4, ((-3.5, 1.55, 2.7, 6.1, True), (-1.95, 1.42, 2.4, 6.3, False)))
	return parts


def broken(k):
	"""the flat trestle after a bad winter: one frame gone over and the deck open for a jump. One rail still hangs across the gap."""
	rng = k.rng
	W, HALF = 8.0, 13.5
	path = Path(lambda x: -0.18 * (1 - (x / HALF) ** 2) + 0.05 * math.sin(x * 0.9 + 1), -HALF, HALF)
	G0, G1 = 1.6, 8.0  # the open stretch of deck
	parts = k.deck(path, W, keep=lambda x: not (G0 < x < G1))
	cap = -PLANK_T - STRINGER_H
	parts += k.bent(-6.2, path.y_of(-6.2) + cap + 0.05, W)
	for side in (-1, 1):
		parts += k.pier(-6.2, side * (W / 2 + 0.15))
	# the far frame's footings: one still sitting, the other knocked apart in the water
	parts += k.pier(6.6, -(W / 2 + 0.2))
	parts += [
		k.block(5.6, -6.1, W / 2 + 0.5, 2.8, 1.7, 2.5, low=True, yaw=24, tilt=9, roll=-7),
		k.block(9.1, -5.7, W / 2 - 1.2, 2.0, 1.1, 1.7, yaw=-31, tilt=-16, roll=11),
		k.block(3.0, -6.0, -1.0, 2.2, 1.2, 1.8, low=True, yaw=48, tilt=6, roll=12),
	]
	# the far frame has gone over: both piles lean hard, the cap has slid off one
	fx = 6.8
	for side, lean, top_y, u1 in ((-1, 3.2, -4.2, 0.66), (1, 2.5, -5.1, 0.58)):
		parts.append(bar_raw(k.pile, k.dend, (fx - 0.4, -11, side * 4.2), (fx + lean, top_y, side * 3.5), 1.1, 1.1, front=(0, 0, side), rings=3, bend=0.06, rng=rng, u=(0, u1), tip=0.32, name="LeaningPile"))
	parts.append(bar(k.stringer, k.dend, (fx + 2.4, -4.15, -4.6), (fx + 1.4, -6.5, 3.8), 0.9, 0.9, front=(1, 0.2, 0), bend=0.02, rng=rng, u=(0.1, 0.1 + 8.8 / STRINGER_L), name="SlidCap"))
	# near beams end in splinters, far beams still rest on the bank and dip into the water
	for z, reach in ((-W / 2 + 1.0, 2.2), (0.1, 1.2), (W / 2 - 1.0, 3.0)):
		parts.append(k.stringer_run(path, z, 0.05, path.s_of(reach), n=4))
	for z, end_pt in ((-W / 2 + 1.0, (6.4, -3.4)), (W / 2 - 1.0, (5.9, -5.4))):
		x0 = HALF - 0.05
		y0 = path.y_of(x0) - PLANK_T - STRINGER_H / 2
		parts.append(sweep(k.stringer, k.dend, [(x0, y0, z), (9.4, y0 - 0.1, z + 0.06), (end_pt[0], end_pt[1], z + 0.2)], 0.7, STRINGER_H, (0, 0, 1), rng, name="FallenBeam"))
	parts.append(k.stringer_run(path, 0.1, path.s_of(8.4), path.total - 0.05, n=3))
	for sign in (-1, 1):
		parts.append(bar(k.stringer, k.dend, (sign * 12.9, -0.72, -W / 2 - 1.3), (sign * 13.0, -0.68, W / 2 + 1.3), 1.0, 1.2, front=(0, 1, 0), bend=0.025, rng=rng, u=(0.1, 0.1 + (W + 2.6) / STRINGER_L), name="Sill"))
		parts += k.wall(11.5, sign, W / 2 + 1.6, ((-6.6, 1.9, 2.9, 11.5, True), (-4.7, 1.7, 2.7, 11.5, False), (-3.0, 1.75, 2.5, 11.7, False)))
	parts += k.gate_stones(14.4, W / 2 + 1.25, -0.6, 1.6)
	# loose planks at the lip of the gap, and two going down
	x, y, nx, ny = path.at(path.s_of(G0 + 0.55))
	parts.append(k.plank(x + 0.2, y - 0.5, nx + 0.22, ny - 0.03, W - 2.4, 1.32, skew=0.5, length=4.6, name="Hanging"))
	x, y, nx, ny = path.at(path.s_of(G1 - 0.5))
	parts.append(k.plank(x - 0.2, y - 0.6, nx - 0.3, ny - 0.05, W - 2, 1.32, skew=0.4, length=5.2, name="Hanging"))
	parts.append(bar_raw(k.planks[0], k.end, (3.2, -5.8, -2.2), (5.6, -2.5, 3.1), PLANK_T, 1.3, front=(0.5, 0.75, -0.3), bend=0.015, rng=rng, u=(0.1, 0.72), name="Falling"))
	# rails: the near side whole but for the span over the gap, the far side's top rail sagging across it
	near = (-13.1, -6.5, -0.1)
	far = (8.8, 13.1)
	parts += k.posts_and_rails(path, W, near)
	parts += k.posts_and_rails(path, W, far)
	sag = lambda t: path.y_of(-0.1) * (1 - t) + path.y_of(8.8) * t + RAIL_H - 2.5 * math.sin(math.pi * t)
	z = -W / 2 - 0.22
	for t0, t1 in ((0, 0.53), (0.49, 1)):
		parts.append(sweep(k.rail, k.end, [(-0.6 + 9.9 * t, sag(t), z + 0.1 * math.sin(t * 7)) for t in np.linspace(t0, t1, 3)], 0.52, 0.56, (0, 0, -1), rng, bend=0.03, name="SaggingRail"))
	# the other rail snapped and hangs off its post
	zb = W / 2 + 0.22
	yb = path.y_of(-0.1) + RAIL_H
	parts.append(bar(k.rail, k.end, (-0.6, yb, zb), (3.4, yb - 3.9, zb + 0.6), 0.52, 0.56, front=(0, 0, 1), bend=0.03, rng=rng, u=(0.1, 0.1 + 5.7 / RAIL_L), tip=0.3, name="SnappedRail"))
	return parts


def build():
	P = PR["load_painter"]()
	PR["PAINTER"] = P
	P["SHADOW"] = np.array((70, 48, 70), float)
	rng = np.random.default_rng(23)
	sheet = P["Sheet"]()
	sky = Skyline()
	sheet.place = sky.place
	k = Kit(P, sheet, rng)
	bridges = {"BridgeArched": arched(k), "BridgeFlat": flat(k), "BridgePlank": plank_crossing(k), "BridgeBroken": broken(k)}
	raw = Image.fromarray(np.clip(sheet.img * P["GRADE"] * PR["STUDIO_LIFT"], 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS)
	raw.save(os.path.join(OUT, "Woodbridge_Color_Raw.png"))
	finish_sheet(np.array(raw), k.stone_rects, []).save(os.path.join(OUT, "Woodbridge_Color.png"))
	report = {}
	bounds = {}
	for name, parts in bridges.items():
		report[name] = write_obj(os.path.join(OUT, name + ".obj"), name, parts)
		v = np.array([p for part in parts for t in part.tris for p in t[:3]])
		bounds[name] = [round(float(x), 3) for x in (v[:, 0].min(), v[:, 0].max(), v[:, 1].min(), v[:, 1].max(), v[:, 2].min(), v[:, 2].max())]
	json.dump({"Triangles": report, "Bounds": bounds, "SheetUsedToRow": sky.used()}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print(report, "sheet used to row", sky.used(), "of", SHEET)


def compare_sheet():
	r = os.path.join(OUT, "renders")
	font = ImageFont.truetype("arial.ttf", 22)
	rows = [
		(("hero_arched", "Arched"), ("hero_flat", "Flat trestle")),
		(("hero_plank", "Plank crossing"), ("hero_broken", "Broken trestle")),
		(("side_arched", "Arched from the side, 5.2-stud player"), ("side_flat", "Flat, with the fence on the bank")),
		(("side_plank", "Plank crossing from the side"), ("side_broken", "Broken from the side")),
		(("walk_arched", "Walking up the arch"), ("walk_flat", "Walking the flat deck")),
		(("walk_plank", "Walking the planks"), ("walk_broken", "At the gap")),
		(("under_arched", "From the water, arched"), ("under_flat", "From the water, flat")),
		(("above_arched", "Above and behind, back faces hidden as in Roblox"), ("above_broken", "Same, broken")),
		(("close_wood", "Up close: beam, post and rail"), ("close_stone", "Up close: the footing")),
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
		canvas = Image.new("RGB", (W, max(i.height for i in ims)), (38, 30, 44))
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
