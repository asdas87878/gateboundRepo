"""Crisp paint, the method from the stone bridge (docs/style/crisp-paint.md): firm brushed shapes, clusters of fine marks and a sharpen, so a texture holds up close with a slight painted grain.
Use it either way:
  on any finished sheet, same layout, so it fits the model as it is (colours come from the sheet, no palette needed):
    python tools/art/crisp_paint.py <in.png> <out.png> [--look crisp|soft] [--grain x|none] [--strength 1.0] [--seed 5] [--shapes N] [--marks N] [--dark N] [--sharpen N]
  or inside a painter:
    from crisp_paint import crisp_pass, brushed_wash, chisel_marks, sharpen
--look soft keeps the grain but not the hard finish: fainter shapes, paler marks, almost no sharpen, the island's brightness kept.
--grain x: marks and shapes run along the sheet's x, for wood painted with its grain along x (the fence, the props). --grain none: any direction, for stone.
"""
import argparse
import math

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label


def ss(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def over(img, colour, a):
	a = np.clip(a, 0, 1)[..., None]
	return img * (1 - a) + colour * a


def smooth1d(n, width, rng):
	v = rng.normal(size=n + width * 4)
	v = np.convolve(v, np.ones(width) / width, "same")[width * 2 : width * 2 + n]
	return v / (np.abs(v).max() + 1e-6)


def jagged(H, W, rng, scale):
	"""noise of a given size, one standard deviation = 1: what makes an edge wander"""
	n = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), scale)
	return n / (n.std() + 1e-6)


