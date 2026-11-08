"""Paints the stone sword's sheets (docs/style/stone-sword.md), from tools/blender/stone_sword.py's bake.npz and layout.json.

  python tools/art/paint_sword.py [--only BF,GF]

Painted the way a person would, in layers of real brush marks, not filtered noise:
  plane tones -> big gouache patches -> long streaks -> fine dry-brush -> runes -> moss dabs (dark, mid, light) and moss runs -> cracks -> ink -> soft pale edges.
Every stroke keeps to the flat face it started on, so ridges and chips stay crisp, and frays at its ends, which is the streaky look.
Canvases are painted at twice the sheet's size in sRGB, then sized down.
"""

import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "sword")
SS = 2  # canvases are this many times the sheet's size
# Studio's sky adds blue: measured in the place, lit stone came out 175, 188, 179 against the reference's 165, 185, 152, and moss 108, 143, 89 against 114, 135, 70
GRADE = np.array((0.97, 0.99, 0.85), dtype=np.float32)

layout = json.load(open(os.path.join(OUT, "layout.json")))
W, LB = layout["Params"]["W"], layout["Params"]["LB"]
GRIP_R = layout["Params"]["GripR"]
BASE = LB + 0.38 * W  # where the grip starts

# colours measured from the reference (k-means over its blades, guards and grips), sRGB
STONE = np.array(
	[
		(0.00, 38, 52, 56),
		(0.18, 68, 84, 84),
		(0.34, 100, 114, 116),  # the slate of the shaded faces
		(0.48, 132, 146, 134),
		(0.62, 166, 172, 146),
		(0.78, 190, 194, 165),
		(1.00, 214, 217, 189),
	],
	dtype=np.float32,
)
# the reference's tones, measured on its guards: a flat mid green, a darker olive, a very slight lift, near-black ticks.
# Trimmed against Studio: 124, 146, 78 came out 112, 150, 77 in the place, the reference's being 115, 136, 66
MOSS_DEEP = np.array((40, 56, 32), dtype=np.float32)
MOSS_DARK = np.array((88, 100, 56), dtype=np.float32)
MOSS_MID = np.array((127, 134, 74), dtype=np.float32)
MOSS_LIGHT = np.array((149, 155, 88), dtype=np.float32)
INK = np.array((26, 38, 40), dtype=np.float32)
PALE = np.array((236, 238, 214), dtype=np.float32)

LIGHTS = {"F": (0.55, -0.42, 0.72), "B": (-0.55, 0.42, 0.72), "R": (0.75, -0.3, 0.6), "L": (-0.75, 0.3, 0.6), "U": (0.3, -0.2, 0.93), "D": (0.3, -0.2, 0.93)}


def ramp(t):
	t = np.clip(t, 0, 1)
	return np.stack([np.interp(t, STONE[:, 0], STONE[:, i]) for i in (1, 2, 3)], axis=-1).astype(np.float32)


def smooth(a, b, x):
	k = np.clip((x - a) / (b - a), 0, 1)
	return k * k * (3 - 2 * k)


def field(shape, sx, sy, seed):
	"""soft random shapes, about sx by sy pixels; used only to decide where marks go, never drawn itself"""
	h, w = shape
	rng = np.random.default_rng(seed)
	small = rng.normal(size=(max(4, int(h / sy) + 4), max(4, int(w / sx) + 4)))
	small = ndimage.gaussian_filter(small, 0.8, mode="wrap")
	img = Image.fromarray(small.astype(np.float32), mode="F").resize((w, h), Image.BICUBIC)
	out = np.asarray(img, dtype=np.float32)
	return (out - out.mean()) / (out.std() + 1e-6)


class Canvas:
	def __init__(self, name):
		self.name = name
		info = layout["Canvases"][name]
		self.u0, self.v0, self.u1, self.v1 = info["U0"], info["V0"], info["U1"], info["V1"]
		self.s = info["Scale"] * SS
		self.w = math.ceil((self.u1 - self.u0) * self.s)
		self.h = math.ceil((self.v1 - self.v0) * self.s)
		self.kind = name[-1]
		self.rng = np.random.default_rng(abs(hash_name(name)))
		self.raster(np.load(os.path.join(OUT, "bake.npz")))
		self.c = np.zeros((self.h, self.w, 3), dtype=np.float32)

	def px(self, u, v):
		return (u - self.u0) * self.s, (self.v1 - v) * self.s

	def raster(self, bake):
		uvw = bake[self.name + "_uvw"]
		pos, nor, fn = bake[self.name + "_pos"], bake[self.name + "_nor"], bake[self.name + "_fn"]
		self.mask = np.zeros((self.h, self.w), dtype=bool)
		self.P = np.zeros((self.h, self.w, 3), dtype=np.float32)
		self.N = np.zeros((self.h, self.w, 3), dtype=np.float32)
		self.F = np.zeros((self.h, self.w, 3), dtype=np.float32)
		depth = np.full((self.h, self.w), -1e9, dtype=np.float32)
		for t in range(len(uvw)):
			xs, ys = self.px(uvw[t, :, 0], uvw[t, :, 1])
			x0, x1 = max(int(xs.min()) - 1, 0), min(int(xs.max()) + 2, self.w)
			y0, y1 = max(int(ys.min()) - 1, 0), min(int(ys.max()) + 2, self.h)
			if x0 >= x1 or y0 >= y1:
				continue
			area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
			if abs(area) < 1e-6:
				continue
			gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
			b0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
			b1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
			b2 = 1 - b0 - b1
			inside = (b0 >= -0.02) & (b1 >= -0.02) & (b2 >= -0.02)
			d = b0 * uvw[t, 0, 2] + b1 * uvw[t, 1, 2] + b2 * uvw[t, 2, 2]
			write = inside & (d >= depth[y0:y1, x0:x1])
			if not write.any():
				continue
			depth[y0:y1, x0:x1][write] = d[write]
			self.mask[y0:y1, x0:x1][write] = True
			bary = np.stack([b0[write], b1[write], b2[write]], axis=-1)
			self.P[y0:y1, x0:x1][write] = bary @ pos[t]
			self.N[y0:y1, x0:x1][write] = bary @ nor[t]
			self.F[y0:y1, x0:x1][write] = fn[t]
		# flat faces get an id, so a stroke can keep to its face
		q = np.round(self.F * 7).astype(np.int32)
		self.ids = (q[..., 0] + 8) * 289 + (q[..., 1] + 8) * 17 + (q[..., 2] + 8)
		self.ids[~self.mask] = -1
		yy, xx = np.nonzero(self.mask)
		self.yy, self.xx = yy, xx

	def stroke(self, x, y, length, width, angle, colour, opacity=1.0, dry=0.0, fray=0.2, round_=False, stay=True, mask=None):
		"""one brush mark. dry = how much the bristles skip; fray = how raggedly its ends stop"""
		rng = self.rng
		reach = (length + width) / 2 + 1
		ca, sa = math.cos(angle), math.sin(angle)
		ex = abs(ca) * length / 2 + abs(sa) * width / 2 + 1
		ey = abs(sa) * length / 2 + abs(ca) * width / 2 + 1
		x0, x1 = max(int(x - ex), 0), min(int(x + ex) + 1, self.w)
		y0, y1 = max(int(y - ey), 0), min(int(y + ey) + 1, self.h)
		if x0 >= x1 or y0 >= y1:
			return
		ys, xs = np.ogrid[y0:y1, x0:x1]
		dx, dy = xs - x, ys - y
		s = dx * ca + dy * sa
		t = -dx * sa + dy * ca
		bristles = max(3, int(width / 1.6))
		idx = np.clip(((t / max(width, 1) + 0.5) * bristles).astype(np.int32), 0, bristles - 1)
		along = s + length / 2
		start = rng.random(bristles) ** 2 * fray * length
		end = rng.random(bristles) ** 2 * fray * length
		a = (along >= start[idx]) & (along <= length - end[idx])
		if round_:
			r = np.clip(2 * s / max(length, 1), -1, 1)
			a &= np.abs(t) <= (width / 2) * np.sqrt(1 - r * r) * (0.85 + 0.3 * rng.random(bristles))[idx]
		else:
			a &= np.abs(t) <= width / 2
		if dry > 0:
			strength = rng.random(bristles)
			strength = (strength + np.roll(strength, 1)) / 2
			runs = rng.random((24, bristles))
			cell = np.clip((along / max(length, 1) * 24).astype(np.int32), 0, 23)
			a &= strength[idx] * 0.72 + runs[cell, idx] * 0.28 > dry
		if stay:
			cy, cx = int(min(max(y, 0), self.h - 1)), int(min(max(x, 0), self.w - 1))
			face = self.ids[cy, cx]
			a &= self.ids[y0:y1, x0:x1] == face
		else:
			a &= self.mask[y0:y1, x0:x1]
		if mask is not None:
			a &= mask[y0:y1, x0:x1]
		if not a.any():
			return
		block = self.c[y0:y1, x0:x1]
		block[a] += (colour - block[a]) * opacity

	def pick(self, count, weight=None):
		"""random painted pixels, likelier where weight is high"""
		if weight is None:
			i = self.rng.integers(0, len(self.yy), count)
		else:
			w = np.maximum(weight[self.yy, self.xx], 0).astype(np.float64)
			total = w.sum()
			if total <= 0:
				return np.zeros(0, int), np.zeros(0, int)
			i = self.rng.choice(len(self.yy), count, p=w / total)
		return self.xx[i], self.yy[i]

	def finish_fill(self):
		_, (iy, ix) = ndimage.distance_transform_edt(~self.mask, return_indices=True)
		self.c[~self.mask] = self.c[iy[~self.mask], ix[~self.mask]]


