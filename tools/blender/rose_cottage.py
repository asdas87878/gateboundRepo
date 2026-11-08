"""Rose Cottage: a new house in the old house kit's family (cream plaster, square windows, a green door and shutters, generous plaster
round every piece of wood), made a bit cooler with the crooked cottage study's chunky pink tiles, bell-cast roofs and wood painting.
My own design, no reference: an L plan. A 1.5-storey main block whose roof sweeps down over the porch in the inside corner (a
catslide), a dormer over the shuttered window, a chimney at the gable end; and a jettied two-storey gable wing, its upper floor
standing out over a row of joist ends.

Spacing (tools/art/house_base.py, the kit the user approved): 1.35 studs of clear plaster from a window or door surround to other
wood or the roof, separate wood parts don't touch, windows square at 2.6 (the dormer's 0.8 of that). Wood slimmer than the study's:
corner posts 0.9 square standing 0.3 out of the plaster, window surrounds 0.15 out. Wood only where a house has it: corner posts,
sill beams, floor beams and plates, door posts and lintel; plain plaster between.

tools/blender/crooked_cottage.py is the library here (tiles, roof faces, timbers, windows, render), pink_cottage.py under it.

  blender --background --python tools/blender/rose_cottage.py -- build
  blender --background --python tools/blender/rose_cottage.py -- bake_ao 40
  COTTAGE_OUT=art/kit/rosecottage python tools/art/paint_crooked_cottage.py
  blender --background --python tools/blender/rose_cottage.py -- render <tag> [--view=hero|near|far|back] [--clay] [--flat]
"""

import json
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crooked_cottage as cc  # noqa: E402
import pink_cottage as pc  # noqa: E402
from crooked_cottage import UP, X, Y, beam, wbeam, wpt, wnorm, wall, window, opening_loop, stone_course, lay_tiles, roof_skin, roof_edges, barge, ridge_beak, king_block, register, roof_top, quarter, obox, in_box  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "rosecottage")
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["build"]
cc.OUT = pc.OUT = OUT
cc.ARGS = pc.ARGS = ARGS
cc.PROUD = 0.3  # timbers stand this far out of the plaster (the study's 0.45 read too heavy)
cc.FRAME_PROUD = 0.15

# ---------------------------------------------------------------------------------------------------------------- the kit's numbers
FOOT = 2.2  # the sill beam's top: posts and plaster start here
SILL0 = 1.6  # the sill beam's foot; stones below
F1_0, F1_1 = 8.97, 9.71  # the ground floor's top beam (house_base F1 = 9.34, 0.74 tall)
WIN = 2.6
WIN0 = 4.28  # a ground-floor window's glass foot (house_base WIN0)
FR = 0.42  # a window's surround
DOOR_W, DOOR_V0, DOOR_H = 3.5, 0.35, 6.5
DOOR_TOP = 7.62  # the lintel's top
PANES = [((0.5, 0.0), (0.5, 1.0)), ((0.0, 0.5), (1.0, 0.5))]
SILL = (0.2, 0.5, 0.3)

# the main block: 17 x 10, one storey and the roof (long enough for the porch post to stand in a clear gap of plaster)
XL, XR = -15.0, 2.0
YF, YB = 0.0, 10.0
EAVE_Z = 9.44  # the eave's lip (house_base: the plate + 0.1)
MAIN_OVER = 1.6
VERGE = 1.1
RIDGE_Y = (YF + YB) / 2
MAIN_PITCH = 1.35
RIDGE_Z = EAVE_Z + (RIDGE_Y - (YF - MAIN_OVER)) * MAIN_PITCH
BOARD = 0.55  # the ridge board stands this far above the faces' ridge line
VERGE_EDGE = 0.42  # a verge's edge strip reaches up under the tiles' lips, so a far verge seen from below shows no gap

# the wing: 9 wide, two storeys, the upper one jettied 0.7 out over joist ends
WX0, WX1 = 2.0, 11.0
WY_G, WY_U, WY_B = -4.0, -4.7, 12.5  # ground front, upper front, back
BR_0, BR_1 = 10.2, 10.94  # the bressumer (the jetty beam); joist ends between F1_1 and BR_0
WP_0, WP_1 = 18.56, 19.3  # the wing's plate: high, so its eave clears the main ridge
WIN_U = 13.45  # the upper window's glass foot: centred in its storey
WEAVE_Z = 19.4
WING_OVER = 1.4
WRIDGE_X = (WX0 + WX1) / 2
WING_PITCH = 1.2
WRIDGE_Z = WEAVE_Z + (WRIDGE_X - (WX0 - WING_OVER)) * WING_PITCH

# the front: the shuttered window, the door in the inside corner under the catslide, the porch post
WIN_A = -10.0
DOOR_U = -1.55
PORCH_Y, PORCH_Z = -3.75, 8.0  # the catslide's eave over the porch
POST_X, POST_Y = -5.6, -3.5
PORCH_X0 = -6.1
SWOOP = (-7.75, -6.05)  # where the eave swings out to the porch's line
DORMER_X, DORMER_Y = WIN_A, 0.15
DORMER_W = 2.08  # the dormer's window (0.8 of the house's)
CHIM_X = -13.85

W_F = (Vector((0.0, YF, 0.0)), X)  # main front, u = x
W_ML = (Vector((XL, 0.0, 0.0)), -Y)  # main left gable end, u = -y
W_MB = (Vector((0.0, YB, 0.0)), -X)  # main back, u = -x
W_WF = (Vector((0.0, WY_G, 0.0)), X)  # wing ground front
W_WU = (Vector((0.0, WY_U, 0.0)), X)  # wing upper front and gable
W_WL = (Vector((WX0, 0.0, 0.0)), -Y)  # wing left side, u = -y
W_WR = (Vector((WX1, 0.0, 0.0)), Y)  # wing right side, u = y
W_WB = (Vector((0.0, WY_B, 0.0)), -X)  # wing back, u = -x

# ---------------------------------------------------------------------------------------------------------------- views
RES = (1200, 900)
VIEWS = {
	"hero": {"Target": (-2.5, 2.0, 11.0), "Yaw": -24.0, "Pitch": -4.5, "Dist": 74.0, "FOV": 31.0},
	"near": {"Target": (-4.2, -1.5, 6.2), "Yaw": -14.0, "Pitch": -2.5, "Dist": 32.0, "FOV": 30.0},
	"far": {"Target": (-2.5, 2.0, 11.0), "Yaw": -24.0, "Pitch": -4.5, "Dist": 125.0, "FOV": 31.0},
	"back": {"Target": (-1.0, 4.0, 10.0), "Yaw": 145.0, "Pitch": -4.0, "Dist": 70.0, "FOV": 31.0},
}


