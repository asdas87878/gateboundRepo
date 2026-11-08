"""The crooked townhouse: built on the cottage's kit (tools/art/cottage_kit.py: door, windows, timber, plaster, stone painters), with blue slate on its roof.
A tall, thin house for tight streets. Each upper floor jets out at the front only, the back and sides drop straight, and the whole tower leans one way with straight timbers, so it reads old rather than rubbery.
Writes into art/kit/townhouse: Townhouse_<Frame|Joinery|Walls|Roof>.png, Townhouse_Walls_Normal.png, .obj per sheet, kit.json. Studs, y up, the door faces +z.

  python tools/art/townhouse_kit.py art/kit/townhouse
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/townhouse")
import cottage_kit as K  # noqa: E402

K.PREFIX = "Townhouse"
for mesh, name in ((K.MW, "Frame"), (K.MJ, "Joinery"), (K.ML, "Walls"), (K.MR, "Roof")):
	mesh.name = "Townhouse_" + name

# the house, studs
X0, X1 = 6.85, 7.15  # half width: ground floor, then upper floors just wider
Z_BACK = -5.4
Z0, Z1, Z2 = 5.4, 6.6, 7.7  # front faces: ground, middle, gable. The front jets out, a little over a stud a floor
FOOT_Y = 2.2
# the user's rule, on this house: be liberal with plaster around all the wood. Windows and the door keep clear plaster on every side, and separate wood pieces don't touch.
# Floors are sized from the openings outward. Only the frame's own joints meet: corner posts and bracket into the jetty beams
MARGIN = 1.35  # studs of clear plaster from a window or door surround to any other wood or the roof
FRAME_ABOVE, SILL_BELOW = 0.42, 0.41  # how far a window's head and sill reach past its glass
DOOR_TOP = 7.62  # the top of the lintel
JETTY_H = 0.95  # the beam under each upper floor
WIN = 2.6  # every window on the house is this one size, square
WIN0, WIN1, WIN2 = WIN, WIN, WIN
F1 = DOOR_TOP + MARGIN + JETTY_H / 2  # the first jetty: its height comes from the door
_clear = (F1 - JETTY_H / 2) - FOOT_Y - (WIN0 + FRAME_ABOVE + SILL_BELOW)
V0 = FOOT_Y + _clear / 2 + SILL_BELOW  # the ground window, centred in the plaster from footing to jetty
V1 = F1 + JETTY_H / 2 + MARGIN + SILL_BELOW
F2 = V1 + WIN1 + FRAME_ABOVE + MARGIN + JETTY_H / 2  # the second
V2 = F2 + JETTY_H / 2 + MARGIN + SILL_BELOW
EAVE_X, EAVE_Y = X1 + 1.0, F2 + 0.3
RIDGE_Y = EAVE_Y + EAVE_X * 1.4
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_X
ROOF_FRONT, ROOF_BACK = 8.65, -6.4
K.FOOT_Y = FOOT_Y
# uniformity: at this size the cottage's hand-cut variation read as mistakes. Timbers keep one thickness per job, and pieces vary only slightly
K.BEAM_TAPER = 0.025
K.SHUTTER_DROOP = 0.03
K.SHUTTER_OPEN = (0.2, 0.26)
K.SHORT = 3.0  # shares the two wood sheets evenly, so long beams and short pieces hold the same sharpness
POST = 0.8  # every corner post
POST_DEPTH = 0.7
K.FOOTING_CAST = 0  # no sill rails here, so nothing throws a shadow on the stone
K.STROKE_STRENGTH = 0.4  # big plain walls showed the strokes as pale ghost shapes
K.CRACK_DENSITY = 0
K.STROKE_DENSITY = 0.45  # these walls are small, so the cottage's stroke count reads as streaks

# blue slate, close together; flat-ended tiles, wider than the cottage's
K.TL_BASE = np.array((66, 74, 106), float)
K.TL_WARM = np.array((72, 77, 106), float)
K.TL_ROSE = np.array((74, 74, 106), float)
K.TL_DUSK = np.array((58, 64, 94), float)
K.TL_LIGHT = np.array((82, 92, 120), float)
K.TL_GAP = np.array((46, 48, 72), float)
K.TL_SHADOW = np.array((52, 56, 82), float)
K.TILE_ROUND = (0.03, 0.07)
K.TILE_WIDTH = (1.7, 2.5)
K.SCHEMES["Slate"] = {"BASE": (68, 76, 106), "LIGHT": (76, 84, 114), "WARM": (74, 78, 106), "DUSK": (60, 66, 96), "COOL": (62, 72, 104), "GRAIN": (48, 52, 78)}


def warp(p):
	"""one lean, in one direction: no floor bulges against another. The ridge sags, the eaves droop a little"""
	x, y, z = p
	yc = max(y, 0.0)
	wave = math.cos(min(abs(z - 0.9) / 8.0, 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	dx = 0.028 * yc
	dz = -0.012 * yc
	dy = -0.55 * rise * wave - 0.18 * wave * min(max((abs(x) - X0) / 1.3, 0), 1) + 0.02 * z * min(yc / 14, 1)
	return (x + dx, y + dy, z + dz)


K.warp = warp
K.GRAD_Y = (2.5, RIDGE_Y - 2)


def roofline(u):
	return RIDGE_Y - abs(u) * SLOPE


def side(sign, x):
	"""a side wall's frame. u runs towards the front on the left, towards the back on the right"""
	return K.Face("side", (sign * x, 0, 0), (0, 0, -sign), (sign, 0, 0))


