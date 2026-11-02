"""Draw a Land's layout map from its map.json (zones, river, paths, places, waystones), parchment style.

  python tools/art/land_map.py art/lands/land1/map.json      -> map.png beside it
"""

import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCALE = 1.0  # px per stud
PAD = 60


def hexc(h, a=255):
	return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4)) + (a,)


def blob(cx, cy, rx, ry, seed, n=48):
	r = random.Random(seed)
	ph = [r.uniform(0, math.tau) for _ in range(3)]
	pts = []
	for i in range(n):
		a = i * math.tau / n
		k = 1 + 0.08 * math.sin(3 * a + ph[0]) + 0.05 * math.sin(5 * a + ph[1]) + 0.03 * math.sin(9 * a + ph[2])
		pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
	return pts


def main():
	path = sys.argv[1]
	m = json.load(open(path, encoding="utf-8"))
	W, H = (int(v * SCALE) + PAD * 2 for v in m["Size"])
	P = lambda x, y: (PAD + x * SCALE, PAD + y * SCALE)
	img = Image.new("RGBA", (W, H), hexc("efe4c8"))
	d = ImageDraw.Draw(img, "RGBA")
	big = ImageFont.truetype("georgiab.ttf", 26)
	mid = ImageFont.truetype("georgia.ttf", 18)
	small = ImageFont.truetype("georgia.ttf", 15)

	zl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	zd = ImageDraw.Draw(zl)
	for k, z in enumerate(m["Zones"]):
		cx, cy = P(*z["At"])
		zd.polygon(blob(cx, cy, z["Radius"][0] * SCALE, z["Radius"][1] * SCALE, k), fill=hexc(z["Colour"], 200))
	img.alpha_composite(zl.filter(ImageFilter.GaussianBlur(6)))
	d = ImageDraw.Draw(img, "RGBA")

	river = [P(*p) for p in m["River"]]
	d.line(river, fill=hexc("6aa6c8"), width=26, joint="curve")
	d.line(river, fill=hexc("9cc8e0"), width=12, joint="curve")
	for line in m["Paths"]:
		pts = [P(*p) for p in line]
		d.line(pts, fill=hexc("8a6a42"), width=7, joint="curve")
		d.line(pts, fill=hexc("d8b984"), width=4, joint="curve")

	for z in m["Zones"]:
		cx, cy = P(*z["At"])
		cy -= z["Radius"][1] * SCALE * 0.55  # names sit high in the zone, clear of the places
		t = z["Name"]
		b = d.textbbox((0, 0), t, font=big)
		d.text((cx - (b[2] - b[0]) / 2, cy - 40), t, font=big, fill=hexc("2e2a22"))
		lv = f"Lv {z['Levels']}"
		b = d.textbbox((0, 0), lv, font=mid)
		d.text((cx - (b[2] - b[0]) / 2, cy - 8), lv, font=mid, fill=hexc("4a4336"))

	icons = {"castle": ("H", "3d5a80"), "start": ("S", "5a8a43"), "gate": ("G", "8f2621"), "dungeon": ("D", "4b2f5e"),
			 "boss": ("B", "b0451c"), "secret": ("?", "c79a1e"), "ruin": ("R", "7b7466"), "camp": ("C", "8a6a42")}
	for p in m["Places"]:
		x, y = P(*p["At"])
		ch, col = icons[p["Icon"]]
		r = 20 if p["Icon"] in ("castle", "gate", "dungeon") else 14
		d.ellipse((x - r, y - r, x + r, y + r), fill=hexc(col), outline=hexc("f6efdc"), width=3)
		b = d.textbbox((0, 0), ch, font=mid)
		d.text((x - (b[2] - b[0]) / 2, y - (b[3] - b[1]) / 2 - 4), ch, font=mid, fill=hexc("ffffff"))
		d.text((x + r + 6, y - 9), p["Name"], font=small, fill=hexc("2e2a22"))
	for w in m.get("Waystones", []):
		x, y = P(*w)
		d.polygon([(x, y - 9), (x + 7, y), (x, y + 9), (x - 7, y)], fill=hexc("5fb3c9"), outline=hexc("1f4f5c"))

	# legend + scale bar
	lx, ly = PAD, H - PAD + 10
	d.text((lx, ly - 4), "H hub   S start   G gate guardian   D dungeon   B field boss   ? secret   R ruins   C camp   ◆ waystone"
		   "   ~ river   — paths", font=small, fill=hexc("2e2a22"))
	sx = W - PAD - 200 * SCALE
	d.line([(sx, ly + 6), (sx + 200 * SCALE, ly + 6)], fill=hexc("2e2a22"), width=3)
	d.text((sx, ly + 10), "200 studs", font=small, fill=hexc("2e2a22"))
	d.text((PAD, 14), "Gate 1: Verdant Vale (draft layout)", font=big, fill=hexc("2e2a22"))
	img.convert("RGB").save(os.path.join(os.path.dirname(path), "map.png"))


if __name__ == "__main__":
	main()
