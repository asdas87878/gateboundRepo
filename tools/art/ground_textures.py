"""Paint the tiling ground detail textures (docs/style/ground.md): the close-up detail that keeps the ground crisp at a
player's feet while the vertex colours carry the big colour patches. Each texture tiles seamlessly and averages about
DETAIL_MEAN, so the shader can multiply the ground colour by tex / DETAIL_MEAN without changing its average. In Roblox
the same images are Terrain MaterialVariant colour maps (Grass, Ground, Rock) at the StudsPerTile below.

  python tools/art/ground_textures.py      -> art/kit/textures/ground_grass.png, ground_dirt.png, ground_rock.png

grass: soft mottling at two scales and thousands of short blade strokes, lighter ones a little yellower, darker ones a
little bluer. dirt: fine grit, scattered pebbles with a lit top and a dark foot, faint scuffs. rock: broad flat patches
split by thin dark cracks with a lit edge.
"""

import math
import os
import random

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "textures")
SIZE = 1024
DETAIL_MEAN = 0.72  # average value of every texture (0-1, sRGB): the shader divides by it
STUDS_PER_TILE = {"grass": 12.0, "dirt": 8.0, "rock": 16.0}


def periodic_noise(n, sigma, seed):
	"""seamless smooth noise: white noise low-passed in Fourier space (so it wraps), scaled to -1..1"""
	r = np.random.RandomState(seed)
	f = np.fft.fft2(r.randn(n, n))
	k = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
	out = np.real(np.fft.ifft2(f * np.exp(-k * (2 * math.pi * sigma) ** 2 / 2)))
	return out / np.abs(out).max()


def strokes(n, count, length, width, seed, value_fn):
	"""short strokes drawn with wrap-around (each stroke repeated across the tile edges) on a 2x canvas"""
	from PIL import Image, ImageDraw  # here, not at the top: Blender's Python imports this module for DETAIL_MEAN and has no PIL

	big = n * 2
	img = Image.new("L", (big, big), 128)
	d = ImageDraw.Draw(img)
	r = random.Random(seed)
	for _ in range(count):
		x, y = r.uniform(0, big), r.uniform(0, big)
		a = r.uniform(0, math.tau)
		L = r.uniform(*length) * 2
		w = max(1, int(r.uniform(*width) * 2))
		v = value_fn(r)
		dx, dy = math.cos(a) * L, math.sin(a) * L
		for ox in (-big, 0, big):
			for oy in (-big, 0, big):
				d.line([(x + ox, y + oy), (x + ox + dx, y + oy + dy)], fill=int(v), width=w)
	return np.asarray(img.resize((n, n), Image.LANCZOS), np.float32) / 128.0 - 1.0  # -1..1 around 0


def to_png(rgb, name):
	from PIL import Image

	rgb = rgb * (DETAIL_MEAN / rgb.mean())  # pin the average so tex / DETAIL_MEAN averages 1
	img = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))
	os.makedirs(OUT, exist_ok=True)
	img.save(os.path.join(OUT, name))
	print(f"{name}: mean {np.asarray(img, np.float32).mean() / 255:.3f}")


def grass(seed=21):
	n = SIZE
	v = 1.0 + periodic_noise(n, 90, seed) * 0.05 + periodic_noise(n, 22, seed + 1) * 0.04
	light = strokes(n, 9000, (6, 16), (1.0, 2.2), seed + 2, lambda r: 128 + r.uniform(20, 60))
	dark = strokes(n, 7000, (5, 14), (1.0, 2.0), seed + 3, lambda r: 128 - r.uniform(20, 55))
	s = np.clip(light, 0, None) * 0.14 + np.clip(dark, None, 0) * 0.12
	v = v + s
	# lighter strokes lean yellow, darker ones blue-green: a painted look without moving the average hue
	warm = np.clip(light, 0, None)[..., None] * np.array([0.05, 0.03, -0.06])
	cool = np.clip(-dark, 0, None)[..., None] * np.array([-0.03, 0.0, 0.03])
	rgb = v[..., None] * np.ones(3) + warm + cool
	to_png(rgb, "ground_grass.png")


def dirt(seed=31):
	from PIL import Image, ImageDraw

	n = SIZE
	r = np.random.RandomState(seed)
	v = 1.0 + periodic_noise(n, 60, seed) * 0.05 + periodic_noise(n, 6, seed + 1) * 0.05 + r.randn(n, n) * 0.025
	img = Image.fromarray(((np.clip(v, 0, 2) / 2) * 255).astype(np.uint8))
	big = img.resize((n * 2, n * 2), Image.BICUBIC)
	d = ImageDraw.Draw(big)
	rr = random.Random(seed + 2)
	for _ in range(900):  # pebbles: lit top, dark foot
		x, y = rr.uniform(0, n * 2), rr.uniform(0, n * 2)
		rad = rr.uniform(2.5, 9)
		for ox in (-n * 2, 0, n * 2):
			for oy in (-n * 2, 0, n * 2):
				cx, cy = x + ox, y + oy
				d.ellipse([cx - rad, cy - rad * 0.55 + rad * 0.35, cx + rad, cy + rad * 0.55 + rad * 0.35], fill=int(rr.uniform(70, 95)))
				d.ellipse([cx - rad, cy - rad * 0.55, cx + rad, cy + rad * 0.55], fill=int(rr.uniform(140, 175)))
	v = np.asarray(big.resize((n, n), Image.LANCZOS), np.float32) / 255 * 2
	scuff = strokes(n, 1500, (10, 40), (1.0, 2.5), seed + 3, lambda q: 128 + q.choice((-1, 1)) * q.uniform(10, 25))
	v = v + scuff * 0.05
	to_png(v[..., None] * np.ones(3), "ground_dirt.png")


def rock(seed=41):
	from PIL import Image, ImageDraw

	n = SIZE
	v = 1.0 + periodic_noise(n, 70, seed) * 0.08 + periodic_noise(n, 14, seed + 1) * 0.04
	# flat patches: quantise a smooth noise into a few levels (facets read as cut stone)
	q = periodic_noise(n, 40, seed + 2)
	v = v + (np.round(q * 3) / 3) * 0.05
	big = Image.fromarray(((np.clip(v, 0, 2) / 2) * 255).astype(np.uint8)).resize((n * 2, n * 2), Image.BICUBIC)
	d = ImageDraw.Draw(big)
	rr = random.Random(seed + 3)
	for _ in range(60):  # cracks: a wandering dark line with a lit edge beside it
		x, y = rr.uniform(0, n * 2), rr.uniform(0, n * 2)
		a = rr.uniform(0, math.tau)
		pts = [(x, y)]
		for _ in range(rr.randint(4, 9)):
			a += rr.uniform(-0.6, 0.6)
			L = rr.uniform(20, 70)
			x, y = x + math.cos(a) * L, y + math.sin(a) * L
			pts.append((x, y))
		for ox in (-n * 2, 0, n * 2):
			for oy in (-n * 2, 0, n * 2):
				p = [(px + ox, py + oy) for px, py in pts]
				d.line([(px + 2, py + 2) for px, py in p], fill=150, width=3)
				d.line(p, fill=55, width=3)
	v = np.asarray(big.resize((n, n), Image.LANCZOS), np.float32) / 255 * 2
	to_png(v[..., None] * np.ones(3), "ground_rock.png")


if __name__ == "__main__":
	grass()
	dirt()
	rock()
