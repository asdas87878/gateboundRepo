"""Wooden bridges, second set, from the user's concept image (art/kit/woodbridge_b/reference.webp): a chunky flat bridge, an arch with lattice rails and mossy caps, and a rope bridge.
Square pegs and rope instead of iron. Three values of chestnut carry the read from afar: light deck and top rails, mid panels, dark structure with plum shadows. Slate at the banks, one muted red banner each.
The paint fits the form: every part type has its own strip at its true size, end grain cut to its shape, and contact marks only on the faces something really touches. Each bridge has its own sheet and is one mesh. The build reports how far each part strays from its paint's scale.
Origin of each bridge: the middle of its span at bank level (y=0). x runs along the bridge, z across. Studs; the player is 5.2 tall. Every part is checked closed and outward wound.

  python tools/art/woodbridge_b_kit.py art/kit/woodbridge_b           parts, Woodbridge_B_<Bridge>.png, OBJs, kit.json
  python tools/art/woodbridge_b_kit.py art/kit/woodbridge_b --sheet   only the comparison sheet from the Blender renders
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter

from crisp_paint import jagged

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/woodbridge_b")
KIT_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "woodbridge_kit.py")


def load_kit():
	src = open(KIT_PY, encoding="utf-8").read()
	ns = {"__name__": "woodbridge_painter", "__file__": KIT_PY}
	exec(compile(src[: src.rindex("os.makedirs(OUT, exist_ok=True)")], KIT_PY, "exec"), ns)
	return ns


WB = load_kit()
PR = WB["PR"]
Path, sweep, bar, bar_raw, finish, fixed_grain, deck_paint, Rect = WB["Path"], WB["sweep"], WB["bar"], WB["bar_raw"], WB["finish"], WB["fixed_grain"], WB["deck_paint"], WB["Rect"]
Piece, write_obj, finish_sheet, T, SHEET = PR["Piece"], PR["write_obj"], PR["finish_sheet"], PR["T"], PR["SHEET"]

# before the sheet's grade (about 1.46, 1.47, 1.19). Light lands near 166 112 71, far calmer than the first orange. Measured against the approved props (140 101 72 in Studio)
WOOD_LIGHT = {"BASE": (114, 76, 60), "LIGHT": (126, 87, 67), "WARM": (124, 82, 58), "DUSK": (100, 68, 60), "COOL": (102, 74, 66), "GRAIN": (80, 50, 44)}
WOOD_MID = {"BASE": (96, 63, 54), "LIGHT": (106, 72, 60), "WARM": (104, 68, 54), "DUSK": (84, 57, 55), "COOL": (86, 62, 60), "GRAIN": (64, 41, 40)}
WOOD_DARK = {"BASE": (74, 50, 50), "LIGHT": (84, 58, 55), "WARM": (82, 55, 50), "DUSK": (64, 44, 48), "COOL": (66, 49, 54), "GRAIN": (46, 31, 36)}
OFF = (0, 0, 0, 0)
PLANK_T = 0.36
STONE_T = 30  # texels per stud on the walls: stone holds up lower than wood (the stone bridge's walls are 28)
ROPE_L = 3.0  # one repeat of the rope's paint, in studs
STRAW, STRAW_LIGHT, STRAW_DARK = np.array((188, 160, 116), float), np.array((218, 196, 150), float), np.array((128, 100, 70), float)  # paler and greyer than the wood, so the rope is its own material
MOSS_A, MOSS_B, MOSS_C = np.array((96, 112, 60), float), np.array((122, 134, 72), float), np.array((70, 88, 52), float)
CLOTH, CLOTH_DARK, CLOTH_TRIM = np.array((146, 54, 52), float), np.array((96, 36, 48), float), np.array((186, 150, 92), float)  # a muted red: the one accent on each bridge


def undo_grade(P, img):
	"""the sheet's wood grade lands on everything at the end. Rope, moss and cloth are painted to their final colour."""
	return img / (P["GRADE"] * PR["STUDIO_LIFT"])


# ---------------------------------------------------------------- the sheet: everything is declared first, packed, then painted


class Spec:
	def __init__(self, kit, L, H, painter, name, free=False, keep=False):
		self.L, self.H, self.painter, self.name = int(L), int(H), painter, name
		self.x = self.y = None
		self.free, self.keep = free, keep
		kit.specs.append(self)

	@property
	def rect(self):
		return Rect(self.x, self.y, self.L, self.H)


class TileSpec(Spec):
	def uv(self, fx, fy):
		"""beam ends ask for 0.26 to 0.74 of a tile (props_kit's cap_uv). Opened out here, so an end uses the whole tile at the paint's full scale"""
		return (self.x + (0.5 + (fx - 0.5) * 2.05) * self.L, self.y + (0.5 + (fy - 0.5) * 2.05) * self.H)


class BeamSpec(Spec):
	"""a beam's sides unrolled at a set density, shaped as props_kit's Strip so its beam() can use it. hidden: bands nobody sees, kept thin to save the sheet."""

	def __init__(self, kit, name, studs, w, h, ch, painter, dens=T, hidden=(), **kw):
		pts, kinds = kit.P["beam_section"](w, h, ch)
		perim = [math.dist(pts[i], pts[(i + 1) % 8]) for i in range(8)]
		self.bands = [(6 if i in hidden else max(4 if kinds[i] == "edge" else 6, int(round(perim[i] * dens))), kinds[i]) for i in range(8)]
		self.rows = [0]
		for b in self.bands:
			self.rows.append(self.rows[-1] + b[0])
		self.mids = [(self.rows[2 * j + 1] + self.rows[2 * j + 2]) / 2 for j in range(4)]
		self.ch, self.studs, self.dens = ch, studs, dens
		super().__init__(kit, studs * dens, self.rows[-1], painter, name, **kw)

	def uv(self, f, row):
		return (self.x + f * self.L, self.y + row)


def pack(specs):
	"""a skyline packer, tallest first. If that fails it tries other orders."""

	def attempt(order):
		h = np.zeros(SHEET, int)
		g = 8
		for s in order:
			best = None
			for x in range(g, SHEET - s.L - g, 2):
				y = int(h[x : x + s.L + g].max())
				if y + s.H + g <= SHEET and (best is None or y < best[1]):
					best = (x, y)
			if best is None:
				return None
			s.x, s.y = best[0], max(best[1], g)
			h[s.x : s.x + s.L + g] = s.y + s.H + g
		return int(h.max())

	order = sorted(specs, key=lambda s: (-s.H, -s.L))
	used = attempt(order)
	r = np.random.default_rng(1)
	tries = 0
	while used is None and tries < 3000:
		order = list(r.permutation(np.array(specs, dtype=object)))
		used = attempt(order)
		tries += 1
	if used is None:
		raise RuntimeError(f"sheet full: {sum(s.L * s.H for s in specs)} texels in {len(specs)} strips")
	return used


# ---------------------------------------------------------------- paint hooks, each knowing the part it's on


def calm(extra=None, amount=0.5):
	"""lifts the broad patches out of paint_strip's result and leaves the fine marks"""

	def paint(img, strip):
		SS = PR["PAINTER"]["SS"]
		low = gaussian_filter(img, (4 * SS, 30 * SS, 0))
		img = img - (low - low.mean(axis=(0, 1), keepdims=True)) * amount
		return extra(img, strip) if extra else img

	return paint