def hash_name(name):
	return sum((i + 1) * 131 * ord(ch) for i, ch in enumerate(name))


def plane_tone(cv, boost=2.2, centre=0.415, mid=0.55):
	"""each face one tone from its own direction: the light is painted in"""
	light = np.array(LIGHTS[cv.kind], dtype=np.float32)
	light /= np.linalg.norm(light)
	return mid + boost * ((cv.F @ light) - centre)


def strokes_on_form(cv, tone, count, length, width, angle, spread, jitter, opacity, dry, fray=0.3, weight=None, bias=0.0):
	"""many marks whose colours sit close to the form's tone at their middle"""
	rng = cv.rng
	xs, ys = cv.pick(count, weight)
	for x, y in zip(xs, ys):
		L = rng.uniform(*length)
		w = rng.uniform(*width)
		t = float(tone[y, x]) + rng.normal(bias, spread)
		col = ramp(np.array(t))
		col = col + rng.normal(0, 2.0, 3).astype(np.float32)
		cv.stroke(x, y, L, w, angle + rng.normal(0, jitter), col, rng.uniform(*opacity), dry=rng.uniform(*dry), fray=fray)


def paint_stone(cv, tone, along, big=1.0):
	"""three layers of marks along a direction: big patches, streaks, dry-brush"""
	s = cv.s
	cv.c[:] = ramp(tone)
	area = cv.mask.sum() / (s * s)  # square studs
	strokes_on_form(cv, tone, int(area / 26 * big) + 6, (s * 9, s * 34), (s * 1.2, s * 4.5), along, 0.06, 0.03, (0.45, 0.9), (0.0, 0.25), 0.3)
	# shapes that break the plane's tone: paler on shade, slate on light, as the reference's grey patches do
	strokes_on_form(cv, tone * 0.0 + 0.36, int(area / 80 * big) + 2, (s * 7, s * 26), (s * 1.2, s * 3.6), along, 0.035, 0.03, (0.35, 0.75), (0.1, 0.4), 0.38, weight=smooth(0.5, 0.75, tone))
	strokes_on_form(cv, tone * 0.0 + 0.66, int(area / 110 * big) + 2, (s * 6, s * 20), (s * 0.9, s * 2.6), along, 0.04, 0.03, (0.25, 0.55), (0.15, 0.45), 0.38, weight=smooth(0.5, 0.3, tone))
	strokes_on_form(cv, tone, int(area / 5 * big) + 4, (s * 1.5, s * 7), (s * 0.8, s * 3.0), along, 0.07, 0.07, (0.5, 0.95), (0.0, 0.25), 0.34)
	strokes_on_form(cv, tone, int(area / 5.5 * big), (s * 2.5, s * 14), (s * 0.15, s * 0.65), along, 0.07, 0.03, (0.25, 0.55), (0.35, 0.62), 0.42)
	strokes_on_form(cv, tone, int(area / 4.5 * big), (s * 0.9, s * 5), (s * 0.05, s * 0.16), along, 0.07, 0.04, (0.2, 0.5), (0.4, 0.65), 0.45)


def glaze(cv, tone, along, weight=None, amount=1.0):
	"""thin, broad, dry strokes of olive over the stone"""
	rng = cv.rng
	s = cv.s
	area = cv.mask.sum() / (s * s)
	xs, ys = cv.pick(int(area / 9 * amount) + 3, weight)
	for x, y in zip(xs, ys):
		stone = ramp(np.array(float(tone[y, x])))
		col = stone * 0.68 + moss_colour(MOSS_MID, float(tone[y, x])) * 0.32
		cv.stroke(x, y, rng.uniform(3, 18) * s, rng.uniform(0.5, 3.0) * s, along + rng.normal(0, 0.05), col, rng.uniform(0.18, 0.42), dry=rng.uniform(0.2, 0.5), fray=0.5, stay=False)


