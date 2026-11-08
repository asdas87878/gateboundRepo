"""The tattered house: an abandoned prop. A hole in the roof with bare rafters, boarded windows, bare lath patches, a timber propping one wall, a broken chimney, a strong lean. Greyed in tools/art/house_looks.py.
  python tools/art/tattered_kit.py art/kit/tattered
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/tattered")
import house_base as B  # noqa: E402

K = B.K
B.setup("Tattered")
HX, HZ = 9.6, 6.2
F1, F2 = B.F1, B.F1 + B.FLOOR
K.FOOT_Y = B.FOOT
K.GRAD_Y = (2.5, 24)
K.warp = B.make_warp(-HX - 1.2, HX + 1.2, lean=0.045, sag=1.5, lean_z=-0.02)
warp = K.warp
STONE = dict(xa=-HX, xb=HX, zb=-HZ, zf=HZ, foot=B.FOOT, du=-3.6, chimneys=[[(5.2, -2.0, 1.2, 1.4, 19.0, 26.3)]])


def paint_dark(r):
	return np.ones((r.h * K.SS, r.w * K.SS, 3)) * np.array((40, 32, 44), float)


def board(face, cu, v):
	"""planks nailed over a window: uneven, not quite level"""
	w, h = B.WIN, B.WIN
	for dy, tilt, d in ((0.62, 0.22, 0.42), (1.45, -0.16, 0.46), (2.15, 0.12, 0.42)):
		face.beam((cu - w / 2 - 0.42, v + dy - tilt), (cu + w / 2 + 0.42, v + dy + tilt), w=0.2, h=0.62, d=d, knots=1, nails=((0.06, 0.5), (0.94, 0.5)))


def build():
	info = B.block(0, 0, HX, HZ, [F1, F2], ridge="x", pitch=1.05, has_roof=False, door_u=-3.6,
		windows={"front": [(4.1, B.WIN0, False), (-4.1, B.above(F1), False), (4.1, B.above(F1), False)], "back": [(-4.5, B.WIN0, False), (4.5, B.above(F1), False)], "left": [(0, B.WIN0, False), (0, B.above(F2), False)], "right": [(0, B.above(F1), False)]})
	front, back, right = info["faces"]["front"], info["faces"]["back"], info["faces"]["right"]
	board(front, 4.1, B.WIN0)
	board(front, -4.1, B.above(F1))
	board(back, 4.5, B.above(F1))
	board(right, 0, B.above(F1))
	# plaster fallen away, the laths showing
	front.patches = [(-0.6, F2 - 2.2, 1.9, 0.95)]
	back.patches = [(0.0, 12.5, 2.0, 1.0)]
	right.patches = [(-3.3, 5.0, 1.3, 1.2)]
	# a plank across the door
	front.beam((-3.6 - 2.3, 2.7), (-3.6 + 2.3, 4.1), w=0.22, h=0.66, d=0.52, knots=0, nails=((0.08, 0.5), (0.92, 0.5)))
	# a timber propping the leaning wall
	K.Beam((HX + 5.0, -0.5, -1.5), (HX + 0.4, F1 + 0.3, -1.5), (0, 0, 1), 0.64, 0.7, ch=0.09, hidden_back=False, rings=3, knots=1, unique=True)
	# ---- the roof: whole on the back, broken open on the front
	X, EZ = HX + 1.1, HZ + 1.4
	R, E = info["ridge_y"], info["eave_y"]
	pt = lambda x, f: (x, R + (E - R) * f, EZ * f)
	tile = dict(lift=0.3, moss=0.3)
	K.tiled((X, R, 0), (-X, R, 0), (X, E, -EZ), 8, (0, 1, -1), nx=10, mossy_end=1, **tile)
	hole0, hole1 = -1.8, 5.6
	K.tiled(pt(-X, 0), pt(hole0, 0), pt(-X, 1), 8, (0, 1, 1), nx=5, mossy_end=-1, **tile)
	K.tiled(pt(hole1, 0), pt(X, 0), pt(hole1, 1), 8, (0, 1, 1), nx=3, mossy_end=1, **tile)
	K.tiled(pt(hole0, 0), pt(hole1, 0), pt(hole0, 0.2), 2, (0, 1, 1), nx=4, moss=0.3)
	K.tiled(pt(hole0 - 0.5, 0.72), pt(hole1 + 0.5, 0.72), pt(hole0 - 0.5, 1), 3, (0, 1, 1), nx=4, moss=0.3)
	# inside the hole: dark, with bare rafters and two laths across
	rect = K.JOIN.add((0.4, 0.4), paint_dark)
	under = [pt(hole0 - 0.7, 0.8), pt(hole1 + 0.7, 0.8), pt(hole1 + 0.7, 0.13), pt(hole0 - 0.7, 0.13)]
	under = [(p[0], p[1] - 0.26, p[2]) for p in under]
	K.emit.append(lambda: K.plate(under, rect, (0, 1, 1), 0.04))
	for x in (-0.6, 1.2, 3.0, 4.6):
		K.Beam(pt(x, 0.1), pt(x, 0.82), (1, 0, 0), 0.34, 0.42, ch=0.07, hidden_back=False, rings=3, knots=0)
	for f, x0, x1 in ((0.38, hole0 - 0.2, 2.4), (0.58, 0.2, hole1 + 0.2)):
		K.Beam(pt(x0, f), pt(x1, f), (0, 0.7, 0.7), 0.14, 0.42, ch=0.04, hidden_back=False, rings=2, knots=0)
	# the ridge, a length of it gone; barge boards on one end only, the other end's left bare
	K.Beam((-X - 0.25, R + 0.14, 0), (-0.6, R + 0.14, 0), (0, 0, 1), 1.15, 0.5, ch=0.14, scheme_name="Clay", knots=0, rings=4, bend=0.03, hidden_back=False, unique=True)
	K.Beam((3.4, R + 0.14, 0), (X + 0.25, R + 0.14, 0), (0, 0, 1), 1.15, 0.5, ch=0.14, scheme_name="Clay", knots=0, rings=3, bend=0.03, hidden_back=False, unique=True, )
	for zs in (1, -1):
		K.Beam((-X, R + 0.05, 0), (-X, E - 0.2, zs * (EZ + 0.22)), (-1, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, knots=1, rings=4)
	K.Beam((X, R + 0.05, 0), (X, E + 2.2, -(EZ - 2.2)), (1, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, knots=1, rings=3)


if __name__ == "__main__":
	K.main(build)
