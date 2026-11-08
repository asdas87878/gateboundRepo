"""The tree kit (docs/style/art-style.md), system Python: painted spray planes on a dark core, chunky bark from the fence's strip painter. No Blender until export.
A crown is shingled sprays: a two-by-two curved plane whose picture is a fan of pointed brush strokes, on a dark opaque core so nothing shows through.
Every spray shape is painted in several tones with the same strokes (same alpha); front faces take a tone by where they sit, back faces take the dark underside.
Writes into art/kit/trees/<set>: Tree_Leaves.png, Tree_Bark.png, <Name>_Crown.obj, <Name>_Trunk.obj, kit.json.

  python tools/art/tree_kit.py art/kit/trees/test test
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/trees/test")
MODE = sys.argv[2] if len(sys.argv) > 2 else "test"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- colours
# greens measured from the lesson's trees (tools: scratch k-means on ref_01), darks pushed to teal so nothing is black or grey
UNDER = np.array((12, 80, 74), float)
SHADE = np.array((16, 98, 76), float)
DEEP = np.array((30, 124, 76), float)
MID = np.array((40, 146, 72), float)
LIT = np.array((54, 170, 66), float)
TOP = np.array((84, 190, 82), float)
PALE = np.array((176, 230, 150), float)
# a spray's strokes run root -> tip; each tone is that ramp (root colour, tip colour)
TONES = {"top": (LIT, TOP * 1.08), "lit": (DEEP, LIT), "mid": (SHADE, MID), "shade": (UNDER, DEEP), "under": (UNDER * 0.86, SHADE * 0.92)}
GLOW = {"top": 0.34, "lit": 0.2, "mid": 0.06, "shade": 0.0, "under": 0.0}
TONE_ORDER = ("top", "lit", "mid", "shade", "under")
# bark: the fence's chestnut, cooler and a step darker so it sits under a crown
BASE = np.array((106, 78, 70), float)
LIGHT = np.array((122, 92, 80), float)
WARM = np.array((118, 84, 66), float)
DUSK = np.array((90, 68, 68), float)
COOL = np.array((94, 74, 78), float)
GRAIN = np.array((62, 44, 50), float)
SHADOW = np.array((58, 44, 56), float)
EDGE = np.array((232, 206, 168), float)
EDGE_PALE = np.array((196, 160, 128), float)
MOSS_DARK = np.array((54, 112, 72), float)
GRAIN_FACE = {"top": 1.14, "front": 1.0, "back": 0.92, "bottom": 0.7}

LEAF_SHEET = 1024
CELL = 256
BARK_SHEET = 1024
BARK_SS = 2
BARK_TEXELS = 26  # per stud: trees are big and seen from further than a fence
NORMAL_UP = 0.62  # how far crown normals lean up, so a clump stays bright all round: the paint carries the form


def ss(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def over(img, colour, a):
	a = np.clip(a, 0, 1)[..., None]
	return img * (1 - a) + colour * a


def smooth1d(n, width, rng):
	v = rng.normal(size=n + width * 2)
	v = np.convolve(v, np.ones(width) / width, "same")[width : width + n]
	return v / (np.abs(v).max() + 1e-6)


def unit(v):
	v = np.array(v, float)
	return v / (np.linalg.norm(v) + 1e-9)


# ---------------------------------------------------------------- the spray paint
def spike(x, y, ang, length, width, bend):
	"""a brush mark as a polygon: round at the root, pointed at the tip, curving a little"""
	pts_l, pts_r = [], []
	n = 7
	for i in range(n + 1):
		t = i / n
		a = ang + bend * t
		cx = x + math.sin(a) * length * t
		cy = y + math.cos(a) * length * t
		w = width * min(1, (t / 0.16) ** 0.6) * (1 - t) ** 0.75
		pts_l.append((cx - math.cos(a) * w, cy + math.sin(a) * w))
		pts_r.append((cx + math.cos(a) * w, cy - math.sin(a) * w))
	return pts_l + pts_r[::-1]


def spray_strokes(seed, count=260, fan=1.3, reach=1.0):
	"""the shared stroke list of one spray shape, outermost first so upper strokes shingle over lower ones. Coordinates are 0..1, root at the top middle"""
	rng = np.random.default_rng(seed)
	out = []
	ts = np.sort(rng.uniform(0.0, 1.0, count) ** 0.75)[::-1]
	for t in ts:
		a = rng.uniform(-fan, fan) * (0.72 + 0.28 * rng.random())
		rmax = min(0.47 / max(abs(math.sin(a)), 1e-3), 0.95 / max(math.cos(a), 1e-3)) * reach
		# the fringe is uneven: some directions stop short, for a broken silhouette
		rmax *= 0.8 + 0.2 * math.sin(a * 7 + seed) * 0.5 + rng.uniform(0, 0.15)
		length = rng.uniform(0.15, 0.27) * rmax
		start = max(t * rmax - length, 0)
		x = 0.5 + math.sin(a) * start
		y = 0.03 + math.cos(a) * start
		width = rng.uniform(0.016, 0.034) * (0.72 + 0.55 * t)
		bend = rng.uniform(-0.25, 0.25) + a * -0.12
		ang = a + rng.uniform(-0.12, 0.12)
		shade = rng.normal(0, 1)
		hue = rng.normal(0, 1)
		dark = rng.random() < 0.13
		sec = None
		if rng.random() < 0.55:
			sec = (rng.uniform(0.42, 0.62), rng.choice((-1, 1)) * rng.uniform(0.14, 0.32), rng.uniform(0.36, 0.56))
		out.append(dict(x=x, y=y, ang=ang, length=length, width=width, bend=bend, t=t, shade=shade, hue=hue, dark=dark, sec=sec))
	return out


def paint_spray(strokes, tone, size, solid=False):
	"""one cell: fill under the fan, then each stroke with a dark sliver under it. Crisp strokes with one soft glow over the lit middle. Painted large, then shrunk"""
	S = 3
	big = size * S
	root_c, tip_c = TONES[tone]
	img = Image.new("RGB", (big, big), tuple(int(v) for v in root_c))
	mask = Image.new("L", (big, big), 0)
	d = ImageDraw.Draw(img)
	m = ImageDraw.Draw(mask)

	def poly(points, colour):
		p = [(a * big, b * big) for a, b in points]
		d.polygon(p, fill=tuple(int(np.clip(v, 0, 255)) for v in colour))
		m.polygon(p, fill=255)

	# the fill under the fan, so the middle never has holes
	fill = [(0.5, 0.0)]
	for a in np.linspace(-1.15, 1.15, 15):
		r = 0.66 * (1 - 0.3 * (a / 1.15) ** 2) + 0.03 * math.sin(a * 9)
		fill.append((0.5 + math.sin(a) * r, 0.03 + math.cos(a) * r))
	poly(fill, root_c)
	for s in strokes:
		ramp = s["t"] ** 0.9
		c = root_c * (1 - ramp) + tip_c * ramp
		c = c * (1 + s["shade"] * 0.035) + np.array((1, 0.2, -0.8)) * s["hue"] * 3.0
		if s["dark"]:
			c = c * 0.8 + root_c * 0.2
		under = root_c * 0.82
		args = (s["x"], s["y"], s["ang"], s["length"], s["width"], s["bend"])
		poly(spike(s["x"] + 0.002, s["y"] + 0.013, s["ang"], s["length"] * 1.02, s["width"] * 1.25, s["bend"]), under)
		poly(spike(*args), c)
		if s["sec"]:
			at, turn, ln = s["sec"]
			x = s["x"] + math.sin(s["ang"]) * s["length"] * at
			y = s["y"] + math.cos(s["ang"]) * s["length"] * at
			poly(spike(x, y, s["ang"] + turn, s["length"] * ln, s["width"] * 0.62, s["bend"] * 0.5), c)
	a = np.array(mask, np.float32) / 255
	rgb = np.array(img, np.float32)
	# a soft pale glow on the lit part of the fan, under the crisp strokes' edges only in value: never noise
	yy, xx = np.mgrid[0:big, 0:big].astype(np.float32) / big
	glow = np.exp(-(((xx - 0.5) / 0.3) ** 2) - ((yy - 0.5) / 0.26) ** 2)
	if GLOW[tone]:
		rgb = over(rgb, PALE, glow * a * GLOW[tone])
	# colour under the transparent parts, so no dark or pale fringe shows at the alpha edge
	if not solid:
		idx = distance_transform_edt(a < 0.5, return_distances=False, return_indices=True)
		rgb = rgb[idx[0], idx[1]]
	cell_rgb = np.array(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS), np.float32)
	cell_a = np.array(Image.fromarray((a * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS), np.float32)
	return cell_rgb, cell_a


class LeafSheet:
	"""a grid of cells: for each spray shape, one cell per tone"""

	def __init__(self):
		self.rgb = np.zeros((LEAF_SHEET, LEAF_SHEET, 3), np.float32)
		self.rgb[:] = UNDER
		self.a = np.zeros((LEAF_SHEET, LEAF_SHEET), np.float32)
		self.cells = {}
		self.n = 0

	def add_shape(self, name, strokes):
		for tone in TONE_ORDER:
			col, row = self.n % (LEAF_SHEET // CELL), self.n // (LEAF_SHEET // CELL)
			self.n += 1
			c, a = paint_spray(strokes, tone, CELL)
			x, y = col * CELL, row * CELL
			self.rgb[y : y + CELL, x : x + CELL] = c
			self.a[y : y + CELL, x : x + CELL] = a
			self.cells[(name, tone)] = (x, y)

	def uv(self, name, tone, u, v):
		"""u, v in 0..1 inside the cell, with a small margin, to sheet UV"""
		x, y = self.cells[(name, tone)]
		m = 3
		return ((x + m + u * (CELL - 2 * m)) / LEAF_SHEET, 1 - (y + m + v * (CELL - 2 * m)) / LEAF_SHEET)

	def save(self, path):
		rgba = np.dstack((np.clip(self.rgb, 0, 255), self.a)).astype(np.uint8)
		Image.fromarray(rgba, "RGBA").save(path)


# ---------------------------------------------------------------- bark: the fence's strip painter, its layers kept in the same order
def stroke(img, x0, x1, y, half, rng, wander=0.0, tail=0.6):
	h, w = img.shape
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
	mask &= t[None, :] < 1 - tail * bristle[:, None]
	img[ya:yb, xa:xb][mask] = 1


def paint_lines(shape, count, length, half, rng, wander, xspan=(-0.1, 0.6)):
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


def soft(mask, along, across):
	return gaussian_filter(mask, (across, along))


def paint_bark(length, bands, rng, foot=False, fade_tip=True):
	"""a limb unrolled, grain along x, root at x = 0"""
	SS = BARK_SS
	H = sum(b[0] for b in bands) * SS
	L = length * SS
	rows = []
	y = 0
	for px, kind in bands:
		rows.append((y, y + px * SS, kind))
		y += px * SS
	value = np.zeros(H, np.float32)
	for y0, y1, kind in rows:
		value[y0:y1] = GRAIN_FACE.get(kind, 1.08)
	value = gaussian_filter(value, 1.8 * SS, mode="wrap")
	img = np.tile(value[:, None, None], (1, L, 3)) * BASE
	yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
	for colour, count, along, across, strength in ((LIGHT, 7, 9, 1.1, 0.7), (DUSK, 8, 9, 1.1, 0.7), (WARM, 4, 12, 1.6, 0.42), (COOL, 4, 12, 1.6, 0.34), (LIGHT, 10, 3, 0.32, 0.42), (DUSK, 10, 3, 0.32, 0.42)):
		m = np.zeros((H, L), np.float32)
		for _ in range(count):
			x0 = rng.uniform(-0.15, 0.8) * L
			stroke(m, x0, x0 + rng.uniform(0.25, 0.75) * L, rng.uniform(0, H), rng.uniform(0.05, 0.13) * H + 2, rng, wander=H * 0.02, tail=0.4)
		img = over(img, colour, soft(m, along * SS, across * SS) * strength * 1.5)
	# long ridges in the bark, then the fine grain
	dark = paint_lines((H, L), max(8, H // (SS * 4)), (0.3, 0.9), 0.85 * SS, rng, H * 0.012)
	img = over(img, GRAIN, soft(dark, 0.5 * SS, 0.16 * SS) * 0.86)
	pale = paint_lines((H, L), max(3, H // (SS * 10)), (0.1, 0.32), 0.6 * SS, rng, H * 0.01)
	img = over(img, LIGHT * 1.16, soft(pale, 0.6 * SS, 0.18 * SS) * 0.6)
	ticks = paint_lines((H, L), max(12, H // SS), (0.015, 0.07), 0.42 * SS, rng, H * 0.003, xspan=(0.0, 0.98))
	img = over(img, GRAIN, soft(ticks, 0.25 * SS, 0.1 * SS) * 0.55)
	if foot:
		reach = L * 0.2
		wob = gaussian_filter(rng.normal(0, 1, H).astype(np.float32), 3 * SS, mode="wrap")
		wob = wob / (np.abs(wob).max() + 1e-6) * reach * 0.3
		m = np.clip(1 - (xx - wob[:, None]) / reach, 0, 1)
		img = over(img, SHADOW, m**1.5 * 0.8)
		img = over(img, MOSS_DARK, np.clip(1 - (xx - wob[:, None]) / (reach * 0.65), 0, 1) ** 1.5 * 0.6)
	if fade_tip:
		img = over(img, SHADOW, ss(0.62, 1.0, xx / L) * 0.72)  # the crown's shade, painted in
	img = np.clip(img + (img - gaussian_filter(img, (1.4 * SS, 1.4 * SS, 0))) * 0.75, 0, 255)
	# edge highlights, the fence's recipe: each edge its own rhythm, soft-sided, fading
	high = np.zeros((H, L), np.float32)
	for i, (y0, y1, kind) in enumerate(rows):
		if kind != "edge":
			continue
		cy = (y0 + y1) / 2
		wobble = smooth1d(L, max(L // 7, 8), rng) * 1.0 * SS
		dy = yy - cy - wobble[None, :]
		w = (y1 - y0) / 2 + 2.4 * SS
		upper = 1.0 if i < 2 else 0.75 if i < 4 else 0.3 if i < 6 else 0.6
		runs = max(4, int(length / 30))
		levels = rng.choice((0.04, 0.2, 0.55, 1.0), size=runs + 2, p=(0.14, 0.18, 0.3, 0.38) if upper >= 0.75 else (0.3, 0.28, 0.27, 0.15))
		fade = np.interp(np.arange(L), np.linspace(-0.08, 1.08, runs + 2) * L, levels)
		fade = gaussian_filter(fade, L / runs * 0.22)
		high = np.maximum(high, ss(w, 0, np.abs(dy)) ** 1.3 * fade[None, :] * upper)
	if fade_tip:
		high = high * (1 - ss(0.5, 0.85, xx / L))
	img = over(img, EDGE, gaussian_filter(high, 0.45 * SS) * 0.58)
	img = over(img, EDGE_PALE, gaussian_filter(high, (4.5 * SS, 10 * SS)) * 0.34)
	return np.clip(img, 0, 255)


class BarkSheet:
	def __init__(self):
		self.img = np.zeros((BARK_SHEET * BARK_SS, BARK_SHEET * BARK_SS, 3), np.float32)
		self.img[:] = BASE
		self.x, self.y, self.row = 8, 8, 0
		# the core's patch: dark mottled foliage, top-left corner kept for it
		self.core = self.place(128, 128)
		cx, cy = self.core
		rng = np.random.default_rng(5)
		n = 128 * BARK_SS
		patch = np.zeros((n, n, 3), np.float32)
		patch[:] = UNDER
		for colour, count in ((SHADE, 40), (UNDER * 0.84, 40)):
			pm = Image.new("L", (n, n), 0)
			d = ImageDraw.Draw(pm)
			for _ in range(count):
				x, y = rng.uniform(0, 1, 2)
				d.polygon([(a * n, b * n) for a, b in spike(x, y, rng.uniform(-0.7, 0.7), rng.uniform(0.1, 0.22), rng.uniform(0.02, 0.04), 0.1)], fill=255)
			patch = over(patch, colour, np.array(pm, np.float32) / 255)
		self.img[cy * BARK_SS : (cy + 128) * BARK_SS, cx * BARK_SS : (cx + 128) * BARK_SS] = patch

	def place(self, w, h):
		if self.x + w + 8 > BARK_SHEET:
			self.x, self.y, self.row = 8, self.y + self.row + 8, 0
		if self.y + h + 8 > BARK_SHEET:
			raise RuntimeError("bark sheet full")
		at = (self.x, self.y)
		self.x += w + 10
		self.row = max(self.row, h)
		return at

	def save(self, path):
		Image.fromarray(np.clip(self.img, 0, 255).astype(np.uint8)).resize((BARK_SHEET, BARK_SHEET), Image.LANCZOS).save(path)


# ---------------------------------------------------------------- mesh
class Mesh:
	"""unwelded triangles with normals and UVs. Y up, studs. Triangles wind counter-clockwise from outside."""

	def __init__(self, name):
		self.name = name
		self.v, self.n, self.t, self.closed = [], [], [], []

	def tri(self, ps, ns, uvs):
		self.v += [tuple(p) for p in ps]
		self.n += [tuple(n) for n in ns]
		self.t += [tuple(u) for u in uvs]

	@property
	def tris(self):
		return len(self.v) // 3

	def write(self, path):
		lines = [f"o {self.name}"]
		for p, n, t in zip(self.v, self.n, self.t):
			lines.append("v %.4f %.4f %.4f" % p)
			lines.append("vt %.5f %.5f" % t)
			lines.append("vn %.4f %.4f %.4f" % n)
		for i in range(self.tris):
			a = i * 3 + 1
			lines.append(f"f {a}/{a}/{a} {a + 1}/{a + 1}/{a + 1} {a + 2}/{a + 2}/{a + 2}")
		open(path, "w").write("\n".join(lines) + "\n")


def tri_normal(a, b, c):
	return np.cross(np.array(b) - np.array(a), np.array(c) - np.array(a))


def tube(mesh, sheet, name, pts, radii, rng, foot=False, fade_tip=True):
	"""a chamfered limb along a path: four faces and four thin edges, unrolled onto the bark sheet. Closed, and checked for positive volume"""
	pts = [np.array(p, float) for p in pts]
	frames = []
	prev = None
	for i, p in enumerate(pts):
		d = unit(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
		a = unit(np.cross(d, (0.3, 0.1, 1.0))) if prev is None else unit(prev - d * np.dot(prev, d))
		frames.append((a, unit(np.cross(a, d))))
		prev = a
	along = [0.0]
	for i in range(len(pts) - 1):
		along.append(along[-1] + np.linalg.norm(pts[i + 1] - pts[i]))
	total = along[-1]
	ch = 0.3  # chamfer share of the half width
	sec = [(-1 + ch, 1), (1 - ch, 1), (1, 1 - ch), (1, -1 + ch), (1 - ch, -1), (-1 + ch, -1), (-1, -1 + ch), (-1, 1 - ch)]
	kinds = ["top", "edge", "front", "edge", "bottom", "edge", "back", "edge"]
	r0 = max(radii)
	mean_r = sum(radii) / len(radii)
	bands = []
	for k in range(8):
		px = math.dist(sec[k], sec[(k + 1) % 8]) * mean_r * BARK_TEXELS
		bands.append((max(5 if kinds[k] == "edge" else 7, int(round(px))), kinds[k]))
	sh, sl = sum(b[0] for b in bands), int(total * BARK_TEXELS)
	x, y = sheet.place(sl, sh)
	strip = paint_bark(sl, bands, rng, foot, fade_tip)
	S = BARK_SS
	sheet.img[y * S : (y + sh) * S, x * S : (x + sl) * S] = strip
	vrows = [y]
	for b in bands:
		vrows.append(vrows[-1] + b[0])
	rings = []
	for p, r, (a, c) in zip(pts, radii, frames):
		jit = rng.normal(0, 0.03, (8, 2)) * r
		rings.append([p + a * (sx * r + jit[k, 0]) + c * (sy * r + jit[k, 1]) for k, (sx, sy) in enumerate(sec)])
	start = mesh.tris
	sides = []
	for i in range(len(rings) - 1):
		u0, u1 = (x + sl * along[i] / total) / BARK_SHEET, (x + sl * along[i + 1] / total) / BARK_SHEET
		for k in range(8):
			k1 = (k + 1) % 8
			q = [rings[i][k], rings[i + 1][k], rings[i + 1][k1], rings[i][k1]]
			v0, v1 = 1 - vrows[k] / BARK_SHEET, 1 - vrows[k + 1] / BARK_SHEET
			uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
			mid = (pts[i] + pts[i + 1]) / 2
			for tri_i in ((0, 1, 2), (0, 2, 3)):
				t = [q[j] for j in tri_i]
				tu = [uv[j] for j in tri_i]
				if np.dot(tri_normal(*t), (t[0] + t[1] + t[2]) / 3 - mid) < 0:
					t = [t[0], t[2], t[1]]
					tu = [tu[0], tu[2], tu[1]]
				sides.append((t, tu))
	# smooth normals over the sides: light rolls over the corners
	acc = {}
	key = lambda v: (round(float(v[0]), 3), round(float(v[1]), 3), round(float(v[2]), 3))
	for t, _ in sides:
		n = tri_normal(*t)
		for p in t:
			acc[key(p)] = acc.get(key(p), 0) + n
	for t, tu in sides:
		mesh.tri(t, [unit(acc[key(p)]) for p in t], tu)
	# caps: both ends, dark end grain from the core patch; hidden in the ground or the crown
	cx, cy = sheet.core
	cap_uv = ((cx + 40) / BARK_SHEET, 1 - (cy + 40) / BARK_SHEET)
	for ring, pt, sign in ((rings[0], pts[0], -1), (rings[-1], pts[-1], 1)):
		out = unit(pts[-1] - pts[-2]) if sign > 0 else unit(pts[0] - pts[1])
		for k in range(8):
			a, b = ring[k], ring[(k + 1) % 8]
			t = [a, b, pt]
			if np.dot(tri_normal(*t), out) < 0:
				t = [b, a, pt]
			mesh.tri(t, [out] * 3, [cap_uv] * 3)
	# a closed tube wound outward has positive volume
	vs = np.array(mesh.v[start * 3 :])
	vol = sum(np.dot(vs[i], np.cross(vs[i + 1], vs[i + 2])) for i in range(0, len(vs), 3)) / 6
	assert vol > 0, f"{name} is inside out ({vol:.2f})"


ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
_g = (1 + 5**0.5) / 2
ICO_V = [unit(p) for p in [(-1, _g, 0), (1, _g, 0), (-1, -_g, 0), (1, -_g, 0), (0, -1, _g), (0, 1, _g), (0, -1, -_g), (0, 1, -_g), (_g, 0, -1), (_g, 0, 1), (-_g, 0, -1), (-_g, 0, 1)]]


def core_lobe(mesh, sheet, c, r, rng):
	"""a dark lump inside the crown, opaque, on the trunk's sheet: it fills the gaps between sprays and casts the ground shadow"""
	cx, cy = sheet.core
	yaw = rng.uniform(0, math.tau)
	cos, sin = math.cos(yaw), math.sin(yaw)
	vs = []
	for v in ICO_V:
		w = v * (1 + rng.normal(0, 0.05))
		vs.append(np.array(c) + np.array(((w[0] * cos - w[2] * sin) * r[0], w[1] * r[1], (w[0] * sin + w[2] * cos) * r[2])))
	start = mesh.tris
	for f in ICO_F:
		t = [vs[i] for i in f]
		ns = [unit(unit(p - np.array(c)) * 0.4 + np.array((0, 0.6, 0))) for p in t]
		uvs = [((cx + 8 + 112 * (0.5 + 0.5 * math.sin(p[0] * 0.5))) / BARK_SHEET, 1 - (cy + 8 + 112 * (0.5 + 0.5 * math.sin(p[1] * 0.5 + p[2] * 0.3))) / BARK_SHEET) for p in t]
		mesh.tri(t, ns, uvs)
	vs_ = np.array(mesh.v[start * 3 :]) - np.array(c)
	vol = sum(np.dot(vs_[i], np.cross(vs_[i + 1], vs_[i + 2])) for i in range(0, len(vs_), 3)) / 6
	assert vol > 0, "core lobe inside out"


