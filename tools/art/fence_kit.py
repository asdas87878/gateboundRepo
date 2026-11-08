"""The fence kit (docs/style/art-style.md), system Python: chunky hand-cut parts and one painted texture sheet, no Blender needed until export.
Parts are chamfered beams unrolled into strips, so the painter knows which texels are faces and which are edges: edges get the bright painted line.
Writes into art/kit/fence: Fence_Color.png (1024), <Section>.obj per section, kit.json.

  python tools/art/fence_kit.py art/kit/fence
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/fence")
os.makedirs(OUT, exist_ok=True)
SHEET = 1024
GRADE = np.array((1.3, 1.27, 1.12))  # was 1.42:  # Roblox lighting took the lit mean to about #613e42 against the lesson's #7a534f (measured in Studio), so the whole sheet is lifted
SS = 2  # painted at twice the size, then shrunk: crisp but not aliased
TEXELS = 50  # per stud
# colours: measured from the lesson's fence (lit mean about #7a534f, edges redder), darks pushed to plum and lights to warm, so nothing is black or grey
BASE = np.array((126, 88, 68), float)
LIGHT = np.array((158, 116, 88), float)
WARM = np.array((152, 102, 70), float)
DUSK = np.array((100, 72, 66), float)
DARK = np.array((74, 54, 56), float)
INK = np.array((48, 30, 44), float)
EDGE = np.array((232, 206, 168), float)
EDGE_PALE = np.array((206, 164, 124), float)
MOSS = np.array((96, 150, 70), float)
PLANE_LIGHT = np.array((138, 90, 78), float)
PLANE_WARM = np.array((136, 80, 66), float)
PLANE_DARK = np.array((106, 66, 60), float)
SHADOW = np.array((72, 54, 58), float)
EDGE_BASE = np.array((126, 66, 54), float)
MOSS_DARK = np.array((66, 112, 70), float)
NAIL = np.array((150, 148, 130), float)
# colour schemes: one family of browns, the paint patches close to the base so the wood reads as one colour. Pick with: fence_kit.py <folder> <scheme>
SCHEMES = {
	"Chestnut": {"BASE": (124, 86, 66), "LIGHT": (133, 93, 71), "WARM": (132, 90, 66), "DUSK": (113, 79, 64), "COOL": (116, 84, 71), "GRAIN": (88, 60, 50)},
	"Weathered": {"BASE": (118, 92, 74), "LIGHT": (127, 100, 81), "WARM": (125, 97, 76), "DUSK": (107, 84, 71), "COOL": (108, 88, 78), "GRAIN": (80, 62, 55)},
	"Honey": {"BASE": (146, 106, 72), "LIGHT": (155, 115, 79), "WARM": (153, 110, 72), "DUSK": (133, 97, 68), "COOL": (135, 103, 78), "GRAIN": (98, 70, 52)},
}
SCHEME = sys.argv[2] if len(sys.argv) > 2 else "Chestnut"  # the user's pick, 2026-11-06
for _key, _value in SCHEMES[SCHEME].items():
	globals()[_key] = np.array(_value, float)
GRAIN_FACE = {"top": 1.14, "front": 1.0, "back": 0.92, "bottom": 0.66}


def ss(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def smooth1d(n, width, rng):
	v = rng.normal(size=n + width * 2)
	v = np.convolve(v, np.ones(width) / width, "same")[width : width + n]
	return v / (np.abs(v).max() + 1e-6)


def stroke(img, x0, x1, y, half, colour, rng, alpha=1.0, wander=0.0, tail=0.6, soft_head=False):
	"""one brush mark along x: a crisp head at x0, bristles drying out toward x1 and a wandering centre line"""
	h, w, _ = img.shape
	if x1 < x0:
		x0, x1 = x1, x0
	xa, xb = max(int(x0), 0), min(int(x1), w)
	if xb - xa < 2:
		return
	L = xb - xa
	centre = y + smooth1d(L, max(L // 5, 3), rng) * wander
	ya, yb = int(max(centre.min() - half - 2, 0)), int(min(centre.max() + half + 3, h))
	if yb <= ya:
		return
	rows = yb - ya
	bristle = np.abs(smooth1d(rows + 8, 2, rng))[:rows]
	t = (np.arange(L) + xa - x0) / max(x1 - x0, 1)
	ys = np.arange(ya, yb)[:, None]
	d = np.abs(ys - centre[None, :]) / max(half, 0.5)
	profile = np.minimum(1, t / 0.04) * (1 - np.clip((t - 0.75) / 0.25, 0, 1) * 0.5)
	mask = d < profile
	# dry tail: each bristle stops at its own length
	mask &= t[None, :] < 1 - tail * bristle[:, None]
	img[ya:yb, xa:xb][mask] = img[ya:yb, xa:xb][mask] * (1 - alpha) + colour * alpha


def grain(img, x0, x1, y, half, colour, rng, wander):
	"""a thin line with no bristles: tapered at both ends, gently curving"""
	h, w, _ = img.shape
	xa, xb = max(int(x0), 0), min(int(x1), w)
	if xb - xa < 4:
		return
	L = xb - xa
	centre = y + np.cumsum(smooth1d(L, max(L // 3, 5), rng)) / max(L, 1) * wander * 3
	t = np.arange(L) / L
	width = half * np.minimum(1, np.minimum(t, 1 - t) * 8) + 0.2
	rows = np.arange(h)[:, None]
	mask = np.abs(rows - centre[None, :]) < width[None, :]
	img[:, xa:xb][mask] = colour


def scatter_colour(c, rng, amount=8):
	return c + rng.normal(0, amount, 3) * np.array((1, 0.8, 0.8))


class Sheet:
	def __init__(self):
		self.img = np.zeros((SHEET * SS, SHEET * SS, 3), float)
		self.img[:] = BASE
		self.x = 8
		self.y = 8
		self.row = 0

	def place(self, w, h):
		if self.x + w + 8 > SHEET:
			self.x, self.y, self.row = 8, self.y + self.row + 8, 0
		if self.y + h + 8 > SHEET:
			raise RuntimeError("sheet full")
		at = (self.x, self.y)
		self.x += w + 10
		self.row = max(self.row, h)
		return at


def soft(mask, along, across):
	"""soft paint: a mask blurred more along the grain than across it, the wet gouache look"""
	return gaussian_filter(mask, (across, along))


def paint_lines(shape, count, length, half, rng, wander, xspan=(-0.1, 0.6)):
	"""thin curving lines into a mask, tapered at both ends"""
	m = np.zeros(shape, np.float32)
	H, L = shape
	for _ in range(count):
		x0 = rng.uniform(*xspan) * L
		ln = rng.uniform(*length) * L
		xa, xb = max(int(x0), 0), min(int(x0 + ln), L)
		if xb - xa < 6:
			continue
		n = xb - xa
		centre = rng.uniform(0, H) + np.cumsum(smooth1d(n, max(n // 3, 5), rng)) / n * wander * 3
		t = np.arange(n) / n
		width = half * np.minimum(1, np.minimum(t, 1 - t) * 5) * rng.uniform(0.6, 1.1) + 0.15
		rows = np.arange(H)[:, None]
		v = np.clip(width[None, :] - np.abs(rows - centre[None, :]), 0, 1)
		m[:, xa:xb] = np.maximum(m[:, xa:xb], v * rng.uniform(0.55, 1))
	return m


def over(img, colour, a):
	a = np.clip(a, 0, 1)[..., None]
	return img * (1 - a) + colour * a


def paint_strip(length, bands, rng, contacts=(), foot=False, knots=1, nails=(), scratch=False):
	"""a beam's sides, unrolled, grain along x. Soft paint throughout: every layer is a blurred mask, so nothing has a hard edge or stops dead.
	Edge highlights use the rock kit's recipe (tools/art/paint_rock_kit.py): a soft-sided band that wobbles and fades, never a cut-off stroke."""
	H = sum(b[0] for b in bands) * SS
	L = length * SS
	rows = []
	y = 0
	for px, kind in bands:
		rows.append((y, y + px * SS, kind))
		y += px * SS
	# the base: value per face, blended across the corners
	value = np.zeros(H, np.float32)
	for y0, y1, kind in rows:
		value[y0:y1] = GRAIN_FACE.get(kind, 1.08)
	value = gaussian_filter(value, 2.2 * SS, mode="wrap")
	img = np.tile(value[:, None, None], (1, L, 3)) * BASE
	# broad soft planes along the grain, close to the base in hue: big calm shapes
	yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
	for colour, count, along, across, strength in ((LIGHT, 8, 9, 1.1, 0.7), (DUSK, 9, 9, 1.1, 0.7), (WARM, 5, 12, 1.6, 0.42), (COOL, 4, 12, 1.6, 0.3), (LIGHT, 12, 3, 0.32, 0.42), (DUSK, 12, 3, 0.32, 0.42)):
		m = np.zeros((H, L), np.float32)
		for _ in range(count):
			x0 = rng.uniform(-0.15, 0.8) * L
			stroke(m[..., None], x0, x0 + rng.uniform(0.25, 0.75) * L, rng.uniform(0, H), rng.uniform(0.05, 0.13) * H + 2, np.array((1.0,)), rng, wander=H * 0.02, tail=0.4)
		img = over(img, colour, soft(m, along * SS, across * SS) * strength * 1.5)
	# value drifting slowly along the length, so no stretch is flat
	drift = gaussian_filter(rng.normal(0, 1, (H, L)).astype(np.float32), (10 * SS, 40 * SS))
	drift = drift / (np.abs(drift).max() + 1e-6)
	img *= 1 + drift[..., None] * 0.04
	# grain: a thin soft line, in brown rather than near-black, with a paler sliver beside some
	dark = paint_lines((H, L), max(5, H // (SS * 6)), (0.35, 0.95), 0.75 * SS, rng, H * 0.012)
	img = over(img, GRAIN, soft(dark, 0.5 * SS, 0.16 * SS) * 0.86)
	pale = paint_lines((H, L), max(2, H // (SS * 14)), (0.1, 0.32), 0.55 * SS, rng, H * 0.01)
	img = over(img, LIGHT * 1.14, soft(pale, 0.6 * SS, 0.18 * SS) * 0.6)
	# short fine ticks in the grain: the close-up detail
	ticks = paint_lines((H, L), max(14, H // SS), (0.015, 0.07), 0.42 * SS, rng, H * 0.003, xspan=(0.0, 0.98))
	img = over(img, GRAIN, soft(ticks, 0.25 * SS, 0.1 * SS) * 0.55)
	faces = [r for r in rows if r[2] in ("front", "back")]
	for _ in range(knots):
		y0, y1, _k = faces[int(rng.integers(len(faces)))]
		cx, cy = rng.uniform(0.2, 0.8) * L, rng.uniform(y0, y1)
		r = rng.uniform(0.18, 0.26) * (y1 - y0)
		d = np.hypot((xx - cx) / 1.9, yy - cy) / r
		img = over(img, GRAIN, gaussian_filter((d < 0.34).astype(np.float32), 0.3 * SS) * 0.72)
		img = over(img, DUSK, gaussian_filter((np.abs(d - 0.8) < 0.1).astype(np.float32), 0.35 * SS) * 0.42)
	if scratch:
		y0, y1, _k = faces[0]
		cx = rng.uniform(0.35, 0.65) * L
		m = np.zeros((H, L), np.float32)
		for a in (-0.5, 0.55):
			for i in range(int((y1 - y0) * 0.8)):
				py, px = int(y0 + (y1 - y0) * 0.1 + i), int(cx + a * (i - (y1 - y0) * 0.4))
				if 0 <= px < L and 0 <= py < H:
					m[py, px] = 1
		img = over(img, GRAIN, gaussian_filter(m, 0.3 * SS) * 1.5)
	# painted light: the painted shadows where parts touch, soft and warm-plum
	for cx, half in contacts:
		m = np.exp(-((xx - cx * L) / (half * SS * 0.8)) ** 4) * (0.7 + 0.3 * gaussian_filter(rng.random((H, L)).astype(np.float32), (2 * SS, 6 * SS)) * 4 - 0.6)
		img = over(img, SHADOW, gaussian_filter(m.astype(np.float32), (1 * SS, 2.5 * SS)) * 0.72)
	if foot:
		reach = L * 0.18
		wob = gaussian_filter(rng.normal(0, 1, H).astype(np.float32), 3 * SS, mode="wrap")
		wob = wob / (np.abs(wob).max() + 1e-6) * reach * 0.3
		m = np.clip(1 - (xx - wob[:, None]) / reach, 0, 1)
		img = over(img, SHADOW, m**1.5 * 0.8)
		img = over(img, MOSS_DARK, np.clip(1 - (xx - wob[:, None]) / (reach * 0.6), 0, 1) ** 1.6 * 0.55)
	img = np.clip(img + (img - gaussian_filter(img, (1.4 * SS, 1.4 * SS, 0))) * 0.75, 0, 255)
	# edge highlights, placed like a painter would: each edge has its own rhythm of strong runs, faint stretches and real gaps,
	# and a few worn spots where the light bleeds off the edge into the face, broken up along the grain
	high = np.zeros((H, L), np.float32)
	streak = gaussian_filter(rng.random((H, L)).astype(np.float32), (0.35 * SS, 7 * SS))
	streak = np.clip((streak - streak.mean()) / (streak.std() * 1.6) * 0.5 + 0.5, 0, 1)
	for i, (y0, y1, kind) in enumerate(rows):
		if kind != "edge":
			continue
		cy = (y0 + y1) / 2
		wobble = smooth1d(L, max(L // 7, 8), rng) * 1.0 * SS
		dy = yy - cy - wobble[None, :]
		w = (y1 - y0) / 2 + 3.0 * SS
		upper = 1.0 if i < 2 else 0.8 if i < 4 else 0.3 if i < 6 else 0.6
		# the rhythm: a level per stretch, weighted so upper edges carry more, then eased between
		runs = max(4, int(length / 34))
		levels = rng.choice((0.04, 0.2, 0.55, 1.0), size=runs + 2, p=(0.14, 0.18, 0.3, 0.38) if upper >= 0.8 else (0.3, 0.28, 0.27, 0.15))
		fade = np.interp(np.arange(L), np.linspace(-0.08, 1.08, runs + 2) * L, levels)
		fade = gaussian_filter(fade, L / runs * 0.22)
		# worn spots: one or two per edge, on a chosen side of it
		wide_up, wide_down = np.zeros(L), np.zeros(L)
		for _ in range(int(rng.integers(2, 4)) if upper >= 0.6 else 0):
			cx = rng.uniform(0.08, 0.92) * L
			reach = rng.uniform(0.04, 0.11) * L
			bump = np.exp(-(((np.arange(L) - cx) / reach) ** 2))
			fade = np.maximum(fade, bump * rng.uniform(0.7, 1.0))
			amount = rng.uniform(2.2, 5.0) * w
			if rng.random() < 0.5:
				wide_up = np.maximum(wide_up, bump * amount)
			else:
				wide_down = np.maximum(wide_down, bump * amount)
		core = ss(w, 0, np.abs(dy)) ** 1.3
		extra = np.where(dy < 0, wide_up[None, :], wide_down[None, :])
		spread = ss(w + extra + 1e-3, w * 0.3, np.abs(dy)) * (extra > 0.5)
		bleed = spread * (0.25 + 0.75 * streak)
		high = np.maximum(high, np.maximum(core, bleed) * fade[None, :] * upper)
	img = over(img, EDGE, gaussian_filter(high, 0.45 * SS) * 0.74)
	# a wide faint glow beside the lit edges, so they sink into the face
	img = over(img, EDGE_PALE, gaussian_filter(high, (4.5 * SS, 10 * SS)) * 0.42)
	for nx, ny in nails:
		cx, cy = nx * L, ny * H
		d = np.hypot(xx - cx, yy - cy)
		img = over(img, GRAIN, ss(3.2 * SS, 1.8 * SS, d) * 0.55)
		img = over(img, NAIL, ss(2.0 * SS, 1.2 * SS, d))
	return np.clip(img, 0, 255)


def paint_end(px, rng):
	"""end grain: rings as strokes, pale, with a dark split"""
	n = px * SS
	img = np.zeros((n, n, 3), float)
	img[:] = LIGHT * 1.08
	yy, xx = np.mgrid[0:n, 0:n]
	cx, cy = n * rng.uniform(0.4, 0.6), n * rng.uniform(0.4, 0.6)
	d = np.hypot(xx - cx, (yy - cy) * 1.2) + np.sin(np.arctan2(yy - cy, xx - cx) * 5) * n * 0.012
	img[:] = LIGHT * 1.02
	for r in (0.44, 0.27, 0.12):
		img[np.abs(d - r * n) < 0.012 * n + 0.5] = DUSK * 1.12
	for _ in range(2):
		a = rng.uniform(0, math.tau)
		for t in np.linspace(0, 0.5 * n, n):
			x, y = cx + math.cos(a) * t, cy + math.sin(a) * t
			if 0 <= x < n - 2 and 0 <= y < n - 2:
				img[int(y), int(x) : int(x) + 2] = GRAIN
	return gaussian_filter(img, (0.6 * SS, 0.6 * SS, 0))


def beam_section(w, h, ch):
	"""the chamfered cross-section, going round: 8 corners. Returned with the band list (top to bottom on the strip)"""
	pts = [(-w / 2 + ch, h / 2), (w / 2 - ch, h / 2), (w / 2, h / 2 - ch), (w / 2, -h / 2 + ch), (w / 2 - ch, -h / 2), (-w / 2 + ch, -h / 2), (-w / 2, -h / 2 + ch), (-w / 2, h / 2 - ch)]
	kinds = ["top", "edge", "front", "edge", "bottom", "edge", "back", "edge"]
	return pts, kinds


class Part:
	"""a beam along +x: rings of the section, tapered and wandering, unrolled into its strip. Local axes: x along, y up, z out of the front."""

	def __init__(self, sheet, name, length, w0, h0, rng, w1=None, h1=None, ch=0.13, rings=5, bend=0.05, contacts=(), foot=False, knots=1, nails=(), scratch=False, tip=0.0):
		w1, h1 = w1 or w0, h1 or h0
		self.name = name
		pts, kinds = beam_section(max(w0, w1), max(h0, h1), ch)
		# the strip: face widths in studs -> px; faces get at least 6 px and edges at least 4
		perim = [math.dist(pts[i], pts[(i + 1) % 8]) for i in range(8)]
		bands = [(max(4 if kinds[i] == "edge" else 6, int(round(perim[i] * TEXELS))), kinds[i]) for i in range(8)]
		sh = sum(b[0] for b in bands)
		sl = int(length * TEXELS)
		x, y = sheet.place(sl, sh)
		strip = paint_strip(sl, bands, rng, contacts, foot, knots, nails, scratch)
		sheet.img[y * SS : (y + sh) * SS, x * SS : (x + sl) * SS] = strip
		# the end cap
		cap = max(int(max(w0, h0) * TEXELS), 12)
		cx, cy = sheet.place(cap, cap)
		sheet.img[cy * SS : (cy + cap) * SS, cx * SS : (cx + cap) * SS] = paint_end(cap, rng)
		self.verts, self.uvs, self.faces = [], [], []
		self.flat = []
		rows = [y]
		for b in bands:
			rows.append(rows[-1] + b[0])
		ring = []
		wob = rng.normal(0, 1, (rings, 2)) * bend
		wob[0] = wob[0] * 0.3
		for i in range(rings):
			f = i / (rings - 1)
			sw = (w0 + (w1 - w0) * f) / max(w0, w1)
			sh2 = (h0 + (h1 - h0) * f) / max(h0, h1)
			jitter = rng.normal(0, 0.012, (8, 2))
			rp = []
			for k, (a, b) in enumerate(pts):
				snap = rng.uniform(-tip, tip) if i == rings - 1 else 0
				rp.append((length * f + snap, b * sh2 + wob[i, 0] + jitter[k, 0], a * sw + wob[i, 1] + jitter[k, 1]))
			ring.append(rp)
		for i in range(rings - 1):
			f0, f1 = i / (rings - 1), (i + 1) / (rings - 1)
			u0, u1 = x + sl * f0, x + sl * f1
			for k in range(8):
				q = [ring[i][k], ring[i + 1][k], ring[i + 1][(k + 1) % 8], ring[i][(k + 1) % 8]]
				vt0, vt1 = rows[k], rows[k + 1]
				uv = [(u0, vt0), (u1, vt0), (u1, vt1), (u0, vt1)]
				self.quad(q, uv)
		# caps: the far end, cut at a slant with a slightly raised lip; the near end too on planks
		for end, r in ((1, ring[-1]), (0, ring[0])):
			centre = tuple(np.mean(r, axis=0))
			centre = (centre[0] - (tip * 0.5 if end == 1 else 0), centre[1], centre[2])
			for k in range(8):
				a, b = r[k], r[(k + 1) % 8]
				ua = (cx + cap * (0.5 + 0.5 * pts[k][1] / max(h0, h1) * 0.96), cy + cap * (0.5 + 0.5 * pts[k][0] / max(w0, w1) * 0.96))
				ub = (cx + cap * (0.5 + 0.5 * pts[(k + 1) % 8][1] / max(h0, h1) * 0.96), cy + cap * (0.5 + 0.5 * pts[(k + 1) % 8][0] / max(w0, w1) * 0.96))
				uc = (cx + cap / 2, cy + cap / 2)
				tri = [a, b, centre] if end == 0 else [b, a, centre]
				tu = [ua, ub, uc] if end == 0 else [ub, ua, uc]
				self.flat.append(len(self.faces))
				self.tri(tri, tu)
		self.face_outward()
		self.smooth_normals()

	def face_outward(self):
		"""Roblox hides the back of every triangle, so each must wind outward: sides away from the beam's axis, caps away from its middle"""
		v = np.array(self.verts)
		middle = v.mean(axis=0)
		axis_y, axis_z = middle[1], middle[2]
		for fi, f in enumerate(self.faces):
			a, b, c = v[list(f)]
			centre = (a + b + c) / 3
			out = centre - middle if fi in self.flat else np.array((0, centre[1] - axis_y, centre[2] - axis_z))
			if np.dot(np.cross(b - a, c - a), out) < 0:
				self.faces[fi] = (f[0], f[2], f[1])

	def smooth_normals(self):
		"""sides share averaged normals, so light rolls softly over the corners; end caps stay flat"""
		acc = {}
		key = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))
		faces_n = []
		for fi, f in enumerate(self.faces):
			a, b, c = [np.array(self.verts[i]) for i in f]
			n = np.cross(b - a, c - a)
			faces_n.append(n)
			if fi in self.flat:
				continue
			for i in f:
				acc[key(self.verts[i])] = acc.get(key(self.verts[i]), 0) + n
		self.normals = [None] * len(self.verts)
		for fi, f in enumerate(self.faces):
			for i in f:
				n = faces_n[fi] if fi in self.flat else acc[key(self.verts[i])]
				self.normals[i] = n / (np.linalg.norm(n) + 1e-9)

	def quad(self, q, uv):
		self.tri([q[0], q[1], q[2]], [uv[0], uv[1], uv[2]])
		self.tri([q[0], q[2], q[3]], [uv[0], uv[2], uv[3]])

	def tri(self, t, uv):
		n = len(self.verts)
		self.verts += t
		self.uvs += uv
		self.faces.append((n, n + 1, n + 2))

	def placed(self, cf):
		"""world positions of this part under a transform: origin, x axis (along), y axis (up), z axis"""
		o, ax, ay, az = cf
		return [tuple(np.array(o) + ax * v[0] + ay * v[1] + az * v[2]) for v in self.verts]


def unit(v):
	v = np.array(v, float)
	return v / np.linalg.norm(v)


def frame_along(p0, p1, up=(0, 1, 0)):
	ax = unit(np.array(p1, float) - np.array(p0, float))
	az = unit(np.cross(ax, np.array(up, float)))
	ay = np.cross(az, ax)
	return np.array(p0, float), ax, ay, az


def write_obj(path, name, placed):
	lines = [f"o {name}"]
	vi = 1
	faces = []
	for part, cf in placed:
		pos = part.placed(cf)
		o, ax, ay, az = cf
		for f in part.faces:
			for i in f:
				n = ax * part.normals[i][0] + ay * part.normals[i][1] + az * part.normals[i][2]
				lines.append("v %.4f %.4f %.4f" % pos[i])
				lines.append("vt %.5f %.5f" % (part.uvs[i][0] / SHEET, 1 - part.uvs[i][1] / SHEET))
				lines.append("vn %.4f %.4f %.4f" % tuple(n))
			faces.append(f"f {vi}/{vi}/{vi} {vi + 1}/{vi + 1}/{vi + 1} {vi + 2}/{vi + 2}/{vi + 2}")
			vi += 3
	open(path, "w").write("\n".join(lines + faces) + "\n")
	# a closed mesh wound outward has positive volume, per part: anything else would show inside out in Roblox
	for part, cf in placed:
		pos = np.array(part.placed(cf))
		vol = sum(np.dot(pos[f[0]], np.cross(pos[f[1]], pos[f[2]])) for f in part.faces) / 6
		assert vol > 0, f"{name}: {part.name} is inside out (volume {vol:.2f})"


def main():
	rng = np.random.default_rng(23)
	s = Sheet()
	# posts: thick, foot sunk 1 stud; painted shadows where the rails cross
	POST = 5.6
	posts = [
		Part(s, "PostA", POST, 1.05, 1.05, rng, 0.92, 0.96, 0.085, rings=5, bend=0.05, contacts=((0.73, 12), (0.40, 7)), foot=True, knots=1),
		Part(s, "PostB", POST - 0.5, 1.16, 1.0, rng, 0.98, 0.9, 0.09, rings=5, bend=0.07, contacts=((0.78, 12), (0.44, 7)), foot=True, knots=1),
		Part(s, "PostC", POST + 0.3, 0.98, 1.1, rng, 0.9, 0.92, 0.08, rings=5, bend=0.05, contacts=((0.70, 12), (0.38, 7)), foot=True, knots=1),
		Part(s, "PostStump", 2.7, 1.2, 1.12, rng, 1.0, 0.98, 0.09, rings=4, bend=0.05, foot=True, knots=0),
	]
	# rails: flat wide planks. The top rail is a wedge, wide at one end; the lower rail thinner
	rails = [
		Part(s, "RailTopA", 10.4, 0.34, 1.46, rng, 0.3, 1.02, 0.08, rings=6, bend=0.022, nails=((0.05, 0.42), (0.95, 0.42)), scratch=True, knots=1),
		Part(s, "RailTopB", 9.8, 0.32, 1.12, rng, 0.32, 1.38, 0.08, rings=6, bend=0.022, nails=((0.05, 0.42), (0.95, 0.42)), knots=1),
		Part(s, "RailLowA", 10.2, 0.28, 0.72, rng, 0.26, 0.5, 0.07, rings=5, bend=0.018, nails=((0.04, 0.42), (0.96, 0.42)), knots=0),
		Part(s, "RailBroken", 5.6, 0.32, 1.26, rng, 0.3, 0.7, 0.08, rings=4, bend=0.03, tip=0.5, nails=((0.07, 0.42),), knots=1),
	]
	P = {p.name: p for p in posts + rails}

	def post(name, x, lean_x=0.0, lean_z=0.0, z=0.0, sink=1.0):
		L = {"PostA": POST, "PostB": POST - 0.5, "PostC": POST + 0.3, "PostStump": 2.7}[name]
		top = np.array((x + lean_x * L, -sink + L, z + lean_z * L))
		return P[name], frame_along((x, -sink, z), top, up=(0, 0, 1))

	def rail(name, a, b, z=0.62):
		p0, p1 = np.array((a[0], a[1], z), float), np.array((b[0], b[1], z + b[2] if len(b) > 2 else z), float)
		# plank faces forward: x along, y up the plank, z toward the viewer
		ax = unit(p1 - p0)
		az = unit(np.cross(ax, (0, 1, 0)))
		ay = np.cross(az, ax)
		return P[name], (p0, ax, ay, az)

	sections = {
		"FenceA": [
			post("PostA", -4.5, -0.03, 0.02),
			post("PostB", 4.6, 0.05, -0.02),
			rail("RailTopA", (-5.2, 3.55), (5.2, 3.15)),
			rail("RailLowA", (-5.1, 1.75), (5.1, 1.6)),
		],
		"FenceLean": [
			post("PostC", -4.4, -0.2, 0.05),
			post("PostA", 4.4, -0.1, -0.03),
			rail("RailTopB", (-5.6, 3.15), (4.2, 3.65)),
			rail("RailLowA", (-5.2, 1.5), (5.0, 1.85)),
		],
		"FenceBroken": [
			post("PostB", -4.4, 0.04, 0.04),
			post("PostStump", 4.6, 0.13, -0.05),
			rail("RailBroken", (-5.0, 3.3), (0.6, 2.7)),
			rail("RailLowA", (-5.0, 1.6), (5.0, 0.72)),
		],
		"FencePost": [post("PostC", 0, 0.05, 0.03)],
	}
	Image.fromarray(np.clip(s.img * GRADE, 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS).save(os.path.join(OUT, "Fence_Color.png" if SCHEME == "Chestnut" else f"Fence_Color_{SCHEME}.png"))
	report = {}
	for name, parts in sections.items():
		write_obj(os.path.join(OUT, name + ".obj"), name, parts)
		report[name] = sum(len(p.faces) for p, _ in parts)
	json.dump({"Triangles": report, "SheetUsedToRow": s.y + s.row}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print(report, "sheet used to row", s.y + s.row)


main()