def set_view(name):
	v = VIEWS[name]
	pc.CAM = dict(v)
	pc.RES = RES
	cc.W_REF, cc.H_REF = RES
	pitch, yaw = math.radians(v["Pitch"]), math.radians(v["Yaw"])
	fh = Vector((-math.sin(yaw), math.cos(yaw), 0.0))
	fwd = fh * math.cos(pitch) - UP * math.sin(pitch)
	cc.FWD = fwd
	cc.EYE = Vector(v["Target"]) - fwd * v["Dist"]
	cc.RIGHTV = Vector((fh.y, -fh.x, 0.0))
	cc.UPV = cc.RIGHTV.cross(fwd)
	cc.F_PX = (RES[1] / 2) / math.tan(math.radians(v["FOV"]) / 2)
	cc.FOCUS = v["Dist"]


# ---------------------------------------------------------------------------------------------------------------- roofs
class XSurface(cc.Surface):
	"""a roof face whose eave and ridge are matched column by column (the same x), not resampled by length: the catslide's eave swings
	out and down over the porch while every column still runs straight up the slope"""

	def __init__(self, eave, ridge, c=0.55, k=2.0, name=""):
		cc.Surface.__init__(self, eave, ridge, c=c, k=k, n=len(eave), name=name)
		self.E = [Vector(p) for p in eave]
		self.R = [Vector(p) for p in ridge]
		self.t0 = (self.E[0] - self.E[1]).normalized()
		self.t1 = (self.E[-1] - self.E[-2]).normalized()
		xs = [p.x for p in self.E + self.R]
		ys = [p.y for p in self.E + self.R]
		self.bbox = (min(xs) - 0.5, max(xs) + 0.5, min(ys) - 0.5, max(ys) + 0.5)


def smoothstep(a, b, x):
	return cc.smoothstep(a, b, x)


def front_eave(x):
	"""the main front's eave: 1.6 out at 9.44, swinging out to the porch's line and down over it, right of the shuttered window"""
	t = smoothstep(SWOOP[0], SWOOP[1], x)
	y = (YF - MAIN_OVER) + (PORCH_Y - (YF - MAIN_OVER)) * t
	z = EAVE_Z + (PORCH_Z - EAVE_Z) * t - 0.12 * math.sin(math.pi * min(max((x - (XL - VERGE)) / 7.0, 0.0), 1.0)) * (1 - t)
	return Vector((x, y, z))


def define_roofs():
	R = {}
	xs = np.linspace(XL - VERGE, XR - 0.08, 64)
	span = xs[-1] - xs[0]
	ridge = [Vector((x, RIDGE_Y, RIDGE_Z - BOARD - 0.18 * math.sin(math.pi * (x - xs[0]) / span))) for x in xs]
	R["main_ridge"] = ridge
	R["MAIN_F"] = XSurface([front_eave(x) for x in xs], ridge, c=0.6, k=1.9, name="MAIN_F")
	R["MAIN_B"] = XSurface([Vector((x, YB + MAIN_OVER, EAVE_Z - 0.05 - 0.1 * math.sin(math.pi * (x - xs[0]) / span))) for x in xs], ridge, c=0.6, k=1.9, name="MAIN_B")
	# the wing: a crisp gable with a gentle bell-cast, its front corners flaring out a little
	ys = [WY_U - VERGE, WY_B + VERGE]
	wr = cc.smooth_curve([Vector((WRIDGE_X, ys[0], WRIDGE_Z - BOARD)), Vector((WRIDGE_X, (ys[0] + ys[1]) / 2, WRIDGE_Z - BOARD - 0.2)), Vector((WRIDGE_X, ys[1], WRIDGE_Z - BOARD - 0.05))], 40)
	R["wing_ridge"] = wr
	for side, xe in (("L", WX0 - WING_OVER), ("R", WX1 + WING_OVER)):
		eave = cc.smooth_curve([Vector((xe, ys[0], WEAVE_Z)), Vector((xe, (ys[0] + ys[1]) / 2, WEAVE_Z - 0.12)), Vector((xe, ys[1], WEAVE_Z - 0.02))], 40)
		R["WING_" + side] = cc.Surface(eave, wr, c=0.72, k=1.7, n=40, name="WING_" + side, kick=(0.3, 0.0, 0.12, 0.3, 0.3))
	register("HOUSE", R["MAIN_F"], R["MAIN_B"], R["WING_L"], R["WING_R"])
	# the dormer: its front on the wall line, its little gable roof running back into the main roof
	zr = R["MAIN_F"].height(DORMER_X, DORMER_Y)
	d = {"zr": zr, "glass": zr + 1.15}
	d["head"] = d["glass"] + DORMER_W + 0.36
	d["eave"] = d["head"] + 0.62
	d["half"] = DORMER_W / 2 + 0.36 + 0.72 + 0.25
	d["apex"] = d["eave"] + (d["half"] + 0.3) * 0.85
	yf, yb = DORMER_Y - 0.55, 4.4
	ridge = [Vector((DORMER_X, yf, d["apex"] - 0.3)), Vector((DORMER_X, yb, d["apex"] - 0.45))]
	for side, sx in (("L", -1), ("R", 1)):
		xe = DORMER_X + sx * (d["half"] + 0.3)
		R["DM_" + side] = cc.Surface([Vector((xe, yf, d["eave"])), Vector((xe, yb, d["eave"] - 0.1))], ridge, c=0.8, k=1.5, n=8, name="DM_" + side)
	R["dormer"] = d
	register("DM", R["DM_L"], R["DM_R"])
	print("[rose] main ridge %.2f, wing eave %.2f apex %.2f, dormer glass %.2f apex %.2f" % (RIDGE_Z, WEAVE_Z, WRIDGE_Z, d["glass"], d["apex"]), flush=True)
	return R


# ---------------------------------------------------------------------------------------------------------------- parts
def post(g, x, y, z0, z1, sx, sy, size=0.9, lean=(0.0, 0.0), **kw):
	"""a corner post: a square timber whose outer faces stand PROUD out of both walls (sx, sy: which way is out)"""
	c = Vector((x + sx * (cc.PROUD - size / 2), y + sy * (cc.PROUD - size / 2), 0.0))
	mid = c + UP * ((z0 + z1) / 2) + Vector((lean[0], lean[1], 0.0))
	beam(g, [c + UP * z0, mid, c + UP * z1], size, size, Y, taper=(1.03, 0.98), Part="post", **kw)