def spray_points(root, down, side, out, L, W, droop, ridge, teeth=0, rng=None):
	"""the plane's grid: rows root, middle, tip; columns left, ridge, right. With teeth, the tip row is a zigzag of real geometry"""
	def at(t, s):
		w = W * (0.62 + 0.38 * min(t * 1.5, 1))
		return root + down * (L * t) + side * (w * s * 0.5) + out * (L * (0.2 * math.sin(t * math.pi) - droop * t * t) + ridge * W * (1 - s * s))
	return at


def add_spray(mesh, leaves, shape, tone, root, down, side, out, L, W, normal_of, droop=0.14, ridge=0.1, teeth=0, rng=None, back=True):
	"""front faces in the tone, back faces (real, Roblox hides the reverse of a triangle) in the dark underside. Checked: front faces wind toward out"""
	at = spray_points(root, down, side, out, L, W, droop, ridge)
	if not teeth:
		rows = [(t, [(at(t, s), (0.5 + 0.5 * s, t)) for s in (-1, 0, 1)]) for t in (0, 0.5, 1)]
		quads = []
		for i in range(2):
			for j in range(2):
				a, b = rows[i][1], rows[i + 1][1]
				quads.append([a[j], b[j], b[j + 1], a[j + 1]])
		tris = [[q[0], q[1], q[2]] for q in quads] + [[q[0], q[2], q[3]] for q in quads]
	else:
		# no alpha: the feathers are geometry. root row -> valley row -> zigzag of pointed teeth
		V = 0.58
		root_row = [(at(0, s), (0.5 + 0.28 * s, 0.1)) for s in (-1, 0, 1)]
		valley = []
		for k in range(teeth + 1):
			s = -1 + 2 * k / teeth
			tv = V + rng.uniform(-0.05, 0.05)
			valley.append((at(tv, s), (0.5 + 0.3 * s, tv * 0.75)))
		tips = []
		for k in range(teeth):
			s = -1 + 2 * (k + 0.5) / teeth
			tt = rng.uniform(0.88, 1.12)
			tips.append((at(tt, s + rng.uniform(-0.12, 0.12)), (0.5 + 0.28 * s, 0.86)))
		tris = []
		# fan the root row down onto the valley row
		a, b = 0, 0
		while a < 2 or b < teeth:
			if b >= teeth or (a < 2 and (a + 1) / 2 <= (b + 1) / teeth):
				tris.append([root_row[a], valley[b], root_row[a + 1]])
				a += 1
			else:
				tris.append([root_row[a], valley[b], valley[b + 1]])
				b += 1
		for k in range(teeth):
			tris.append([valley[k], tips[k], valley[k + 1]])
	for t in tris:
		ps = [p for p, _ in t]
		uvs = [uv for _, uv in t]
		if np.dot(tri_normal(*ps), out) < 0:
			ps = [ps[0], ps[2], ps[1]]
			uvs = [uvs[0], uvs[2], uvs[1]]
		ns = [normal_of(p) for p in ps]
		mesh.tri(ps, ns, [leaves.uv(shape, tone, u, v) for u, v in uvs])
		# the back: same points, reversed, dark
		if back:
			mesh.tri([ps[0], ps[2], ps[1]], [ns[0], ns[2], ns[1]], [leaves.uv(shape, "under", *uvs[0]), leaves.uv(shape, "under", *uvs[2]), leaves.uv(shape, "under", *uvs[1])])


