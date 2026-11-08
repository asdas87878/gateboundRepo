"""Paints a tree trunk's colour map from tools/blender/foliage_kit.py's trunk_tubes.json (system Python), in a hand-painted game style.

Under the strokes: base colour, fading up the tree, with a slight value change per mesh facet. Over it, brush marks stamped in layers: a crisp head, one hard
side and one soft side, and a dry-brush tail that fades off along separate bristles. Where a stroke goes and what colour it is come from the form (distance to
the other limbs, height), not chance: pale planes down the exposed middle of limbs, dark growing down from the forks in some places only, olive strokes rising
from the foot. Darks stay restrained, and no light or shadow is painted: the engine does those.

Edge highlights use the original rock kit's recipe (tools/art/paint_rock_kit.py): soft-sided bands at distance from real edges (here the mesh's convex facet
edges), wobbling, broken by noise, stronger facing up; kept subtle.

usage: paint_trunk.py <folder holding trunk_tubes.json> [--size 1024] [--out bark_painted.png]
"""
import argparse
import json
import math
import os
import random

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates
from scipy.spatial import cKDTree

BASE = "675856"
TOP = "66534a"  # what the limbs fade to
MID = "746359"
LOW = "5d4d48"
PALE = "8c7a70"
PINK = "9a8580"
LIGHT = "a39186"  # thin light strokes
DARK = "4e3d36"
RED = "6e4436"
OLIVE = "6c6e46"
EDGE = "bdaca0"  # edge highlights
GRADE = (1.22, 1.2, 1.02)  # final multiply, from lit Studio measurements against the video
FADE_FROM, FADE_TO = 0.5, 0.92  # share of the tree's height over which detail fades out
TOP_DETAIL = 0.4  # how much detail stays at the top
FACET_VALUE = 0.05  # value change per facet
EDGE_WIDTH = 0.16  # studs: highlight band, soft-sided as on the rocks
EDGE_WOBBLE = 0.05  # studs
EDGE_STRENGTH = 0.42
RIBBONS = {"leader": 7, "branch": 2, "root": 5}  # bark ribbons round a limb
RIBBON_TWIST = 0.05  # radians per stud, scaled by thickness
RIBBON_DARK, RIBBON_LIGHT = 0.86, 1.05  # value at a ribbon's edge and middle
GROOVE = "372624"
RIDGE = "b3a08f"
HEAD_SOFT = 0.07  # share of a stroke's length its start fades in over
BRISTLE = 0.5  # how much bristles break the tail
GRAIN = 0.035
SUPERSAMPLE = 2  # paint at this many times the final size, then shrink
UNDER_BLUR = 1.4  # texels, final size: melts the broad planes together before the details


