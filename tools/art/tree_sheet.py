"""Comparison sheets for the tree kit: renders beside crops of the lesson's reference (private, study only).
  python tools/art/tree_sheet.py art/kit/trees/test test
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

D = os.path.abspath(sys.argv[1])
MODE = sys.argv[2] if len(sys.argv) > 2 else "test"
REF = Image.open("research/stylized_lesson/ref_01.png").convert("RGB")
FONT = ImageFont.truetype("arial.ttf", 22)


def tile(path_or_img, h, label):
	im = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(os.path.join(D, path_or_img)).convert("RGB")
	im = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
	d = ImageDraw.Draw(im)
	d.rectangle((0, 0, d.textlength(label, font=FONT) + 14, 30), fill=(24, 30, 40))
	d.text((7, 3), label, font=FONT, fill=(240, 240, 230))
	return im


def rows(rs, out):
	gap = 8
	w = max(sum(i.width for i in r) + gap * (len(r) - 1) for r in rs)
	h = sum(r[0].height for r in rs) + gap * (len(rs) - 1)
	s = Image.new("RGB", (w, h), (30, 32, 36))
	y = 0
	for r in rs:
		x = 0
		for i in r:
			s.paste(i, (x, y))
			x += i.width + gap
		y += r[0].height + gap
	s.save(os.path.join(D, out), quality=92)


if MODE == "test":
	ra = REF.crop((430, 0, 720, 240))
	rb = REF.crop((1040, 90, 1333, 340))
	rows(
		[
			[tile("view_wide.png", 460, "A painted planes (left)  |  B no alpha, modelled feathers (right)"), tile(ra, 460, "reference")],
			[tile("view_walk_a.png", 400, "A player height"), tile("view_under_a.png", 400, "A under the crown"), tile("view_close_a.png", 400, "A up close"), tile(rb, 400, "reference")],
			[tile("view_walk_b.png", 400, "B player height"), tile("view_under_b.png", 400, "B under the crown"), tile("view_close_b.png", 400, "B up close")],
		],
		"test_sheet.jpg",
	)