def build_crown(mesh, leaves, lobes, rng, shapes, teeth=0, skip_inside=0.72, spray_scale=1.0):
	"""boughs in tiers round each lobe: fans leaving the middle and sloping out and down, so seen from the side they close up into fine level feathers.
	Tone by where it sits: top of the tree lightest, each lobe lit on top and shaded under. Only the low tiers show their undersides, so only they get back faces."""
	low = min(l["c"][1] - l["r"][1] for l in lobes)
	high = max(l["c"][1] + l["r"][1] for l in lobes)
	for li, lobe in enumerate(lobes):
		c = np.array(lobe["c"], float)
		r = np.array(lobe["r"], float)
		plan = lobe["tiers"]  # (height on the lobe -1..1, count, slope in degrees)
		yaw0 = rng.uniform(0, math.tau)
		for ti, (h, count, slope) in enumerate(plan):
			rho = math.sqrt(max(1 - h * h, 0.04))  # the lobe's radius at this tier
			for k in range(count):
				az = yaw0 + (k + rng.uniform(-0.22, 0.22)) / count * math.tau + ti * 0.9
				radial = np.array((math.cos(az), 0.0, math.sin(az)))
				hh = h + rng.uniform(-0.1, 0.1)
				reach = rho * rng.uniform(0.82, 1.2)
				root = c + np.array((0, hh * r[1], 0)) + radial * r * reach * 0.22
				tip_centre = c + np.array((0, hh * r[1], 0)) + radial * r * reach
				if any(oi != li and np.linalg.norm((tip_centre - np.array(o["c"])) / np.array(o["r"])) < skip_inside for oi, o in enumerate(lobes)):
					continue
				sl = math.radians(slope + rng.uniform(-6, 6))
				down = unit(radial * math.cos(sl) + np.array((0, -math.sin(sl), 0)))
				side = unit(np.cross((0, 1, 0), radial))
				out = unit(np.cross(down, side))
				if out[1] < 0:
					out = -out
				roll = rng.uniform(-0.12, 0.12)
				side = unit(side + out * roll)
				L = np.linalg.norm(tip_centre - root) * 1.4 * spray_scale
				W = max(math.tau * np.mean(r[[0, 2]]) * reach / count * 2.1, L * 1.05) * spray_scale
				shape = shapes[int(rng.integers(len(shapes)))]
				tree_h = (c[1] + hh * r[1] - low) / max(high - low, 1)
				score = 0.45 * tree_h + 0.55 * (hh * 0.5 + 0.5) + rng.normal(0, 0.035)
				tone = "top" if score > 0.7 else "lit" if score > 0.57 else "mid" if score > 0.46 else "shade"
				cc = c

				def normal_of(p, cc=cc):
					return unit(unit(np.array(p) - cc) * (1 - NORMAL_UP) + np.array((0, NORMAL_UP, 0)))

				add_spray(mesh, leaves, shape, tone, root, down, side, out, L, W, normal_of, droop=0.3, ridge=0.1, teeth=teeth, rng=rng, back=h < 0.3)