def soft_light(img, strip):
	"""light falling off smoothly down a beam's side, with no shadow shape: a painted shadow needs something visibly casting it"""
	SS = PR["PAINTER"]["SS"]
	y = 0
	for px, kind in strip.bands:
		if kind in ("front", "back"):
			t = (np.arange(px * SS) + 0.5) / (px * SS)
			img[y * SS : (y + px) * SS] *= 1 - (1 - PR["darken"](t if kind == "front" else 1 - t)[:, None, :]) * PR["GRAD_PLANK"]
		y += px
	return img


def touches(marks):
	"""contact shading on the faces a part really touches, nowhere else. marks: (face bands, from, to along the part in studs, half width across the face in studs). The touching piece sits above it, so it falls a little further below."""

	def paint(img, strip):
		P = PR["PAINTER"]
		SS = P["SS"]
		dens = strip.dens * SS
		H, L = img.shape[:2]
		m = np.zeros((H, L), np.float32)
		rows = [r * SS for r in strip.rows]
		for faces, u0, u1, half in marks:
			for k in faces:
				# k counts faces: 0 the strip's top, 1 its front, 2 its bottom, 3 its back
				a, b = rows[k * 2 - 0 if k * 2 < 8 else 0], rows[k * 2 + 1]
				# the face proper sits between the chamfers on each side of it
				a, b = rows[k * 2], rows[k * 2 + 1]
				c = (a + b) / 2
				x0, x1 = int((u0 - 0.2) * dens), int((u1 + 0.07) * dens)
				y0, y1 = int(c - (half + 0.05) * dens), int(c + (half + 0.05) * dens)
				m[max(y0, 0) : y1, max(x0, 0) : x1] = 1
		broad = gaussian_filter(m, (0.1 * dens, 0.1 * dens))
		fine = gaussian_filter(m, 0.025 * dens)
		img = P["over"](img, P["SHADOW"], fine * 0.42)
		return P["over"](img, P["SHADOW"], broad * 0.32)

	return paint


def ends_dark(reach=0.45):
	"""a piece's ends go into something at both ends: braces, rails, ties"""

	def paint(img, strip):
		P = PR["PAINTER"]
		L = img.shape[1]
		d = strip.dens * P["SS"] * reach
		t = np.minimum(np.arange(L), L - 1 - np.arange(L)) / d
		return P["over"](img, P["SHADOW"], (np.clip(1 - t, 0, 1) ** 1.4 * 0.55)[None, :])

	return paint


def hand_worn(img, strip):
	"""top rails: pale along the top where hands run, fading out before the posts"""
	SS = PR["PAINTER"]["SS"]
	L = img.shape[1]
	r = [v * SS for v in strip.rows]
	u = (np.arange(L) + 0.5) / L
	wear = np.exp(-(((u - 0.5) / 0.28) ** 2)) * 0.12
	for a, b in ((r[0], r[1]), (r[7], r[8]), (r[1], r[2])):
		img[a:b] = img[a:b] * (1 + wear[None, :, None])
	return img


def chain(*hooks):
	hooks = [h for h in hooks if h]

	def paint(img, strip):
		for h in hooks:
			img = h(img, strip)
		return img

	return paint


def mossy_post(u_deck):
	"""moss just under the post's top, and a patch or two where it stands on the deck. Broken edges, never a ring."""

	def paint(img, strip):
		P = PR["PAINTER"]
		SS = P["SS"]
		H, L = img.shape[:2]
		rng = np.random.default_rng(31)
		xx = np.arange(L, dtype=np.float32)[None, :]
		for lo, hi, a in ((0.975, 1.2, 0.9), (u_deck - 0.012, u_deck + 0.055, 0.85)):
			n = gaussian_filter(rng.normal(0, 1, H).astype(np.float32), 3 * SS, mode="wrap")
			n = n / (np.abs(n).max() + 1e-6) * 0.035 * L
			far = np.clip((hi * L + n[:, None] - xx) / (1.2 * SS), 0, 1)
			near = np.clip((xx - lo * L - n[:, None] * 0.6) / (1.2 * SS), 0, 1)
			m = gaussian_filter(far * near, 0.3 * SS)
			if lo < 0.9:
				blob = gaussian_filter(rng.normal(0, 1, H).astype(np.float32), 14 * SS, mode="wrap")
				m = m * np.clip((blob / (np.abs(blob).max() + 1e-6) - 0.25) * 5, 0, 1)[:, None]
			img = P["over"](img, undo_grade(P, MOSS_A), m * a)
			img = P["over"](img, undo_grade(P, MOSS_C), m * np.clip((lo * L + 0.018 * L + n[:, None] * 0.6 - xx) / (1.2 * SS), 0, 1) * 0.6)
		return img

	return paint


def rope_paint(H, L):
	"""two strands twisting along the rope, with dark seams. Whole turns along and around, so the paint repeats with no seam."""
	yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
	phase = xx / L * int(ROPE_L * 4) + yy / H * 2
	v = np.abs(np.sin(np.pi * phase))
	img = STRAW_DARK + (STRAW - STRAW_DARK) * np.clip(v * 1.7, 0, 1)[..., None]
	lit = np.clip((v - 0.72) / 0.28, 0, 1)[..., None] * 0.7
	return img * (1 - lit) + STRAW_LIGHT * lit


def coil_paint(H, L):
	"""rope wound round a beam: turns across the strip, slightly off square"""
	yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
	phase = xx / L * 6 + yy / H * 1 + np.sin(yy / H * math.tau) * 0.08
	v = np.abs(np.sin(np.pi * phase))
	img = STRAW_DARK + (STRAW - STRAW_DARK) * np.clip(v * 1.6, 0, 1)[..., None]
	lit = np.clip((v - 0.7) / 0.3, 0, 1)[..., None] * 0.7
	return img * (1 - lit) + STRAW_LIGHT * lit


def cloth_paint(H, L):
	"""the banner, top of the cloth at x=0: soft folds, a darker foot, one trim band near each end"""
	yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
	t = xx / L
	img = CLOTH + (CLOTH_DARK - CLOTH) * (t**1.6 * 0.6)[..., None]
	img = img * (1 + 0.08 * np.sin(yy / H * math.tau * 4 + np.sin(t * 4) * 0.8))[..., None]
	trim = np.clip((np.abs(t - 0.1) < 0.025) + (np.abs(t - 0.88) < 0.02), 0, 1)
	return img * (1 - trim[..., None] * 0.85) + CLOTH_TRIM * trim[..., None] * 0.85


