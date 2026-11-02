"""Put the zone and place names on a block-out's aerial render (positions from labels.json).

  python tools/art/land_labels.py art/lands/land1/blockout      -> aerial_labelled.png
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def main():
	d = sys.argv[1]
	im = Image.open(os.path.join(d, "aerial.png")).convert("RGB")
	W, H = im.size
	dr = ImageDraw.Draw(im, "RGBA")
	big, small = ImageFont.truetype("georgiab.ttf", 26), ImageFont.truetype("georgia.ttf", 18)
	for lb in json.load(open(os.path.join(d, "labels.json"))):
		x, y = lb["X"] * W, lb["Y"] * H
		f = big if lb["Kind"] == "zone" else small
		b = dr.textbbox((0, 0), lb["Text"], font=f)
		tx, ty = x - (b[2] - b[0]) / 2, y - (b[3] - b[1]) / 2
		dr.rectangle((tx - 6, ty - 3, tx + b[2] - b[0] + 6, ty + b[3] - b[1] + 7), fill=(255, 250, 235, 190) if lb["Kind"] == "zone" else (30, 30, 34, 170))
		dr.text((tx, ty), lb["Text"], font=f, fill=(40, 36, 28) if lb["Kind"] == "zone" else (255, 255, 255))
	im.save(os.path.join(d, "aerial_labelled.png"))


if __name__ == "__main__":
	main()