def write_part(mesh, kit):
	mesh.write(os.path.join(OUT, mesh.name + ".obj"))
	kit[mesh.name] = mesh.tris


MAIN_TIERS = ((0.8, 3, 22), (0.42, 5, 30), (0.0, 5, 38))
SIDE_TIERS = ((0.62, 3, 20), (0.12, 4, 32), (-0.42, 4, 30))


def broadleaf_lobes(scale=1.0):
	lobes = [
		{"c": (0.5, 23.0, -0.5), "r": (7.6, 6.0, 7.6), "tiers": MAIN_TIERS},
		{"c": (-7.0, 18.2, 3.0), "r": (6.2, 5.0, 6.0), "tiers": SIDE_TIERS},
		{"c": (7.4, 16.6, 2.6), "r": (6.6, 5.2, 6.2), "tiers": SIDE_TIERS},
		{"c": (1.8, 15.2, 7.4), "r": (6.0, 4.6, 5.6), "tiers": SIDE_TIERS},
		{"c": (-1.6, 16.0, -7.4), "r": (6.4, 5.0, 6.0), "tiers": SIDE_TIERS},
	]
	return [{**l, "c": tuple(np.array(l["c"]) * scale), "r": tuple(np.array(l["r"]) * scale)} for l in lobes]


def build_broadleaf(name, leaves, bark, seed, scale=1.0, teeth=0, shapes=("A", "B")):
	rng = np.random.default_rng(seed)
	crown, trunk = Mesh(name + "_Crown"), Mesh(name + "_Trunk")
	lobes = broadleaf_lobes(scale)
	build_crown(crown, leaves, lobes, rng, shapes, teeth=teeth)
	# the trunk: flared foot, chunky, then limbs that overlap it into each lobe
	s = scale
	tube(trunk, bark, name + "Main", [(0, -1.2 * s, 0), (0.1 * s, 1.0 * s, 0.05 * s), (0.4 * s, 4.5 * s, -0.1 * s), (0.2 * s, 9.0 * s, 0.1 * s), (0.5 * s, 13.0 * s, 0.0)], [2.5 * s, 1.75 * s, 1.35 * s, 1.15 * s, 0.85 * s], rng, foot=True)
	for i, l in enumerate(lobes[:5]):
		c = np.array(l["c"])
		start = np.array((0.3 * s, (8.0 + i * 1.4) * s, 0.0))
		midp = start * 0.45 + c * 0.55 + np.array((0, -1.0 * s, 0))
		tube(trunk, bark, f"{name}Limb{i}", [start, midp, c], [0.95 * s, 0.62 * s, 0.26 * s], rng)
	for l in lobes:
		core_lobe(trunk, bark, tuple(np.array(l["c"]) + np.array((0, l["r"][1] * 0.12, 0))), tuple(np.array(l["r"]) * np.array((0.74, 0.62, 0.74))), rng)
	return crown, trunk