def lines(shape, count, length, half, rng, wander):
	"""thin curving lines into a mask, tapered at both ends"""
	H, W = shape
	m = np.zeros(shape, np.float32)
	for _ in range(count):
		n = int(rng.uniform(*length) * W)
		x0 = int(rng.uniform(-0.1, 0.9) * W)
		xa, xb = max(x0, 0), min(x0 + n, W)
		if xb - xa < 6:
			continue
		n = xb - xa
		c = rng.uniform(0, H) + np.cumsum(smooth1d(n, max(n // 3, 4), rng)) / n * wander * 3 + rng.uniform(-0.25, 0.25) * np.arange(n)
		t = np.arange(n) / n
		w = half * np.minimum(1, np.minimum(t, 1 - t) * 5) * rng.uniform(0.6, 1.1) + 0.15
		rows = np.arange(H)[:, None]
		v = np.clip(w[None, :] - np.abs(rows - c[None, :]), 0, 1)
		m[:, xa:xb] = np.maximum(m[:, xa:xb], v * rng.uniform(0.55, 1))
	return m


def brushed_mask(H, W, rng, scale, radii=((0.3, 0.55), (0.2, 0.4)), tilt=0.35, centre=None):
	"""the key shape: an ellipse roughened with noise, then cut hard and barely softened. A firm edge that wanders: painted, not airbrushed.
	scale is the painting's pixels per sheet pixel (2 if painted at double size)."""
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	cx, cy = (rng.uniform(0, W), rng.uniform(0, H)) if centre is None else centre
	a = rng.uniform(-tilt, tilt)
	dx, dy = (xx - cx) * math.cos(a) + (yy - cy) * math.sin(a), -(xx - cx) * math.sin(a) + (yy - cy) * math.cos(a)
	f = (dx / rng.uniform(*radii[0]) / W) ** 2 + (dy / rng.uniform(*radii[1]) / H) ** 2 + jagged(H, W, rng, 2.2 * scale) * 0.13 + jagged(H, W, rng, 0.7 * scale) * 0.04
	return gaussian_filter((f < 1).astype(np.float32), 0.4 * scale)


def brushed_wash(img, colour, strength, rng, scale):
	"""a flat wash of one colour in a brushed shape"""
	H, W = img.shape[:2]
	return over(img, colour, brushed_mask(H, W, rng, scale) * strength)


def hewn_plane(img, colour, strength, rng, scale):
	"""a straight firm edge with one side a touch different"""
	H, W = img.shape[:2]
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	cx, cy, a = rng.uniform(0.15, 0.85) * W, rng.uniform(0.1, 0.9) * H, rng.uniform(-0.9, 0.9)
	d = (xx - cx) * math.sin(a) - (yy - cy) * math.cos(a)
	return over(img, colour, gaussian_filter((d > 0).astype(np.float32), 0.3 * scale) * strength)


def mark_mask(H, W, rng, scale, cx, cy, a, spread):
	"""a cluster of short fine strokes, each stamped pixel by pixel and tapered, then barely softened"""
	m = np.zeros((H, W), np.float32)
	for _k in range(int(rng.integers(3, 7))):
		ln = rng.uniform(3, 9) * scale
		ox, oy = rng.normal(0, spread), rng.normal(0, spread * 0.5)
		for f in np.linspace(0, 1, int(ln) + 2):
			x, y = int(cx + ox + math.cos(a) * ln * f), int(cy + oy + math.sin(a) * ln * f)
			if 0 <= x < W and 0 <= y < H:
				m[y, x] = min(1, 4 * f * (1 - f) + 0.1)
	return np.clip(gaussian_filter(m, 0.42 * scale) * 3.2, 0, 1)


def chisel_marks(img, rng, dark, light, scale, strength=0.5, along=False):
	"""clusters of marks, close in colour, most of them dark. The number follows the area. along=True keeps them on the x axis, for wood grain"""
	H, W = img.shape[:2]
	per = W * H / (150 * scale * 150 * scale)
	for _ in range(int(rng.integers(2, 4) + per * 3)):
		cx, cy, a, spread = rng.uniform(0.08, 0.92) * W, rng.uniform(0.08, 0.92) * H, rng.uniform(0.5, 1.2) * rng.choice((-1, 1)), rng.uniform(4, 9) * scale
		if along:
			a = a * 0.12
		colour = dark if rng.random() < 0.6 else light
		img = over(img, colour, mark_mask(H, W, rng, scale, cx, cy, a, spread) * strength)
	return img


def sharpen(img, amount, scale, radius=1.1):
	"""the finishing fringe: every painted edge gets a thin light and dark side"""
	return np.clip(img + (img - gaussian_filter(img, (radius * scale, radius * scale, 0))) * amount, 0, 255)


# how much of each ingredient. shapes and marks make the grain; dark and sharpen make it hard and heavy; keep_brightness puts each island's average colour back
LOOKS = {
	"crisp": dict(shapes=1.0, marks=1.0, dark=1.0, sharpen=1.0, keep_brightness=False),
	"soft": dict(shapes=1.1, marks=0.9, dark=0.35, sharpen=0.2, keep_brightness=True),
}


def crisp_pass(img, rng, scale=2, along=True, strength=1.0, mask=None, shapes=1.0, marks=1.0, dark=1.0, sharpen_by=1.0, keep_brightness=False):
	"""the whole method over paint that already exists, with colours taken from that paint. Shapes tint what's there, so grain and highlights underneath survive.
	img: float RGB, painted at scale times the final size. mask: where to paint, 1 inside the island. shapes, marks, dark and sharpen_by scale each ingredient (see LOOKS)."""
	H, W = img.shape[:2]
	inside = np.ones((H, W), bool) if mask is None else mask > 0.5
	if inside.sum() < 16:
		return img
	mean = img[inside].mean(axis=0)
	out = img.astype(np.float32).copy()
	# firm-edged shapes, a few per island, the size of a big brush whatever the island's size
	reach = 90 * scale
	wide, tall = min(W, reach * 2), min(H, reach)
	radii = ((0.25 * wide / W, 0.5 * wide / W), (0.18 * tall / H, 0.42 * tall / H))
	if along:
		radii = (radii[0], (radii[1][0] * 0.55, radii[1][1] * 0.55))
	count = max(3, int(W * H / (reach * reach * 0.7)))
	for i in range(count):
		tint = np.array((1.075, 1.05, 1.0)) if i % 2 == 0 else 1 + (np.array((0.93, 0.92, 0.96)) - 1) * dark
		m = brushed_mask(H, W, rng, scale, radii, 0.08 if along else 0.35)
		out = out * (1 + (tint - 1)[None, None, :] * (m * strength * shapes)[..., None])
	dark_mark = mean * (1 + (np.array((0.8, 0.77, 0.84)) - 1) * dark)
	light_mark = mean * np.array((1.2, 1.17, 1.08))
	out = chisel_marks(out, rng, dark_mark, light_mark, scale, 0.5 * strength * marks, along)
	out = sharpen(out, 0.9 * strength * sharpen_by, scale)
	if keep_brightness:
		out = np.clip(out * (mean / (out[inside].mean(axis=0) + 1e-6))[None, None, :], 0, 255)
	return np.where(inside[..., None], out, img)


def crisp_sheet(sheet, rng, grain=True, strength=1.0, background_tolerance=8, **ingredients):
	"""a finished sheet (H, W, 3, 0-255): paint at double size, island by island so nothing crosses a seam, and shrink back"""
	base = Image.fromarray(np.clip(sheet, 0, 255).astype(np.uint8))
	big = np.array(base.resize((base.width * 2, base.height * 2), Image.LANCZOS)).astype(np.float32)
	# the background is the most common colour; everything else, in connected pieces, is an island
	flat = big.astype(np.uint8).reshape(-1, 3)
	values, counts = np.unique(flat[:: max(1, flat.shape[0] // 200000)], axis=0, return_counts=True)
	back = values[counts.argmax()].astype(np.float32)
	share = counts.max() / counts.sum()
	found = np.abs(big - back).max(axis=2) > background_tolerance if share > 0.05 else np.ones(big.shape[:2], bool)
	labels, n = label(found)
	boxes = __import__("scipy.ndimage", fromlist=["find_objects"]).find_objects(labels)
	painted = 0
	for i, box in enumerate(boxes):
		y, x = box
		if y.stop - y.start < 24 or x.stop - x.start < 24:
			continue
		crop = big[y.start : y.stop, x.start : x.stop]
		big[y.start : y.stop, x.start : x.stop] = crisp_pass(crop, rng, 2, grain, strength, (labels[box] == i + 1).astype(np.float32), **ingredients)
		painted += 1
	done = Image.fromarray(np.clip(big, 0, 255).astype(np.uint8)).resize((base.width, base.height), Image.LANCZOS)
	return np.array(done), painted


def main():
	ap = argparse.ArgumentParser(description="Crisp paint over a finished texture sheet; same layout, so it fits the model as it is")
	ap.add_argument("input")
	ap.add_argument("output")
	ap.add_argument("--grain", choices=("x", "none"), default="x")
	ap.add_argument("--strength", type=float, default=1.0)
	ap.add_argument("--seed", type=int, default=5)
	ap.add_argument("--look", choices=tuple(LOOKS), default="crisp")
	for name in ("shapes", "marks", "dark", "sharpen"):
		ap.add_argument("--" + name, type=float, help="override the look's amount of this ingredient")
	args = ap.parse_args()
	sheet = np.array(Image.open(args.input).convert("RGB"))
	look = dict(LOOKS[args.look])
	for name in ("shapes", "marks", "dark", "sharpen"):
		if getattr(args, name) is not None:
			look[name] = getattr(args, name)
	look["sharpen_by"] = look.pop("sharpen")
	done, painted = crisp_sheet(sheet, np.random.default_rng(args.seed), args.grain == "x", args.strength, **look)
	Image.fromarray(done).save(args.output)
	print("painted", painted, "islands ->", args.output)


if __name__ == "__main__":
	main()
