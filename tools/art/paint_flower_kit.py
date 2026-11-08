"""Paint the flower kit's textures (tools/blender/flower_kit.py): the leaf mound and the card atlas in three colourways.

  python tools/art/paint_flower_kit.py      art/kit/flowers: FlowerMound_Color.png, FlowerCards_White.png, _Pink.png, _Mixed.png (1024)

The mound: overlapping painted leaves on a dark-foot-to-lit-top ramp, repeating across (u runs round each mound). The cards: a 4 x 4 atlas,
cells 0-7 leaf fans growing from the bottom middle (side cards stand on the mound by their foot), 8-15 flower clusters over a few leaves.
Every leaf and petal is a shape painted in two or three tones, lit from above, with soft edges: drawn at 4x and shrunk. Colour is spread
under the transparent parts so the edges have no dark fringe in Roblox.
"""

import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "flowers")
FINAL, SS = 1024, 4
N = FINAL * SS
GRID = 4
CELL = N // GRID

LEAF = [(34, 76, 58), (48, 102, 66), (66, 130, 74), (96, 160, 86), (136, 190, 104)]  # foot shade to top light
DAISY = {"Petal": (247, 246, 239), "Shade": (208, 212, 228), "Eye": (242, 198, 70), "EyeShade": (212, 146, 50), "EyeLit": (255, 236, 150)}
PINK = {"Petal": (247, 172, 198), "Mid": (230, 136, 170), "Shade": (204, 104, 146), "Eye": (176, 76, 116), "Dot": (250, 220, 120)}
LILAC = {"Petal": (200, 176, 238), "Shade": (154, 128, 210), "Eye": (250, 240, 200)}
YELLOW = {"Petal": (255, 216, 92), "Shade": (234, 172, 52), "Eye": (214, 136, 40)}
VARIANTS = {
	"White": ["daisy"] * 7 + ["daisy_small"],
	"Pink": ["pink"] * 7 + ["pink_small"],
	"Mixed": ["daisy", "daisy_small", "pink", "pink", "lilac", "lilac", "yellow", "daisy"],
}


def jitter(c, r, amount):
	k = 1 + r.uniform(-amount, amount)
	return tuple(int(max(0, min(255, v * k))) for v in c)


def mix(a, b, t):
	return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def leaf_poly(cx, cy, length, width, angle, curve=0.0, steps=14):
	"""a pointed leaf from its base (cx, cy) along angle (radians, image space): returns its outline and its two halves"""
	ca, sa = math.cos(angle), math.sin(angle)
	left, right = [], []
	for i in range(steps + 1):
		t = i / steps
		w = width * math.sin(math.pi * t) ** 0.8 * (1 - 0.25 * t)
		along = length * t
		bend = curve * length * t * t
		for side, out in ((1, left), (-1, right)):
			x, y = along, side * w / 2 + bend
			out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
	return left + right[::-1], left, right


def draw_leaf(d, r, cx, cy, length, width, angle, tones, curve=0.0):
	"""two tones split down the midrib (the side facing the light lighter), a soft lighter midrib stroke"""
	poly, left, right = leaf_poly(cx, cy, length, width, angle, curve)
	lit_left = math.sin(angle) < 0  # the half facing up the image catches the light
	dark, light = tones
	d.polygon(poly, fill=dark)
	mid = [((left[i][0] + right[i][0]) / 2, (left[i][1] + right[i][1]) / 2) for i in range(len(left))]
	d.polygon((left if lit_left else right) + mid[::-1], fill=light)
	d.line(mid[1:-2], fill=mix(light, (230, 240, 190), 0.35), width=max(1, int(width * 0.06)))