class Kit:
	"""one bridge's strips on its own sheet"""

	def __init__(self, P, seed):
		self.P = P
		self.specs = []
		self.rng = np.random.default_rng(seed)  # the shapes
		self.paint_rng = np.random.default_rng(seed + 100)  # the paint: changing paint can't move the shapes

	# ---- declaring strips
	def wood(self, name, studs, w, h, ch, pal, knots=0, grad=None, foot=False, hook=None, edges=(1, 7), level=0.5, window=(0.0, 1.0), gaps=(1.2, 2.8), lengths=(0.8, 1.8), light=True, hidden=()):
		"""a timber's strip at its true size. Marks stay stud-sized, light falls off down its sides, and hook paints what only this part has."""

		def painter(s):
			P, rng = self.P, self.paint_rng
			with PR["palette"](P, pal), fixed_grain(P):
				img = PR["strip_paint"](P, s.L, s.bands, rng, levels=OFF, ao_ends=(False, False), grad=grad, knots=knots, foot=foot)
			return finish(extra=calm(chain(soft_light if light and grad is None else None, hook)), edges=edges, level=level, window=window, gaps=gaps, lengths=lengths)(img, s)

		s = BeamSpec(self, name, studs, w, h, ch, painter, hidden=hidden)
		setattr(self, name, s)
		return s

	def end_grain(self, name, w, h, pal, split=True):
		"""end grain cut to one part's shape: rings at a fixed spacing in studs, cropped by the end rather than squashed onto it. Width on the sheet is the part's h."""
		dens = T

		def painter(s):
			P = self.P
			SS = P["SS"]
			rng = self.paint_rng
			yy, xx = np.mgrid[0 : s.H * SS, 0 : s.L * SS].astype(np.float32)
			# the heart of the log sits off the end for thin boards, inside it for big timbers
			cx, cy = s.L * SS * rng.uniform(0.35, 0.65), s.H * SS * (rng.uniform(0.35, 0.65) if min(w, h) > 0.7 else rng.uniform(1.5, 2.5))
			d = np.hypot(xx - cx, yy - cy) / (dens * SS) + np.sin(np.arctan2(yy - cy, xx - cx) * 5) * 0.012
			with PR["palette"](P, pal):
				img = np.zeros((s.H * SS, s.L * SS, 3), np.float32) + P["LIGHT"] * 1.02
				ring = np.abs((d / 0.2) % 1 - 0.5) < 0.09
				img = P["over"](img, P["DUSK"] * 1.02, gaussian_filter(ring.astype(np.float32), 0.35 * SS) * 0.7)
				if split and min(w, h) > 0.7:
					a = rng.uniform(0, math.tau)
					sd = np.abs((xx - cx) * math.sin(a) - (yy - cy) * math.cos(a))
					img = P["over"](img, P["GRAIN"], gaussian_filter((sd < 0.5 * SS).astype(np.float32), 0.3 * SS) * 0.85)
			return img

		s = TileSpec(self, max(h * dens, 10), max(w * dens, 10), painter, name)
		setattr(self, name, s)
		return s

	def plain_tile(self, name, px, pal):
		"""a peg's carved face: flat, with a lit top edge and a dark foot"""

		def painter(s):
			P = self.P
			n = px * P["SS"]
			with PR["palette"](P, pal):
				img = np.zeros((n, n, 3), np.float32) + P["LIGHT"]
				t = np.arange(n, dtype=np.float32)[:, None] / n
				return img * (1.06 - 0.24 * t)[..., None]

		s = TileSpec(self, px, px, painter, name)
		setattr(self, name, s)
		return s

	def planks(self, W, width=1.42):
		Lp = W + 0.5
		deck = deck_paint()
		self.plank_len = Lp
		common = dict(grad=None, light=False, hidden=(6,), gaps=(2.4, 4.4))
		self.wood("plank_a", Lp, PLANK_T, width, 0.07, WOOD_LIGHT, hook=deck, edges=(1,), level=0.45, **common)
		# the odd replaced board, darker: set by hand along the deck, not scattered
		self.wood("plank_c", Lp, PLANK_T, width, 0.07, WOOD_MID, knots=1, hook=deck, edges=(3,), level=0.35, **common)
		self.end_grain("plank_end", PLANK_T, width, WOOD_LIGHT)
		self.plank_w = width

	def small_parts(self):
		self.wood("peg", 0.6, 0.56, 0.56, 0.0, WOOD_MID, grad=None, edges=(), level=0.0)
		self.plain_tile("peg_face", 26, WOOD_MID)
		self.under_strip = BeamSpec(self, "under", 0.4, 0.5, 0.5, 0.0, lambda s: self.flat_paint(s, np.array((44, 28, 40), np.float32)), keep=True)
		self.cloth = BeamSpec(self, "cloth", 3.0, 0.12, 1.3, 0.0, lambda s: undo_grade(self.P, cloth_paint(s.H * self.P["SS"], s.L * self.P["SS"])), keep=True)

	def flat_paint(self, s, colour):
		SS = self.P["SS"]
		return undo_grade(self.P, np.zeros((s.H * SS, s.L * SS, 3), np.float32) + colour)

	def stone_strips(self, depth, height, gate=True):
		"""stone painted for the blocks it's on: a wet and a dry course size, and two sizes standing at the deck ends"""

		def stone(low):
			return lambda s: WB["paint_stone"](self.P, s.L * self.P["SS"], s.rows, low, self.paint_rng)

		self.stone_size = (depth, height)
		self.stone = BeamSpec(self, "stone", 3.9, depth, height, 0.14, stone(False), dens=STONE_T, free=True)
		self.stone_low = BeamSpec(self, "stoneLow", 3.9, depth, height, 0.14, stone(True), dens=STONE_T, free=True)
		self.stone_end = TileSpec(self, height * STONE_T, depth * STONE_T, lambda s: WB["paint_stone_end"](self.P, 0, self.paint_rng) if False else self.stone_end_paint(s), "stoneEnd", free=True)
		if gate:
			self.gate_low = BeamSpec(self, "gateLow", 2.4, 2.2, 1.2, 0.16, stone(False), dens=STONE_T + 8, free=True)
			self.gate_up = BeamSpec(self, "gateUp", 1.9, 1.75, 0.85, 0.16, stone(False), dens=STONE_T + 8, free=True)
			self.gate_end = TileSpec(self, 1.2 * (STONE_T + 8), 2.2 * (STONE_T + 8), self.stone_end_paint, "gateEnd", free=True)

	def stone_end_paint(self, s):
		P = self.P
		img, _c = WB["stone_surface"](P, s.H * P["SS"], s.L * P["SS"], self.paint_rng)
		return WB["stone_colour"](P, np.clip(img * 0.92, 0, 255))

	def moss_tile(self, n=90):
		def painter(s):
			P, rng = self.P, self.paint_rng
			SS = P["SS"]
			N = n * SS
			img = np.zeros((N, N, 3), np.float32) + MOSS_A
			for colour, cut, a in ((MOSS_B, 0.56, 0.8), (MOSS_C, 0.6, 0.65)):
				f = gaussian_filter(rng.random((N, N)).astype(np.float32), 4 * SS) + jagged(N, N, rng, 1.5 * SS) * 0.012
				f = (f - f.mean()) / f.std() * 0.2 + 0.5
				img = P["over"](img, colour, np.clip((f - cut) / 0.03, 0, 1) * a)
			return undo_grade(P, img)

		self.moss = TileSpec(self, n, n, painter, "moss", keep=True)

	def rope_strips(self):
		self.rope = BeamSpec(self, "rope", ROPE_L, 0.44, 0.44, 0.13, lambda s: undo_grade(self.P, rope_paint(s.H * self.P["SS"], s.L * self.P["SS"])), keep=True)
		self.coil = BeamSpec(self, "coil", 1.0, 1.42, 1.42, 0.2, lambda s: undo_grade(self.P, coil_paint(s.H * self.P["SS"], s.L * self.P["SS"])), keep=True)

	def paint_all(self):
		P = self.P
		SS = P["SS"]
		sheet = P["Sheet"]()
		used = pack(self.specs)
		for s in self.specs:
			sheet.img[s.y * SS : (s.y + s.H) * SS, s.x * SS : (s.x + s.L) * SS] = s.painter(s)
		self.sheet, self.used = sheet, used

	# ---- building
	def plank(self, x, y, nx, ny, W, wd, replaced=False):
		rng = self.rng
		strip = self.plank_c if replaced else self.plank_a
		Lp = W + rng.uniform(-0.04, 0.12)
		off = rng.uniform(-0.04, 0.04)
		cx, cy = x - nx * PLANK_T / 2, y - ny * PLANK_T / 2
		dx, dy = rng.uniform(-0.025, 0.025), rng.uniform(-0.012, 0.012)
		a, b = (cx - dx, cy - dy, off - Lp / 2), (cx + dx, cy + dy, off + Lp / 2)
		if rng.random() < 0.5:
			a, b = b, a
		u0 = 0.5 - Lp / 2 / self.plank_len
		return bar_raw(strip, self.plank_end, a, b, PLANK_T, wd, front=(nx, ny, 0), bend=0.008, jitter=0.008, rng=rng, u=(u0, u0 + Lp / self.plank_len), name="Plank")

	def deck(self, path, W, width=(1.3, 1.5), gap=(0.05, 0.11)):
		"""even planks with fine gaps. The replaced boards are placed by a set of gaps, so they don't scatter."""
		rng = self.rng
		out = []
		s = 0.1
		i, nxt, gaps = 0, 4, iter((7, 3, 11, 6, 2, 13, 5, 9, 4, 8, 12, 3, 7, 10))
		while s < path.total - 0.8:
			wd = rng.uniform(*width)
			x, y, nx, ny = path.at(s + wd / 2)
			replaced = i == nxt
			if replaced:
				nxt += next(gaps, 9)
			out.append(self.plank(x, y, nx, ny, W, wd, replaced))
			s += wd + rng.uniform(*gap)
			i += 1
		return out

	def under(self, path, W, n):
		"""a dark board under the deck, so the gaps read as dark seams rather than holes"""
		return sweep(self.under_strip, self.dark_end, path.line(0.6, path.total - 0.6, n, -PLANK_T - 0.06, 0.0), 0.1, W - 0.5, (0, 1, 0), self.rng, bend=0.0, jitter=0.0, box=True, u=(0, 1), name="Under")

	def beam_run(self, strip, path, z, x0, x1, off, n=4, w=0.8, h=1.15):
		pts = path.line(path.s_of(x0), path.s_of(x1), n, off, z)
		return sweep(strip, self.dark_end, pts, w, h, (0, 0, 1 if z >= 0 else -1), self.rng, bend=0.012, name="Beam")

	def post_at(self, strip, end, x, y0, y1, z, width, front):
		rng = self.rng
		return bar_raw(strip, end, (x, y0, z), (x + rng.uniform(-0.03, 0.03), y1, z), width, width, w1=width - 0.08, h1=width - 0.08, front=(0, 0, front), bend=0.012, jitter=0.012, rng=rng, u=(0.0, min(1.0, (y1 - y0) / strip.studs)), name="Post")

	def cap(self, strip, end, x, y0, y1, z, width):
		"""a heavier block on a post's top: this is what makes an end post read as the end"""
		return bar_raw(strip, end, (x, y0, z), (x, y1, z), width, width, w1=width - 0.14, h1=width - 0.14, front=(0, 0, 1 if z >= 0 else -1), bend=0.0, jitter=0.012, rng=self.rng, u=(0.05, 0.05 + (y1 - y0) / strip.studs), name="Cap")

	def peg_at(self, c, n, size=0.56, depth=0.22):
		"""a square peg standing proud, set in a dark recess so it sits in the wood rather than on it"""
		c, n = np.array(c, float), np.array(n, float)
		up = np.array((0, 1, 0), float) if abs(n[1]) < 0.9 else np.array((1, 0, 0), float)
		rng = self.rng
		return [
			bar_raw(self.under_strip, self.dark_end, c - n * 0.08, c + n * 0.035, size + 0.18, size + 0.18, front=up, box=True, bend=0.0, jitter=0.008, rng=rng, u=(0.1, 0.9), name="Recess"),
			bar_raw(self.peg, self.peg_face, c - n * 0.08, c + n * depth, size, size, front=up, box=True, bend=0.0, jitter=0.012, rng=rng, u=(0.1, 0.9), name="Peg"),
		]

	def rod(self, strip, a, b, bow=0.05, n=3, w=0.44, h=0.44, side=1):
		a, b = np.array(a, float), np.array(b, float)
		pts = [a + (b - a) * t + np.array((0, bow * math.sin(math.pi * t), 0)) for t in np.linspace(0, 1, n)]
		return sweep(strip, self.light_end, pts, w, h, (0, 0, side), self.rng, bend=0.012, name="Rail")

	def collar(self, x, y, z, d, size):
		"""a rail's shoulder where it enters a post: a slightly bigger stub, so it looks let in rather than passing through"""
		return bar_raw(self.peg, self.peg_face, (x, y, z), (x + d * 0.26, y, z), size, size, front=(0, 1, 0), box=True, bend=0.0, jitter=0.01, rng=self.rng, u=(0.1, 0.8), name="Collar")

	def knee_at(self, a, b, z):
		return bar(self.knee, self.dark_end, a, b, 0.72, 0.72, front=(0, 0, 1 if z >= 0 else -1), bend=0.01, rng=self.rng, u=(0.03, 0.03 + min(0.94, math.dist(a, b) / self.knee.studs)), name="Knee")

	def banner(self, x, y_top, z, side, length=2.9, width=1.25):
		"""the one accent: a cloth on a little rod, pegged to a face at z, looking toward side"""
		rng = self.rng
		pts = [(x + 0.03 * math.sin(t * 4), y_top - t * length, z + side * (0.08 + 0.05 * math.sin(t * 5))) for t in np.linspace(0, 1, 5)]
		return [
			sweep(self.cloth, self.light_end, pts, 0.1, width, (0, 0, side), rng, bend=0.008, jitter=0.006, box=True, u=(0.02, 0.98), name="Banner"),
			bar_raw(self.peg, self.peg_face, (x - width / 2 - 0.22, y_top + 0.03, z + side * 0.14), (x + width / 2 + 0.22, y_top + 0.03, z + side * 0.14), 0.2, 0.2, front=(0, 1, 0), box=True, bend=0.0, jitter=0.004, rng=rng, u=(0.05, 0.95), name="BannerRod"),
		]

	def block(self, strip, end, x, y, z, sx, sy, sz, yaw=0.0):
		"""one chunky stone, centred. Its long side runs across the bridge; depth and height stay near what the strip was painted for."""
		rng = self.rng
		L = sz if sz >= sx else sx
		w = sx if sz >= sx else sz
		u0 = rng.uniform(0, max(0.001, 1 - L / strip.studs))
		a, b = ((0, 0, -L / 2), (0, 0, L / 2)) if sz >= sx else ((-L / 2, 0, 0), (L / 2, 0, 0))
		front = (1, 0, 0) if sz >= sx else (0, 0, 1)
		part = bar(strip, end, a, b, w, sy, front=front, bend=0.03, jitter=0.035, tip=0.05, rng=rng, u=(u0, min(1.0, u0 + L / strip.studs)), name="Stone")
		return part.moved((x, y, z), PR["ry"](yaw + rng.uniform(-1.5, 1.5)))

	def wall(self, sign, half, courses):
		"""running bond across the bridge's end. Block lengths stay between 2.2 and 3.9, so none outgrows its paint. courses: (bottom y, height, depth, face x, wet)"""
		rng = self.rng
		parts = []
		for i, (y0, h, depth, face, low) in enumerate(courses):
			z = -half - (0 if i % 2 == 0 else rng.uniform(0.6, 1.1))
			strip = self.stone_low if low else self.stone
			while z < half:
				left = half - z
				wd = rng.uniform(2.3, 3.8)
				if left < 2.3 + 2.3:
					wd = min(max(left, 2.3), 3.8)
				dp = depth + rng.uniform(-0.05, 0.05)
				parts.append(self.block(strip, self.stone_end, sign * (face + dp / 2), y0 + h / 2, z + wd / 2, dp, h - 0.04, wd - 0.05))
				z += wd
		return parts

	def gate_stones(self, x, half, y0):
		"""two stacked stones either side of the deck at the bank"""
		rng = self.rng
		parts = []
		for sign in (-1, 1):
			for side in (-1, 1):
				z = side * half
				cx = sign * x + rng.uniform(-0.1, 0.1)
				parts.append(self.block(self.gate_low, self.gate_end, cx, y0 + 0.6, z, 2.2, 1.2, 2.4, yaw=rng.uniform(-5, 5)))
				parts.append(self.block(self.gate_up, self.gate_end, cx + rng.uniform(-0.1, 0.1), y0 + 1.2 + 0.42, z + rng.uniform(-0.1, 0.1), 1.75, 0.85, 1.9, yaw=rng.uniform(-9, 9)))
		return parts

	def sleeve(self, p0, p1, w, h, front=(0, 1, 0)):
		"""rope wound round a beam: a short thick stretch of coil"""
		return bar_raw(self.coil, self.light_end, p0, p1, w, h, front=front, ch=0.2, bend=0.0, jitter=0.012, rng=self.rng, u=(0, 1), name="Coil")

	def knot(self, c, size):
		c = np.array(c, float)
		return bar_raw(self.coil, self.light_end, c - (size / 2, 0, 0), c + (size / 2, 0, 0), size, size, front=(0, 0, 1), box=True, bend=0.0, jitter=0.012, rng=self.rng, u=(0, 0.6), name="Knot")

	def rope_line(self, pts, w=0.28):
		"""a rope through points, resampled so each segment is exactly one repeat of its paint"""
		pts = np.array(pts, float)
		seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
		arc = np.concatenate(([0], np.cumsum(seg)))
		n = max(1, int(round(arc[-1] / ROPE_L)))
		fine = np.linspace(0, arc[-1], n + 1)
		out = np.column_stack([np.interp(fine, arc, pts[:, i]) for i in range(3)])
		return sweep(self.rope, self.light_end, out, w, w, (0, 1, 0.01) if abs(pts[-1][1] - pts[0][1]) > arc[-1] * 0.9 else (0, 0, 1), self.rng, bend=0.006, jitter=0.004, ch=w * 0.3, tile=True, name="Rope")


