"""Review sheet: the cottage's views beside the lesson's timber house and the approved fence.
The sheet holds a private reference frame, so it is written to the gitignored research/ folder.

  python tools/art/cottage_sheet.py art/kit/cottage research/cottage/compare.jpg
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

KIT = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
font = ImageFont.truetype("arial.ttf", 22)
CELL_H = 560
GAP = 10


def cell(img, label, w, h=CELL_H):
	"""fit by cropping to the cell's shape, never stretching"""
	sw, sh = img.size
	scale = max(w / sw, h / sh)
	r = img.resize((round(sw * scale), round(sh * scale)), Image.LANCZOS)
	x, y = (r.width - w) // 2, (r.height - h) // 2
	r = r.crop((x, y, x + w, y + h)).convert("RGB")
	d = ImageDraw.Draw(r)
	box = d.textbbox((12, 8), label, font=font)
	d.rectangle((box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4), fill=(32, 30, 40))
	d.text((12, 8), label, font=font, fill=(240, 234, 220))
	return r


view = lambda n: Image.open(os.path.join(KIT, "views", n + ".png"))
ref = Image.open(os.path.join(ROOT, "research", "stylized_lesson", "ref_01.png"))
rows = [
	[(ref.crop((630, 195, 745, 330)), "Reference: the lesson's timber house (tiny in its frame, upscaled)", 620), (view("front"), "Cottage, front", 620), (view("back"), "Back", 620)],
	[(view("gable"), "Gable end", 620), (view("above"), "From above", 620), (view("straight"), "Front, straight on", 620)],
	[(view("walk"), "Walk view: player's camera, FOV 70", 1000), (view("door"), "Door, close", 425), (Image.open(os.path.join(ROOT, "art", "kit", "props", "renders", "close_stack.png")), "The small props", 425)],
]
W = 620 * 3 + GAP * 2
sheet = Image.new("RGB", (W, (CELL_H + GAP) * len(rows) - GAP), (24, 24, 30))
y = 0
for row in rows:
	x = 0
	for img, label, w in row:
		sheet.paste(cell(img, label, w), (x, y))
		x += w + GAP
	y += CELL_H + GAP
sheet.save(OUT, quality=92)
print(OUT, sheet.size)
