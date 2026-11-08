"""Paint the foliage card textures (RGBA, transparent around the foliage) for tools/blender/card_trees.py.

  python tools/art/foliage_textures.py            -> art/kit/textures/needles.png, leaves.png, leaves_autumn.png

needles: a spruce branch lying along +u (twig from the left edge to the tip on the right), side twigs, needles angled
forward, darker underneath and lighter on top. leaves: a round cluster of pointed leaves, denser and darker in the
middle. Painted at 2x and scaled down for clean edges; colour is bled into the transparent area so mipmaps don't get
dark fringes (Roblox and Blender both filter across the cut-out edge).
"""

import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "textures")


def hexc(h):
	return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
	return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def vary(c, r, k=0.08):
	f = 1 + r.uniform(-k, k)
	return tuple(max(0, min(255, int(v * f))) for v in c)


def bleed(img):
	"""fill transparent pixels with the nearby foliage colour (alpha unchanged)"""
	a = np.asarray(img, np.float32) / 255
	rgb, al = a[..., :3], a[..., 3:4]
	acc_c, acc_a = rgb * al, al.copy()
	out = rgb.copy()
	for radius in (2, 4, 8, 16, 32, 64):
		bc = np.asarray(Image.fromarray((acc_c * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255
		ba = np.asarray(Image.fromarray((acc_a[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius)), np.float32)[..., None] / 255
		fill = (ba > 0.002) & (al < 0.5)
		est = bc / np.maximum(ba, 1e-4)
		out = np.where(fill & (out.sum(-1, keepdims=True) == rgb.sum(-1, keepdims=True)), est, out)
	res = np.concatenate([np.where(al > 0.5, rgb, out), al], -1)
	return Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8), "RGBA")


def needles(seed=3, w=1024, h=512):
	S = 2
	W, H = w * S, h * S
	img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	r = random.Random(seed)
	dark, mid, light = hexc("223d35"), hexc("3c6254"), hexc("6e9483")
	twig = hexc("4a3a2c")

	def branch(x0, y0, ang, length, width, depth):
		pts = []
		steps = 40
		for i in range(steps + 1):
			t = i / steps
			a = ang + math.sin(t * 2.5) * 0.08 * (1 if depth == 0 else -1)
			pts.append((x0 + math.cos(a) * length * t, y0 + math.sin(a) * length * t))
		# needles first (under the twig), back to front: lower side darker, upper side lighter
		for side in (1, -1):
			for i in range(1, steps + 1):
				t = i / steps
				px, py = pts[i]
				nl = (1 - t * 0.55) * width * r.uniform(0.75, 1.1)
				for _ in range(4):
					a = ang + side * r.uniform(0.6, 1.1) + r.uniform(-0.1, 0.1)
					ex, ey = px + math.cos(a) * nl, py + math.sin(a) * nl
					shade = 0.65 * (side < 0) + r.uniform(0, 0.35)  # side -1 = upper (y up in the image is -)
					c = lerp(dark, light, shade) if side < 0 else lerp(dark, mid, r.uniform(0, 0.6))
					d.line([(px, py), (ex, ey)], fill=vary(c, r) + (255,), width=max(2, int(S * 3.0)))
		d.line(pts, fill=twig + (255,), width=max(2, int(S * (4 if depth == 0 else 2.5))))
		if depth == 0:
			for i in range(3, steps - 3, 3):
				t = i / steps
				px, py = pts[i]
				for side in (1, -1):
					if r.random() < 0.85:
						sa = r.uniform(0.45, 0.65)
						sl = min(length * (1 - t) * r.uniform(0.26, 0.34), H * 0.36 / math.sin(sa))
						branch(px, py, ang + side * sa, sl, width * 0.8, 1)

	branch(int(W * 0.01), H // 2, 0.0, W * 0.96, H * 0.16, 0)
	img = img.resize((w, h), Image.LANCZOS)
	return bleed(img)


def leaves(seed=5, size=1024, palette=("2a4f2e", "4f7d3c", "93b35e")):
	S = 2
	N = size * S
	img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	r = random.Random(seed)
	dark, mid, light = (hexc(p) for p in palette)
	cx = cy = N / 2
	R = N * 0.44
	items = []
	for _ in range(520):
		rr = R * math.sqrt(r.random())
		a = r.uniform(0, math.tau)
		x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
		items.append((y, x, rr))
	items.sort()  # paint top to bottom so lower leaves overlap upper ones a little
	for y, x, rr in items:
		size_l = N * r.uniform(0.035, 0.055)
		ang = r.uniform(0, math.tau)
		top = 1 - (y - (cy - R)) / (2 * R)  # lighter toward the top of the cluster
		edge = rr / R
		t = min(1, max(0, 0.25 + 0.55 * top + 0.25 * edge + r.uniform(-0.15, 0.15)))
		c = lerp(dark, mid, t * 2) if t < 0.5 else lerp(mid, light, (t - 0.5) * 2)
		pts = []
		for k in range(12):
			s = k / 12 * math.tau
			lx = math.cos(s) * size_l
			ly = math.sin(s) * size_l * 0.45 * (1 - 0.35 * math.cos(s))
			pts.append((x + lx * math.cos(ang) - ly * math.sin(ang), y + lx * math.sin(ang) + ly * math.cos(ang)))
		d.polygon(pts, fill=vary(c, r, 0.06) + (255,))
	img = img.resize((size, size), Image.LANCZOS)
	return bleed(img)


def grass_tuft(seed=9, w=1024, h=512, blades=70):
	"""a grass tuft card (u across, v up): tapered curved blades fanning out of the bottom middle, white at the root
	and tip-tinted so a material can multiply in the ground colour; dark-to-light gradient up each blade"""
	S = 2
	W, H = w * S, h * S
	img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	r = random.Random(seed)
	order = sorted(range(blades), key=lambda k: r.random())
	for k in order:
		x0 = W / 2 + r.gauss(0, W * 0.09)
		lean = r.gauss(0, 0.35) + (x0 - W / 2) / (W * 0.25)
		hgt = H * r.uniform(0.45, 0.97)
		width = W * r.uniform(0.012, 0.02)
		steps = 14
		pts_l, pts_r = [], []
		for i in range(steps + 1):
			t = i / steps
			x = x0 + lean * hgt * 0.5 * t * t
			y = H - hgt * t
			hw = width * (1 - t) ** 0.8
			pts_l.append((x - hw, y))
			pts_r.append((x + hw, y))
		shade = r.uniform(0.0, 1.0)
		for i in range(steps):  # draw as stacked quads so each band gets its gradient value
			t = (i + 0.5) / steps
			v = int(255 * (0.45 + 0.55 * t) * (0.85 + 0.15 * shade))
			d.polygon([pts_l[i], pts_r[i], pts_r[i + 1], pts_l[i + 1]], fill=(v, v, v, 255))
	img = img.resize((w, h), Image.LANCZOS)
	return bleed(img)


def main():
	os.makedirs(OUT, exist_ok=True)
	grass_tuft().save(os.path.join(OUT, "grass_tuft.png"))
	needles().save(os.path.join(OUT, "needles.png"))
	leaves().save(os.path.join(OUT, "leaves.png"))
	leaves(seed=6, palette=("8a3f17", "c9702a", "efb04a")).save(os.path.join(OUT, "leaves_autumn.png"))
	print("written to", OUT)


if __name__ == "__main__":
	main()
