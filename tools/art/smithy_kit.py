"""The blacksmith: no front wall, a heavy lintel on two corner posts, a stone forge with a glowing mouth and a big chimney at the back, an anvil on a stump. Built on the house kit.
  python tools/art/smithy_kit.py art/kit/smithy
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/smithy")
import house_base as B  # noqa: E402

K = B.K
B.setup("Smithy")
B.slate()
HX, HZ = 9.0, 6.4
FOOT_Y = 2.2
F = B.DOOR_TOP + B.MARGIN + 0.55
ROOF_X, EAVE_Z, EAVE_Y = HX + 1.15, HZ + 2.2, F - 0.1
RIDGE_Y = EAVE_Y + EAVE_Z * 0.95
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_Z
K.FOOT_Y = FOOT_Y
K.GRAD_Y = (2.5, RIDGE_Y - 3)
K.SCHEMES["Iron"] = {"BASE": (96, 98, 118), "LIGHT": (120, 122, 142), "WARM": (108, 104, 118), "DUSK": (80, 82, 104), "COOL": (88, 96, 122), "GRAIN": (66, 68, 90)}
FORGE = (4.6, -3.9)
STONE = dict(xa=-HX, xb=HX, zb=-HZ, zf=HZ, foot=FOOT_Y, du=0.0, dw=2 * HX - 3.4, step=False, floor=True, chimneys=[[(FORGE[0], FORGE[1], 2.9, 2.0, -1.0, 6.2), (FORGE[0] + 0.1, FORGE[1], 1.5, 1.3, 6.44, RIDGE_Y + 3.0)]])


def warp(p):
	x, y, z = p
	yc = max(y, 0.0)
	wave = math.cos(min(abs(x) / (ROOF_X + 0.5), 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	return (x + 0.016 * yc, y - 0.55 * rise * wave - 0.2 * wave * min(max((abs(z) - HZ) / 2.2, 0), 1), z - 0.008 * yc)


K.warp = warp


def roof(u):
	return RIDGE_Y - abs(u) * SLOPE


def paint_forge(r):
	"""the forge's mouth: dark brick shadow, embers rising to a soft bright glow"""
	H, W = r.h * K.SS, r.w * K.SS
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	u, v = xx / W, yy / H
	img = np.zeros((H, W, 3))
	img[:] = (46, 34, 48)
	# embers: broken clusters low in the mouth, soft where they light the dark, never rings
	g = np.random.default_rng(13)
	field = K.gaussian_filter(g.normal(0, 1, (H, W)).astype(np.float32), (H * 0.05, W * 0.035))
	field = field / (np.abs(field).max() + 1e-6)
	heat = np.clip(1.25 - (1 - v) * 2.2 - (np.abs(u - 0.5) / 0.5) ** 2 * 0.8 + field * 0.75, 0, 1.3)
	img = K.over(img, np.array((150, 58, 44), float), K.gaussian_filter(np.clip((heat - 0.1) / 0.5, 0, 1).astype(np.float32), 3))
	img = K.over(img, np.array((228, 118, 54), float), K.gaussian_filter(np.clip((heat - 0.55) / 0.3, 0, 1).astype(np.float32), 2) * 0.95)
	img = K.over(img, np.array((250, 196, 112), float), K.gaussian_filter(np.clip((heat - 0.95) / 0.25, 0, 1).astype(np.float32), 1.5) * 0.9)
	return np.clip(img, 0, 255)