def hexc(h):
	return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def smooth(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def over(col, colour, amount):
	amount = np.clip(amount, 0, 1)[..., None]
	return col * (1 - amount) + hexc(colour) * amount


class Noise:
	"""smooth periodic 3D noise, mostly -1..1"""

	def __init__(self, seed, size=48):
		v = gaussian_filter(np.random.RandomState(seed).normal(size=(size, size, size)), 1.6, mode="wrap")
		self.v, self.size = v / (v.std() * 2.0), size

	def __call__(self, x, y, z):
		return map_coordinates(self.v, np.stack([x, y, z]) % self.size, order=1, mode="grid-wrap")


def stamp(canvas, rng, x, y, length, width, angle, colour, opacity):
	"""one brush mark from (x, y) along angle (0 = up the limb), in texels; wraps round the limb"""
	ny, nx, _ = canvas.shape
	reach = int(length + width + 2)
	x0, y0 = int(x), int(y)
	ya, yb = max(y0 - reach, 0), min(y0 + reach + 1, ny)
	if yb <= ya:
		return
	xs = np.arange(x0 - min(reach, nx // 2), x0 + min(reach, nx // 2) + 1)
	ys = np.arange(ya, yb)
	dx, dy = np.meshgrid(xs - x, ys - y)
	sa, ca = math.sin(angle), math.cos(angle)
	u = (dx * sa + dy * ca) / length
	v = (dx * ca - dy * sa) / width
	if rng.random() < 0.5:
		v = -v
	# feathered, not spiked: bristles only nudge a long soft fade, and the head is rounded
	bristle = np.interp(v, np.linspace(-1, 1, 10), gaussian_filter(rng.random(10), 0.5, mode="nearest"))
	head = u - 0.1 * v * v
	along = smooth(-0.03, HEAD_SOFT, head) * smooth(0.0, 0.75, (1 - u) * 1.25 - bristle * BRISTLE)
	edge = max(0.2, 4.0 / max(width, 1.0))  # at least a few texels of soft edge, so no stair-steps
	across = np.where(v > 0, smooth(1.0, 1.0 - min(edge, 0.9), v), smooth(1.0, 0.2, -v))  # one firmer side, one soft
	alpha = (along * across * opacity)[..., None]
	idx = np.ix_(ys, xs % nx)
	canvas[idx] = canvas[idx] * (1 - alpha) + hexc(colour) * alpha


def limb_surface(tube, size):
	x0, y0, w, h = tube["box"]
	ix0, iy0 = int(np.floor(x0 * size)), int(np.floor(y0 * size))
	nx, ny = max(int(np.ceil(w * size)), 2), max(int(np.ceil(h * size)), 2)
	us, vs = (np.arange(nx) + 0.5) / nx, (np.arange(ny) + 0.5) / ny
	along = np.array(tube["along"])
	s = vs ** (1 / tube.get("vpower", 1.0)) * along[-1]
	pts, a, b = (np.array(tube[k]) for k in ("pts", "a", "b"))
	c = np.stack([np.interp(s, along, pts[:, i]) for i in range(3)], -1)
	fa = np.stack([np.interp(s, along, a[:, i]) for i in range(3)], -1)
	fb = np.stack([np.interp(s, along, b[:, i]) for i in range(3)], -1)
	r = np.interp(s, along, np.array(tube["radii"]))
	theta = us * np.pi * 2
	out = np.cos(theta)[None, :, None] * fa[:, None, :] + np.sin(theta)[None, :, None] * fb[:, None, :]
	p = c[:, None, :] + out * r[:, None, None]
	return ix0, iy0, nx, ny, p, out, np.broadcast_to(s[:, None], (ny, nx)), np.broadcast_to(theta[None, :], (ny, nx)), np.broadcast_to(r[:, None], (ny, nx))


def sample_limbs(tubes, kinds):
	centres, rads, owner = [], [], []
	for i, t in enumerate(tubes):
		if t["kind"] not in kinds:
			continue
		along = np.array(t["along"])
		s = np.arange(0.0, along[-1], 0.2)
		pts = np.array(t["pts"])
		centres.append(np.stack([np.interp(s, along, pts[:, k]) for k in range(3)], -1))
		rads.append(np.interp(s, along, t["radii"]))
		owner.append(np.full(len(s), i))
	return np.concatenate(centres), np.concatenate(rads), np.concatenate(owner)


def gap_to(p, i, centres, rads, owner):
	keep = owner != i
	if not keep.any():  # a single-trunk tree: no other limb to measure against
		return np.full(p.shape[:2], 1e6, np.float32)
	dist, idx = cKDTree(centres[keep]).query(p.reshape(-1, 3), workers=-1)
	return (dist - rads[keep][idx]).reshape(p.shape[:2])


def convex_columns(tube):
	"""the mesh's outward-chiselled columns: same seed and draw order as foliage_kit.Tube.build"""
	sides = tube["sides"]
	r = random.Random(int(tube["along"][-1] * 1000) + sides)
	cols = [r.uniform(-1, 1) for _ in range(sides)]
	return np.array([k for k in range(sides) if cols[k] >= cols[k - 1] and cols[k] >= cols[(k + 1) % sides]]), sides


def paint(t, i, height, leaders, n, size, rng):
	ix0, iy0, nx, ny, p, out, S, T, R = limb_surface(t, size)
	z = p[..., 2]
	rel = np.clip(z / height, 0, 1)
	ox = i * 7.3
	rx, ry = np.cos(T), np.sin(T)
	is_leader = t["kind"] == "leader"
	detail = TOP_DETAIL + (1 - TOP_DETAIL) * smooth(FADE_TO, FADE_FROM, rel)
	along = np.array(t["along"])
	length = along[-1]
	px_up = ny / length
	mean_r = float(np.mean(t["radii"]))
	px_round = nx / (mean_r * math.tau)
	area = length * mean_r * math.tau
	if mean_r > 3:
		scale = mean_r / 3
		px_up *= scale
		area /= scale * scale

	if is_leader:
		g = gap_to(p, i, *leaders) / np.maximum(R, 0.15)
		wander = n["b"](rx * 1.6 + ox, ry * 1.6, S * 0.16) * 0.6
		mass = smooth(0.42, 1.0, g + wander * 0.3)
	else:
		g = smooth(0.0, t["radii"][0] * 1.6, S)
		wander = n["b"](rx * 1.6 + ox, ry * 1.6, S * 0.16) * 0.6
		mass = smooth(-0.3, 0.7, out[..., 2] + wander * 0.5)

	# under the strokes: base, per-facet planes, soft form
	col = np.ones((ny, nx, 3), np.float32) * hexc(BASE)
	col = over(col, TOP, smooth(FADE_FROM, FADE_TO, rel) * 0.5)
	sides = t["sides"]
	facet_r = np.random.RandomState(i + 5).uniform(-1, 1, (len(along), sides))
	row = np.clip(np.searchsorted(along, S) - 1, 0, len(along) - 1)
	column = np.minimum((T / math.tau * sides).astype(int), sides - 1)
	col = col * (1 + (facet_r[row, column] * FACET_VALUE * detail)[..., None])
	col = over(col, PALE, mass * 0.3 * (0.4 + 0.6 * detail))
	col = over(col, DARK, smooth(0.14, 0.01, g) * 0.55)  # only the tight seam itself
	col = over(col, OLIVE, smooth(1.4, -0.2, z) * 0.3)

	def pick(count, test):
		"""random points passing a test on (row, column)"""
		ys, xs = rng.integers(0, ny, count), rng.integers(0, nx, count)
		keep = test(ys, xs)
		return ys[keep], xs[keep]

	def wide(rad_at, lo, hi):
		return max(rng.uniform(lo, hi) * rad_at * px_round, 1.0)

	# broad planes, coloured by where they sit
	ys, xs = pick(int(area * 0.5) + 3, lambda y, x: rng.random(len(y)) < detail[y, x])
	for y, x in zip(ys, xs):
		m = mass[y, x]
		colour = PALE if m > 0.55 else (LOW if m < 0.2 else MID)
		stamp(col, rng, x, y, rng.uniform(4, 9) * px_up, wide(R[y, x], 0.4, 0.8), rng.uniform(-0.2, 0.2), colour, 0.62 * detail[y, x])

	col = gaussian_filter(col, (UNDER_BLUR * SUPERSAMPLE, UNDER_BLUR * SUPERSAMPLE, 0), mode=("nearest", "wrap", "nearest"))

	# medium strokes over the blended base: the visible brushwork
	ys, xs = pick(int(area * 1.1) + 3, lambda y, x: rng.random(len(y)) < detail[y, x])
	for y, x in zip(ys, xs):
		m = mass[y, x] + rng.normal(0, 0.18)
		colour = LIGHT if m > 0.8 else (PALE if m > 0.5 else (MID if m > 0.2 else LOW))
		stamp(col, rng, x, y, rng.uniform(2, 6) * px_up, wide(R[y, x], 0.1, 0.28), rng.uniform(-0.2, 0.2), colour, 0.38 * detail[y, x])

	# darks grow down from the forks, only in some places
	grow = n["c"](rx * 1.2 + ox, ry * 1.2, S * 0.12)
	if is_leader:
		ys, xs = pick(int(area * 0.35), lambda y, x: (g[y, x] > 0.02) & (g[y, x] < 0.42) & (rel[y, x] > 0.1) & (grow[y, x] > 0.05))
		for y, x in zip(ys, xs):
			stamp(col, rng, x, y, rng.uniform(3, 8) * px_up, wide(R[y, x], 0.1, 0.24), math.pi + rng.uniform(-0.15, 0.15), DARK, 0.5)
		ys, xs = pick(int(area * 0.1), lambda y, x: (g[y, x] > 0.15) & (g[y, x] < 0.6) & (grow[y, x] > -0.1))
		for y, x in zip(ys, xs):
			stamp(col, rng, x, y, rng.uniform(2, 5) * px_up, wide(R[y, x], 0.05, 0.1), math.pi + rng.uniform(-0.2, 0.2), RED, 0.32)

	# the root: pink above, olive rising from the foot and fading out
	ys, xs = pick(int(area * 0.3), lambda y, x: (z[y, x] > 1.5) & (z[y, x] < 6.5) & (mass[y, x] > 0.35))
	for y, x in zip(ys, xs):
		stamp(col, rng, x, y, rng.uniform(1.5, 4) * px_up, wide(R[y, x], 0.2, 0.45), rng.uniform(-0.2, 0.2), PINK, 0.32)
	ys, xs = pick(int(area * 0.6), lambda y, x: z[y, x] < 1.3)
	for y, x in zip(ys, xs):
		stamp(col, rng, x, y, rng.uniform(1.5, 4.5) * px_up, wide(R[y, x], 0.12, 0.32), rng.uniform(-0.25, 0.25), OLIVE, 0.5)
	if is_leader and i == 1:
		ys, xs = pick(int(area * 0.12), lambda y, x: (z[y, x] > 7) & (z[y, x] < 15) & (mass[y, x] > 0.4))
		for y, x in zip(ys, xs):
			stamp(col, rng, x, y, rng.uniform(3, 7) * px_up, wide(R[y, x], 0.15, 0.35), rng.uniform(-0.15, 0.15), OLIVE, 0.3)

	# a few thin lights
	ys, xs = pick(int(area * 0.1), lambda y, x: (mass[y, x] > 0.35) & (rng.random(len(y)) < detail[y, x]))
	for y, x in zip(ys, xs):
		stamp(col, rng, x, y, rng.uniform(2, 6) * px_up, max(rng.uniform(0.05, 0.1) * px_round, 1.0), rng.uniform(-0.2, 0.2), LIGHT, 0.3)

	# faint grain along the limb
	grain = n["d"](rx * 14 + ox, ry * 14, S * 0.8)
	col = col * (1 + (grain * GRAIN * detail)[..., None])

	if t["kind"] == "branch" or t["kind"] == "twig":
		# branches stay close to one soft colour: strong variation here read as sharp patches
		col = gaussian_filter(col, (3 * SUPERSAMPLE, 2 * SUPERSAMPLE, 0), mode=("nearest", "wrap", "nearest"))
		col = col * 0.35 + hexc(MID) * 0.65

	# framing: bark ribbons running up the limb. Long dark grooves split it into shapes, each ribbon is lighter down its middle and darker toward its edges,
	# and a pale line runs beside each groove on one side. This is what makes the bark look painted on purpose rather than mottled.
	ribbons = RIBBONS.get(t["kind"], 0)
	if ribbons and mean_r > 0.2:
		fr = np.random.RandomState(i * 3 + 11)
		twist = fr.uniform(-1, 1) * RIBBON_TWIST / max(mean_r, 0.5)
		starts = (np.arange(ribbons) + fr.uniform(-0.28, 0.28, ribbons)) / ribbons * math.tau
		nearest = np.full(T.shape, 1e6, np.float32)
		lines = []
		for k in range(ribbons):
			wave, phase = fr.uniform(0.05, 0.14), fr.uniform(0, math.tau)
			centre = starts[k] + twist * S + min(0.35, 1.2 / max(mean_r, 1)) * np.sin(S * wave * min(1.0, 3 / max(mean_r, 1)) + phase)
			delta = ((T - centre + math.pi) % math.tau) - math.pi
			lines.append((delta * R, k))
			nearest = np.minimum(nearest, np.abs(delta * R))
		half = mean_r * math.pi / ribbons
		form = smooth(0.0, half * 0.9, nearest)
		col = col * (RIBBON_DARK + (RIBBON_LIGHT - RIBBON_DARK) * form)[..., None]
		ends = smooth(0, 0.06, S / length) * smooth(1.0, 0.82, S / length)
		for dist, k in lines:
			w = (0.035 + 0.05 * fr.random()) * mean_r * (0.7 + 0.5 * n["c"](rx + k, ry, S * 0.1)) + 0.02
			fade = np.clip(0.55 + n["b"](rx * 0.8 + k * 3, ry * 0.8, S * 0.09) * 1.6, 0, 1) * ends
			strength = 0.45 if t["kind"] == "branch" else 1.0
			col = over(col, GROOVE, smooth(w * 1.15, 0, np.abs(dist)) * fade * 0.74 * strength)
			if t["kind"] != "branch":
				col = over(col, RIDGE, smooth(w * 2.6, 0, np.abs(dist - w * 2.2)) * fade * 0.3)

	# edge highlights, the rock kit's way: distance to the real convex edges, wobbling, broken, stronger facing up
	columns, sides = convex_columns(t)
	if len(columns):
		angles = columns / sides * math.tau
		d = np.abs(((T[..., None] - angles + math.pi) % math.tau) - math.pi).min(-1) * R  # studs round the limb
		wobble = n["d"](rx * 2 + ox, ry * 2, S * 0.5) * EDGE_WOBBLE
		e = smooth(EDGE_WIDTH, EDGE_WIDTH * 0.25, d + wobble)
		e = e * smooth(-0.3, 0.2, n["a"](rx * 2 + ox + 5, ry * 2, S * 0.35))
		e = e * (0.35 + 0.65 * smooth(-0.5, 0.4, out[..., 2] + 0.25))
		e = e * smooth(0.04, 0.25, R) * smooth(0.1, 0.35, g)
		col = over(col, EDGE, e * EDGE_STRENGTH * (0.5 + 0.5 * detail) * (1.0 if is_leader else 0.4))
	return ix0, iy0, nx, ny, col


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("folder")
	ap.add_argument("--size", type=int, default=1024)
	ap.add_argument("--out", default="bark_painted.png")
	a = ap.parse_args()
	data = json.load(open(os.path.join(a.folder, "trunk_tubes.json"), encoding="utf-8"))
	tubes, size, height = data["tubes"], a.size * SUPERSAMPLE, data["height"]
	leaders = sample_limbs(tubes, ("leader",)) if any(t["kind"] == "leader" for t in tubes) else None
	n = {"a": Noise(1), "b": Noise(2), "c": Noise(3), "d": Noise(4)}
	rng = np.random.default_rng(21)
	img = np.zeros((size, size, 3), np.float32)
	filled = np.zeros((size, size), bool)
	for i, t in enumerate(tubes):
		ix0, iy0, nx, ny, col = paint(t, i, height, leaders, n, size, rng)
		col = col[::-1]  # UV rows run up, image rows run down
		y_top = size - iy0 - ny
		ya, yb, xa, xb = max(y_top, 0), min(y_top + ny, size), max(ix0, 0), min(ix0 + nx, size)
		img[ya:yb, xa:xb] = col[ya - y_top : yb - y_top, xa - ix0 : xb - ix0]
		filled[ya:yb, xa:xb] = True
	idx = distance_transform_edt(~filled, return_distances=False, return_indices=True)
	img = img[idx[0], idx[1]]
	img = gaussian_filter(img, (0.6 * SUPERSAMPLE, 0.6 * SUPERSAMPLE, 0))
	img = np.clip(img * np.array(GRADE), 0, 1)
	path = os.path.join(a.folder, a.out)
	Image.fromarray((img * 255).astype(np.uint8)).resize((a.size, a.size), Image.LANCZOS).save(path)
	print(path, "tubes", len(tubes), "filled", round(float(filled.mean()), 2))


if __name__ == "__main__":
	main()
