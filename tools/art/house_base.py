"""What every house after the cottage shares (tools/art/cottage_kit.py is the kit): the settings the user approved on the townhouse, and small helpers.
Rules: plaster stays generous around all wood (MARGIN), separate wood parts don't touch, all windows one square size. See docs/style/art-style.md."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cottage_kit as K  # noqa: E402

MARGIN = 1.35  # studs of clear plaster from a window or door surround to other wood or the roof
WIN = 2.6  # every window, square
FRAME_ABOVE, SILL_BELOW = 0.42, 0.41  # how far a window's head and sill reach past its glass
JETTY_H = 0.74  # a floor beam
POST, POST_DEPTH = 0.8, 0.7  # every corner post
DOOR_W, DOOR_V0, DOOR_H = 3.5, 0.35, 6.5
DOOR_TOP = 7.62  # the top of the lintel


def setup(name):
	K.PREFIX = name
	for mesh, sheet in ((K.MW, "Frame"), (K.MJ, "Joinery"), (K.ML, "Walls"), (K.MR, "Roof")):
		mesh.name = f"{name}_{sheet}"
	K.BEAM_TAPER = 0.025
	K.SHUTTER_DROOP = 0.03
	K.SHUTTER_OPEN = (0.2, 0.26)
	K.SHORT = 3.0
	K.FOOTING_CAST = 0
	K.STROKE_STRENGTH = 0.4
	K.CRACK_DENSITY = 0
	K.STROKE_DENSITY = 0.45
	K.SCHEMES["Slate"] = {"BASE": (68, 76, 106), "LIGHT": (76, 84, 114), "WARM": (74, 78, 106), "DUSK": (60, 66, 96), "COOL": (62, 72, 104), "GRAIN": (48, 52, 78)}


def tiles(base, warm, rose, dusk, light, gap, shadow, width, rnd):
	K.TL_BASE, K.TL_WARM, K.TL_ROSE, K.TL_DUSK, K.TL_LIGHT = (np.array(c, float) for c in (base, warm, rose, dusk, light))
	K.TL_GAP, K.TL_SHADOW = np.array(gap, float), np.array(shadow, float)
	K.TILE_WIDTH, K.TILE_ROUND = width, rnd


def slate():
	tiles((66, 74, 106), (72, 77, 106), (74, 74, 106), (58, 64, 94), (82, 92, 120), (46, 48, 72), (52, 56, 82), (1.7, 2.5), (0.03, 0.07))


def side(sign, x):
	"""a side wall's frame: u runs towards the front on the left, towards the back on the right"""
	return K.Face("side", (sign * x, 0, 0), (0, 0, -sign), (sign, 0, 0))


def door_set(face, du, foot=-0.5):
	"""a door with its posts and lintel: the house's feature"""
	dw = DOOR_W
	face.beam((du - dw / 2 - 0.42, foot), (du - dw / 2 - 0.4, DOOR_V0 + DOOR_H + 0.72), w=0.72, h=0.7, unique=True, foot=True, d=0.22, hero=True)
	face.beam((du + dw / 2 + 0.42, foot), (du + dw / 2 + 0.4, DOOR_V0 + DOOR_H + 0.72), w=0.72, h=0.7, unique=True, foot=True, d=0.22)
	face.beam((du - dw / 2 - 0.72, DOOR_V0 + DOOR_H + 0.5), (du + dw / 2 + 0.76, DOOR_V0 + DOOR_H + 0.42), w=0.84, h=0.74, unique=True, d=0.3, hero=True, nails=((0.05, 0.3), (0.95, 0.3)))
	K.door(face, du, dw, DOOR_V0, DOOR_H)


def doorstep(du, z):
	K.stone_prism((du - DOOR_W / 2 - 0.5, 0.0, z + 1.05), (du + DOOR_W / 2 + 0.5, 0.05, z + 1.0), 1.8, 0.86, (0, 1, 0), course=(1.5, 2.4), block=(2.6, 3.8))


def chimney(cx, cz, y0, top):
	"""the clay pot; the stone is in house_stone.py"""
	K.Beam((cx + 0.06, top + 0.5, cz + 0.03), (cx + 0.14, top + 1.6, cz), (0, 0, 1), 0.9, 0.9, ch=0.15, scheme_name="Clay", knots=0, rings=2, bend=0.01, hidden_back=False, cap_top=K.SOOT)


def bracket(face, u, v, reach):
	"""a chunky bracket growing out of a post, turning out to carry a beam"""
	kw = dict(ch=0.08, hidden_back=False, rings=2, knots=0)
	K.Beam(face.at(u, v - 1.75, 0.34), face.at(u, v - 0.86, reach * 0.42), face.right, 0.7, 0.72, **kw)
	K.Beam(face.at(u, v - 1.0, reach * 0.34), face.at(u, v - 0.3, reach), face.right, 0.7, 0.72, **kw)


FOOT = 2.2
F1 = DOOR_TOP + MARGIN + JETTY_H / 2  # the first floor's height comes from the door
FLOOR = 2 * JETTY_H / 2 + 2 * MARGIN + SILL_BELOW + WIN + FRAME_ABOVE  # one more storey, sized from its window
WIN0 = FOOT + ((F1 - JETTY_H / 2) - FOOT - (WIN + FRAME_ABOVE + SILL_BELOW)) / 2 + SILL_BELOW  # a ground-floor window


def above(f):
	"""a window's foot in the storey above floor beam f"""
	return f + JETTY_H / 2 + MARGIN + SILL_BELOW


