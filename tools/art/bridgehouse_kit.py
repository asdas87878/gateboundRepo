"""The bridge house, after the user's concept: a timber upper floor on a stone arch a player walks through, a stair up the side to a door, a landing with a rail, terracotta and a dormer.
Built on the house kit (tools/art/house_base.py). The street runs along z, under the arch.
  python tools/art/bridgehouse_kit.py art/kit/bridgehouse
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/bridgehouse")
import house_base as B  # noqa: E402

K = B.K
B.setup("Bridgehouse")
K.TILE_ROUND = (0.04, 0.09)
K.TILE_WIDTH = (1.8, 2.7)
from bridgehouse_shape import BACK, LANDING_Z, PIER_W, R, RING, SPRING, STAIR_W, STEP_H, STEP_Z, STEPS, XO, Y0, ZS, Z_END  # noqa: E402

# the floor above: sized from the door
HX, HZ = XO + 0.4, ZS + 0.55
F = Y0 + B.DOOR_TOP + B.MARGIN + B.JETTY_H / 2
EAVE_Z, EAVE_Y = HZ + 1.45, F + 0.1
RIDGE_Y = EAVE_Y + EAVE_Z * 1.12
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_Z
ROOF_X = HX + 1.05
K.FOOT_Y = Y0
K.GRAD_Y = (Y0, RIDGE_Y - 2)


def warp(p):
	x, y, z = p
	high = min(max((y - Y0) / 8, 0), 1)  # the stone stands true, the timber above leans and sags
	wave = math.cos(min(abs(x) / (ROOF_X + 0.5), 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	return (x + 0.12 * high + 0.02 * max(y - Y0, 0), y - 0.7 * rise * wave - 0.22 * wave * min(max((abs(z) - HZ) / 1.4, 0), 1) + 0.012 * x * high, z - 0.015 * max(y - Y0, 0))


K.warp = warp


def roof(u):
	return RIDGE_Y - abs(u) * SLOPE


def stair():
	"""the stone is in tools/art/bridgehouse_stone.py, from the stone bridge's parts. Here, the wooden rail"""
	x1 = XO + STAIR_W
	n = STEPS
	h = Y0 / n
	back = BACK
	# the rail: posts on the outer edge, a sloped rail, and round the landing
	rail_x = x1 - 0.28
	post = dict(ch=0.07, hidden_back=False, rings=2, knots=0)
	tall = 3.1
	for i in (n - 1, n - 5, n - 9, n - 13):
		if i < 0:
			continue
		y, z = Y0 - i * h - h, LANDING_Z + i * STEP_Z + STEP_Z * 0.5
		K.Beam((rail_x, y + h, z), (rail_x, y + h + tall, z), (1, 0, 0), 0.5, 0.5, **post)
	yt = lambda i: Y0 - i * h + tall - 0.5
	zt = lambda i: LANDING_Z + i * STEP_Z + STEP_Z * 0.5
	K.Beam((rail_x, yt(n - 1), zt(n - 1)), (rail_x, yt(0), zt(0)), (1, 0, 0), 0.34, 0.38, ch=0.07, hidden_back=False, rings=4, knots=0, unique=True)
	for z in (-1.8, back + 0.3):
		K.Beam((rail_x, Y0, z), (rail_x, Y0 + tall, z), (1, 0, 0), 0.5, 0.5, **post)
	K.Beam((rail_x, Y0 + tall - 0.5, zt(0)), (rail_x, Y0 + tall - 0.5, back + 0.3), (1, 0, 0), 0.34, 0.38, ch=0.07, hidden_back=False, rings=2, knots=0)
	K.Beam((rail_x, Y0 + tall - 0.5, back + 0.3), (XO + 0.5, Y0 + tall - 0.5, back + 0.3), (0, 0, -1), 0.34, 0.38, ch=0.07, hidden_back=False, rings=2, knots=0)


