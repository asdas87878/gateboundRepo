"""Labelled grid of images.

  python tools/art/contact_sheet.py <out.jpg> <columns> "<title>" <image>=<label> [<image>=<label> ...] [--width 800]
"""

import sys

from PIL import Image, ImageDraw, ImageFont


def main():
	a = sys.argv[1:]
	width = int(a[a.index("--width") + 1]) if "--width" in a else 800
	if "--width" in a:
		i = a.index("--width")
		a = a[:i] + a[i + 2 :]
	out, cols, title = a[0], int(a[1]), a[2]
	items = [x.split("=", 1) for x in a[3:]]
	ims = [Image.open(p).convert("RGB") for p, _ in items]
	h = int(width * ims[0].size[1] / ims[0].size[0])
	rows = (len(ims) + cols - 1) // cols
	top = 44
	S = Image.new("RGB", (cols * width + (cols - 1) * 6, top + rows * (h + 6)), (18, 18, 22))
	d = ImageDraw.Draw(S)
	fb, f = ImageFont.truetype("arialbd.ttf", 24), ImageFont.truetype("arialbd.ttf", 20)
	d.text((10, 8), title, font=fb, fill="white")
	for k, (im, (_, label)) in enumerate(zip(ims, items)):
		x, y = (k % cols) * (width + 6), top + (k // cols) * (h + 6)
		S.paste(im.resize((width, h), Image.LANCZOS), (x, y))
		b = d.textbbox((x + 10, y + 8), label, font=f)
		d.rectangle((b[0] - 6, b[1] - 4, b[2] + 6, b[3] + 4), fill=(20, 20, 24))
		d.text((x + 10, y + 8), label, font=f, fill="white")
	S.save(out, quality=90)


if __name__ == "__main__":
	main()
