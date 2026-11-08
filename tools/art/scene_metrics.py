"""Numbers for "why does our landscape feel off next to good games" (docs/style/landscape-review.md): the same measures
over sets of frames (our renders, reference gameplay frames in the gitignored research/), one row per set.

  python tools/art/scene_metrics.py <out.md> <name>=<folder or file glob> [<name>=...] [--pick <name>=<list.txt>]

Per frame, averaged per set (the lower 60% of the frame is "land": ground, props, near mountains):
  L p5/p50/p95       value range (CIELAB L): squeezed = flat, lifted darks = washed out
  dark C / light C   mean chroma of the darkest and lightest fifth of the land: games keep shadows coloured
  hue variety        entropy of the land's hue histogram (18 bins, pixels with chroma > 12), in bits: one green = low
  macro patches      std of L after a blur of 4% of the width over the land: big light/dark masses (cloud shadows,
                     clearings, patches); a flat carpet scores low
  fine/coarse        detail at 1 px over detail at 6 px (scale-normalised): > 1 busy small marks, < 1 big shapes
  edges near/mid/far share of strong-edge pixels in the bottom, middle and top thirds of the land
Frames come from tools/art/frame_study.py extract; footage stays private (only these numbers go in the repo).
"""

import glob
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def lab(rgb):
	c = rgb / 255.0
	c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
	x = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
	x = x / np.array([0.9505, 1.0, 1.089])
	f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
	return 116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])


def measures(path):
	im = Image.open(path).convert("RGB")
	im = im.resize((640, int(640 * im.height / im.width)))
	rgb = np.asarray(im, np.float64)
	L, a, b = lab(rgb)
	C = np.hypot(a, b)
	H = L.shape[0]
	land = slice(int(H * 0.4), H)
	Ll, Cl = L[land], C[land]
	p5, p50, p95 = np.percentile(Ll, (5, 50, 95))
	dark = Ll <= np.percentile(Ll, 20)
	light = Ll >= np.percentile(Ll, 80)
	hue = (np.degrees(np.arctan2(b[land], a[land])) + 360) % 360
	sel = Cl > 12
	if sel.sum() > 100:
		hist = np.bincount((hue[sel] / 20).astype(int) % 18, minlength=18).astype(float)
		pr = hist / hist.sum()
		ent = float(-(pr[pr > 0] * np.log2(pr[pr > 0])).sum())
	else:
		ent = 0.0
	macro = float(ndimage.gaussian_filter(Ll, 640 * 0.04).std())
	fine = np.abs(ndimage.laplace(ndimage.gaussian_filter(Ll, 1.0))).mean()
	coarse = (np.abs(ndimage.laplace(ndimage.gaussian_filter(Ll, 6.0))) * 36).mean()
	g = ndimage.gaussian_gradient_magnitude(Ll, 1.2)
	strong = g > 6.0
	h3 = Ll.shape[0] // 3
	edges = [float(strong[i * h3 : (i + 1) * h3].mean()) for i in (2, 1, 0)]  # near (bottom), mid, far (top of land)
	return [p5, p50, p95, float(Cl[dark].mean()), float(Cl[light].mean()), ent, macro, float(fine / max(coarse, 1e-6))] + edges


def main():
	a = sys.argv[1:]
	picks = {}
	while "--pick" in a:
		i = a.index("--pick")
		k, v = a[i + 1].split("=", 1)
		picks[k] = {ln.strip() for ln in open(v, encoding="utf-8") if ln.strip() and not ln.startswith("#")}
		a = a[:i] + a[i + 2 :]
	out, sets = a[0], a[1:]
	rows = []
	for spec in sets:
		name, where = spec.split("=", 1)
		files = sorted(glob.glob(os.path.join(where, "*.jpg")) + glob.glob(os.path.join(where, "*.png"))) if os.path.isdir(where) else sorted(glob.glob(where))
		if name in picks:
			files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in picks[name]]
		if not files:
			print("no frames for", name)
			continue
		m = np.mean([measures(f) for f in files], 0)
		rows.append((name, len(files), m))
		print(name, len(files), " ".join(f"{v:.2f}" for v in m))
	head = "| Set | Frames | L p5 / p50 / p95 | Dark C | Light C | Hue variety (bits) | Macro patches | Fine/coarse | Edges near / mid / far |"
	lines = [head, "|" + "---|" * 9]
	for name, n, m in rows:
		lines.append(f"| {name} | {n} | {m[0]:.0f} / {m[1]:.0f} / {m[2]:.0f} | {m[3]:.1f} | {m[4]:.1f} | {m[5]:.2f} | {m[6]:.1f} | {m[7]:.2f} | "
					 f"{m[8] * 100:.0f}% / {m[9] * 100:.0f}% / {m[10] * 100:.0f}% |")
	open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
	print("\n".join(lines))


if __name__ == "__main__":
	main()
