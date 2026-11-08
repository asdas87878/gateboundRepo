"""The inn: the biggest house in town. Two storeys, the upper one jetting out at the front, a front gable over a double door, a hanging sign with a picture, two chimneys. Built on the house kit.
  python tools/art/inn_kit.py art/kit/inn
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/inn")
import house_base as B  # noqa: E402

K = B.K
B.setup("Inn")
HX, HZ = 14.0, 7.5
Z_UP = HZ + 1.1  # the upper floor's front
FOOT_Y = 2.2
DOOR_W = 4.6
F1 = B.DOOR_TOP + B.MARGIN + B.JETTY_H / 2
V1 = F1 + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW
F2 = V1 + B.WIN + B.FRAME_ABOVE + B.MARGIN + B.JETTY_H / 2
ROOF_X, EAVE_Z, EAVE_Y = HX + 1.15, Z_UP + 1.3, F2 + 0.1
RIDGE_Y = EAVE_Y + EAVE_Z * 1.0
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_Z
K.FOOT_Y = FOOT_Y
K.GRAD_Y = (2.5, RIDGE_Y - 4)
if os.environ.get("HOUSE_RIM") == "1":
	K.RIM = dict(hx=HX, z0=-HZ, z1=Z_UP)
STONE = dict(xa=-HX, xb=HX, zb=-HZ, zf=HZ, foot=FOOT_Y, du=0.0, dw=DOOR_W, chimneys=[[(-8.5, -1.6, 1.25, 1.45, RIDGE_Y - 7, RIDGE_Y + 2.6)], [(9.0, -1.8, 1.18, 1.38, RIDGE_Y - 7, RIDGE_Y + 2.1)]])


def warp(p):
	x, y, z = p
	yc = max(y, 0.0)
	wave = math.cos(min(abs(x) / (ROOF_X + 0.5), 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	return (x + 0.016 * yc, y - 0.8 * rise * wave - 0.24 * wave * min(max((abs(z) - HZ) / 1.6, 0), 1) + 0.012 * x * min(yc / 12, 1), z - 0.01 * yc)


K.warp = warp


def roof(u):
	return RIDGE_Y - abs(u) * SLOPE


def paint_sign(r):
	"""a tankard on a board: a picture, no words"""
	img = K.planks(r.w, r.h, 3, "Chestnut", K.child())
	H, W = img.shape[:2]
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	u, v = xx / W, yy / H
	body = (np.abs(u - 0.46) < 0.2) & (v > 0.32) & (v < 0.8)
	foam = ((u - 0.46) / 0.25) ** 2 + ((v - 0.28) / 0.1) ** 2 < 1
	handle = (np.hypot((u - 0.68) / 0.11, (v - 0.55) / 0.15) < 1) & (np.hypot((u - 0.68) / 0.055, (v - 0.55) / 0.08) > 1) & (u > 0.66)
	board = np.array((60, 58, 80), float)
	img = K.over(img, board, K.gaussian_filter(((np.abs(u - 0.5) < 0.42) & (np.abs(v - 0.5) < 0.38)).astype(np.float32), 1.2) * 0.8)
	img = K.over(img, np.array((206, 150, 74), float), K.gaussian_filter((body | handle).astype(np.float32), 1.0))
	img = K.over(img, np.array((242, 232, 208), float), K.gaussian_filter(foam.astype(np.float32), 1.0))
	return np.clip(img, 0, 255)


def build():
	v0 = FOOT_Y - 0.5
	clear = (F1 - B.JETTY_H / 2) - FOOT_Y - (B.WIN + B.FRAME_ABOVE + B.SILL_BELOW)
	win0 = FOOT_Y + clear / 2 + B.SILL_BELOW
	# ---- ground floor
	f = K.Face("front0", (0, 0, HZ), (1, 0, 0), (0, 0, 1))
	for u in (-HX + 0.1, HX - 0.1):
		f.beam((u, FOOT_Y), (u, F1), w=B.POST_DEPTH, h=B.POST, unique=True, d=0.2)
	for s in (-1, 1):
		f.beam((s * (DOOR_W / 2 + 0.42), -0.5), (s * (DOOR_W / 2 + 0.4), B.DOOR_V0 + B.DOOR_H + 0.72), w=0.72, h=0.7, unique=True, foot=True, d=0.22, hero=s < 0)
	f.beam((-DOOR_W / 2 - 0.72, B.DOOR_V0 + B.DOOR_H + 0.5), (DOOR_W / 2 + 0.76, B.DOOR_V0 + B.DOOR_H + 0.42), w=0.84, h=0.74, unique=True, d=0.3, hero=True)
	K.door(f, 0.0, DOOR_W, B.DOOR_V0, B.DOOR_H)
	K.window(f, -8.9, win0, B.WIN, B.WIN)
	K.window(f, 8.9, win0, B.WIN, B.WIN)
	for u in (-HX + 0.9, HX - 0.9):
		B.bracket(f, u, F1, Z_UP - HZ + 0.1)
	K.wall(f, -HX, HX, v0, lambda u: F1 + 0.1, shade_y=F1, shadow_depth=1.0, cols=8, rows=3)
	# ---- upper floor, jetting out, three windows
	u_ = K.Face("front1", (0, 0, Z_UP), (1, 0, 0), (0, 0, 1))
	u_.beam((-HX - 0.3, F1), (HX + 0.3, F1 + 0.06), w=1.6, h=0.95, d=-0.6, unique=True, knots=1)
	u_.beam((-HX - 0.3, F2), (HX + 0.3, F2 - 0.05), w=0.9, h=B.JETTY_H, d=0.1, unique=True, knots=1)
	for u in (-HX + 0.1, HX - 0.1):
		u_.beam((u, F1), (u, F2), w=B.POST_DEPTH, h=B.POST, unique=True, d=0.2)
	K.window(u_, -8.9, V1, B.WIN, B.WIN)
	K.window(u_, 0.0, V1, B.WIN, B.WIN, shutters=False)
	K.window(u_, 8.9, V1, B.WIN, B.WIN)
	K.wall(u_, -HX, HX, F1 - 0.2, lambda u: F2 + 0.2, shade_y=F2, shadow_depth=0.8, cols=8, rows=3)
	# ---- the front gable, flush with the upper floor
	gw, gpeak = 6.0, F2 + 7.0
	g = K.Face("gablefront", (0, 0, Z_UP), (1, 0, 0), (0, 0, 1))
	line = lambda u: gpeak - abs(u) * (gpeak - F2 - 0.3) / gw
	g.window = None
	K.window(g, 0.0, F2 + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW, B.WIN, B.WIN, shutters=False)
	K.wall(g, -gw, gw, F2 + 0.1, line, cols=6, rows=4, shadow_depth=0.7)
	z_back = max((RIDGE_Y - gpeak) / SLOPE, 0.5)
	front = Z_UP + 1.0
	for s in (1, -1):
		a, b_ = ((0, gpeak + 0.05, z_back), (0, gpeak + 0.05, front)) if s > 0 else ((0, gpeak + 0.05, front), (0, gpeak + 0.05, z_back))
		K.tiled(a, b_, (s * (gw + 1.0), F2 - 0.5, a[2]), 6, (s, 1, 0), lift=0.26, nx=6, moss=0.0)
		K.Beam((0, gpeak + 0.03, front + 0.06), (s * (gw + 1.05), F2 - 0.65, front + 0.06), (0, 0, 1), 0.34, 0.84, ch=0.07, hidden_back=False, rings=4, knots=1, unique=True, hero=s < 0)
	K.Beam((0, gpeak + 0.16, front + 0.14), (0, gpeak + 0.1, z_back), (1, 0, 0), 1.0, 0.44, ch=0.12, scheme_name="Clay", knots=0, rings=4, hidden_back=False, bend=0.015, unique=True)
	# ---- back: two storeys on one plane
	b = K.Face("back", (0, 0, -HZ), (-1, 0, 0), (0, 0, -1))
	b.beam((-HX - 0.3, F1), (HX + 0.3, F1 + 0.05), w=0.72, h=B.JETTY_H, d=0.1)
	b.beam((-HX - 0.3, F2), (HX + 0.3, F2 - 0.05), w=0.72, h=B.JETTY_H, d=0.1)
	for u in (-HX + 0.1, HX - 0.1):
		b.beam((u, FOOT_Y), (u, F2), h=B.POST, w=B.POST_DEPTH, d=0.18)
	for u, y in ((-7.0, win0), (6.0, win0), (-3.5, V1), (9.0, V1)):
		K.window(b, u, y, B.WIN, B.WIN, shutters=False)
	K.wall(b, -HX, HX, v0, lambda u: roof(HZ), cols=8, rows=5, shadow_depth=0.8)
	# ---- sides
	for sign in (1, -1):
		s = B.side(sign, HX)
		a, c = sorted((-sign * -HZ, -sign * Z_UP))
		s.beam((a - 0.1, F1), (c + 0.1, F1 + 0.04), w=0.72, h=B.JETTY_H, d=0.05)
		s.beam((a - 0.1, F2), (c + 0.1, F2 - 0.04), w=0.72, h=B.JETTY_H, d=0.05)
		for z in (-HZ + 0.15, HZ - 0.15):
			s.beam((-sign * z, FOOT_Y), (-sign * z, F1), h=B.POST, w=B.POST_DEPTH, d=0.18)
		K.window(s, -sign * -2.2, win0, B.WIN, B.WIN, shutters=sign > 0)
		K.window(s, -sign * 0.6, V1, B.WIN, B.WIN, shutters=False)
		K.window(s, 0.0, F2 + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW, B.WIN, B.WIN, shutters=False)
		if K.RIM:  # the lower floor stops at its own front, so no plaster hangs past the corner post as a thin fin. Only in the test so far
			K.wall(s, -HZ, HZ, v0, lambda u: F1 + 0.1, shade_y=F1, shadow_depth=0.8, cols=6, rows=3)
			_keep = K.rng.bit_generator.state  # this extra wall mustn't use up a draw, or every later timber and roof moves
			K.wall(s, a, c, F1 - 0.2, lambda u: roof(u), cols=6, rows=4, shadow_depth=0.8)
			K.rng.bit_generator.state = _keep
		else:
			K.wall(s, a, c, v0, lambda u: roof(u), cols=6, rows=6, shadow_depth=0.8)
	# ---- the sign, on an arm from the corner post's top
	sx = 4.45
	K.Beam((sx, F1 - 1.2, HZ + 0.2), (sx, F1 - 1.2, HZ + 3.8), (1, 0, 0), 0.34, 0.42, ch=0.07, hidden_back=False, rings=2, knots=0, unique=True)
	rect = K.JOIN.add((3.0, 2.3), paint_sign)
	corners = [(sx, F1 - 4.0, HZ + 3.5), (sx, F1 - 4.0, HZ + 0.7), (sx, F1 - 1.7, HZ + 0.7), (sx, F1 - 1.7, HZ + 3.5)]
	K.emit.append(lambda: K.plate(corners, rect, (1, 0, 0), 0.16))
	for z in (HZ + 1.0, HZ + 3.2):
		K.Beam((sx, F1 - 1.75, z), (sx, F1 - 1.25, z), (1, 0, 0), 0.14, 0.14, ch=0.03, hidden_back=False, rings=2, knots=0)
	# ---- roof
	K.tiled((-ROOF_X, RIDGE_Y, 0), (ROOF_X, RIDGE_Y, 0), (-ROOF_X, EAVE_Y, EAVE_Z), 9, (0, 1, 1), moss=0, sun=(0.2, 0.45), nx=14)
	K.tiled((ROOF_X, RIDGE_Y, 0), (-ROOF_X, RIDGE_Y, 0), (ROOF_X, EAVE_Y, -EAVE_Z), 9, (0, 1, -1), moss=0.35, mossy_end=1, nx=14)
	K.Beam((-ROOF_X - 0.25, RIDGE_Y + 0.14, 0), (ROOF_X + 0.25, RIDGE_Y + 0.14, 0), (0, 0, 1), 1.2, 0.52, ch=0.14, scheme_name="Clay", knots=0, rings=12, bend=0.02, hidden_back=False, unique=True)
	for x, sign in ((ROOF_X, 1), (-ROOF_X, -1)):
		for zs in (1, -1):
			K.Beam((x, RIDGE_Y + 0.05, 0), (x, EAVE_Y - 0.2, zs * (EAVE_Z + 0.22)), (sign, 0, 0), 0.36, 0.9, ch=0.07, hidden_back=False, unique=sign > 0, knots=1, rings=5, hero=True)
	for ch in STONE["chimneys"]:
		cx, cz, _, _, _, top = ch[-1]
		B.chimney(cx, cz, 0, top)


if __name__ == "__main__":
	K.main(build)
