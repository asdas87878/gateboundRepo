"""Seamless terrain tiles built from painted shapes, the way hand-painted tiles are, instead of filtered noise: overlapping grass clumps of
blades with lit tips, chiselled stone planes with cracks and pale rims, dirt with dry strokes and pebbles. Worn is dirt with broken grass clumps
on it, a transition material so the path meets the grass in steps instead of the engine's blur.

Each shape's colour comes from a small palette through a slow value field, so light and dark group calmly without blotches (FIELD).
Maps hold colour / tint: Roblox multiplies by the terrain material's colour, and the printed tint goes there. Grass blades take that tint.

usage: paint_shape_tiles.py <out folder> [--size 1024] [--only Grass,Path]   -> <Name>_Tile.png + preview.jpg + tints.json
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree

SS = 2  # paint at twice the size, then shrink
GRASS = ["2f7f4f", "3a9150", "4aa453", "5fb655", "7ac75c"]  # dark to lit
TIP = "a2d968"
GROUND_GREEN = ["58a85a", "5cad5b", "61b35c"]  # the plain ground under the blades: only just different
CLIFF_FADE = 0.42  # contrast kept in the cliff tile, toward its own mean colour
DIRT = ["6d5236", "7d6040", "8d6e48", "9e7e54", "ae8e62"]
PEBBLE = ["a79a86", "8f8574", "bdb19c"]
STONE = ["5d6b7c", "75838f", "8e989c", "a8aeaa", "c2c5ba"]
CRACK = "47515f"
RIM = "dcdccd"
FIELD = 0.55  # how much the slow value field moves a shape along its palette; the rest is per-shape chance


def hexc(h):
	return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def field(size, feature, seed):
	"""periodic smooth noise, 0..1"""
	spec = np.fft.fft2(np.random.RandomState(seed).normal(size=(size, size)))
	f = np.fft.fftfreq(size)
	d2 = f[:, None] ** 2 + f[None, :] ** 2
	o = np.fft.ifft2(spec * np.exp(-d2 * (np.pi * feature * size) ** 2 * 2)).real
	return np.clip(o / (o.std() * 3.5) + 0.5, 0, 1).astype(np.float32)


def pick(palette, t):
	return palette[min(int(max(t, 0) * len(palette)), len(palette) - 1)]


class Canvas:
	def __init__(self, size, colour):
		self.w = size * SS
		self.im = Image.new("RGB", (self.w, self.w), hexc(colour))
		self.d = ImageDraw.Draw(self.im)

	def poly(self, pts, colour):
		"""draws a polygon and any wrapped copies, so the tile has no seams"""
		xs, ys = [p[0] for p in pts], [p[1] for p in pts]
		w = self.w
		for ox in (0, -w, w):
			if max(xs) + ox < 0 or min(xs) + ox > w:
				continue
			for oy in (0, -w, w):
				if max(ys) + oy < 0 or min(ys) + oy > w:
					continue
				self.d.polygon([(x + ox, y + oy) for x, y in pts], fill=hexc(colour))

	def array(self):
		return np.asarray(self.im, np.float32) / 255

	def set_array(self, a):
		self.im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
		self.d = ImageDraw.Draw(self.im)


def blade(x, y, angle, length, width, bend):
	"""a tapered curved blade from its base at (x, y)"""
	ca, sa = math.cos(angle), math.sin(angle)
	left, right = [], []
	n = 6
	for i in range(n + 1):
		t = i / n
		w = width * (1 - t) ** 0.8 * min(1.0, 0.45 + t * 3)
		off = bend * t * t
		cx, cy = x + ca * length * t - sa * off, y + sa * length * t + ca * off
		left.append((cx - sa * w, cy + ca * w))
		right.append((cx + sa * w, cy - ca * w))
	return left + right[::-1]


def grass_clumps(c, r, size, count, val, scale=1.0, keep=None):
	"""overlapping clumps, top of the tile first so nearer clumps lie over them; a clump lights from base to tip"""
	w = c.w
	spots = sorted(((r.random() * w, r.random() * w) for _ in range(count)), key=lambda p: p[1])
	for x, y in spots:
		i, j = int(y / SS) % size, int(x / SS) % size
		if keep is not None and r.random() > keep[i, j]:
			continue
		v = FIELD * val[i, j] + (1 - FIELD) * r.random()
		blades = int(r.integers(7, 13))
		for b in range(blades):
			u = (b + 0.5) / blades - 0.5
			a = -math.pi / 2 + u * 1.9 + r.normal(0, 0.12)
			length = (34 + 34 * (1 - abs(u) * 1.2) + r.uniform(-6, 8)) * SS * scale
			width = (5.0 + r.uniform(0, 2.5)) * SS * scale
			bend = u * 34 * SS * scale + r.normal(0, 4) * SS
			bx, by = x + u * 22 * SS * scale, y + r.uniform(-3, 3) * SS
			shade = v * 0.72 + (0.28 if abs(u) < 0.2 else 0.1) + r.normal(0, 0.05)
			c.poly(blade(bx, by, a, length, width, bend), pick(GRASS, shade))
			if shade > 0.45 and r.random() < 0.55:  # a lit stroke up the blade
				c.poly(blade(bx + math.cos(a) * length * 0.3, by + math.sin(a) * length * 0.3, a, length * 0.62, width * 0.45, bend * 0.5), pick(GRASS, shade + 0.22) if shade < 0.78 else TIP)


def dry_stroke(c, r, x, y, length, width, angle, colour):
	"""a flat stroke of a few broken bristle bands"""
	ca, sa = math.cos(angle), math.sin(angle)
	bands = int(r.integers(2, 5))
	for b in range(bands):
		o = (b / max(bands - 1, 1) - 0.5) * width * 2
		l0, l1 = r.uniform(0, 0.2) * length, r.uniform(0.65, 1.0) * length
		w = width / bands * r.uniform(0.7, 1.1)
		pts = []
		for s, side in ((l0, -1), (l1, -1), (l1, 1), (l0, 1)):
			pts.append((x + ca * s - sa * (o + side * w), y + sa * s + ca * (o + side * w)))
		c.poly(pts, colour)


def paint_grass(size, seed):
	"""low-key: nearly plain, faint jagged strokes in every direction, softened. The terrain's own blades carry the grass (and the path edge)."""
	r = np.random.default_rng(seed)
	c = Canvas(size, GROUND_GREEN[1])
	w = c.w
	for count, lmin, lmax, wmin, wmax in ((90, 90, 240, 18, 44), (240, 40, 120, 6, 16)):
		for _ in range(count):
			dry_stroke(c, r, r.random() * w, r.random() * w, r.uniform(lmin, lmax) * SS, r.uniform(wmin, wmax) * SS, r.uniform(0, math.tau), GROUND_GREEN[int(r.integers(0, 3))])
		c.set_array(gaussian_filter(c.array(), (1.2 * SS, 1.2 * SS, 0), mode="wrap"))
	return c.array()


