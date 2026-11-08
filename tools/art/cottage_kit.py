"""The cottage (docs/style/art-style.md), system Python: chunky crooked geometry and four painted 1024 sheets, no Blender needed until export.
Wood uses the approved fence painter (tools/art/fence_kit.py, paint_strip); plaster, stone and tiles have their own painters here, in the same order:
firm planes in broad strokes, crisp marks, painted contact shadows, a sharpen pass, then soft cream highlights with their own rhythm.
Every vertex goes through warp(), so the walls, frame and roof lean and sag together.
Writes into art/kit/cottage: Cottage_<Frame|Joinery|Walls|Roof>.png, Cottage_Walls_Normal.png (stone relief), Cottage_<...>.obj, kit.json. Studs, y up, the door faces +z.

  python tools/art/cottage_kit.py art/kit/cottage
"""
import contextlib
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter, label

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/cottage")
os.makedirs(OUT, exist_ok=True)
# the fence painter, one source for the approved wood: fence_kit.py runs on import, so its source is loaded without the last line
_argv = sys.argv
sys.argv = ["fence_kit", OUT]
_src = open(os.path.join(HERE, "fence_kit.py"), encoding="utf-8").read()
# the fence's worn spots and wide glow were tuned for planks 1 to 1.4 studs wide; on 0.7-stud timbers they swallow the whole face and read as camouflage. Scaled here, and only here
for _old, _new in (
	("rng.uniform(2.2, 5.0) * w", "rng.uniform(0.9, 1.9) * w"),
	# the user, on the first cottage: way fewer edge highlights, strategic, not randomised. Each strip says where its highlights go (Beam.plan)
	("fade = gaussian_filter(fade, L / runs * 0.22)", "fade = EDGE_PLAN(i, L)"),
	("for _ in range(int(rng.integers(2, 4)) if upper >= 0.6 else 0):", "for cx_f, reach_f in EDGE_WORN(i):"),
	("cx = rng.uniform(0.08, 0.92) * L", "cx = cx_f * L"),
	("reach = rng.uniform(0.04, 0.11) * L", "reach = reach_f * L"),
	("gaussian_filter(high, (4.5 * SS, 10 * SS)) * 0.42", "gaussian_filter(high, (1.8 * SS, 16 * SS)) * 0.2"),
	("runs = max(4, int(length / 34))", "runs = max(3, int(length / 110))"),
):
	assert _old in _src, "fence_kit.py changed: " + _old
	_src = _src.replace(_old, _new)
FP = {"__name__": "fence_painter"}
exec(compile(_src[: _src.rindex("main()")], "fence_kit.py", "exec"), FP)
sys.argv = _argv


def _edge_plan(i, L):
	t = np.arange(L) / L
	out = np.zeros(L)
	for edge, f0, f1, amount in FP["GLINTS"]:
		if edge == i:
			taper = (f1 - f0) * 0.4  # always fades out, never stops dead
			win = np.clip((t - f0) / taper, 0, 1) * np.clip((f1 - t) / taper, 0, 1)
			out = np.maximum(out, win * win * (3 - 2 * win) * amount)
	return out


FP.update(EDGE_PLAN=_edge_plan, EDGE_WORN=lambda i: [(c, r) for e, c, r in FP["WORN"] if e == i], GLINTS=[], WORN=[])
paint_strip, paint_end, ss, smooth1d, over, stroke = (FP[k] for k in ("paint_strip", "paint_end", "ss", "smooth1d", "over", "stroke"))

SHEET = 1024
SS = 2
GRADE = np.array((1.3, 1.27, 1.12))  # the fence's Studio grade, until the cottage has its own reading
SEED = 41
PREFIX = "Cottage"  # other houses import this file as their kit (tools/art/townhouse_kit.py) and set their own name, warp, colours
BEAM_TAPER = 0.08  # how much each timber varies, end to end
SHUTTER_DROOP = 0.1
SHUTTER_OPEN = (0.16, 0.44)
# plaster, after the video study (research/ultimate_stylized): big painted shapes with a cause, not an even cream. All from their own random stream, so the rest of the paint stays put
PLASTER_PASS = 1.0  # all of the below; 0 leaves the plain wall
PLASTER_TOP = np.array((1.0, 1.0, 1.0))  # the plaster keeps its one colour: the user wanted only the streaks and darks to change
PLASTER_LOW = np.array((1.0, 1.0, 1.0))
PLASTER_GRAD = 0.8
STREAK_TINT = np.array((0.62, 0.66, 0.84))  # a cold blue-grey dark, multiplied. Streaks only ever darken: no highlights
STREAK_STRENGTH = 0.0  # the short drips under sills and beams: replaced by the accent gradient's fingers
ACCENT_DEEP = np.array((0.74, 0.72, 0.86))  # the plaster's accent, multiplied: a muted purple-blue at its deepest
ACCENT_LIGHT = np.array((0.8, 0.88, 0.88))  # falling to a muted green-blue as it fades
ACCENT_STRENGTH = 0.8
ACCENT_DEPTH = 0.37  # how far down a block it runs, as a share of the block's height
ACCENT_MAX_HEIGHT = 6.5  # studs: a tall gable doesn't get a longer fade than this
ACCENT_MIN_RUN = 2.5  # studs: nor a short wall a shorter one, or its eave shadow swallows the fade
ACCENT_CORNER = 0.4  # how much further it runs down near a block's corners
ACCENT_STROKE_WIDTH = (0.22, 0.75)  # studs
ACCENT_CLUSTER_SHARE = 55  # percent of a block's width that is clusters of colour, not streaks
ACCENT_CLUSTER_WIDTH = (1.1, 2.8)  # studs
ACCENT_CLUSTER_AMP = 0.45  # how much a cluster's edge bulges: big bulges read as round blobs
ACCENT_FINGER_FLOOR = 0.5  # the fingers' strength between the streak stretches
ACCENT_STREAK_PATCH = 0.75  # studs: the size of a stretch of streaks
ACCENT_LAYERS = ((0.45, 0.08, 0.6), (0.65, 0.13, 0.5), (0.85, 0.2, 0.42), (1.08, 0.3, 0.36))  # stacked washes: how far down, how uneven the lower edge, how soft its fade
STREAK_LENGTH = (0.6, 1.9)  # studs: short, every one of them
ROUGH_STRENGTH = 0.0  # pale edge marks read as streak highlights: off
STROKE_STRENGTH = 1.0  # plaster strokes' opacity
CRACK_DENSITY = 1.0
DIRT_STRENGTH = 0.0  # the old long rain runs: replaced by short placed streaks
FOOTING_CAST = 0.4  # studs of shadow on the stone, from a sill rail standing on it; 0 when there is no rail
STROKE_DENSITY = 1.0  # plaster's painted strokes; small walls may want fewer
TILE_ROUND = (0.17, 0.27)  # how round a tile's lower end is, as a share of its course
TILE_WIDTH = (1.5, 2.2)  # studs
TILE_SIDE = 0.6  # how dark the gap beside each tile is
TILE_PLANE = 0.16  # the painted plane on each tile
NORMAL_STRENGTH = 1.0  # stone relief: scales every slope in the normal map
PAINT_T = 50  # strips and planks are painted at the fence's own density, then shrunk onto the sheet, so grain and highlights keep their approved proportions

# the house, studs. Player 5.2, door 3.5 x 6.5, eave tip 1.7 players up
HX, HZ = 10.5, 6.0  # half footprint
FOOT_Y = 2.0
EAVE_Y, EAVE_Z = 9.6, 7.6
RIDGE_Y = 19.4
JET = 0.7  # the gable ends jut out over the walls
ROOF_X = HX + JET + 0.95
SLOPE = (RIDGE_Y - EAVE_Y) / EAVE_Z
DORMER_X = 5.5
CHIMNEY = (12.0, -2.6)  # outside the right gable, running from the ground

# wood colours: Chestnut from the fence; sage is its faded painted cousin for the door and shutters, clay for the ridge
SCHEMES = dict(FP["SCHEMES"])
SCHEMES["Sage"] = {"BASE": (96, 116, 104), "LIGHT": (104, 125, 112), "WARM": (106, 120, 100), "DUSK": (86, 104, 98), "COOL": (88, 108, 108), "GRAIN": (62, 76, 74)}
SCHEMES["Clay"] = {"BASE": (126, 74, 62), "LIGHT": (136, 82, 68), "WARM": (134, 76, 58), "DUSK": (112, 66, 62), "COOL": (114, 72, 70), "GRAIN": (84, 50, 50)}


def scheme(name):
	for k, v in SCHEMES[name].items():
		FP[k] = np.array(v, float)


EDGE = np.array((232, 206, 168), float)
EDGE_PALE = np.array((206, 170, 134), float)
# plaster: warm cream, shadows to rose-plum, cool strokes to lavender
PL_BASE = np.array((192, 180, 160), float)
PL_LIGHT = np.array((200, 190, 168), float)
PL_WARM = np.array((194, 174, 146), float)
PL_ROSE = np.array((182, 164, 150), float)
PL_COOL = np.array((174, 170, 162), float)
PL_SHADE = np.array((112, 88, 96), float)
PL_DEEP = np.array((84, 62, 76), float)
LATH = np.array((132, 92, 76), float)
LATH_DARK = np.array((92, 62, 62), float)
# stone: cool darks to warm lights, as the rock kit
ST_RAMP = [np.array(c, float) for c in ((86, 88, 102), (108, 108, 114), (130, 126, 122), (148, 142, 130))]
ST_OCHRE = np.array((136, 124, 100), float)
ST_SLATE = np.array((100, 106, 122), float)
ST_GAP = np.array((66, 58, 74), float)
MOSS_D = np.array((64, 110, 70), float)
MOSS_L = np.array((98, 148, 76), float)
# tiles: a muted terracotta, close together
TL_BASE = np.array((122, 76, 66), float)
TL_WARM = np.array((127, 78, 64), float)
TL_ROSE = np.array((116, 73, 70), float)
TL_DUSK = np.array((106, 69, 69), float)
TL_LIGHT = np.array((133, 87, 74), float)
TL_GAP = np.array((72, 48, 58), float)
TL_SHADOW = np.array((86, 56, 62), float)
SOFFIT = np.array((58, 42, 56), float)
IRON = np.array((60, 58, 74), float)


# ---- the darkening and framing pass (Ghibli, anime): the props' recipe. Colour moves with light (gold lit, plum under), multiplied so the paint's marks stay;
# shadows are clean hand-cut shapes painted over the paint, not fades. Own random stream, so tuning this never moves the paint
LIT_TINT = np.array((1.07, 1.03, 0.9))
UNDER_TINT = np.array((0.76, 0.67, 0.76))
SHADE_TINT = np.array((0.7, 0.6, 0.74))
SHADE_RNG = np.random.default_rng(29)
PLASTER_VALUE = 0.9  # down from a glare to a warm cream
STONE_VALUE = 1.0  # lifted after the Studio reading: its light took the stone far darker and bluer than Blender
WALL_SHADE_TINT = np.array((0.74, 0.76, 0.88))  # the plaster's shadow shapes: Studio's cool sky pushed the props' plum to vivid purple on a pale wall
TILE_VALUE = 0.95
GREEN_TINT = np.array((0.5, 0.68, 0.88))  # the door and shutters' accent, multiplied: a rich cold teal-blue, darkest at the top
GREEN_STRENGTH = 0.9
GREEN_POWER = 1.3


def green_light(f):
	"""multiplier for the green wood, f = 0 at the top of the door or shutter and 1 at its foot"""
	return 1 + (GREEN_TINT - 1) * (np.clip(1 - f, 0, 1) ** GREEN_POWER * GREEN_STRENGTH)[..., None]


GREEN_STREAK_REACH = (0.5, 1.3)  # how far down each finger of the gradient runs, as a share of the panel. Around 1, so the overall shape holds
GREEN_STREAK_WIDTH = (0.12, 0.42)  # studs


def streak_reach(W, S, g, width, length):
	"""how far each column's stroke runs: strokes of uneven width and length, each tapering to a point"""
	reach = np.ones(W, np.float32)
	x = -g.uniform(0, 0.2) * S
	while x < W:
		w = g.uniform(*width) * S
		r = g.uniform(*length)
		a, b = max(int(x), 0), min(int(x + w) + 1, W)
		if b > a:
			c = np.linspace(-1, 1, b - a)
			reach[a:b] = r * (1 - 0.3 * c**2)
		x += w
	return reach