def moss_colour(base, tone):
	"""moss in shade is darker and cooler"""
	k = np.clip(0.62 + 0.62 * tone, 0.55, 1.08)
	return base * k


def clean_shape(cv, shape_mask, smallest, smallest_hole):
	"""big grouped shapes only: no small islands, no pinholes (sizes in pixels)"""
	labels, count = ndimage.label(shape_mask)
	if count:
		sizes = ndimage.sum_labels(shape_mask, labels, index=np.arange(1, count + 1))
		shape_mask = np.concatenate([[False], sizes >= smallest])[labels]
	holes = cv.mask & ~shape_mask
	labels, count = ndimage.label(holes)
	if count:
		sizes = ndimage.sum_labels(holes, labels, index=np.arange(1, count + 1))
		shape_mask = shape_mask | np.concatenate([[False], sizes < smallest_hole])[labels]
	return shape_mask


def lay(cv, shape_mask, colour, opacity, soft):
	"""one flat tone: a wet soft edge in some stretches, a firmer one in others (soft = blur in studs)"""
	s = cv.s
	firm = ndimage.gaussian_filter(shape_mask.astype(np.float32), 1.3)
	wet = ndimage.gaussian_filter(shape_mask.astype(np.float32), s * soft)
	mix = smooth(-0.5, 0.7, field((cv.h, cv.w), s * 3.5, s * 3.5, hash_name(cv.name) + int(soft * 1000) + 41))
	alpha = (firm + (wet - firm) * mix)[..., None] * opacity
	cv.c += (colour - cv.c) * alpha


def paint_moss(cv, tone, density, dab=1.0, hangs=True):
	"""Grouped moss in two tones and a slight third, after the reference: one flat mid-green mass with short drips, thinning into the stone at its edges,
	a darker olive group along its lower edge and in a pool or two, a few patches barely lighter, and a few small clusters of dark ticks. No grain.
	hangs: on faces that aren't level, moss drips and pools at the bottom"""
	rng = cv.rng
	s = cv.s
	shape = (cv.h, cv.w)
	seed = hash_name(cv.name)
	big = field(shape, s * 3.6 * dab, s * 3.6 * dab, seed + 21)
	drip = field(shape, s * 1.1 * dab, s * (3.6 if hangs else 1.1) * dab, seed + 22)
	edge = field(shape, s * 0.42 * dab, s * 0.42 * dab, seed + 23)
	level = density + 0.14 * big + 0.12 * drip + 0.075 * edge
	unit = s * s * dab * dab
	mass = clean_shape(cv, (level > 0.6) & cv.mask, 4 * unit, 0.7 * unit)
	if mass.sum() < 2 * unit:
		return mass
	base = moss_colour(MOSS_MID, tone[..., None])
	base = base * (1 + 0.03 * field(shape, s * 4, s * 4, seed + 27))[..., None]

	# dry-brush: no new colours, but near its edges the moss skips along the bristles and stone shows through; past the edge a few dry marks
	bristles = field(shape, s * 0.17, s * (1.5 if hangs else 0.17), seed + 28)
	depth = ndimage.distance_transform_edt(mass).astype(np.float32) / s
	skip = mass & (depth < 0.8 * dab) & (bristles < -0.25 + 0.9 * (depth / (0.8 * dab)) - 0.45)
	marks_out = (level > 0.47) & cv.mask & ~mass & (bristles > 0.35)
	lay(cv, marks_out, base, 0.5, 0.03)
	lay(cv, mass & ~skip, base, 0.95, 0.09)

	# painted, not printed: broad marks barely apart from the base colour, along the brush
	area = mass.sum() / (s * s)
	direction = math.pi / 2 if hangs else 0.0
	xs, ys = cv.pick(int(area / 7) + 2, mass.astype(np.float32))
	for x, y in zip(xs, ys):
		col = moss_colour(MOSS_MID, float(tone[y, x])) * rng.uniform(0.92, 1.05)
		cv.stroke(x, y, rng.uniform(1.5, 6) * s, rng.uniform(0.5, 1.9) * s, direction + rng.normal(0, 0.12), col, rng.uniform(0.45, 0.8), dry=rng.uniform(0.05, 0.3), fray=0.5, stay=False, mask=mass & ~skip)

	# the darker group: along the lower edge, and a pool or two inside, with the same brushed edge
	below = np.zeros(shape, dtype=np.float32)
	for row in range(cv.h - 2, -1, -1):
		below[row] = (below[row + 1] + 1) * mass[row]
	below /= s
	wander = field(shape, s * 2.2, s * 1.0, seed + 24) + 0.5 * edge
	thickness = np.clip(0.75 + 0.6 * wander, 0.1, 2.0) * dab
	pool = field(shape, s * 2.2 * dab, s * 2.4 * dab, seed + 25) + 0.25 * edge > (1.3 if hangs else 0.9)
	dark = ((below < thickness) if hangs else np.zeros(shape, dtype=bool)) | pool
	dark = clean_shape(cv, dark & mass & ~skip, 0.9 * unit, 0.3 * unit)
	lay(cv, dark, moss_colour(MOSS_DARK, tone[..., None]), 0.8, 0.05)

	# barely lighter: few, and away from the lower edge
	lift = field(shape, s * 2.0 * dab, s * 1.4 * dab, seed + 26) + 0.3 * edge > 1.2
	light = clean_shape(cv, lift & mass & ~dark & ~skip & (below > 0.9), 0.8 * unit, 0.3 * unit)
	lay(cv, light, moss_colour(MOSS_LIGHT, tone[..., None]), 0.75, 0.05)

	# a few clusters of little dark marks, mostly near the lower edge
	near_edge = (mass & (below < 2.0 * dab)).astype(np.float32) + 0.05 * mass
	xs, ys = cv.pick(max(1, int(area / 26)), near_edge)
	for x, y in zip(xs, ys):
		spread = rng.uniform(0.7, 1.5) * s * dab
		for i in range(int(rng.integers(3, 6))):
			px = x + (i - 2) * spread * 0.45 + rng.normal(0, spread * 0.12)
			py = y + rng.normal(0, spread * 0.22)
			cv.stroke(px, py, rng.uniform(0.25, 0.6) * s, rng.uniform(0.08, 0.15) * s, math.pi / 2 + rng.normal(0, 0.3), moss_colour(MOSS_DEEP, 0.6), rng.uniform(0.65, 0.9), round_=True, stay=False)
	return mass


