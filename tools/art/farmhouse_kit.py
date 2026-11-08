"""The thatched farmhouse: low and wide under a thick straw roof, for the meadows. Built on the house kit (tools/art/house_base.py).
  python tools/art/farmhouse_kit.py art/kit/farmhouse
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/farmhouse")
import house_base as B  # noqa: E402

K = B.K
B.setup("Farmhouse")
HX, HZ = 13.0, 6.6
FOOT_Y = 2.2
F = B.DOOR_TOP + B.MARGIN + B.JETTY_H / 2  # the plate's height comes from the door
ROOF_X, EAVE_Z, EAVE_Y, RIDGE_Y = 14.2, 8.8, 8.3, 19.4
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_Z
K.FOOT_Y = FOOT_Y
K.GRAD_Y = (2.5, 16.0)
if os.environ.get("HOUSE_RIM") == "1":
	K.RIM = dict(hx=HX, z0=-HZ, z1=HZ)
# straw: close, muted, thin bundles with blunt ends
B.tiles((136, 120, 88), (140, 122, 84), (130, 114, 88), (118, 104, 84), (150, 134, 100), (82, 70, 62), (92, 80, 68), (0.22, 0.42), (0.0, 0.03))
K.TILE_SIDE = 0.28  # straw: fine strands, not shingles
K.TILE_PLANE = 0.3
K.SCHEMES["Straw"] = {"BASE": (136, 112, 72), "LIGHT": (150, 128, 84), "WARM": (142, 114, 68), "DUSK": (112, 92, 68), "COOL": (118, 100, 74), "GRAIN": (86, 68, 50)}


def warp(p):
	x, y, z = p
	yc = max(y, 0.0)
	wave = math.cos(min(abs(x) / (ROOF_X + 0.5), 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	return (x + 0.02 * yc, y - 0.8 * rise * wave - 0.28 * wave * min(max((abs(z) - HZ) / 1.6, 0), 1) + 0.015 * x * min(yc / 9, 1), z - 0.012 * yc)


K.warp = warp


def roof(u):
	return RIDGE_Y - abs(u) * SLOPE


def build():
	v0 = FOOT_Y - 0.5
	clear = (F - B.JETTY_H / 2) - FOOT_Y - (B.WIN + B.FRAME_ABOVE + B.SILL_BELOW)
	win_y = FOOT_Y + clear / 2 + B.SILL_BELOW
	du = -4.6
	# ---- front: door, one plain window beside it, one shuttered window in a wide calm bay
	f = K.Face("front", (0, 0, HZ), (1, 0, 0), (0, 0, 1))
	f.beam((-HX - 0.3, F + 0.05), (HX + 0.3, F - 0.05), w=0.66, h=B.JETTY_H, unique=True, knots=1, d=0.2)
	for u in (-HX + 0.1, HX - 0.1):
		f.beam((u, FOOT_Y), (u, F), w=B.POST_DEPTH, h=B.POST, unique=True, d=0.2)
	B.door_set(f, du)
	K.window(f, -9.65, win_y, B.WIN, B.WIN, shutters=False)
	K.window(f, 5.3, win_y, B.WIN, B.WIN)
	K.wall(f, -HX, HX, v0, lambda u: roof(HZ), shade_y=F, shadow_depth=0.8, cols=8, rows=3)
	# ---- back: two windows off-centre
	b = K.Face("back", (0, 0, -HZ), (-1, 0, 0), (0, 0, -1))
	b.beam((-HX - 0.3, F - 0.04), (HX + 0.3, F + 0.05), w=0.66, h=B.JETTY_H, d=0.2)
	for u in (-HX + 0.1, HX - 0.1):
		b.beam((u, FOOT_Y), (u, F), w=B.POST_DEPTH, h=B.POST, d=0.2)
	K.window(b, -6.8, win_y, B.WIN, B.WIN, shutters=False)
	K.window(b, 4.6, win_y, B.WIN, B.WIN, shutters=False)
	K.wall(b, -HX, HX, v0, lambda u: roof(HZ), shade_y=F, shadow_depth=0.8, cols=8, rows=3)
	# ---- gable ends: a window below and one in the gable
	for sign in (1, -1):
		s = B.side(sign, HX)
		s.beam((-HZ - 0.1, F), (HZ + 0.1, F + 0.04), w=0.66, h=B.JETTY_H, d=0.1)
		for z in (-HZ + 0.15, HZ - 0.15):
			s.beam((z, FOOT_Y), (z, F), h=B.POST, w=B.POST_DEPTH, d=0.18)
		K.window(s, 0.0, win_y, B.WIN, B.WIN, shutters=sign > 0)
		K.window(s, 0.0, F + B.JETTY_H / 2 + B.MARGIN + B.SILL_BELOW, B.WIN, B.WIN, shutters=False)
		K.wall(s, -HZ, HZ, v0, roof, cols=6, rows=5, shadow_depth=0.7)
	# ---- stone
	K.footing(f, -HX - 0.45, du - B.DOOR_W / 2 - 0.72, cap_ends=True)
	K.footing(f, du + B.DOOR_W / 2 + 0.72, HX + 0.45, cap_ends=True)
	K.footing(b, -HX - 0.45, HX + 0.45)
	for sign in (1, -1):
		K.footing(B.side(sign, HX), -HZ - 0.45, HZ + 0.45, shared="side")
	# ---- the roof: fewer, thicker courses than tile, a rolled ridge
	K.tiled((-ROOF_X, RIDGE_Y, 0), (ROOF_X, RIDGE_Y, 0), (-ROOF_X, EAVE_Y, EAVE_Z), 7, (0, 1, 1), lift=0.3, nx=14, moss=0.1, mossy_end=-1)
	K.tiled((ROOF_X, RIDGE_Y, 0), (-ROOF_X, RIDGE_Y, 0), (ROOF_X, EAVE_Y, -EAVE_Z), 7, (0, 1, -1), lift=0.3, nx=14, moss=0.2, mossy_end=1)
	K.Beam((-ROOF_X - 0.25, RIDGE_Y + 0.22, 0), (ROOF_X + 0.25, RIDGE_Y + 0.22, 0), (0, 0, 1), 1.7, 0.74, ch=0.22, scheme_name="Straw", knots=0, rings=12, bend=0.02, hidden_back=False, unique=True)
	for x, sign in ((ROOF_X, 1), (-ROOF_X, -1)):
		for zs in (1, -1):
			K.Beam((x, RIDGE_Y + 0.05, 0), (x, EAVE_Y - 0.2, zs * (EAVE_Z + 0.22)), (sign, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, unique=sign > 0, knots=1, rings=5, hero=True)
	B.chimney(6.2, -1.7, RIDGE_Y - 6.0, RIDGE_Y + 2.9)


if __name__ == "__main__":
	K.main(build)