def green_streaked(H, W, g):
	"""the green wood's gradient, broken into streaks: solid at the top, its lower edge falling in tapered fingers of uneven length, each one its own fade. H and W are painted pixels"""
	S = JOIN.T * SS
	reach = streak_reach(W, S, g, GREEN_STREAK_WIDTH, GREEN_STREAK_REACH)
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	wob = smooth1d(H, max(H // 3, 6), g)[:, None] * 0.05 * S  # the strokes wander a little
	col = np.clip(xx + wob, 0, W - 1).astype(int)
	amount = np.clip(1 - (yy / H) / reach[col], 0, 1) ** GREEN_POWER * GREEN_STRENGTH
	amount = gaussian_filter(amount.astype(np.float32), (0.05 * S, 0.012 * S + 0.4))  # soft down the stroke, firm across it
	return 1 + (GREEN_TINT - 1) * amount[..., None]


RICH_TINT = np.array((0.66, 0.5, 0.47))  # the deep brown the wood falls to, multiplied: warmer than plum
WOOD_RICH = 1.0  # the whole gradient and contact pass; 0 leaves plain wood
RICH_START = 0.62  # where on a face, from the top, the fall begins. Higher up, a flat board rounds off like a log
RICH_UNDER = 0.22  # each timber's own fall stays faint: stacked individual gradients read as clutter
RICH_ENDS = 0.28
GRAD_STRENGTH = 0.95  # the house's one gradient, the main shape: rich at the top, the base colour low down
GRAD_Y = (2.5, 19.0)  # studs: where it starts and where it is full
GRAD_POWER = 1.15
RICH_REACH = 0.6  # studs: how far the dark runs in from a timber's ends
FRAME_TINT = np.array((1.0, 1.0, 1.0))  # the user, on the darkening pass: wood back to normal, too detailed and dark
JOINERY_TINT = np.array((1.0, 1.0, 1.0))  # window frames and small pieces in Chestnut
# two tests, off by default so every house paints as approved. HOUSE_FORM_FIT=1: grain stays stud-sized on long timbers and end grain is cut to each timber's shape (the wooden bridges' method).
# HOUSE_RIM=1, with a house setting RIM: the house framed like a picture, a darker, richer outer rim in the paint, and the middle left light
FORM_FIT = os.environ.get("HOUSE_FORM_FIT") == "1"
GRAIN_QUIET = 0.72  # the marks' strength on long timbers: the user found the first strength ugly on the pale low wood
GRAIN_REF = 5.0  # studs: past this, marks stay the size they'd be on a timber this long
RIM = None  # dict(hx, z0, z1): the outer box of the walls; the front and back can differ, as on a jettied house
# the user, on the first try where whole timbers changed colour: "just the edges", it "should fade in and be more subtle". So only a timber's outer edge takes it, fading out across the face
RIM_TINT = np.array((0.74, 0.56, 0.48))  # deep red-brown, multiplied, at the very edge
RIM_POST_REACH = 0.62  # studs: across a corner post, from its outer edge. Wide and soft: narrow read as a dark stripe on the pale low wood
RIM_POST_STRENGTH = 0.6
RIM_BEAM_REACH = 0.9  # studs: along a long beam, in from the outer corner
RIM_BARGE_REACH = 0.24  # studs: down a barge board from its upper edge
RIM_FLOOR = np.array((0.5, 0.33, 0.28))  # the rim and the house's own gradient together never go darker than this
RIM_REACH = 3.0  # studs along a wall from the outer corner
RIM_ROOF_TINT = np.array((0.8, 0.68, 0.6))  # a deeper version of the roof's own colour
RIM_ROOF_SIDE, RIM_ROOF_EAVE = 0.8, 0.9  # studs in from a gable edge, and up from the eave
RIM_PLASTER_TINT = np.array((0.93, 0.95, 0.99))  # faint and cool
RIM_PLASTER_REACH = 1.2
EAVE_DEPTH = 1.75  # studs of the eave's cast shadow below its line on the long walls
for _c in (PL_BASE, PL_LIGHT, PL_WARM, PL_ROSE, PL_COOL):
	_c *= PLASTER_VALUE
for _c in ST_RAMP + [ST_OCHRE, ST_SLATE]:
	_c *= STONE_VALUE
for _c in (TL_BASE, TL_WARM, TL_ROSE, TL_DUSK, TL_LIGHT):
	_c *= TILE_VALUE


def darken(t, strength=1.0):
	"""multiplier for t, 0 at the lit top of a surface and 1 at its underside"""
	t = np.clip(t, 0, 1)[..., None]
	return 1 + ((LIT_TINT - 1) * (1 - t) ** 1.5 + (UNDER_TINT - 1) * t**1.3) * strength


def cut_edge(n, base, amp, knots):
	"""a hand-cut line: straight runs between a few points, rather than noise"""
	return np.interp(np.arange(n), np.linspace(0, n, max(knots, 2)), base + SHADE_RNG.uniform(-amp, amp, max(knots, 2)))


def shade(img, mask, amount=1.0, tint=None):
	m = gaussian_filter(mask.astype(np.float32), 0.45 * SS)[..., None] * amount
	return img * (1 - m * (1 - (SHADE_TINT if tint is None else tint)))


def rim_corner(points, reach=None):
	"""how near the points are to the house's outer vertical corners, 1 at a corner and fading along the wall. Timbers standing outside the walls, the gable's barge boards, are all rim"""
	points = np.atleast_2d(points)
	dx, dz = RIM["hx"] - np.abs(points[:, 0]), np.minimum(points[:, 2] - RIM["z0"], RIM["z1"] - points[:, 2])
	d = np.maximum(np.maximum(dx, dz), 0)
	r = np.exp(-((d / (reach or RIM_REACH)) ** 1.5))
	return np.where((dx < -0.4) | (dz < -0.4), 1.0, r)


def rim_roof(img, S):
	"""the roof's gable edges and eave, in a deeper version of its own colour, with an edge that wanders a little rather than a ruled line"""
	H, W = img.shape[:2]
	g = np.random.default_rng(H * 7919 + W)  # its own stream: this can't move anything else
	wander_u = gaussian_filter(g.normal(0, 1, H), S * 0.5, mode="wrap")
	wander_v = gaussian_filter(g.normal(0, 1, W), S * 0.7, mode="wrap")
	du = (np.minimum(np.arange(W), np.arange(W)[::-1]) / S)[None, :] + (wander_u / (wander_u.std() + 1e-6) * 0.22)[:, None]
	dv = (np.arange(H)[::-1] / S)[:, None] + (wander_v / (wander_v.std() + 1e-6) * 0.25)[None, :]
	side = np.exp(-(np.clip(du, 0, None) / RIM_ROOF_SIDE) ** 1.6)
	eave = np.exp(-(np.clip(dv, 0, None) / RIM_ROOF_EAVE) ** 1.6) * 0.85
	m = np.maximum(side, eave)[..., None]
	return img * (1 + (RIM_ROOF_TINT - 1) * m)


def wood_light(img, bands, tint, length_px, rich=False, world_y=None):
	"""per face, gently: the under side a little plum, the front barely graded. rich adds the deeper brown: mostly the whole house's top-to-bottom gradient, from each timber's height (world_y, along its length),
	then a faint fall on each face, its under side and its ends"""
	y = 0
	for px, kind in bands:
		h = px * SS
		t = (np.arange(h) + 0.5) / h
		if kind == "bottom":
			img[y : y + h] *= 1 + (UNDER_TINT - 1) * 0.5
			if rich:
				img[y : y + h] *= 1 + (RICH_TINT - 1) * RICH_UNDER * WOOD_RICH
		elif kind == "front":
			img[y : y + h] *= darken(t, 0.2)[:, None, :]
			if rich:
				fall = np.clip((t - RICH_START) / (1 - RICH_START), 0, 1) ** 1.4
				img[y : y + h] *= (1 + (RICH_TINT - 1) * (fall * RICH_UNDER * WOOD_RICH)[..., None])[:, None, :]
		y += h
	if rich:
		L = img.shape[1]
		x = np.arange(L, dtype=np.float32) / (PAINT_T * SS)  # studs from the start
		reach = min(RICH_REACH, x[-1] * 0.22)
		ends = np.exp(-((np.minimum(x, x[::-1]) / reach) ** 1.5)) * RICH_ENDS * WOOD_RICH
		img = img * (1 + (RICH_TINT - 1)[None, None, :] * ends[None, :, None])
	if rich and world_y is not None:
		g = np.clip((world_y - GRAD_Y[0]) / (GRAD_Y[1] - GRAD_Y[0]), 0, 1) ** GRAD_POWER * GRAD_STRENGTH
		img = img * (1 + (RICH_TINT - 1)[None, None, :] * g[None, :, None])
	return img * tint


def unit(v):
	v = np.array(v, float)
	return v / (np.linalg.norm(v) + 1e-9)


def warp(p):
	"""the whole house is one crooked object: leans, the ridge sags, one end has settled, the eaves droop in the middle"""
	x, y, z = p
	yc = max(y, 0.0)
	wave = math.cos(min(abs(x) / (ROOF_X + 0.5), 1) * math.pi / 2) ** 2
	rise = min(max((y - EAVE_Y) / (RIDGE_Y - EAVE_Y), 0), 1.3)
	dx = 0.024 * yc + 0.07 * math.sin(yc * 0.45)
	dz = 0.016 * yc + 0.11 * math.sin(x * 0.33 + 0.6) * min(yc / 9, 1)
	dy = -0.62 * rise * wave + 0.022 * x * min(yc / 9, 1) - 0.24 * wave * min(max((abs(z) - HZ) / 1.6, 0), 1)
	return (x + dx, y + dy, z + dz)


class Rect:
	"""a place on a sheet, sized in studs or by a function of the sheet's texel density; painted after packing"""

	def __init__(self, size, paint=None):
		self.size = size if callable(size) else (lambda T, s=size: (max(int(s[0] * T), 4), max(int(s[1] * T), 4)))
		self.paint = paint
		self.x = self.y = self.w = self.h = 0


TAGS = {"glass": [], "sage": [], "stone": []}  # which rects on the sheets hold what: tools/art/house_looks.py recolours by these
HEIGHT = None  # left by a painter that wants relief, in studs, the size of its rect


def normals_from(h, S):
	"""tangent-space normals from a height in studs, S pixels per stud. OpenGL style (+Y up the texture), as Roblox and glTF expect; texture rows run downward"""
	gy, gx = np.gradient(h)
	n = np.stack((-gx * S * NORMAL_STRENGTH, gy * S * NORMAL_STRENGTH, np.ones(h.shape, np.float32)), axis=2)
	n /= np.linalg.norm(n, axis=2, keepdims=True)
	return (n * 0.5 + 0.5) * 255


class Atlas:
	def __init__(self, name, gap=6):
		self.name, self.rects, self.gap, self.T = name, [], gap, 0

	def add(self, size, paint=None):
		r = Rect(size, paint)
		self.rects.append(r)
		return r

	def fit(self, T):
		order = sorted(self.rects, key=lambda r: -r.size(T)[1])
		x = y = self.gap
		row = 0
		for r in order:
			w, h = r.size(T)
			if w + 2 * self.gap > SHEET:
				return False
			if x + w + self.gap > SHEET:
				x, y, row = self.gap, y + row + self.gap, 0
			if y + h + self.gap > SHEET:
				return False
			r.x, r.y, r.w, r.h = x, y, w, h
			x += w + self.gap
			row = max(row, h)
		self.used = y + row
		return True

	def pack(self, start=60.0):
		T = start
		while not self.fit(T):
			T -= 0.5
			if T < 8:
				raise RuntimeError("sheet full: " + self.name)
		self.T = T

	def paint(self, base):
		global HEIGHT
		img = np.zeros((SHEET * SS, SHEET * SS, 3), float)
		img[:] = base
		self.normal = None
		for r in self.rects:
			if r.paint:
				HEIGHT = None
				part = r.paint(r)
				img[r.y * SS : (r.y + r.h) * SS, r.x * SS : (r.x + r.w) * SS] = part
				if HEIGHT is not None:
					if self.normal is None:
						self.normal = np.zeros((SHEET * SS, SHEET * SS, 3), np.float32)
						self.normal[:] = (127.5, 127.5, 255)  # flat
					self.normal[r.y * SS : (r.y + r.h) * SS, r.x * SS : (r.x + r.w) * SS] = normals_from(HEIGHT, self.T * SS)
		return img


class Mesh:
	def __init__(self, name, atlas):
		self.name, self.atlas = name, atlas
		self.v, self.vn, self.uv, self.tris, self.group, self.vg = [], None, [], [], [], []
		self.next = 0
		self.closed = []

	def new_group(self):
		self.next += 1
		return self.next

	def tri(self, q, uv, out, group, vg=None):
		vg = vg or (group, group, group)
		a, b, c = [np.array(p, float) for p in q]
		n = np.cross(b - a, c - a)
		if np.linalg.norm(n) < 1e-7:
			return
		if np.dot(n, out) < 0:
			q = (q[0], q[2], q[1])
			uv = (uv[0], uv[2], uv[1])
			vg = (vg[0], vg[2], vg[1])
		i = len(self.v)
		for p, t, g in zip(q, uv, vg):
			self.v.append(warp(p))
			self.uv.append(t)
			self.vg.append(g)
		self.tris.append((i, i + 1, i + 2))
		self.group.append(group)

	def quad(self, q, uv, out, group=0, vg=None):
		"""vg: per-corner normal groups, for a corner band that takes its normals from the two faces beside it"""
		vg = vg or (group, group, group, group)
		self.tri((q[0], q[1], q[2]), (uv[0], uv[1], uv[2]), out, group, (vg[0], vg[1], vg[2]))
		self.tri((q[0], q[2], q[3]), (uv[0], uv[2], uv[3]), out, group, (vg[0], vg[2], vg[3]))

	def finish(self):
		v = np.array(self.v)
		acc = {}
		fn = []
		for (i, j, k), g in zip(self.tris, self.group):
			n = np.cross(v[j] - v[i], v[k] - v[i])
			fn.append(n)
			if g:
				for m in (i, j, k):
					key = (g, round(v[m][0], 3), round(v[m][1], 3), round(v[m][2], 3))
					acc[key] = acc.get(key, 0) + n
		self.vn = [None] * len(v)
		for (i, j, k), g, n in zip(self.tris, self.group, fn):
			for m in (i, j, k):
				a = acc.get((self.vg[m], round(v[m][0], 3), round(v[m][1], 3), round(v[m][2], 3)), n)
				self.vn[m] = a / (np.linalg.norm(a) + 1e-9)
		# closed parts, wound outward, have positive volume: anything else shows inside out in Roblox
		for name, t0, t1 in self.closed:
			c = v[[m for t in self.tris[t0:t1] for m in t]].mean(axis=0)
			vol = sum(np.dot(v[i] - c, np.cross(v[j] - c, v[k] - c)) for i, j, k in self.tris[t0:t1]) / 6
			assert vol > 0, f"{self.name}: {name} is inside out (volume {vol:.3f})"

	def write(self, folder):
		lines = [f"o {self.name}"]
		f = []
		for (i, j, k) in self.tris:
			for m in (i, j, k):
				lines.append("v %.4f %.4f %.4f" % tuple(self.v[m]))
				lines.append("vt %.5f %.5f" % (self.uv[m][0] / SHEET, 1 - self.uv[m][1] / SHEET))
				lines.append("vn %.4f %.4f %.4f" % tuple(self.vn[m]))
		for n in range(len(self.tris)):
			a = n * 3 + 1
			f.append(f"f {a}/{a}/{a} {a + 1}/{a + 1}/{a + 1} {a + 2}/{a + 2}/{a + 2}")
		open(os.path.join(folder, self.name + ".obj"), "w").write("\n".join(lines + f) + "\n")


WOOD = Atlas("Frame")  # the long timbers
JOIN = Atlas("Joinery")  # door, windows, shutters, braces, all the short pieces
WALL = Atlas("Walls")
ROOF = Atlas("Roof")
MW, MJ, ML, MR = Mesh("Cottage_Frame", WOOD), Mesh("Cottage_Joinery", JOIN), Mesh("Cottage_Walls", WALL), Mesh("Cottage_Roof", ROOF)
SHORT = 5.6  # studs: shorter beams go on the joinery sheet
emit = []  # geometry that needs its rect's place on the sheet, run after packing
rng = np.random.default_rng(SEED)


def child():
	return np.random.default_rng(int(rng.integers(1 << 31)))


def shrink(img, w, h):
	small = np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), float)
	return np.clip(small + (small - gaussian_filter(small, (1.2 * SS, 1.2 * SS, 0))) * 0.3, 0, 255)


# ---------------------------------------------------------------- end grain, soot
def paint_grain_end(r):
	scheme("Chestnut")
	g = child()
	img = paint_end(r.w, g)
	return np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((r.w * SS, r.h * SS), Image.BILINEAR), float)


END_CAPS = {a.name: [a.add((0.9, 0.9), paint_grain_end) for _ in range(3)] for a in (WOOD, JOIN)}
END_FIT = {}


def paint_end_fit(r, w, h, g):
	"""end grain cut to one timber's shape: rings at a fixed spacing in studs, cropped by the end rather than squashed onto it"""
	scheme("Chestnut")
	H, W = r.h * SS, r.w * SS
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	stud = W / h
	cx, cy = W * g.uniform(0.35, 0.65), H * (g.uniform(0.35, 0.65) if min(w, h) > 0.7 else g.uniform(1.5, 2.5))
	d = np.hypot(xx - cx, yy - cy) / stud + np.sin(np.arctan2(yy - cy, xx - cx) * 5) * 0.012
	img = np.zeros((H, W, 3), float) + FP["LIGHT"] * 1.02
	ring = np.abs((d / 0.2) % 1 - 0.5) < 0.09
	return over(img, FP["DUSK"] * 1.02, gaussian_filter(ring.astype(np.float32), 0.35 * SS) * 0.7)


def paint_soot(r):
	img = np.zeros((r.h * SS, r.w * SS, 3))
	img[:] = PL_DEEP * 0.72
	return img


SOOT = JOIN.add((0.3, 0.3), paint_soot)