# ---------------------------------------------------------------- the bridges


def chunky(P):
	"""long and level. Big capped end posts bookend the run, smaller posts between, on a slate wall at each bank. Dark structure, light deck, a mid lower rail."""
	k = Kit(P, 37)
	W, HALF = 9.0, 19.5
	FOOT = -3.2
	END_W, MID_W = 2.0, 1.42
	# the marks say what touches each post, in studs up from its foot: the low rail and top rail, the side beam, the knee braces.
	# face numbers: 0 is the strip's top, 2 its bottom. Middle posts have rails on both; end posts are turned so face 2 looks along the bridge.
	beam_y, top_y, low_y = -PLANK_T - 0.56 - FOOT, 2.6 - FOOT, 1.5 - FOOT
	beam_mark = ((0, 2), beam_y - 0.58, beam_y + 0.58, 0.42)
	knee_mark = ((0, 2), 0.3, 1.0, 0.38)
	k.wood("post_mid", 6.3, MID_W, MID_W, 0.2, WOOD_DARK, grad="along", hook=touches((beam_mark, knee_mark, ((0, 2), top_y - 0.22, top_y + 0.22, 0.24), ((0, 2), low_y - 0.18, low_y + 0.18, 0.2))), edges=(1, 3, 5, 7), level=0.45, window=(0.5, 0.97), gaps=(0.6, 1.2), lengths=(0.7, 1.4))
	k.wood("post_end", 6.6, END_W, END_W, 0.26, WOOD_DARK, grad="along", hook=touches((beam_mark, knee_mark, ((2,), top_y - 0.22, top_y + 0.22, 0.24), ((2,), low_y - 0.18, low_y + 0.18, 0.2))), edges=(1, 3, 5, 7), level=0.45, window=(0.5, 0.97), gaps=(0.6, 1.2), lengths=(0.7, 1.4))
	k.wood("cap_end", 0.9, 2.42, 2.42, 0.22, WOOD_DARK, edges=(1, 7), level=0.6, gaps=(0.2, 0.4), lengths=(0.3, 0.6))
	k.wood("beam", 12.2, 0.8, 1.15, 0.16, WOOD_DARK, knots=3, level=0.55)
	k.wood("cross", 8.0, 1.0, 1.0, 0.14, WOOD_DARK, knots=1, hook=ends_dark(), level=0.4)
	k.wood("knee", 3.6, 0.72, 0.72, 0.1, WOOD_DARK, knots=0, hook=ends_dark(), level=0.5, gaps=(0.6, 1.6), lengths=(0.7, 1.4))
	k.wood("rail", 8.9, 0.44, 0.44, 0.12, WOOD_LIGHT, knots=1, hook=chain(ends_dark(0.3), hand_worn), level=0.85, gaps=(0.9, 2.2))
	k.wood("rail_low", 8.9, 0.36, 0.36, 0.1, WOOD_MID, knots=1, hook=ends_dark(0.3), level=0.55, gaps=(1.2, 2.6))
	k.planks(W)
	k.small_parts()
	k.stone_strips(2.9, 2.05)
	k.end_grain("dark_end", 1.15, 0.8, WOOD_DARK)
	k.end_grain("big_end", END_W, END_W, WOOD_DARK)
	k.end_grain("cap_top", 2.42, 2.42, WOOD_DARK)
	k.end_grain("mid_top", MID_W, MID_W, WOOD_DARK)
	k.end_grain("light_end", 0.44, 0.44, WOOD_LIGHT)
	k.paint_all()

	rng = k.rng
	path = Path(lambda x: -0.1 * (1 - (x / HALF) ** 2) + 0.03 * math.sin(x * 0.5), -HALF, HALF)
	parts = k.deck(path, W) + [k.under(path, W, 5)]
	xs = (-16.0, -8.0, 0.0, 8.0, 16.0)
	for side in (-1, 1):
		z = side * (W / 2 - 0.1)
		for a, b in ((-19.4, -7.5), (-8.5, 0.5), (-0.5, 8.5), (7.5, 19.4)):
			parts.append(k.beam_run(k.beam, path, side * (W / 2 - 0.25), a, b, -PLANK_T - 0.56, n=3))
		for i, x in enumerate(xs):
			y = path.y_of(x)
			is_end = i in (0, len(xs) - 1)
			pw = END_W if is_end else MID_W
			if is_end:
				parts.append(k.post_at(k.post_end, k.big_end, x, FOOT, y + 3.3, z, pw, -1 if x > 0 else 1))
				parts.append(k.cap(k.cap_end, k.cap_top, x, y + 3.26, y + 3.95, z, 2.42))
			else:
				parts.append(k.post_at(k.post_mid, k.mid_top, x, FOOT, y + 3.0, z, pw, side))
			parts += k.peg_at((x, y - 0.75, z + side * (pw / 2 + 0.02)), (0, 0, side))
			parts += k.peg_at((x, FOOT + 0.8, z + side * (pw / 2 + 0.02)), (0, 0, side), size=0.66)
			for d in (-1, 1):
				parts.append(k.knee_at((x + d * 0.3, FOOT + 0.65, z), (x + d * 2.9, -PLANK_T - 1.0, z), z))
			if i < len(xs) - 1:
				nx = xs[i + 1]
				y2 = path.y_of(nx)
				pw2 = END_W if i + 1 == len(xs) - 1 else MID_W
				parts.append(k.rod(k.rail, (x, y + 2.6, z), (nx, y2 + 2.6, z), side=side))
				parts.append(k.rod(k.rail_low, (x, y + 1.5, z), (nx, y2 + 1.5, z), w=0.36, h=0.36, side=side))
				for yy, size in ((2.6, 0.6), (1.5, 0.5)):
					parts.append(k.collar(x + pw / 2 - 0.04, y + yy, z, 1, size))
					parts.append(k.collar(nx - pw2 / 2 + 0.04, y2 + yy, z, -1, size))
	for x in xs:
		y = path.y_of(x) - PLANK_T - 1.1
		parts.append(bar(k.cross, k.dark_end, (x, y - 0.25, -W / 2 + 0.55), (x + 0.04, y - 0.22, W / 2 - 0.55), 1.0, 1.0, front=(1, 0, 0), bend=0.012, rng=rng, u=(0.02, 0.02 + (W - 1.1) / 8.0), name="Cross"))
	for sign in (-1, 1):
		parts += k.wall(sign, W / 2 + 2.0, ((-7.8, 2.0, 3.0, 16.6, True), (-5.8, 2.05, 2.9, 16.6, False), (-3.75, 2.15, 2.7, 17.0, False)))
	parts += k.gate_stones(18.0, W / 2 + 1.45, -0.9)
	parts += k.banner(-16.0, path.y_of(-16.0) + 3.15, W / 2 - 0.1 + 1.0, 1)
	return k, parts


