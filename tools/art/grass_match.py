"""How well the grass matches the ground (docs/style/grass.md): the same view rendered with grass and without (map.json
GrassStyles "none" keeps everything else), compared over the ground in front of the player. If grass takes the ground's
colour and light, adding it barely changes the ground area's average colour; dark grass pulls it down.

  python tools/art/grass_match.py <ground-only pass dir> <grass pass dir> [<grass pass dir> ...] --views a,b,c

Compares <dir>/<view>/final.png over the lower 45% of the frame minus the player stand-in's box in the middle. Prints
mean CIELAB L, a, b and the change from the ground-only render (dL: lighter/darker, dC: colour strength).
"""

import os
import sys

import numpy as np
from PIL import Image


def lab(rgb):
	c = rgb / 255.0
	c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
	x = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
	x = x / np.array([0.9505, 1.0, 1.089])
	f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
	return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def ground_lab(path):
	im = np.asarray(Image.open(path).convert("RGB"), np.float64)
	H, W = im.shape[:2]
	m = np.zeros((H, W), bool)
	m[int(H * 0.55) :, :] = True
	m[int(H * 0.5) :, int(W * 0.38) : int(W * 0.62)] = False  # the player stand-in
	return lab(im)[m].mean(0)


def main():
	a = sys.argv[1:]
	views = a[a.index("--views") + 1].split(",")
	dirs = [d for d in a[: a.index("--views")]]
	base, others = dirs[0], dirs[1:]
	print(f"{'view':16s} {'pass':12s}   L      a      b     dL     dC")
	for v in views:
		b0 = ground_lab(os.path.join(base, v, "final.png"))
		print(f"{v:16s} {os.path.basename(os.path.normpath(base)):12s} {b0[0]:5.1f} {b0[1]:6.1f} {b0[2]:6.1f}")
		for d in others:
			f = os.path.join(d, v, "final.png")
			if not os.path.exists(f):
				continue
			x = ground_lab(f)
			dC = np.hypot(x[1], x[2]) - np.hypot(b0[1], b0[2])
			print(f"{'':16s} {os.path.basename(os.path.normpath(d)):12s} {x[0]:5.1f} {x[1]:6.1f} {x[2]:6.1f} {x[0] - b0[0]:+5.1f} {dC:+5.1f}")


if __name__ == "__main__":
	main()