# ---------------------------------------------------------------- beams
class Strip:
	def __init__(self, length, w, h, ch, name):
		self.length, self.w, self.h, self.ch, self.name = length, w, h, ch, name
		self.atlas = JOIN if length <= SHORT else WOOD
		self.uses = 0
		self.contacts, self.foot, self.nails, self.knots, self.hidden_back = [], False, (), 1, True
		self.glints, self.worn = [], []
		self.rect = self.atlas.add(self.px, self.paint)

	def sect(self):
		w, h, ch = self.w, self.h, self.ch
		pts = [(-w / 2 + ch, h / 2), (w / 2 - ch, h / 2), (w / 2, h / 2 - ch), (w / 2, -h / 2 + ch), (w / 2 - ch, -h / 2), (-w / 2 + ch, -h / 2), (-w / 2, -h / 2 + ch), (-w / 2, h / 2 - ch)]
		return pts, ["top", "edge", "front", "edge", "bottom", "edge", "back", "edge"]

	def bands(self, T):
		pts, kinds = self.sect()
		out = []
		for i, k in enumerate(kinds):
			d = math.dist(pts[i], pts[(i + 1) % 8])
			px = max(4 if k == "edge" else 6, int(round(d * T)))
			if k == "back" and self.hidden_back:
				px = 4
			out.append((px, k))
		return out

	def px(self, T):
		return max(int(self.length * T), 8), sum(b[0] for b in self.bands(T))

	def paint(self, r):
		scheme(self.name)
		FP["GLINTS"], FP["WORN"] = self.glints, self.worn
		F = PAINT_T / self.atlas.T
		cs = [(c, max(h * PAINT_T * 0.42, 6)) for c, h in self.contacts]
		bands = [(max(int(round(px * F)), 3), k) for px, k in self.bands(self.atlas.T)]
		img = paint_strip(int(r.w * F), bands, child(), cs, self.foot, self.knots, self.nails)
		if self.name == "Chestnut":
			world_y = np.linspace(self.owner.p0[1], self.owner.p1[1], img.shape[1])
			img = wood_light(img, bands, FRAME_TINT if self.atlas is WOOD else JOINERY_TINT, r.w, rich=True, world_y=world_y)
			if RIM:
				R = self.owner.rim_map(bands, img.shape[1])[..., None]
				g = np.clip((world_y - GRAD_Y[0]) / (GRAD_Y[1] - GRAD_Y[0]), 0, 1) ** GRAD_POWER * GRAD_STRENGTH
				gm = 1 + (RICH_TINT - 1)[None, :] * g[:, None]
				img = img * np.maximum(1 + (RIM_TINT - 1)[None, None, :] * R, (RIM_FLOOR[None, :] / gm)[None, ...])
		else:
			img = wood_light(img, bands, np.ones(3), r.w)
			if self.name == "Sage" and self.owner.panel:
				bot, top = self.owner.panel
				img = img * green_light(np.array((top - self.owner.p0[1]) / (top - bot)))[None, None, :]
		return shrink(img, r.w * SS, r.h * SS)


STRIPS = []


class Beam:
	"""p0 to p1, chamfered, tapered and wandering, unrolled into a strip. local z is `front`: the painted front face looks that way"""

	def __init__(self, p0, p1, front, w, h, ch=0.09, scheme_name="Chestnut", face=None, unique=False, foot=False, knots=1, nails=(), bend=0.03, hidden_back=True, rings=None, mesh=None, cap_top=None, hero=False, panel=None):
		self.p0, self.p1, self.front = np.array(p0, float), np.array(p1, float), np.array(front, float)
		self.w, self.h, self.ch, self.scheme = w, h, ch, scheme_name
		self.L = float(np.linalg.norm(self.p1 - self.p0))
		self.face, self.unique, self.foot, self.knots, self.nails, self.bend, self.hidden_back, self.rings = face, unique, foot, knots, nails, bend, hidden_back, rings
		self.strip = None
		self.mesh = mesh
		self.cap_top = cap_top
		self.hero = hero
		self.panel = panel  # for green rails: the height range of the shutter they sit on
		BEAMS.append(self)

	def rim_map(self, bands, L):
		"""the rim per painted texel, from where each texel really is: rows run round the timber's section, columns along it. A post takes it on its outer edge, a long beam only near the corner, a barge board along its upper edge"""
		ax = unit(self.p1 - self.p0)
		az = unit(self.front - ax * np.dot(self.front, ax))
		ay = np.cross(az, ax)
		pts, _ = self.strip.sect()
		ab = []
		for i, (px, _k) in enumerate(bands):
			t = (np.arange(px * SS) + 0.5)[:, None] / (px * SS)
			ab.append(np.array(pts[i]) * (1 - t) + np.array(pts[(i + 1) % 8]) * t)
		ab = np.concatenate(ab)
		off = ay[None, :] * ab[:, 1:2] + az[None, :] * ab[:, 0:1]  # rows, 3
		f = (np.arange(L) + 0.5) / L
		along = self.p0[None, :] + f[:, None] * (self.p1 - self.p0)[None, :]  # columns, 3
		x = along[:, 0][None, :] + off[:, 0:1]
		z = along[:, 2][None, :] + off[:, 2:3]
		y_off = off[:, 1:2]
		dx, dz = RIM["hx"] - np.abs(x), np.minimum(z - RIM["z0"], RIM["z1"] - z)
		d = np.maximum(np.maximum(dx, dz), 0)
		up = abs(ax[1])
		if 0.2 < up < 0.97 and dx.mean() < -0.4:  # a barge board
			d, reach = np.tile(y_off.max() - y_off, (1, L)), RIM_BARGE_REACH
		else:
			reach = RIM_POST_REACH if up >= 0.97 else RIM_BEAM_REACH
		return np.exp(-((d / reach) ** 2)) * (RIM_POST_STRENGTH if up >= 0.97 else 1.0)

	def rim_touched(self):
		"""does the rim reach this timber at all? Then it keeps its own paint: the mark depends on which corner it is"""
		pts = self.p0 + np.linspace(0, 1, 9)[:, None] * (self.p1 - self.p0)
		dx, dz = RIM["hx"] - np.abs(pts[:, 0]), np.minimum(pts[:, 2] - RIM["z0"], RIM["z1"] - pts[:, 2])
		return bool((np.maximum(np.maximum(dx, dz), 0) < 1.6).any() or dx.mean() < -0.4)

	def plan(self):
		"""where this timber's highlights go. Edge 1 is the lit upper edge. Hero timbers (one door post, the lintel, window sills, barge boards) carry one run;
		everything else none. Returns (glints, worn spots)"""
		if not self.hero or self.L < 1.6:
			return [], []
		up = abs(unit(self.p1 - self.p0)[1])
		if up > 0.8:
			return [(1, 0.68, 0.96, 0.7)], []
		if up > 0.35:
			return [(1, 0.06, 0.32, 0.6)], []
		return [(1, 0.03, 0.34, 0.75)], []

	def assign(self):
		for s in STRIPS:
			if self.unique or s.name != self.scheme or s.uses >= 6 or s.hidden_back != self.hidden_back or (s.length <= SHORT) != (self.L <= SHORT):
				continue
			if self.scheme == "Sage" and self.panel and abs((self.panel[1] - self.p0[1]) - (s.owner.panel[1] - s.owner.p0[1])) > 0.3:
				continue
			if self.scheme == "Chestnut" and (abs(s.owner.p0[1] - self.p0[1]) > 0.8 or abs(s.owner.p1[1] - self.p1[1]) > 0.8):
				continue
			if RIM and self.scheme == "Chestnut" and (self.rim_touched() or s.owner.rim_touched()):
				continue
			if abs(s.w - self.w) < 0.06 and abs(s.h - self.h) < 0.06 and self.L <= s.length <= self.L + 1.6:
				self.strip = s
				s.uses += 1
				break
		if self.strip is None:
			self.strip = Strip(self.L, self.w, self.h, self.ch, self.scheme)
			self.strip.hidden_back = self.hidden_back
			self.strip.foot, self.strip.knots, self.strip.nails = self.foot, (self.knots if self.hero else 0), self.nails
			self.strip.glints, self.strip.worn = self.plan()
			self.strip.uses = 1
			self.strip.owner = self
			STRIPS.append(self.strip)
		self.strip_shift = rng.uniform(0, max(self.strip.length - self.L, 0))

	def build(self):
		s = self.strip
		r = s.rect
		T = s.atlas.T
		self.mesh = MJ if s.atlas is JOIN else MW
		rows = [r.y]
		for px, _k in s.bands(T):
			rows.append(rows[-1] + px)
		pts, _ = s.sect()
		ax = unit(self.p1 - self.p0)
		az = unit(self.front - ax * np.dot(self.front, ax))
		ay = np.cross(az, ax)
		n = self.rings or 2 + int(self.L / 4.5)
		g = np.random.default_rng(int(rng.integers(1 << 31)))
		wob = g.normal(0, 1, (n, 2)) * self.bend
		taper = 1 + g.uniform(-BEAM_TAPER, BEAM_TAPER, 2)
		ring = []
		for i in range(n):
			f = i / (n - 1)
			sc = taper[0] + (taper[1] - taper[0]) * f
			jit = g.normal(0, 0.01, (8, 2))
			ring.append([self.p0 + ax * self.L * f + ay * (b * sc + wob[i, 0] + jit[k, 0]) + az * (a * sc + wob[i, 1] + jit[k, 1]) for k, (a, b) in enumerate(pts)])
		t0 = len(self.mesh.tris)
		# flat faces with their own normals; the corner bands blend from one face's normal to the next, so light rolls only over the corners
		grp = {k: self.mesh.new_group() for k in (0, 2, 4, 6)}
		for i in range(n - 1):
			f0, f1 = i / (n - 1), (i + 1) / (n - 1)
			u0 = r.x + (self.strip_shift + self.L * f0) * T
			u1 = r.x + (self.strip_shift + self.L * f1) * T
			for k in range(8):
				if self.hidden_back and k in (5, 6, 7):
					continue  # against the wall: nobody sees it
				q = [ring[i][k], ring[i + 1][k], ring[i + 1][(k + 1) % 8], ring[i][(k + 1) % 8]]
				uv = [(u0, rows[k]), (u1, rows[k]), (u1, rows[k + 1]), (u0, rows[k + 1])]
				c = np.mean(q, axis=0)
				axis = self.p0 + ax * np.dot(c - self.p0, ax)
				if k % 2 == 0:
					self.mesh.quad(q, uv, c - axis, grp[k])
				else:
					ga, gb = grp[k - 1], grp[(k + 1) % 8]
					self.mesh.quad(q, uv, c - axis, 0, (ga, ga, gb, gb))
		for end, rr in ((0, ring[0]), (1, ring[-1])):
			cap = self.cap_top if (end == 1 and self.cap_top) else END_CAPS[s.atlas.name][int(g.integers(3))]
			fit = FORM_FIT and not (end == 1 and self.cap_top)
			if fit:
				cap = END_FIT[(s.atlas.name, round(s.w, 2), round(s.h, 2))]
			centre = np.mean(rr, axis=0)
			ext = max(self.w, self.h)
			for k in range(8):
				a, b = pts[k], pts[(k + 1) % 8]
				uva = (cap.x + cap.w * (0.5 + 0.48 * a[1] / ext), cap.y + cap.h * (0.5 + 0.48 * a[0] / ext))
				uvb = (cap.x + cap.w * (0.5 + 0.48 * b[1] / ext), cap.y + cap.h * (0.5 + 0.48 * b[0] / ext))
				if fit:  # the true shape on a tile of the true shape, so a thin board's end isn't squashed
					uva = (cap.x + cap.w * (0.5 + 0.96 * a[1] / s.h), cap.y + cap.h * (0.5 + 0.96 * a[0] / s.w))
					uvb = (cap.x + cap.w * (0.5 + 0.96 * b[1] / s.h), cap.y + cap.h * (0.5 + 0.96 * b[0] / s.w))
				uvc = (cap.x + cap.w / 2, cap.y + cap.h / 2)
				self.mesh.tri((rr[k], rr[(k + 1) % 8], centre), (uva, uvb, uvc), ax if end else -ax, 0)
		if not self.hidden_back:
			self.mesh.closed.append((f"beam {self.scheme} {self.L:.1f}", t0, len(self.mesh.tris)))


BEAMS = []


def segment_contact(a, b):
	"""the fraction along beam a where beam b crosses or lands on it, or None"""
	sa = a.p0 + np.linspace(0, 1, 24)[:, None] * (a.p1 - a.p0)
	sb = b.p0 + np.linspace(0, 1, 24)[:, None] * (b.p1 - b.p0)
	d = np.linalg.norm(sa[:, None] - sb[None], axis=2)
	i = np.unravel_index(np.argmin(d), d.shape)
	if d[i] < (a.h + b.h) / 2 * 1.1 + 0.08:
		return i[0] / 23
	return None


# ---------------------------------------------------------------- flat wooden plates: door, shutters, glass
def plate(corners, rect, out, thick=0.12, tops=None, mesh=None, nx=1, ny=1):
	"""a box. corners = BL, BR, TR, TL of the front face. tops(f) lowers the top edge, for the arched door"""
	mesh = mesh or MJ
	BL, BR, TR, TL = [np.array(c, float) for c in corners]
	out = unit(out)
	inset = 1.5

	def at(fu, fv):
		top = tops(fu) if tops else 1.0
		fv = fv * top
		return BL * (1 - fu) * (1 - fv) + BR * fu * (1 - fv) + TR * fu * fv + TL * (1 - fu) * fv

	def uv(fu, fv):
		top = tops(fu) if tops else 1.0
		return (rect.x + inset + (rect.w - 2 * inset) * fu, rect.y + inset + (rect.h - 2 * inset) * (1 - fv * top))

	t0 = len(mesh.tris)
	g = mesh.new_group()
	for i in range(nx):
		for j in range(ny):
			a, b = i / nx, (i + 1) / nx
			c, d = j / ny, (j + 1) / ny
			mesh.quad((at(a, c), at(b, c), at(b, d), at(a, d)), (uv(a, c), uv(b, c), uv(b, d), uv(a, d)), out, g)
			back = -out * thick
			mesh.quad((at(a, c) + back, at(b, c) + back, at(b, d) + back, at(a, d) + back), (uv(a, c), uv(b, c), uv(b, d), uv(a, d)), -out, 0)
	centre = (BL + BR + TR + TL) / 4 - out * thick / 2
	bord = []
	for i in range(nx):
		bord.append((at(i / nx, 0), at((i + 1) / nx, 0)))
	for j in range(ny):
		bord.append((at(1, j / ny), at(1, (j + 1) / ny)))
	for i in range(nx, 0, -1):
		bord.append((at(i / nx, 1), at((i - 1) / nx, 1)))
	for j in range(ny, 0, -1):
		bord.append((at(0, j / ny), at(0, (j - 1) / ny)))
	for a, b in bord:
		# side strip: the plank's edge, sampled from the painted edge of the same panel
		m = (a + b) / 2 - out * thick / 2
		mesh.quad((a, b, b - out * thick, a - out * thick), [(rect.x + 2, rect.y + 2), (rect.x + rect.w - 2, rect.y + 2), (rect.x + rect.w - 2, rect.y + 5), (rect.x + 2, rect.y + 5)], m - centre, mesh.new_group())
	mesh.closed.append(("plate", t0, len(mesh.tris)))


def planks(w_px, h_px, count, name, g, gap=1.4):
	"""vertical planks side by side, each one the fence painter's strip turned upright. Sizes are sheet pixels; the result is at SS"""
	scheme(name)
	F = PAINT_T / JOIN.T
	out_w, out_h = w_px * SS, h_px * SS
	w_px, h_px = int(w_px * F), int(h_px * F)
	img = np.zeros((h_px * SS, w_px * SS, 3))
	cuts = np.cumsum(g.uniform(0.75, 1.25, count))
	cuts = (cuts / cuts[-1] * w_px).astype(int)
	x = 0
	for c in cuts:
		pw = max(c - x, 10)
		FP["GLINTS"], FP["WORN"] = [], []
		strip = paint_strip(h_px, [(pw, "front")], g, knots=int(g.random() < 0.5))
		up = np.rot90(strip, 1)
		pp = up[: h_px * SS, : pw * SS]
		xe = min(x * SS + pp.shape[1], w_px * SS)
		img[:, x * SS : xe] = pp[:, : xe - x * SS]
		img[:, max(xe - int(gap * SS), 0) : xe] = FP["GRAIN"] * 0.6
		x = c
	return shrink(img, out_w, out_h)