def poly_mask(cv, draw_fn):
	img = Image.new("L", (cv.w, cv.h), 0)
	draw_fn(ImageDraw.Draw(img))
	return np.asarray(img, dtype=np.float32) / 255


def blend(cv, alpha, colour):
	alpha = (alpha * cv.mask)[..., None]
	cv.c += (colour - cv.c) * alpha


RUNES = [
	[[(-0.25, -0.5), (-0.25, 0.5)], [(-0.25, 0.1), (0.25, 0.45)], [(-0.25, -0.15), (0.25, 0.2)]],
	[[(-0.25, -0.5), (-0.25, 0.5), (0.25, 0.1), (0.25, -0.5)]],
	[[(-0.2, -0.5), (-0.2, 0.5)], [(-0.2, 0.3), (0.25, 0.0), (-0.2, -0.3)]],
	[[(-0.2, -0.5), (-0.2, 0.5), (0.25, 0.2)], [(-0.2, 0.15), (0.25, -0.15)]],
	[[(-0.25, -0.5), (-0.25, 0.5), (0.2, 0.25), (-0.25, 0.0), (0.25, -0.5)]],
	[[(0.2, 0.5), (-0.25, 0.0), (0.2, -0.5)]],
	[[(-0.3, 0.5), (0.3, -0.5)], [(0.3, 0.5), (-0.3, -0.5)]],
	[[(-0.2, -0.5), (-0.2, 0.5), (0.25, 0.2), (-0.2, -0.1)]],
	[[(-0.25, -0.5), (-0.25, 0.5)], [(0.25, -0.5), (0.25, 0.5)], [(-0.25, 0.2), (0.25, -0.2)]],
	[[(0.0, -0.5), (0.0, 0.5)], [(-0.3, 0.2), (0.3, -0.1)]],
	[[(0.0, -0.5), (0.0, 0.5), (0.28, 0.25)], [(0.0, -0.5), (-0.28, -0.25)]],
	[[(-0.25, -0.5), (-0.25, 0.5), (0.2, 0.2)], [(-0.25, -0.5), (0.2, -0.2)]],
	[[(0.0, -0.5), (0.0, 0.5)], [(-0.3, 0.45), (0.0, 0.1), (0.3, 0.45)]],
	[[(0.2, 0.5), (-0.2, 0.1), (0.2, -0.1), (-0.2, -0.5)]],
	[[(0.0, -0.5), (0.0, 0.5)], [(-0.28, 0.2), (0.0, 0.5), (0.28, 0.2)]],
	[[(-0.2, -0.5), (-0.2, 0.5), (0.22, 0.25), (-0.2, 0.0), (0.22, -0.25), (-0.2, -0.5)]],
	[[(-0.25, -0.5), (-0.25, 0.5), (0.0, 0.1), (0.25, 0.5), (0.25, -0.5)]],
	[[(-0.25, -0.5), (-0.25, 0.5), (0.25, -0.1)], [(0.25, -0.5), (0.25, 0.5), (-0.25, -0.1)]],
	[[(-0.3, -0.5), (0.22, 0.05), (0.0, 0.5), (-0.22, 0.05), (0.3, -0.5)]],
	[[(-0.28, -0.4), (-0.28, 0.4), (0.28, -0.4), (0.28, 0.4), (-0.28, -0.4)]],
]


def draw_runes(cv, columns, size, gap, z_top, count, tones):
	"""carved letters: a dark stroke, a pale catch-light just below it, a lighter floor inside the thick parts"""
	rng = cv.rng
	s = cv.s
	rng_shape = np.random.default_rng(hash_name(cv.name) + 31)
	for u_of_z, tone_note in columns:
		order = rng.permutation(len(RUNES))
		lines = []
		z = z_top
		for i in range(count):
			glyph = RUNES[order[i % len(RUNES)]]
			u = u_of_z(z) + rng.normal(0, 0.03 * W)
			turn = rng.normal(0, 0.09)
			h = size * rng.uniform(0.9, 1.08)
			for pl in glyph:
				pts = []
				for gx, gy in pl:
					x = gx * math.cos(turn) - gy * math.sin(turn)
					y = gx * math.sin(turn) + gy * math.cos(turn)
					pts.append(cv.px(u + x * h + rng.normal(0, 0.008 * h), z + y * h + rng.normal(0, 0.008 * h)))
				lines.append(pts)
			z -= gap * rng.uniform(0.94, 1.08)
		width = size * s * 0.135

		def stroke_lines(draw, w):
			for pts in lines:
				for (ax, ay), (bx, by) in zip(pts, pts[1:]):
					# each stroke bows slightly and goes from thick to thin
					mx, my = (ax + bx) / 2 + rng_shape.normal(0, 0.012 * size * s), (ay + by) / 2 + rng_shape.normal(0, 0.012 * size * s)
					wa, wm, wb = w * rng_shape.uniform(0.8, 1.2), w * rng_shape.uniform(0.85, 1.15), w * rng_shape.uniform(0.5, 1.0)
					for p, q, u0, u1 in (((ax, ay), (mx, my), wa, wm), ((mx, my), (bx, by), wm, wb)):
						dx, dy = q[0] - p[0], q[1] - p[1]
						n = math.hypot(dx, dy) + 1e-3
						nx, ny = -dy / n / 2, dx / n / 2
						draw.polygon([(p[0] + nx * u0, p[1] + ny * u0), (q[0] + nx * u1, q[1] + ny * u1), (q[0] - nx * u1, q[1] - ny * u1), (p[0] - nx * u0, p[1] - ny * u0)], fill=255)
						draw.ellipse((q[0] - u1 / 2, q[1] - u1 / 2, q[0] + u1 / 2, q[1] + u1 / 2), fill=255)

		body = poly_mask(cv, lambda d: stroke_lines(d, width))
		floor = poly_mask(cv, lambda d: stroke_lines(d, max(1.0, width * 0.34)))
		catch = np.roll(np.roll(body, int(width * 0.34), axis=0), int(width * 0.22), axis=1) * (1 - body)
		wear = smooth(-1.4, 0.2, field((cv.h, cv.w), s * 1.1, s * 1.1, hash_name(cv.name) + 7 + int(tone_note * 10)))
		blend(cv, ndimage.gaussian_filter(catch, 0.8) * 0.5 * tone_note, PALE)
		blend(cv, body * (0.66 + 0.3 * wear), INK * 1.3 + 8)
		blend(cv, floor * 0.45, ramp(np.array(0.2 + 0.1 * tone_note)))


def crack_line(rng, start, direction, length, wander):
	"""a jagged walk; returns points in studs"""
	pts = [start]
	a = direction
	left = length
	while left > 0:
		step = rng.uniform(0.7, 2.6)
		a += rng.normal(0, wander)
		a = direction + np.clip(a - direction, -0.9, 0.9)
		x, y = pts[-1]
		pts.append((x + math.cos(a) * step, y + math.sin(a) * step))
		left -= step
	return pts


