"""Calm, seamless terrain tiles for custom terrain materials (MaterialVariant colour maps).

The tile holds only soft value change, near white: Roblox multiplies it by the terrain material's colour, so the palette stays in
Studio and one tile can serve many biomes. Periodic noise (filtered in frequency space) makes it tile with no seams.

usage: make_terrain_tiles.py <out folder> [--size 1024]
"""
import argparse
import os

import numpy as np
from PIL import Image

# name: (seed, [(feature size as a share of the tile, strength)], lowest value, highest value)
TILES = {
	"Grass": (3, [(0.30, 0.55), (0.10, 0.30), (0.035, 0.15)], 205, 255),
	"Dirt": (8, [(0.34, 0.5), (0.12, 0.33), (0.05, 0.17)], 200, 255),
	"Sand": (5, [(0.40, 0.6), (0.14, 0.3), (0.03, 0.1)], 222, 255),
}


def periodic_noise(size, feature, seed):
	"""white noise blurred in frequency space, so it wraps; scaled to -1..1"""
	r = np.random.RandomState(seed)
	spec = np.fft.fft2(r.normal(size=(size, size)))
	f = np.fft.fftfreq(size)
	d2 = f[:, None] ** 2 + f[None, :] ** 2
	out = np.fft.ifft2(spec * np.exp(-d2 * (np.pi * feature) ** 2 * 2)).real
	return out / np.abs(out).max()


def build(size, seed, layers, low, high):
	v = sum(periodic_noise(size, feat, seed + i) * amt for i, (feat, amt) in enumerate(layers))
	v = (v - v.min()) / (v.max() - v.min())
	# painted patches: soft steps of value rather than a smooth cloud, the "stylized" part
	steps = 5
	q = v * steps
	v = (np.floor(q) + np.clip((q - np.floor(q) - 0.35) / 0.3, 0, 1)) / steps
	return (low + (high - low) * v).clip(0, 255).astype(np.uint8)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("out")
	ap.add_argument("--size", type=int, default=1024)
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	for name, (seed, layers, low, high) in TILES.items():
		grey = build(a.size, seed, layers, low, high)
		path = os.path.join(a.out, f"{name}_Tile.png")
		Image.fromarray(grey).convert("RGB").save(path)
		print(path, "value", grey.min(), grey.max())


if __name__ == "__main__":
	main()