def paint_door(r):
	g = child()
	img = planks(r.w, r.h, 5, "Sage", g)
	H, W, _ = img.shape
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	# painted iron straps, each wandering: darks to plum-blue, a soft lit top edge, round nails
	for fy in (0.26, 0.74):
		y0 = fy * H + g.uniform(-3, 3)
		half = H * 0.02
		tip = W * g.uniform(0.76, 0.88)
		wander = smooth1d(W, W // 3, g) * H * 0.004
		d = np.abs(yy - y0 - wander[None, :])
		width = half * np.clip((tip - xx) / (W * 0.1), 0.45, 1)
		m = (d < width) & (xx < tip + half)
		shadow = gaussian_filter(np.roll(m.astype(np.float32), int(0.006 * H), axis=0), 3.0)
		img = over(img, FP["GRAIN"] * 0.55, shadow * 0.6)
		img = over(img, IRON, gaussian_filter(m.astype(np.float32), 0.7))
		high = gaussian_filter(((yy - y0 - wander[None, :] + width) < 2.5).astype(np.float32) * m, 0.8)
		img = over(img, EDGE_PALE, high * ss(W * 0.55, W * 0.05, xx) * 0.7)
		for fx in np.linspace(0.08, tip / W - 0.08, 4):
			dd = np.hypot(xx - fx * W, yy - y0)
			img = over(img, EDGE_PALE, ss(H * 0.006, H * 0.003, dd) * 0.5)
	# the ring handle
	cx, cy = W * 0.8, H * 0.49
	dd = np.hypot(xx - cx, (yy - cy) * 0.9)
	img = over(img, FP["GRAIN"] * 0.5, gaussian_filter((np.abs(dd - H * 0.022) < H * 0.008).astype(np.float32), 2.5) * 0.5)
	img = over(img, IRON, gaussian_filter((np.abs(dd - H * 0.021) < H * 0.005).astype(np.float32), 0.7))
	# painted light: dark at the foot and under the head, worn at the middle where hands go
	img = over(img, FP["DUSK"] * 0.75, ss(0.3, 0.02, yy / H) * 0.32)
	img = over(img, MOSS_D, ss(0.92, 1.0, yy / H) * 0.32)
	img = over(img, FP["LIGHT"] * 1.22, gaussian_filter(np.exp(-(((xx - cx) / (W * 0.16)) ** 2) - ((yy - cy) / (H * 0.09)) ** 2).astype(np.float32), 4) * 0.28)
	# the head's shadow and the sunward post's shadow, cut clean
	img = shade(img, yy < cut_edge(W, H * 0.13, H * 0.012, 5)[None, :], 0.65)
	img = img * green_streaked(H, W, g)
	return np.clip(img, 0, 255)


def paint_shutter(r):
	g = child()
	img = planks(r.w, r.h, 3, "Sage", g)
	H, _W, _ = img.shape
	yy = np.arange(H, dtype=np.float32)[:, None, None]
	return np.clip(img * darken(yy[:, 0, 0] / H, 0.15)[:, None, :] * green_streaked(H, img.shape[1], g), 0, 255)


def paint_glass(r):
	"""dark blue glass with broad flat strokes: a slash of sky and a warm glow low down. Crisp strokes and a soft bloom"""
	g = child()
	H, W = r.h * SS, r.w * SS
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	img = np.zeros((H, W, 3), float)
	img[:] = (50, 52, 84)
	img = over(img, np.array((64, 72, 108), float), ss(0.9, 0.2, yy / H) * 0.9)
	img = over(img, np.array((36, 34, 62), float), ss(0.35, 0.0, yy / H) * 0.6)
	for colour, a, x0, x1 in (((96, 118, 150), 0.42, 0.05, 0.42),):
		line = (yy / H) * -0.35 + x0 + 0.2
		band = (xx / W > line) & (xx / W < line + (x1 - x0))
		img = over(img, np.array(colour, float), gaussian_filter(band.astype(np.float32), 1.4) * a)
	# warm light from inside: flat wandering strokes low in the pane, no disc
	m = np.zeros((H, W, 1), np.float32)
	stroke(m, -W * 0.1, W * g.uniform(0.85, 1.1), H * 0.86, H * 0.14, np.array((1.0,)), g, wander=H * 0.05, tail=0.35)
	img = over(img, np.array((150, 104, 92), float), gaussian_filter(m[..., 0], 2.2) * 0.5)
	img = shade(img, yy < cut_edge(W, H * 0.2, H * 0.015, 4)[None, :], 0.95)
	img = shade(img, xx < cut_edge(H, W * 0.1, W * 0.012, 3)[:, None], 0.8)
	return np.clip(img, 0, 255)


# ---------------------------------------------------------------- plaster
class Face:
	"""a wall's frame: u right, v up, d out; beams and windows placed on it, remembered for the plaster's contact shadows"""

	def __init__(self, name, origin, right, out):
		self.name, self.origin, self.right, self.out = name, np.array(origin, float), np.array(right, float), np.array(out, float)
		self.marks = []  # (u0, v0, u1, v1, thickness)
		self.patches = []  # worn plaster, placed by hand: (u, v, half width, half height)

	def at(self, u, v, d=0.0):
		return self.origin + self.right * u + np.array((0, v, 0.0)) + self.out * d

	def beam(self, a, b, w=0.62, h=0.72, d=0.14, **kw):
		self.marks.append((a[0], a[1], b[0], b[1], h))
		return Beam(self.at(a[0], a[1], d), self.at(b[0], b[1], d), self.out, w, h, face=self.name, **kw)

	def block(self, u0, v0, u1, v1):
		self.marks.append((u0, (v0 + v1) / 2, u1, (v0 + v1) / 2, abs(v1 - v0)))


def plaster_accent(img, valid, S, W, H, yy, xx, g, shadow_row):
	"""per white block (each enclosed area of plaster): one gradient from the block's own top edge, broken into tapered fingers and running a little further down at its corners"""
	labels, n = label(valid)
	for i in range(1, n + 1):
		m = labels == i
		if m.sum() < 1.5 * S * S:
			continue
		cols = np.where(m.any(axis=0))[0]
		rows = np.where(m.any(axis=1))[0]
		x0, x1 = cols[0], cols[-1]
		height = min(rows[-1] - rows[0] + 1, ACCENT_MAX_HEIGHT * S)
		top = m.argmax(axis=0).astype(np.float32)
		top[:x0], top[x1 + 1 :] = top[x0], top[x1]
		has = m.any(axis=0)
		top = np.interp(np.arange(W), np.where(has)[0], top[has]).astype(np.float32)
		top = np.maximum(gaussian_filter(top, 0.08 * S), shadow_row)  # starts where the eave's painted shadow ends, or that shadow hides it
		edge = np.abs(2 * (xx - x0) / max(x1 - x0, 1) - 1).clip(0, 1) ** 1.7  # a gentle arc: higher in the middle, curving down to the sides
		base = max(height * ACCENT_DEPTH, ACCENT_MIN_RUN * S * min((rows[-1] - rows[0] + 1) / (5 * S), 1)) * (0.85 + ACCENT_CORNER * edge)
		depth_px = np.maximum(yy - top[None, :], 0)
		# stacked washes: every layer is solid from the top, so nothing shows between them up there. They only part near the bottom, each with its own uneven edge and soft fade
		amount = np.zeros((H, W), np.float32)
		# most of the width is clusters of colour; streaks only in chosen stretches, the same stretches through every layer so they gather
		field = gaussian_filter(g.normal(0, 1, W).astype(np.float32), ACCENT_STREAK_PATCH * S)
		cut = np.percentile(field[x0 : x1 + 1], ACCENT_CLUSTER_SHARE)
		streaky = gaussian_filter((field > cut).astype(np.float32), 0.14 * S)
		for reach_f, amp, soft_f in ACCENT_LAYERS:
			cluster = gaussian_filter(streak_reach(W, S, g, ACCENT_CLUSTER_WIDTH, (1 - amp * ACCENT_CLUSTER_AMP, 1 + amp * ACCENT_CLUSTER_AMP)), 0.12 * S)
			finger = gaussian_filter(streak_reach(W, S, g, ACCENT_STROKE_WIDTH, (1 - amp * 1.15, 1 + amp * 1.15)), 0.03 * S)
			edge_x = cluster + (finger - 1) * (ACCENT_FINGER_FLOOR + (1 - ACCENT_FINGER_FLOOR) * streaky)  # lighter fingers everywhere, so no stretch ends in a smooth round curve
			wob = smooth1d(H, max(H // 3, 6), g)[:, None] * 0.06 * S
			col = np.clip(xx + wob, 0, W - 1).astype(int)
			run = base * reach_f * edge_x[col]
			amount += np.clip((run - depth_px) / (run * soft_f), 0, 1)
		f = amount / len(ACCENT_LAYERS)
		amount = f**1.1 * ACCENT_STRENGTH * (0.94 + 0.06 * edge) * PLASTER_PASS
		amount = gaussian_filter(amount.astype(np.float32), (0.03 * S, 0.012 * S + 0.4)) * gaussian_filter(m.astype(np.float32), 0.6)
		tint = ACCENT_LIGHT + (ACCENT_DEEP - ACCENT_LIGHT) * (f**1.1)[..., None]
		img = img * (1 + (tint - 1) * amount[..., None])
	return img


def plaster_pass(img, xx, yy, vs, line, mm, S, W, H, u0, v1, face, depth=0.75):
	"""one cool gradient by height, short streaks placed by hand under the things that would cause them, rough painted edges against the timber"""
	if not PLASTER_PASS:
		return img
	g = np.random.default_rng(W * 31 + H)
	# colour by height on the house, the same line across every wall
	f = np.clip((vs - GRAD_Y[0]) / (GRAD_Y[1] - GRAD_Y[0]), 0, 1)[..., None] ** 1.1
	low = np.clip(1 - (vs - FOOT_Y) / 2.5, 0, 1)[..., None]
	img = img * (1 + (PLASTER_TOP - 1) * f * PLASTER_GRAD * PLASTER_PASS) * (1 + (PLASTER_LOW - 1) * low * PLASTER_PASS)
	# short streaks in small uneven clusters, each starting from something: the ends of a sill or beam, or the eave. A wall gets few of them, placed near its corners and openings, not spread evenly
	seeds = []
	for (a0, b0, a1, b1, th) in face.marks:
		if th > 1.1 or abs(b1 - b0) > 0.4 or abs(a1 - a0) < 1.2:
			continue  # only horizontal timbers
		lo, hi = sorted((a0, a1))
		y = (v1 - (b0 + b1) / 2 + th / 2) * S
		for end, side in ((lo, 1), (hi, -1)):
			seeds.append(((end + side * g.uniform(0.2, 0.75) - u0) * S, y))
	for fx in (g.uniform(0.06, 0.2), g.uniform(0.8, 0.94)):
		col = int(np.clip(fx * W, 0, W - 1))
		seeds.append((fx * W, (v1 - line[0, col]) * S))
	g.shuffle(seeds)
	mask = np.zeros((H, W), np.float32)
	placed = []
	limit = max(3, min(9, int(W * H / (S * S) / 5.5)))
	for sx, sy in seeds:
		if len(placed) >= limit:
			break
		if not (0 <= sx < W and 0 <= sy < H) or any(math.hypot(sx - px, sy - py) < 1.6 * S for px, py in placed):
			continue
		placed.append((sx, sy))
		count = int(g.choice((1, 2, 3), p=(0.25, 0.45, 0.3)))
		lead = g.uniform(*STREAK_LENGTH)
		x = sx
		for k in range(count):
			length = lead * (1 if k == 0 else g.uniform(0.3, 0.7)) * S
			half = g.uniform(0.08, 0.17) * S
			y0 = int(sy + g.uniform(0, 0.08) * S)
			n = int(length)
			if n < 6:
				continue
			drift = np.cumsum(smooth1d(n, max(n // 3, 4), g)) / n * S * 0.07
			for i in range(n):
				t = i / n
				row = y0 + i
				if not 0 <= row < H:
					break
				w = half * (1 - t) ** 0.65 + 0.4
				a0, a1 = int(x + drift[i] - w), int(x + drift[i] + w) + 1
				a0, a1 = max(a0, 0), min(a1, W)
				if a1 > a0:
					mask[row, a0:a1] = np.maximum(mask[row, a0:a1], (1 - t) ** 2.0)
			x += g.uniform(0.2, 0.42) * S * (1 if g.random() < 0.7 else -1)
	m = gaussian_filter(mask, 0.012 * S + 0.5) * (mm < 0.5)
	img = img * (1 + (STREAK_TINT - 1)[None, None, :] * (m * STREAK_STRENGTH * PLASTER_PASS)[..., None])
	img = plaster_accent(img, (mm < 0.5) & (vs <= line + 0.02) & (vs >= FOOT_Y), S, W, H, yy, xx, g, ((v1 - line[0]) + depth * 0.7) * S)
	# rough painted edges: the plaster breaks up against the timber and the stone, as if brushed up to it
	n = gaussian_filter(g.random((H, W)).astype(np.float32), 0.14 * S)
	n = np.clip((n - n.mean()) / (n.std() * 2.2) + 0.5, 0, 1)
	far = distance_transform_edt(mm < 0.5).astype(np.float32) / S
	foot = np.maximum(vs - FOOT_Y, 0)
	near = np.minimum(far, foot)
	# only in stretches: an even line around every timber read as a halo
	patch = gaussian_filter(g.random((H, W)).astype(np.float32), 0.9 * S)
	patch = np.clip((patch - patch.mean()) / (patch.std() + 1e-6) * 0.9 - 0.15, 0, 1)
	band = ((near < 0.04 + 0.16 * n) & (mm < 0.5)).astype(np.float32) * patch
	img = over(img, PL_LIGHT * 1.07, gaussian_filter(band, 0.02 * S + 0.6) * ROUGH_STRENGTH * PLASTER_PASS)
	return img


def paint_plaster(r, face, u0, v1, top, shade_y, rng_, shadow_depth=None):
	"""broad flat strokes of close values (the video's method), then patches, then the contact shadows the frame throws"""
	T = WALL.T
	g = rng_
	H, W = r.h * SS, r.w * SS
	S = T * SS
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	img = np.zeros((H, W, 3), float)
	img[:] = PL_BASE
	# big soft planes first, then crisper strokes in several directions
	for colour, count, half, soften, strength in ((PL_LIGHT, 7, 1.1, 2.2, 0.55), (PL_ROSE, 6, 1.0, 2.2, 0.5), (PL_COOL, 5, 0.9, 2.0, 0.4), (PL_WARM, 6, 0.55, 1.1, 0.55), (PL_LIGHT, 9, 0.28, 0.5, 0.5), (PL_ROSE, 7, 0.22, 0.45, 0.42)):
		m = np.zeros((H, W, 1), np.float32)
		count = int(count * max(W * H / (S * S * 60), 0.6) * 0.6 * STROKE_DENSITY)
		for _ in range(count):
			if g.random() < 0.0:
				# upright stroke: painted on a turned mask
				mt = np.zeros((W, H, 1), np.float32)
				x0 = g.uniform(-0.1, 0.85) * H
				stroke(mt, x0, x0 + g.uniform(0.3, 0.7) * H, g.uniform(0, W), half * S * g.uniform(0.6, 1.1), np.array((1.0,)), g, wander=S * 0.12, tail=0.5)
				m = np.maximum(m, np.transpose(mt, (1, 0, 2)))
			else:
				x0 = g.uniform(-0.1, 0.85) * W
				stroke(m, x0, x0 + g.uniform(0.2, 0.5) * W, g.uniform(0, H), half * S * g.uniform(0.5, 1.0), np.array((1.0,)), g, wander=S * 0.12, tail=0.5)
		img = over(img, colour, gaussian_filter(m[..., 0], soften * 2) * strength * STROKE_STRENGTH)
	# worn patches where the laths show: a crisp wobbling hole, dark inner lip, warm strips, the cream lit lower rim
	area = W * H / (S * S)
	for pu, pv, prx, pry in face.patches:
		cx, cy = (pu - u0) * S, (v1 - pv) * S
		rx, ry = prx * S, pry * S
		ang = np.arctan2((yy - cy) / ry, (xx - cx) / rx)
		wob = sum(np.sin(ang * f + g.uniform(0, 6.3)) * a for f, a in ((3, 0.14), (5, 0.1), (9, 0.05)))
		d = np.hypot((xx - cx) / rx, (yy - cy) / ry) - (1 + wob)
		hole = d < 0
		img[hole] = LATH * 0.5 + PL_ROSE * 0.5
		rows = np.sin((yy + np.sin(xx / S * 2) * S * 0.04) / (S * 0.3) * math.pi)
		img = over(img, LATH_DARK, (rows < -0.45) * hole * 0.85)
		img = over(img, PL_DEEP, ss(-0.2, 0, d) * hole * 0.35)
		rim = ss(0.16, 0.0, np.abs(d)) * (yy > cy)
		img = over(img, PL_LIGHT * 1.08, gaussian_filter((rim * (d >= 0)).astype(np.float32), 1.0) * 0.45)
		img = over(img, PL_ROSE * 0.86, gaussian_filter(((np.abs(d) < 0.1) * (yy < cy) * (d >= 0)).astype(np.float32), 1.0) * 0.8)
	# hairline cracks, tapered, from the marks
	from_lines = FP["paint_lines"]((H, W), int(area / 45 * CRACK_DENSITY), (0.05, 0.16), 0.5 * SS, g, H * 0.06, xspan=(0.0, 0.9))
	img = over(img, PL_SHADE, gaussian_filter(from_lines, 0.5) * 0.5)
	# the frame's shadows: the mask of everything standing on the wall, thrown down and a little sideways
	mask = Image.new("L", (W, H), 0)
	dr = ImageDraw.Draw(mask)
	for (a0, b0, a1, b1, th) in face.marks:
		ax, ay, bx, by = (a0 - u0) * S, (v1 - b0) * S, (a1 - u0) * S, (v1 - b1) * S
		L = math.hypot(bx - ax, by - ay) + 1e-6
		nx, ny = (by - ay) / L * th * S / 2, (ax - bx) / L * th * S / 2
		dr.polygon([(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)], fill=255)
	mm = np.array(mask, np.float32) / 255
	near = gaussian_filter(np.roll(mm, (int(0.16 * S), int(0.04 * S)), (0, 1)), 0.09 * S)
	wide = gaussian_filter(mm, 0.42 * S)
	img = over(img, PL_SHADE, np.clip(wide * 1.1, 0, 1) * 0.2)
	img = shade(img, np.roll(mm, (int(0.2 * S), int(0.08 * S)), (0, 1)) > 0.5, 0.9, WALL_SHADE_TINT)
	# dirt run down from every rail and sill, broken into streaks: rain, not noise
	streak = gaussian_filter(g.random((H, W)).astype(np.float32), (1.2 * S, 0.05 * S))
	streak = np.clip((streak - streak.mean()) / (streak.std() * 1.5) * 0.5 + 0.5, 0, 1)
	run = gaussian_filter(np.roll(mm, int(0.5 * S), 0), (0.5 * S, 0.1 * S))
	img = over(img, PL_ROSE * 0.78, run * streak * 0.22 * DIRT_STRENGTH)
	# light: under the eave and the barge boards dark, and the wall's foot damp
	vs = v1 - yy / S
	us = u0 + xx / S
	tops = np.vectorize(top)(us[0])[None, :]
	line = np.minimum(tops, shade_y)
	depth = shadow_depth or (EAVE_DEPTH if shade_y < 90 else 0.75)
	img = shade(img, vs > line - depth + cut_edge(W, 0, 0.1, max(int(W / (S * 3)), 3))[None, :], 1.0, WALL_SHADE_TINT)
	img = over(img, PL_SHADE, ss(1.0, 0.05, line - vs) * 0.3)
	img = plaster_pass(img, xx, yy, vs, line, mm, S, W, H, u0, v1, face, depth)
	# framing: the plaster's brightest around its middle, falling to plum at the wall's ends and damp at its foot
	across = np.abs(xx / W - 0.5) * 2
	fall = np.clip(across**2.2 * 0.62 + ss(FOOT_Y + 1.3, FOOT_Y, vs) * 0.45, 0, 1)[..., None]
	img = img * (1 + (UNDER_TINT - 1) * fall**1.3 * 0.55)  # the plum half only: gold turned the cream yellow
	img = img * np.array((1.0, 0.995, 1.05))
	if RIM:
		R = rim_corner(np.array([face.at(u, 5.0) for u in us[0]]), RIM_PLASTER_REACH)
		img = img * (1 + (RIM_PLASTER_TINT - 1)[None, None, :] * R[None, :, None])
	img = np.clip(img + (img - gaussian_filter(img, (1.3 * SS, 1.3 * SS, 0))) * 0.6, 0, 255)
	return img


def wall(face, u0, u1, v0, top, shade_y=99.0, d=0.0, cols=6, rows=4, shadow_depth=None):
	v1 = max(top(u) for u in np.linspace(u0, u1, 40))
	sub = child()
	rect = WALL.add((u1 - u0, v1 - v0), lambda r, f=face: paint_plaster(r, f, u0, v1, top, shade_y, sub, shadow_depth))
	us = sorted(set(list(np.linspace(u0, u1, cols + 1)) + ([0.0] if u0 < 0 < u1 else [])))

	def build():
		T = WALL.T
		g = ML.new_group()
		for a, b in zip(us[:-1], us[1:]):
			ta, tb = top(a), top(b)
			for j in range(rows):
				f0, f1 = j / rows, (j + 1) / rows
				q = [face.at(a, v0 + (ta - v0) * f0, d), face.at(b, v0 + (tb - v0) * f0, d), face.at(b, v0 + (tb - v0) * f1, d), face.at(a, v0 + (ta - v0) * f1, d)]
				uv = [(rect.x + (a - u0) * T, rect.y + (v1 - (v0 + (ta - v0) * f0)) * T), (rect.x + (b - u0) * T, rect.y + (v1 - (v0 + (tb - v0) * f0)) * T), (rect.x + (b - u0) * T, rect.y + (v1 - (v0 + (tb - v0) * f1)) * T), (rect.x + (a - u0) * T, rect.y + (v1 - (v0 + (ta - v0) * f1)) * T)]
				ML.quad(q, uv, face.out, g)

	emit.append(build)
	return rect


# ---------------------------------------------------------------- stone
def paint_stones(H, W, S, g, foot=0.0, ledge=0.0, course=(1.0, 1.6), block=(2.2, 4.2), lit=None, cast=0.0):
	"""stones as painted shapes: rows and joints wander; each stone has its own planes, a lit top edge with a rhythm, a dark plum-blue joint"""
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	# rows from the bottom: wandering boundaries
	bounds = []
	y = float(H)
	while y > -S:
		bounds.append(y + smooth1d(W, max(W // 6, 8), g) * S * 0.09)
		y -= g.uniform(*course) * S
	bounds = np.array(bounds)  # row i is between bounds[i] (lower) and bounds[i+1] (upper)
	row = np.zeros((H, W), int)
	top = np.zeros((H, W), np.float32)
	bot = np.zeros((H, W), np.float32)
	for i in range(len(bounds) - 1):
		sel = (yy < bounds[i][None, :]) & (yy >= bounds[i + 1][None, :])
		row[sel] = i
		top[sel] = (yy - bounds[i + 1][None, :])[sel]
		bot[sel] = (bounds[i][None, :] - yy)[sel]
	ids = np.zeros((H, W), int)
	nrows = len(bounds)
	info = []
	for i in range(nrows):
		x = -g.uniform(0, block[1]) * S
		cuts = []
		while x < W + S:
			x += g.uniform(*block) * S
			cuts.append(x)
		cuts = np.array(cuts)
		sel = row == i
		if not sel.any():
			continue
		lean = g.uniform(-0.12, 0.12)
		shift = smooth1d(H, max(H // 3, 6), g)[yy[sel].astype(int)] * S * 0.08 + (yy[sel] - yy[sel].mean()) * lean
		col = np.searchsorted(cuts, xx[sel] + shift)
		base = len(info)
		ids[sel] = base + col
		for _ in range(len(cuts) + 1):
			info.append(i)
	n = len(info)
	value = np.clip(g.normal(1.6, 0.24, n), 0.8, 2.4)
	hue = g.choice((0, 1, 2), n, p=(0.8, 0.12, 0.08))
	ang = g.uniform(0, math.tau, n)
	offs = g.uniform(-0.4, 0.4, n)
	shift_v = g.uniform(-0.15, 0.15, n)
	# the stone's centre, for its own plane
	counts = np.bincount(ids.ravel(), minlength=n).astype(np.float32) + 1
	cx = np.bincount(ids.ravel(), xx.ravel(), minlength=n) / counts
	cy = np.bincount(ids.ravel(), yy.ravel(), minlength=n) / counts
	# highlights only where lit() says: a stone's level from its place, not a dice roll
	level = lit(cx / W, np.minimum(cx, W - cx) / S, cy / S) if lit else np.zeros(n)
	vx = (xx - cx[ids]) * np.cos(ang)[ids] + (yy - cy[ids]) * np.sin(ang)[ids]
	v = value[ids].astype(np.float32) + np.where(vx > offs[ids] * S * 0.7, shift_v[ids], 0).astype(np.float32)
	# edges of stones
	edge = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
	d = distance_transform_edt(~edge).astype(np.float32)
	v += ss(0.0, 0.5 * S, top) * -0.1
	v += ss(0.5 * S, 0, top) * 0.4
	v += ss(0.28 * S, 0, bot) * -0.75
	v = np.clip(v, 0, 3)
	lo = np.floor(v).astype(int).clip(0, 2)
	frac = (v - lo)[..., None]
	ramp = np.stack(ST_RAMP)
	img = ramp[lo] * (1 - frac) + ramp[lo + 1] * frac
	img = over(img, ST_OCHRE, (hue[ids] == 1) * 0.3)
	img = over(img, ST_SLATE, (hue[ids] == 2) * 0.3)
	# small planes and fine strokes
	fine = FP["paint_lines"]((H, W), int(H * W / (S * S) / 5), (0.03, 0.09), 0.5 * SS, g, S * 0.08, xspan=(0.0, 0.98))
	img = over(img, ST_RAMP[0], gaussian_filter(fine, 0.5) * 0.28)
	img = over(img, ST_GAP, ss(1.2 * SS, 0.4 * SS, d) * 0.62)
	img = over(img, ST_RAMP[0], ss(3.4 * SS, 0.8 * SS, d) * 0.34)
	# the wall above the moss: a damp shade
	if foot:
		vs = 1 - yy / H
		wob = gaussian_filter(g.normal(0, 1, W).astype(np.float32), S * 0.5)
		wob = (wob / (np.abs(wob).max() + 1e-6) * 0.5)[None, :]
		img = over(img, ST_GAP * 1.2, ss(foot * 1.4, foot * 0.3, vs + wob * foot * 0.3) * 0.62)
		m = ss(foot * 0.6, foot * 0.25, vs + wob * foot * 0.4)
		img = over(img, MOSS_D, m * 0.75)
		img = over(img, MOSS_L, ss(foot * 0.4, foot * 0.1, vs + wob * foot * 0.5) * (ss(0.1 * S, 0.5 * S, top)) * 0.4)
	img = img * darken(yy / H, 0.45)
	img = img * (1 + (np.array((0.9, 0.88, 1.02)) - 1) * ss(0.35, 1.0, yy / H)[..., None])
	if cast:
		img = shade(img, yy < (ledge + cast) * S + cut_edge(W, 0, 0.07 * S, max(int(W / (S * 3)), 3))[None, :], 0.95)
	img = np.clip(img + (img - gaussian_filter(img, (1.3 * SS, 1.3 * SS, 0))) * 0.65, 0, 255)
	# lit top edges: each stone's own level, a soft-sided band with a streaked bleed
	wob = smooth1d(W, max(W // 12, 6), g)[None, :] * SS
	lvl = level[ids].astype(np.float32)
	w = 0.1 * S
	high = ss(w, 0, np.abs(top - wob - w * 0.5)) * lvl
	bleed = gaussian_filter(g.random((H, W)).astype(np.float32), (0.02 * S, 0.25 * S))
	bleed = np.clip((bleed - bleed.mean()) / (bleed.std() * 1.5) * 0.5 + 0.5, 0, 1)
	high = np.maximum(high, ss(0.32 * S, 0.02 * S, top) * lvl * (lvl > 0.7) * bleed * 0.6)
	high = high * (d > 0.8 * SS) * (0.55 + 0.45 * bleed)
	img = over(img, EDGE, gaussian_filter(high, 0.45 * SS) * 0.56)
	img = over(img, EDGE_PALE, gaussian_filter(high, (0.1 * S, 0.3 * S)) * 0.2)
	# relief for the normal map: one simple idea, each stone's face gently rounded, easing flat at the joints. The user rejected creases, chisel cuts and swells as too much: the paint carries the stone
	global HEIGHT
	sd = gaussian_filter(d, 1.0 * SS)  # the joint's wander stays out of the normals
	height = 0.05 * ss(0.02 * S, 0.5 * S, sd)
	if ledge:
		height = height * ss(ledge * 0.9, ledge * 1.3, yy / S)
	HEIGHT = gaussian_filter(height.astype(np.float32), 0.5 * SS)
	if ledge:
		img = over(img, ST_RAMP[3] * 1.04, ss(ledge * 1.3, ledge * 0.7, yy / S) * 0.42)
	return np.clip(img, 0, 255)


def footing(face, u0, u1, shared=None, cap_ends=False, seed=None):
	"""the stone base: a battered wall with a lit ledge along its top, sunk a stud into the ground.
	Stone highlights gather at the run's two ends, the corners and door jambs, in the upper courses, and fade away along it"""
	if not USE_FOOTING:
		return  # every house now stands on the base from tools/art/house_stone.py
	lit = lambda fx, ends, down: np.clip((2.4 - ends) / 1.4, 0, 1) * np.clip((1.5 - down) / 0.6, 0, 1) * 0.75
	h = FOOT_Y + 1.0
	ledge = 0.42
	key = shared if shared is not None else None
	if key is not None and key in FOOTS:
		rect = FOOTS[key]
	else:
		L = (u1 - u0)
		rect = WALL.add((L, h + ledge), lambda r, s=child(): paint_stones(r.h * SS, r.w * SS, WALL.T * SS, s, foot=0.7, ledge=ledge, lit=lit, cast=FOOTING_CAST))
		TAGS["stone"].append(rect)
		if key is not None:
			FOOTS[key] = rect
	g2 = child()
	nc = max(4, int((u1 - u0) / 1.8))

	def build():
		T = WALL.T
		us = np.linspace(u0, u1, nc + 1)
		jit = g2.normal(0, 0.05, nc + 1)
		dep = g2.normal(0, 0.035, nc + 1)
		g = ML.new_group()
		g3 = ML.new_group()
		L = u1 - u0
		rw = rect.w / T
		for i in range(nc):
			a, b = us[i], us[i + 1]
			ua = rect.x + ((a - u0) / L) * rw * T
			ub = rect.x + ((b - u0) / L) * rw * T
			top_a, top_b = FOOT_Y + jit[i], FOOT_Y + jit[i + 1]
			da, db = 0.42 + dep[i], 0.42 + dep[i + 1]
			ledge_a, ledge_b = rect.y + 2, rect.y + 2
			yl = rect.y + ledge * T
			mit = lambda u, dep_: u + (dep_ - 0.42) * (-1 if (u == us[0]) else 1 if (u == us[-1]) else 0) * (0 if cap_ends else 1)
			ML.quad([face.at(mit(a, 0.82), -1, 0.82), face.at(mit(b, 0.82), -1, 0.82), face.at(b, top_b, db), face.at(a, top_a, da)], [(ua, rect.y + rect.h), (ub, rect.y + rect.h), (ub, yl), (ua, yl)], face.out + np.array((0, 0.25, 0)), g)
			ML.quad([face.at(a, top_a, da), face.at(b, top_b, db), face.at(b, top_b + 0.08, -0.05), face.at(a, top_a + 0.08, -0.05)], [(ua, yl), (ub, yl), (ub, ledge_b), (ua, ledge_a)], np.array((0, 1, 0)), g3)
		if cap_ends:
			for u, sign, j in ((u0, -1, 0), (u1, 1, nc)):
				x = rect.x + 3 if sign < 0 else rect.x + rect.w - 3
				ML.quad([face.at(u, -1, 0), face.at(u, -1, 0.82), face.at(u, FOOT_Y + jit[j], 0.42 + dep[j]), face.at(u, FOOT_Y + jit[j], 0)], [(x, rect.y + rect.h), (x, rect.y + rect.h), (x, rect.y + ledge * T), (x, rect.y + ledge * T)], face.right * sign, 0)

	emit.append(build)
	return rect


FOOTS = {}
JOINT_COLLAR, JOINT_SHOE, JOINT_GROW = 0.62, 0.42, 0.26  # studs: a post's collar and shoe, how much thicker than the post
USE_FOOTING = False
PRISMS = {}  # stone_prism(share=key): prisms of one size sharing one painted place


def stone_prism(p0, p1, w, h, front, foot=0.0, ledge=0.0, taper=1.0, course=(0.55, 0.95), block=(0.8, 1.7), cast=0.0, share=None):
	"""a stone block, upright or lying: stones wrap round it. Rows of stones run across the axis"""
	ch = min(w, h) * 0.07
	pts = [(-w / 2 + ch, h / 2), (w / 2 - ch, h / 2), (w / 2, h / 2 - ch), (w / 2, -h / 2 + ch), (w / 2 - ch, -h / 2), (-w / 2 + ch, -h / 2), (-w / 2, -h / 2 + ch), (-w / 2, h / 2 - ch)]
	perim = sum(math.dist(pts[i], pts[(i + 1) % 8]) for i in range(8))
	p0, p1 = np.array(p0, float), np.array(p1, float)
	L = float(np.linalg.norm(p1 - p0))
	sub = child()
	if share and share in PRISMS:
		rect, top_rect = PRISMS[share]
	else:
		rect = WALL.add((perim, L), lambda r, s=sub: paint_stones(r.h * SS, r.w * SS, WALL.T * SS, s, foot=foot, ledge=ledge, course=course, block=block, cast=cast, lit=lambda fx, ends, down: np.clip((1.5 - down) / 0.7, 0, 1) * 0.8))
		top_rect = WALL.add((0.6, 0.6), lambda r, s=child(): paint_stones(r.h * SS, r.w * SS, WALL.T * SS, s, course=(0.2, 0.3), block=(0.2, 0.3)))
		TAGS["stone"] += [rect, top_rect]
		if share:
			PRISMS[share] = (rect, top_rect)

	def build():
		ax = unit(p1 - p0)
		az = unit(np.array(front, float) - ax * np.dot(front, ax))
		ay = np.cross(az, ax)
		n = max(2, int(L / 2) + 2)
		T = WALL.T
		acc = [0.0]
		for i in range(8):
			acc.append(acc[-1] + math.dist(pts[i], pts[(i + 1) % 8]))
		rings = []
		for i in range(n):
			f = i / (n - 1)
			sc = 1 + (taper - 1) * f
			rings.append([p0 + ax * L * f + ay * b * sc + az * a * sc for a, b in pts])
		g = ML.new_group()
		t0 = len(ML.tris)
		for i in range(n - 1):
			f0, f1 = i / (n - 1), (i + 1) / (n - 1)
			for k in range(8):
				q = [rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % 8], rings[i][(k + 1) % 8]]
				y0, y1 = rect.y + rect.h * (1 - f0), rect.y + rect.h * (1 - f1)
				x0, x1 = rect.x + acc[k] * T, rect.x + acc[k + 1] * T
				c = np.mean(q, axis=0)
				axis = p0 + ax * np.dot(c - p0, ax)
				ML.quad(q, [(x0, y0), (x0, y1), (x1, y1), (x1, y0)], c - axis, g)
		for end, rr in ((0, rings[0]), (1, rings[-1])):
			c = np.mean(rr, axis=0)
			for k in range(8):
				u = lambda a: (top_rect.x + top_rect.w * (0.5 + 0.48 * a[0] / max(w, h)), top_rect.y + top_rect.h * (0.5 + 0.48 * a[1] / max(w, h)))
				ML.tri((rr[k], rr[(k + 1) % 8], c), (u(pts[k]), u(pts[(k + 1) % 8]), (top_rect.x + top_rect.w / 2, top_rect.y + top_rect.h / 2)), ax if end else -ax, 0)
		ML.closed.append(("stone prism", t0, len(ML.tris)))

	emit.append(build)


# ---------------------------------------------------------------- tiles
def paint_roof(r, courses, width, lift, shadows, g, moss=0.5, mossy_end=None, sun=None):
	"""each course a row of painted tiles, rounded lower ends, one calm colour family; then the slope's own big shapes"""
	T = ROOF.T
	S = T * SS
	W = r.w * SS
	rows = []
	y = 0
	for fh, lh in courses:
		rows.append((y, int(fh * T) * SS, int(lh * T) * SS))
		y += (int(fh * T) + int(lh * T)) * SS
	H = r.h * SS
	img = np.zeros((H, W, 3), float)
	img[:] = TL_GAP
	tile_mask = np.zeros((H, W), np.float32)
	high = np.zeros((H, W), np.float32)
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	palette = [TL_BASE, TL_WARM, TL_ROSE, TL_DUSK, TL_LIGHT]
	big = gaussian_filter(g.normal(0, 1, (H // 8 + 1, W // 8 + 1)).astype(np.float32), 18)
	big = big / (np.abs(big).max() + 1e-6)
	big_at = lambda a, b: big[min(int(a) // 8, big.shape[0] - 1), min(int(b) // 8, big.shape[1] - 1)]
	nrows = len(rows)
	for ri, (y0, fh, lh) in enumerate(rows):
		x = -g.uniform(0, 1.0) * S
		course_cut = cut_edge(W, fh * 0.2, fh * 0.03, max(int(W / (S * 3)), 3))
		while x < W:
			tw = g.uniform(*TILE_WIDTH) * S
			xa, xb = int(max(x, 0)), int(min(x + tw, W))
			if xb - xa < 3:
				x += tw
				continue
			cx = x + tw / 2
			sl = (slice(y0, y0 + fh), slice(xa, xb))
			ty, tx = yy[sl] - y0, xx[sl]
			# the tile's rounded lower end
			f = np.clip(np.abs(tx - cx) / (tw / 2), 0, 1)
			round_px = fh * g.uniform(*TILE_ROUND)
			curve = fh - round_px * (1 - np.sqrt(1 - f**2)) - g.uniform(0, 0.06) * S
			inside = ty < curve
			# side gaps
			side = ss(0.05 * S, 0.0, np.minimum(tx - x, x + tw - tx)) * ss(0.12, 0.4, ty / fh)
			# colour: a pick of the family, drifting with the slope's big shapes
			bias = big_at(y0 + fh / 2, cx)
			pick = g.choice(5, p=np.array((0.62, 0.16, 0.12, 0.06, 0.04)))
			if g.random() < 0.03:
				pick = 3 if g.random() < 0.6 else 4
			col = palette[pick] * (1 + bias * 0.05) * (1 + g.normal(0, 0.008)) + g.normal(0, 1.6, 3)
			part = np.zeros(ty.shape + (3,), float)
			part[:] = col
			# a flat plane on each tile, along the slope, crisp: the painted facet
			for _ in range(1):
				a0, a1 = sorted(g.uniform(x, x + tw, 2))
				plane = (tx > a0) & (tx < a1 + tw * 0.15)
				part = over(part, palette[int(g.integers(5))], gaussian_filter(plane.astype(np.float32), 1.0) * TILE_PLANE)
			# fine lengthwise strokes
			lines = gaussian_filter(g.random(ty.shape).astype(np.float32), (fh * 0.22, 0.6))
			lines = np.clip((lines - lines.mean()) / (lines.std() + 1e-6), -2, 2) / 2
			part *= (1 + lines * 0.04)[..., None]
			# painted light on the tile: the shade from the course above, lit towards its end
			part = over(part, TL_SHADOW, ss(fh * 0.3, fh * 0.03, ty) * 0.3)
			part = shade(part, ty < course_cut[xa:xb][None, :], 0.95)
			part = part * (0.97 + 0.1 * ss(0.3, 0.75, ty / fh))[..., None]
			part = over(part, TL_GAP, side * TILE_SIDE)
			# moss creeps onto whole tiles, in clusters low on the slope, from the course above downward with a torn edge
			fy = (y0 + fh) / H
			fx = cx / W
			end_bias = 0 if mossy_end is None else (fx if mossy_end > 0 else 1 - fx) * 0.35
			amount = (big_at(y0 + fh / 2, cx) * 2.2 + fy * 0.3 + end_bias - 1.3 + moss * 0.2 + g.uniform(-0.1, 0.1))
			moss_px = np.zeros(ty.shape, np.float32)
			if moss and amount > 0:
				torn = smooth1d(xb - xa, max((xb - xa) // 3, 3), g) * fh * 0.1
				edge_y = fh * (0.42 + g.uniform(-0.1, 0.12)) + torn[None, :]
				cover = ss(edge_y + fh * 0.04, edge_y - fh * 0.04, ty)
				moss_px = cover * min(amount * 3.5, 1)
				part = over(part, MOSS_D, moss_px * 0.82)
				blot = gaussian_filter(g.random(ty.shape).astype(np.float32), (fh * 0.05, 0.05 * S))
				blot = np.clip((blot - blot.mean()) / (blot.std() + 1e-6) * 0.5, 0, 1)
				part = over(part, MOSS_L, moss_px * ss(0.15, 0.55, blot) * 0.65)
			img[sl] = np.where(inside[..., None], part, img[sl])
			# a shade right on the course below is the gap's colour; the end's lit rim has its own level
			dist = curve - ty
			# rims light only in the slope's one sunlit patch and, more faintly, along the eave: a shape of light, not a scatter
			patch = math.exp(-(((cx / W - sun[0]) / 0.12) ** 2) - (((y0 + fh / 2) / H - sun[1]) / 0.14) ** 2) if sun else 0
			eave = 0
			level = max(patch * 0.6, eave)
			level = 0.0 if level < 0.12 else level
			rim = ss(0.1 * S, 0.0, np.abs(dist - 0.05 * S)) * inside * level * (0.6 + 0.4 * ss(1.0, 0.2, f)) * (1 - moss_px)
			high[sl] = np.maximum(high[sl], rim)
			tile_mask[sl] = np.maximum(tile_mask[sl], inside.astype(np.float32))
			x += tw
		# the lip: the course's thick end, dark, warmer towards the bottom
		yl0, yl1 = y0 + fh, y0 + fh + lh
		img[yl0:yl1] = TL_SHADOW * (0.8 + 0.3 * ((yy[yl0:yl1] - yl0) / max(lh, 1))[..., None])
	# big shapes across the slope: lighter near the ridge, a shade under the things standing on it
	vs = yy / H
	for ri, (y0, fh, lh) in enumerate(rows):
		img[y0 : y0 + fh + lh] *= darken(np.array(ri / max(nrows - 1, 1)) ** 1.5 * 0.85, 0.85)
	for sh in shadows:
		ax0, ax1, sy0, sy1 = [c * S for c in sh]
		box = ((xx > ax0) & (xx < ax1) & (yy > sy0) & (yy < sy1)).astype(np.float32)
		img = shade(img, np.roll(box, (int(0.25 * S), int(0.14 * S)), (0, 1)) > 0.5, 1.0)
		img = over(img, TL_SHADOW, gaussian_filter(box, 0.3 * S) * 0.3)
	img = np.clip(img + (img - gaussian_filter(img, (1.2 * SS, 1.2 * SS, 0))) * 0.55, 0, 255)
	img = over(img, EDGE, gaussian_filter(high, 0.5 * SS) * 0.46)
	img = over(img, EDGE_PALE, gaussian_filter(high, (0.1 * S, 0.14 * S)) * 0.2)
	return np.clip(img, 0, 255)


def paint_soffit(r):
	g = child()
	H, W = r.h * SS, r.w * SS
	img = np.zeros((H, W, 3))
	img[:] = SOFFIT
	for yy in range(0, H, max(int(0.8 * ROOF.T * SS), 8)):
		img[yy : yy + 2 * SS] = SOFFIT * 0.6
	return img


SOFFIT_RECT = ROOF.add((2.2, 2.2), paint_soffit)


def tiled(A, B, E, n_courses, out, shadows=(), lift=0.3, nx=12, moss=0.5, mossy_end=None, sun=None):
	"""one roof slope, A-B along the ridge, A-E down the slope; n_courses stepped rows of tiles, under them a dark underside"""
	A, B, E = np.array(A, float), np.array(B, float), np.array(E, float)
	along, down = B - A, E - A
	width, length = np.linalg.norm(along), np.linalg.norm(down)
	nrm = unit(np.cross(along, down))
	if np.dot(nrm, out) < 0:
		nrm = -nrm
	over_s = 0.16
	course_h = length / n_courses
	courses = [(course_h + over_s, lift + 0.04)] * n_courses
	total = sum(a + b for a, b in courses)
	sub = child()
	rect = ROOF.add((width, total), None)
	rect.paint = lambda r: (rim_roof if RIM else (lambda i, S: i))(paint_roof(r, courses, width, lift, shadows, sub, moss, mossy_end, sun), ROOF.T * SS)

	def build():
		T = ROOF.T
		g2 = np.random.default_rng(int(rng.integers(1 << 31)))
		y = rect.y
		for i in range(n_courses):
			s0 = max(i * course_h - over_s, 0)
			s1 = (i + 1) * course_h
			lp = lift + 0.04
			jit = g2.normal(0, 0.05, nx + 1)
			lj = g2.normal(0, 0.035, nx + 1)
			gf, gl = MR.new_group(), MR.new_group()
			fh_px, lh_px = int((course_h + over_s) * T), int(lp * T)
			for k in range(nx):
				a, b = k / nx, (k + 1) / nx
				ua, ub = rect.x + a * rect.w, rect.x + b * rect.w
				t = lambda f, s, h=0.0, j=0.0: A + along * f + down * (s + j) / length + nrm * h
				MR.quad([t(a, s0), t(b, s0), t(b, s1, lift + lj[k + 1], jit[k + 1]), t(a, s1, lift + lj[k], jit[k])], [(ua, y), (ub, y), (ub, y + fh_px), (ua, y + fh_px)], nrm, gf)
				MR.quad([t(a, s1, lift + lj[k], jit[k]), t(b, s1, lift + lj[k + 1], jit[k + 1]), t(b, s1, -0.04, jit[k + 1]), t(a, s1, -0.04, jit[k])], [(ua, y + fh_px), (ub, y + fh_px), (ub, y + fh_px + lh_px), (ua, y + fh_px + lh_px)], unit(down), gl)
			for f, j, sign in ((0.0, 0, -1), (1.0, nx, 1)):
				x = rect.x + 2 if sign < 0 else rect.x + rect.w - 2
				p0 = A + along * f + down * s0 / length
				p1 = A + along * f + down * (s1 + jit[j]) / length + nrm * (lift + lj[j])
				p2 = A + along * f + down * (s1 + jit[j]) / length - nrm * 0.04
				MR.tri((p0, p1, p2), ((x, y + fh_px + 1), (x, y + fh_px + 1), (x, y + fh_px + 2)), along * sign, 0)
			y += fh_px + lh_px
		# the underside
		nv = 4
		g = MR.new_group()
		for k in range(nx):
			for j in range(nv):
				a, b = k / nx, (k + 1) / nx
				c, d = j / nv, (j + 1) / nv
				t = lambda f, s: A + along * f + down * s - nrm * 0.05
				u = lambda f, s: (SOFFIT_RECT.x + 2 + (SOFFIT_RECT.w - 4) * f, SOFFIT_RECT.y + 2 + (SOFFIT_RECT.h - 4) * s)
				MR.quad([t(a, c), t(b, c), t(b, d), t(a, d)], [u(a, c), u(b, c), u(b, d), u(a, d)], -nrm, g)

	emit.append(build)


# ---------------------------------------------------------------- windows, the door
def window(face, cu, v0, w, h, shutters=True, rng_lean=0.0):
	v1 = v0 + h
	d = 0.1
	glass = JOIN.add((w, h), paint_glass)
	TAGS["glass"].append(glass)

	def build():
		plate([face.at(cu - w / 2, v0, d), face.at(cu + w / 2, v0, d), face.at(cu + w / 2, v1, d), face.at(cu - w / 2, v1, d)], glass, face.out, 0.08)

	emit.append(build)
	face.block(cu - w / 2, v0, cu + w / 2, v1)
	FW, FD = 0.36, 0.5
	face.beam((cu - w / 2 - FW / 2 + 0.02, v0 - 0.1), (cu - w / 2 - FW / 2 - 0.02, v1 + 0.1), w=FD, h=FW, d=0.24, ch=0.06)
	face.beam((cu + w / 2 + FW / 2 - 0.02, v0 - 0.1), (cu + w / 2 + FW / 2 + 0.03, v1 + 0.1), w=FD, h=FW, d=0.24, ch=0.06)
	face.beam((cu - w / 2 - 0.48, v1 + FW / 2 + 0.03), (cu + w / 2 + 0.48, v1 + FW / 2 - 0.03), w=FD + 0.08, h=FW + 0.08, d=0.27, ch=0.07, knots=0)
	# the sill: a thick plank sticking out, higher at one end
	face.beam((cu - w / 2 - 0.58, v0 - 0.2), (cu + w / 2 + 0.58, v0 - 0.15), w=0.95, h=0.42, d=0.36, ch=0.08, hidden_back=True, hero=True)
	# glazing bars
	face.beam((cu + 0.02, v0), (cu - 0.03, v1), w=0.2, h=0.17, d=0.16, ch=0.04, knots=0)
	face.beam((cu - w / 2, v0 + h * 0.52), (cu + w / 2, v0 + h * 0.5), w=0.2, h=0.17, d=0.16, ch=0.04, knots=0)
	if not shutters:
		return
	sw = w * 0.5 + 0.05
	for side in (-1, 1):
		hinge = cu + side * (w / 2 + FW + 0.04)
		outer = hinge + side * sw
		droop = rng.uniform(-SHUTTER_DROOP, SHUTTER_DROOP)
		bot, top = v0 - 0.1, v1 + 0.08
		rect = JOIN.add((sw, top - bot), paint_shutter)
		TAGS["sage"].append(rect)
		dh, do = 0.32, 0.32 + rng.uniform(*SHUTTER_OPEN)
		corners = [face.at(hinge, bot, dh), face.at(outer, bot + droop, do), face.at(outer, top + droop, do), face.at(hinge, top, dh)]
		emit.append(lambda c=corners if side > 0 else [corners[1], corners[0], corners[3], corners[2]], rect=rect: plate(c, rect, face.out, 0.14))
		face.block(min(hinge, outer), bot, max(hinge, outer), top)
		# the battens: two rails and a brace, all painted in sage
		lerp = lambda f, v: (hinge + (outer - hinge) * f, v + droop * f, dh + (do - dh) * f + 0.08)
		for fv in (0.16, 0.84):
			v = bot + (top - bot) * fv
			p0, p1 = lerp(0.04, v), lerp(0.96, v)
			Beam(face.at(p0[0], p0[1], p0[2]), face.at(p1[0], p1[1], p1[2]), face.out, 0.14, 0.32, ch=0.04, scheme_name="Sage", face=None, knots=0, rings=2, bend=0.01, panel=(bot, top))


def door(face, cu, w, v0, h):
	rect = JOIN.add((w, h), paint_door)
	TAGS["sage"].append(rect)
	back = JOIN.add((0.3, 0.3), paint_soot)
	d = 0.2

	def arch(f):
		return 0.9 + 0.1 * math.sqrt(max(1 - (2 * f - 1) ** 2, 0))

	def build():
		plate([face.at(cu - w / 2, v0, d), face.at(cu + w / 2, v0, d), face.at(cu + w / 2, v0 + h, d), face.at(cu - w / 2, v0 + h, d)], rect, face.out, 0.14, tops=arch, nx=6, ny=2)
		plate([face.at(cu - w / 2 - 0.1, v0 - 0.3, 0.06), face.at(cu + w / 2 + 0.1, v0 - 0.3, 0.06), face.at(cu + w / 2 + 0.1, v0 + h + 0.1, 0.06), face.at(cu - w / 2 - 0.1, v0 + h + 0.1, 0.06)], back, face.out, 0.05)

	emit.append(build)
	face.block(cu - w / 2, v0, cu + w / 2, v0 + h)
	# chunky posts into the ground, a lintel that is not quite level
	return rect


# ---------------------------------------------------------------- the house
def build_house():
	front = Face("front", (0, 0, HZ), (1, 0, 0), (0, 0, 1))
	back = Face("back", (0, 0, -HZ), (-1, 0, 0), (0, 0, -1))
	right = Face("right", (HX, 0, 0), (0, 0, -1), (1, 0, 0))
	left = Face("left", (-HX, 0, 0), (0, 0, 1), (-1, 0, 0))
	gable_r = Face("gableR", (HX + JET, 0, 0), (0, 0, -1), (1, 0, 0))
	gable_l = Face("gableL", (-HX - JET, 0, 0), (0, 0, 1), (-1, 0, 0))
	roofline = lambda z: RIDGE_Y - abs(z) * SLOPE
	wall_top_fb = roofline(HZ)
	WALL_V0 = FOOT_Y - 0.5
	# ---- front: the door surround is the feature; one brace answers it across the wide plaster bay
	du, dw = -1.56, 3.5  # door centre and width
	dv0, dh = 0.35, 6.5
	PLATE = 9.1
	front.beam((-HX - 0.3, PLATE + 0.06), (HX + 0.3, PLATE - 0.06), w=0.66, h=0.74, unique=True, knots=1, d=0.2)
	front.beam((-HX - 0.25, FOOT_Y + 0.28), (du - dw / 2 - 0.35, FOOT_Y + 0.33), h=0.58, unique=True)
	front.beam((du + dw / 2 + 0.35, FOOT_Y + 0.33), (HX + 0.25, FOOT_Y + 0.26), h=0.58, unique=True)
	front.beam((-HX + 0.1, FOOT_Y), (-HX + 0.06, PLATE + 0.25), w=0.7, h=0.8, unique=True, d=0.2)
	front.beam((HX - 0.1, FOOT_Y), (HX - 0.05, PLATE + 0.25), w=0.7, h=0.8, unique=True, d=0.2)
	front.beam((du - dw / 2 - 0.42, -0.5), (du - dw / 2 - 0.36, dv0 + dh + 0.75), w=0.72, h=0.7, unique=True, foot=True, d=0.22, hero=True)
	front.beam((du + dw / 2 + 0.42, -0.5), (du + dw / 2 + 0.36, dv0 + dh + 0.75), w=0.72, h=0.7, unique=True, foot=True, d=0.22)
	front.beam((du - dw / 2 - 0.75, dv0 + dh + 0.5), (du + dw / 2 + 0.8, dv0 + dh + 0.38), w=0.84, h=0.74, unique=True, d=0.3, knots=1, hero=True, nails=((0.05, 0.3), (0.95, 0.3)))
	door(front, du, dw, dv0, dh)
	FRONT_WINDOW = 3.0  # the two front windows are one size, on one line
	window(front, 5.48, 4.2, FRONT_WINDOW, FRONT_WINDOW)
	window(front, -7.04, 4.2, FRONT_WINDOW, FRONT_WINDOW, shutters=False)
	front.beam((10.0, PLATE - 1.75), (8.35, PLATE - 0.2), h=0.44, w=0.42, d=0.12)  # one knee brace, high in the far corner
	# ---- back: two windows and one post off-centre; the rest is left plain
	back.beam((-HX - 0.3, PLATE - 0.04), (HX + 0.3, PLATE + 0.08), w=0.66, h=0.74, d=0.2)
	back.beam((-HX - 0.25, FOOT_Y + 0.3), (HX + 0.25, FOOT_Y + 0.28), h=0.58)
	for u, lean in ((-HX + 0.1, 0.04), (HX - 0.1, -0.05), (1.1, -0.06)):
		back.beam((u, FOOT_Y), (u + lean, PLATE + 0.1), h=0.66, d=0.16)
	window(back, -5.7, 4.2, 2.2, 2.2)
	window(back, 5.6, 4.1, 2.2, 2.25)
	# ---- sides, under the jetty: corners, one long brace opposite the window
	for f, cu, sign in ((right, -2.6, -1), (left, -2.5, 1)):
		f.beam((-HZ, EAVE_Y - 0.45), (HZ, EAVE_Y - 0.5), w=0.62, h=0.62)
		f.beam((-HZ - 0.1, FOOT_Y + 0.28), (HZ + 0.1, FOOT_Y + 0.3), h=0.58)
		f.beam((-HZ + 0.15, FOOT_Y), (-HZ + 0.1, EAVE_Y - 0.3), w=0.7, h=0.8, d=0.2)
		f.beam((HZ - 0.15, FOOT_Y), (HZ - 0.08, EAVE_Y - 0.3), w=0.7, h=0.8, d=0.2)
		if f is left:
			f.beam((sign * 5.4, FOOT_Y + 0.5), (sign * 0.4, EAVE_Y - 0.8), h=0.46, w=0.42, d=0.1)
		window(f, cu, 4.25, 2.2, 2.2)
	# brackets and the big beam the gable stands on; above it only the window and a king post
	for f, g, s_ in ((right, gable_r, 1), (left, gable_l, -1)):
		for u in (-4.9, 4.9):
			p0 = f.at(u + rng.uniform(-0.1, 0.1), EAVE_Y - 1.9 + rng.uniform(-0.1, 0.1), 0.2)
			p1 = f.at(u, EAVE_Y - 0.25, JET + 0.1)
			Beam(p0, p1, f.right, 0.5, 0.5, ch=0.07, face=None, hidden_back=False, rings=2, knots=0)
		g.beam((-6.3, EAVE_Y - 0.08), (6.3, EAVE_Y + 0.06), w=1.15, h=0.66, d=-0.3, unique=s_ > 0, knots=1)
		gt = lambda u, off=0.0: roofline(u) - off
		g.beam((-6.05, EAVE_Y + 0.2), (-6.0, gt(-6.0, 0.5)), h=0.5, w=0.48)
		g.beam((6.05, EAVE_Y + 0.2), (6.0, gt(6.0, 0.5)), h=0.5, w=0.48)
		if s_ < 0:
			g.beam((0.02, 14.9), (0.05, gt(0, 0.6)), h=0.5, w=0.48)
		window(g, 0.0 if s_ < 0 else -2.0, 11.7, 2.4 if s_ < 0 else 2.2, 2.4 if s_ < 0 else 2.2, shutters=s_ < 0)
	# ---- walls
	wall(front, -HX, HX, WALL_V0, lambda u: wall_top_fb, shade_y=EAVE_Y)
	wall(back, -HX, HX, WALL_V0, lambda u: wall_top_fb, shade_y=EAVE_Y)
	wall(right, -HZ, HZ, WALL_V0, lambda u: EAVE_Y + 0.2, cols=5)
	wall(left, -HZ, HZ, WALL_V0, lambda u: EAVE_Y + 0.2, cols=5)
	wall(gable_r, -6.2, 6.2, EAVE_Y, lambda u: roofline(u), cols=6)
	wall(gable_l, -6.2, 6.2, EAVE_Y, lambda u: roofline(u), cols=6)
	# ---- the stone footing, sides sharing one painted run
	footing(front, -HX - 0.45, du - dw / 2 - 0.72, cap_ends=True)
	footing(front, du + dw / 2 + 0.72, HX + 0.45, cap_ends=True)
	footing(back, -HX - 0.45, HX + 0.45)
	footing(right, -HZ - 0.45, HZ + 0.45, shared="side")
	footing(left, -HZ - 0.45, HZ + 0.45, shared="side")
	# ---- roof: two big slopes, a dormer, a hood over the door
	ez_s = np.hypot(EAVE_Z, RIDGE_Y - EAVE_Y)
	L = ez_s
	z_to_s = lambda z: abs(z) / EAVE_Z * L
	roof_w = 2 * ROOF_X
	dormer_shadow = (ROOF_X + DORMER_X - 2.9, ROOF_X + DORMER_X + 2.9, z_to_s(1.2), z_to_s(4.35))
	tiled((-ROOF_X, RIDGE_Y, 0), (ROOF_X, RIDGE_Y, 0), (-ROOF_X, EAVE_Y, EAVE_Z), 8, (0, 1, 1), shadows=[dormer_shadow], moss=0, sun=(0.24, 0.42))
	tiled((ROOF_X, RIDGE_Y, 0), (-ROOF_X, RIDGE_Y, 0), (ROOF_X, EAVE_Y, -EAVE_Z), 8, (0, 1, -1), mossy_end=1, moss=0.5, sun=(0.72, 0.5))
	Beam((-ROOF_X - 0.25, RIDGE_Y + 0.14, 0), (ROOF_X + 0.25, RIDGE_Y + 0.14, 0), (0, 0, 1), 1.15, 0.5, ch=0.14, scheme_name="Clay", knots=0, rings=11, bend=0.02, hidden_back=False, unique=True)
	# barge boards along the gable edges, fascia plates
	bn = unit((0, EAVE_Z, RIDGE_Y - EAVE_Y))
	for x, sign in ((ROOF_X, 1), (-ROOF_X, -1)):
		for zs in (1, -1):
			Beam((x, RIDGE_Y + 0.05, 0), (x, EAVE_Y - 0.2, zs * (EAVE_Z + 0.22)), (sign, 0, 0), 0.34, 0.86, ch=0.07, hidden_back=False, unique=sign > 0, knots=1, rings=5, hero=True)
	# ---- dormer
	dx = DORMER_X
	dz = 4.15
	dw2 = 2.15
	dtop = 16.35
	dpeak = 17.65
	dv0 = 13.2
	dfront = Face("dormer", (dx, 0, dz), (1, 0, 0), (0, 0, 1))
	dlin = lambda u: min(dtop + (dpeak - dtop) * (1 - abs(u) / dw2), dpeak)
	wall(dfront, -dw2, dw2, dv0, dlin, cols=4, rows=3)
	window(dfront, 0.0, 14.45, 1.75, 1.6, shutters=False)
	dfront.beam((-dw2 - 0.1, 13.7), (-dw2 + 0.05, dtop + 0.1), h=0.56, w=0.5, d=0.14)
	dfront.beam((dw2 + 0.1, 13.7), (dw2 - 0.04, dtop + 0.1), h=0.56, w=0.5, d=0.14)
	dfront.beam((-dw2 - 0.35, dtop), (dw2 + 0.35, dtop + 0.08), h=0.56, w=0.56, d=0.18)
	# cheeks
	for s in (1, -1):
		ch = Face("cheek", (dx + s * dw2, 0, 0), (0, 0, -s), (s, 0, 0))
		wall(ch, -dz, -2.0, dv0, lambda u: dtop, cols=2, rows=2) if s > 0 else wall(ch, 2.0, dz, dv0, lambda u: dtop, cols=2, rows=2)
	dA, dE = 5.0, 1.4  # dormer ridge, front to back
	over_x = 0.6
	sl_e = dtop - 0.3
	for s in (1, -1):
		a, b = ((dx, dpeak + 0.05, dE), (dx, dpeak + 0.05, dA)) if s > 0 else ((dx, dpeak + 0.05, dA), (dx, dpeak + 0.05, dE))
		e = (dx + s * (dw2 + over_x), sl_e, a[2])
		tiled(a, b, e, 3, (s, 1, 0), lift=0.22, nx=4, moss=0.25)
		Beam((dx, dpeak + 0.03, dA + 0.06), (dx + s * (dw2 + over_x + 0.04), sl_e - 0.12, dA + 0.06), (0, 0, 1), 0.26, 0.44, ch=0.06, hidden_back=False, rings=2, knots=0)
	Beam((dx, dpeak + 0.18, dA + 0.14), (dx, dpeak + 0.12, dE), (1, 0, 0), 0.72, 0.36, ch=0.09, scheme_name="Clay", knots=0, rings=3, hidden_back=False, bend=0.015)
	# ---- the door's little hood, on two brackets
	hx0, hx1 = du - dw / 2 - 0.62, du + dw / 2 + 0.66
	tiled((hx0, 8.85, HZ + 0.2), (hx1, 8.85, HZ + 0.2), (hx0, 7.95, HZ + 1.6), 2, (0, 1, 1), lift=0.2, nx=4, moss=0.0)
	for u in (hx0 + 0.35, hx1 - 0.35):
		Beam((u, 6.5, HZ + 0.25), (u, 7.95, HZ + 1.4), (1, 0, 0), 0.34, 0.38, ch=0.06, hidden_back=False, rings=2, knots=0)
	# ---- chimney: the house's one big feature. A broad stone breast from the ground, a sloped shoulder, a narrower stack past the ridge
	cx, cz = CHIMNEY
	Beam((cx + 0.36, 21.45, cz + 0.1), (cx + 0.46, 22.6, cz + 0.08), (0, 0, 1), 0.9, 0.9, ch=0.15, scheme_name="Clay", knots=0, rings=2, bend=0.01, hidden_back=False, cap_top=SOOT)


def add_joints():
	"""connecting pieces where a main post meets a beam: a chunky collar under the beam, a shoe at the post's foot, both pegged. Only on the frame's posts, so the small joinery stays calm"""
	for post in list(BEAMS):
		if post.face is None or post.scheme != "Chestnut" or post.h < 0.6 or post.hero and post.foot:
			continue
		ax = unit(post.p1 - post.p0)
		if abs(ax[1]) < 0.85:
			continue
		at = lambda y: post.p0 + (post.p1 - post.p0) * (y - post.p0[1]) / (post.p1[1] - post.p0[1])
		top, foot = None, None
		for beam in BEAMS:
			bx = beam.p1 - beam.p0
			if beam is post or beam.face is None or beam.scheme != "Chestnut" or beam.h < 0.5 or abs(unit(bx)[1]) > 0.3 or abs(np.dot(unit(beam.front), unit(post.front))) < 0.9:
				continue
			if abs(np.dot(beam.p0 - post.p0, unit(post.front))) > 1.3:
				continue
			f = np.dot(post.p0 - beam.p0, unit(bx)) / np.dot(bx, unit(bx))
			if not -0.02 <= f <= 1.02:
				continue
			y = beam.p0[1] + bx[1] * f
			if abs(y - post.p1[1]) < 1.0:
				top = y - beam.h / 2
			if abs(y - post.p0[1]) < 0.8:
				foot = y + beam.h / 2
		kw = dict(ch=0.08, scheme_name="Chestnut", knots=0, rings=2, bend=0.0, hidden_back=post.hidden_back, nails=((0.5, 0.55),))
		if top is not None:
			Beam(at(top - JOINT_COLLAR), at(top + 0.03), post.front, post.w + JOINT_GROW * 0.8, post.h + JOINT_GROW, **kw)
		if not post.foot:
			y0 = foot if foot is not None else post.p0[1]
			Beam(at(y0 - 0.03), at(y0 + JOINT_SHOE), post.front, post.w + JOINT_GROW * 0.8, post.h + JOINT_GROW, **kw)


def rect_tags():
	box = lambda r: [r.x, r.y, r.w, r.h]
	return {
		"glass": [box(r) for r in TAGS["glass"]],
		"stone": [box(r) for r in TAGS["stone"]],
		"sage": [box(r) for r in TAGS["sage"]] + [box(s.rect) for s in STRIPS if s.name == "Sage"],
		"frame_other": [box(s.rect) for s in STRIPS if s.name not in ("Chestnut", "Sage") and s.atlas is WOOD],
		"joinery_other": [box(s.rect) for s in STRIPS if s.name not in ("Chestnut", "Sage") and s.atlas is JOIN] + [box(SOOT)],
	}


@contextlib.contextmanager
def fixed_grain():
	"""paint_strip with its marks sized in studs on long strips, by wrapping the two functions it draws with (woodbridge_kit.py's method). The fence's own painter is untouched"""
	real_lines, real_stroke = FP["paint_lines"], FP["stroke"]
	stud = SS * PAINT_T

	def lines(shape, count, length, half, g, wander, xspan=(-0.1, 0.6)):
		k = max(1.0, shape[1] / (GRAIN_REF * stud))
		if k > 1:
			xspan = (-0.04, 0.98)
		mask = real_lines(shape, int(round(count * k)), (length[0] / k, length[1] / k), half, g, wander, xspan)
		return mask * (GRAIN_QUIET if k > 1 else 1.0)

	def strokes(m, x0, x1, y, half, colour, g, **kw):
		H, L = m.shape[:2]
		k = max(1.0, L / (GRAIN_REF * stud))
		for _ in range(int(round(k))):
			a = g.uniform(-0.08, 0.95) * L if k > 1 else x0
			if k > 1:
				kw_ = dict(kw)
				kw_["alpha"] = kw.get("alpha", 1.0) * GRAIN_QUIET
				real_stroke(m, a, a + (x1 - x0) / k, g.uniform(0, H), half, colour, g, **kw_)
			else:
				real_stroke(m, a, a + (x1 - x0) / k, y, half, colour, g, **kw)

	FP["paint_lines"], FP["stroke"] = lines, strokes
	yield
	FP["paint_lines"], FP["stroke"] = real_lines, real_stroke


def stretch_report(out_dir, sheets):
	"""how far each triangle's texels stray from its sheet's scale, and how long the painted marks on long timbers are, in studs"""
	result = {"Texels": {}, "Marks": []}
	off_by = {}
	caps = {}
	for a in (WOOD, JOIN):
		caps[a.name] = [(c.x, c.y, c.w, c.h) for c in END_CAPS[a.name]] + [(c.x, c.y, c.w, c.h) for k, c in END_FIT.items() if k[0] == a.name]
	for m in (MW, MJ):
		T = m.atlas.T
		table = {"sides": [0.0, 0.0, 1.0, 1.0], "ends": [0.0, 0.0, 1.0, 1.0]}
		for i, j, k in m.tris:
			p = [np.array(m.v[n]) for n in (i, j, k)]
			uv = [m.uv[n] for n in (i, j, k)]
			e1, e2 = p[1] - p[0], p[2] - p[0]
			nrm = np.cross(e1, e2)
			area = np.linalg.norm(nrm) / 2
			if area < 1e-5:
				continue
			x_ = unit(e1)
			y_ = unit(np.cross(nrm, x_))
			M = np.array(((e1 @ x_, e2 @ x_), (e1 @ y_, e2 @ y_)))
			U = np.array(((uv[1][0] - uv[0][0], uv[2][0] - uv[0][0]), (uv[1][1] - uv[0][1], uv[2][1] - uv[0][1])))
			s = np.linalg.svd(U @ np.linalg.inv(M), compute_uv=False)
			is_cap = any(all(cx - 1 <= t[0] <= cx + cw + 1 and cy - 1 <= t[1] <= cy + ch + 1 for t in uv) for cx, cy, cw, ch in caps[m.atlas.name])
			if s[1] < 0.5:
				continue  # a sliver mapped onto one texel on purpose: a tile's edge, no paint to stretch
			row = table["ends" if is_cap else "sides"]
			row[0] += area
			row[1] += area if (s[0] > T * 1.15 or s[1] < T * 0.85) else 0
			if not is_cap and (s[0] > T * 1.15 or s[1] < T * 0.85):
				u_, v_ = np.mean([t[0] for t in uv]), np.mean([t[1] for t in uv])
				for r_ in m.atlas.rects:
					if r_.x <= u_ <= r_.x + r_.w and r_.y <= v_ <= r_.y + r_.h:
						who = next((f"{s_.name} strip L{s_.length:.1f} w{s_.w:.2f} h{s_.h:.2f}" for s_ in STRIPS if s_.rect is r_), f"tile {r_.w}x{r_.h}")
						off_by[who] = off_by.get(who, 0) + area
						break
			row[2] = min(row[2], s[1] / T)
			row[3] = max(row[3], s[0] / s[1])
		result["Texels"][m.atlas.name] = {k: {"sq_studs": round(v[0], 1), "off_pct": round(v[1] / max(v[0], 1e-6) * 100, 1), "thinnest_vs_scale": round(v[2], 2), "worst_aspect": round(v[3], 2)} for k, v in table.items()}
	sheet = np.array(Image.open(os.path.join(out_dir, f"{PREFIX}_Frame.png")).convert("L"), float)
	for s in sorted((s for s in STRIPS if s.atlas is WOOD and s.name == "Chestnut"), key=lambda t: -t.length)[:6]:
		r, T = s.rect, WOOD.T
		y = r.y
		for px, kind in s.bands(T):
			if kind == "front":
				band = sheet[y + 1 : y + px - 1, r.x : r.x + r.w]
				break
			y += px
		d = band - gaussian_filter(band, (0, T * 6))  # wide, so a streak many studs long still counts
		dark = d < -max(d.std() * 0.8, 1.0)
		ac = np.mean([np.correlate(row - row.mean(), row - row.mean(), "full")[row.size - 1 :] / (np.sum((row - row.mean()) ** 2) * (1 - np.arange(row.size) / row.size) + 1e-6) for row in d], axis=0)
		half = np.argmax(ac < 0.5) if (ac < 0.5).any() else ac.size
		runs = []
		for row in dark:
			run = 0
			for v in row:
				if v:
					run += 1
				elif run:
					runs.append(run)
					run = 0
			if run:
				runs.append(run)
		runs = np.array(runs or [0]) / T
		result["Marks"].append({"length": round(s.length, 1), "uses": s.uses, "mark_p90_studs": round(float(np.percentile(runs, 90)), 2), "mark_max_studs": round(float(runs.max()), 2), "marks_per_stud": round(len(runs) / s.length / max(band.shape[0], 1), 3), "grain_correlation_studs": round(float(half) / T, 2)})
	result["Off_by_part"] = {k: round(v, 1) for k, v in sorted(off_by.items(), key=lambda kv: -kv[1])[:12]}
	json.dump(result, open(os.path.join(out_dir, "stretch.json"), "w"), indent=1)
	print(json.dumps(result))


def main(build=None):
	(build or build_house)()
	add_joints()
	for b in BEAMS:
		b.assign()
	for b in BEAMS:
		for o in BEAMS:
			if o is b or o.face != b.face or b.face is None or abs(np.dot(unit(o.p1 - o.p0), unit(b.p1 - b.p0))) > 0.97:
				continue
			f = segment_contact(b, o)
			if f is not None and b.strip.owner is b:
				b.strip.contacts.append((f, o.h))
	if FORM_FIT:
		for s in STRIPS:
			k = (s.atlas.name, round(s.w, 2), round(s.h, 2))
			if k not in END_FIT:
				g_ = np.random.default_rng(int(k[1] * 1000) * 7 + int(k[2] * 1000))
				END_FIT[k] = s.atlas.add((max(s.h, 0.3), max(s.w, 0.3)), lambda r, w=s.w, h=s.h, g=g_: paint_end_fit(r, w, h, g))
	for a in (WOOD, JOIN, WALL, ROOF):
		a.pack()
	print("texels per stud: frame %.1f, joinery %.1f, walls %.1f, roof %.1f" % (WOOD.T, JOIN.T, WALL.T, ROOF.T))
	base_scheme = np.array((124, 86, 66), float)
	sheets = [("Frame", WOOD, base_scheme), ("Joinery", JOIN, base_scheme), ("Walls", WALL, PL_BASE), ("Roof", ROOF, SOFFIT)]
	for b in BEAMS:
		b.build()
	for f in emit:
		f()
	report = {}
	for name, atlas, base in sheets:
		with (fixed_grain() if FORM_FIT and atlas in (WOOD, JOIN) else contextlib.nullcontext()):
			img = atlas.paint(base)
		out = Image.fromarray(np.clip(img * GRADE, 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS)
		out.save(os.path.join(OUT, f"{PREFIX}_{name}.png"))
		if atlas.normal is not None:
			Image.fromarray(np.clip(atlas.normal, 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS).save(os.path.join(OUT, f"{PREFIX}_{name}_Normal.png"))
	for m in (MW, MJ, ML, MR):
		m.finish()
		m.write(OUT)
		report[m.name] = len(m.tris)
	json.dump({"Triangles": report, "Total": sum(report.values()), "TexelsPerStud": {"Frame": WOOD.T, "Joinery": JOIN.T, "Walls": WALL.T, "Roof": ROOF.T}, "Beams": len(BEAMS), "Strips": len(STRIPS), "Rects": rect_tags()}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print(report, "total", sum(report.values()), "beams", len(BEAMS), "strips", len(STRIPS))
	if os.environ.get("HOUSE_STRETCH") == "1":
		stretch_report(OUT, sheets)


if __name__ == "__main__":
	main()