def draw_cracks(cv, cracks):
	"""ink that thins toward its tip, with a light chipped lip on one side"""
	rng = cv.rng
	s = cv.s
	ink = np.zeros((cv.h, cv.w), dtype=np.float32)
	img = Image.new("L", (cv.w, cv.h), 0)
	d = ImageDraw.Draw(img)
	for pts, width in cracks:
		n = len(pts)
		for i in range(n - 1):
			a, b = cv.px(*pts[i]), cv.px(*pts[i + 1])
			w = max(2, int((width * (1 - i / n) ** 0.6) * s * rng.uniform(0.7, 1.35)))
			d.line((a, b), fill=255, width=w)
	ink = np.asarray(img, dtype=np.float32) / 255
	lip = np.roll(np.roll(ink, 3, axis=0), 3, axis=1) * (1 - ink)
	blend(cv, ndimage.gaussian_filter(lip, 1.0) * 0.55, PALE)
	blend(cv, ink * 0.96, INK)


def ink_and_edges(cv, angle_ink, tone, width=1.5, strength=1.0, pale=0.4, boundary=True, faint=None):
	"""lines where flat faces meet, each with its own rhythm: firm runs, thin stretches, gaps; a soft pale band beside them on the sun side"""
	s = cv.s
	F = cv.F
	cos = np.cos(np.radians(angle_ink))
	edge = np.zeros((cv.h, cv.w), dtype=bool)
	for axis in (0, 1):
		shifted = np.roll(F, 1, axis=axis)
		dot = (F * shifted).sum(-1)
		both = cv.mask & np.roll(cv.mask, 1, axis=axis)
		edge |= both & (dot < cos)
		if boundary:
			edge |= cv.mask ^ np.roll(cv.mask, 1, axis=axis)
	dist = ndimage.distance_transform_edt(~edge).astype(np.float32)
	rhythm = field((cv.h, cv.w), s * 5, s * 5, hash_name(cv.name) + 11)
	rough = field((cv.h, cv.w), s * 1.6, s * 1.6, hash_name(cv.name) + 13)
	w = (width * (cv.s / 34)) * (1.05 + 0.38 * rhythm + 0.14 * rough)
	alpha = np.clip(w - dist, 0, 1)
	blend(cv, alpha * strength, INK)
	if pale > 0:
		band = np.exp(-(((dist - w - 3.5 * cv.s / 34) / (2.6 * cv.s / 34)) ** 2))
		runs = smooth(-0.3, 1.1, field((cv.h, cv.w), s * 7, s * 11, hash_name(cv.name) + 17))
		lit = smooth(0.42, 0.72, tone)
		blend(cv, band * runs * lit * pale, PALE)


def flecks(cv, tone, count, weight=None):
	rng = cv.rng
	s = cv.s
	xs, ys = cv.pick(count, weight)
	for x, y in zip(xs, ys):
		dark = rng.random() < 0.72
		col = (INK * 1.5 + 6) if dark else PALE
		cv.stroke(x, y, rng.uniform(0.08, 0.5) * s, rng.uniform(0.05, 0.16) * s, rng.uniform(0, 3.14), col, rng.uniform(0.4, 0.85), round_=True, stay=False)


# ------------------------------------------------------------------ the blade


def blade_half(z):
	k = (z + layout["Params"]["BURY"]) / (LB + layout["Params"]["BURY"])
	return W / 2 * (0.85 + 0.15 * k)


def tongue_shadow(cv, sign):
	"""the guard's painted cast shadow on the blade: its underside's outline, dropped and shifted away from the sun, crisp like the reference's"""
	u = W
	under = [(-1.0, 0.1), (-0.5, 0.1), (-0.5, -0.1), (-0.3, -0.42), (-0.14, -0.62), (0.03, -0.82), (0.2, -0.56), (0.34, -0.36), (0.46, -0.16), (0.5, 0.1), (1.0, 0.1), (1.0, 1.0), (-1.0, 1.0)]
	pts = [cv.px((x - 0.05) * u * sign if False else (x - 0.05) * u, LB + z * u - 0.6) for x, z in under]
	m = poly_mask(cv, lambda d: d.polygon(pts, fill=255))
	return ndimage.gaussian_filter(m, 1.2)