def lattice(P):
	"""a gentle curve. The rhythm climbs: heavy capped posts at the banks, slim ones between, a taller pair either side of the crown. Dark posts and beams, mid lattice, light top rail and deck."""
	k = Kit(P, 53)
	W, HALF, RISE = 7.6, 20.0, 3.3
	END_W, CROWN_W, MID_W = 1.78, 1.5, 1.28
	POST = 5.45  # 2.25 under the deck, 3.2 over
	beam_mark = ((0, 2), 2.25 - PLANK_T - 0.56 - 0.58, 2.25 - PLANK_T - 0.56 + 0.58, 0.42)
	top = 2.25 + 2.45
	low = 2.25 + 0.8

	def post_hook(faces):
		return chain(touches((beam_mark, (faces, top - 0.2, top + 0.2, 0.22), (faces, low - 0.17, low + 0.17, 0.19))), mossy_post(2.25 / POST))

	for name, width, faces, ch in (("post_end", END_W, (2,), 0.24), ("post_crown", CROWN_W, (0, 2), 0.2), ("post_mid", MID_W, (0, 2), 0.18)):
		k.wood(name, POST, width, width, ch, WOOD_DARK, grad="along", hook=post_hook(faces), edges=(1, 3, 5, 7), level=0.45, window=(0.5, 0.88), gaps=(0.5, 1.1), lengths=(0.7, 1.4))
	k.wood("cap_end", 0.7, 2.14, 2.14, 0.2, WOOD_DARK, edges=(1, 7), level=0.6, gaps=(0.2, 0.4), lengths=(0.3, 0.6))
	k.wood("cap_crown", 0.9, 1.76, 1.76, 0.18, WOOD_DARK, edges=(1, 7), level=0.6, gaps=(0.2, 0.4), lengths=(0.3, 0.6))
	k.wood("beam", 12.2, 0.8, 1.15, 0.16, WOOD_DARK, knots=3, level=0.55)
	k.wood("beam_low", 8.3, 0.66, 0.74, 0.12, WOOD_DARK, knots=2, level=0.45)
	k.wood("cross", 7.0, 0.9, 0.9, 0.13, WOOD_DARK, knots=1, hook=ends_dark(), level=0.4)
	k.wood("knee", 3.2, 0.72, 0.72, 0.1, WOOD_DARK, hook=ends_dark(), level=0.5, gaps=(0.6, 1.6), lengths=(0.7, 1.4))
	k.wood("rail", 8.1, 0.42, 0.42, 0.11, WOOD_LIGHT, knots=1, hook=chain(ends_dark(0.3), hand_worn), level=0.85, gaps=(0.9, 2.2))
	k.wood("rail_low", 7.9, 0.36, 0.36, 0.1, WOOD_MID, knots=1, hook=ends_dark(0.3), level=0.55, gaps=(1.2, 2.6))
	k.wood("lattice_strip", 6.2, 0.2, 0.28, 0.0, WOOD_MID, hook=ends_dark(0.25), level=0.55, gaps=(0.8, 2.0), lengths=(0.6, 1.3))
	k.planks(W, 1.36)
	k.small_parts()
	k.moss_tile()
	k.stone_strips(2.9, 1.75)
	k.end_grain("dark_end", 1.15, 0.8, WOOD_DARK)
	k.end_grain("light_end", 0.42, 0.42, WOOD_LIGHT)
	k.paint_all()

	rng = k.rng
	R = (HALF**2 + RISE**2) / (2 * RISE)
	path = Path(lambda x: math.sqrt(R * R - x * x) - (R - RISE), -HALF, HALF)
	parts = k.deck(path, W, width=(1.25, 1.45)) + [k.under(path, W, 17)]
	xs = (-17.5, -10.5, -3.5, 3.5, 10.5, 17.5)
	for side in (-1, 1):
		z = side * (W / 2 - 0.02)
		for a, b in ((-20.0, -9.6), (-11.4, 0.5), (-0.5, 11.4), (9.6, 20.0)):
			parts.append(k.beam_run(k.beam, path, side * (W / 2 - 0.25), a, b, -PLANK_T - 0.56, n=4))
		for a, b in ((-15.5, -7.6), (-8.2, 0.3), (-0.3, 8.2), (7.6, 15.5)):
			parts.append(k.beam_run(k.beam_low, path, side * (W / 2 - 0.5), a, b, -PLANK_T - 1.35, n=4, w=0.66, h=0.74))

		def width_of(i):
			return END_W if i in (0, 5) else CROWN_W if i in (2, 3) else MID_W

		for i, x in enumerate(xs):
			y = path.y_of(x)
			pw = width_of(i)
			foot = y - 2.25
			strip = k.post_end if i in (0, 5) else k.post_crown if i in (2, 3) else k.post_mid
			parts.append(k.post_at(strip, k.moss, x, foot, y + 3.2, z, pw, (-1 if x > 0 else 1) if i in (0, 5) else side))
			if i in (0, 5):
				parts.append(k.cap(k.cap_end, k.moss, x, y + 3.16, y + 3.7, z, 2.14))
			if i in (2, 3):
				parts.append(k.cap(k.cap_crown, k.moss, x, y + 3.16, y + 3.92, z, 1.76))
			parts += k.peg_at((x, y - PLANK_T - 0.75, z + side * (pw / 2 + 0.0)), (0, 0, side), size=0.54)
			parts += k.peg_at((x, foot + 0.55, z + side * (pw / 2 + 0.0)), (0, 0, side), size=0.58)
			for d in (-1, 1):
				parts.append(k.knee_at((x + d * 0.3, foot + 0.45, z), (x + d * 2.4, path.y_of(x + d * 2.4) - PLANK_T - 1.45, z), z))
			if i < len(xs) - 1:
				nxt = xs[i + 1]
				y2 = path.y_of(nxt)
				pw2 = width_of(i + 1)
				y_top_a, y_top_b = y + 2.45, y2 + 2.45
				parts.append(k.rod(k.rail, (x, y_top_a, z), (nxt, y_top_b, z), bow=0.42, n=6, side=side, w=0.42, h=0.42))
				s0, s1 = path.s_of(x), path.s_of(nxt)
				parts.append(sweep(k.rail_low, k.light_end, path.line(s0, s1, 4, 0.8, z), 0.36, 0.36, (0, 0, side), rng, bend=0.008, ch=0.1, name="LowRail"))
				for yy, ya, yb, size in ((2.45, y_top_a, y_top_b, 0.58), (0.8, y + 0.8, y2 + 0.8, 0.5)):
					parts.append(k.collar(x + pw / 2 - 0.04, ya + (0.08 if yy > 1 else 0), z, 1, size))
					parts.append(k.collar(nxt - pw2 / 2 + 0.04, yb + (0.08 if yy > 1 else 0), z, -1, size))
				xa, xb = x + pw / 2 + 0.15, nxt - pw2 / 2 - 0.15
				ya, yb = path.y_of(xa) + 0.8, path.y_of(xb) + 0.8
				ta = y_top_a + 0.42 * math.sin(math.pi * 0.1)
				tb = y_top_b + 0.42 * math.sin(math.pi * 0.9)
				mx = (xa + xb) / 2
				for p0, p1 in (((xa, ya, z), (xb, tb, z)), ((xb, yb, z), (xa, ta, z))):
					parts.append(bar(k.lattice_strip, k.light_end, p0, p1, 0.2, 0.28, front=(0, 0, side), box=True, bend=0.006, jitter=0.006, rng=rng, u=(0.02, 0.02 + min(0.96, math.dist(p0, p1) / 6.2)), name="Lattice"))
				parts.append(bar_raw(k.lattice_strip, k.light_end, (mx, path.y_of(mx) + 0.8, z), (mx, (ta + tb) / 2 + 0.3, z), 0.2, 0.28, front=(0, 0, side), box=True, bend=0.004, jitter=0.006, rng=rng, u=(0.5, 0.5 + 2.0 / 6.2), name="Spindle"))
	for x in xs:
		y = path.y_of(x) - PLANK_T - 1.75
		parts.append(bar(k.cross, k.dark_end, (x, y, -W / 2 + 0.5), (x + 0.03, y + 0.02, W / 2 - 0.5), 0.9, 0.9, front=(1, 0, 0), bend=0.01, rng=rng, u=(0.02, 0.02 + (W - 1) / 7.0), name="Cross"))
	for sign in (-1, 1):
		parts += k.wall(sign, W / 2 + 2.0, ((-7.8, 1.73, 3.0, 16.8, True), (-6.07, 1.73, 2.9, 16.8, False), (-4.34, 1.72, 2.9, 16.8, False), (-2.62, 1.72, 2.7, 17.2, False)))
	parts += k.gate_stones(19.2, W / 2 + 1.5, -0.9)
	parts += k.banner(-3.5, path.y_of(-3.5) + 3.1, W / 2 - 0.02 + 0.75, 1, length=2.6, width=1.15)
	return k, parts