def hbeam(g, W, u0, u1, zc, h, sag=0.0, out=None, **kw):
	"""a horizontal timber on wall W from u0 to u1, centred at height zc, h tall, sagging a little in the middle"""
	um = (u0 + u1) / 2
	wbeam(g, W, [(u0, zc), (um, zc - sag), (u1, zc)], h, 0.6, out=cc.PROUD if out is None else out, **kw)


def square_window(g, W, cu, v0, size=WIN, tilt=0.0, sill=SILL, **params):
	window(g, W, cu - size / 2, cu + size / 2, v0, v0 + size, frame=FR, ft=0.42, recess=0.32, bars=PANES, sill=sill, tilt=tilt, bar_w=0.14, **params)


def win_hole(cu, v0, size=WIN):
	return opening_loop(cu - size / 2, cu + size / 2, v0, v0 + size)


def shutter(g, W, cu, v0, side, open_deg=14.0):
	"""a planked shutter hinged at the surround's outer edge, swung open nearly flat to the wall, two ledges across it"""
	n = wnorm(W)
	org, au = W
	sw, sh = 1.25, WIN + 0.55
	hinge = wpt(W, cu + side * (WIN / 2 + FR + 0.06), v0 - 0.28, 0.1)
	a = math.radians(open_deg)
	d = au * (side * math.cos(a)) + n * math.sin(a)
	nn = d.cross(UP) * side
	c = hinge + d * (sw / 2) + UP * (sh / 2)
	obox(g, "Joinery", "Joinery", "shutter", c, d, UP, (sw, sh, 0.16), Part="leaf")
	for z in (0.55, sh - 0.6):
		obox(g, "Joinery", "Joinery", "shutter", hinge + d * (sw / 2) + UP * z + nn * 0.12, d, UP, (sw - 0.1, 0.36, 0.1), Part="ledge")
	for z in (0.55, sh - 0.6):
		obox(g, "Joinery", "Joinery", "iron", hinge + d * 0.32 + UP * z + nn * 0.19, d, UP, (0.62, 0.14, 0.05), Part="strap")


def plank_door(g, W, du):
	"""the green planked door set back in its opening, two iron straps and a ring; chunky posts and a lintel (house_base door_set)"""
	n = wnorm(W)
	org, au = W
	u0, u1, v0, top = du - DOOR_W / 2, du + DOOR_W / 2, DOOR_V0, DOOR_V0 + DOOR_H
	back = 0.3
	leaf = g.island("Joinery", "door_green", pc.frame_of(wpt(W, u0, v0, -back), au, UP), Face="leaf", Wd=DOOR_W, Ht=DOOR_H)
	g.tri_fill("Joinery", [[wpt(W, u0, v0, -back), wpt(W, u1, v0, -back), wpt(W, u1, top, -back), wpt(W, u0, top, -back)]], n, leaf)
	rv = g.island("Joinery", "reveal", None, Face="reveal")
	ctr = wpt(W, du, (v0 + top) / 2)
	run = 0.0
	for a, b in (((u0, v0), (u0, top)), ((u0, top), (u1, top)), ((u1, top), (u1, v0))):
		A, B = wpt(W, *a), wpt(W, *b)
		L = (B - A).length
		q = [A, B, B - n * back, A - n * back]
		uv = [(run, 0), (run + L, 0), (run + L, back), (run, back)]
		if (q[1] - q[0]).cross(q[3] - q[0]).dot(ctr - (A + B) / 2) < 0:
			q, uv = q[::-1], uv[::-1]
		g.face("Joinery", q, rv, uv)
		run += L
	for z in (v0 + 1.15, top - 1.25):
		obox(g, "Joinery", "Joinery", "iron", wpt(W, u0 + 1.15, z, -back + 0.03), au, UP, (2.1, 0.22, 0.06), Part="strap")
		obox(g, "Joinery", "Joinery", "iron", wpt(W, u0 + 0.18, z, -back + 0.05), au, UP, (0.3, 0.42, 0.1), Part="hinge")
	obox(g, "Joinery", "Joinery", "iron", wpt(W, u1 - 0.55, v0 + 3.1, -back + 0.06), au, UP, (0.3, 0.3, 0.12), Part="ring")
	wbeam(g, W, [(u0 - 0.36, v0), (u0 - 0.34, DOOR_TOP - 0.05)], 0.72, 0.62, out=cc.PROUD, Part="door_post", taper=(1.04, 0.99))
	wbeam(g, W, [(u1 + 0.36, v0), (u1 + 0.34, DOOR_TOP - 0.05)], 0.72, 0.62, out=cc.PROUD, Part="door_post", taper=(1.04, 0.99))
	wbeam(g, W, [(u0 - 0.72, top + 0.385), (du, top + 0.36), (u1 + 0.76, top + 0.39)], 0.77, 0.66, out=cc.PROUD + 0.04, Part="lintel")


def wall_lantern(g, W, u, v):
	"""an iron lantern on a bracket: a short arm out of the wall, a curved strut under it, the lantern hanging from the arm's end"""
	n = wnorm(W)
	org, au = W
	beam(g, [wpt(W, u, v + 1.45, 0.0), wpt(W, u, v + 1.5, 1.05)], 0.16, 0.16, UP, obj="Joinery", kind="iron", Part="arm")
	beam(g, cc.bezier(wpt(W, u, v + 0.55, 0.0), wpt(W, u, v + 0.65, 0.7), wpt(W, u, v + 1.42, 0.85), 8), 0.13, 0.13, au, obj="Joinery", kind="iron", Part="strut")
	c = wpt(W, u, v, 0.95)
	beam(g, [c + UP * 1.45, c + UP * 1.05], 0.06, 0.06, au, obj="Joinery", kind="iron", Part="chain")
	obox(g, "Joinery", "Joinery", "iron", c + UP * 0.98, au, n, (0.72, 0.72, 0.16), Part="cap")
	obox(g, "Joinery", "Joinery", "iron", c + UP * 1.1, au, n, (0.34, 0.34, 0.12), Part="cap_top")
	obox(g, "Joinery", "Joinery", "lantern_glass", c + UP * 0.5, au, n, (0.52, 0.52, 0.8), Part="glass")
	obox(g, "Joinery", "Joinery", "iron", c + UP * 0.05, au, n, (0.62, 0.62, 0.12), Part="base")
	for su in (-1, 1):
		for sn in (-1, 1):
			p = c + au * (0.27 * su) + n * (0.27 * sn)
			beam(g, [p + UP * 0.08, p + UP * 0.92], 0.07, 0.07, n, obj="Joinery", kind="iron", Part="bar")