def paint_blade_face(cv):
	s = cv.s
	front = cv.kind == "F"
	z = cv.P[..., 2]
	tone = np.clip(plane_tone(cv, boost=2.0, mid=0.52), 0.31, 0.72)
	# darker and damper toward the foot; lit a touch near the top
	tone = tone - 0.13 * smooth(0.42 * LB, 0.0, z) + 0.03 * smooth(0.5 * LB, LB, z)
	shadow = tongue_shadow(cv, 1 if front else -1)
	tone = tone - 0.34 * shadow
	tone = np.where(z < 0.5, 0.2, tone)
	along = math.pi / 2
	paint_stone(cv, tone, along, big=1.0)

	# long dark stains running down from the guard and the chips
	stain = smooth(LB - 1.7 * W, LB - 0.2 * W, z) + 0.08
	strokes_on_form(cv, tone, 30, (s * 6, s * 34), (s * 0.2, s * 1.0), along, 0.03, 0.015, (0.25, 0.5), (0.35, 0.6), 0.7, weight=stain, bias=-0.15)

	# runes: a column down the middle of each big face
	sign = 1.0
	def lit_column(zz):
		return sign * 0.47 * blade_half(zz)
	def shade_column(zz):
		return -sign * 0.47 * blade_half(zz)
	seed_shift = 0.0 if front else 0.05
	draw_runes(cv, [(lit_column, 1.0), (shade_column, 0.55)], 0.19 * W, 0.272 * W, LB - (0.92 + seed_shift) * W, 13, tone)
	# the incised line along each face
	lines = []
	for side in (1, -1):
		pts = []
		for zz in np.arange(LB - 0.75 * W, 0.16 * LB, -4.0):
			pts.append((side * (0.82 * blade_half(zz)) + cv.rng.normal(0, 0.03), zz))
		start = int(cv.rng.integers(0, 3))
		lines.append((pts[start:], 0.08))
	draw_cracks(cv, lines)

	# where the moss grows
	u = (cv.P[..., 0] if front else -cv.P[..., 0])
	a = u / np.maximum(W / 2 * (0.85 + 0.15 * np.clip(z / LB, 0, 1)), 1)
	zn = z / LB
	wig = field((cv.h, cv.w), s * 3, s * 9, hash_name(cv.name) + 1)
	wob = field((cv.h, cv.w), s * 1.5, s * 3, hash_name(cv.name) + 2)
	patches = (
		[(0.7, 0.56, 1.02, 0.26), (-0.76, 0.66, 1.02, 0.3), (0.3, -0.05, 0.2, 0.8), (-0.55, -0.05, 0.3, 0.55), (0.6, 0.2, 0.36, 0.3), (0.14, 0.92, 1.03, 0.24), (-0.84, 0.4, 0.5, 0.12), (0.84, 0.44, 0.56, 0.14)]
		if front
		else [(-0.7, 0.52, 1.02, 0.28), (0.74, 0.7, 1.02, 0.26), (-0.35, -0.05, 0.25, 0.75), (0.5, -0.05, 0.24, 0.6), (-0.62, 0.24, 0.36, 0.26), (-0.1, 0.93, 1.03, 0.24), (0.84, 0.34, 0.45, 0.14)]
	)
	density = np.zeros((cv.h, cv.w), dtype=np.float32)
	for a0, z0, z1, wd in patches:
		across = 1 - ((a - a0 + 0.1 * wob) / wd) ** 2
		mid, half = (z0 + z1) / 2, (z1 - z0) / 2
		lengthwise = 1 - ((zn - mid + 0.012 * wig) / half) ** 2
		density = np.maximum(density, np.clip(across, 0, 1) ** 0.6 * np.clip(lengthwise * 3, 0, 1))
	density[~cv.mask] = 0
	glaze(cv, tone, math.pi / 2, smooth(-0.1, 0.5, density) + 0.12)
	paint_moss(cv, tone, density)

	# cracks: one across the lower blade, one up from the foot, small ones
	rng = cv.rng
	right = 1.0
	cracks = [
		(crack_line(rng, (right * 0.5 * W, 0.235 * LB), math.pi - 0.28, 0.52 * W, 0.34), 0.34),
		(crack_line(rng, (-right * 0.1 * W, 0.235 * LB - 3), math.pi + 0.5, 0.4 * W, 0.3), 0.24),
		(crack_line(rng, (-right * 0.3 * W, 0.0), math.pi / 2 + 0.1, 0.27 * LB, 0.2), 0.32),
		(crack_line(rng, (right * 0.2 * W, 0.05 * LB), math.pi / 2 - 0.15, 0.13 * LB, 0.24), 0.22),
		(crack_line(rng, (right * 0.47 * W, 0.67 * LB), math.pi - 0.15, 0.2 * W, 0.4), 0.2),
		(crack_line(rng, (-right * 0.45 * W, 0.53 * LB), 0.2, 0.26 * W, 0.4), 0.22),
	]
	draw_cracks(cv, cracks)
	ink_and_edges(cv, 8, tone, width=2.0, pale=0.24)
	flecks(cv, tone, 70, smooth(0.5, 0.0, density))
	return tone


def paint_blade_side(cv):
	s = cv.s
	z = cv.P[..., 2]
	tone = np.clip(plane_tone(cv, boost=0.4, centre=0.3, mid=0.42), 0.3, 0.6)
	tone = tone - 0.14 * smooth(0.4 * LB, 0.0, z)
	tone = np.where(z < 0.5, 0.2, tone)
	paint_stone(cv, tone, math.pi / 2, big=1.6)
	wig = field((cv.h, cv.w), s * 3, s * 11, hash_name(cv.name) + 1)
	zn = z / LB
	density = np.clip(smooth(0.26, 0.05, zn) + smooth(0.74, 0.96, zn) * 0.9 + 0.45 * smooth(0.5, 1.5, wig), 0, 1)
	density[~cv.mask] = 0
	glaze(cv, tone, math.pi / 2, density + 0.2)
	paint_moss(cv, tone, density, dab=0.55)
	ink_and_edges(cv, 8, tone, width=1.3, pale=0.25, boundary=False)
	flecks(cv, tone, 12)


def paint_cap(cv):
	s = cv.s
	tone = plane_tone(cv, boost=0.3, centre=0.9, mid=0.72 if cv.kind == "U" else 0.2)
	paint_stone(cv, tone, 0.0, big=2.0)
	if cv.kind == "U":
		density = smooth(-1.0, 0.6, field((cv.h, cv.w), s * 2, s * 2, hash_name(cv.name) + 1)) * cv.mask
		paint_moss(cv, tone, density, dab=0.6, hangs=False)
	ink_and_edges(cv, 20, tone, width=1.2, pale=0.2, boundary=False)


# ------------------------------------------------------------------ the guard


def guard_emblem(cv):
	"""the shield drawn on the tongue: its outline from the grip's collar down to the point, a small arch round a diamond"""
	u = W
	rng = cv.rng

	def wander(pts, step=1.6):
		out = []
		for (ax, az), (bx, bz) in zip(pts, pts[1:]):
			n = max(1, int(math.hypot(bx - ax, bz - az) * u / step))
			for i in range(n):
				k = i / n
				out.append(((ax + (bx - ax) * k) * u + rng.normal(0, 0.05), LB + (az + (bz - az) * k) * u + rng.normal(0, 0.05)))
		out.append((pts[-1][0] * u, LB + pts[-1][1] * u))
		return out

	shield = [(-0.31, 0.42), (-0.37, 0.16), (-0.23, -0.14), (0.0, -0.45), (0.23, -0.14), (0.37, 0.16), (0.31, 0.42)]
	arch = [(0.15 * math.cos(math.pi * i / 12), 0.1 + 0.2 * math.sin(math.pi * i / 12)) for i in range(13)]
	inner = [(0.15, 0.1)] + arch[1:12] + [(-0.15, 0.1), (0.0, -0.2), (0.15, 0.1)]
	diamond = [(0, 0.2), (0.055, 0.1), (0, 0.0), (-0.055, 0.1), (0, 0.2)]
	lines = [(shield, 0.2), (inner, 0.14), (diamond, 0.13), ([(0.37, 0.16), (0.62, 0.2), (0.82, 0.17)], 0.09), ([(-0.37, 0.16), (-0.64, 0.19), (-0.8, 0.16)], 0.09)]
	img = Image.new("L", (cv.w, cv.h), 0)
	d = ImageDraw.Draw(img)
	for pts, width in lines:
		path = wander(pts)
		for a, b in zip(path, path[1:]):
			d.line((cv.px(*a), cv.px(*b)), fill=255, width=max(2, int(width * cv.s * rng.uniform(0.72, 1.3))))
	m = np.asarray(img, dtype=np.float32) / 255
	m = m * smooth(-1.7, -0.5, field((cv.h, cv.w), cv.s * 1.4, cv.s * 1.4, 77))
	lip = np.roll(np.roll(m, 3, axis=0), 2, axis=1) * (1 - m)
	blend(cv, ndimage.gaussian_filter(lip, 0.9) * 0.4, PALE)
	blend(cv, m * 0.9, INK)