def dormer():
	dx, dz = -0.8, 4.3
	dw2 = 2.5
	dv0 = roof(dz) - 0.7
	win_y = dv0 + 1.05
	dtop = win_y + B.WIN * 0.8 + 1.0
	dpeak = dtop + 1.5
	f = K.Face("dormer", (dx, 0, dz), (1, 0, 0), (0, 0, 1))
	line = lambda u: min(dtop + (dpeak - dtop) * (1 - abs(u) / dw2), dpeak)
	K.wall(f, -dw2, dw2, dv0, line, cols=4, rows=3)
	K.window(f, 0.0, win_y, B.WIN * 0.8, B.WIN * 0.8, shutters=False)
	for sign in (1, -1):
		f.beam((sign * (dw2 + 0.05), roof(dz) + 0.2), (sign * (dw2 - 0.05), dtop + 0.1), h=0.56, w=0.5, d=0.14)
	f.beam((-dw2 - 0.35, dtop), (dw2 + 0.35, dtop + 0.06), h=0.54, w=0.56, d=0.18)
	z_back = (RIDGE_Y - dpeak) / SLOPE
	for s in (1, -1):
		c = K.Face("cheek", (dx + s * dw2, 0, 0), (0, 0, -s), (s, 0, 0))
		if s > 0:
			K.wall(c, -dz, -z_back, dv0, lambda u: dtop, cols=2, rows=2)
		else:
			K.wall(c, z_back, dz, dv0, lambda u: dtop, cols=2, rows=2)
	front, over = dz + 0.85, 0.6
	sl = dtop - 0.3
	for s in (1, -1):
		a, b = ((dx, dpeak + 0.05, z_back), (dx, dpeak + 0.05, front)) if s > 0 else ((dx, dpeak + 0.05, front), (dx, dpeak + 0.05, z_back))
		K.tiled(a, b, (dx + s * (dw2 + over), sl, a[2]), 3, (s, 1, 0), lift=0.22, nx=4, moss=0.0)
		K.Beam((dx, dpeak + 0.03, front + 0.06), (dx + s * (dw2 + over + 0.04), sl - 0.12, front + 0.06), (0, 0, 1), 0.26, 0.5, ch=0.06, hidden_back=False, rings=2, knots=0)
	K.Beam((dx, dpeak + 0.18, front + 0.14), (dx, dpeak + 0.12, z_back), (1, 0, 0), 0.72, 0.36, ch=0.09, scheme_name="Clay", knots=0, rings=3, hidden_back=False, bend=0.015)


