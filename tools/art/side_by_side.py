"""Reference and a pass side by side (or stacked with --stack), for a quick look.

  python tools/art/side_by_side.py <pass dir> [--ref art/look/ashen_ref/frame.png] [--stack] [--crop x0,y0,x1,y1]
"""

import os
import sys

from PIL import Image


def main():
	a = sys.argv[1:]
	d = a[0]
	ref = a[a.index("--ref") + 1] if "--ref" in a else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(d))), "frame.png")
	R = Image.open(ref).convert("RGB")
	O = Image.open(os.path.join(d, "final.png")).convert("RGB").resize(R.size)
	if "--crop" in a:
		box = tuple(int(v) for v in a[a.index("--crop") + 1].split(","))
		R, O = R.crop(box), O.crop(box)
	w, h = R.size
	if "--stack" in a:
		S = Image.new("RGB", (w, h * 2 + 6), (0, 0, 0))
		S.paste(R, (0, 0))
		S.paste(O, (0, h + 6))
	else:
		S = Image.new("RGB", (w * 2 + 6, h), (0, 0, 0))
		S.paste(R, (0, 0))
		S.paste(O, (w + 6, 0))
	S.save(os.path.join(d, "side.jpg"), quality=90)


if __name__ == "__main__":
	main()