def pebble(c, r, x, y, rad):
	n = int(r.integers(6, 9))
	off = r.uniform(0, math.tau)
	radii = r.uniform(0.75, 1.15, n)
	sq = r.uniform(0.62, 0.85)
	shape = [(math.cos(off + i / n * math.tau) * rad * radii[i], math.sin(off + i / n * math.tau) * rad * radii[i] * sq) for i in range(n)]
	c.poly([(x + px * 1.1, y + py * 1.1 + rad * 0.32) for px, py in shape], DIRT[0])
	col = PEBBLE[int(r.integers(0, 2))]
	c.poly([(x + px, y + py) for px, py in shape], col)
	c.poly([(x + px * 0.62 - rad * 0.14, y + py * 0.55 - rad * 0.2) for px, py in shape], PEBBLE[2])


def paint_dirt(c, r, size, val, strokes, pebbles):
	w = c.w
	for layer, (count, lmin, lmax, wmin, wmax, jitter) in enumerate(strokes):
		for _ in range(count):
			x, y = r.random() * w, r.random() * w
			v = FIELD * val[int(y / SS) % size, int(x / SS) % size] + (1 - FIELD) * r.random()
			dry_stroke(c, r, x, y, r.uniform(lmin, lmax) * SS, r.uniform(wmin, wmax) * SS, r.normal(0.2, jitter), pick(DIRT, 0.1 + v * 0.8))
		c.set_array(gaussian_filter(c.array(), (1.6 * SS * (2 - layer) / 2 + 0.5, 1.6 * SS * (2 - layer) / 2 + 0.5, 0), mode="wrap"))
	for _ in range(pebbles):
		pebble(c, r, r.random() * w, r.random() * w, r.uniform(5, 16) * SS)


STROKES = [(170, 110, 280, 24, 52, 0.25), (260, 60, 150, 10, 22, 0.3), (90, 26, 70, 3, 6, 0.35)]