# ---------------------------------------------------------------------------------------------------------------- the mound
def mound():
	r = random.Random(3)
	img = Image.new("RGB", (N, N), LEAF[1])
	d = ImageDraw.Draw(img)
	# the ramp: image bottom is the mound's foot (v small), top its crown
	for y in range(0, N, 8):
		t = 1 - y / N
		k = min(len(LEAF) - 2, int(t * (len(LEAF) - 1)))
		f = t * (len(LEAF) - 1) - k
		d.rectangle([0, y, N, y + 8], fill=mix(LEAF[k], LEAF[k + 1], f))
	# leaves in passes, dark and big first, lighter and smaller over them, more and lighter toward the top
	for pas, (count, size, lift) in enumerate(((900, 1.0, -0.12), (1100, 0.85, 0.0), (900, 0.7, 0.12))):
		for _ in range(count):
			x, y = r.uniform(0, N), r.uniform(0, N)
			t = 1 - y / N + lift + r.uniform(-0.1, 0.1)
			k = max(0, min(len(LEAF) - 2, int(t * (len(LEAF) - 1))))
			dark = jitter(LEAF[k], r, 0.08)
			light = jitter(LEAF[min(k + 1, len(LEAF) - 1)], r, 0.06)
			length = r.uniform(110, 190) * size
			width = length * r.uniform(0.34, 0.46)
			ang = -math.pi / 2 + r.uniform(-1.2, 1.2)  # mostly pointing up the mound
			for dx in (-N, 0, N):  # across the seam, so it repeats round the mound
				draw_leaf(d, r, x + dx, y, length, width * 0.75, ang, (dark, light), r.uniform(-0.15, 0.15))
	img = img.filter(ImageFilter.GaussianBlur(1.5)).resize((FINAL, FINAL), Image.LANCZOS)
	img.save(os.path.join(OUT, "FlowerMound_Color.png"))
	print("saved FlowerMound_Color.png", flush=True)


# ---------------------------------------------------------------------------------------------------------------- the cards
def leaf_fan(d, r, ox, oy, dark_bias=0.0):
	"""leaves growing from the bottom middle of a cell, fanning up and out, the inner ones darker"""
	n = r.randint(6, 9)
	base = (ox + CELL / 2 + r.uniform(-10, 10), oy + CELL * 0.97)
	leaves = []
	for i in range(n):
		ang = -math.pi / 2 + (i / (n - 1) - 0.5) * r.uniform(1.9, 2.5) + r.uniform(-0.12, 0.12)
		length = CELL * r.uniform(0.55, 0.82) * (1 - 0.25 * abs(i / (n - 1) - 0.5))
		leaves.append((abs(i / (n - 1) - 0.5), ang, length))
	for outer, ang, length in sorted(leaves, key=lambda l: -l[0]):  # outer ones first, the middle ones over them
		k = 1 + int((1 - outer * 2) * 2 + dark_bias)
		k = max(0, min(len(LEAF) - 2, k))
		draw_leaf(d, r, base[0], base[1], length, length * r.uniform(0.32, 0.42), ang, (jitter(LEAF[k], r, 0.07), jitter(LEAF[k + 1], r, 0.06)), r.uniform(-0.18, 0.18))


def daisy(d, r, cx, cy, rad):
	n = r.randint(12, 16)
	rot = r.uniform(0, math.pi)
	for i in range(n):
		a = rot + 2 * math.pi * i / n
		lower = math.sin(a) > 0.2  # petals hanging toward the bottom of the image sit in the flower's own shade
		col = mix(DAISY["Petal"], DAISY["Shade"], 0.75 if lower else r.uniform(0.0, 0.2))
		poly, _, _ = leaf_poly(cx, cy, rad * r.uniform(0.92, 1.05), rad * 0.34, a, 0.0, 10)
		d.polygon(poly, fill=jitter(col, r, 0.02))
	e = rad * 0.3
	d.ellipse([cx - e, cy - e, cx + e, cy + e], fill=DAISY["EyeShade"])
	d.ellipse([cx - e * 0.92, cy - e, cx + e * 0.8, cy + e * 0.75], fill=DAISY["Eye"])
	h = e * 0.32
	d.ellipse([cx - e * 0.45 - h, cy - e * 0.45 - h, cx - e * 0.45 + h, cy - e * 0.45 + h], fill=DAISY["EyeLit"])