def u_of(sign, z):
	return -sign * z


def bracket(face, u, v, reach):
	"""the house's personality: a chunky bracket growing out of a corner post and curving up to carry the jetty beam. It is part of the post, so it adds no new piece of wood beside anything"""
	kw = dict(ch=0.08, hidden_back=False, rings=2, knots=0)
	K.Beam(face.at(u, v - 1.75, 0.34), face.at(u, v - 0.86, reach * 0.42), face.right, 0.7, 0.72, **kw)
	K.Beam(face.at(u, v - 1.0, reach * 0.34), face.at(u, v - 0.3, reach), face.right, 0.7, 0.72, **kw)


def build():
	v0 = FOOT_Y - 0.5
	# ---- ground floor: the door is the feature
	f0 = K.Face("front0", (0, 0, Z0), (1, 0, 0), (0, 0, 1))
	du, dw = -2.3, 3.5
	dv0, dh = 0.35, 6.5
	f0.beam((-X0 + 0.1, FOOT_Y), (-X0 + 0.1, F1), w=POST_DEPTH, h=POST, unique=True, d=0.2)
	f0.beam((X0 - 0.1, FOOT_Y), (X0 - 0.1, F1), w=POST_DEPTH, h=POST, unique=True, d=0.2)
	f0.beam((du - dw / 2 - 0.42, -0.5), (du - dw / 2 - 0.4, dv0 + dh + 0.72), w=0.72, h=0.7, unique=True, foot=True, d=0.22, hero=True)
	f0.beam((du + dw / 2 + 0.42, -0.5), (du + dw / 2 + 0.4, dv0 + dh + 0.72), w=0.72, h=0.7, unique=True, foot=True, d=0.22)
	f0.beam((du - dw / 2 - 0.72, dv0 + dh + 0.5), (du + dw / 2 + 0.76, dv0 + dh + 0.42), w=0.84, h=0.74, unique=True, d=0.3, hero=True, nails=((0.05, 0.3), (0.95, 0.3)))
	K.door(f0, du, dw, dv0, dh)
	K.window(f0, (du + dw / 2 + 0.77 + X0 - 0.53) / 2, V0, WIN, WIN, shutters=False)
	for u in (-X0 + 0.1, X0 - 0.1):
		bracket(f0, u, F1, Z1 - Z0 + 0.1)
	K.wall(f0, -X0, X0, v0, lambda u: F1 + 0.1, shade_y=F1, shadow_depth=0.9, cols=4, rows=3)
	# ---- middle floor: one wide window with the only shutters on the house
	f1 = K.Face("front1", (0, 0, Z1), (1, 0, 0), (0, 0, 1))
	f1.beam((-X1 - 0.25, F1), (X1 + 0.25, F1 + 0.06), w=1.5, h=0.95, d=-0.6, unique=True, knots=1)  # its underside closes the jetty
	f1.beam((-X1 + 0.1, F1), (-X1 + 0.1, F2), w=POST_DEPTH, h=POST, unique=True, d=0.2)
	f1.beam((X1 - 0.1, F1), (X1 - 0.1, F2), w=POST_DEPTH, h=POST, unique=True, d=0.2)
	K.window(f1, 0.1, V1, WIN1, WIN1)
	for u in (-X1 + 0.1, X1 - 0.1):
		bracket(f1, u, F2, Z2 - Z1 + 0.1)
	K.wall(f1, -X1, X1, F1 - 0.2, lambda u: F2 + 0.1, shade_y=F2, shadow_depth=1.0, cols=4, rows=3)
	# ---- the gable: a window and plaster
	f2 = K.Face("front2", (0, 0, Z2), (1, 0, 0), (0, 0, 1))
	f2.beam((-X1 - 0.3, F2), (X1 + 0.3, F2 + 0.06), w=1.45, h=0.95, d=-0.55, unique=True, knots=1)
	K.window(f2, 0.0, V2, WIN2, WIN2, shutters=False)
	K.wall(f2, -X1 - 0.05, X1 + 0.05, F2 - 0.2, roofline, cols=4, rows=3)
	# ---- back: the same plane all the way up, so the tower looks like it stands
	b = K.Face("back", (0, 0, Z_BACK), (-1, 0, 0), (0, 0, -1))
	b.beam((-X1 - 0.2, F1), (X1 + 0.2, F1 + 0.05), w=0.72, h=JETTY_H, d=0.1)
	b.beam((-X1 - 0.2, F2), (X1 + 0.2, F2 - 0.05), w=0.72, h=JETTY_H, d=0.1)
	for u in (-X0 + 0.1, X0 - 0.1):
		b.beam((u, FOOT_Y), (u, F1), h=POST, w=POST_DEPTH, d=0.18)
	for u in (-X1 + 0.1, X1 - 0.1):
		b.beam((u, F1), (u, F2), h=POST, w=POST_DEPTH, d=0.14)
	K.window(b, -2.6, V0, WIN, WIN, shutters=False)
	K.window(b, 2.6, V1, WIN, WIN, shutters=False)
	K.wall(b, -X1, X1, v0, roofline, cols=4, rows=6, shadow_depth=0.7)
	# ---- sides: plain plaster between straight corners. One small window on the left's middle floor, the right left bare
	for sign in (1, -1):
		s0 = side(sign, X0)
		a, c = sorted((u_of(sign, Z_BACK), u_of(sign, Z0)))
		s0.beam((u_of(sign, Z_BACK + 0.15), FOOT_Y), (u_of(sign, Z_BACK + 0.15), F1), h=POST, w=POST_DEPTH, d=0.18)
		s0.beam((u_of(sign, Z0 - 0.15), FOOT_Y), (u_of(sign, Z0 - 0.15), F1), h=POST, w=POST_DEPTH, d=0.18)
		K.wall(s0, a, c, v0, lambda u: F1 + 0.1, shade_y=F1, shadow_depth=0.9, cols=3, rows=3)
		s1 = side(sign, X1)
		a1, c1 = sorted((u_of(sign, Z_BACK), u_of(sign, Z1)))
		s1.beam((a1 - 0.1, F1), (c1 + 0.1, F1 + 0.04), w=0.72, h=JETTY_H, d=-0.08)
		s1.beam((a1 - 0.1, F2), (c1 + 0.1, F2 - 0.04), w=0.72, h=JETTY_H, d=0.05)
		s1.beam((u_of(sign, Z_BACK + 0.15), F1), (u_of(sign, Z_BACK + 0.15), F2), h=POST, w=POST_DEPTH, d=0.16)
		s1.beam((u_of(sign, Z1 - 0.2), F1), (u_of(sign, Z1 - 0.2), F2), h=POST, w=POST_DEPTH, d=0.16)
		if sign < 0:
			K.window(s1, u_of(sign, 0.6), V1, WIN, WIN, shutters=False)
		K.wall(s1, a1, c1, F1 - 0.2, lambda u: F2 + 0.1, shade_y=F2, shadow_depth=0.8, cols=3, rows=3)
		s2 = side(sign, X1)
		a2, c2 = sorted((u_of(sign, Z_BACK), u_of(sign, Z2)))
		K.wall(s2, a2, c2, F2 - 0.2, lambda u: roofline(X1) + 0.2, cols=3, rows=1)
	# ---- stone: one footing round the house, one slab for a doorstep
	K.footing(f0, -X0 - 0.45, du - dw / 2 - 0.72, cap_ends=True)
	K.footing(f0, du + dw / 2 + 0.72, X0 + 0.45, cap_ends=True)
	K.footing(b, -X0 - 0.45, X0 + 0.45)
	for sign in (1, -1):
		K.footing(side(sign, X0), -abs(Z_BACK) - 0.45, Z0 + 0.45, shared="side")
	# ---- roof: slate down both sides, a ridge board and chunky barge boards
	K.tiled((0, RIDGE_Y, ROOF_FRONT), (0, RIDGE_Y, ROOF_BACK), (EAVE_X, EAVE_Y, ROOF_FRONT), 8, (1, 1, 0), moss=0, sun=None, nx=8)
	K.tiled((0, RIDGE_Y, ROOF_BACK), (0, RIDGE_Y, ROOF_FRONT), (-EAVE_X, EAVE_Y, ROOF_BACK), 8, (-1, 1, 0), moss=0.2, sun=(0.72, 0.42), nx=8)
	K.Beam((0, RIDGE_Y + 0.16, ROOF_FRONT + 0.25), (0, RIDGE_Y + 0.16, ROOF_BACK - 0.25), (1, 0, 0), 1.1, 0.46, ch=0.13, scheme_name="Slate", knots=0, rings=8, bend=0.02, hidden_back=False, unique=True)
	for z, zs in ((ROOF_FRONT, 1), (ROOF_BACK, -1)):
		for s_ in (1, -1):
			K.Beam((0, RIDGE_Y + 0.06, z), (s_ * (EAVE_X + 0.22), EAVE_Y - 0.2, z), (0, 0, zs), 0.38, 0.9, ch=0.08, hidden_back=False, unique=zs > 0, knots=1, rings=5, hero=zs > 0)
	# ---- chimney: stone, on the ridge towards the back, chunky, with a clay pot
	cx, cz = 0.75, -2.7
	K.Beam((cx + 0.06, RIDGE_Y + 3.2, cz + 0.03), (cx + 0.14, RIDGE_Y + 4.3, cz), (0, 0, 1), 0.9, 0.9, ch=0.15, scheme_name="Clay", knots=0, rings=2, bend=0.01, hidden_back=False, cap_top=K.SOOT)


print("floors: window feet %.2f %.2f %.2f, jetties %.2f %.2f, eave %.2f, ridge %.2f" % (V0, V1, V2, F1, F2, EAVE_Y, RIDGE_Y))
print("margin, ground window: above and below %.2f" % (_clear / 2))
if __name__ == "__main__":
	K.main(build)
