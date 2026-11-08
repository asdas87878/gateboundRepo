"""The watermill: a tall mill with a big wooden waterwheel on its side, fed by a flume on posts. Built on the house kit. The wheel's foot is meant to sit in a stream.
  python tools/art/mill_kit.py art/kit/mill
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/mill")
import house_base as B  # noqa: E402

K = B.K
B.setup("Mill")
HX, HZ = 8.6, 6.4
FOOT_Y = 2.2
F1 = B.DOOR_TOP + B.MARGIN + B.JETTY_H / 2
V1 = F1 + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW
F2 = V1 + B.WIN + B.FRAME_ABOVE + B.MARGIN + B.JETTY_H / 2
ROOF_X, EAVE_Z, EAVE_Y = HX + 1.1, HZ + 1.4, F2 + 0.1
RIDGE_Y = EAVE_Y + EAVE_Z * 1.15
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_Z
K.FOOT_Y = FOOT_Y
K.GRAD_Y = (2.5, RIDGE_Y - 3)
DU = -3.0
WHEEL_X, WHEEL_Y, WHEEL_Z, WHEEL_R, WHEEL_W = HX + 2.2, 5.6, -0.7, 6.2, 2.3
STONE = dict(xa=-HX, xb=HX, zb=-HZ, zf=HZ, foot=FOOT_Y, du=DU, dw=B.DOOR_W, chimneys=[[(-4.2, -2.0, 1.18, 1.38, RIDGE_Y - 6, RIDGE_Y + 2.2)]])


def warp(p):
	x, y, z = p
	if x > HX + 0.6:  # the wheel runs true
		return (x, y, z)
	yc = max(y, 0.0)
	wave = math.cos(min(abs(x) / (ROOF_X + 0.5), 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	return (x - 0.02 * yc, y - 0.6 * rise * wave - 0.2 * wave * min(max((abs(z) - HZ) / 1.5, 0), 1) + 0.012 * x * min(yc / 12, 1), z - 0.01 * yc)


K.warp = warp


def roof(u):
	return RIDGE_Y - abs(u) * SLOPE


def wheel():
	kw = dict(ch=0.06, hidden_back=False, rings=2, knots=0, bend=0.0)
	c = np.array((WHEEL_X, WHEEL_Y, WHEEL_Z))
	at = lambda r, a, side: c + np.array((side * WHEEL_W / 2, r * math.sin(a), r * math.cos(a)))
	n = 12
	for side in (1, -1):
		for i in range(n):
			a0, a1 = math.tau * i / n, math.tau * (i + 1) / n
			K.Beam(at(WHEEL_R, a0, side), at(WHEEL_R, a1, side), (side, 0, 0), 0.34, 0.5, **kw)
		for i in range(4):  # spokes right across, as one timber through the hub
			a = math.tau * (i + 0.5) / 8
			K.Beam(at(WHEEL_R - 0.1, a, side), at(WHEEL_R - 0.1, a + math.pi, side), (side, 0, 0), 0.3, 0.42, **kw)
	for i in range(n):  # the paddles, between the rims
		a = math.tau * (i + 0.5) / n
		K.Beam(at(WHEEL_R + 0.1, a, -1), at(WHEEL_R + 0.1, a, 1), (0, math.cos(a), -math.sin(a)), 0.2, 1.3, **kw)
	# the axle, from the wall through the hub, and a hub block
	K.Beam((HX - 0.1, WHEEL_Y, WHEEL_Z), (WHEEL_X + WHEEL_W / 2 + 0.5, WHEEL_Y, WHEEL_Z), (0, 0, 1), 0.7, 0.7, ch=0.12, hidden_back=False, rings=2, knots=0, unique=True, bend=0.0)
	K.Beam((WHEEL_X - WHEEL_W / 2 - 0.24, WHEEL_Y, WHEEL_Z), (WHEEL_X + WHEEL_W / 2 + 0.24, WHEEL_Y, WHEEL_Z), (0, 0, 1), 1.3, 1.3, ch=0.2, hidden_back=False, rings=2, knots=0, unique=True, bend=0.0)
	# the outer post carrying the axle
	K.Beam((WHEEL_X + WHEEL_W / 2 + 0.5, -1, WHEEL_Z - 0.5), (WHEEL_X + WHEEL_W / 2 + 0.5, WHEEL_Y - 0.3, WHEEL_Z - 0.5), (1, 0, 0), 0.7, 0.8, ch=0.08, hidden_back=False, rings=2, knots=1, unique=True, foot=True)
	K.Beam((WHEEL_X + WHEEL_W / 2 + 0.5, -1, WHEEL_Z + 0.5), (WHEEL_X + WHEEL_W / 2 + 0.5, WHEEL_Y - 0.3, WHEEL_Z + 0.5), (1, 0, 0), 0.7, 0.8, ch=0.08, hidden_back=False, rings=2, knots=1, unique=True, foot=True)
	# the flume: a trough on posts, coming in over the top from behind
	y = WHEEL_Y + WHEEL_R + 0.9
	z0, z1 = WHEEL_Z + 0.4, -HZ - 8.0
	for x in (WHEEL_X - 0.95, WHEEL_X + 0.95):
		K.Beam((x, y, z1), (x, y, z0), (1 if x > WHEEL_X else -1, 0, 0), 0.26, 0.95, ch=0.05, hidden_back=False, rings=3, knots=0, unique=x > WHEEL_X, bend=0.0)
	K.Beam((WHEEL_X, y - 0.5, z1), (WHEEL_X, y - 0.5, z0), (1, 0, 0), 2.1, 0.26, ch=0.05, hidden_back=False, rings=3, knots=0, unique=True, bend=0.0)
	for z in (-HZ - 1.2, -HZ - 6.8):
		for x in (WHEEL_X - 1.0, WHEEL_X + 1.0):
			K.Beam((x, -1, z), (x, y - 0.5, z), (0, 0, 1), 0.5, 0.56, ch=0.07, hidden_back=False, rings=2, knots=0, foot=True)
		K.Beam((WHEEL_X - 1.25, y - 0.72, z), (WHEEL_X + 1.25, y - 0.72, z), (0, 0, 1), 0.46, 0.5, ch=0.07, hidden_back=False, rings=2, knots=0)


def build():
	v0 = FOOT_Y - 0.5
	clear = (F1 - B.JETTY_H / 2) - FOOT_Y - (B.WIN + B.FRAME_ABOVE + B.SILL_BELOW)
	win0 = FOOT_Y + clear / 2 + B.SILL_BELOW
	top = roof(HZ)
	f = K.Face("front", (0, 0, HZ), (1, 0, 0), (0, 0, 1))
	f.beam((-HX - 0.3, F1 + 0.05), (HX + 0.3, F1 - 0.05), w=0.7, h=B.JETTY_H, unique=True, knots=1, d=0.14)
	f.beam((-HX - 0.3, F2 - 0.04), (HX + 0.3, F2 + 0.04), w=0.66, h=B.JETTY_H, unique=True, d=0.2)
	for u in (-HX + 0.1, HX - 0.1):
		f.beam((u, FOOT_Y), (u, F2), w=B.POST_DEPTH, h=B.POST, unique=True, d=0.2)
	B.door_set(f, DU)
	K.window(f, 3.6, win0, B.WIN, B.WIN, shutters=False)
	K.window(f, -3.6, V1, B.WIN, B.WIN)
	K.window(f, 3.8, V1, B.WIN, B.WIN, shutters=False)
	K.wall(f, -HX, HX, v0, lambda u: top, shade_y=F2, shadow_depth=0.8, cols=6, rows=5)
	b = K.Face("back", (0, 0, -HZ), (-1, 0, 0), (0, 0, -1))
	b.beam((-HX - 0.3, F1), (HX + 0.3, F1 + 0.05), w=0.7, h=B.JETTY_H, d=0.14)
	b.beam((-HX - 0.3, F2), (HX + 0.3, F2 - 0.04), w=0.66, h=B.JETTY_H, d=0.2)
	for u in (-HX + 0.1, HX - 0.1):
		b.beam((u, FOOT_Y), (u, F2), h=B.POST, w=B.POST_DEPTH, d=0.18)
	K.window(b, -3.5, win0, B.WIN, B.WIN, shutters=False)
	K.window(b, 3.5, V1, B.WIN, B.WIN, shutters=False)
	K.wall(b, -HX, HX, v0, lambda u: top, shade_y=F2, shadow_depth=0.8, cols=6, rows=5)
	for sign in (1, -1):
		s = B.side(sign, HX)
		s.beam((-HZ - 0.1, F1), (HZ + 0.1, F1 + 0.04), w=0.7, h=B.JETTY_H, d=0.1)
		s.beam((-HZ - 0.1, F2), (HZ + 0.1, F2 - 0.04), w=0.66, h=B.JETTY_H, d=0.1)
		for u in (-HZ + 0.15, HZ - 0.15):
			s.beam((u, FOOT_Y), (u, F2), h=B.POST, w=B.POST_DEPTH, d=0.18)
		if sign < 0:
			K.window(s, 0.0, win0, B.WIN, B.WIN, shutters=False)
		K.window(s, 0.0 if sign < 0 else -3.0, V1, B.WIN, B.WIN, shutters=False)
		K.window(s, 0.0, F2 + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW, B.WIN, B.WIN, shutters=False)
		K.wall(s, -HZ, HZ, v0, roof, cols=6, rows=6, shadow_depth=0.7)
	K.tiled((-ROOF_X, RIDGE_Y, 0), (ROOF_X, RIDGE_Y, 0), (-ROOF_X, EAVE_Y, EAVE_Z), 8, (0, 1, 1), moss=0, sun=(0.3, 0.45), nx=10)
	K.tiled((ROOF_X, RIDGE_Y, 0), (-ROOF_X, RIDGE_Y, 0), (ROOF_X, EAVE_Y, -EAVE_Z), 8, (0, 1, -1), moss=0.45, mossy_end=1, nx=10)
	K.Beam((-ROOF_X - 0.25, RIDGE_Y + 0.14, 0), (ROOF_X + 0.25, RIDGE_Y + 0.14, 0), (0, 0, 1), 1.15, 0.5, ch=0.14, scheme_name="Clay", knots=0, rings=8, bend=0.02, hidden_back=False, unique=True)
	for x, sign in ((ROOF_X, 1), (-ROOF_X, -1)):
		for zs in (1, -1):
			K.Beam((x, RIDGE_Y + 0.05, 0), (x, EAVE_Y - 0.2, zs * (EAVE_Z + 0.22)), (sign, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, unique=sign > 0, knots=1, rings=5, hero=True)
	cx, cz, _, _, _, ctop = STONE["chimneys"][0][-1]
	B.chimney(cx, cz, 0, ctop)
	wheel()


if __name__ == "__main__":
	K.main(build)