def chimney(g):
	"""a cream rendered stack astride the ridge near the left gable, bricks showing near the top, a thin cap and a clay pot"""
	cy = RIDGE_Y
	zb, zt = 15.2, 21.8

	def ring(z):
		t = (z - zb) / (zt - zb)
		hw = 1.0 + (0.86 - 1.0) * t
		hd = hw * 0.94
		cx = CHIM_X + 0.08 * t
		return [Vector((cx - hw, cy - hd, z)), Vector((cx + hw, cy - hd, z)), Vector((cx + hw, cy + hd, z)), Vector((cx - hw, cy + hd, z))]

	zs = [zb, zt - 1.25, zt]
	for k in range(2):
		lo, hi = ring(zs[k]), ring(zs[k + 1])
		kind = "chimney" if k == 0 else "brick"
		for i, (fname, au) in enumerate((("-y", X), ("+x", Y), ("+y", -X), ("-x", -Y))):
			isl = g.island("Stone", kind, pc.frame_of(lo[i], au, UP), Face=fname, Part="chimney")
			g.face("Stone", [lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i]], isl)
	cx = CHIM_X + 0.08
	obox(g, "Stone", "Stone", "chimney_cap", (cx, cy, zt + 0.17), X, Y, (2.3, 2.2, 0.34), Part="cap")
	obox(g, "Stone", "Stone", "chimney_cap", (cx, cy, zt + 0.47), X, Y, (1.6, 1.5, 0.26), Part="cap_top")
	cc.lathe(g, "Stone", "pot", cx + 0.25, cy + 0.1, zt + 0.6, [(0.0, 0.0), (0.42, 0.0), (0.36, 0.6), (0.3, 1.1), (0.4, 1.25), (0.42, 1.4), (0.3, 1.4)], segs=14)


