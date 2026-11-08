"""The stone bridge (docs/style/art-style.md), system Python: chunky hand-laid stones and one painted sheet, the fence kit's method in stone.
Every stone is a pillow (a face and a chamfer band) drawn from a small set of painted stone cards, so the painter knows faces from edges and the edge highlights stay continuous.
Two sheets: the parts seen up close (deck, parapet, coping) at about 55 texels a stud, the fence is 50; the walls at about 28.
Writes into art/kit/bridge: Bridge_Color.png (walls), Bridge_Top_Color.png (close-up parts), Bridge<A,B,C,Loose,TopA,TopB,TopC>.obj, kit.json (triangles, pieces, colliders, how the ends meet the terrain).

  python tools/art/bridge_kit.py art/kit/bridge
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from crisp_paint import brushed_wash, chisel_marks, hewn_plane, jagged, lines, over, smooth1d, ss

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/bridge")
os.makedirs(OUT, exist_ok=True)
SPEC = "art/lands/verdant_vale/spec.json"
SHEET = 1024
SS = 2
GRADE = np.array((1.0, 0.985, 0.92))  # Studio reading: the lit wall came out 216 213 207 against Blender's 202 199 182, so bright enough but half as warm
SEED = 41

# --- the shape, in studs. Local axes: x along the bridge from From to To, y up (world height), z across
DECK = next(d for d in json.load(open(SPEC, encoding="utf-8"))["Decks"] if d["Name"] == "Stone bridge")
A, B = np.array(DECK["From"], float), np.array(DECK["To"], float)
L = float(np.linalg.norm(B - A))
LEVEL, RISE = DECK["Level"], DECK["Arch"]
HALF = DECK["Width"] / 2
WATER = 8.0
BED = 3.0
ABUT = 11.5
SPANS = (30.0, 38.0, 30.0)
PIER = 9.0
SPRING = 8.6
RING = 2.2  # voussoir depth
PARAPET = 2.2  # stone wall above the deck; the coping sits on it
COPING_H, COPING_W = 0.8, 2.5
INNER = HALF - 1.8  # the parapet's inner face
APRON = 7.0  # stone tongue running down into the road at each end
WING = 7.0  # the parapets flare out this far past the ends
FLARE = 3.0
NOSE = 3.4  # cutwaters stick out this far from the walls
WALL_UP = 15.0  # the parapet colliders reach this far above the stone: a character steps over anything under its hip height (3.8), and at 9 a single jump still landed on the invisible top
NOSE_TOP = 13.6
COURSE = 2.3  # every wall stone is this tall: rows stay parallel and line up on every face
WIDTHS = (2.2, 3.4, 4.4, 5.4)
JOINT = 0.05

# --- colours: Ghibli, not realism. Warm light stone, soft joints, shadows lavender rather than dark. Pick with: bridge_kit.py <folder> <scheme>
SCHEMES = {
	"Sandstone": dict(BASE=(190, 178, 156), LIGHT=(214, 202, 176), WARM=(204, 180, 146), DUSK=(158, 152, 158), COOL=(168, 170, 172), CRACK=(122, 112, 118), MORTAR=(112, 100, 114), SHADOW=(122, 120, 156), WET=(136, 146, 160), DECK_BASE=(206, 192, 164), DECK_LIGHT=(224, 210, 180), DECK_DUSK=(176, 166, 160)),
	"Dove": dict(BASE=(168, 170, 172), LIGHT=(196, 196, 190), WARM=(186, 176, 160), DUSK=(138, 142, 162), COOL=(150, 162, 178), CRACK=(104, 106, 128), MORTAR=(96, 94, 122), SHADOW=(108, 112, 156), WET=(120, 138, 160), DECK_BASE=(188, 184, 172), DECK_LIGHT=(208, 202, 186), DECK_DUSK=(158, 158, 166)),
	"Rose": dict(BASE=(186, 164, 150), LIGHT=(212, 190, 170), WARM=(206, 168, 136), DUSK=(154, 138, 150), COOL=(160, 152, 166), CRACK=(120, 100, 112), MORTAR=(112, 92, 108), SHADOW=(124, 110, 150), WET=(140, 136, 156), DECK_BASE=(204, 182, 160), DECK_LIGHT=(222, 202, 176), DECK_DUSK=(172, 156, 156)),
}
SCHEME = sys.argv[2] if len(sys.argv) > 2 else "Sandstone"
LOOK = sys.argv[3] if len(sys.argv) > 3 else "crisp"  # crisp or soft (docs/style/crisp-paint.md)
MARK_DARK, MARK_STRENGTH, SHARPEN, HIGHLIGHT_BLUR, RIM_BLUR = (0.94, 0.5, 0.9, 0.3, 0.4) if LOOK == "crisp" else (1.0, 0.42, 0.22, 0.5, 0.65)
for _key, _value in SCHEMES[SCHEME].items():
	globals()[_key] = np.array(_value, float)
EDGE = np.array((254, 246, 224), float)
EDGE_PALE = np.array((236, 226, 200), float)
MOSS = np.array((132, 182, 88), float)
MOSS_DARK = np.array((82, 142, 88), float)
ALGAE = np.array((104, 160, 138), float)
# what big shapes read from far away: light by height, tone by patch. Low stone goes cooler, not black
LEVEL_VALUE = {"lip": 1.02, "lit": 1.06, "mid": 1.0, "low": 0.93, "water": 0.86}
LEVEL_HIGHLIGHT = {"lip": 0.5, "lit": 1.0, "mid": 0.8, "low": 0.55, "water": 0.3}
TONE = {"base": np.array((1.0, 1.0, 1.0)), "pale": np.array((1.12, 1.08, 1.0)), "dark": np.array((0.86, 0.88, 0.98))}
# patches of tone on each face: (side, s, y, radius along, radius up, strength). Pale = sun-bleached and repairs; dark = cool damp
PATCHES = (
	(1, 52, 17, 11, 5, 1), (1, 118, 18, 10, 5, 1), (1, 22, 15, 8, 6, -1), (1, 84, 14, 6, 7, -1), (1, 104, 19, 3, 8, -1), (1, 136, 15, 7, 6, -1),
	(-1, 36, 18, 10, 5, 1), (-1, 98, 16, 11, 5, 1), (-1, 12, 14, 6, 6, -1), (-1, 68, 19, 3.5, 8, -1), (-1, 128, 17, 8, 6, -1),
)


def rhythm(n, rng, upper=1.0, spans=4):
	"""a level along an edge: strong runs, faint stretches, real gaps, eased between; never stops dead"""
	p = (0.14, 0.2, 0.3, 0.36) if upper >= 0.8 else (0.34, 0.3, 0.24, 0.12)
	levels = rng.choice((0.04, 0.22, 0.55, 1.0), size=spans + 2, p=p)
	f = np.interp(np.arange(n), np.linspace(-0.1, 1.1, spans + 2) * n, levels)
	return gaussian_filter(f, n / spans * 0.22)


def surface(H, W, rng, palette, facets=1):
	"""the stone's surface in gouache, the crisp method (tools/art/crisp_paint.py): big flat washes with firm brushed edges, one plane, chisel marks, a hairline"""
	base, light, warm, dusk, cool = palette
	yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
	img = np.empty((H, W, 3), np.float32)
	img[:] = base
	for colour, n, strength in ((light, 2, 0.46), (warm, 1, 0.34), (dusk, 1, 0.26), (cool, 1, 0.26)):
		for _ in range(n):
			img = brushed_wash(img, colour, strength, rng, SS)
	for _ in range(facets):
		img = hewn_plane(img, light, 0.14, rng, SS)
	img = chisel_marks(img, rng, dusk * MARK_DARK, light * 1.1, SS, MARK_STRENGTH)
	if rng.random() < 0.55:
		img = over(img, dusk * 0.9, gaussian_filter(lines((H, W), 1, (0.14, 0.34), 0.7 * SS, rng, H * 0.02), 0.25 * SS) * 0.6)
	return img, yy, xx


def moss_on(img, reach, rng, strength=1.0):
	"""moss where reach > 0.5: one calm shape with a broken edge and a darker lip, no speckle"""
	H, W = reach.shape
	n = jagged(H, W, rng, 3.5 * SS) * 0.055 + jagged(H, W, rng, 1.2 * SS) * 0.025
	img = over(img, MOSS_DARK, gaussian_filter(ss(0.4, 0.47, reach + n), 0.7 * SS) * 0.75 * strength)
	img = over(img, MOSS, ss(0.48, 0.54, reach + n) * 0.92 * strength)
	return img


def patches(n, rng, count=2, low=0.0):
	"""a level along a side that is zero except for a few patches"""
	f = np.full(n, low, np.float32)
	for _ in range(count):
		c, w = rng.uniform(0, n), rng.uniform(0.12, 0.3) * n
		f = np.maximum(f, np.exp(-(((np.arange(n) - c) / w) ** 2)))
	return f


class Card:
	"""one painted stone: a face and the chamfer band round it, in one island of the sheet"""

	def __init__(self, sheet, name, w, h, b, tx, state, rng):
		self.name, self.w, self.h, self.b, self.state = name, w, h, b, state
		W, H = int(round((w + 2 * b) * tx)), int(round((h + 2 * b) * tx))
		self.x, self.y = sheet.place(W, H)
		self.W, self.H = W, H
		self.mx, self.my = b / (w + 2 * b), b / (h + 2 * b)
		sheet.img[self.y * SS : (self.y + H) * SS, self.x * SS : (self.x + W) * SS] = paint_card(W * SS, H * SS, b * tx * SS, state, rng)

	def uv(self, fu, fv):
		return (self.x + 1 + fu * (self.W - 2), self.y + 1 + fv * (self.H - 2))


