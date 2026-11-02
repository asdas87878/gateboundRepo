"""sRGB hex <-> CIELAB, and nudging a colour by Lab amounts (docs/look-passes.md: palette tuning).

  python tools/art/colour_tool.py lab <hex>                 -> L a b
  python tools/art/colour_tool.py nudge <hex> <dL> <da> <db> -> new hex
  python tools/art/colour_tool.py chroma <hex> <factor>     -> hex with a, b scaled (factor < 1 = greyer)
"""

import sys

import numpy as np

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def hex_to_lab(h):
	c = np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)])
	c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
	x = (M @ c) / WHITE
	f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
	return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def lab_to_hex(lab):
	L, a, b = lab
	fy = (L + 16) / 116
	fx, fz = fy + a / 500, fy - b / 200
	inv = lambda t: t**3 if t**3 > 0.008856 else (t - 16 / 116) / 7.787
	x = np.array([inv(fx), inv(fy), inv(fz)]) * WHITE
	lin = np.linalg.solve(M, x)
	s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
	return "".join(f"{int(round(float(np.clip(v, 0, 1)) * 255)):02x}" for v in s)


def nudge(h, dL=0.0, da=0.0, db=0.0):
	return lab_to_hex(hex_to_lab(h) + np.array([dL, da, db]))


def chroma(h, k):
	L, a, b = hex_to_lab(h)
	return lab_to_hex((L, a * k, b * k))


if __name__ == "__main__":
	cmd, h = sys.argv[1], sys.argv[2]
	if cmd == "lab":
		print(" ".join(f"{v:.1f}" for v in hex_to_lab(h)))
	elif cmd == "nudge":
		print(nudge(h, *(float(v) for v in sys.argv[3:6])))
	elif cmd == "chroma":
		print(chroma(h, float(sys.argv[3])))
