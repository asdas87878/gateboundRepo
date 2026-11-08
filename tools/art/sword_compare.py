"""A sheet of the sword's views beside crops of the user's reference: python tools/art/sword_compare.py <tag> [out.jpg]"""

import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "sword")
tag = sys.argv[1]
ref = Image.open(os.path.join(OUT, "reference", "reference.png")).convert("RGB")
HEIGHT = 900
cells = [
	("reference", ref.crop((90, 80, 225, 610))),
	(f"{tag} whole", Image.open(os.path.join(OUT, "views", f"{tag}_whole.png")).convert("RGB").crop((280, 40, 620, 1040))),
	("reference", ref.crop((430, 80, 600, 300))),
	(f"{tag} guard", Image.open(os.path.join(OUT, "views", f"{tag}_guard.png")).convert("RGB")),
	("reference", ref.crop((0, 620, 220, 985))),
	(f"{tag} blade", Image.open(os.path.join(OUT, "views", f"{tag}_blade.png")).convert("RGB").crop((230, 0, 690, 1100))),
]
scaled = []
for label, im in cells:
	k = HEIGHT / im.height
	scaled.append((label, im.resize((int(im.width * k), HEIGHT), Image.LANCZOS)))
sheet = Image.new("RGB", (sum(i.width for _, i in scaled) + 8 * (len(scaled) + 1), HEIGHT + 40), (20, 22, 26))
d = ImageDraw.Draw(sheet)
x = 8
for label, im in scaled:
	sheet.paste(im, (x, 32))
	d.text((x + 4, 10), label, fill=(235, 235, 225))
	x += im.width + 8
path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "views", f"compare_{tag}.jpg")
sheet.save(path, quality=88)
print(path, sheet.size)