def rope(P):
	"""dark timber frames, pale rope, a light deck on a shallow sag, slate under the frames. Each side has its own A-frame, so the path stays open: the concept's frames read as one portal with its X in the way."""
	k = Kit(P, 71)
	W, XT, SAG = 6.4, 19.5, 0.5
	TOP = 5.8
	k.wood("leg", 7.4, 1.3, 1.3, 0.18, WOOD_DARK, knots=1, grad="along", foot=True, edges=(1, 7), level=0.45, window=(0.3, 0.95), gaps=(0.8, 1.6))
	k.wood("top_beam", 5.6, 1.15, 1.15, 0.17, WOOD_DARK, knots=1, edges=(1, 7), level=0.6, gaps=(0.8, 1.6))
	k.wood("sill", 8.8, 1.1, 1.0, 0.16, WOOD_DARK, knots=1, level=0.45, hook=None)
	k.wood("brace", 5.6, 0.5, 0.56, 0.08, WOOD_DARK, hook=ends_dark(0.35), level=0.5, gaps=(0.6, 1.6), lengths=(0.7, 1.4))
	k.wood("cross", 7.6, 1.0, 0.9, 0.14, WOOD_DARK, knots=1, hook=ends_dark(), level=0.4)
	k.planks(W, 1.16)
	k.small_parts()
	k.rope_strips()
	k.stone_strips(3.0, 2.0, gate=False)
	k.end_grain("dark_end", 1.15, 1.15, WOOD_DARK)
	k.end_grain("light_end", 0.5, 0.5, WOOD_LIGHT)
	k.paint_all()

	rng = k.rng
	END = XT - 3.0
	deck_y = lambda x: -SAG * (1 - (x / END) ** 2) if abs(x) < END else 0.0
	path = Path(deck_y, -XT - 2.4, XT + 2.4)
	parts = k.deck(path, W, width=(1.08, 1.24), gap=(0.05, 0.1)) + [k.under(path, W, 11)]
	for sign in (-1, 1):
		xt = sign * XT
		for side in (-1, 1):
			z = side * (W / 2 + 0.8)
			for d in (-1, 1):
				parts.append(bar_raw(k.leg, k.dark_end, (xt + d * 2.95, -1.0, z), (xt + d * 0.95, TOP - 0.45, z), 1.3, 1.3, w1=1.18, h1=1.18, front=(0, 0, side), bend=0.012, rng=rng, u=(0, 6.9 / 7.4), name="Leg"))
			parts.append(bar(k.top_beam, k.dark_end, (xt - 2.75, TOP, z), (xt + 2.75, TOP + 0.04, z), 1.15, 1.15, front=(0, 0, side), bend=0.01, rng=rng, u=(0.01, 0.01 + 5.5 / 5.6), name="TopBeam"))
			parts.append(bar(k.sill, k.dark_end, (xt - 4.3, -0.55, z), (xt + 4.3, -0.5, z), 1.1, 1.0, front=(0, 0, side), bend=0.012, rng=rng, u=(0.01, 0.01 + 8.6 / 8.8), name="Sill"))
			for d in (-1, 1):
				parts.append(bar(k.brace, k.dark_end, (xt - d * 2.4, 0.35, z - side * 0.08), (xt + d * 1.1, 4.5, z + side * 0.08), 0.5, 0.56, front=(0, 0, side), bend=0.008, rng=rng, u=(0.02, 0.02 + min(0.96, 5.43 / 5.6)), name="Brace"))
			for d in (-1, 1):
				parts.append(k.sleeve((xt + d * 1.5, TOP + 0.02, z), (xt + d * 2.3, TOP + 0.02, z), 1.42, 1.42, front=(0, 0, side)))
				parts.append(k.sleeve((xt + d * 2.65, -0.15, z), (xt + d * 2.65, 0.65, z), 1.5, 1.5, front=(0, 0, side)))
				parts += k.peg_at((xt + d * 3.85, -0.5, z + side * 0.55), (0, 0, side), size=0.6)
		parts.append(bar(k.cross, k.dark_end, (sign * (XT - 1.1), -PLANK_T - 0.5, -W / 2 - 0.5), (sign * (XT - 1.1), -PLANK_T - 0.48, W / 2 + 0.5), 1.0, 0.9, front=(0, 1, 0), bend=0.01, rng=rng, u=(0.02, 0.02 + (W + 1) / 7.6), name="Cross"))
		parts += k.wall(sign, W / 2 + 2.4, ((-8.8, 2.0, 3.0, 16.2, True), (-6.8, 2.0, 3.0, 16.2, False), (-4.8, 2.0, 3.0, 16.2, False), (-2.8, 2.0, 2.8, 16.5, False)))
	span = XT - 1.5
	for side in (-1, 1):
		z = side * (W / 2 + 0.45)
		top = lambda x: deck_y(x) + 3.0 + (TOP - 3.0) * (abs(x) / span) ** 4
		low = lambda x: deck_y(x) + 2.1 + (TOP - 0.25 - 2.1) * (abs(x) / span) ** 4
		xs = np.linspace(-span, span, 25)
		parts.append(k.rope_line([(x, top(x), z + side * 0.35 * (abs(x) / span) ** 4) for x in xs]))
		parts.append(k.rope_line([(x, low(x), z + side * 0.35 * (abs(x) / span) ** 4) for x in xs], w=0.24))
		for x in np.arange(-14.0, 14.1, 4.0):
			x += rng.uniform(-0.08, 0.08)
			y0 = deck_y(x)
			parts.append(k.rope_line([(x, y0 - 0.1, z - side * 0.02), (x, top(x), z)], w=0.2))
			parts.append(k.knot((x, top(x), z), 0.4))
			parts.append(k.knot((x, low(x), z), 0.34))
			parts += k.peg_at((x, y0 - PLANK_T * 0.5, z + side * 0.05), (0, 0, side), size=0.42, depth=0.16)
	parts += k.banner(-XT, TOP - 0.62, W / 2 + 0.8 + 0.58, 1, length=3.3, width=1.3)
	return k, parts