def build():
	v0 = Y0 - 0.2
	clear = (F - B.JETTY_H / 2) - (Y0 + B.JETTY_H / 2) - (B.WIN + B.FRAME_ABOVE + B.SILL_BELOW)
	win_y = Y0 + B.JETTY_H / 2 + clear / 2 + B.SILL_BELOW
	top = roof(HZ)
	stair()
	# ---- front and back: one post between two wide bays, short posts and braces down onto the stone
	for z, right, out, shutter in ((HZ, 1, 1, True), (-HZ, -1, -1, False)):
		f = K.Face("front" if out > 0 else "back", (0, 0, z), (right, 0, 0), (0, 0, out))
		f.beam((-HX - 0.3, Y0 + 0.04), (HX + 0.3, Y0 - 0.04), w=1.35, h=B.JETTY_H, d=-0.45, unique=out > 0, knots=1)
		f.beam((-HX - 0.3, F + 0.05), (HX + 0.3, F - 0.05), w=0.66, h=B.JETTY_H, d=0.2, unique=out > 0, knots=1)
		for u in (-HX + 0.1, HX - 0.1):
			f.beam((u, Y0), (u, F), w=B.POST_DEPTH, h=B.POST, unique=out > 0, d=0.2)
		f.beam((0.05, Y0), (-0.03, F), w=0.6, h=0.66, d=0.14, unique=out > 0)
		K.window(f, -HX / 2, win_y, B.WIN, B.WIN, shutters=shutter)
		K.window(f, HX / 2, win_y, B.WIN, B.WIN, shutters=shutter)
		K.wall(f, -HX, HX, v0, lambda u: top, shade_y=F, shadow_depth=0.8, cols=8, rows=3)
		# carried on the stone
		stone = K.Face("carry", (0, 0, out * (ZS + 0.05)), (right, 0, 0), (0, 0, out))
		for u in (-8.9, 8.9):
			stone.beam((u, SPRING - 0.02), (u, Y0 - 0.2), w=0.6, h=0.72, d=0.3, foot=False)
		for s in (-1, 1):
			stone.beam((s * 8.6, Y0 - 3.1), (s * 6.6, Y0 - 0.25), w=0.46, h=0.5, d=0.26)
	# ---- the door's gable, over the landing, and the plain one
	r = B.side(1, HX)
	door_u = 2.9  # z = -2.9
	dv = Y0 + B.DOOR_V0
	for u in (door_u - B.DOOR_W / 2 - 0.42, door_u + B.DOOR_W / 2 + 0.42):
		r.beam((u, Y0), (u + 0.02, dv + B.DOOR_H + 0.72), w=0.72, h=0.7, unique=True, d=0.22, hero=u < door_u)
	r.beam((door_u - B.DOOR_W / 2 - 0.72, dv + B.DOOR_H + 0.5), (door_u + B.DOOR_W / 2 + 0.76, dv + B.DOOR_H + 0.42), w=0.84, h=0.74, unique=True, d=0.3, hero=True)
	K.door(r, door_u, B.DOOR_W, dv, B.DOOR_H)
	l = B.side(-1, HX)
	K.window(l, 0.0, win_y, B.WIN, B.WIN)
	for s in (r, l):
		s.beam((-HZ - 0.1, Y0), (HZ + 0.1, Y0 + 0.04), w=0.9, h=B.JETTY_H, d=-0.1)
		s.beam((-HZ - 0.1, F), (HZ + 0.1, F - 0.04), w=0.66, h=B.JETTY_H, d=0.1)
		for u in (-HZ + 0.15, HZ - 0.15):
			s.beam((u, Y0), (u, F), h=B.POST, w=B.POST_DEPTH, d=0.18)
		K.window(s, 0.0, F + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW, B.WIN, B.WIN, shutters=False)
		K.wall(s, -HZ, HZ, v0, roof, cols=6, rows=5, shadow_depth=0.7)
	# ---- the roof, the dormer, a chimney at the back of the ridge
	K.tiled((-ROOF_X, RIDGE_Y, 0), (ROOF_X, RIDGE_Y, 0), (-ROOF_X, EAVE_Y, EAVE_Z), 7, (0, 1, 1), moss=0, sun=(0.2, 0.45), nx=12)
	K.tiled((ROOF_X, RIDGE_Y, 0), (-ROOF_X, RIDGE_Y, 0), (ROOF_X, EAVE_Y, -EAVE_Z), 7, (0, 1, -1), moss=0.4, mossy_end=1, nx=12)
	K.Beam((-ROOF_X - 0.25, RIDGE_Y + 0.14, 0), (ROOF_X + 0.25, RIDGE_Y + 0.14, 0), (0, 0, 1), 1.15, 0.5, ch=0.14, scheme_name="Clay", knots=0, rings=10, bend=0.02, hidden_back=False, unique=True)
	for x, sign in ((ROOF_X, 1), (-ROOF_X, -1)):
		for zs in (1, -1):
			K.Beam((x, RIDGE_Y + 0.05, 0), (x, EAVE_Y - 0.2, zs * (EAVE_Z + 0.22)), (sign, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, unique=sign > 0, knots=1, rings=5, hero=True)
	dormer()
	B.chimney(7.8, -1.9, RIDGE_Y - 6.0, RIDGE_Y + 2.6)
	print("passage %.1f wide, crown %.1f; floor %.2f, plate %.2f, ridge %.2f" % (R * 2, SPRING + R, Y0, F, RIDGE_Y))


if __name__ == "__main__":
	K.main(build)