def paint_path(size, seed):
	r = np.random.default_rng(seed)
	c = Canvas(size, DIRT[2])
	paint_dirt(c, r, size, field(size, 0.14, seed), STROKES, 34)
	return c.array()


def paint_worn(size, seed):
	r = np.random.default_rng(seed)
	c = Canvas(size, DIRT[2])
	paint_dirt(c, r, size, field(size, 0.14, seed), STROKES, 12)
	val = field(size, 0.11, seed + 1)
	keep = np.clip((field(size, 0.05, seed + 2) - 0.42) * 7, 0, 1)  # broken islands of grass, bare dirt between
	grass_clumps(c, r, size, 520, val, 0.8, keep)
	return c.array()


def paint_cliff(size, seed):
	"""chiselled planes at two scales from a periodic Voronoi pattern: each cell one flat tone, dark cracks, a pale rim on the upper side"""
	r = np.random.default_rng(seed)
	yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
	warp = 18.0
	wx = (field(size, 0.05, seed + 3) - 0.5) * warp * 2
	wy = (field(size, 0.05, seed + 4) - 0.5) * warp * 2

	def cells(n):
		pts = r.random((n, 2)) * size
		all_pts = np.concatenate([pts + np.array([a, b]) * size for a in (-1, 0, 1) for b in (-1, 0, 1)])
		q = np.stack([(xx + wx).ravel(), (yy + wy).ravel()], 1)
		d, idx = cKDTree(all_pts).query(q, k=2, workers=-1)
		return (idx[:, 0] % n).reshape(size, size), (d[:, 1] - d[:, 0]).reshape(size, size), (all_pts[idx[:, 0]] - q).reshape(size, size, 2)

	big_id, big_edge, big_vec = cells(46)
	small_id, small_edge, _ = cells(190)
	val = field(size, 0.14, seed)
	tone = FIELD * val + (1 - FIELD) * r.random(46)[big_id]
	tone = tone * 0.82 + (r.random(190)[small_id] - 0.5) * 0.14 + 0.1
	stone = np.array([hexc(s) for s in STONE], np.float32) / 255
	stepped = np.clip(tone, 0, 0.999) * len(STONE)
	col = stone[stepped.astype(int)]
	col = gaussian_filter(col, (0.9, 0.9, 0), mode="wrap")
	crack = np.array(hexc(CRACK), np.float32)[None, None] / 255
	rim = np.array(hexc(RIM), np.float32)[None, None] / 255
	upper = np.clip(big_vec[..., 1] / 40, 0, 1)  # this pixel lies above its cell's centre
	k = np.clip((14 - big_edge) / 9, 0, 1)[..., None] * upper[..., None] * 0.3
	col = col * (1 - k) + rim * k
	k = np.clip((6 - big_edge) / 5, 0, 1)[..., None] * 0.5
	col = col * (1 - k) + crack * k
	col = gaussian_filter(col, (1.4, 1.4, 0), mode="wrap")
	mean = col.reshape(-1, 3).mean(0)
	return (mean + (col - mean) * CLIFF_FADE).astype(np.float32)


MATERIALS = {"Grass": (paint_grass, 3), "Path": (paint_path, 8), "Worn": (paint_worn, 14), "Cliff": (paint_cliff, 11)}


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("out")
	ap.add_argument("--size", type=int, default=1024)
	ap.add_argument("--only")
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	names = a.only.split(",") if a.only else list(MATERIALS)
	path = os.path.join(a.out, "tints.json")
	tints = json.load(open(path)) if os.path.exists(path) else {}
	row = []
	for name in names:
		fn, seed = MATERIALS[name]
		col = fn(a.size, seed)
		if col.shape[0] != a.size:
			col = np.asarray(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).resize((a.size, a.size), Image.LANCZOS), np.float32) / 255
		tint = np.percentile(col.reshape(-1, 3), 99.5, axis=0)
		tints[name] = "".join(f"{int(v * 255):02x}" for v in tint)
		Image.fromarray((np.clip(col / tint, 0, 1) * 255).astype(np.uint8)).save(os.path.join(a.out, f"{name}_Tile.png"))
		row.append(np.concatenate([col, col], 0)[: a.size * 2])
		print(name, tints[name])
	json.dump(tints, open(path, "w"))
	sheet = np.concatenate(row, 1)
	Image.fromarray((np.clip(sheet, 0, 1) * 255).astype(np.uint8)).resize((sheet.shape[1] // 2, sheet.shape[0] // 2), Image.LANCZOS).save(os.path.join(a.out, "preview.jpg"), quality=90)


if __name__ == "__main__":
	main()
