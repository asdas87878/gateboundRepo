"""Whole-frame look numbers outside the HUD mask (docs/look-passes.md): per horizontal band (sky, middle, ground) the
mean CIELAB lightness, its spread (contrast), mean chroma, and how much fine detail there is (mean gradient of L after a
small blur: busy grass and foliage score high, flat surfaces low).

  python tools/art/look_global.py <image> [<image> ...]
"""

import json
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
from look_compare import lab  # noqa: E402

AREAS = "art/look/ashen_ref/areas.json"
BANDS = {"top 0-200": (0, 200), "mid 200-420": (200, 420), "ground 420-752": (420, 752)}


def numbers(path, spec):
	im = Image.open(path).convert("RGB").resize(tuple(spec["Frame"]))
	L = lab(np.asarray(im, np.float64))
	Lb = lab(np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), np.float64))[..., 0]
	gy, gx = np.gradient(Lb)
	grad = np.hypot(gx, gy)
	mask = np.ones(L.shape[:2], bool)
	for x0, y0, x1, y1 in spec["Mask"]:
		mask[y0:y1, x0:x1] = False
	out = {}
	for name, (y0, y1) in BANDS.items():
		m = mask[y0:y1]
		l = L[y0:y1][..., 0][m]
		c = np.hypot(L[y0:y1][..., 1], L[y0:y1][..., 2])[m]
		out[name] = (l.mean(), l.std(), c.mean(), grad[y0:y1][m].mean())
	return out


def main():
	spec = json.load(open(AREAS, encoding="utf-8"))
	rows = {p: numbers(p, spec) for p in sys.argv[1:]}
	print(f"{'band':16s}" + "".join(f"{p[-28:]:>34s}" for p in rows))
	print(f"{'':16s}" + "".join(f"{'L   spread chroma detail':>34s}" for _ in rows))
	for band in BANDS:
		print(f"{band:16s}" + "".join(f"{v[band][0]:>13.1f}{v[band][1]:>7.1f}{v[band][2]:>7.1f}{v[band][3]:>7.2f}" for v in rows.values()))


if __name__ == "__main__":
	main()