def make_warp(xa, xb, lean=0.016, sag=0.7, lean_z=-0.01):
	"""one lean for the whole house, and one sag along its length that grows with height"""
	import math

	def warp(p):
		x, y, z = p
		yc = max(y, 0.0)
		f = min(max((x - xa) / (xb - xa), 0), 1)
		return (x + lean * yc, y - sag * math.sin(f * math.pi) * min(yc / 30, 1) ** 1.5, z + lean_z * yc)

	return warp


def block(cx, cz, hx, hz, floors, ridge="x", pitch=1.05, eave_over=1.4, gable_over=1.1, courses=8, lift=0.3, moss=0.0, sun=None, windows=None, door_u=None, ridge_scheme="Clay", has_roof=True, hide=()):
	"""a plain gabled block of the house kit: walls, floor beams, corner posts, windows, optional door on the front (+z), and its roof.
	floors: heights of the floor beams, the last under the eaves. windows: {"front"|"back"|"left"|"right": [(u, foot, shutters)]}, u from that face's centre. hide: faces another block covers"""
	windows = windows or {}
	F = floors[-1]
	EX, EZ = hx + (gable_over if ridge == "x" else eave_over), hz + (eave_over if ridge == "x" else gable_over)
	half = hz + eave_over if ridge == "x" else hx + eave_over
	eave_y = F + 0.1
	ridge_y = eave_y + half * pitch
	roofat = lambda d: ridge_y - abs(d) * pitch
	faces = {
		"front": (K.Face("front", (cx, 0, cz + hz), (1, 0, 0), (0, 0, 1)), hx, ridge == "x"),
		"back": (K.Face("back", (cx, 0, cz - hz), (-1, 0, 0), (0, 0, -1)), hx, ridge == "x"),
		"right": (K.Face("right", (cx + hx, 0, cz), (0, 0, -1), (1, 0, 0)), hz, ridge == "z"),
		"left": (K.Face("left", (cx - hx, 0, cz), (0, 0, 1), (-1, 0, 0)), hz, ridge == "z"),
	}
	for name, (f, s, eave_side) in faces.items():
		if name in hide:
			continue
		for fl in floors:
			f.beam((-s - 0.3, fl), (s + 0.3, fl + 0.05), w=0.7, h=JETTY_H, d=0.14, unique=name == "front")
		for u in (-s + 0.1, s - 0.1):
			f.beam((u, FOOT), (u, F), w=POST_DEPTH, h=POST, unique=name == "front", d=0.18)
		for u, v, sh in windows.get(name, ()):
			K.window(f, u, v, WIN, WIN, shutters=sh)
		if name == "front" and door_u is not None:
			door_set(f, door_u)
		if eave_side:
			t = roofat(hz if ridge == "x" else hx)
			K.wall(f, -s, s, FOOT - 0.5, lambda u, t=t: t, shade_y=F, shadow_depth=0.8, cols=max(4, int(s)), rows=3 + len(floors))
		else:
			K.wall(f, -s, s, FOOT - 0.5, lambda u: roofat(u), cols=max(4, int(s)), rows=3 + 2 * len(floors), shadow_depth=0.7)
	info = dict(ridge_y=ridge_y, eave_y=eave_y, EX=EX, EZ=EZ, roofat=roofat, faces={k: v[0] for k, v in faces.items()})
	if not has_roof:
		return info
	if ridge == "x":
		K.tiled((cx - EX, ridge_y, cz), (cx + EX, ridge_y, cz), (cx - EX, eave_y, cz + EZ), courses, (0, 1, 1), lift=lift, moss=moss, sun=sun, nx=max(6, int(EX)))
		K.tiled((cx + EX, ridge_y, cz), (cx - EX, ridge_y, cz), (cx + EX, eave_y, cz - EZ), courses, (0, 1, -1), lift=lift, moss=moss, nx=max(6, int(EX)))
		K.Beam((cx - EX - 0.25, ridge_y + 0.14, cz), (cx + EX + 0.25, ridge_y + 0.14, cz), (0, 0, 1), 1.15, 0.5, ch=0.14, scheme_name=ridge_scheme, knots=0, rings=max(4, int(EX)), bend=0.02, hidden_back=False, unique=True)
		for sign in (1, -1):
			for zs in (1, -1):
				K.Beam((cx + sign * EX, ridge_y + 0.05, cz), (cx + sign * EX, eave_y - 0.2, cz + zs * (EZ + 0.22)), (sign, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, knots=1, rings=4, hero=True)
	else:
		K.tiled((cx, ridge_y, cz + EZ), (cx, ridge_y, cz - EZ), (cx + EX, eave_y, cz + EZ), courses, (1, 1, 0), lift=lift, moss=moss, nx=max(6, int(EZ)))
		K.tiled((cx, ridge_y, cz - EZ), (cx, ridge_y, cz + EZ), (cx - EX, eave_y, cz - EZ), courses, (-1, 1, 0), lift=lift, moss=moss, sun=sun, nx=max(6, int(EZ)))
		K.Beam((cx, ridge_y + 0.14, cz + EZ + 0.25), (cx, ridge_y + 0.14, cz - EZ - 0.25), (1, 0, 0), 1.15, 0.5, ch=0.14, scheme_name=ridge_scheme, knots=0, rings=max(4, int(EZ)), bend=0.02, hidden_back=False, unique=True)
		for zs in (1, -1):
			for sign in (1, -1):
				K.Beam((cx, ridge_y + 0.06, cz + zs * EZ), (cx + sign * (EX + 0.22), eave_y - 0.2, cz + zs * EZ), (0, 0, zs), 0.36, 0.9, ch=0.08, hidden_back=False, knots=1, rings=4, hero=zs > 0)
	return info
