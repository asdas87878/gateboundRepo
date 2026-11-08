"""Paints the crooked cottage study's sheets (tools/blender/crooked_cottage.py; private, research/crooked_cottage).

  python tools/art/paint_crooked_cottage.py [--only RoofRB,Timber] [--no-ao]

Every island is painted from its own pattern coordinates (u, v in studs), world position and normal per texel, by its kind. Colours
are the reference's (measured, see the palettes): salmon-pink tiles in a few grouped tones with a sunlit lip and the next row's
shadow, warm tan timbers with a soft grain, cream render with ragged patches of orange brick, lilac-grey stones, deep blue glass.
Flat tones in big groups, soft painted edges, a faint brush grain. Painted at 2x, shrunk with Lanczos.
"""

import argparse
import json
import math
import os
import time

import numpy as np

np.seterr(over="ignore")
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.interpolate import griddata

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# the study by default; another house built on the same library names its folder (COTTAGE_OUT=art/kit/rosecottage)
OUT = os.path.join(ROOT, os.environ.get("COTTAGE_OUT") or os.path.join("research", "crooked_cottage"))
SS = 2

layout = json.load(open(os.path.join(OUT, "layout.json")))
K = layout.get("Consts", {})
BRICKS = K.get("Bricks", [])
MOSS = K.get("Moss", [])
bake = np.load(os.path.join(OUT, "bake.npz"))
ISL = bake["isl"]
order = np.argsort(ISL, kind="stable")
ISL_S, UV_S, POS_S, NOR_S = ISL[order], bake["uv"][order], bake["pos"][order], bake["nor"][order]
SIZE = layout["Size"]


# ---------------------------------------------------------------------------------------------------------------- helpers
def C(*rgb):
	return np.array(rgb, dtype=np.float32)