def paint_guard_face(cv):
	s = cv.s
	z = cv.P[..., 2]
	x = cv.P[..., 0] if cv.kind == "F" else -cv.P[..., 0]
	light = np.array(LIGHTS[cv.kind], dtype=np.float32)
	light /= np.linalg.norm(light)
	tone = 0.6 + 0.5 * ((cv.N @ light) - 0.42)
	# the arm rolls over: lighter on its upper half, dark at its underside; the tongue lit like a raised plate
	rel = (z - (LB - 0.05 * W)) / (0.55 * W)
	tone = tone + 0.16 * np.clip(rel - 0.35, -1, 1) + 0.05 * smooth(0.0, 1.25 * W, np.abs(x)) * 0
	tone = tone + 0.07 * (x / (1.15 * W))
	# the shield's plate a little lighter than the arms beside it, its lower half in the blade's light
	inside = (np.abs(x) < 0.36 * W - np.maximum(0, (LB + 0.1 * W - z)) * 0.72) & (z < LB + 0.42 * W)
	tone = tone + 0.05 * inside
	paint_stone(cv, tone, 0.0, big=1.5)
	# patches of slate cut across it, as on the foreground guard
	guard_emblem(cv)
	wig = field((cv.h, cv.w), s * 2.5, s * 1.6, hash_name(cv.name) + 1)
	wob = field((cv.h, cv.w), s * 1.1, s * 0.9, hash_name(cv.name) + 2)
	top = smooth(LB + 0.16 * W, LB + 0.42 * W, z + 0.9 * wig)
	ends = smooth(0.95 * W, 1.22 * W, np.abs(x)) * 0.55
	shoulder = smooth(0.42 * W, 0.2 * W, np.abs(np.abs(x) - 0.42 * W)) * smooth(LB + 0.05 * W, LB + 0.3 * W, z) * 0.6
	foot = smooth(LB + 0.02 * W, LB - 0.08 * W, z) * smooth(0.5 * W, 1.0 * W, np.abs(x)) * 0.5
	density = np.clip(top + ends * smooth(-0.8, 0.5, wig) + shoulder + foot * smooth(0.0, 1.0, wig), 0, 1)
	density[~cv.mask] = 0
	glaze(cv, tone, 0.0, smooth(-0.1, 0.5, density) + 0.3)
	paint_moss(cv, tone, density)
	cracks = [
		(crack_line(cv.rng, (0.72 * W, LB + 0.47 * W), -math.pi / 2 - 0.2, 0.33 * W, 0.4), 0.17),
		(crack_line(cv.rng, (-0.86 * W, LB - 0.02 * W), math.pi / 2 + 0.25, 0.3 * W, 0.4), 0.17),
		(crack_line(cv.rng, (1.1 * W, LB + 0.16 * W), math.pi - 0.1, 0.22 * W, 0.45), 0.13),
	]
	if cv.kind == "B":
		cracks = [([(-px, py) for px, py in pts], w) for pts, w in cracks]
	draw_cracks(cv, [([(p if cv.kind == "F" else p, q) for p, q in pts], w) for pts, w in cracks])
	ink_and_edges(cv, 36, tone, width=2.0, pale=0.3)
	flecks(cv, tone, 46, smooth(0.5, 0.0, density))


def paint_guard_other(cv):
	s = cv.s
	light = np.array(LIGHTS[cv.kind], dtype=np.float32)
	light /= np.linalg.norm(light)
	if cv.kind == "D":
		tone = 0.42 + 0.1 * (cv.N @ light)
		paint_stone(cv, tone, 0.0, big=1.6)
		ink_and_edges(cv, 36, tone, width=1.3, pale=0.0, boundary=False)
		return
	tone = 0.46 + 0.5 * ((cv.N @ light) - 0.5) if cv.kind != "U" else 0.66 + 0.25 * ((cv.N @ light) - 0.9)
	paint_stone(cv, tone, 0.0 if cv.kind == "U" else math.pi / 2, big=1.6)
	wig = field((cv.h, cv.w), s * 2.2, s * 1.2, hash_name(cv.name) + 1)
	wob = field((cv.h, cv.w), s * 0.9, s * 0.9, hash_name(cv.name) + 2)
	if cv.kind == "U":
		density = smooth(-1.3, -0.1, wig + 0.6 * wob)
	else:
		density = smooth(LB + 0.0 * W, LB + 0.36 * W, cv.P[..., 2] + 1.2 * wig)
	density = density * cv.mask
	paint_moss(cv, tone, density, hangs=cv.kind != "U")
	ink_and_edges(cv, 36, tone, width=1.6, pale=0.4, boundary=False)
	flecks(cv, tone, 24, smooth(0.5, 0.0, density))


# ------------------------------------------------------------------ the grip and pommel