# ---------------------------------------------------------------------------------------------------------------- the main block
def build_main(g, R):
	F, B = R["MAIN_F"], R["MAIN_B"]
	du = DOOR_U
	# plinth stones, a gap at the door
	stone_course(g, (XL - 0.5, YF), (XR, YF), 0.0, SILL0, 0.7, 1, normal=-Y, gaps=[(du - 2.0 - (XL - 0.5), du + 2.0 - (XL - 0.5))])
	stone_course(g, (XL, YB + 0.5), (XL, YF - 0.5), 0.0, SILL0, 0.7, 2, normal=-X)
	stone_course(g, (XR, YB), (XL - 0.5, YB), 0.0, SILL0, 0.7, 3, normal=Y)
	# the front wall: plaster up to the roof, the door's notch, the shuttered window
	top = [(x, roof_top((F,), x, YF, F1_1) - 0.35) for x in np.linspace(XR - 0.12, XL, 48)]
	top = [(XR, top[0][1])] + top
	notch = [(du - DOOR_W / 2, SILL0), (du - DOOR_W / 2, DOOR_V0 + DOOR_H), (du + DOOR_W / 2, DOOR_V0 + DOOR_H), (du + DOOR_W / 2, SILL0)]
	wall(g, "plaster", W_F, [(XL, SILL0)] + notch + [(XR, SILL0)] + top, holes=[win_hole(WIN_A, WIN0)], Block="Main", Side="front")
	square_window(g, W_F, WIN_A, WIN0, tilt=0.6, Win="front")
	for side in (-1, 1):
		shutter(g, W_F, WIN_A, WIN0, side)
	obox(g, "Joinery", "Joinery", "box", wpt(W_F, WIN_A, 3.25, 0.55), X, -Y, (3.5, 0.95, 0.8), Part="flower_box")
	for su in (-1, 1):
		beam(g, [wpt(W_F, WIN_A + su * 1.3, 2.7, 0.0), wpt(W_F, WIN_A + su * 1.3, 2.86, 0.85)], 0.2, 0.2, X, obj="Joinery", kind="iron", Part="box_bracket")
	plank_door(g, W_F, du)
	obox(g, "Stone", "Stone", "stone", (du, YF - 0.95, DOOR_V0 / 2), X, Y, (DOOR_W + 1.3, 1.9, DOOR_V0), Part="doorstep")
	# its frame: the corner post, the sill beam (broken by the door), the plate under the eave
	post(g, XL, YF, FOOT, F1_0, -1, -1, lean=(-0.05, 0.0))
	hbeam(g, W_F, XL - cc.PROUD, du - DOOR_W / 2 - 0.72, (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_F, du + DOOR_W / 2 + 0.72, XR, (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_F, XL - cc.PROUD, XR, (F1_0 + F1_1) / 2, F1_1 - F1_0, sag=0.06, Part="plate")
	# the left gable end: a plain window, the post at the back corner, sill and plate run round
	gtop = [(-y, roof_top((F, B), XL + 0.05, y, F1_1) - 0.35) for y in np.linspace(YF, YB, 40)]
	wall(g, "plaster", W_ML, [(-YB, SILL0), (-YF, SILL0)] + gtop, holes=[win_hole(-RIDGE_Y, WIN0)], Block="Main", Side="left")
	square_window(g, W_ML, -RIDGE_Y, WIN0, tilt=-0.5, Win="left")
	for side in (-1, 1):
		shutter(g, W_ML, -RIDGE_Y, WIN0, side, open_deg=10.0)
	post(g, XL, YB, FOOT, F1_0, -1, 1)
	hbeam(g, W_ML, -(YB + cc.PROUD), cc.PROUD, (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_ML, -(YB + cc.PROUD), cc.PROUD, (F1_0 + F1_1) / 2, F1_1 - F1_0, sag=0.04, Part="plate")
	# the back: plain for now
	btop = [(-x, roof_top((B,), x, YB, F1_1) - 0.35) for x in np.linspace(XL, XR - 0.12, 40)]
	btop.append((-XR, btop[-1][1]))
	wall(g, "plaster", W_MB, [(-XR, SILL0), (-XL, SILL0)] + btop, holes=[win_hole(-(WIN_A + 1.0), WIN0)], Block="Main", Side="back")
	square_window(g, W_MB, -(WIN_A + 1.0), WIN0, Win="back")
	hbeam(g, W_MB, -XR, -(XL - cc.PROUD), (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_MB, -XR, -(XL - cc.PROUD), (F1_0 + F1_1) / 2, F1_1 - F1_0, sag=0.05, Part="plate")
	# the roof: tiles round the dormer, the barges and ridge board at the left gable, a king block under the barges' crossing
	d = R["dormer"]
	box = (DORMER_X - d["half"] - 0.2, DORMER_X + d["half"] + 0.2, DORMER_Y - 0.25, 4.0)
	nf = lay_tiles(g, F, "RoofMain", seed=11, skip=lambda P: in_box(P, box), inside=True)
	nb = lay_tiles(g, B, "RoofMain", seed=12, inside=True)
	for s in (F, B):
		roof_skin(g, s, "RoofMain", na=40, nb=10)
		roof_edges(g, s, "RoofMain", sides=("eave",), n=40)
		roof_edges(g, s, "RoofMain", sides=("lo",), drop=VERGE_EDGE, n=24)
		barge(g, s, 0.0, -X, "MAIN", w=0.9, t=0.4, inset=0.3, drop=0.38, ext=0.3)
	ridge_beak(g, list(reversed(R["main_ridge"])), Y, "MAIN", beak=1.1, rise=0.35, w=0.9, t=0.55)
	king_block(g, F.at(0.0, 1.0) + X * 0.4, -X, w=0.62, h=1.3, d=0.55)
	# the porch: a post on a stone pad, a beam into the wing's corner post, one curved brace
	obox(g, "Stone", "Stone", "stone", (POST_X, POST_Y, 0.3), X, Y, (1.3, 1.3, 0.6), Part="pad")
	pz = 7.5
	beam(g, [(POST_X, POST_Y, 0.6), (POST_X + 0.04, POST_Y, 4.0), (POST_X, POST_Y, pz - 0.33)], 0.8, 0.8, Y, Part="porch_post", taper=(1.05, 0.97))
	beam(g, [(PORCH_X0, POST_Y, pz), ((PORCH_X0 + WX0) / 2, POST_Y, pz - 0.07), (WX0 - cc.PROUD, POST_Y, pz)], 0.66, 0.6, Y, Part="porch_beam")
	br = [(POST_X + 0.4 + (1.6 - 1.6 * math.cos(math.radians(t))), pz - 0.33 - 2.0 + 2.0 * math.sin(math.radians(t))) for t in np.linspace(0, 90, 10)]
	beam(g, [Vector((x, POST_Y, z)) for x, z in br], 0.44, 0.4, Y, Part="brace")
	chimney(g)
	build_dormer(g, R)
	print("[rose] main tiles", nf, nb, flush=True)


def build_dormer(g, R):
	d = R["dormer"]
	F = R["MAIN_F"]
	Wd = (Vector((0.0, DORMER_Y, 0.0)), X)
	x0, x1 = DORMER_X - d["half"], DORMER_X + d["half"]
	zs = d["zr"] - 0.6
	gt = [(x, roof_top((R["DM_L"], R["DM_R"]), x, DORMER_Y + 0.05, d["eave"]) - 0.3) for x in np.linspace(x1, x0, 24)]
	wall(g, "plaster", Wd, [(x0, zs), (x1, zs)] + gt, holes=[win_hole(DORMER_X, d["glass"], DORMER_W)], Block="Dormer")
	window(g, Wd, DORMER_X - DORMER_W / 2, DORMER_X + DORMER_W / 2, d["glass"], d["glass"] + DORMER_W, frame=0.36, ft=0.4, recess=0.3, bars=PANES, sill=(0.15, 0.45, 0.28), tilt=1.0, bar_w=0.12, Win="dormer")
	for sx, x_ in ((-1, x0), (1, x1)):
		cc.cheek(g, F, x_, sx, DORMER_Y, 4.2, zs, d["eave"], kind="plaster", Block="Dormer")
		wbeam(g, Wd, [(x_ - sx * 0.25, d["zr"] + 0.1), (x_ - sx * 0.25, d["eave"] - 0.05)], 0.5, 0.45, out=0.25, Part="post")
	for s, sd in ((R["DM_L"], 31), (R["DM_R"], 32)):
		lay_tiles(g, s, "RoofMain", tile_w=1.4, row=1.2, tile_len=1.8, thick=0.28, rest=0.14, seed=sd, inside=True)
		roof_skin(g, s, "RoofMain", na=6, nb=6)
		roof_edges(g, s, "RoofMain", sides=("eave",))
		roof_edges(g, s, "RoofMain", sides=("lo",), drop=VERGE_EDGE - 0.08)
		barge(g, s, 0.0, -Y, "DM", w=0.55, t=0.32, inset=0.2, drop=0.28, ext=0.35)
	ridge_beak(g, list(reversed(R["DM_L"].R)), X, "DM", beak=0.6, rise=0.2, w=0.6, t=0.4)


# ---------------------------------------------------------------------------------------------------------------- the wing
def build_wing(g, R):
	L, Rr = R["WING_L"], R["WING_R"]
	cx = WRIDGE_X
	stone_course(g, (WX0 - 0.5, WY_G), (WX1 + 0.5, WY_G), 0.0, SILL0, 0.7, 21, normal=-Y)
	stone_course(g, (WX1, WY_G - 0.5), (WX1, WY_B + 0.5), 0.0, SILL0, 0.7, 22, normal=X)
	stone_course(g, (WX1 + 0.5, WY_B), (WX0 - 0.5, WY_B), 0.0, SILL0, 0.7, 23, normal=Y)
	stone_course(g, (WX0, YF), (WX0, WY_G - 0.5), 0.0, SILL0, 0.7, 24, normal=-X)
	stone_course(g, (WX0, WY_B + 0.5), (WX0, YB), 0.0, SILL0, 0.7, 25, normal=-X)
	# ground floor front: one window centred, corner posts, sill, the floor beam the joists sit on
	wall(g, "plaster", W_WF, [(WX0, SILL0), (WX1, SILL0), (WX1, BR_0), (WX0, BR_0)], holes=[win_hole(cx, WIN0)], Block="Wing", Floor=0)
	square_window(g, W_WF, cx, WIN0, tilt=-0.5, Win="wing_low")
	post(g, WX0, WY_G, FOOT, F1_1, -1, -1, lean=(0.0, 0.04))
	post(g, WX1, WY_G, FOOT, F1_1, 1, -1, lean=(0.05, 0.0))
	hbeam(g, W_WF, WX0 - cc.PROUD, WX1 + cc.PROUD, (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_WF, WX0 - cc.PROUD + 0.9, WX1 + cc.PROUD - 0.9, (F1_0 + F1_1) / 2, F1_1 - F1_0, sag=0.05, Part="plate")
	# the jetty: joist ends out of the wall under the bressumer, the outer joists along both sides, boards under the overhang
	jz = (F1_1 + BR_0) / 2
	jh = BR_0 - F1_1
	for i in range(6):
		x = 3.3 + i * (9.7 - 3.3) / 5
		obox(g, "Timber", "Timber", "timber", (x, (WY_G + WY_U) / 2 - 0.12, jz), X, -Y, (0.46, 0.95, jh - 0.02), Part="joist", Width=0.46)
	for x_, W_, u0, u1 in ((WX0, W_WL, -(WY_G + 0.3), -(WY_U - 0.05)), (WX1, W_WR, WY_B + 0.3, WY_U - 0.05)):
		hbeam(g, W_, u0, u1, jz, jh - 0.02, out=cc.PROUD, Part="joist")
	sf = g.island("Timber", "soffit", pc.frame_of((WX0, WY_U, BR_0 - 0.01), X, Y), Face="jetty")
	g.face("Timber", [Vector((WX0 - 0.3, WY_U + 0.3, BR_0 - 0.01)), Vector((WX0 - 0.3, WY_G, BR_0 - 0.01)), Vector((WX1 + 0.3, WY_G, BR_0 - 0.01)), Vector((WX1 + 0.3, WY_U + 0.3, BR_0 - 0.01))], sf)
	hbeam(g, W_WU, WX0 - 0.45, WX1 + 0.45, (BR_0 + BR_1) / 2, BR_1 - BR_0, sag=0.07, Part="bressumer")
	# upper floor and gable: one window, the upper corner posts, two curved braces under the plate, the plate
	utop = [(x, roof_top((L, Rr), x, WY_U + 0.05, WP_1) - 0.35) for x in np.linspace(WX1, WX0, 40)]
	wall(g, "plaster", W_WU, [(WX0, BR_0), (WX1, BR_0)] + utop, holes=[win_hole(cx, WIN_U)], Block="Wing", Floor=1)
	square_window(g, W_WU, cx, WIN_U, tilt=0.7, Win="wing_up")
	post(g, WX0, WY_U, BR_1, WP_0, -1, -1, lean=(0.04, 0.0))
	post(g, WX1, WY_U, BR_1, WP_0, 1, -1, lean=(-0.04, 0.0))
	wbeam(g, W_WU, quarter((WX0 + cc.PROUD + 0.55, 16.0), (WX0 + 2.45, WP_0 - 0.22), bulge=0.6), 0.48, 0.42, out=0.24, Part="brace")
	wbeam(g, W_WU, quarter((WX1 - cc.PROUD - 0.55, 16.0), (WX1 - 2.45, WP_0 - 0.22), bulge=0.6), 0.48, 0.42, out=0.24, Part="brace")
	hbeam(g, W_WU, WX0 - 0.45, WX1 + 0.45, (WP_0 + WP_1) / 2, WP_1 - WP_0, sag=0.06, Part="plate")
	# the sides: the left one seen past the porch (plaster, the lantern, the plate under the eave), the right one plain
	ltop = [(-y, roof_top((L,), WX0 - 0.05, y, WP_1) - 0.35) for y in np.linspace(WY_U, WY_B, 40)]
	wall(g, "plaster", W_WL, [(-WY_B, SILL0), (-WY_G, SILL0), (-WY_G, BR_0), (-WY_U, BR_0)] + ltop, Block="Wing", Side="left")
	rtop = [(y, roof_top((Rr,), WX1 + 0.05, y, WP_1) - 0.35) for y in np.linspace(WY_B, WY_U, 40)]
	wall(g, "plaster", W_WR, [(WY_U, BR_0), (WY_G, BR_0), (WY_G, SILL0), (WY_B, SILL0)] + rtop, holes=[win_hole(3.5, WIN0), win_hole(3.5, WIN_U)], Block="Wing", Side="right")
	square_window(g, W_WR, 3.5, WIN0, Win="right_low")
	square_window(g, W_WR, 3.5, WIN_U, tilt=-0.6, Win="right_up")
	for W_, u0, u1 in ((W_WL, -(WY_G - cc.PROUD), 0.0), (W_WL, -YB, -(WY_B + cc.PROUD))):
		hbeam(g, W_, u0, u1, (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_WR, WY_G - cc.PROUD, WY_B + cc.PROUD, (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_WR, WY_G - cc.PROUD + 0.9, WY_B + cc.PROUD, (F1_0 + F1_1) / 2, F1_1 - F1_0, sag=0.05, Part="plate")
	hbeam(g, W_WL, -YB, -(WY_B + cc.PROUD), (F1_0 + F1_1) / 2, F1_1 - F1_0, Part="plate")
	hbeam(g, W_WL, -(WY_U - cc.PROUD), -(WY_B + cc.PROUD), (WP_0 + WP_1) / 2, WP_1 - WP_0, sag=0.06, Part="plate")
	hbeam(g, W_WR, WY_U - cc.PROUD, WY_B + cc.PROUD, (WP_0 + WP_1) / 2, WP_1 - WP_0, sag=0.06, Part="plate")
	wall_lantern(g, W_WL, 1.9, 5.6)
	# the back: plain gable, posts at its corners
	btop = [(-x, roof_top((L, Rr), x, WY_B - 0.05, WP_1) - 0.35) for x in np.linspace(WX0, WX1, 40)]
	wall(g, "plaster", W_WB, [(-WX1, SILL0), (-WX0, SILL0)] + btop, holes=[win_hole(-cx, WIN_U)], Block="Wing", Side="back")
	square_window(g, W_WB, -cx, WIN_U, Win="wing_back")
	for x_, sx in ((WX0, -1), (WX1, 1)):
		post(g, x_, WY_B, FOOT, F1_0, sx, 1)
		post(g, x_, WY_B, BR_0, WP_0, sx, 1)
	hbeam(g, W_WB, -(WX1 + cc.PROUD), -(WX0 - cc.PROUD), (SILL0 + FOOT) / 2, FOOT - SILL0, Part="sill")
	hbeam(g, W_WB, -(WX1 + cc.PROUD), -(WX0 - cc.PROUD), (F1_0 + F1_1) / 2, F1_1 - F1_0, sag=0.04, Part="plate")
	hbeam(g, W_WB, -(WX1 + 0.45), -(WX0 - 0.45), (WP_0 + WP_1) / 2, WP_1 - WP_0, sag=0.05, Part="plate")
	# the roof
	nl = lay_tiles(g, L, "RoofWing", seed=41, inside=True)
	nr = lay_tiles(g, Rr, "RoofWing", seed=42, inside=True)
	for s in (L, Rr):
		roof_skin(g, s, "RoofWing", na=18, nb=10)
		roof_edges(g, s, "RoofWing", sides=("eave",))
		roof_edges(g, s, "RoofWing", sides=("lo", "hi"), drop=VERGE_EDGE)
		barge(g, s, 0.0, -Y, "WING", w=1.0, t=0.44, inset=0.3, drop=0.4, ext=0.3)
		barge(g, s, 1.0, Y, "WING", w=1.0, t=0.44, inset=0.3, drop=0.4, ext=0.3)
	ridge_beak(g, list(reversed(R["wing_ridge"])), X, "WING", beak=1.3, rise=0.4, w=1.0, t=0.6)
	king_block(g, L.at(0.0, 1.0) + Y * 0.45, -Y, w=0.66, h=1.45, d=0.6)
	print("[rose] wing tiles", nl, nr, flush=True)


# ---------------------------------------------------------------------------------------------------------------- the garden
def ground(g):
	"""the study's rolling lawn, wider, so the far view stays on it"""
	x0, x1, y0, y1, cell = -170.0, 130.0, -170.0, 110.0, 5.0
	isl = g.island("Ground", "grass", pc.frame_of((0, 0, 0), X, Y), Face="+z")
	for i in range(int((x1 - x0) / cell)):
		for j in range(int((y1 - y0) / cell)):
			xa, xb, ya, yb = x0 + i * cell, x0 + (i + 1) * cell, y0 + j * cell, y0 + (j + 1) * cell
			q = [Vector((xa, ya, cc.ground_h(xa, ya))), Vector((xb, ya, cc.ground_h(xb, ya))), Vector((xb, yb, cc.ground_h(xb, yb))), Vector((xa, yb, cc.ground_h(xa, yb)))]
			g.face("Ground", q, isl, [(p.x, p.y) for p in q])


def sky_card(g):
	"""the painted sky card, sized from the far view (the widest), so every view along the hero's line sees only the card"""
	set_view("far")
	c = cc.EYE + cc.FWD * 520.0
	hw = 520.0 * math.tan(math.radians(VIEWS["far"]["FOV"]) / 2) * RES[0] / RES[1] * 1.5
	hh = 520.0 * math.tan(math.radians(VIEWS["far"]["FOV"]) / 2) * 1.6
	right, up = cc.RIGHTV, cc.UPV
	q = [c - right * hw - up * hh, c + right * hw - up * hh, c + right * hw + up * hh, c - right * hw + up * hh]
	isl = g.island("Sky", "sky", pc.frame_of(q[0], right, up), Face="sky", W=2 * hw, H=2 * hh)
	g.face("Sky", q if (q[1] - q[0]).cross(q[3] - q[0]).dot(-cc.FWD) > 0 else q[::-1], isl, [(0, 0), (2 * hw, 0), (2 * hw, 2 * hh), (0, 2 * hh)])
	set_view("hero")


def build_env(g):
	rnd = random.Random(3)
	ground(g)
	sky_card(g)
	# a stepping-stone path from the door out through the porch and across the lawn
	path = [Vector((DOOR_U + 0.1, -2.1, 0)), Vector((DOOR_U - 0.6, -5.6, 0)), Vector((-3.6, -9.2, 0)), Vector((-5.6, -12.8, 0)), Vector((-6.6, -16.5, 0)), Vector((-6.8, -20.4, 0)), Vector((-6.0, -24.4, 0))]
	for i, p in enumerate(path):
		cc.flagstone(g, p + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.2), 0)), rnd.uniform(1.15, 1.45), 300 + i, yaw=rnd.uniform(0, 40))
	cc.flagstone(g, Vector((POST_X + 1.6, -1.6, 0)), 1.0, 320, yaw=12)
	cc.flagstone(g, Vector((0.6, -2.3, 0)), 0.9, 321, yaw=30)
	# props: a barrel by the porch post, a crate and a pumpkin by the wing, a short fence at the left
	cc.barrel(g, cc.on_ground((XL - 1.7, 1.4, 0)), 1.0, 2.3, 51)
	cc.crate(g, cc.on_ground((WX1 + 1.9, WY_G + 1.1, 0)), (2.3, 2.0, 1.8), 14, 52)
	cc.pumpkin(g, cc.on_ground((WX1 + 1.2, WY_G - 1.3, 0)), 0.9, 61)
	cc.pumpkin(g, cc.on_ground((POST_X - 0.4, -4.6, 0)), 0.65, 62)
	cc.fence(g, cc.on_ground((-40.0, 2.0, 0)), cc.on_ground((-33.0, -4.0, 0)), 3.2, 41)
	cc.fence(g, cc.on_ground((-33.0, -4.0, 0)), cc.on_ground((-26.0, -7.5, 0)), 3.0, 42)
	cc.rock(g, Vector((-21.0, -2.0, -0.3)), (1.2, 1.0, 1.4), 31)
	cc.rock(g, Vector((15.0, -6.0, -0.3)), (0.8, 0.7, 0.7), 32)
	cc.lathe(g, "Props", "log", -14.9, -5.2, -0.1, [(0.0, 0.0), (0.85, 0.0), (0.78, 0.65), (0.0, 0.68)], segs=10)


def build_foliage():
	made = []
	rnd = random.Random(5)
	green = ("4f7a3e", "8db45a", "cfe08c")
	made += pc.cloud("BushLeft", [((XL - 2.2, -2.4, 1.3), (2.2, 1.7, 1.7)), ((XL - 2.9, 0.8, 1.0), (1.6, 1.4, 1.3))], 1.0, 91, green, card_tint="8db45a", cards_per=40, card_size=1.0)
	made += pc.cloud("BushWing", [((12.9, -1.2, 1.1), (1.7, 1.5, 1.5)), ((13.3, 1.6, 0.9), (1.3, 1.2, 1.2))], 0.95, 93, green, card_tint="8db45a", cards_per=36, card_size=0.95)
	made += pc.blob("BoxPlants", (WIN_A, YF - 0.62, 3.85), (1.75, 0.5, 0.5), 26, 0.34, 84, ("3e6a3a", "6e9a48", "aac86a"), up_lean=0.5, cards=60, card_size=0.5)
	made.append(pc.flowers("BoxFlowers", [Vector((WIN_A + rnd.uniform(-1.6, 1.6), YF - 0.6 + rnd.gauss(0, 0.2), 4.05 + rnd.random() * 0.4)) for _ in range(16)], "f08aa0", size=0.2, seed=71))
	# the rose that names the house, climbing the wing's side wall by the door
	made += pc.blob("RoseLeaves", (WX0 - 0.45, -0.75, 3.4), (0.42, 0.62, 3.0), 34, 0.36, 85, ("3e6a3a", "6e9a48", "aac86a"), up_lean=0.3, cards=60, card_size=0.55)
	made.append(pc.flowers("RoseFlowers", [Vector((WX0 - 0.72 + rnd.gauss(0, 0.1), -0.75 + rnd.gauss(0, 0.35), 0.9 + rnd.random() * 5.2)) for _ in range(24)], "e8708c", size=0.26, seed=72))
	made += pc.cloud("TreeBack", [((15.0, 24.0, 14.0), (5.6, 5.0, 6.0)), ((19.0, 28.0, 10.0), (4.5, 4.0, 4.5)), ((12.5, 22.0, 18.5), (3.4, 3.0, 3.0))], 1.7, 92, ("88aa70", "b8d290", "eaf0c4"), card_tint="b8d290", cards_per=56, card_size=1.5)
	made.append(cc.trunk("TrunkBack", (16.0, 26.0, -0.2), (15.5, 25.0, 10.0), 1.0, 0.7, 2))
	made += pc.cloud("TreeLeft", [((-30.0, 16.0, 11.0), (6.0, 5.0, 6.5)), ((-26.0, 20.0, 15.0), (4.4, 4.0, 4.2))], 2.0, 94, ("4a6e4c", "7a9c62", "bccc8a"), card_tint="7a9c62", cards_per=44, card_size=1.8)
	made.append(cc.trunk("TrunkLeft", (-29.0, 17.0, -0.4), (-29.5, 17.0, 8.0), 0.9, 0.6, 1))
	made += pc.cloud("TreeFar", [((-55.0, 60.0, 12.0), (12.0, 9.0, 9.0)), ((45.0, 70.0, 12.0), (11.0, 9.0, 9.0))], 3.0, 95, ("6c8a5c", "9cb47a", "d0dca2"), card_tint="9ab47a", cards_per=40, card_size=2.6)
	spots = []
	for x0, x1, y0, y1, n, k in ((XL - 1.0, WIN_A - 3.2, -1.0, -0.6, 5, 0.6), (WX0 + 0.5, WX1, WY_G - 1.0, WY_G - 0.6, 5, 0.6), (XL - 1.2, XL - 0.7, 0.5, YB, 6, 0.6), (-26.0, 14.0, -18.0, -7.0, 30, 0.95), (-40.0, -18.0, -8.0, 14.0, 16, 1.0)):
		for _ in range(n):
			spots.append((rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0.0, k * rnd.uniform(0.8, 1.2)))
	made.append(cc.grass_tufts("GrassTufts", spots, 7))
	made.append(pc.flowers("FlowersLawn", [Vector((rnd.uniform(-22, 10), rnd.uniform(-18, -8), 0.7 + rnd.random() * 0.4)) for _ in range(30)], "8aa6e8", size=0.22, seed=73))
	made.append(pc.flowers("FlowersBush", [Vector((XL - 2.2 + rnd.gauss(0, 1.2), -2.4 + rnd.gauss(0, 1.0), 1.6 + rnd.random() * 1.4)) for _ in range(18)], "f2f0f4", size=0.2, seed=74))
	for o in made:
		if o.name.endswith("Cards"):
			o["Tint"] = "c8d850"
		if o.name in pc.FOLIAGE_TINTS:
			o["Tint"] = pc.FOLIAGE_TINTS[o.name]
		elif "Tint" not in o.keys():
			o["Vcol"] = 1
	return made


# ---------------------------------------------------------------------------------------------------------------- the painter's hints
def brick_patches():
	"""where the render has fallen off and bricks show (centre, half width, half height, wall normal): low by the corner posts, where
	splash and knocks wear a wall, and once under the wing's eave; never mid-panel, where it reads as a sticker"""
	return [
		[[XL + 2.9, YF, 3.05], 1.35, 0.75, [0, -1, 0]],
		[[WX1 - 1.55, WY_G, 3.0], 1.1, 0.7, [0, -1, 0]],
		[[XL, YB - 2.0, 3.1], 1.3, 0.8, [-1, 0, 0]],
		[[WX1 - 1.7, WY_U, 20.3], 1.0, 0.6, [0, -1, 0]],
	]


def build():
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	cc.ROOFS.clear()
	cc.GROUP.clear()
	cc.SKIPS.clear()
	os.makedirs(OUT, exist_ok=True)
	set_view("hero")
	g = pc.Geo()
	R = define_roofs()
	build_main(g, R)
	build_wing(g, R)
	build_env(g)
	pc.WOBBLE = (0.12, 8.0)
	pc.WOBBLE_OBJS = ("Walls", "Timber", "Joinery", "Stone", "RoofMain", "RoofWing")
	pc.wobble(g)
	objs = pc.make_objects(g)
	print("[rose] tile skips", cc.SKIPS, flush=True)
	print("[rose] objects", [(o.name, len(o.data.polygons)) for o in objs], "faces", sum(len(o.data.polygons) for o in objs), "islands", len(g.islands), flush=True)
	pc.pack_and_bake(g, objs)
	made = build_foliage()
	print("[rose] foliage objects", len(made), "faces", sum(len(o.data.polygons) for o in made), flush=True)
	path = os.path.join(OUT, "layout.json")
	lay = json.load(open(path))
	lay["Consts"] = {
		# no brick patches or painted moss: on this clean plaster both read as stamps (brick_patches() kept for a weathered variant)
		"Bricks": [],
		"Moss": [],
		"Peach": [[[-11.5, 0.5, 11.6], 2.2], [[WRIDGE_X - 2.5, 4.0, 22.5], 2.0]],
	}
	json.dump(lay, open(path, "w"))
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "cottage.blend"))


def render():
	view = "hero"
	for a in ARGS:
		if a.startswith("--view="):
			view = a[7:]
	set_view(view)
	cc.SUN_DIR = (0.42, 0.62, -0.66)  # from the front-left, high: the front lit, the left gable end in soft light
	cc.render()


if __name__ == "__main__":
	os.makedirs(OUT, exist_ok=True)
	{"build": build, "render": render, "bake_ao": pc.bake_ao}[ARGS[0]]()
