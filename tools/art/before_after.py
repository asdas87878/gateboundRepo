"""A before/after sheet: the same views from two passes side by side, one row per view (left = before, right = after).

  python tools/art/before_after.py <out.jpg> <before dir> <after dir> "<title>" <view> [<view> ...] [--width 800]

Each pass dir holds <view>/final.png (tools/art/look_post.py). Labels come from the folder names.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
	a = sys.argv[1:]
	width = a[a.index("--width") + 1] if "--width" in a else "800"
	if "--width" in a:
		i = a.index("--width")
		a = a[:i] + a[i + 2 :]
	out, before, after, title, views = a[0], a[1], a[2], a[3], a[4:]
	bn, an = os.path.basename(os.path.normpath(before)), os.path.basename(os.path.normpath(after))
	items = []
	for v in views:
		items += [f"{os.path.join(before, v, 'final.png')}={v}: {bn}", f"{os.path.join(after, v, 'final.png')}={v}: {an}"]
	subprocess.run([sys.executable, os.path.join(HERE, "contact_sheet.py"), out, "2", title] + items + ["--width", width], check=True)


if __name__ == "__main__":
	main()