def paint_grip(cv):
	s = cv.s
	z = cv.P[..., 2]
	u = np.arange(cv.w, dtype=np.float32)[None, :] / s + cv.u0
	theta = u / GRIP_R
	# round form: lit from the right of the front, again from the right of the back
	lit = np.cos(2 * theta - 0.9)
	tone = 0.53 + 0.17 * lit + 0.14 * (cv.N[..., 2])
	paint_stone(cv, tone, math.pi / 2, big=2.2)
	h = (z - BASE) / W
	# wrapping lines, one helix each way, stopping at the bands
	plain = ((h > 0.27) & (h < 0.95)) | ((h > 1.15) & (h < 1.62))
	rng = cv.rng
	img = Image.new("L", (cv.w, cv.h), 0)
	d = ImageDraw.Draw(img)
	rise = 0.42
	run = 2 * math.pi * GRIP_R
	for k in range(-1, 7):
		for sign, step in ((1, 1), (-1, 1.0)):
			z0 = BASE + 0.1 * W + k * rise * run * (0.5 if sign > 0 else 1.0)
			pts = []
			for uu in np.linspace(cv.u0, cv.u1, 40):
				pts.append(cv.px(uu, z0 + sign * (uu - cv.u0) * rise + rng.normal(0, 0.05)))
			if sign < 0 and rng.random() < 0.4:
				continue
			d.line(pts, fill=255, width=max(2, int((0.13 if sign > 0 else 0.08) * s)), joint="curve")
	wrap = np.asarray(img, dtype=np.float32) / 255 * plain
	lip = np.roll(np.roll(wrap, 3, axis=0), 0, axis=1) * (1 - wrap)
	blend(cv, ndimage.gaussian_filter(lip, 0.9) * 0.42, PALE)
	gaps = smooth(-1.1, -0.1, field((cv.h, cv.w), s * 2.5, s * 2.5, 5))
	blend(cv, wrap * gaps * 0.85, INK)
	# moss: lengthwise on the lower grip, in the grooves, on the collar tops
	wig = field((cv.h, cv.w), s * 1.5, s * 5.5, hash_name(cv.name) + 1)
	wob = field((cv.h, cv.w), s * 0.8, s * 1.2, hash_name(cv.name) + 2)
	lower = smooth(1.3, 0.45, h) * smooth(-0.6, 0.65, wig)
	upper = smooth(0.8, 1.3, h) * smooth(0.25, 1.2, wig)
	groove = sum(np.exp(-(((h - g) / 0.035) ** 2)) for g in (0.255, 0.98, 1.66, 1.14)) * 0.7
	density = np.clip(lower + upper * 0.8 + groove, 0, 1)
	density = density * cv.mask
	glaze(cv, tone, math.pi / 2, density + 0.3, amount=1.6)
	paint_moss(cv, tone, density, dab=0.65)
	# the rings: an ink line wherever the profile steps
	lines = []
	for g, width in ((0.09, 0.2), (0.2, 0.15), (0.25, 0.22), (0.98, 0.18), (1.1, 0.14), (1.14, 0.2), (1.66, 0.18), (1.77, 0.13), (1.84, 0.2)):
		pts = [cv.px(uu, BASE + g * W + rng.normal(0, 0.04)) for uu in np.linspace(cv.u0, cv.u1, 44)]
		lines.append((pts, width))
	img = Image.new("L", (cv.w, cv.h), 0)
	d = ImageDraw.Draw(img)
	for pts, width in lines:
		d.line(pts, fill=255, width=max(2, int(width * s)), joint="curve")
	rings = np.asarray(img, dtype=np.float32) / 255
	blend(cv, np.roll(rings, 3, axis=0) * (1 - rings) * 0.35, PALE)
	blend(cv, rings * smooth(-1.4, 0.0, field((cv.h, cv.w), s * 1.6, s * 1.6, 9)) * 0.92, INK)
	flecks(cv, tone, 34, smooth(0.5, 0.0, density))


def paint_pommel_face(cv):
	s = cv.s
	light = np.array(LIGHTS[cv.kind], dtype=np.float32)
	light /= np.linalg.norm(light)
	tone = 0.56 + 0.62 * ((cv.N @ light) - 0.42)
	z = cv.P[..., 2]
	centre = BASE + (1.92 + 0.27) * W
	tone = tone + 0.1 * np.clip((z - centre) / (0.4 * W), -1, 1)
	paint_stone(cv, tone, math.pi / 2, big=3.0)
	wig = field((cv.h, cv.w), s * 1.2, s * 1.2, hash_name(cv.name) + 1)
	density = (smooth(centre + 0.05 * W, centre + 0.45 * W, z + 1.2 * wig) + smooth(centre - 0.12 * W, centre - 0.34 * W, z + wig) * 0.8) * cv.mask
	glaze(cv, tone, math.pi / 2, density + 0.3, amount=1.6)
	paint_moss(cv, tone, density, dab=0.5)
	# the crescent on the boss
	pts = []
	for i in range(14):
		a = math.pi * (0.1 + 0.8 * i / 13)
		pts.append((0.1 * W * math.cos(a), centre + 0.03 * W + 0.125 * W * math.sin(a)))
	draw_cracks(cv, [(pts, 0.14)])
	ink_and_edges(cv, 34, tone, width=1.9, pale=0.3)
	flecks(cv, tone, 14)


def paint_small(cv):
	s = cv.s
	light = np.array(LIGHTS[cv.kind], dtype=np.float32)
	light /= np.linalg.norm(light)
	tone = 0.5 + 0.45 * ((cv.N @ light) - 0.5)
	paint_stone(cv, tone, math.pi / 2, big=3.0)
	ink_and_edges(cv, 34, tone, width=1.2, pale=0.3, boundary=False)


def paint(name):
	cv = Canvas(name)
	if name in ("BF", "BB"):
		paint_blade_face(cv)
	elif name in ("BR", "BL"):
		paint_blade_side(cv)
	elif name in ("BU", "BD"):
		paint_cap(cv)
	elif name in ("GF", "GB"):
		paint_guard_face(cv)
	elif name in ("GU", "GD", "GR", "GL"):
		paint_guard_other(cv)
	elif name == "HW":
		paint_grip(cv)
	elif name in ("HF", "HB"):
		paint_pommel_face(cv)
	else:
		paint_small(cv)
	cv.finish_fill()
	# a brush's edge isn't a pixel's edge
	cv.c = ndimage.gaussian_filter(cv.c, (0.55, 0.55, 0))
	return cv


def compose(canvases):
	size = layout["Size"]
	for sheet, info in layout["Sheets"].items():
		out = np.zeros((size, size, 3), dtype=np.float32)
		have = np.zeros((size, size), dtype=bool)
		for isl in info["Islands"]:
			cv = canvases[isl["Canvas"]]
			k = info["Scale"] * isl["K"]
			w = math.ceil((isl["U1"] - isl["U0"]) * k)
			h = math.ceil((isl["V1"] - isl["V0"]) * k)
			# the exact window of the canvas, sized down: at 1/SS the sheet's pixels line up with the UVs
			x0, x1 = (isl["U0"] - cv.u0) * cv.s, (isl["U0"] + w / k - cv.u0) * cv.s
			y0, y1 = (cv.v1 - isl["V1"]) * cv.s, (cv.v1 - isl["V1"] + h / k) * cv.s
			img = Image.fromarray(np.clip(cv.c, 0, 255).astype(np.uint8))
			img = img.resize((w, h), Image.LANCZOS, box=(x0, y0, min(x1, cv.w), min(y1, cv.h)))
			out[isl["PY"] : isl["PY"] + h, isl["PX"] : isl["PX"] + w] = np.asarray(img, dtype=np.float32)
			have[isl["PY"] : isl["PY"] + h, isl["PX"] : isl["PX"] + w] = True
		_, (iy, ix) = ndimage.distance_transform_edt(~have, return_indices=True)
		out[~have] = out[iy[~have], ix[~have]]
		img = Image.fromarray(np.clip(out * GRADE, 0, 255).astype(np.uint8))
		img = img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=1))
		img.save(os.path.join(OUT, f"Sword_{sheet}.png"))
		print("sheet", sheet, flush=True)


def main():
	ap = argparse.ArgumentParser()
	ap.parse_args()
	canvases = {}
	for name in layout["Canvases"]:
		canvases[name] = paint(name)
		print("painted", name, canvases[name].w, "x", canvases[name].h, flush=True)
	compose(canvases)


if __name__ == "__main__":
	main()
