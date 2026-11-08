"""Painted, seamless terrain tiles by the Substance Painter recipe from the "KEY in making Roblox games" video, recreated in numpy:
base colour, then layers of colour through black-and-white spot masks (balance + contrast) run through Blur Slope, a directional blur
and a sharpen, which is what turns noise into paint strokes. Everything wraps, so tiles have no seams.

Style "recipe" is the video's chain as it stands. Style "planes" adds soft value steps afterwards, so strokes read as flat painted planes.
Colours are baked in. Roblox multiplies the map by the terrain material's colour, so the map holds colour / TINT and TINT is set in Studio.
(The video's light, AO and curvature layers need a model's own UVs, so they can't go on a repeating tile: they're for rocks.)

usage: paint_terrain_tiles.py <out folder> [--size 1024]   -> <out>/<style>/<Name>_Tile.png + preview sheet
"""
import argparse
import os

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

# name: seed, tint for Studio, base, then layers (colour, spot size as a share of the tile, balance, contrast, opacity)
MATERIALS = {
	"Grass": (3, "7cc25a", "4aa455", [("2f8a5e", 0.10, 0.52, 7, 0.75), ("5fb456", 0.08, 0.5, 7, 0.7), ("7cc25a", 0.05, 0.68, 8, 0.55)]),
	"Sand": (5, "f6e39a", "ecd488", [("dcbf78", 0.12, 0.55, 6, 0.6), ("f6e39a", 0.08, 0.5, 7, 0.7), ("d6c28c", 0.05, 0.7, 8, 0.35)]),
	"Path": (8, "b08a68", "8f6d52", [("6f5244", 0.09, 0.55, 7, 0.65), ("a07e5f", 0.07, 0.5, 7, 0.65), ("b08a68", 0.04, 0.7, 8, 0.45)]),
	"Rock": (11, "c3c6bf", "8d96a0", [("5f7288", 0.12, 0.52, 7, 0.75), ("a7aeb0", 0.09, 0.5, 7, 0.7), ("c3c6bf", 0.05, 0.68, 8, 0.6)]),
}
SLOPE_BLUR = 0.035  # share of the tile
DIRECTION_BLUR = 0.03  # share of the tile
DIRECTION = 0.5  # radians
SHARPEN = 1.1
PLANE_STEPS = 6
PLANE_MIX = 0.6


def hexc(h):
	return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def noise(size, feature, seed):
	"""periodic gaussian noise, feature as a share of the tile, scaled to 0..1 by rank-like clipping"""
	spec = np.fft.fft2(np.random.RandomState(seed).normal(size=(size, size)))
	f = np.fft.fftfreq(size)
	d2 = f[:, None] ** 2 + f[None, :] ** 2
	o = np.fft.ifft2(spec * np.exp(-d2 * (np.pi * feature * size) ** 2 * 2)).real
	return np.clip(o / (o.std() * 4) + 0.5, 0, 1).astype(np.float32)


def spots(size, feature, seed):
	"""BnW Spots: blotches with finer speckle inside"""
	return noise(size, feature, seed) * 0.72 + noise(size, feature * 0.3, seed + 1) * 0.28


def levels(v, balance, contrast):
	return np.clip((v - balance) * contrast + 0.5, 0, 1)


def advect(v, dx, dy, samples):
	"""average v along a per-pixel offset, wrapping"""
	h, w = v.shape
	yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
	out = np.zeros_like(v)
	for i in range(samples):
		t = i / (samples - 1) - 0.5
		out += map_coordinates(v, [yy + dy * t, xx + dx * t], order=1, mode="grid-wrap")
	return out / samples


def slope_blur(v, slope, reach):
	"""blur along the slope of a second map, the filter that makes strokes"""
	gy, gx = np.gradient(gaussian_filter(slope, 3, mode="wrap"))
	m = np.sqrt(gx * gx + gy * gy) + 1e-5
	return advect(v, gx / m * reach, gy / m * reach, 9)


def direction_blur(v, reach, angle):
	return advect(v, np.full(v.shape, np.cos(angle) * reach, np.float32), np.full(v.shape, np.sin(angle) * reach, np.float32), 7)


def sharpen(v, amount, radius=2.0):
	return np.clip(v + (v - gaussian_filter(v, radius, mode="wrap")) * amount, 0, 1)


def stroke_mask(size, feature, balance, contrast, seed):
	v = levels(spots(size, feature, seed), balance, contrast)
	v = slope_blur(v, noise(size, feature * 0.8, seed + 2), SLOPE_BLUR * size)
	v = direction_blur(v, DIRECTION_BLUR * size, DIRECTION + (seed % 5) * 0.5)
	v = gaussian_filter(v, 0.8, mode="wrap")
	return sharpen(v, SHARPEN)


def build(name, size, style):
	seed, tint, base, layers = MATERIALS[name]
	col = np.ones((size, size, 3), np.float32) * hexc(base)
	for i, (colour, feature, balance, contrast, opacity) in enumerate(layers):
		m = stroke_mask(size, feature, balance, contrast, seed * 10 + i)[..., None] * opacity
		col = col * (1 - m) + hexc(colour) * m
	if style == "planes":
		# soft value steps: scale each pixel's colour so its brightness lands on a painted step
		lum = np.maximum(col @ np.array([0.3, 0.59, 0.11], np.float32), 1e-3)
		lo, hi = np.percentile(lum, 1), np.percentile(lum, 99)
		q = np.clip((lum - lo) / (hi - lo), 0, 1) * PLANE_STEPS
		f = q - np.floor(q)
		stepped = (np.floor(q) + np.clip((f - 0.3) / 0.4, 0, 1)) / PLANE_STEPS * (hi - lo) + lo
		col = np.clip(col * (1 + (stepped / lum - 1) * PLANE_MIX)[..., None], 0, 1)
	return col, hexc(tint)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("out")
	ap.add_argument("--size", type=int, default=1024)
	a = ap.parse_args()
	rows = []
	for style in ("recipe", "planes"):
		folder = os.path.join(a.out, style)
		os.makedirs(folder, exist_ok=True)
		row = []
		for name in MATERIALS:
			col, tint = build(name, a.size, style)
			Image.fromarray((np.clip(col / tint, 0, 1) * 255).astype(np.uint8)).save(os.path.join(folder, f"{name}_Tile.png"))
			row.append(np.concatenate([col, col], 1)[: a.size])  # two repeats side by side shows any seam
		rows.append(np.concatenate(row, 0))
		print(style, "done")
	sheet = np.concatenate(rows, 1)
	Image.fromarray((np.clip(sheet, 0, 1) * 255).astype(np.uint8)).resize((sheet.shape[1] // 2, sheet.shape[0] // 2), Image.LANCZOS).save(os.path.join(a.out, "preview.jpg"), quality=90)


if __name__ == "__main__":
	main()
