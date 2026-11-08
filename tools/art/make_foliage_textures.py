"""Leaf-card and bark textures for stylized foliage (the method: white leaves on transparency, tinted in Roblox).

leaves_white.png is a 2 x 2 atlas of leaf clusters at different values, so cards low in a crown can use a darker cluster
and cards on top a lighter one: the crown gets its gradient with no baked light. Colour under the transparent parts is
spread out from the leaves, which is what stops the dark fringe (the job PixelFix does).
bark_white.png is a seamless streaked tile, tinted the same way.

usage: make_foliage_textures.py <out folder>
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

CELL = 512
SS = 3  # supersampling while drawing
# cell order matches UV cells in tools/blender/foliage_kit.py: dark, mid, light, light and sparse
CELLS = [(0.64, 190), (0.8, 190), (0.97, 180), (1.0, 95)]


def leaf_polygon(cx, cy, length, width, angle):
	"""a pointed painted leaf, slightly bent"""
	pts = []
	n = 7
	bend = random.uniform(-0.18, 0.18) * length
	for side in (1, -1):
		rng = range(n + 1) if side == 1 else range(n, -1, -1)
		for i in rng:
			t = i / n
			w = width * math.sin(math.pi * t ** 0.8) * side
			pts.append((t * length, w + bend * t * t))
	c, s = math.cos(angle), math.sin(angle)
	return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


# leaf shapes for different forests: length and width as shares of the cluster, how many a cell holds (scaled by CELLS' count), and how round the cluster is
SHAPES = {
	"default": {"Length": (0.11, 0.2), "Width": (0.15, 0.26), "Count": 1.0, "Spread": 0.34, "Fan": 0.75},
	"broad": {"Length": (0.2, 0.36), "Width": (0.26, 0.38), "Count": 0.42, "Spread": 0.36, "Fan": 0.85},
	"small": {"Length": (0.07, 0.12), "Width": (0.3, 0.44), "Count": 1.5, "Spread": 0.36, "Fan": 1.2},
	"needle": {"Length": (0.2, 0.34), "Width": (0.035, 0.06), "Count": 1.5, "Spread": 0.3, "Fan": 0.4},
}
SHAPE = SHAPES["default"]


def draw_cell(value, count, seed):
	random.seed(seed)
	count = int(count * SHAPE["Count"])
	size = CELL * SS
	rgb = Image.new("L", (size, size), 0)
	alpha = Image.new("L", (size, size), 0)
	dr, da = ImageDraw.Draw(rgb), ImageDraw.Draw(alpha)
	mid = size / 2
	leaves = []
	for _ in range(count):
		# a loose round cluster, denser in the middle with a broken outline
		a = random.uniform(0, math.tau)
		d = (random.random() ** 0.62) * size * SHAPE["Spread"]
		leaves.append((d, a))
	leaves.sort()  # the middle first, so outer leaves overlap it
	for d, a in leaves:
		x, y = mid + math.cos(a) * d, mid + math.sin(a) * d
		length = random.uniform(*SHAPE["Length"]) * size * 0.5
		width = length * random.uniform(*SHAPE["Width"])
		turn = a + random.uniform(-SHAPE["Fan"], SHAPE["Fan"])  # leaves point outward, more or less
		poly = leaf_polygon(x, y, length, width, turn)
		v = value * (0.86 + 0.14 * d / (size * SHAPE["Spread"])) + random.uniform(-0.05, 0.05)
		dr.polygon(poly, fill=int(np.clip(v, 0, 1) * 255))
		da.polygon(poly, fill=255)
	return rgb.resize((CELL, CELL), Image.LANCZOS), alpha.resize((CELL, CELL), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.7))


def spread_colour(value, alpha):
	"""fill the transparent area with colour blurred out from the leaves"""
	v, a = np.asarray(value, np.float32), np.asarray(alpha, np.float32) / 255
	out = v.copy()
	for radius in (2, 6, 16, 48, 128):
		d = gaussian_filter(a, radius)
		fill = gaussian_filter(out * a, radius) / np.maximum(d, 1e-4)
		hole = (a < 0.5) & (d > 0.002)
		out[hole] = fill[hole]
		a = np.where(hole, 1.0, a)
	return out


def leaves(path):
	sheet = np.zeros((CELL * 2, CELL * 2, 4), np.uint8)
	for i, (value, count) in enumerate(CELLS):
		rgb, alpha = draw_cell(value, count, 40 + i)
		v = spread_colour(rgb, alpha)
		# image rows run down and UVs run up: cell 0 sits at the bottom left
		x0, y0 = (i % 2) * CELL, (1 - i // 2) * CELL
		sheet[y0 : y0 + CELL, x0 : x0 + CELL, :3] = np.clip(v, 0, 255)[..., None]
		sheet[y0 : y0 + CELL, x0 : x0 + CELL, 3] = np.asarray(alpha)
	Image.fromarray(sheet, "RGBA").save(path)


def bark(path, size=512):
	r = np.random.RandomState(9)
	fx, fy = np.fft.fftfreq(size)[None, :], np.fft.fftfreq(size)[:, None]

	def layer(wide, long, seed):
		s = np.fft.fft2(np.random.RandomState(seed).normal(size=(size, size)))
		o = np.fft.ifft2(s * np.exp(-(fx ** 2 * wide ** 2 + fy ** 2 * long ** 2) * 19.7)).real
		return o / np.abs(o).max()

	v = layer(0.03, 0.3, 1) * 0.6 + layer(0.012, 0.12, 2) * 0.3 + layer(0.1, 0.5, 3) * 0.3
	v = (v - v.min()) / (v.max() - v.min())
	q = v * 4  # painted steps of value
	v = (np.floor(q) + np.clip((q - np.floor(q) - 0.3) / 0.4, 0, 1)) / 4
	Image.fromarray((150 + 105 * v).clip(0, 255).astype(np.uint8)).convert("RGB").save(path)


if __name__ == "__main__":
	out = sys.argv[1]
	os.makedirs(out, exist_ok=True)
	if len(sys.argv) > 2:
		for name in sys.argv[2:]:
			SHAPE = SHAPES[name]
			leaves(os.path.join(out, f"leaves_{name}.png"))
	else:
		leaves(os.path.join(out, "leaves_white.png"))
		bark(os.path.join(out, "bark_white.png"))
	print("wrote", out)