def stretch_report(name, parts):
	"""how far each part type strays from its paint's scale, by area. Skips what's meant to repeat or carries no marks to stretch."""
	skip = {"Under", "Recess", "Rope", "Knot", "Coil", "Banner", "BannerRod", "Peg", "Collar"}
	table = {}
	for part in parts:
		if part.name in skip:
			continue
		nominal = STONE_T if part.name == "Stone" else T
		for a, b, c, ua, ub, uc, _g in part.tris:
			e1, e2 = b - a, c - a
			n = np.cross(e1, e2)
			area = np.linalg.norm(n) / 2
			if area < 1e-5 or (part.name == "Plank" and n[1] / (2 * area) < -0.5):  # a plank's underside sits on the dark board: never seen
				continue
			x = e1 / np.linalg.norm(e1)
			y = np.cross(n, x)
			y /= np.linalg.norm(y)
			M = np.array(((e1 @ x, e2 @ x), (e1 @ y, e2 @ y)))
			U = np.array(((ub[0] - ua[0], uc[0] - ua[0]), (ub[1] - ua[1], uc[1] - ua[1])))
			try:
				s = np.linalg.svd(U @ np.linalg.inv(M), compute_uv=False)
			except np.linalg.LinAlgError:
				continue
			off = s[0] > nominal * 1.15 * 1.4 or s[1] < nominal * 0.85 / 1.1
			t = table.setdefault(part.name, [0.0, 0.0])
			t[0] += area
			t[1] += area if off else 0
	total = sum(t[0] for t in table.values())
	bad = sum(t[1] for t in table.values())
	print(f"{name}: {bad / total * 100:.0f}% of the area is thinner than its paint's scale by more than 15%")
	for part, (area, off) in sorted(table.items(), key=lambda kv: -kv[1][1]):
		if off / area > 0.1:
			print(f"   {part}: {off / area * 100:.0f}% of {area:.0f} sq studs")
	return bad / total