def paint_card(W, H, bp, state, rng):
	state, tone = state.split("/") if "/" in state else (state, "base")
	deck = state.startswith("deck")
	palette = (DECK_BASE, DECK_LIGHT, DECK_LIGHT * 0.98, DECK_DUSK, DECK_DUSK * 1.03) if deck else (BASE, LIGHT, WARM, DUSK, COOL)
	img, yy, xx = surface(H, W, rng, palette, 1)
	cx, cy = W / 2, H / 2
	hw, hh = W / 2 - bp, H / 2 - bp
	r = min(bp * 0.7, min(hw, hh) * 0.5)
	wobble = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), bp * 0.9)
	wobble = wobble / (np.abs(wobble).max() + 1e-6) * bp * 0.14
	qx, qy = np.abs(xx - cx) - (hw - r), np.abs(yy - cy) - (hh - r)
	sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r + wobble  # 0 at the crest, bp at the rim
	v = yy / H
	# painted light: lit top, dark foot, per stone
	if not deck:
		img *= (1.05 - 0.1 * ss(0.15, 1.0, v))[..., None]
	# chamfer band: lit above, shaded below, turning into the mortar at the rim
	up = np.clip((cy - yy) / max(hh, 1), -1, 1)
	band = ss(0, bp * 0.7, sd)
	img = img * (1 + (band * (0.12 * up - 0.14 * (up < 0)))[..., None])
	img = over(img, SHADOW, band * ss(0.1, 1, -up) * 0.3)
	if state == "mossy":
		img *= 1.05
	if state in LEVEL_VALUE:
		img = img * LEVEL_VALUE[state]
	img = img * TONE[tone]
	if state == "lip":
		# the ledge's shadow: a clean lavender shape, cel-painted
		img = over(img, SHADOW, ss(0.34, 0.26, v + jagged(H, W, rng, 5 * SS) * 0.02) * 0.42)
	if state == "low":
		img = over(img, WET, ss(0.3, 1.0, v) * 0.3)
	if state == "water":
		img = over(img, WET, ss(0.0, 0.7, v) * 0.45)
		img = over(img, ALGAE, ss(0.5, 0.56, v + jagged(H, W, rng, 5 * SS) * 0.035) * 0.8)
	if state == "mossy":
		img = moss_on(img, ss(0.34, 0.0, v) * patches(W, rng, 2)[None, :] * 0.95, rng)
	if state == "deck_side":
		img = moss_on(img, ss(0.72, 1.0, xx / W) * patches(H, rng, 2)[:, None] * 0.95, rng)
	img = np.clip(img + (img - gaussian_filter(img, (1.1 * SS, 1.1 * SS, 0))) * SHARPEN, 0, 255)
	# edge highlights, the fence's recipe: each side its own rhythm, upper sides carry it, worn spots bleed off into the face
	high = np.zeros((H, W), np.float32)
	streak = gaussian_filter(rng.random((H, W)).astype(np.float32), (0.35 * SS, 5 * SS))
	streak = np.clip((streak - streak.mean()) / (streak.std() * 1.6) * 0.5 + 0.5, 0, 1)
	levels = {**LEVEL_HIGHLIGHT, "mossy": 0.85, "deck": 0.55, "deck_side": 0.4}[state]
	sides = (
		(cy - yy, xx, W, 1.0),  # top
		(cx - xx, yy, H, 0.62),  # the sun's side
		(xx - cx, yy, H, 0.3),
		(yy - cy, xx, W, 0.08 if not deck else 0.5),
	)
	near = np.stack([s[0] / (hh if i in (0, 3) else hw) for i, s in enumerate(sides)])
	which = near.argmax(axis=0)
	line = 0.5 * bp + 0.7 * SS
	for i, (_d, along, n, weight) in enumerate(sides):
		f = rhythm(n, rng, weight, max(3, n // (46 * SS)))
		extra = np.zeros(n)
		for _ in range(int(rng.integers(0, 3)) if weight >= 0.6 else 0):
			c, reach = rng.uniform(0.1, 0.9) * n, rng.uniform(0.07, 0.16) * n
			bump = np.exp(-(((np.arange(n) - c) / reach) ** 2))
			f = np.maximum(f, bump * rng.uniform(0.7, 1))
			extra = np.maximum(extra, bump * rng.uniform(2, 4.2) * line)
		idx = np.clip(along.astype(int), 0, n - 1)
		core = ss(line, 0, np.abs(sd)) ** 1.3
		ex = extra[idx]
		bleed = ss(line + ex + 1e-3, line * 0.3, np.abs(sd)) * (ex > 0.5) * (sd < 0) * (0.25 + 0.75 * streak)
		high = np.maximum(high, np.maximum(core, bleed) * f[idx] * weight * levels * (which == i))
	high = gaussian_filter(high, HIGHLIGHT_BLUR * SS)
	img = over(img, EDGE, high * 0.85)
	img = over(img, EDGE_PALE, gaussian_filter(high, (3.5 * SS, 7 * SS)) * 0.65)
	# the rim: stone turns into the dark joint with a soft crisp edge, so a square quad reads hand cut
	img = over(img, MORTAR, gaussian_filter((sd > bp * 0.96).astype(np.float32), RIM_BLUR * SS))
	return np.clip(img, 0, 255)


class BeamCard:
	"""a long stone's sides unrolled: back, edge, top, edge, front"""

	def __init__(self, sheet, name, length, w, h, e, tx, state, rng, end=None):
		self.name, self.length, self.end = name, length, end
		self.bands = [(h, "back"), (e, "edge"), (w - 2 * e, "top"), (e, "edge"), (h, "front")]
		Lp = int(length * tx)
		rows = [max(4, int(round(a * tx))) for a, _ in self.bands]
		Hp = sum(rows)
		self.x, self.y = sheet.place(Lp, Hp)
		self.W, self.H = Lp, Hp
		self.rows = np.cumsum([0] + rows)
		sheet.img[self.y * SS : (self.y + Hp) * SS, self.x * SS : (self.x + Lp) * SS] = paint_beam(Lp * SS, [r * SS for r in rows], state, rng)

	def uv(self, fu, band):
		return (self.x + 1 + fu * (self.W - 2), self.y + self.rows[band])


def paint_beam(W, rows, state, rng):
	H = sum(rows)
	lift = 1.0 if state == "string" else 1.03
	img, yy, xx = surface(H, W, rng, (BASE * lift, LIGHT * lift, WARM * lift, DUSK * lift, COOL * lift), 2)
	starts = np.cumsum([0] + rows)
	val = np.ones(H, np.float32)
	val[starts[0] : starts[1]] = 0.92
	val[starts[2] : starts[3]] = 1.1
	val[starts[4] : starts[5]] = 0.96
	val = gaussian_filter(val, 2 * SS)
	img = img * val[:, None, None]
	# lower lip of each side goes dark where it sits on the wall
	for y0, y1, flip in ((starts[0], starts[1], True), (starts[4], starts[5], False)):
		f = (yy - y0) / max(y1 - y0, 1)
		f = 1 - f if flip else f
		img = over(img, SHADOW, ss(0.45, 0.55, f) * ((yy >= y0) & (yy < y1)) * 0.5)
	if state == "mossy":
		t = starts[2] + rows[2] / 2
		img = moss_on(img, ss(rows[2] * 0.48, rows[2] * 0.12, np.abs(yy - t)) * patches(W, rng, 1)[None, :], rng)
	img = np.clip(img + (img - gaussian_filter(img, (1.4 * SS, 1.4 * SS, 0))) * 0.75, 0, 255)
	high = np.zeros((H, W), np.float32)
	streak = gaussian_filter(rng.random((H, W)).astype(np.float32), (0.8 * SS, 2.5 * SS))
	streak = np.clip((streak - streak.mean()) / (streak.std() * 1.6) * 0.5 + 0.5, 0, 1)
	for i in (1, 3):
		c = (starts[i] + starts[i + 1]) / 2
		dy = yy - c - (smooth1d(W, max(W // 7, 8), rng) * SS)[None, :]
		w = rows[i] / 2 + 2.4 * SS
		f = rhythm(W, rng, 1.0, max(4, W // (60 * SS)))
		extra = np.zeros(W)
		for _ in range(int(rng.integers(1, 4))):
			cx, reach = rng.uniform(0.08, 0.92) * W, rng.uniform(0.04, 0.11) * W
			bump = np.exp(-(((np.arange(W) - cx) / reach) ** 2))
			f = np.maximum(f, bump * rng.uniform(0.7, 1))
			extra = np.maximum(extra, bump * rng.uniform(2.2, 5) * w)
		core = ss(w, 0, np.abs(dy)) ** 1.3
		bleed = ss(w + extra[None, :] + 1e-3, w * 0.3, np.abs(dy)) * (extra[None, :] > 0.5) * (0.25 + 0.75 * streak)
		high = np.maximum(high, np.maximum(core, bleed) * f[None, :])
	high = gaussian_filter(high, 0.3 * SS)
	img = over(img, EDGE, high * 0.92)
	img = over(img, EDGE_PALE, gaussian_filter(high, (4 * SS, 10 * SS)) * 0.55)
	return np.clip(img, 0, 255)


class Tile:
	"""a plain painted patch: soffit, mortar"""

	def __init__(self, sheet, W, H, kind, rng):
		self.x, self.y = sheet.place(W, H)
		self.W, self.H = W, H
		sheet.img[self.y * SS : (self.y + H) * SS, self.x * SS : (self.x + W) * SS] = paint_tile(W * SS, H * SS, kind, rng)

	def uv(self, fu, fv):
		return (self.x + 1 + fu * (self.W - 2), self.y + 1 + fv * (self.H - 2))


def paint_tile(W, H, kind, rng):
	if kind == "mortar":
		img = np.empty((H, W, 3), np.float32)
		img[:] = MORTAR
		return img
	img, yy, xx = surface(H, W, rng, (SHADOW, SHADOW * 1.12, SHADOW * 1.06, SHADOW * 0.94, SHADOW), 1)
	if kind == "soffit":
		# rough courses running across the barrel, broken joints
		rows = 5
		m = np.zeros((H, W), np.float32)
		for r in range(rows + 1):
			y = int(r / rows * (H - 1))
			m[max(y - SS, 0) : y + SS, :] = 1
			if r < rows:
				for x in rng.uniform(0, W, 4).astype(int):
					m[y : int((r + 1) / rows * (H - 1)), max(x - SS, 0) : x + SS] = 1
		img = over(img, MORTAR, gaussian_filter(m, 0.6 * SS) * 0.55)
	if kind == "end":
		img, yy, xx = surface(H, W, rng, (DUSK, BASE, DUSK, SHADOW * 1.3, DUSK), 1)
		img *= 0.82
	if kind == "cap":
		img, yy, xx = surface(H, W, rng, (BASE, LIGHT, WARM, DUSK, COOL), 1)
		img *= (1.12 - 0.22 * yy / H)[..., None]
		img = over(img, SHADOW, ss(H * 0.82, H, yy) * 0.6)
	if kind == "ivy":
		img = np.empty((H, W, 3), np.float32)
		img[:] = (72, 128, 86)
		# overlapping leaf dabs, lighter toward the sun: crisp shapes, close in hue
		for pass_, (count, a, b_) in enumerate(((H * W // (90 * SS * SS)), c1, c2) for c1, c2 in (((66, 122, 84), (84, 146, 86)), ((84, 146, 86), (116, 170, 88)), ((116, 170, 88), (164, 204, 106)))):
			r = 4.4 * SS
			for _ in range(int(count * (1.0 - pass_ * 0.25))):
				cx, cy = rng.uniform(0, W), rng.uniform(0, H)
				x0, x1, y0, y1 = max(int(cx - 2 * r), 0), min(int(cx + 2 * r) + 1, W), max(int(cy - 2 * r), 0), min(int(cy + 2 * r) + 1, H)
				if x1 <= x0 or y1 <= y0:
					continue
				yy2, xx2 = np.mgrid[y0:y1, x0:x1].astype(np.float32)
				ang = rng.uniform(-1.2, 1.2)
				u_ = (xx2 - cx) * math.cos(ang) + (yy2 - cy) * math.sin(ang)
				v_ = -(xx2 - cx) * math.sin(ang) + (yy2 - cy) * math.cos(ang)
				m = ((u_ / (r * 1.3)) ** 2 + (v_ / (r * 0.8)) ** 2) < 1
				colour = np.array(a) + (np.array(b_) - np.array(a)) * (1 - cy / H) * rng.uniform(0.5, 1)
				img[y0:y1, x0:x1][m] = colour
		return np.clip(gaussian_filter(img, (0.35 * SS, 0.35 * SS, 0)), 0, 255)
	if kind == "rock":
		img = over(img, LIGHT, ss(H * 0.55, H * 0.1, yy) * 0.75)
		img = over(img, BASE * 1.1, ss(H * 0.1, H * 0.5, yy) * 0.8)
		img = over(img, WET, ss(H * 0.65, H, yy) * 0.75)
		ln = H * 0.34
		high = ss(5 * SS, 0, np.abs(yy - ln - (smooth1d(W, max(W // 6, 8), rng) * 4 * SS)[None, :])) * rhythm(W, rng, 1.0, 5)[None, :]
		img = over(img, EDGE, gaussian_filter(high.astype(np.float32), 0.6 * SS) * 0.74)
		img = over(img, EDGE_PALE, gaussian_filter(high.astype(np.float32), (4 * SS, 9 * SS)) * 0.4)
		img = moss_on(img, ss(H * 0.28, 0, yy) * 0.66, rng)
	return np.clip(img, 0, 255)


class Sheet:
	def __init__(self):
		self.img = np.zeros((SHEET * SS, SHEET * SS, 3), np.float32)
		self.img[:] = MORTAR
		self.x, self.y, self.row = 4, 4, 0

	def place(self, w, h):
		if self.x + w + 4 > SHEET:
			self.x, self.y, self.row = 4, self.y + self.row + 4, 0
		if self.y + h + 4 > SHEET:
			raise RuntimeError("sheet full")
		at = (self.x, self.y)
		self.x += w + 5
		self.row = max(self.row, h)
		return at


class Mesh:
	"""triangles with per-corner normals and UVs, by piece. Every triangle says which way is out, and is flipped or refused"""

	def __init__(self):
		self.tris = {}
		self.clip = []

	def add(self, piece, tri, uvs, normals, out):
		if self.clip:
			self.add_clipped(piece, tri, uvs, normals, out)
			return
		self.add_plain(piece, tri, uvs, normals, out)

	def add_clipped(self, piece, tri, uvs, normals, out):
		"""keep the part of the triangle on the kept side of every plane: a stone cut to fit"""
		poly = [(np.asarray(p, float), np.asarray(u, float), np.asarray(n, float)) for p, u, n in zip(tri, uvs, normals)]
		for pt, nrm in self.clip:
			new = []
			for i, a in enumerate(poly):
				b = poly[(i + 1) % len(poly)]
				da, db = np.dot(a[0] - pt, nrm), np.dot(b[0] - pt, nrm)
				if da >= 0:
					new.append(a)
				if (da >= 0) != (db >= 0):
					f = da / (da - db)
					new.append(tuple(x + (y - x) * f for x, y in zip(a, b)))
			poly = new
			if len(poly) < 3:
				return
		for i in range(1, len(poly) - 1):
			c = (poly[0], poly[i], poly[i + 1])
			self.add_plain(piece, tuple(x[0] for x in c), tuple(tuple(x[1]) for x in c), tuple(x[2] for x in c), out)

	def add_plain(self, piece, tri, uvs, normals, out):
		a, b, c = [np.asarray(p, float) for p in tri]
		n = np.cross(b - a, c - a)
		if np.linalg.norm(n) < 1e-7:
			return
		if np.dot(n, out) < 0:
			tri, uvs, normals = (tri[0], tri[2], tri[1]), (uvs[0], uvs[2], uvs[1]), (normals[0], normals[2], normals[1])
		self.tris.setdefault(piece, []).append((tri, uvs, normals))

	def quad(self, piece, q, uv, n, out):
		self.add(piece, (q[0], q[1], q[2]), (uv[0], uv[1], uv[2]), (n[0], n[1], n[2]), out)
		self.add(piece, (q[0], q[2], q[3]), (uv[0], uv[2], uv[3]), (n[0], n[2], n[3]), out)

	def check(self):
		"""every triangle's winding must agree with its smooth normals: Roblox draws only the front"""
		bad = 0
		for tris in self.tris.values():
			for tri, _uv, normals in tris:
				a, b, c = [np.asarray(p, float) for p in tri]
				if np.dot(np.cross(b - a, c - a), np.mean(normals, axis=0)) <= 0:
					bad += 1
		assert bad == 0, f"{bad} triangles wound against their normals"

	def write(self, folder):
		out = {}
		for piece, tris in self.tris.items():
			p = np.array([v for t in tris for v in t[0]])
			centre = (p.min(axis=0) + p.max(axis=0)) / 2
			lines_ = [f"o {piece}"]
			faces = []
			vi = 1
			for tri, uv, normals in tris:
				for q, t, n in zip(tri, uv, normals):
					n = np.asarray(n, float)
					n = n / (np.linalg.norm(n) + 1e-9)
					lines_.append("v %.4f %.4f %.4f" % tuple(np.asarray(q) - centre))
					lines_.append("vt %.5f %.5f" % (t[0] / SHEET, 1 - t[1] / SHEET))
					lines_.append("vn %.4f %.4f %.4f" % tuple(n))
				faces.append(f"f {vi}/{vi}/{vi} {vi + 1}/{vi + 1}/{vi + 1} {vi + 2}/{vi + 2}/{vi + 2}")
				vi += 3
			open(os.path.join(folder, piece + ".obj"), "w").write("\n".join(lines_ + faces) + "\n")
			out[piece] = {"Triangles": len(tris), "Centre": [round(float(c), 4) for c in centre], "Size": [round(float(c), 3) for c in p.max(axis=0) - p.min(axis=0)]}
		return out


def unit(v):
	v = np.asarray(v, float)
	return v / (np.linalg.norm(v) + 1e-9)


def piece_of(s):
	return "BridgeA" if s < L * 0.33 else "BridgeB" if s < L * 0.67 else "BridgeC"


# --- the land under it
def load_terrain():
	S = json.load(open(SPEC, encoding="utf-8"))
	im = np.array(Image.open(os.path.join(os.path.dirname(SPEC), "terrain.png"))).astype(np.float32)
	Z = (im[..., 0] * 256 + im[..., 1]) / 50 - 40
	border = S["Border"]

	def height(x, y):
		j, k = (y + border) / 4, (x + border) / 4
		j0, k0 = int(j), int(k)
		fj, fk = j - j0, k - k0
		return float(Z[j0, k0] * (1 - fj) * (1 - fk) + Z[j0, k0 + 1] * (1 - fj) * fk + Z[j0 + 1, k0] * fj * (1 - fk) + Z[j0 + 1, k0 + 1] * fj * fk)

	# a crop for the Blender views (Blender's Python has no PIL)
	x0, y0, x1, y1 = 640, 940, 1320, 1520
	j0, j1, k0, k1 = (y0 + border) // 4, (y1 + border) // 4 + 1, (x0 + border) // 4, (x1 + border) // 4 + 1
	np.savez_compressed(os.path.join(OUT, "land_crop.npz"), Z=Z[j0:j1, k0:k1], M=im[j0:j1, k0:k1, 2], x0=x0, y0=y0, step=4)
	return height


GROUND = load_terrain()
U2 = (B - A) / L
N2 = np.array((-U2[1], U2[0]))  # land (x, y) of local +z


def ground_at(s, z=0.0):
	p = A + U2 * s + N2 * z
	return GROUND(p[0], p[1])


def deck_y(s):
	"""the walking surface. Past the ends it runs down on to the road: under the road at its tip, never under the ground before that"""
	if 0 <= s <= L:
		return LEVEL + RISE * math.sin(math.pi * s / L)
	f = min((-s if s < 0 else s - L) / APRON, 1.0)
	tip = ground_at(-APRON if s < 0 else L + APRON) - 0.2
	line = LEVEL + (tip - LEVEL) * f
	above = ground_at(s) + 0.12 * (1 - f) - 0.2 * f
	return min(LEVEL, max(line, above))


def arches():
	out = []
	s = ABUT
	for w in SPANS:
		sm = s + w / 2
		crown = deck_y(sm) - 2.6
		r = crown - SPRING
		R = (w * w / 4 + r * r) / (2 * r)
		out.append(dict(a=s, b=s + w, m=sm, r=r, R=R, cy=crown - R, crown=crown))
		s += w + PIER
	return out


ARCHES = arches()


def in_hole(s, y, margin=0.0):
	for a in ARCHES:
		if a["a"] - margin < s < a["b"] + margin and y > 0:
			if y < SPRING:
				return True
			if (s - a["m"]) ** 2 + (y - a["cy"]) ** 2 < (a["R"] + margin) ** 2:
				return True
	return False


def in_ring(s, y, inset=0.25):
	for a in ARCHES:
		if (s - a["m"]) ** 2 + (y - a["cy"]) ** 2 < (a["R"] + RING - inset) ** 2 and y > SPRING and a["a"] - RING < s < a["b"] + RING:
			return True
	return False


class Builder:
	def __init__(self, cards, rng):
		self.m = Mesh()
		self.c = cards
		self.rng = rng

	def pillow(self, piece, rim, N, card, b, depth, tilt=0.03, jitter=0.0):
		"""a stone: rim corners bl, br, tr, tl in the wall plane, a raised face inside them. Smooth normals roll the light over the corners"""
		N = unit(N)
		rim = [np.asarray(p, float) for p in rim]
		rng = self.rng
		if jitter:
			rim = [p + rng.normal(0, jitter, 3) * (1 - np.abs(N)) for p in rim]
		w = np.linalg.norm(rim[1] - rim[0]) or 1
		h = np.linalg.norm(rim[3] - rim[0]) or 1
		fx, fy = min(b / w, 0.3), min(b / h, 0.3)

		def bil(u, v):
			return rim[0] * (1 - u) * (1 - v) + rim[1] * u * (1 - v) + rim[2] * u * v + rim[3] * (1 - u) * v

		corners = ((fx, fy), (1 - fx, fy), (1 - fx, 1 - fy), (fx, 1 - fy))
		crest = [bil(u, v) + N * (depth + rng.normal(0, tilt)) for u, v in corners]
		centre = sum(rim) / 4
		cuv = [card.uv(card.mx, 1 - card.my), card.uv(1 - card.mx, 1 - card.my), card.uv(1 - card.mx, card.my), card.uv(card.mx, card.my)]
		ruv = [card.uv(0, 1), card.uv(1, 1), card.uv(1, 0), card.uv(0, 0)]
		nc = [unit(N + unit(c - centre) * 0.14) for c in crest]
		nr = [unit(N + unit(p - centre) * 0.3) for p in rim]
		self.m.quad(piece, crest, cuv, nc, N)
		for i in range(4):
			j = (i + 1) % 4
			self.m.quad(piece, (rim[i], rim[j], crest[j], crest[i]), (ruv[i], ruv[j], cuv[j], cuv[i]), (nr[i], nr[j], nc[j], nc[i]), N)

	def plain_quad(self, piece, q, N, tile, u=(0, 1), v=(0, 1)):
		N = unit(N)
		self.m.quad(piece, q, [tile.uv(u[0], v[1]), tile.uv(u[1], v[1]), tile.uv(u[1], v[0]), tile.uv(u[0], v[0])], [N] * 4, N)

	def courses(self, piece_at, o, U, N, u0, u1, anchor, ybot, shear, chooser, clips, b=0.2, depth=0.16, ytop=None):
		"""hand-laid masonry on a plane: rows COURSE tall, anchored so they line up across faces, in running bond. shear(u) moves whole columns, so a row keeps its height"""
		rng = self.rng
		k = 0
		prev = []
		while True:
			y1 = anchor - k * COURSE
			y0 = y1 - COURSE
			if y1 <= ybot:
				break
			k += 1
			if ytop is not None and y0 >= ytop - 0.2:
				continue
			# widths along the row, none lining up with a joint in the row above
			span = u1 - u0
			row, at = [], 0.0
			while at < span - 0.01:
				for _ in range(12):
					w = float(rng.choice(WIDTHS[1:], p=(0.34, 0.42, 0.24)))
					if at == 0 and k % 2 == 0 and span > 7:
						w = WIDTHS[0]
					if not prev or all(abs(at + w - j) > 0.85 for j in prev):
						break
				if span - at - w < WIDTHS[0] * 0.9:
					w = span - at
				row.append(w)
				at += w
			edges = u0 + np.cumsum([0.0] + row)
			prev = [e - u0 for e in edges[1:-1]]
			for a, c in zip(edges, edges[1:]):
				mid = (a + c) / 2
				cl = clips(a, c, y0, y1)
				if cl is None:
					continue
				j = rng.normal(0, 0.012, 8)
				corners = [(a + j[0], y0 + j[1]), (c - JOINT + j[2], y0 + j[3]), (c - JOINT + j[4], y1 - JOINT + j[5]), (a + j[6], y1 - JOINT + j[7])]
				rim = [o + U * p + np.array((0, q + shear(p), 0)) for p, q in corners]
				self.m.clip = cl
				self.pillow(piece_at(mid), rim, N, chooser(c - a, (y0 + y1) / 2 + shear(mid), mid, k), b, depth * rng.uniform(0.92, 1.08), tilt=0.012)
				self.m.clip = []

	def beam(self, piece, p0, p1, w, h, card, up=(0, 1, 0), e=0.24, tip=0.0):
		"""a long stone along p0..p1: back, edge, top, edge, front, closed underneath. Smooth round the section, flat ends"""
		p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
		rng = self.rng
		ax = unit(p1 - p0)
		side = unit(np.cross(ax, up))
		upv = np.cross(side, ax)
		ln = np.linalg.norm(p1 - p0)
		sec = [(-w / 2, 0), (-w / 2, h - e), (-w / 2 + e, h), (w / 2 - e, h), (w / 2, h - e), (w / 2, 0)]
		rings = []
		for end, base in ((0, p0), (1, p1)):
			j = rng.normal(0, 0.008, (6, 2))
			rings.append([base + side * (a + j[i, 0]) + upv * (b + j[i, 1] + (rng.uniform(-tip, 0) if end else 0)) for i, (a, b) in enumerate(sec)])
		# normals: average of the two faces at each corner of the section
		norms = []
		fn = [unit(side * (sec[i + 1][1] - sec[i][1]) * -1 + upv * (sec[i + 1][0] - sec[i][0])) for i in range(5)]
		middle_up = upv * h * 0.3
		if np.dot(fn[2], upv) < 0:
			fn = [-f for f in fn]
		norms = [fn[0], unit(fn[0] + fn[1]), unit(fn[1] + fn[2]), unit(fn[2] + fn[3]), unit(fn[3] + fn[4]), fn[4]]
		fu = min(1.0, ln / card.length)
		start = float(rng.uniform(0, max(1 - fu, 0.0001)))
		axis = (p0 + p1) / 2 + middle_up
		for k in range(5):
			q = (rings[0][k], rings[1][k], rings[1][k + 1], rings[0][k + 1])
			uv = (card.uv(start, k), card.uv(start + fu, k), card.uv(start + fu, k + 1), card.uv(start, k + 1))
			centre = sum(q) / 4
			out = centre - (axis + ax * np.dot(centre - axis, ax))
			self.m.quad(piece, q, uv, (norms[k], norms[k], norms[k + 1], norms[k + 1]), out)
		mort = card.end
		# the underside: seen from the river where the stone overhangs the wall
		self.m.quad(piece, (rings[0][0], rings[1][0], rings[1][5], rings[0][5]), [mort.uv(0, 0), mort.uv(1, 0), mort.uv(1, 1), mort.uv(0, 1)], [-upv] * 4, -upv)
		for ring, sign in ((rings[0], -1), (rings[1], 1)):
			# ends: dark, mostly hidden against the next stone
			c = sum(ring) / 6
			n = ax * sign
			for k in range(5):
				self.m.add(piece, (ring[k], ring[k + 1], c), (mort.uv(0.3, 0.3), mort.uv(0.7, 0.3), mort.uv(0.5, 0.7)), (n, n, n), n)

	def pad(self, piece, centre, a, b_, n, r, tile, fv):
		"""one clump of leaves: a lobed disc, raised in the middle, its part of the leaf patch chosen by how high it hangs"""
		rng = self.rng
		k = 7
		ang = np.linspace(0, math.tau, k, endpoint=False) + rng.uniform(0, 1)
		rad = r * rng.uniform(0.82, 1.12, k)
		fu = float(rng.uniform(0.2, 0.8))
		span = 0.17
		rim = [centre + a * math.cos(q) * s_ + b_ * math.sin(q) * s_ for q, s_ in zip(ang, rad)]
		uv = [tile.uv(fu + math.cos(q) * span, np.clip(fv - math.sin(q) * span, 0, 1)) for q in ang]
		top = centre + n * r * 0.08
		ntop = n
		for i in range(k):
			j = (i + 1) % k
			self.m.add(piece, (top, rim[i], rim[j]), (tile.uv(fu, fv), uv[i], uv[j]), (ntop, unit(n + unit(rim[i] - centre) * 0.12), unit(n + unit(rim[j] - centre) * 0.12)), n)

	def ivy(self, side, s0, width, drop, tile):
		"""ivy over the parapet: a mat over the coping, then clumps hanging in uneven strands, higher clumps lapping over lower ones; a short spill on the deck side"""
		rng = self.rng
		n = max(5, int(width / 0.85))
		sa = np.linspace(s0, s0 + width, n + 1)
		spill = (0.2 + rng.uniform(0, 0.5, n + 1)) * np.sin(np.linspace(0, math.pi, n + 1)) ** 0.7

		def out_chain(i):
			top = deck_y(sa[i]) + PARAPET + COPING_H - 0.05
			return [np.array((sa[i], top + 0.08, side * 7.2)), np.array((sa[i], top - 0.12, side * 8.62)), np.array((sa[i], top - 0.7, side * 8.62))]

		def in_chain(i):
			top = deck_y(sa[i]) + PARAPET + COPING_H - 0.05
			return [np.array((sa[i], top + 0.08, side * 7.2)), np.array((sa[i], top - 0.12, side * 5.82)), np.array((sa[i], top - 0.2 - spill[i], side * 5.8))]

		for chain, nrm in ((out_chain, np.array((0, 0.35, side))), (in_chain, np.array((0, 0.35, -side)))):
			cols = [chain(i) for i in range(n + 1)]
			for i in range(n):
				for j in range(2):
					q = (cols[i][j], cols[i + 1][j], cols[i + 1][j + 1], cols[i][j + 1])
					fu0, fu1, fv0, fv1 = i / n, (i + 1) / n, j / 4, (j + 1) / 4
					n_ = unit(np.array((0, 1.0, 0.25 * nrm[2]))) if j == 0 else unit(nrm)
					self.m.quad(piece_of((sa[i] + sa[i + 1]) / 2), q, [tile.uv(fu0, fv0), tile.uv(fu1, fv0), tile.uv(fu1, fv1), tile.uv(fu0, fv1)], [n_] * 4, n_)
		a_ = np.array((1.0, 0, 0))
		b_ = np.array((0, 1.0, 0))
		nz = np.array((0, 0.12, float(side)))
		nz = unit(nz)
		piece = piece_of(s0 + width / 2)

		def hang(sv, drop_here, r):
			d = deck_y(sv)
			y = d + PARAPET + COPING_H - 0.45 - drop_here
			z = 8.74 - 0.02 * drop_here if y > d - 0.9 else 8.42
			fv = float(np.clip(0.12 + drop_here / (drop + 1.5) * 0.78, 0.12, 0.88))
			self.pad(piece, np.array((sv, y, side * z)), a_, b_, nz, r, tile, fv)

		for i in range(int(width / 0.8) + 1):
			hang(s0 + 0.2 + i * 0.8 + rng.uniform(-0.15, 0.15), rng.uniform(0, 0.4), rng.uniform(0.95, 1.3))
		strands = max(3, int(width / 1.7))
		for i in range(strands):
			f = (i + 0.5) / strands
			length = drop * math.sin(f * math.pi) ** 0.8 * rng.uniform(0.5, 1.0)
			sv = s0 + width * f + rng.uniform(-0.3, 0.3)
			at = 0.9
			while at < length:
				hang(sv + rng.uniform(-0.4, 0.4), at, 1.2 - 0.55 * at / max(length, 1) + rng.uniform(-0.08, 0.08))
				at += rng.uniform(0.7, 1.0)

	def blob(self, piece, at, r, height, card, sides=7, rot=0.0):
		"""a loose cobble: an irregular foot, a shoulder, a tilted flat top narrower than the foot; sinks into what it sits on"""
		rng = self.rng
		at = np.asarray(at, float)
		ang = np.sort(rng.uniform(0, math.tau, sides)) + rot
		ang = np.linspace(0, math.tau, sides, endpoint=False) * 0.7 + ang * 0.3
		rad = rng.uniform(0.74, 1.08, sides) * r
		tilt = rng.normal(0, 0.1, 2)
		rings = []
		for frac_h, frac_r in ((-0.4, 1.0), (0.42, 1.0), (1.0, 0.68)):
			ring = []
			for a, q in zip(ang, rad):
				x, z = math.cos(a) * q * frac_r, math.sin(a) * q * frac_r
				y = frac_h * height + (x * tilt[0] + z * tilt[1]) * (frac_h > 0.6)
				ring.append(at + np.array((x, y, z)))
			rings.append(ring)
		c = sum(rings[0]) / sides
		c[1] = at[1] + height * 0.3
		vs = (1.0, 0.56, 0.34)
		for i in range(2):
			for k in range(sides):
				j = (k + 1) % sides
				q = (rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k])
				u0, u1 = k / sides, (k + 1) / sides
				uv = (card.uv(u0, vs[i]), card.uv(u1, vs[i]), card.uv(u1, vs[i + 1]), card.uv(u0, vs[i + 1]))
				out = sum(q) / 4 - c
				ns = [unit(p - c + np.array((0, 0.3, 0)) * r) for p in q]
				self.m.quad(piece, q, uv, ns, out)
		top = sum(rings[2]) / sides
		up = np.array((0, 1, 0.0))
		for k in range(sides):
			j = (k + 1) % sides
			a, b = rings[2][k], rings[2][j]
			self.m.add(piece, (a, b, top), (card.uv(0.2 + 0.6 * k / sides, 0.28), card.uv(0.2 + 0.6 * (k + 1) / sides, 0.28), card.uv(0.5, 0.05)), (unit(up + unit(a - top) * 0.4), unit(up + unit(b - top) * 0.4), up), up)


def main():
	rng = np.random.default_rng(SEED)
	s = Sheet()  # the walls
	top_sheet = Sheet()  # what the eye gets close to
	C = {}
	C["mortar"] = Tile(s, 16, 16, "mortar", rng)
	C["soffit"] = Tile(s, 170, 96, "soffit", rng)
	C["cap"] = Tile(s, 84, 84, "cap", rng)
	C["end"] = Tile(s, 24, 24, "end", rng)
	C["ivy"] = Tile(s, 150, 150, "ivy", rng)
	C["rock"] = Tile(s, 150, 110, "rock", rng)
	C["rock2"] = Tile(s, 150, 110, "rock", rng)
	# close to the eye: deck, parapet and coping on their own sheet
	TOP_TX = 54
	C["mortar_top"] = Tile(top_sheet, 16, 16, "mortar", rng)
	C["end_top"] = Tile(top_sheet, 24, 24, "end", rng)
	C["deck"] = [Card(top_sheet, f"deck{i}", 3.5, 3.0, 0.2, TOP_TX, "deck", rng) for i in range(5)] + [Card(top_sheet, f"deckside{i}", 3.5, 3.0, 0.2, TOP_TX, "deck_side", rng) for i in range(3)]
	C["coping"] = [BeamCard(top_sheet, f"coping{i}", 6.0, COPING_W, COPING_H, 0.24, TOP_TX, "mossy" if i == 3 else "plain", rng, C["end_top"]) for i in range(4)]
	C["string"] = [BeamCard(s, f"string{i}", 6.0, 1.0, 0.85, 0.16, 34, "string", rng, C["end"]) for i in range(2)]
	C["inner"] = {(w, 1.05): Card(top_sheet, f"inner{w}", w, 1.05, 0.15, TOP_TX, "lit", rng) for w in (2.3, 3.2, 4.2)}
	for i in range(2):
		C["inner"][(3.2, 1.05, i)] = Card(top_sheet, f"inner_b{i}", 3.2, 1.05, 0.15, TOP_TX, "mossy" if i else "mid", rng)
	C["wall"] = {}
	for level in LEVEL_VALUE:
		for tone in TONE:
			for w in WIDTHS:
				if w == WIDTHS[0] and tone != "base":
					continue
				C["wall"][(level, tone, w)] = Card(s, f"wall_{level}_{tone}_{w}", w, COURSE, 0.2, 28, f"{level}/{tone}", rng)
	C["vous"] = {st: [Card(s, f"vous_{st}{i}", 1.9, 2.3, 0.2, 34, paint, rng) for i in range(2)] for st, paint in (("lit", "lit/pale"), ("mid", "mid/pale"), ("damp", "low/pale"))}
	for sheet_, name_ in ((s, "Bridge_Color.png"), (top_sheet, "Bridge_Top_Color.png")):
		Image.fromarray(np.clip(sheet_.img * GRADE, 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS).save(os.path.join(OUT, name_))
	piece_top = lambda sv: "BridgeTop" + piece_of(sv)[-1]

	b = Builder(C, rng)

	def state_at(y, s=None):
		if y < WATER + 2.6:
			return "damp"
		return "lit" if y > 15 else "mid"

	def level_at(y):
		return "lit" if y > 19 else "mid" if y > 15 else "low" if y > 11 else "water"

	def tone_at(side, sv, y):
		"""which patch a stone falls in, the edge broken up per stone"""
		f = rng.normal(0, 0.22)
		for ps, ss_, ys, ra, rb, sign in PATCHES:
			if ps == side:
				f += sign * math.exp(-(((sv - ss_) / (ra * 1.3)) ** 2 + ((y - ys) / (rb * 1.3)) ** 2)) * 1.5
		return "pale" if f > 0.42 else "dark" if f < -0.42 else "base"

	def wall_card(w, y, sv=None, side=None, lip=False):
		ws = min(WIDTHS, key=lambda v: abs(v - w))
		tone = tone_at(side, sv, y) if side and ws != WIDTHS[0] else "base"
		return C["wall"][("lip" if lip else level_at(y), tone, ws)]

	def hump(sv):
		return RISE * math.sin(math.pi * sv / L) if 0 <= sv <= L else 0.0

	ANCHOR = LEVEL + PARAPET + 0.02  # the top of the top row, in the flat

	def wall_clips(s0, s1, y0, y1, z):
		"""where a stone on the main wall meets an opening: leave it, cut it or drop it. Cuts sit under the arch ring or at the pier's edge. Returns planes in (s, y), None to drop"""
		sc = (s0 + s1) / 2
		dy = hump(sc)
		y0, y1 = y0 + dy, y1 + dy
		if y1 < WATER - 1.5:  # stones run on under the banks, so the wall holds up wherever the terrain ends up
			return None
		for a in ARCHES:
			if s1 <= a["a"] or s0 >= a["b"]:
				continue
			c = np.array((a["m"], a["cy"]))
			rc = a["R"] + 0.45
			pts = [np.array((u, v)) for u in (s0, s1) for v in (y0, y1)]
			radii = [np.linalg.norm(p - c) for p in pts]

			def hole(p):
				return a["a"] < p[0] < a["b"] and (p[1] < SPRING or np.linalg.norm(p - c) < rc)

			if not any(hole(p) for p in pts) and min(radii) > rc:
				continue  # clear of this arch
			if max(radii) < a["R"] + RING - 0.3 and y0 > SPRING:
				return None  # wholly under the ring
			if y0 < SPRING and sc < a["a"]:
				return [("v", a["a"], -1)]
			if y0 < SPRING and sc > a["b"]:
				return [("v", a["b"], 1)]
			dirn = np.array((sc, (y0 + y1) / 2)) - c
			if dirn[1] <= 0:
				return None
			dirn = dirn / np.linalg.norm(dirn)
			if max(np.dot(p - c, dirn) for p in pts) < rc:
				return None
			return [("t", c, dirn, rc)]
		return []

	for side in (1, -1):
		N = np.array((0, 0, side), float)
		U = np.array((side, 0, 0), float)
		zw = side * (HALF - 0.3)
		o = np.array((0, 0, zw), float)
		lo, hi = (-1.0, L + 1.0) if side == 1 else (-L - 1.0, 1.0)

		def clips3(u0_, u1_, y0, y1, side=side, zw=zw):
			sa, sb = sorted((u0_ * side, u1_ * side))
			got = wall_clips(sa, sb, y0, y1, side * HALF)
			if got is None:
				return None
			out = []
			for g in got:
				if g[0] == "v":
					out.append((np.array((g[1], 0, zw)), np.array((g[2], 0, 0.0))))
				else:
					_k, c, dirn, rc = g
					out.append((np.array((c[0] + dirn[0] * rc, c[1] + dirn[1] * rc, zw)), np.array((dirn[0], dirn[1], 0.0))))
			return out

		b.courses(lambda mid, side=side: piece_of(mid * side), o, U, N, lo, hi, ANCHOR, WATER - 3, lambda u, side=side: hump(u * side), lambda w, y, u, k, side=side: wall_card(w, y, u * side, side, k == 1), clips3)
		# the dark core behind the stones, stopping at each arch
		cols = sorted(set(list(np.linspace(-1.0, L + 1.0, 34)) + [a["a"] for a in ARCHES] + [a["b"] for a in ARCHES] + [a["m"] + a["R"] * math.sin(t) for a in ARCHES for t in np.linspace(-math.asin((a["b"] - a["m"]) / a["R"]), math.asin((a["b"] - a["m"]) / a["R"]), 9)]))
		for sa, sb in zip(cols, cols[1:]):
			mid = (sa + sb) / 2

			def low(sv, mid=mid):
				for a in ARCHES:
					if a["a"] - 1e-6 <= mid <= a["b"] + 1e-6:
						return a["cy"] + math.sqrt(max(a["R"] ** 2 - (sv - a["m"]) ** 2, 0))
				return BED - 1

			q = [(sa, low(sa)), (sb, low(sb)), (sb, deck_y(sb) + PARAPET + 0.2), (sa, deck_y(sa) + PARAPET + 0.2)]
			pts = [np.array((p, h, side * (HALF - 0.34))) for p, h in q]
			b.plain_quad(piece_of(mid), pts, N, C["mortar"])

	# arches: soffit barrel, pier faces, voussoirs on both faces
	for a in ARCHES:
		th0 = math.asin((a["b"] - a["m"]) / a["R"])
		segs = 12
		for i in range(segs):
			t0, t1 = -th0 + 2 * th0 * i / segs, -th0 + 2 * th0 * (i + 1) / segs
			P = lambda t, z: np.array((a["m"] + a["R"] * math.sin(t), a["cy"] + a["R"] * math.cos(t), z))
			q = [P(t0, -HALF + 0.3), P(t1, -HALF + 0.3), P(t1, HALF - 0.3), P(t0, HALF - 0.3)]
			tm = (t0 + t1) / 2
			down = -unit(P(tm, 0) - np.array((a["m"], a["cy"], 0)))
			nA, nB = -unit(P(t0, 0) - np.array((a["m"], a["cy"], 0))), -unit(P(t1, 0) - np.array((a["m"], a["cy"], 0)))
			v0 = (i % 4) / 4
			uv = [C["soffit"].uv(0, v0), C["soffit"].uv(0, v0 + 0.25), C["soffit"].uv(1, v0 + 0.25), C["soffit"].uv(1, v0)]
			b.m.quad(piece_of(a["m"]), q, uv, (nA, nB, nB, nA), down)
		for s0, dirn in ((a["a"], 1), (a["b"], -1)):
			q = [np.array((s0, BED - 1, -HALF + 0.3)), np.array((s0, BED - 1, HALF - 0.3)), np.array((s0, SPRING + 0.2, HALF - 0.3)), np.array((s0, SPRING + 0.2, -HALF + 0.3))]
			b.plain_quad(piece_of(s0), q, (dirn, 0, 0), C["soffit"])
		# voussoirs: chunky and uneven, a bigger keystone
		arc = 2 * th0 * a["R"]
		n = int(round(arc / 2.2)) | 1
		edges = np.cumsum(np.concatenate(([0], rng.uniform(0.97, 1.03, n))))
		edges = edges / edges[-1] * 2 * th0 - th0
		for i in range(n):
			t0, t1 = edges[i], edges[i + 1]
			key = i == n // 2
			depth = RING + (0.12 if key else 0.0)
			for side in (1, -1):
				z = side * (HALF - 0.14)
				R0, R1 = a["R"] - 0.28, a["R"] + depth
				P = lambda r, t: np.array((a["m"] + r * math.sin(t), a["cy"] + r * math.cos(t), z))
				gap = 0.035 / a["R"]
				rim = [P(R0, t0 + gap), P(R0, t1 - gap), P(R1, t1 - gap), P(R1, t0 + gap)]
				if side == 1:
					rim = [P(R0, t1 - gap), P(R0, t0 + gap), P(R1, t0 + gap), P(R1, t1 - gap)]
				y = (rim[0][1] + rim[2][1]) / 2
				pool = C["vous"][state_at(y)]
				b.pillow(piece_of(a["m"]), rim, (0, 0, side), pool[int(rng.integers(len(pool)))], 0.2, 0.3 if not key else 0.4)

	# cutwaters on the piers, both sides
	for p0 in (ARCHES[0]["b"], ARCHES[1]["b"]):
		p1 = p0 + PIER
		pm = (p0 + p1) / 2 + rng.uniform(-0.25, 0.25)
		for side in (1, -1):
			z0 = side * (HALF - 0.25)
			apex = np.array((pm, 0, side * (HALF + NOSE)))
			legs = ((np.array((p0 + 0.35, 0, z0)), apex), (apex, np.array((p1 - 0.35, 0, z0)))) if side == 1 else ((np.array((p1 - 0.35, 0, z0)), apex), (apex, np.array((p0 + 0.35, 0, z0))))
			Y = np.array((0, 1.0, 0))
			for q0, q1 in legs:
				ln = np.linalg.norm(q1 - q0)
				U = unit(q1 - q0)
				N = unit(np.cross(U, Y))

				dy = hump(pm)
				rows_down = round((ANCHOR + dy - NOSE_TOP) / COURSE)
				top_y = ANCHOR + dy - rows_down * COURSE
				b.courses(lambda _m: piece_of(pm), q0, U, N, 0, ln, top_y, WATER - 3, lambda _u: 0.0, lambda w, y, u, k: wall_card(w, y), lambda *_a: [], depth=0.2)
				core = [q0 + Y * (BED - 1) - N * 0.1, q1 + Y * (BED - 1) - N * 0.1, q1 + Y * top_y - N * 0.1, q0 + Y * top_y - N * 0.1]
				b.plain_quad(piece_of(pm), core, N, C["mortar"])
				# the cap, a sloped mossy stone running back up to the wall
				top = np.array((pm, deck_y(pm) - 4.2, side * (HALF - 0.1)))
				t = [q0 + Y * (top_y + 0.05) + N * 0.34, q1 + Y * (top_y + 0.05) + N * 0.34, top]
				cap = C["cap"]
				nrm = unit(np.cross(t[1] - t[0], t[2] - t[0]))
				if nrm[1] < 0:
					nrm = -nrm
				b.m.add(piece_of(pm), t, (cap.uv(0.05, 0.95), cap.uv(0.95, 0.95), cap.uv(0.5, 0.05)), (nrm, nrm, nrm), nrm)
				base_mid = (t[0] + t[1]) / 2
				ca = unit(t[1] - t[0])
				cb = unit(t[2] - base_mid)
				for f_up, off, r_ in ((0.76, 0.1, 1.2), (0.56, -0.35, 0.95), (0.62, 0.55, 0.8)) if q0[0] < q1[0] else ():
					b.pad(piece_of(pm), base_mid + (t[2] - base_mid) * f_up + ca * off + nrm * 0.06, ca, cb, nrm, r_, C["ivy"], 0.3)

	# deck: flagstones in rows, widening on to the road at the aprons
	span_all = L + 2 * APRON
	n_rows = int(round(span_all / 3.6))
	deck_rows = [(-APRON + span_all * i / n_rows, -APRON + span_all * (i + 1) / n_rows) for i in range(n_rows)]

	def half_at(sv):
		if sv < 0:
			return INNER + FLARE * min(-sv / WING, 1)
		if sv > L:
			return INNER + FLARE * min((sv - L) / WING, 1)
		return INNER

	for ri, (s0, s1) in enumerate(deck_rows):
		count = 4 if ri % 2 == 0 else 3
		parts = rng.uniform(0.96, 1.04, count)
		parts = np.cumsum(np.concatenate(([0], parts)))
		parts = parts / parts[-1]
		for i in range(count):
			fa, fb = parts[i], parts[i + 1]
			zf = lambda sv, f: (2 * f - 1) * half_at(sv)
			g = 0.05
			j = rng.normal(0, 0.02, 8)
			q = [(s0 + g + j[0], zf(s0, fa) + g + j[1]), (s1 - g + j[2], zf(s1, fa) + g + j[3]), (s1 - g + j[4], zf(s1, fb) - g + j[5]), (s0 + g + j[6], zf(s0, fb) - g + j[7])]
			rim = [np.array((a, deck_y(a) - 0.02 + rng.normal(0, 0.012), c)) for a, c in q]
			edge = i == 0 or i == count - 1
			pool = C["deck"][5:] if edge and rng.random() < 0.5 else C["deck"][:5]
			# rim wound so the stone's face looks up; the card's side moss faces the parapet
			rim = [rim[0], rim[3], rim[2], rim[1]] if (i == 0) else [rim[3], rim[0], rim[1], rim[2]]
			if abs(np.cross(rim[1] - rim[0], rim[3] - rim[0])[1]) < 1e-6:
				continue
			b.pillow(piece_top(s0), rim, (0, 1, 0), pool[int(rng.integers(len(pool)))], 0.2, 0.12, tilt=0.012)
	# the dark bed under the flags (joints), down to the water so no see-through
	for s0, s1 in zip(np.linspace(-APRON, L + APRON, 26), np.linspace(-APRON, L + APRON, 26)[1:]):
		hi0, hi1 = half_at(s0) + 0.4, half_at(s1) + 0.4
		q = [np.array((s0, deck_y(s0) - 0.1, -hi0)), np.array((s0, deck_y(s0) - 0.1, hi0)), np.array((s1, deck_y(s1) - 0.1, hi1)), np.array((s1, deck_y(s1) - 0.1, -hi1))]
		b.plain_quad(piece_top((s0 + s1) / 2), q, (0, 1, 0), C["mortar_top"])

	# parapets: inner stones, string course on the outside, coping on top, flaring out at the ends with a chunky post
	def inner_card(w, h, y, _m):
		ws = min((2.3, 3.2, 4.2), key=lambda v: abs(v - w))
		if ws == 3.2 and rng.random() < 0.32:
			return C["inner"][(3.2, 1.05, int(rng.integers(2)))]
		return C["inner"][(ws, 1.05)]

	for side in (1, -1):
		z_in = side * INNER
		N = np.array((0, 0, -side), float)
		U = np.array((-side, 0, 0), float)
		o = np.array((0, 0, z_in), float)
		# inner face, built directly so each course follows the deck
		for row in range(2):
			sv = -0.6 - (1.6 if row else 0)
			while sv < L + 0.6:
				w = float(rng.choice((3.2, 4.2)))
				if sv + w > L + 0.6 - 1.2:
					w = L + 0.6 - sv
				sa, sc = max(sv, -0.6), min(sv + w, L + 0.6)
				if sc - sa < 0.8:
					sv += w
					continue
				top = lambda q, r=row: deck_y(q) + 0.0 + (r + 1) * (PARAPET / 2) - 0.06
				bot = lambda q, r=row: deck_y(q) + r * (PARAPET / 2)
				j = rng.normal(0, 0.012, 4)
				rim = [np.array((sa + j[0], bot(sa), z_in)), np.array((sc - 0.08 + j[1], bot(sc), z_in)), np.array((sc - 0.08 + j[2], top(sc), z_in)), np.array((sa + j[3], top(sa), z_in))]
				if side == 1:
					rim = [rim[1], rim[0], rim[3], rim[2]]
				b.pillow(piece_top((sa + sc) / 2), rim, N, inner_card(sc - sa, 1.05, 0, 0), 0.15, 0.17)
				sv += w
		cols = np.linspace(-0.6, L + 0.6, 24)
		for s0, s1 in zip(cols, cols[1:]):
			q = [np.array((s1, deck_y(s1), z_in + side * 0.02)), np.array((s0, deck_y(s0), z_in + side * 0.02)), np.array((s0, deck_y(s0) + PARAPET + 0.15, z_in + side * 0.02)), np.array((s1, deck_y(s1) + PARAPET + 0.15, z_in + side * 0.02))]
			b.plain_quad(piece_top((s0 + s1) / 2), q, N, C["mortar_top"])

		def lay(s_from, s_to, path, w, h, cards, y_of, skip=None, tip=0.0, piece=piece_of):
			sv = s_from
			while sv < s_to - 0.5:
				ln = float(rng.uniform(4.2, 5.0))
				if sv + ln > s_to - 1.4:
					ln = s_to - sv
				sa, sc = sv, sv + ln - 0.06
				if skip and skip[0] < (sa + sc) / 2 < skip[1]:
					sv += ln
					continue
				p0 = path(sa) + np.array((0, y_of(sa), 0))
				p1 = path(sc) + np.array((0, y_of(sc), 0))
				b.beam(piece((sa + sc) / 2), p0, p1, w, h, cards[int(rng.integers(len(cards)))], tip=tip)
				sv += ln

		zc = side * (INNER + (HALF - INNER) / 2 + 0.1)
		broken = None
		lay(-0.8, L + 0.8, lambda q, zc=zc: np.array((q, 0, zc)), COPING_W, COPING_H, C["coping"], lambda q: deck_y(q) + PARAPET - 0.05, skip=broken, piece=piece_top)
		# the outside string course at deck level
		lay(-0.4, L + 0.4, lambda q, side=side: np.array((q, 0, side * (HALF - 0.05))), 1.0, 0.85, C["string"], lambda q: deck_y(q) + PARAPET - COURSE - 0.42)
		# flares
		for sgn, s_end in ((-1, 0.0), (1, L)):
			wing_path = lambda t, sgn=sgn, s_end=s_end, side=side: np.array((s_end + sgn * t, 0, side * (HALF - 0.9 + FLARE * t / WING)))
			# wing wall: one run of stones on each face, ending in the post. Sinks into the ground
			p0, p1 = wing_path(0), wing_path(WING)
			ya = deck_y(p0[0]) + PARAPET - 0.1
			yb = deck_y(p1[0]) + PARAPET - 0.1
			foot = min(ground_at(p0[0], p0[2]), ground_at(p1[0], p1[2])) - 1.0
			for offs in (0.9, -0.9):
				a0 = np.array((p0[0], 0, p0[2] + offs))
				a1 = np.array((p1[0], 0, p1[2] + offs))
				want = np.array((0, 0, 1.0 if offs > 0 else -1.0))
				if np.dot(np.cross(a1 - a0, (0, 1, 0)), want) < 0:
					a0, a1 = a1, a0
					ytop0, ytop1 = yb, ya
				else:
					ytop0, ytop1 = ya, yb
				ln = np.linalg.norm(a1 - a0)
				Uw = unit(a1 - a0)
				Nw = unit(np.cross(Uw, (0, 1, 0)))
				slope = (ytop1 - ytop0) / ln
				# cut along the coping
				cutn = unit(np.array(Uw) * -slope + np.array((0, 1.0, 0)))
				top_pt = a0 + np.array((0, ytop0 + 0.1, 0))

				def wing_clip(_u0, _u1, _y0, _y1, top_pt=top_pt, cutn=cutn):
					return [(top_pt, -cutn)]

				b.courses(lambda _m, s_end=s_end: piece_of(s_end), a0, Uw, Nw, 0, ln, ANCHOR, foot, lambda _u: 0.0, lambda w, y, u, k: wall_card(w, y), wing_clip)
				core = [a0 + np.array((0, foot, 0)), a1 + np.array((0, foot, 0)), a1 + np.array((0, ytop1, 0)), a0 + np.array((0, ytop0, 0))]
				b.plain_quad(piece_of(s_end), [c - Nw * 0.05 for c in core], Nw, C["mortar"])
			parts_w = 2
			for i in range(parts_w):
				q0, q1 = wing_path(WING * i / parts_w), wing_path(WING * (i + 1) / parts_w - 0.03)
				b.beam(piece_top(s_end), q0 + np.array((0, deck_y(q0[0]) + PARAPET - 0.1, 0)), q1 + np.array((0, deck_y(q1[0]) + PARAPET - 0.1, 0)), COPING_W, COPING_H, C["coping"][int(rng.integers(len(C["coping"])))])
			# the end post: a chunky pier of stone with a pyramid cap
			pe = wing_path(WING)
			top = deck_y(pe[0]) + PARAPET + 2.2
			foot = ground_at(pe[0], pe[2]) - 1.0
			pw = 1.55
			crn = [np.array((pe[0] + dx, 0, pe[2] + dz)) for dx, dz in ((-pw, pw), (pw, pw), (pw, -pw), (-pw, -pw))]
			for k in range(4):
				q0, q1 = crn[k], crn[(k + 1) % 4]
				outn = unit(np.cross(q1 - q0, (0, 1, 0)))
				yr = top
				while yr > foot:
					rim = [q0 + np.array((0, yr - COURSE, 0)), q1 + np.array((0, yr - COURSE, 0)), q1 + np.array((0, yr - JOINT, 0)), q0 + np.array((0, yr - JOINT, 0))]
					b.pillow(piece_of(s_end), rim, outn, wall_card(3.4, 16 if yr < 16 else yr - 1), 0.2, 0.2, tilt=0.01)
					yr -= COURSE
				core = [q0 + np.array((0, foot, 0)), q1 + np.array((0, foot, 0)), q1 + np.array((0, top, 0)), q0 + np.array((0, top, 0))]
				b.plain_quad(piece_of(s_end), core, outn, C["mortar"])
				apex = np.array((pe[0], top + 1.0, pe[2]))
				flat_centre = np.array((pe[0], 0, pe[2]))
				tq = (flat_centre + (q0 - flat_centre) * 1.2 + np.array((0, top - 0.1, 0)), flat_centre + (q1 - flat_centre) * 1.2 + np.array((0, top - 0.1, 0)), apex)
				nrm = unit(np.cross(tq[1] - tq[0], tq[2] - tq[0]))
				if nrm[1] < 0:
					nrm = -nrm
				cap = C["cap"]
				b.m.add(piece_of(s_end), tq, (cap.uv(0.05, 0.95), cap.uv(0.95, 0.95), cap.uv(0.5, 0.05)), (nrm, nrm, nrm), nrm)

	# ivy in a few chosen places, off to one side of each span
	for side, s0, width, drop in ((1, 24, 9, 8.5), (1, 96, 6, 5.5), (-1, 58, 8, 7.0), (-1, 116, 5, 4.5)):
		b.ivy(side, s0, width, drop, C["ivy"])

	# loose stones: round the piers, on the banks, a coping stone fallen off on to the shore
	loose = []
	for p0 in (ARCHES[0]["b"], ARCHES[1]["b"]):
		for side in (1, -1):
			pm = p0 + PIER / 2
			for _ in range(2):
				loose.append((pm + rng.uniform(-5, 5), WATER - 0.2, side * (HALF + NOSE + rng.uniform(-1, 2.5)), rng.uniform(1.0, 2.3), rng.uniform(1.3, 2.4)))
	for s_, z_ in ((30, -13.5), (24, -11), (36, -14), (112, 12), (116, 14.5), (9, 12.5), (130, -11)):
		g = max(ground_at(s_, z_), WATER - 0.2)
		loose.append((s_, g, z_, rng.uniform(1.1, 2.6), rng.uniform(1.2, 2.5)))
	for i, (x, y, z, r, h) in enumerate(loose):
		b.blob("BridgeLoose", (x, y + h * 0.2, z), r, h, C["rock2" if i % 2 else "rock"], sides=int(rng.integers(6, 8)), rot=rng.uniform(0, 6))
	b.m.check()
	pieces = b.m.write(OUT)
	colliders = make_colliders()
	ends = {}
	for name, sv, sv2 in (("From", 0.0, -APRON), ("To", L, L + APRON)):
		ends[name] = {"DeckLevel": round(deck_y(sv), 2), "GroundAtDeckEnd": round(ground_at(sv), 2), "ApronEndsAt": round(deck_y(sv2), 2), "GroundAtApronEnd": round(ground_at(sv2), 2)}
	ang = math.atan2(U2[1], U2[0])
	kit = {
		"From": list(map(float, A)),
		"To": list(map(float, B)),
		"Length": round(L, 2),
		"Origin": "local x along From to To, y is world height, z across; world X = land x + OffsetX, world Z = land y",
		"YawDegrees": round(math.degrees(ang), 3),
		"Pieces": pieces,
		"TrianglesTotal": sum(p["Triangles"] for p in pieces.values()),
		"SheetUsedToRow": {"Walls": s.y + s.row, "Top": top_sheet.y + top_sheet.row},
		"Sheets": {"Bridge_Color.png": ["BridgeA", "BridgeB", "BridgeC", "BridgeLoose"], "Bridge_Top_Color.png": ["BridgeTopA", "BridgeTopB", "BridgeTopC"]},
		"Ends": ends,
		"Arches": [{k: round(v, 2) for k, v in a.items()} for a in ARCHES],
		"Colliders": colliders,
	}
	json.dump(kit, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print({k: p["Triangles"] for k, p in pieces.items()}, "total", kit["TrianglesTotal"], "sheets used to rows", s.y + s.row, top_sheet.y + top_sheet.row, "of", SHEET)
	print(json.dumps(ends))


def make_colliders():
	"""simple invisible blocks: the walking surface, parapets, piers. Local frame; the mesh itself has no collision"""
	out = []

	def box(name, s0, y0, s1, y1, thick, z):
		"""a block whose top edge runs from (s0, y0) to (s1, y1)"""
		cx, cy = (s0 + s1) / 2, (y0 + y1) / 2
		ln = math.hypot(s1 - s0, y1 - y0)
		out.append({"Name": name, "Centre": [round(cx, 3), round(cy - thick / 2, 3), round(z, 3)], "Pitch": round(math.degrees(math.atan2(y1 - y0, s1 - s0)), 3), "Length": round(ln + 0.4, 3), "Height": round(thick, 3)})

	stops = sorted(set(list(np.linspace(0, L, 13)) + list(np.linspace(-APRON, 0, 4)) + list(np.linspace(L, L + APRON, 4))))
	worst = 0.0
	for s0, s1 in zip(stops, stops[1:]):
		for f in np.linspace(0, 1, 9):
			q = s0 + (s1 - s0) * f
			worst = max(worst, abs(deck_y(s0) + (deck_y(s1) - deck_y(s0)) * f + 0.1 - deck_y(q) - 0.1))
		w = 2 * (max(half_collider(s0), half_collider(s1)))
		box("Deck", s0, deck_y(s0) + 0.1, s1, deck_y(s1) + 0.1, 2.0, 0.0)
		out[-1]["Width"] = round(w, 3)
		if -0.1 < s0 and s1 < L + 0.1:
			for side in (1, -1):
				box("Parapet", s0, deck_y(s0) + PARAPET + COPING_H + WALL_UP, s1, deck_y(s1) + PARAPET + COPING_H + WALL_UP, PARAPET + COPING_H + WALL_UP, side * (INNER + HALF) / 2)
				out[-1]["Width"] = round(HALF - INNER, 3)
	for sgn, s_end in ((-1, 0.0), (1, L)):
		for side in (1, -1):
			x0, z0 = s_end, side * (HALF - 0.9)
			x1, z1 = s_end + sgn * WING, side * (HALF - 0.9 + FLARE)
			y0, y1 = deck_y(x0) + PARAPET + COPING_H + WALL_UP, deck_y(x1) + PARAPET + COPING_H + WALL_UP
			out.append({"Name": "Wing", "A": [round(x0, 3), round(y0, 3), round(z0, 3)], "B": [round(x1, 3), round(y1, 3), round(z1, 3)], "Height": round(PARAPET + COPING_H + 1.5 + WALL_UP, 3), "Width": 1.9})
	print("deck collider leaves the deck by at most %.2f studs" % worst)
	# the end posts
	for s_end, sgn in ((0.0, -1), (L, 1)):
		for side in (1, -1):
			px, pz = s_end + sgn * WING, side * (HALF - 0.9 + FLARE)
			top = deck_y(px) + PARAPET + 2.2
			foot = ground_at(px, pz) - 1.0
			out.append({"Name": "Post", "Centre": [round(px, 3), round((top + foot) / 2, 3), round(pz, 3)], "Pitch": 0, "Length": 3.1, "Height": round(top - foot, 3), "Width": 3.1})
	# solid under the deck: the abutments, and columns above each arch stepped to its curve, so nobody walks in through the walls
	for s0, s1 in ((0.0, ABUT), (L - ABUT, L)):
		top = min(deck_y(s0), deck_y(s1)) - 1.8
		out.append({"Name": "Abutment", "Centre": [round((s0 + s1) / 2, 3), round((BED - 1 + top) / 2, 3), 0], "Pitch": 0, "Length": round(s1 - s0, 3), "Height": round(top - (BED - 1), 3), "Width": DECK["Width"]})
	for a in ARCHES:
		cols = 8
		for i in range(cols):
			s0, s1 = a["a"] + (a["b"] - a["a"]) * i / cols, a["a"] + (a["b"] - a["a"]) * (i + 1) / cols
			low = lambda q: a["cy"] + math.sqrt(max(a["R"] ** 2 - (q - a["m"]) ** 2, 0))
			bottom = max(low(s0), low(s1))
			top = min(deck_y(s0), deck_y(s1)) - 1.8
			if top > bottom + 0.2:
				out.append({"Name": "Spandrel", "Centre": [round((s0 + s1) / 2, 3), round((bottom + top) / 2, 3), 0], "Pitch": 0, "Length": round(s1 - s0 + 0.1, 3), "Height": round(top - bottom, 3), "Width": DECK["Width"]})
	assert worst < 0.25
	for a, nxt in zip(ARCHES, ARCHES[1:]):
		out.append({"Name": "Pier", "Centre": [round(a["b"] + PIER / 2, 3), round((BED - 1 + a["crown"] - 3) / 2, 3), 0], "Pitch": 0, "Length": PIER, "Height": round(a["crown"] - 3 - (BED - 1), 3), "Width": DECK["Width"]})
	return out


def half_collider(sv):
	if sv < 0:
		return INNER + FLARE * min(-sv / WING, 1)
	if sv > L:
		return INNER + FLARE * min((sv - L) / WING, 1)
	return INNER + 0.5


main()