def ss(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def mix(a, b, t):
	return a + (b - a) * np.asarray(t, dtype=np.float32)


def hsh(*vals, seed=0):
	h = np.int64(seed * 2654435761 % 2147483647 + 1013904223)
	for i, v in enumerate(vals):
		v = np.asarray(v).astype(np.int64)
		h = h ^ ((v + 0x9E3779B9 + (h << 6) + (h >> 2)) * (2 * i + 1) * 73856093)
		h = (h * 2246822519) & 0xFFFFFFFF
	h = (h ^ (h >> 15)) * 2654435761 & 0xFFFFFFFF
	return ((h ^ (h >> 13)) & 0xFFFFFF).astype(np.float32) / float(0x1000000)


_LATTICE = np.random.default_rng(7).random((64, 64, 64)).astype(np.float32)


def vnoise(P, scale, seed=0):
	q = P / scale + seed * 17.31
	i = np.floor(q).astype(np.int64)
	f = q - i
	f = f * f * (3 - 2 * f)
	out = np.zeros(P.shape[:-1], dtype=np.float32)
	for dx in (0, 1):
		for dy in (0, 1):
			for dz in (0, 1):
				w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
				out += w * _LATTICE[(i[..., 0] + dx) % 64, (i[..., 1] + dy) % 64, (i[..., 2] + dz) % 64]
	return out * 2 - 1


def fbm(P, scale, seed=0, octaves=3):
	out = np.zeros(P.shape[:-1], dtype=np.float32)
	amp, tot = 1.0, 0.0
	for o in range(octaves):
		out += amp * vnoise(P, scale / (2**o), seed + o)
		tot += amp
		amp *= 0.5
	return out / tot


def grain(u, v, along_u, scale_along, scale_across, seed):
	a, b = (u, v) if along_u else (v, u)
	P = np.stack([a / scale_along, b / scale_across, np.zeros_like(a)], -1)
	return vnoise(P, 1.0, seed)


def name_seed(s):
	return sum((i + 1) * 131 * ord(ch) for i, ch in enumerate(str(s))) % 100000


class Ctx:
	def __init__(self, key, info):
		self.key = int(key)
		self.info = info
		self.p = info["Params"]
		self.kind = info["Kind"]
		s2 = info["S"] * SS
		self.s2 = s2
		self.w = info["PW"] * SS
		self.h = info["PH"] * SS
		lo = np.searchsorted(ISL_S, self.key, "left")
		hi = np.searchsorted(ISL_S, self.key, "right")
		uv, pos, nor = UV_S[lo:hi], POS_S[lo:hi], NOR_S[lo:hi]
		U0, V1 = info["U0"], info["V1"]
		px = (uv[..., 0] - U0) * s2
		py = (V1 - uv[..., 1]) * s2
		img = Image.new("L", (self.w, self.h), 0)
		d = ImageDraw.Draw(img)
		for t in range(len(uv)):
			d.polygon([(float(px[t, 0]), float(py[t, 0])), (float(px[t, 1]), float(py[t, 1])), (float(px[t, 2]), float(py[t, 2]))], fill=255, outline=255)
		self.mask = np.asarray(img) > 0
		yy, xx = np.mgrid[0 : self.h, 0 : self.w].astype(np.float32)
		self.u = U0 + (xx + 0.5) / s2
		self.v = V1 - (yy + 0.5) / s2
		pts = np.stack([px.ravel(), py.ravel()], -1)
		Pv, Nv = pos.reshape(-1, 3), nor.reshape(-1, 3)
		self.P = self.interp(pts, Pv, xx, yy)
		self.N = self.interp(pts, Nv, xx, yy)
		n = np.linalg.norm(self.N, axis=-1, keepdims=True)
		self.N = self.N / np.maximum(n, 1e-6)
		self.seed = int(self.p.get("Seed", name_seed(f"{self.p.get('Roof', '')}{self.p.get('Part', '')}{self.key}")))
		self.rng = np.random.default_rng(self.seed)

	def interp(self, pts, vals, xx, yy):
		A = np.concatenate([pts, np.ones((len(pts), 1))], 1)
		coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
		fit = A @ coef
		grid = np.stack([xx + 0.5, yy + 0.5], -1)
		if np.abs(fit - vals).max() < 0.02 or len(pts) < 4:
			return (grid[..., 0, None] * coef[0] + grid[..., 1, None] * coef[1] + coef[2]).astype(np.float32)
		uniq, idx = np.unique(np.round(pts, 3), axis=0, return_index=True)
		out = np.zeros((self.h, self.w, 3), dtype=np.float32)
		m = self.mask
		q = grid[m]
		try:
			res = griddata(pts[idx], vals[idx], q, method="linear")
			bad = np.isnan(res[:, 0])
			if bad.any():
				res[bad] = griddata(pts[idx], vals[idx], q[bad], method="nearest")
		except Exception:
			res = griddata(pts[idx], vals[idx], q, method="nearest")
		out[m] = res
		return out

	def full(self, col):
		return np.broadcast_to(np.asarray(col, dtype=np.float32), self.u.shape + (3,)).astype(np.float32).copy()


def soft_edge(c, width):
	"""0 on the island's border, 1 from `width` studs in (painted edges catch light or darken)"""
	d = ndimage.distance_transform_edt(np.pad(c.mask, 1))[1:-1, 1:-1].astype(np.float32) / c.s2
	return ss(0.0, width, d)


# ---------------------------------------------------------------------------------------------------------------- tiles
# measured on the reference: sunlit faces a light salmon (250, 182, 164), rose where they turn from the light, a few warm peach tiles
TILE_PINKS = [C(244, 160, 148), C(239, 152, 142), C(247, 170, 156), C(232, 144, 138), C(242, 158, 146)]
TILE_PEACH = C(248, 190, 140)
TILE_ROSE = C(214, 124, 122)
TILE_LIP = C(255, 214, 198)
TILE_SHADOW = C(190, 102, 116)
MOSS_DARK, MOSS_MID, MOSS_LIGHT = C(150, 168, 52), C(196, 210, 70), C(232, 236, 128)


def moss_level(P):
	lev = np.zeros(P.shape[:-1], dtype=np.float32)
	for (cx, cy, cz), r in MOSS:
		d = np.sqrt((P[..., 0] - cx) ** 2 + (P[..., 1] - cy) ** 2 + (P[..., 2] - cz) ** 2)
		lev = np.maximum(lev, 1 - ss(r * 0.5, r * 1.4, d))
	return lev


# where the reference's roofs go warm peach (sun-bleached tiles), as world spots: (centre, radius)
PEACH_SPOTS = K.get("Peach") or [((-7.5, 0.5, 15.0), 3.2), ((-3.0, -0.6, 14.4), 2.0), ((-29.0, 0.0, 7.0), 3.5), ((-24.0, 2.5, 8.5), 2.5), ((-12.5, 2.0, 18.0), 1.8)]


def spot_level(P, spots):
	lev = np.zeros(P.shape[:-1], dtype=np.float32)
	for c, r in spots:
		d = np.linalg.norm(P - np.array(c, dtype=np.float32), axis=-1)
		lev = np.maximum(lev, 1 - ss(r * 0.4, r, d))
	return lev


def paint_tile(c):
	W, L = c.p.get("W", 1.6), c.p.get("L", 2.7)
	row = 1.85
	r = hsh(c.seed, seed=3)
	# one calm salmon over the roof, a broad lean across it (big shapes first), each tile only a little its own
	col = c.full(TILE_PINKS[0])
	group = fbm(c.P, 8.0, 11, 2)
	col = mix(col, TILE_PINKS[3], (ss(0.0, 0.6, group) * 0.5)[..., None])
	col = mix(col, TILE_PINKS[2], (ss(0.0, 0.6, -group) * 0.5)[..., None])
	col = col * (1 + 0.045 * (r - 0.5))[..., None]
	peach = spot_level(c.P, PEACH_SPOTS) * (0.55 + 0.45 * ss(-0.3, 0.4, fbm(c.P, 1.6, 23, 2)))
	col = mix(col, TILE_PEACH, (peach * 0.6)[..., None])
	# lighter toward its sunlit foot; under the next row's lip a soft shadow
	v = c.v
	col = col * (1.05 - 0.08 * ss(0.0, row, v))[..., None]
	col = mix(col, TILE_SHADOW, (ss(row - 0.45, row - 0.02, v) * 0.26)[..., None])
	col = mix(col, TILE_LIP, ((1 - ss(0.0, 0.3, v)) * 0.24)[..., None])
	# a broad painted sheen across the tile and a faint grain along it
	sheen = np.exp(-(((v - 0.7 - 0.3 * r) / 0.5) ** 2)) * 0.07
	col = col * (1 + sheen + 0.02 * grain(c.u, c.v, True, 1.1, 0.16, c.seed % 97))[..., None]
	side = ss(0.0, 0.1, np.minimum(c.u, W - c.u))
	col = col * (0.93 + 0.07 * side)[..., None]
	m = moss_level(c.P)
	if m.max() > 0.01:
		cover = ss(0.3, 0.65, m + 0.25 * fbm(c.P, 0.9, 41, 2))
		col = mix(col, C(226, 200, 120), (cover * 0.4)[..., None])
	return col


def paint_tile_lip(c):
	t = c.p.get("Thick", 0.32)
	col = c.full(C(252, 202, 186))
	col = mix(col, C(226, 152, 146), (1 - ss(0.0, t * 0.8, c.v))[..., None] * 0.35)
	col = col * (1 + 0.04 * grain(c.u, c.v, True, 0.7, 0.1, c.seed % 89))[..., None]
	m = moss_level(c.P)
	if m.max() > 0.01:
		col = mix(col, C(226, 196, 120), (ss(0.45, 0.7, m) * 0.35)[..., None])
	return col


def paint_roof_under(c):
	return c.full(C(120, 64, 66))


def paint_soffit(c):
	"""the underside of the eaves: warm dark boards"""
	col = c.full(C(132, 82, 62))
	col = col * (1 + 0.08 * np.sin(c.u * 2 * math.pi / 1.1) * 0.5)[..., None]
	return col


# ---------------------------------------------------------------------------------------------------------------- timber
WOOD_LIGHT, WOOD_MID, WOOD_DARK = C(238, 180, 128), C(204, 136, 96), C(116, 68, 52)
WOOD_GRAIN = C(170, 104, 70)


def house_gradient(P):
	"""one gradient over the whole house: the wood a little richer and darker at the top"""
	return ss(4.0, 24.0, P[..., 2])


def paint_wood_face(c, base=None, along_u=True, width=None, edge=0.14, plank=None):
	base = WOOD_MID if base is None else base
	if c.p.get("Face") == "chamfer":
		# the rounded edge of a chunky timber: a touch lighter, smooth, so it reads as a soft catch-light
		col = c.full(mix(base, WOOD_LIGHT, 0.35))
		col = mix(col, WOOD_DARK, (house_gradient(c.P) * 0.25)[..., None])
		return col * (1 + 0.03 * grain(c.u, c.v, True, 2.0, 0.2, c.seed % 89))[..., None]
	col = c.full(base)
	g = house_gradient(c.P)
	col = mix(col, WOOD_DARK, (g * 0.34)[..., None])
	a, b = (c.u, c.v) if along_u else (c.v, c.u)
	# long soft grain streaks, a few darker ones, a knot now and then
	gr = grain(a, b, True, 2.4, 0.16, c.seed % 101)
	col = mix(col, WOOD_GRAIN, (ss(0.25, 0.75, gr) * 0.32)[..., None])
	fine = grain(a, b, True, 0.7, 0.05, c.seed % 103 + 7)
	col = col * (1 + 0.05 * fine)[..., None]
	# light on the arrises: a soft lighter band along the face's long edges (paint stands in for the bevel)
	if width:
		e = np.minimum(b, width - b)
		lit = 1 - ss(0.0, edge, e)
		col = mix(col, WOOD_LIGHT, (lit * 0.3)[..., None])
	if plank:
		seam = np.abs(((b / plank) % 1.0) - 0.5) * plank
		col = mix(col, WOOD_DARK, ((1 - ss(0.0, 0.05, plank / 2 - seam)) * 0.55)[..., None])
	return col


def paint_timber(c):
	return paint_wood_face(c, width=c.p.get("Width", 0.8))


def paint_barge(c):
	return paint_wood_face(c, base=C(168, 102, 72), width=c.p.get("Width", 1.0), edge=0.2)


def paint_end(c):
	"""end grain: lighter, a ring or two"""
	w, t = c.p.get("W", 0.8), c.p.get("T", 0.6)
	cu, cv = c.u - w / 2, c.v - t / 2
	rr = np.sqrt(cu**2 + cv**2)
	col = c.full(C(232, 178, 128))
	col = mix(col, C(196, 136, 92), (ss(0.6, 1.0, np.cos(rr * 2 * math.pi / 0.32)) * 0.25)[..., None])
	return col


def paint_frame(c):
	if str(c.p.get("Part", "")).startswith("door_"):
		# the door's surround reads darker than its leaf, as the reference's
		return paint_wood_face(c, base=C(132, 76, 54), width=c.p.get("Width", 0.7), edge=0.08)
	return paint_wood_face(c, base=C(176, 108, 74), width=c.p.get("Width", 0.4), edge=0.1)


def paint_frame_bar(c):
	return c.full(C(150, 92, 64))


def paint_sill(c):
	return paint_wood_face(c, base=C(206, 140, 94))


def paint_planks(c):
	if c.p.get("Upright"):
		return paint_wood_face(c, base=C(224, 158, 104), along_u=False)
	return paint_wood_face(c, base=C(206, 140, 94))


def paint_box(c):
	return paint_wood_face(c, base=C(188, 120, 82), plank=0.45)


def paint_gable_boards(c):
	"""the right gable's cladding: upright boards, dark and warm, each its own tone, darker joints"""
	col = c.full(C(132, 82, 60))
	board = 0.85
	k = np.floor(c.u / board)
	tone = hsh(k.astype(np.int64), seed=c.seed % 50 + 3) - 0.5
	col = col * (1 + 0.1 * tone)[..., None]
	col = mix(col, C(104, 62, 46), (ss(0.3, 0.8, grain(c.v, c.u, True, 2.2, 0.14, 133)) * 0.3)[..., None])
	seam = np.abs((c.u / board) % 1.0 - 0.5) * board
	col = mix(col, C(70, 42, 34), ((1 - ss(0.0, 0.05, board / 2 - seam)) * 0.8)[..., None])
	return col


def paint_door(c):
	"""the planked leaf: upright boards, soft grain, darker joints, lighter at the top where the light reaches into the arch"""
	col = c.full(C(206, 138, 94))
	board = 0.62
	k = np.floor(c.u / board)
	tone = hsh(k.astype(np.int64), seed=c.seed % 50) - 0.5
	col = col * (1 + 0.07 * tone)[..., None]
	gr = grain(c.v, c.u, True, 2.0, 0.12, c.seed % 31)
	col = mix(col, C(168, 104, 70), (ss(0.3, 0.8, gr) * 0.35)[..., None])
	seam = np.abs((c.u / board) % 1.0 - 0.5) * board
	col = mix(col, C(120, 74, 52), ((1 - ss(0.0, 0.045, board / 2 - seam)) * 0.75)[..., None])
	col = col * (0.92 + 0.08 * ss(0.0, 6.0, c.v))[..., None]
	return col


# the house kit's sage green (door and shutters), in the study's painted manner: boards in their own tones, darker joints
GREEN, GREEN_DARK, GREEN_LIGHT, GREEN_JOINT = C(118, 162, 128), C(76, 112, 90), C(164, 200, 156), C(52, 80, 66)


def paint_green_planks(c, board):
	col = c.full(GREEN)
	k = np.floor(c.u / board)
	tone = hsh(k.astype(np.int64), seed=c.seed % 50 + 11) - 0.5
	col = col * (1 + 0.08 * tone)[..., None]
	gr = grain(c.v, c.u, True, 2.0, 0.12, c.seed % 31 + 5)
	col = mix(col, GREEN_DARK, (ss(0.35, 0.85, gr) * 0.25)[..., None])
	seam = np.abs((c.u / board) % 1.0 - 0.5) * board
	col = mix(col, GREEN_JOINT, ((1 - ss(0.0, 0.05, board / 2 - seam)) * 0.7)[..., None])
	h = max(float(c.p.get("Ht", 3.0)), 1.0)
	col = mix(col, GREEN_LIGHT, (ss(0.3, 1.0, (c.v - float(np.min(c.v))) / h) * 0.16)[..., None])
	return col


def paint_door_green(c):
	return paint_green_planks(c, 0.7)


def paint_shutter(c):
	if c.p.get("Part") == "ledge":
		return paint_green_planks(c, 10.0) * 0.94
	return paint_green_planks(c, 0.42)


def paint_iron(c):
	col = c.full(C(62, 56, 64))
	return col * (1 + 0.08 * fbm(c.P, 0.3, 141, 2))[..., None]


def paint_lantern_glass(c):
	"""warm lamplight behind the panes, brightest in the middle"""
	t = soft_edge(c, 0.18)
	return mix(c.full(C(236, 170, 92)), C(255, 228, 158), t[..., None])


def paint_pot(c):
	col = c.full(C(196, 112, 82))
	col = col * (0.9 + 0.14 * ss(0.0, 1.4, c.v))[..., None]
	return col * (1 + 0.05 * fbm(c.P, 0.4, 143, 2))[..., None]


# ---------------------------------------------------------------------------------------------------------------- render, brick, stone
PLASTER = C(252, 240, 206)
PLASTER_COOL = C(222, 210, 214)
BRICK_TONES = [C(224, 136, 98), C(210, 122, 88), C(234, 150, 108), C(200, 112, 82), C(228, 142, 100)]
MORTAR = C(186, 112, 90)


BW, BH = 0.92, 0.38


def brick_cells(au, av):
	rowi = np.floor(av / BH)
	off = (rowi % 2) * BW * 0.5
	coli = np.floor((au + off) / BW)
	return rowi, coli, off


def brick_mask(c, au, av):
	"""coverage 0..1 from the reference's patches, decided per whole brick so the patch's edge steps along the courses"""
	cover = np.zeros(c.u.shape, dtype=np.float32)
	if not BRICKS:
		return cover
	rowi, coli, off = brick_cells(au, av)
	cu = (coli + 0.5) * BW - off
	cv = (rowi + 0.5) * BH
	P, N = c.P, c.N
	for (cx, cy, cz), hw, hh, n in BRICKS:
		n = np.array(n, dtype=np.float32)
		face = (N @ n) > 0.6
		if not face.any():
			continue
		d = P - np.array((cx, cy, cz), dtype=np.float32)
		if np.abs(d @ n).min() > 0.9:
			continue
		along = np.cross(n, np.array((0, 0, 1), dtype=np.float32))
		c_along = np.array((cx, cy, cz), dtype=np.float32) @ along
		du = (cu - c_along) / (hw * 0.72)
		dv = (cv - cz) / (hh * 0.72)
		rag = (hsh(rowi.astype(np.int64), coli.astype(np.int64), seed=31) - 0.5) * 0.5
		k = ((du * du + dv * dv) + rag < 1.0).astype(np.float32) * face * (np.abs(d @ n) < 0.9)
		cover = np.maximum(cover, k)
	return cover


def bricks_colour(c, au, av):
	rowi, coli, off = brick_cells(au, av)
	tone = hsh(rowi.astype(np.int64), coli.astype(np.int64), seed=9)
	col = np.zeros(au.shape + (3,), dtype=np.float32)
	idx = (tone * len(BRICK_TONES)).astype(np.int64) % len(BRICK_TONES)
	for i, t in enumerate(BRICK_TONES):
		col[idx == i] = t
	fu = (au + off) / BW - coli
	fv = av / BH - rowi
	joint = np.minimum(np.minimum(fu, 1 - fu) * BW, np.minimum(fv, 1 - fv) * BH)
	col = mix(col, MORTAR, (1 - ss(0.02, 0.05, joint))[..., None])
	col = col * (1 + 0.1 * (1 - ss(0.0, 0.12, (1 - fv) * BH)))[..., None]
	return col


def wall_coords(c):
	"""(along, up) in studs in the wall plane, for brick courses"""
	n = c.N.reshape(-1, 3).mean(0)
	n = n / (np.linalg.norm(n) + 1e-9)
	along = np.cross(n, np.array((0, 0, 1.0)))
	if np.linalg.norm(along) < 1e-3:
		along = np.array((1.0, 0, 0))
	along = along / np.linalg.norm(along)
	return c.P @ along.astype(np.float32), c.P[..., 2]


def paint_plaster(c, base=PLASTER, shade=0.0):
	col = c.full(base)
	# broad soft variation, a little cooler low down and in corners, warm where the sun sits
	lo = fbm(c.P, 5.0, 71, 2)
	col = mix(col, PLASTER_COOL, (ss(-0.1, 0.6, lo) * 0.18 + shade)[..., None])
	col = col * (1 + 0.025 * fbm(c.P, 0.8, 73, 2))[..., None]
	ground = 1 - ss(1.5, 4.5, c.P[..., 2])
	col = mix(col, C(200, 186, 176), (ground * 0.25)[..., None])
	au, av = wall_coords(c)
	cover = brick_mask(c, au, av)
	if cover.max() > 0.01:
		bc = bricks_colour(c, au, av)
		# the broken render's edge: a soft shadow on the plaster just around the bricks
		near = ndimage.gaussian_filter(cover, 0.12 * c.s2)
		col = col * (1 - 0.16 * np.clip(near * 2, 0, 1) * (1 - cover))[..., None]
		col = mix(col, bc, cover[..., None])
	return col


def paint_plaster_shade(c):
	return paint_plaster(c, shade=0.12)


def paint_reveal(c):
	return c.full(C(214, 196, 186))


def paint_brick(c):
	au, av = wall_coords(c)
	return bricks_colour(c, au, av) * 0.92


def paint_stone(c):
	"""the plinth: lilac-grey stones, each its own tone, lighter on top, a few pale ones"""
	r = hsh(c.seed, seed=4)
	base = mix(C(118, 104, 128), C(146, 132, 150), r)
	if hsh(c.seed, seed=8) > 0.86:
		base = C(214, 204, 196)
	col = c.full(base)
	face = c.p.get("Face", "")
	top = (c.N[..., 2] > 0.6)[..., None]
	col = np.where(top, col * 1.22, col)
	col = col * (1 + 0.05 * fbm(c.P, 0.6, 81, 2))[..., None]
	e = soft_edge(c, 0.12)
	col = mix(col * 1.1, col, e[..., None])
	return col


def paint_chimney(c):
	col = c.full(C(236, 224, 200))
	col = mix(col, C(214, 204, 196), (ss(-0.2, 0.6, fbm(c.P, 2.5, 91, 2)) * 0.2)[..., None])
	# bricks showing through, grouped in two patches the reference has
	au, av = wall_coords(c)
	z = c.P[..., 2]
	patch = np.zeros(z.shape, dtype=np.float32)
	zt = float(np.nanmax(z))
	for zc, hz, uc, hu in ((zt - 3.6, 0.55, 0.2, 0.9), (zt - 6.2, 0.35, -0.4, 0.5)):
		dist = np.sqrt(((av - zc) / hz) ** 2 + ((au - au.mean() - uc) / hu) ** 2)
		patch = np.maximum(patch, 1 - ss(0.7, 1.0, dist + fbm(c.P, 0.4, 93, 2) * 0.3))
	col = mix(col, bricks_colour(c, au, av), ss(0.45, 0.6, patch)[..., None])
	return col


def paint_chimney_cap(c):
	col = c.full(C(96, 86, 80))
	top = (c.N[..., 2] > 0.6)[..., None]
	col = np.where(top, C(122, 110, 102), col)
	return col * (1 + 0.05 * fbm(c.P, 0.5, 95, 2))[..., None]


def paint_glass(c):
	"""deep blue panes, lighter at the top with one soft diagonal sheen, different per window"""
	h = max(c.p.get("Ht", 2.0), 0.5)
	t = np.clip((c.v - float(np.min(c.v[c.mask]) if c.mask.any() else 0)) / h, 0, 1)
	if c.p.get("Round"):
		# the round window's glass is a green-teal in the reference, unlike the others
		col = mix(C(56, 118, 96), C(120, 182, 150), ss(0.1, 1.0, t)[..., None])
	else:
		col = mix(C(30, 52, 112), C(82, 118, 186), ss(0.1, 1.0, t)[..., None])
	r = hsh(c.seed, seed=12)
	sheen = np.exp(-(((c.u + c.v * 0.8) - (0.6 + 1.5 * r)) / 0.35) ** 2) * (0.25 + 0.3 * r)
	col = mix(col, C(170, 196, 230), sheen[..., None])
	return col



# ---------------------------------------------------------------------------------------------------------------- the garden
GRASS_SUN, GRASS_MID, GRASS_DEEP = C(206, 208, 108), C(176, 186, 88), C(118, 138, 62)


def paint_grass(c):
	"""the lawn: a sunny yellow-green in big soft patches, deeper green in hollows and toward us, short strokes standing up the view"""
	P = c.P
	big = fbm(P, 16.0, 101, 2)
	col = mix(c.full(GRASS_MID), GRASS_SUN, ss(-0.25, 0.45, big)[..., None])
	col = mix(col, GRASS_DEEP, (ss(0.15, 0.6, -fbm(P, 9.0, 103, 2)) * 0.55)[..., None])
	near = ss(-20.0, -45.0, P[..., 1])
	col = mix(col, GRASS_DEEP, (near * 0.45)[..., None])
	# strokes: short dabs stretched along the view's heading so they stand up on screen
	view = np.array((-0.64, 0.77), dtype=np.float32)
	a = P[..., 0] * view[0] + P[..., 1] * view[1]
	b = P[..., 0] * view[1] - P[..., 1] * view[0]
	st = grain(a, b, True, 0.9, 0.22, 107)
	col = col * (1 + 0.07 * st)[..., None]
	dots = hsh(np.floor(a / 0.7).astype(np.int64), np.floor(b / 0.35).astype(np.int64), seed=109)
	col = mix(col, C(228, 226, 140), ((dots > 0.985) * 0.5)[..., None])
	return col


def paint_flagstone(c):
	r = hsh(c.seed, seed=21)
	col = c.full(mix(C(178, 168, 182), C(204, 196, 200), r))
	if c.p.get("Face") == "side":
		col = col * 0.72
	else:
		col = col * (1 + 0.05 * fbm(c.P, 0.8, 111, 2))[..., None]
		col = mix(col * 0.82, col, soft_edge(c, 0.25)[..., None])
	return col


def paint_rock(c):
	col = c.full(C(140, 132, 152))
	up = np.clip(c.N[..., 2], 0, 1)
	col = col * (0.85 + 0.3 * up)[..., None]
	col = col * (1 + 0.06 * fbm(c.P, 0.9, 113, 2))[..., None]
	moss = ss(0.55, 0.85, up + 0.2 * fbm(c.P, 0.7, 115, 2))
	col = mix(col, C(150, 168, 70), (moss * 0.5)[..., None])
	return col


def paint_fence(c):
	return paint_wood_face(c, base=C(156, 116, 92), along_u=c.p.get("Part") != "board", width=c.p.get("Width"))


def paint_crate(c):
	return paint_wood_face(c, base=C(206, 142, 96), plank=0.5)


def paint_crate_trim(c):
	return paint_wood_face(c, base=C(170, 110, 76), width=c.p.get("Width", 0.34), edge=0.06)


def paint_barrel(c):
	"""staves: upright boards round the barrel, each its own tone, darker joints"""
	col = c.full(C(196, 128, 84))
	k = np.floor(c.u / 0.62)
	tone = hsh(k.astype(np.int64), seed=c.seed % 40) - 0.5
	col = col * (1 + 0.1 * tone)[..., None]
	seam = np.abs((c.u / 0.62) % 1.0 - 0.5) * 0.62
	col = mix(col, C(120, 76, 54), ((1 - ss(0.0, 0.04, 0.31 - seam)) * 0.7)[..., None])
	col = col * (1 + 0.05 * grain(c.v, c.u, True, 1.5, 0.08, 117))[..., None]
	return col


def paint_hoop(c):
	return c.full(C(92, 82, 86))


def paint_barrel_lid(c):
	return paint_wood_face(c, base=C(214, 156, 108), plank=0.55)


def paint_pumpkin(c):
	ribs = c.p.get("Ribs", 10)
	a = c.u / 6.0 * 2 * math.pi * ribs
	rib = (1 - np.cos(a)) / 2
	col = mix(c.full(C(238, 132, 42)), C(196, 92, 30), (rib * 0.45)[..., None])
	col = col * (0.9 + 0.15 * ss(0.0, 2.0, c.v))[..., None]
	return col


def paint_melon(c):
	ribs = c.p.get("Ribs", 8)
	a = c.u / 6.0 * 2 * math.pi * ribs
	stripe = ss(0.55, 0.8, np.cos(a))
	col = mix(c.full(C(66, 132, 62)), C(150, 200, 104), (stripe * 0.7)[..., None])
	return col


def paint_stem(c):
	return c.full(C(110, 120, 60))


def paint_bucket(c):
	return paint_barrel(c) * np.array((1.08, 1.1, 1.1), dtype=np.float32)


def paint_log(c):
	col = c.full(C(132, 92, 66))
	col = col * (1 + 0.12 * grain(c.u, c.v, True, 0.8, 0.1, 119))[..., None]
	return col


SKY_TOP, SKY_MID, SKY_LOW = C(98, 140, 198), C(128, 164, 214), C(178, 196, 226)
CLOUD, CLOUD_SHADE = C(236, 236, 246), C(196, 202, 228)


def paint_sky(c):
	"""the reference's sky: deep blue at the top paling toward the horizon, big soft clouds behind the chimney and to the right"""
	W, H = c.p.get("W", 400.0), c.p.get("H", 200.0)
	x, y = c.u / W, c.v / H
	col = mix(c.full(SKY_LOW), SKY_MID, ss(0.15, 0.55, y)[..., None])
	col = mix(col, SKY_TOP, ss(0.55, 1.0, y)[..., None])
	P = np.stack([c.u, c.v, np.zeros_like(c.u)], -1)
	cl = np.zeros(c.u.shape, dtype=np.float32)
	for cx, cy, rx, ry in ((0.52, 0.62, 0.17, 0.12), (0.66, 0.74, 0.12, 0.09), (0.78, 0.55, 0.14, 0.1), (0.3, 0.5, 0.12, 0.05), (0.92, 0.66, 0.1, 0.12)):
		d = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
		cl = np.maximum(cl, 1 - ss(0.45, 1.05, d + 0.35 * fbm(P, 22.0, 131, 3)))
	shade = ss(0.0, 1.0, (fbm(P, 30.0, 133, 2) + 0.3))
	cc = mix(CLOUD, CLOUD_SHADE, (shade * 0.6)[..., None])
	return mix(col, cc, (cl * 0.88)[..., None])


PAINTERS = {
	"gable_boards": paint_gable_boards,
	"sky": paint_sky,
	"grass": paint_grass,
	"flagstone": paint_flagstone,
	"rock": paint_rock,
	"fence": paint_fence,
	"fence_end": paint_end,
	"crate": paint_crate,
	"crate_trim": paint_crate_trim,
	"crate_trim_end": paint_end,
	"barrel": paint_barrel,
	"hoop": paint_hoop,
	"barrel_lid": paint_barrel_lid,
	"pumpkin": paint_pumpkin,
	"melon": paint_melon,
	"stem": paint_stem,
	"stem_end": paint_stem,
	"bucket": paint_bucket,
	"log": paint_log,
	"log_end": paint_end,
	"tile": paint_tile,
	"tile_lip": paint_tile_lip,
	"roof_under": paint_roof_under,
	"soffit": paint_soffit,
	"timber": paint_timber,
	"timber_end": paint_end,
	"barge": paint_barge,
	"barge_end": paint_end,
	"frame": paint_frame,
	"frame_end": paint_end,
	"frame_bar": paint_frame_bar,
	"frame_bar_end": paint_frame_bar,
	"sill": paint_sill,
	"planks": paint_planks,
	"planks_end": paint_end,
	"box": paint_box,
	"door": paint_door,
	"plaster": paint_plaster,
	"plaster_shade": paint_plaster_shade,
	"reveal": paint_reveal,
	"brick": paint_brick,
	"stone": paint_stone,
	"chimney": paint_chimney,
	"chimney_cap": paint_chimney_cap,
	"glass": paint_glass,
	"door_green": paint_door_green,
	"shutter": paint_shutter,
	"iron": paint_iron,
	"iron_end": paint_iron,
	"lantern_glass": paint_lantern_glass,
	"pot": paint_pot,
}

AO_TINT = C(0.62, 0.54, 0.66)
AO_TINTS = {"Ground": C(0.52, 0.62, 0.42)}
AO_STRENGTH = {"Ground": 0.7, "Props": 0.6, "Walls": 0.85, "Timber": 0.6, "Joinery": 0.7, "Stone": 0.6, "RoofRB": 0.55, "RoofLB": 0.55, "RoofAX": 0.55, "RoofMain": 0.55, "RoofWing": 0.55}


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--only", default="")
	ap.add_argument("--no-ao", action="store_true")
	args = ap.parse_args()
	only = set(args.only.split(",")) if args.only else None
	sheets = {}
	for key, info in layout["Islands"].items():
		sheets.setdefault(info["Sheet"], []).append((key, info))
	os.makedirs(os.path.join(OUT, "sheets"), exist_ok=True)
	missing = set()
	for sheet, items in sorted(sheets.items()):
		if only and sheet not in only:
			continue
		t0 = time.time()
		big = SIZE * SS
		canvas = np.zeros((big, big, 3), dtype=np.float32)
		filled = np.zeros((big, big), dtype=bool)
		for key, info in items:
			c = Ctx(key, info)
			if not c.mask.any():
				continue
			fn = PAINTERS.get(c.kind)
			if fn is None:
				missing.add(c.kind)
			col = fn(c) if fn else c.full(C(255, 0, 255))
			x0, y0 = info["PX"] * SS, info["PY"] * SS
			h, w = min(c.h, big - y0), min(c.w, big - x0)
			m = c.mask[:h, :w]
			canvas[y0 : y0 + h, x0 : x0 + w][m] = np.clip(col[:h, :w][m], 0, 255)
			filled[y0 : y0 + h, x0 : x0 + w] |= m
		ao_path = os.path.join(OUT, "sheets", "ao", f"{sheet}.png")
		if os.path.exists(ao_path) and not args.no_ao:
			ao = np.asarray(Image.open(ao_path).convert("L").resize((big, big), Image.BILINEAR), dtype=np.float32) / 255
			ao = ndimage.gaussian_filter(ao, 1.2)
			k = AO_STRENGTH.get(sheet, 0.65)
			dark = np.clip(1 - ao, 0, 1) ** 1.15 * k
			canvas = canvas + (canvas * AO_TINTS.get(sheet, AO_TINT) - canvas) * dark[..., None] * filled[..., None]
		_, (iy, ix) = ndimage.distance_transform_edt(~filled, return_indices=True)
		canvas = canvas[iy, ix]
		Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS).save(os.path.join(OUT, "sheets", f"{sheet}.png"))
		print(f"[paint] {sheet}: {len(items)} islands, {time.time() - t0:.1f}s", flush=True)
	if missing:
		print("[paint] no painter for", sorted(missing))


if __name__ == "__main__":
	main()