def build():
	P = PR["load_painter"]()
	PR["PAINTER"] = P
	P["SHADOW"] = np.array((70, 48, 70), float)  # the props' plum
	report, bounds, sheets, used = {}, {}, {}, {}
	for name, fn in (("BridgeChunky", chunky), ("BridgeLattice", lattice), ("BridgeRope", rope)):
		k, parts = fn(P)
		raw = Image.fromarray(np.clip(k.sheet.img * P["GRADE"] * PR["STUDIO_LIFT"], 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS)
		free = [s.rect for s in k.specs if s.free]
		keep = [s.rect for s in k.specs if s.keep]
		sheets[name] = f"Woodbridge_B_{name}.png"
		finish_sheet(np.array(raw), free, keep).save(os.path.join(OUT, sheets[name]))
		report[name] = write_obj(os.path.join(OUT, name + ".obj"), name, parts)
		v = np.array([p for part in parts for t in part.tris for p in t[:3]])
		bounds[name] = [round(float(x), 3) for x in (v[:, 0].min(), v[:, 0].max(), v[:, 1].min(), v[:, 1].max(), v[:, 2].min(), v[:, 2].max())]
		used[name] = k.used
		stretch_report(name, parts)
	json.dump({"Triangles": report, "Bounds": bounds, "Sheets": sheets, "SheetUsedToRow": used}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print(report, "sheets used to rows", used, "of", SHEET)


def compare_sheet():
	r = os.path.join(OUT, "renders")
	font = ImageFont.truetype("arial.ttf", 22)
	ref = Image.open(os.path.join(OUT, "reference.webp")).convert("RGB")
	crops = {"ref_top": (470, 10, 1510, 245), "ref_mid": (500, 240, 1480, 442), "ref_low": (510, 440, 1490, 662)}
	W = 1800

	def tile(im, label, cw):
		im = im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS)
		d = ImageDraw.Draw(im)
		d.rectangle((0, 0, min(cw, 16 + d.textlength(label, font=font)), 30), fill=(38, 30, 44))
		d.text((8, 3), label, fill=(240, 230, 210), font=font)
		return im

	rows = []
	for crop, view, label in (("ref_top", "iso_chunky", "Chunky flat"), ("ref_mid", "iso_lattice", "Lattice arch"), ("ref_low", "iso_rope", "Rope bridge")):
		rows.append([tile(ref.crop(crops[crop]), "Your image", W // 2), tile(Image.open(os.path.join(r, view + ".png")).convert("RGB"), label, W // 2)])
	for view, label in (("far_chunky", "Chunky"), ("far_lattice", "Lattice arch"), ("far_rope", "Rope bridge")):
		im = Image.open(os.path.join(r, view + ".png")).convert("RGB")
		rows.append([tile(im, label + " from about 100 studs", W // 2), tile(im.filter(ImageFilter.GaussianBlur(6)), "Blurred: do the big shapes still read?", W // 2)])
	for row in (
		(("hero_chunky", "Chunky over water, 5.2-stud player"), ("walk_chunky", "Walking")),
		(("hero_lattice", "Lattice arch over water"), ("walk_lattice", "Walking")),
		(("hero_rope", "Rope bridge over water"), ("walk_rope", "Walking")),
		(("close_post", "Up close: post, pegs, rails"), ("close_lattice", "Up close: lattice and moss")),
		(("close_rope", "Up close: rope and coils"), ("above_rope", "From above and behind, back faces hidden as in Roblox")),
	):
		rows.append([tile(Image.open(os.path.join(r, n + ".png")).convert("RGB"), l, W // 2) for n, l in row])
	out_rows = []
	for ims in rows:
		c = Image.new("RGB", (W, max(i.height for i in ims)), (38, 30, 44))
		for i, im in enumerate(ims):
			c.paste(im, (i * W // 2, 0))
		out_rows.append(c)
	total = Image.new("RGB", (W, sum(c.height for c in out_rows)))
	y = 0
	for c in out_rows:
		total.paste(c, (0, y))
		y += c.height
	total.save(os.path.join(OUT, "compare_sheet.jpg"), quality=92)
	print("wrote", os.path.join(OUT, "compare_sheet.jpg"), total.size)


os.makedirs(OUT, exist_ok=True)
if "--sheet" in sys.argv:
	compare_sheet()
else:
	build()