def build_bush(name, leaves, bark, seed, teeth=0):
	rng = np.random.default_rng(seed)
	crown, trunk = Mesh(name + "_Crown"), Mesh(name + "_Core")
	lobes = [
		{"c": (0.0, 2.4, 0.0), "r": (3.8, 2.7, 3.8), "tiers": ((0.75, 3, 34), (0.15, 5, 20), (-0.45, 4, 8))},
		{"c": (2.7, 1.7, 1.2), "r": (2.9, 2.0, 2.9), "tiers": ((0.6, 2, 30), (-0.1, 4, 14))},
		{"c": (-2.3, 1.6, 1.5), "r": (2.8, 1.9, 2.8), "tiers": ((0.6, 2, 30), (-0.1, 4, 14))},
	]
	build_crown(crown, leaves, lobes, rng, ("A", "B"), teeth=teeth, skip_inside=0.6)
	for l in lobes:
		core_lobe(trunk, bark, l["c"], tuple(np.array(l["r"]) * 0.74), rng)
	return crown, trunk


def main():
	leaves = LeafSheet()
	leaves.add_shape("A", spray_strokes(11))
	leaves.add_shape("B", spray_strokes(29, count=230, fan=1.15))
	bark = BarkSheet()
	kit = {}
	# the test: one tree and one bush, two ways. A: painted planes with alpha. B: no alpha, feathers modelled
	for name, teeth in (("TestA", 0), ("TestB", 4)):
		for part in build_broadleaf(name, leaves, bark, 41, teeth=teeth) + build_bush(name + "Bush", leaves, bark, 7, teeth=teeth):
			write_part(part, kit)
	leaves.save(os.path.join(OUT, "Tree_Leaves.png"))
	# B uses the same sheet with its alpha ignored
	Image.fromarray(np.clip(leaves.rgb, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "Tree_Leaves_Solid.png"))
	bark.save(os.path.join(OUT, "Tree_Bark.png"))
	json.dump({"Triangles": kit}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print(kit)


main()