def blossom(d, r, cx, cy, rad, pal, petals=5, eye=True):
	rot = r.uniform(0, 2 * math.pi)
	for i in range(petals):
		a = rot + 2 * math.pi * i / petals
		px, py = cx + math.cos(a) * rad * 0.48, cy + math.sin(a) * rad * 0.48
		pr = rad * 0.56
		lower = math.sin(a) > 0.3
		col = pal["Shade"] if lower else pal.get("Mid", pal["Petal"]) if math.sin(a) > -0.3 else pal["Petal"]
		d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=jitter(col, r, 0.03))
		lit = pr * 0.55
		if not lower:
			d.ellipse([px - lit, py - lit - pr * 0.25, px + lit * 0.7, py + lit * 0.4], fill=jitter(pal["Petal"], r, 0.02))
	if eye:
		e = rad * 0.2
		d.ellipse([cx - e, cy - e, cx + e, cy + e], fill=pal["Eye"])
		if "Dot" in pal:
			for _ in range(3):
				dx, dy = r.uniform(-e, e) * 0.6, r.uniform(-e, e) * 0.6
				d.ellipse([cx + dx - e * 0.25, cy + dy - e * 0.25, cx + dx + e * 0.25, cy + dy + e * 0.25], fill=pal["Dot"])


def flower_cell(d, r, ox, oy, kind):
	# a few leaves low down, the heads over them in a loose dome
	for _ in range(r.randint(3, 5)):
		ang = -math.pi / 2 + r.uniform(-1.3, 1.3)
		length = CELL * r.uniform(0.3, 0.45)
		bx, by = ox + CELL / 2 + r.uniform(-CELL * 0.25, CELL * 0.25), oy + CELL * r.uniform(0.72, 0.92)
		draw_leaf(d, r, bx, by, length, length * 0.4, ang, (jitter(LEAF[1], r, 0.06), jitter(LEAF[2], r, 0.06)))
	small = kind.endswith("_small")
	heads = r.randint(7, 11) if small or kind in ("lilac",) else r.randint(4, 6)
	placed = []
	for _ in range(heads):
		for _try in range(30):
			rad = CELL * (r.uniform(0.07, 0.1) if small or kind == "lilac" else r.uniform(0.12, 0.17))
			cx = ox + CELL / 2 + r.gauss(0, CELL * 0.17)
			cy = oy + CELL * 0.5 + r.gauss(0, CELL * 0.12) - CELL * 0.05
			if ox + rad < cx < ox + CELL - rad and oy + rad < cy < oy + CELL * 0.85 and all(math.hypot(cx - p[0], cy - p[1]) > (rad + p[2]) * 0.72 for p in placed):
				placed.append((cx, cy, rad))
				break
	for cx, cy, rad in sorted(placed, key=lambda p: p[1]):  # back (higher) heads first, the front ones overlap them
		if kind.startswith("daisy"):
			daisy(d, r, cx, cy, rad)
		elif kind.startswith("pink"):
			blossom(d, r, cx, cy, rad, PINK)
		elif kind == "lilac":
			blossom(d, r, cx, cy, rad, LILAC, petals=4)
		else:
			blossom(d, r, cx, cy, rad, YELLOW)


def cards(variant):
	r = random.Random(7)  # the same leaves and layout in every colourway; only the flower kinds differ
	img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	for cell in range(GRID * GRID):
		ox, oy = (cell % GRID) * CELL, (cell // GRID) * CELL
		if cell < 8:
			leaf_fan(d, r, ox, oy, dark_bias=-0.5 if cell % 2 else 0.0)
		else:
			flower_cell(d, random.Random(1000 + cell), ox, oy, VARIANTS[variant][cell - 8])
	img = img.filter(ImageFilter.GaussianBlur(1.2)).resize((FINAL, FINAL), Image.LANCZOS)
	a = np.asarray(img).astype(np.float32)
	alpha = a[..., 3]
	solid = alpha > 200
	idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
	rgb = a[..., :3][idx[0], idx[1]]  # spread the colour under the clear parts: no dark fringe
	out = np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8)
	Image.fromarray(out, "RGBA").save(os.path.join(OUT, f"FlowerCards_{variant}.png"))
	print("saved", f"FlowerCards_{variant}.png", flush=True)


if __name__ == "__main__":
	os.makedirs(OUT, exist_ok=True)
	mound()
	for v in VARIANTS:
		cards(v)
