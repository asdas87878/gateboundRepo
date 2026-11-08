"""Review sheet: the townhouse's views beside its concept.
  python tools/art/townhouse_sheet.py art/kit/townhouse research/townhouse/compare.jpg
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

KIT = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
font = ImageFont.truetype("arial.ttf", 22)
H = 780
GAP = 10


def cell(img, label, w, h=H, fit=False):
	sw, sh = img.size
	scale = min(w / sw, h / sh) if fit else max(w / sw, h / sh)
	r = img.convert("RGB").resize((round(sw * scale), round(sh * scale)), Image.LANCZOS)
	out = Image.new("RGB", (w, h), (246, 246, 244))
	if fit:
		out.paste(r, ((w - r.width) // 2, (h - r.height) // 2))
	else:
		x, y = (r.width - w) // 2, (r.height - h) // 2
		out.paste(r.crop((x, y, x + w, y + h)), (0, 0))
	d = ImageDraw.Draw(out)
	box = d.textbbox((12, 8), label, font=font)
	d.rectangle((box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4), fill=(32, 30, 40))
	d.text((12, 8), label, font=font, fill=(240, 234, 220))
	return out


view = lambda n: Image.open(os.path.join(KIT, "views", n + ".png"))
concept = Image.open(os.path.join(os.path.dirname(OUT), "concept.webp"))
rows = [
	[(concept, "Concept", 560, True), (view("three_quarter"), "Townhouse, 3/4", 560, False), (view("straight"), "Straight on", 560, False)],
	[(view("side"), "Side", 560, False), (view("back"), "Back", 560, False), (view("walk"), "Walk view, FOV 70", 560, False)],
]
W = 560 * 3 + GAP * 2
sheet = Image.new("RGB", (W, (H + GAP) * 2 + 600), (24, 24, 30))
y = 0
for row in rows:
	x = 0
	for img, label, w, fit in row:
		sheet.paste(cell(img, label, w, fit=fit), (x, y))
		x += w + GAP
	y += H + GAP
sheet.paste(cell(view("beside_cottage"), "Beside the cottage and a 5.2-stud player", W, 600), (0, y))
sheet.save(OUT, quality=92)
print(OUT, sheet.size)