def build():
	v0 = FOOT_Y - 0.5
	clear = (F - 0.55) - FOOT_Y - (B.WIN + B.FRAME_ABOVE + B.SILL_BELOW)
	win0 = FOOT_Y + clear / 2 + B.SILL_BELOW
	top = roof(HZ)
	# ---- the open front: a heavy lintel on two chunky posts, with brackets
	f = K.Face("front", (0, 0, HZ), (1, 0, 0), (0, 0, 1))
	f.beam((-HX - 0.5, F + 0.06), (HX + 0.5, F - 0.06), w=1.25, h=1.15, unique=True, knots=2, d=0.1, hero=True, hidden_back=False)
	for u in (-HX + 0.25, HX - 0.25):
		f.beam((u, FOOT_Y - 0.3), (u, F), w=1.0, h=1.15, unique=True, d=0.1, hidden_back=False)
		sgn = 1 if u < 0 else -1
		K.Beam(f.at(u + sgn * 0.5, F - 2.2, 0.1), f.at(u + sgn * 2.3, F - 0.5, 0.1), (0, 0, 1), 0.56, 0.6, ch=0.08, hidden_back=False, rings=2, knots=0)
	K.wall(f, -HX, HX, F + 0.3, lambda u: top, cols=6, rows=1)
	# ---- the outside of the back and sides
	b = K.Face("back", (0, 0, -HZ), (-1, 0, 0), (0, 0, -1))
	b.beam((-HX - 0.3, F), (HX + 0.3, F + 0.05), w=0.72, h=B.JETTY_H, d=0.14)
	for u in (-HX + 0.1, HX - 0.1):
		b.beam((u, FOOT_Y), (u, F), h=B.POST, w=B.POST_DEPTH, d=0.18)
	K.window(b, 4.6, win0, B.WIN, B.WIN, shutters=False)
	K.wall(b, -HX, HX, v0, lambda u: top, shade_y=F, shadow_depth=0.8, cols=6, rows=3)
	for sign in (1, -1):
		s = B.side(sign, HX)
		s.beam((-HZ - 0.1, F), (HZ + 0.1, F + 0.04), w=0.7, h=B.JETTY_H, d=0.1)
		s.beam((-HZ + 0.15, FOOT_Y), (-HZ + 0.15, F), h=B.POST, w=B.POST_DEPTH, d=0.18)
		K.window(s, -0.5, win0, B.WIN, B.WIN, shutters=sign < 0)
		K.window(s, 0.0, F + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW, B.WIN, B.WIN, shutters=False)
		K.wall(s, -HZ, HZ, v0, roof, cols=5, rows=5, shadow_depth=0.7)
	# ---- the insides, seen through the open front: deep shadow painted from the top
	back_in = K.Face("in_back", (0, 0, -HZ + 0.06), (1, 0, 0), (0, 0, 1))
	K.wall(back_in, -HX, HX, -0.2, lambda u: top, shade_y=F + 1, shadow_depth=4.0, cols=6, rows=3)
	for x, right, out in ((HX - 0.06, (0, 0, 1), (-1, 0, 0)), (-HX + 0.06, (0, 0, -1), (1, 0, 0))):
		s_in = K.Face("in_side", (x, 0, 0), right, out)
		K.wall(s_in, -HZ, HZ, -0.2, lambda u: top, shade_y=F + 1, shadow_depth=4.0, cols=4, rows=3)
	# a shelf of tools on the back wall
	back_in.beam((-7.8, 6.6), (-1.6, 6.64), w=0.5, h=0.34, d=0.2, unique=True)
	for u, ln in ((-6.9, 1.7), (-5.6, 1.3), (-4.3, 1.9), (-2.9, 1.4)):
		K.Beam(back_in.at(u, 6.4, 0.16), back_in.at(u + 0.04, 6.4 - ln, 0.16), (0, 0, 1), 0.14, 0.2, ch=0.03, scheme_name="Iron", hidden_back=False, rings=2, knots=0)
	# ---- the forge's glowing mouth, on the stone
	fx, fz = FORGE
	rect = K.JOIN.add((3.2, 2.3), paint_forge)
	z = fz + 2.0 + 0.2
	corners = [(fx - 1.6, 1.6, z), (fx + 1.6, 1.6, z), (fx + 1.6, 3.9, z), (fx - 1.6, 3.9, z)]
	K.emit.append(lambda: K.plate(corners, rect, (0, 0, 1), 0.1))
	# ---- the anvil on its stump, out where the smith works
	ax, az = -2.4, 2.6
	K.Beam((ax, -0.5, az), (ax, 2.1, az), (0, 0, 1), 1.5, 1.5, ch=0.2, knots=1, rings=2, hidden_back=False, unique=True)
	iron = dict(scheme_name="Iron", knots=0, rings=2, hidden_back=False, unique=True, bend=0.0)
	K.Beam((ax - 0.75, 2.1, az), (ax + 0.75, 2.1, az), (0, 0, 1), 1.0, 0.3, ch=0.06, **iron)
	K.Beam((ax - 0.34, 2.38, az), (ax + 0.34, 2.38, az), (0, 0, 1), 0.56, 0.4, ch=0.05, **iron)
	K.Beam((ax - 0.8, 2.76, az), (ax + 0.95, 2.76, az), (0, 0, 1), 0.86, 0.42, ch=0.08, **iron)
	K.Beam((ax + 0.95, 2.86, az), (ax + 1.75, 2.94, az), (0, 0, 1), 0.34, 0.22, ch=0.05, **iron)
	# ---- roof
	K.tiled((-ROOF_X, RIDGE_Y, 0), (ROOF_X, RIDGE_Y, 0), (-ROOF_X, EAVE_Y, EAVE_Z), 8, (0, 1, 1), moss=0, sun=None, nx=9)
	K.tiled((ROOF_X, RIDGE_Y, 0), (-ROOF_X, RIDGE_Y, 0), (ROOF_X, EAVE_Y, -EAVE_Z), 8, (0, 1, -1), moss=0.3, mossy_end=1, nx=9)
	K.Beam((-ROOF_X - 0.25, RIDGE_Y + 0.16, 0), (ROOF_X + 0.25, RIDGE_Y + 0.16, 0), (0, 0, 1), 1.1, 0.46, ch=0.13, scheme_name="Slate", knots=0, rings=8, bend=0.02, hidden_back=False, unique=True)
	for x, sign in ((ROOF_X, 1), (-ROOF_X, -1)):
		for zs in (1, -1):
			K.Beam((x, RIDGE_Y + 0.05, 0), (x, EAVE_Y - 0.2, zs * (EAVE_Z + 0.22)), (sign, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, unique=sign > 0, knots=1, rings=5, hero=True)
	cx, cz, _, _, _, ctop = STONE["chimneys"][0][-1]
	B.chimney(cx, cz, 0, ctop)


if __name__ == "__main__":
	K.main(build)
