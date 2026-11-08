"""Paints the pink cottage study's sheets (tools/blender/pink_cottage.py; private, research/pink_cottage).

  python tools/art/paint_pink_cottage.py [--only RoofA,Tower] [--kinds slate,ashlar_round]

Every island is painted from its own pattern coordinates (u, v in studs), world position and normal per texel, by its kind:
fish-scale slates tile by tile with the next row's shadow and grouped lichen, coursed pink ashlar block by block, cream stone,
plaster, planks, the door's roundels, glass, grass with clover. Flat tones in big groups, soft painted edges, a faint brush grain;
light and shade only where something casts them (the next slate row, the eaves, the ground). Painted at 2x, shrunk with Lanczos.
"""

import argparse
import json
import math
import os
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.interpolate import griddata

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "research", "pink_cottage")
SS = 2

layout = json.load(open(os.path.join(OUT, "layout.json")))
_K = layout.get("Consts", {})
EAVE, WALL_TOP, LANE = _K.get("EAVE", 12.4), _K.get("WALL_TOP", 13.4), _K.get("LANE", -13.8)
T_WALL, RING_TOP = _K.get("T_WALL", 37.9), _K.get("RING_TOP", 38.75)
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
	"""integer hash of integer arrays -> [0, 1)"""
	h = np.int64(seed * 2654435761 % 2147483647 + 1013904223)
	for i, v in enumerate(vals):
		v = np.asarray(v).astype(np.int64)
		h = h ^ ((v + 0x9E3779B9 + (h << 6) + (h >> 2)) * (2 * i + 1) * 73856093)
		h = (h * 2246822519) & 0xFFFFFFFF
	h = (h ^ (h >> 15)) * 2654435761 & 0xFFFFFFFF
	return ((h ^ (h >> 13)) & 0xFFFFFF).astype(np.float32) / float(0x1000000)


_LATTICE = np.random.default_rng(7).random((64, 64, 64)).astype(np.float32)


def vnoise(P, scale, seed=0):
	"""smooth value noise in world space, about `scale` studs across, -1..1"""
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
	"""a faint brush grain: noise stretched along one direction (u or v)"""
	a, b = (u, v) if along_u else (v, u)
	P = np.stack([a / scale_along, b / scale_across, np.zeros_like(a)], -1)
	return vnoise(P, 1.0, seed)


def name_seed(s):
	return sum((i + 1) * 131 * ord(ch) for i, ch in enumerate(str(s))) % 100000


# ---------------------------------------------------------------------------------------------------------------- one island
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
		self.P = self.interp(pts, Pv, xx, yy, len(uv))
		self.N = self.interp(pts, Nv, xx, yy, len(uv))
		n = np.linalg.norm(self.N, axis=-1, keepdims=True)
		self.N = self.N / np.maximum(n, 1e-6)
		self.seed = name_seed(f"{self.p.get('Roof', '')}{self.p.get('Row', '')}{self.key}")
		self.rng = np.random.default_rng(self.seed)

	def interp(self, pts, vals, xx, yy, ntri):
		"""positions/normals per texel: an affine fit where the island is flat, linear interpolation over its corners otherwise"""
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

	def edge_dist(self):
		"""distance in studs from each texel to the island's border"""
		return ndimage.distance_transform_edt(np.pad(self.mask, 1))[1:-1, 1:-1].astype(np.float32) / self.s2


# ---------------------------------------------------------------------------------------------------------------- slate
# measured on the reference's roof (warm, a little mauve) and its lichen (a pale olive wash, not a bright yellow)
SLATE = [C(178, 168, 167), C(170, 161, 161), C(186, 176, 174), C(163, 155, 157), C(192, 182, 178), C(174, 165, 164), C(156, 149, 153)]
LICHEN_MID, LICHEN_DARK, LICHEN_LIGHT, LICHEN_OCHRE = C(182, 180, 116), C(150, 156, 96), C(204, 204, 136), C(204, 186, 110)


def lichen_level(P):
	"""where lichen grows, as in the reference: the lower slopes from the dormer rightward, the box dormer's roof and the right half of
	the annex's lean-to; the upper slopes, the cone and the left end stay mostly clean"""
	x, z = P[..., 0], P[..., 2]
	low = 1 - ss(EAVE + 1.5, EAVE + 8.0, z)
	right_of_dormer = ss(3.0, 9.0, x)
	dormer = np.exp(-(((x - 12.5) / 5.0) ** 2 + ((z - 18.0) / 3.5) ** 2))
	box_roof = np.exp(-(((x - 24.0) / 4.0) ** 2 + ((z - 28.0) / 2.0) ** 2))
	annex = ss(2.0, 6.0, x) * ((z < 4.0) & (z > -3.0))
	bias = 0.58 * low * (0.3 + 0.7 * right_of_dormer) + 0.25 * dormer + 0.36 * box_roof + 0.5 * annex
	return bias + 0.26 * fbm(P, 4.0, 31) + 0.08 * vnoise(P, 1.5, 33)


def paint_slate(c):
	"""each slate a pale rounded plate: lighter at its round foot, a soft shadow under the next row's edge; lichen as a dab on the slate"""
	p = c.p
	T, off, S0, RH, Dp = p["Tile"], p["Offset"], p["S0"], p["RowH"], p["Depth"]
	u, v = c.u, c.v
	q = (u - off) / T
	k = np.floor(q)
	tx = q - k - 0.5
	edge = S0 + Dp * (1 - np.sqrt(np.clip(1 - (2 * tx) ** 2, 0, 1)))
	h = v - edge
	q2 = (u - off - T / 2) / T
	k2 = np.floor(q2)
	tx2 = q2 - k2 - 0.5
	edge_up = S0 + RH + Dp * (1 - np.sqrt(np.clip(1 - (2 * tx2) ** 2, 0, 1)))
	hb = edge_up - v
	roof = name_seed(p.get("Roof", "r"))
	ki = k.astype(np.int64)
	row = np.full_like(ki, int(p.get("Row", 0)))
	tid = hsh(ki, row, seed=roof)
	pal = np.stack(SLATE)
	col = pal[np.minimum((tid * len(SLATE)).astype(np.int64), len(SLATE) - 1)]
	z = c.P[..., 2]
	col = col * (1 + 0.03 * ss(EAVE, EAVE + 14, z) + 0.025 * fbm(c.P, 9.0, roof))[..., None]
	# lichen first, as a grouped wash over whole areas (the reference), mottled within and taken a little differently by each slate
	lev = lichen_level(c.P)
	cover = ss(0.26, 0.52, lev)
	mott = 0.5 + 0.5 * fbm(c.P, 0.9, 37)
	amt = np.clip(cover * (0.62 + 0.6 * mott) * (0.8 + 0.4 * hsh(ki, row, seed=roof + 9)), 0, 1)
	lich = mix(LICHEN_DARK, LICHEN_MID, ss(0.25, 0.6, mott)[..., None])
	lich = mix(lich, LICHEN_LIGHT, (ss(0.6, 0.9, mott) * 0.7)[..., None])
	lich = mix(lich, LICHEN_OCHRE, (ss(0.72, 0.95, lev) * 0.35)[..., None])
	col = mix(col, lich, (amt * 0.85)[..., None])
	# the plate: a soft lighter dome toward its round foot
	vis = np.clip((v - edge) / np.maximum(edge_up - edge, 0.2), 0, 1)
	dome = np.exp(-((tx / 0.4) ** 2 + ((vis - 0.34) / 0.46) ** 2))
	col = col * (1 + 0.12 * dome - 0.06 + 0.07 * (hsh(ki, row, seed=roof + 31) - 0.5))[..., None]
	side = np.abs(tx) * 2
	col = col * (1 - 0.05 * ss(0.7, 1.0, side))[..., None]
	# a pale rim where the round foot catches the light (the reference's chunky disc edges)
	rim = (1 - ss(0.0, 0.1, h)) * ss(0.0, 0.03, h)
	col = mix(col, col * 1.12, (rim * 0.8)[..., None])
	# the next row's edge throws a soft, light shadow; no hard line
	shadow = 1 - ss(0.0, 0.34, hb)
	col = mix(col, col * C(0.76, 0.74, 0.84), (shadow * 0.8)[..., None])
	col = mix(col, col * C(0.7, 0.68, 0.76), ((1 - ss(0.0, 0.06, hb)) * 0.45)[..., None])
	col = col * (1 + 0.02 * grain(u, v, True, 0.5, 0.05, roof + 7))[..., None]
	return col


def paint_slate_lip(c):
	"""the slates' thick round edges: a shade under the slate's own colour, lichen-tinted where the roof is grown over"""
	base = C(150, 142, 147) * (0.95 + 0.1 * hsh(np.floor(c.u / 1.3).astype(np.int64), seed=c.seed))[..., None]
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	base = base * (0.86 + 0.18 * vv)[..., None]
	lev = lichen_level(c.P)
	base = mix(base, LICHEN_DARK * 0.9, (ss(0.35, 0.65, lev) * 0.5)[..., None])
	return base


def paint_fascia(c):
	"""the eave's thickness: the slate stack's edge, slate-coloured, darker at its underside"""
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	col = mix(C(118, 112, 120), C(160, 153, 154), ss(0.1, 0.7, vv)[..., None])
	k = np.floor(c.u / 1.8).astype(np.int64)
	return col * (0.96 + 0.08 * hsh(k, seed=c.seed))[..., None]


def paint_slate_cap(c):
	"""rolled hip and ridge tiles, tile by tile (the geometry's own tile length): lighter at each tile's flared foot, shaded where the
	next tile laps over it"""
	u = c.u
	T = c.p.get("Tile", 1.0)
	q = u / T
	k = np.floor(q)
	f = q - k
	tid = hsh(k.astype(np.int64), seed=c.seed)
	pal = np.stack(SLATE)
	col = pal[np.minimum((tid * len(SLATE)).astype(np.int64), len(SLATE) - 1)] * 1.0
	col = col * (1 + 0.1 * (1 - ss(0.0, 0.25, f)))[..., None]
	col = mix(col, col * C(0.78, 0.76, 0.84), (ss(0.75, 1.0, f) * 0.7)[..., None])
	lev = lichen_level(c.P)
	col = mix(col, LICHEN_MID, (ss(0.45, 0.7, lev) * (0.4 + 0.3 * fbm(c.P, 0.8, 38)))[..., None])
	return col


def paint_slate_under(c):
	"""what shows between the eave slates' rounded tips: slate, a shade darker"""
	return (C(134, 128, 134) * (1 + 0.04 * vnoise(c.P, 0.7, 3))[..., None]).astype(np.float32)


# ---------------------------------------------------------------------------------------------------------------- coursed stone
PINK = [C(236, 178, 160), C(228, 164, 146), C(244, 196, 178), C(216, 146, 130), C(250, 212, 196), C(226, 170, 158), C(200, 134, 120)]
PINK_W = np.array([0.22, 0.2, 0.16, 0.13, 0.1, 0.12, 0.07])
BRICK = [C(240, 190, 172), C(230, 174, 156), C(246, 202, 184), C(224, 166, 148)]
RETAIN = [C(238, 210, 186), C(228, 196, 170), C(242, 218, 196), C(222, 188, 164)]
CREAM = C(246, 222, 192)


def coursed(c, course, lengths, palette, weights, mortar_col, mortar=0.08, seed=0, bevel=1.0, vary=1.0, bond=0.5):
	"""blocks laid in courses with running bond, lengths from a short list, mortar between. course: one height, or a list of heights
	that the courses pick from (seeded), for hand-cut stone whose courses differ"""
	u, v = c.u, c.v
	if np.ndim(course) == 0:
		cidx = np.floor(v / course).astype(np.int64)
		fv = v / course - cidx
	else:
		rng = np.random.default_rng(seed * 31 + 7)
		v_lo, v_hi = float(v.min()) - 4.0, float(v.max()) + 4.0
		start = min(-20.0, math.floor(v_lo) - 1.0)  # a fixed origin, so islands that meet (the tower's bands) share their courses
		bounds = [start]
		while bounds[-1] < v_hi:
			bounds.append(bounds[-1] + course[rng.integers(len(course))])
		bounds = np.array(bounds)
		ci = np.clip(np.searchsorted(bounds, v, side="right") - 1, 0, len(bounds) - 2)
		h_c = (bounds[ci + 1] - bounds[ci]).astype(np.float32)
		fv = ((v - bounds[ci]) / h_c).astype(np.float32)
		cidx = ci.astype(np.int64) + int(round(start * 10))
		course = h_c
	out = np.zeros(u.shape + (3,), dtype=np.float32)
	fu_all = np.zeros(u.shape, dtype=np.float32)
	blen_all = np.ones(u.shape, dtype=np.float32)
	bid_all = np.zeros(u.shape, dtype=np.int64)
	u_lo, u_hi = float(u.min()) - 8, float(u.max()) + 8
	for ci in np.unique(cidx[c.mask]):
		rng = np.random.default_rng((seed * 7919 + int(ci) * 104729) % (2**32))
		start = u_lo - (bond * (ci % 2) + rng.random() * 0.4) * np.mean(lengths)
		edges = [start]
		while edges[-1] < u_hi:
			edges.append(edges[-1] + lengths[rng.integers(len(lengths))] * (0.94 + 0.12 * rng.random()))
		edges = np.array(edges)
		m = (cidx == ci) & c.mask
		b = np.searchsorted(edges, u[m]) - 1
		b = np.clip(b, 0, len(edges) - 2)
		L = edges[b + 1] - edges[b]
		fu_all[m] = (u[m] - edges[b]) / L
		blen_all[m] = L
		bid_all[m] = b + int(ci) * 1000
	pick = hsh(bid_all, seed=seed)
	cum = np.cumsum(weights / weights.sum())
	idx = np.searchsorted(cum, pick)
	pal = np.stack(palette)
	col = pal[np.minimum(idx, len(palette) - 1)]
	col = col * (1 + vary * 0.05 * (hsh(bid_all, seed=seed + 3) - 0.5))[..., None]
	# inside a block: a soft lighter middle, a lit top edge, a darker foot and right edge (light from the upper left)
	gu = np.minimum(fu_all * blen_all, (1 - fu_all) * blen_all)
	gv_top = (1 - fv) * course
	gv_bot = fv * course
	col = col * (1 + bevel * (0.06 * (1 - ss(0.0, 0.13, gv_top)) - 0.09 * (1 - ss(0.0, 0.12, gv_bot)) - 0.05 * (1 - ss(0.0, 0.1, (1 - fu_all) * blen_all)) + 0.03 * (1 - ss(0.0, 0.1, fu_all * blen_all))))[..., None]
	blot = vnoise(np.stack([c.u / 0.9, c.v / 0.6, bid_all.astype(np.float32) * 0.37], -1), 1.0, seed + 5)
	col = col * (1 + 0.035 * blot)[..., None]
	# mortar: soft-edged painted joints, slightly uneven in width
	wob = 0.02 * vnoise(c.P, 0.4, seed + 8)
	gv = np.minimum(gv_top, gv_bot)
	rc = 0.16
	jd = rc - np.sqrt(np.maximum(rc - gu, 0) ** 2 + np.maximum(rc - gv, 0) ** 2)
	jd = np.where((gu > rc) | (gv > rc), np.minimum(gu, gv), jd) + wob
	mo = (1 - ss(mortar * 0.35, mortar * 0.75, jd)) * (0.8 - 0.25 * ss(4.0, 30.0, c.P[..., 2]))
	mcol = mortar_col * (1 + 0.04 * vnoise(c.P, 0.7, seed + 9))[..., None]
	col = mix(col, mcol, mo[..., None])
	return col, bid_all


def wall_light(c, col, ground=0.0, top=None, top_band=1.4):
	"""painted light with causes: darker near the ground it stands in, a soft band under the eaves above it"""
	z = c.P[..., 2]
	col = col * (1 - 0.14 * (1 - ss(ground, ground + 2.6, z)))[..., None]
	if top is not None:
		band = ss(top - top_band, top, z) * (1 - ss(top + 0.2, top + 0.5, z))
		col = mix(col, col * C(0.74, 0.7, 0.78), (band * 0.55)[..., None])
	return col


def paint_ashlar(c):
	col, _ = coursed(c, [0.95, 1.15, 1.35, 1.05], [1.8, 2.8, 3.6, 2.3, 4.2], PINK, PINK_W, C(242, 212, 200), mortar=0.075, seed=11, bevel=0.5, vary=1.2)
	col = col * (1 + 0.04 * fbm(c.P, 8.0, 12))[..., None]
	col = wall_light(c, col, ground=0.0, top=WALL_TOP, top_band=1.6)
	col = col * C(1.02, 0.985, 0.94)  # the reference's front is a warmer, more orange pink than the tower
	if c.kind == "ashlar_in":
		col = col * C(0.93, 0.9, 0.92)
	return col


def paint_ashlar_reveal(c):
	col, _ = coursed(c, 1.05, [0.7, 0.9], PINK, PINK_W, C(232, 196, 178), seed=13)
	return col * C(0.9, 0.86, 0.9)


def paint_ashlar_round(c):
	"""the tower's hand-cut sandstone: courses of different heights, long and short blocks, close rose tones, pale soft joints (the
	reference reads as stone, not brick)"""
	col, _ = coursed(c, [1.05, 1.3, 1.55, 1.2, 1.75], [2.2, 3.4, 4.4, 2.8, 1.8, 5.0, 3.0], PINK, PINK_W, C(244, 214, 202), mortar=0.075, seed=17, vary=1.2, bevel=0.45)
	z = c.P[..., 2]
	# the tower deepens toward its foot, warmer and richer (the reference's lower tower), and lifts toward the top
	col = mix(col, col * C(0.88, 0.8, 0.78), ((1 - ss(2.0, 22.0, z)) * 0.55)[..., None])
	col = col * (1 + 0.06 * ss(20.0, 39.0, z) + 0.035 * fbm(c.P, 7.0, 18))[..., None]
	col = mix(col, col * C(0.8, 0.76, 0.82), (ss(T_WALL - 1.0, T_WALL, z) * 0.45)[..., None])
	return col


def paint_brick(c):
	col, _ = coursed(c, 0.46, [0.95, 1.05], BRICK, np.array([0.3, 0.25, 0.25, 0.2]), C(236, 204, 190), mortar=0.07, seed=21, bevel=0.7)
	return col * (1 + 0.03 * fbm(c.P, 4.0, 22))[..., None]


def paint_retaining(c):
	col, _ = coursed(c, 1.45, [2.2, 2.9, 3.6], RETAIN, np.array([0.3, 0.3, 0.25, 0.15]), C(226, 202, 180), mortar=0.12, seed=25, bevel=0.6, vary=0.6)
	z = c.P[..., 2]
	col = col * (1 - 0.16 * (1 - ss(LANE, LANE + 2.0, z)))[..., None]
	col = mix(col, col * C(0.8, 0.82, 0.78), (ss(-0.9, 0.0, z) * 0.35)[..., None])  # under the curb's lip
	return col


def paint_voussoir(c):
	stone = c.p.get("Stone", 0)
	base = C(176, 100, 84) * (0.94 + 0.12 * hsh(np.array(stone), seed=3))
	col = np.broadcast_to(base, c.u.shape + (3,)).astype(np.float32).copy()
	ed = c.edge_dist()
	col = col * (1 + 0.1 * (1 - ss(0.0, 0.18, ed)) * (c.p.get("Face") == "front"))[..., None]
	col = col * (1 + 0.05 * fbm(c.P, 1.5, 4 + stone))[..., None]
	return col


def paint_crown(c):
	"""the crown's merlons (reference): pale pink stone carrying two nested brick chevrons, pointing up, in the band the eave leaves
	visible; their sides are the openings' shaded reveals"""
	face = c.p.get("Face")
	z0 = c.p.get("Z0", RING_TOP)
	base = C(232, 186, 166)
	col = np.broadcast_to(base, c.u.shape + (3,)).astype(np.float32).copy()
	col = col * (1 + 0.04 * fbm(c.P, 1.2, 51))[..., None]
	if face == "outer":
		W = c.p.get("Width", 2.2)
		x = np.abs(c.u - W / 2) / (W / 2)  # 0 in the merlon's middle, 1 at its sides
		y = c.v - z0
		for k, (a, wdt) in enumerate(((0.35, 0.22), (0.85, 0.22))):
			line = a + 0.75 * (1 - x)
			band = np.abs(y - line) < wdt / 2
			col = np.where((band & (x < 0.92))[..., None], C(178, 98, 84) * (0.95 + 0.1 * k), col)
		col = col * (1 - 0.12 * (1 - ss(0.0, 0.25, y)))[..., None]
	elif face == "side":
		col = col * C(0.72, 0.66, 0.7)
	else:
		col = col * C(0.4, 0.3, 0.32)
	return col


def paint_corbel(c):
	"""the small corbels under the tower's ring: cream stone, shaded below, so the row reads as a dotted shadow (reference)"""
	col = paint_cream(c, base=C(222, 196, 176), bottom_dark=0.3)
	if c.p.get("Face") == "-z":
		col = col * C(0.62, 0.56, 0.6)
	return col


def paint_green_light(c):
	return paint_wood(c, C(128, 188, 134), board=0.5, gap=0.0, knots=False, vary=0.05)


# ---------------------------------------------------------------------------------------------------------------- cream stone, plaster
def paint_cream(c, base=None, bottom_dark=0.1):
	base = CREAM if base is None else base
	col = np.broadcast_to(base, c.u.shape + (3,)).astype(np.float32).copy()
	col = col * (1 + 0.035 * fbm(c.P, 2.5, c.seed % 97) + 0.02 * vnoise(c.P, 0.5, 3))[..., None]
	up = c.N[..., 2]
	side = np.abs(up) < 0.5
	if side.any():
		vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
		col = np.where(side[..., None], col * (1 - bottom_dark * (1 - ss(0.0, 0.55, vv)))[..., None], col)
	col = np.where((up > 0.6)[..., None], col * 1.03, col)
	ed = c.edge_dist()
	col = col * (1 - 0.07 * (1 - ss(0.0, 0.07, ed)))[..., None]
	# a few small chips, placed sparsely
	chips = (vnoise(c.P, 0.35, c.seed % 89) > 0.72) & (fbm(c.P, 3.0, 7) > 0.2)
	col = np.where(chips[..., None], col * C(0.88, 0.86, 0.86), col)
	return col


def paint_curb(c):
	b = c.p.get("Block", 0)
	base = CREAM * (0.96 + 0.07 * hsh(np.array(b), seed=8))
	return paint_cream(c, base=base, bottom_dark=0.14)


def paint_step(c):
	up = c.N[..., 2]
	if np.median(up[c.mask]) > 0.5 if c.mask.any() else False:
		return paint_cream(c, base=C(240, 222, 198))
	col, _ = coursed(c, 0.32, [0.7, 0.85], [C(214, 134, 112), C(200, 120, 100), C(222, 146, 124)], np.array([0.4, 0.3, 0.3]), C(236, 200, 180), mortar=0.06, seed=31, bevel=0.6)
	return col


def paint_step_pink(c):
	col = paint_cream(c, base=C(206, 128, 108), bottom_dark=0.12)
	return col


def paint_plaster(c, base=C(242, 224, 198), shadow_tint=C(0.8, 0.78, 0.84)):
	z = c.P[..., 2]
	col = np.broadcast_to(base, c.u.shape + (3,)).astype(np.float32).copy()
	col = col * (1 + 0.03 * fbm(c.P, 4.0, 61) + 0.015 * grain(c.u, c.v, False, 0.9, 0.12, 62))[..., None]
	stain = ss(0.15, 0.45, fbm(c.P, 3.0, 63) + 0.5 * (1 - ss(LANE, LANE + 3.0, z)))
	col = mix(col, col * C(0.9, 0.87, 0.82), (stain * 0.6)[..., None])
	col = col * (1 - 0.12 * (1 - ss(LANE, LANE + 1.8, z)))[..., None]
	# under the ledge and the awning: cast, soft
	if c.kind == "plaster":
		under_awning = ss(3.9 - 3.4, 3.9 - 1.6, z) * (1 - ss(3.3, 3.9, z)) * ss(0.4, 1.6, c.P[..., 0]) * (1 - ss(10.8, 12.2, c.P[..., 0]))
		col = mix(col, col * shadow_tint, (under_awning * 0.5)[..., None])
	return col


def paint_plaster_pink(c):
	col = paint_plaster(c, base=C(224, 152, 128))
	z = c.P[..., 2]
	col = mix(col, col * C(0.74, 0.7, 0.78), (ss(WALL_TOP - 1.8, WALL_TOP, z) * 0.6)[..., None])
	return col


def paint_plaster_reveal(c):
	return paint_plaster(c) * C(0.86, 0.84, 0.88)


# ---------------------------------------------------------------------------------------------------------------- wood
def paint_wood(c, base, board=0.6, along=None, gap=0.05, gap_col=None, knots=True, vary=0.08):
	u, v = c.u, c.v
	du, dv = c.info["U1"] - c.info["U0"], c.info["V1"] - c.info["V0"]
	if along is None:
		along = "u" if du >= dv else "v"
	a, b = (u, v) if along == "u" else (v, u)
	bi = np.floor(b / board).astype(np.int64)
	fb = b / board - bi
	tone = 1 + vary * (hsh(bi, seed=c.seed) - 0.5)
	col = base * tone[..., None]
	streak = grain(a, b, True, 1.6, 0.05, c.seed + 1)
	col = col * (1 + 0.07 * streak + 0.03 * grain(a, b, True, 0.4, 0.02, c.seed + 2))[..., None]
	col = col * (1 - 0.1 * (1 - ss(0.0, 0.12, fb)) + 0.05 * (1 - ss(0.0, 0.1, 1 - fb)))[..., None]
	gap_col = base * 0.5 if gap_col is None else gap_col
	col = np.where((fb < gap / board)[..., None], gap_col, col)
	if knots:
		kn = (vnoise(np.stack([a / 0.35, b / 0.12, np.zeros_like(a)], -1), 1.0, c.seed + 4) > 0.86)
		col = np.where(kn[..., None], col * 0.82, col)
	# houses: wood darker and richer toward the top (the standard's exception)
	z = c.P[..., 2]
	col = col * (1 - 0.08 * ss(4.0, 20.0, z))[..., None]
	return col


def paint_planks(c):
	if c.p.get("Upright"):  # the box dormer's dark timber fascia, upright boards
		return paint_wood(c, C(96, 62, 50), board=0.32, along="v", gap=0.04, knots=False)
	return paint_wood(c, C(164, 112, 84), board=0.65, along="v")


def paint_wood_plain(c):
	return paint_wood(c, C(104, 66, 48), board=0.9, gap=0.0)


def paint_shutter(c):
	return paint_wood(c, C(112, 72, 54), board=0.5, along="v")


def paint_wood_lid(c):
	return paint_wood(c, C(138, 140, 120), board=0.55, along="u")


def paint_window_box(c):
	return paint_wood(c, C(240, 184, 126), board=0.5, along="u", gap=0.04, knots=False, vary=0.04)


def paint_green(c):
	return paint_wood(c, C(66, 128, 72), board=0.5, gap=0.0, knots=False, vary=0.05)


def paint_shutter_green(c):
	col = paint_wood(c, C(62, 122, 68), board=0.5, along="v", knots=False, vary=0.05)
	cu = (c.info["U0"] + c.info["U1"]) / 2
	x = (c.u - cu) / 0.42
	y = (c.v - (c.info["V1"] - 1.1)) / 0.42
	heart = (x * x + (y - 0.55 * np.sqrt(np.abs(x))) ** 2) < 1.0
	if c.p.get("Face") in ("-y",):
		col = np.where(heart[..., None], C(36, 46, 30), col)
	return col


def paint_door(c):
	col = paint_wood(c, C(98, 54, 40), board=0.55, along="v", vary=0.06)
	if c.p.get("Face") != "-y":
		return col
	cu = (c.info["U0"] + c.info["U1"]) / 2
	cv = c.info["V0"] + (c.info["V1"] - c.info["V0"]) * 0.56
	r = np.hypot(c.u - cu, (c.v - cv) / 1.55)  # tall ovals, muted, as on the reference's door
	ring = [(0.95, C(214, 190, 156)), (0.78, C(80, 46, 36)), (0.56, C(206, 182, 148)), (0.34, C(84, 118, 110)), (0.16, C(62, 84, 80))]
	for rad, rc in ring:
		col = mix(col, rc * (1 + 0.04 * vnoise(c.P, 0.3, 5))[..., None], ss(rad + 0.03, rad - 0.03, r)[..., None])
	# panel frame: a raised border
	ed = np.minimum.reduce([c.u - c.info["U0"], c.info["U1"] - c.u, c.v - c.info["V0"], c.info["V1"] - c.v])
	col = np.where((ed < 0.32)[..., None], col * 0.84, col)
	return col


def paint_glass(c):
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	col = mix(C(46, 58, 92), C(132, 186, 232), ss(0.25, 1.0, vv)[..., None])
	streak = ((c.u * 0.7 + c.v) % 3.2) < 0.45
	col = np.where(streak[..., None], mix(col, C(220, 238, 250), 0.35), col)
	cloud = ss(0.35, 0.6, fbm(c.P * C(1, 1, 2.2), 2.2, 71)) * ss(0.45, 0.85, vv)
	col = mix(col, C(236, 244, 250), (cloud * 0.55)[..., None])
	return col


def paint_interior(c):
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	return mix(C(56, 36, 32), C(30, 20, 20), ss(0.0, 0.8, vv)[..., None])


# ---------------------------------------------------------------------------------------------------------------- ground
def clumps(P2, cell, prob, radius, seed):
	"""scattered round clumps in world x/y: distance to the nearest clump centre (studs), and its id"""
	g = np.floor(P2 / cell).astype(np.int64)
	best = np.full(P2.shape[:-1], 1e9, dtype=np.float32)
	bid = np.zeros(P2.shape[:-1], dtype=np.int64)
	for dx in (-1, 0, 1):
		for dy in (-1, 0, 1):
			gx, gy = g[..., 0] + dx, g[..., 1] + dy
			on = hsh(gx, gy, seed=seed) < prob
			cx = (gx + 0.2 + 0.6 * hsh(gx, gy, seed=seed + 1)) * cell
			cy = (gy + 0.2 + 0.6 * hsh(gx, gy, seed=seed + 2)) * cell
			rr = radius * (0.6 + 0.8 * hsh(gx, gy, seed=seed + 3))
			d = np.hypot(P2[..., 0] - cx, P2[..., 1] - cy) / rr
			d = np.where(on, d, 1e9)
			closer = d < best
			best = np.where(closer, d, best)
			bid = np.where(closer, gx * 7919 + gy, bid)
	return best, bid


GRASS = C(204, 226, 126)
VIEW = np.array((-0.462, 0.887))  # the camera's heading on the ground: strokes run along it, so they stand up on screen
PATH = [(20.6, -4.6), (21.0, -9.0), (22.4, -15.0), (23.0, -21.0), (22.4, -27.0), (21.3, -31.2)]
GARDEN_X_CURB = 42.0


def path_dist(P2):
	"""distance (studs) from the flagstone path's centre line"""
	pts = np.array(PATH, dtype=np.float32)
	best = np.full(P2.shape[:-1], 1e9, dtype=np.float32)
	for i in range(len(pts) - 1):
		a, b = pts[i], pts[i + 1]
		ab = b - a
		t = np.clip(((P2 - a) @ ab) / (ab @ ab), 0, 1)
		d = np.linalg.norm(P2 - (a + t[..., None] * ab), axis=-1)
		best = np.minimum(best, d)
	return best


def paint_grass(c):
	P = c.P
	P2 = P[..., :2]
	col = np.broadcast_to(GRASS, c.u.shape + (3,)).astype(np.float32).copy()
	big = fbm(P, 10.0, 81)
	col = mix(col, C(196, 216, 118), (ss(0.05, 0.5, big) * 0.7)[..., None])
	col = mix(col, C(150, 186, 92), (ss(-0.05, -0.5, big) * 0.6)[..., None])
	near_house = ss(-6.0, 0.0, P[..., 1]) * ss(13.0, 16.0, P[..., 0])
	col = mix(col, C(140, 178, 88), (near_house * 0.4)[..., None])
	# fine strokes: blades painted along the view, light and dark
	a = P2 @ VIEW
	b = P2 @ np.array((VIEW[1], -VIEW[0]))
	s1 = grain(a, b, True, 0.55, 0.045, 86)
	s2 = grain(a, b, True, 0.3, 0.03, 90)
	col = col * (1 + 0.055 * s1 + 0.03 * s2)[..., None]
	# clover only in groups beside the path and along the curb
	pd = path_dist(P2)
	beside = (1 - ss(2.6, 4.2, pd)) * ss(1.8, 2.6, pd)
	wall_side = ss(GARDEN_X_CURB - 2.5, GARDEN_X_CURB - 0.8, P[..., 0]) + ss(-28.5, -30.0, P[..., 1])
	want = np.clip(beside + 0.6 * wall_side, 0, 1) * ss(0.0, 0.4, fbm(P, 4.0, 82) + 0.3)
	d, bid = clumps(P2, 1.3, 0.85, 0.55, 83)
	lobes = vnoise(np.concatenate([P2 / 0.16, np.zeros_like(P2[..., :1])], -1), 1.0, 85) > -0.2
	leaf = (d < 1.0) & lobes & (hsh(bid, seed=84) < want)
	clover = mix(C(96, 164, 104), C(76, 140, 92), (hsh(bid, seed=86) > 0.5)[..., None].astype(np.float32))
	col = np.where(leaf[..., None], mix(clover, col, ss(0.7, 1.0, d)[..., None] * 0.5), col)
	# small flowers: red along the front-right curb, a few white and yellow elsewhere
	fd, fid = clumps(P2, 1.5, 0.2, 0.17, 87)
	front = np.clip(ss(-27.0, -29.5, P[..., 1]) * ss(30.0, 34.0, P[..., 0]) + ss(39.0, 41.0, P[..., 0]) * ss(-14.0, -22.0, P[..., 1]), 0, 1)
	red = (fd < 1.0) & (hsh(fid, seed=89) < 0.85 * front)
	other = (fd < 1.0) & (hsh(fid, seed=91) < 0.06) & (front < 0.2)
	col = np.where(red[..., None], C(226, 70, 58), col)
	col = np.where(other[..., None], np.where((hsh(fid, seed=92) < 0.5)[..., None], C(250, 246, 236), C(250, 218, 96)), col)
	return col


def voronoi(P2, cell, seed, jitter=0.8):
	"""nearest and second-nearest feature distances (studs) and the nearest feature's id, features jittered in grid cells"""
	g = np.floor(P2 / cell).astype(np.int64)
	d1 = np.full(P2.shape[:-1], 1e9, dtype=np.float32)
	d2 = np.full(P2.shape[:-1], 1e9, dtype=np.float32)
	i1 = np.zeros(P2.shape[:-1], dtype=np.int64)
	for dx in (-1, 0, 1):
		for dy in (-1, 0, 1):
			gx, gy = g[..., 0] + dx, g[..., 1] + dy
			cx = (gx + 0.5 + jitter * (hsh(gx, gy, seed=seed) - 0.5)) * cell
			cy = (gy + 0.5 + jitter * (hsh(gx, gy, seed=seed + 1) - 0.5)) * cell
			d = np.hypot(P2[..., 0] - cx, P2[..., 1] - cy)
			closer = d < d1
			d2 = np.where(closer, d1, np.minimum(d2, d))
			i1 = np.where(closer, gx * 7919 + gy, i1)
			d1 = np.where(closer, d, d1)
	return d1, d2, i1


def paint_paving(c):
	P2 = c.P[..., :2]
	d1, d2, bid = voronoi(P2, 3.4, 91)
	col = np.stack([C(238, 222, 200), C(232, 214, 192), C(242, 228, 208), C(228, 210, 190)])[np.minimum((hsh(bid, seed=92) * 4).astype(np.int64), 3)]
	col = col * (1 + 0.025 * fbm(c.P, 2.0, 94))[..., None]
	gap = d2 - d1
	col = mix(col, C(214, 196, 174), (1 - ss(0.05, 0.16, gap))[..., None] * 0.7)
	col = col * (1 + 0.05 * (1 - ss(0.1, 0.5, gap)) * 0)[..., None]
	return col


def paint_tiles(c):
	x, y = c.P[..., 0], c.P[..., 1]
	a = (x + y) / math.sqrt(2)
	b = (x - y) / math.sqrt(2)
	t = 2.0
	ia, ib = np.floor(a / t), np.floor(b / t)
	fa, fb = a / t - ia, b / t - ib
	col = C(224, 132, 112) * (0.94 + 0.12 * hsh(ia.astype(np.int64), ib.astype(np.int64), seed=95))[..., None]
	grout = (fa < 0.05) | (fb < 0.05) | (fa > 0.95) | (fb > 0.95)
	col = np.where(grout[..., None], C(240, 214, 188), col)
	r = np.hypot(x - 3.2, y + 21.3)
	disc = r < 2.6
	col = np.where(disc[..., None], C(52, 60, 96), col)
	moon = (r < 1.7) & (np.hypot(x - 3.6, y + 20.9) > 1.35)
	col = np.where(moon[..., None], C(238, 220, 186), col)
	col = np.where(((r > 2.6) & (r < 2.85))[..., None], C(230, 200, 170), col)
	return col


def paint_mat(c):
	x, y = c.P[..., 0], c.P[..., 1]
	r = np.hypot(x - 20.4, (y + 0.39) * 4.0 / 3.4)
	col = np.broadcast_to(C(244, 172, 158), c.u.shape + (3,)).astype(np.float32).copy()
	col = np.where((r > 3.45)[..., None], C(222, 136, 122), col)
	fish = (np.abs(r - 2.2) < 0.4) & (np.sin(np.arctan2(y + 0.39, x - 20.4) * 5) > 0.3)
	col = np.where(fish[..., None], C(250, 220, 140), col)
	return col


# ---------------------------------------------------------------------------------------------------------------- props
def paint_barrel(c):
	"""staves round the barrel (u), warm brown, a darker band where hoops sit, lighter in the middle of each stave"""
	R = c.p.get("Radius", 1.5)
	stave = 0.5
	si = np.floor(c.u / stave).astype(np.int64)
	fs = c.u / stave - si
	col = C(132, 82, 56) * (0.9 + 0.2 * hsh(si, seed=c.seed))[..., None]
	col = col * (1 - 0.18 * (1 - ss(0.0, 0.12, fs)) + 0.06 * np.exp(-((fs - 0.5) / 0.3) ** 2))[..., None]
	col = col * (1 + 0.06 * grain(c.u, c.v, False, 1.2, 0.05, c.seed + 1))[..., None]
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	col = col * (1 - 0.15 * (1 - ss(0.0, 0.25, vv)))[..., None]
	return col


def paint_hoop(c):
	return C(70, 56, 52) * (1 + 0.08 * vnoise(c.P, 0.5, 3))[..., None] + np.zeros(c.u.shape + (3,), np.float32)


def paint_barrel_lid(c):
	col = paint_wood(c, C(140, 92, 64), board=0.55, along="u", knots=False)
	return col


def paint_water(c):
	return mix(C(70, 110, 120), C(140, 190, 196), ss(-0.6, 0.8, fbm(c.P, 0.8, 5))[..., None] * 0.5)


def paint_soil(c):
	return C(92, 66, 50) * (1 + 0.1 * vnoise(c.P, 0.25, 7))[..., None] + np.zeros(c.u.shape + (3,), np.float32)


def paint_pot_navy(c):
	"""glazed dark blue: deep body, a soft blue sheen band, a crisp pale highlight streak, a lighter rim"""
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	ang = c.u / max(c.p.get("Radius", 2.0), 0.1)
	col = mix(C(30, 30, 58), C(52, 58, 104), ss(0.1, 0.6, vv)[..., None])
	sheen = np.exp(-((np.cos(ang - 2.4) - 1) / 0.25) ** 2) * np.exp(-((vv - 0.45) / 0.22) ** 2)
	col = mix(col, C(120, 140, 200), (sheen * 0.6)[..., None])
	hl = np.exp(-((np.cos(ang - 2.2) - 1) / 0.03) ** 2) * ss(0.3, 0.5, vv) * (1 - ss(0.7, 0.85, vv))
	col = mix(col, C(230, 236, 250), (hl * 0.8)[..., None])
	col = mix(col, C(214, 186, 160), ss(0.9, 0.95, vv)[..., None])
	return col


def paint_terracotta(c):
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	col = mix(C(206, 128, 100), C(232, 168, 140), ss(0.0, 0.8, vv)[..., None])
	col = col * (1 + 0.05 * fbm(c.P, 0.8, c.seed % 50))[..., None]
	col = mix(col, C(244, 214, 196), (ss(0.85, 0.95, vv) * 0.5)[..., None])
	return col


def paint_pot_cream(c):
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	col = mix(C(214, 186, 152), C(244, 228, 204), ss(0.0, 0.8, vv)[..., None])
	drip = (vv > 0.75) & (np.sin(c.u * 3.1) * 0.07 + 0.82 < vv)
	col = np.where(drip[..., None], C(250, 244, 232), col)
	return col


def paint_chalkboard(c):
	if c.p.get("Face") not in ("-y", "+y"):
		return paint_wood(c, C(170, 120, 84), board=0.3, along="u", knots=False)
	col = np.broadcast_to(C(44, 50, 46), c.u.shape + (3,)).astype(np.float32).copy()
	col = col * (1 + 0.08 * fbm(c.P, 0.6, 9))[..., None]
	if c.p.get("Face") == "-y":
		cu = (c.info["U0"] + c.info["U1"]) / 2
		x = c.u - cu
		y = c.v - c.info["V0"]
		# chalk: a big looped word and three lines, scrawled
		word = (np.abs(np.sin(x * 5.5) * 0.18 + 2.25 - y) < 0.05) & (np.abs(x) < 0.85)
		loops = np.abs(np.hypot(x + 0.55, y - 2.25) - 0.22) < 0.045
		lines = np.zeros_like(word)
		for i, yy in enumerate((1.55, 1.15, 0.75)):
			lines |= (np.abs(y - yy - 0.05 * np.sin(x * 9 + i)) < 0.035) & (x > -0.8) & (x < 0.55 - 0.2 * i)
		chalk = word | loops | lines
		col = np.where(chalk[..., None], C(226, 230, 222), col)
	return col


def paint_wood_light(c):
	return paint_wood(c, C(176, 126, 86), board=0.3, knots=False)


def paint_metal(c):
	return C(54, 48, 50) * (1 + 0.1 * vnoise(c.P, 0.4, 2))[..., None] + np.zeros(c.u.shape + (3,), np.float32)


def paint_lamp(c):
	vv = (c.v - c.info["V0"]) / max(c.info["V1"] - c.info["V0"], 1e-3)
	return mix(C(255, 214, 140), C(255, 244, 210), np.exp(-((vv - 0.45) / 0.3) ** 2)[..., None])


def paint_sign(c):
	"""the reference's pink sign with a cup on it"""
	col = np.broadcast_to(C(232, 166, 150), c.u.shape + (3,)).astype(np.float32).copy()
	col = col * (1 + 0.04 * fbm(c.P, 0.8, 3))[..., None]
	ed = c.edge_dist()
	col = np.where((ed < 0.16)[..., None], C(196, 120, 104), col)
	if c.p.get("Face") in ("-x", "+x"):
		cu = (c.info["U0"] + c.info["U1"]) / 2
		cv = (c.info["V0"] + c.info["V1"]) / 2
		x, y = c.u - cu, c.v - cv
		cup = (np.abs(x) < 0.42) & (y > -0.45) & (y < 0.35) & ((np.abs(x) > 0.3) | (y < -0.33) | (y > 0.24))
		cup |= (np.abs(np.hypot(x - 0.5, y + 0.02) - 0.16) < 0.06) & (x > 0.42)
		col = np.where(cup[..., None], C(120, 70, 60), col)
	return col


def paint_book(c):
	return np.broadcast_to(C(176, 64, 58), c.u.shape + (3,)).astype(np.float32).copy()


FLAG = [C(204, 166, 142), C(184, 164, 160), C(214, 184, 156), C(176, 146, 136), C(198, 178, 168), C(222, 194, 166)]


def paint_flag(c):
	"""flagstones: warm brown, mauve and grey stones, each one tone with a soft lighter rise toward its middle"""
	sid = c.p.get("Stone", 0)
	base = FLAG[int(hsh(np.array(sid), seed=11) * len(FLAG)) % len(FLAG)]
	col = np.broadcast_to(base, c.u.shape + (3,)).astype(np.float32).copy()
	col = col * (1 + 0.05 * fbm(c.P, 1.2, 12 + sid) + 0.02 * vnoise(c.P, 0.3, 13))[..., None]
	if c.p.get("Face") == "+z":
		ed = c.edge_dist()
		col = col * (1 + 0.07 * ss(0.05, 0.6, ed) - 0.04)[..., None]
	else:
		col = col * C(0.84, 0.8, 0.82)
	return col


def paint_grout(c):
	col = np.broadcast_to(C(232, 214, 190), c.u.shape + (3,)).astype(np.float32).copy()
	col = mix(col, C(170, 196, 110), (ss(0.2, 0.5, fbm(c.P, 1.5, 15)) * 0.45)[..., None])
	return col


AO_TINT = C(0.6, 0.53, 0.6)
AO_STRENGTH = {"Walls": 0.8, "Walls2": 0.75, "Tower": 0.7, "Trim": 0.7, "RoofA": 0.55, "RoofB": 0.55, "RoofC": 0.55, "Garden": 0.42, "Ground": 0.5, "Base": 0.55, "Path": 0.5, "Props": 0.6}
AO_TINTS = {"Garden": C(0.6, 0.68, 0.52)}

PAINTERS = {
	"slate": paint_slate,
	"slate_lip": paint_slate_lip,
	"slate_cap": paint_slate_cap,
	"slate_under": paint_slate_under,
	"ashlar": paint_ashlar,
	"ashlar_in": paint_ashlar,
	"ashlar_reveal": paint_ashlar_reveal,
	"ashlar_round": paint_ashlar_round,
	"brick": paint_brick,
	"retaining": paint_retaining,
	"voussoir": paint_voussoir,
	"crown": paint_crown,
	"corbel": paint_corbel,
	"green_light": paint_green_light,
	"cream": paint_cream,
	"cream_ring": paint_cream,
	"curb": paint_curb,
	"step": paint_step,
	"step_pink": paint_step_pink,
	"plaster": paint_plaster,
	"plaster_pink": paint_plaster_pink,
	"plaster_reveal": paint_plaster_reveal,
	"planks": paint_planks,
	"wood": paint_wood_plain,
	"shutter": paint_shutter,
	"wood_lid": paint_wood_lid,
	"window_box": paint_window_box,
	"green": paint_green,
	"shutter_green": paint_shutter_green,
	"door": paint_door,
	"glass": paint_glass,
	"interior": paint_interior,
	"grass": paint_grass,
	"grass_bed": paint_grass,
	"paving": paint_paving,
	"tiles": paint_tiles,
	"mat": paint_mat,
	"barrel": paint_barrel,
	"hoop": paint_hoop,
	"barrel_lid": paint_barrel_lid,
	"water": paint_water,
	"soil": paint_soil,
	"pot_navy": paint_pot_navy,
	"terracotta": paint_terracotta,
	"pot_cream": paint_pot_cream,
	"chalkboard": paint_chalkboard,
	"wood_light": paint_wood_light,
	"metal": paint_metal,
	"lamp": paint_lamp,
	"sign": paint_sign,
	"book": paint_book,
	"flag": paint_flag,
	"grout": paint_grout,
	"fascia": paint_fascia,
}


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
			col = fn(c) if fn else np.broadcast_to(C(255, 0, 255), c.u.shape + (3,))
			x0, y0 = info["PX"] * SS, info["PY"] * SS
			h, w = min(c.h, big - y0), min(c.w, big - x0)
			m = c.mask[:h, :w]
			canvas[y0 : y0 + h, x0 : x0 + w][m] = np.clip(col[:h, :w][m], 0, 255)
			filled[y0 : y0 + h, x0 : x0 + w] |= m
		# baked ambient occlusion (tools/blender/pink_cottage.py bake_ao): contact shadows Roblox can't draw, in a warm mauve
		ao_path = os.path.join(OUT, "sheets", "ao", f"{sheet}.png")
		if os.path.exists(ao_path) and not args.no_ao:
			ao = np.asarray(Image.open(ao_path).convert("L").resize((big, big), Image.BILINEAR), dtype=np.float32) / 255
			ao = ndimage.gaussian_filter(ao, 1.2)
			k = AO_STRENGTH.get(sheet, 0.65)
			dark = np.clip(1 - ao, 0, 1) ** 1.15 * k
			canvas = canvas + (canvas * AO_TINTS.get(sheet, AO_TINT) - canvas) * dark[..., None] * filled[..., None]
		# bleed colours into the gaps so mip levels and filtering don't pull in black
		_, (iy, ix) = ndimage.distance_transform_edt(~filled, return_indices=True)
		canvas = canvas[iy, ix]
		img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
		img.save(os.path.join(OUT, "sheets", f"{sheet}.png"))
		print(f"[paint] {sheet}: {len(items)} islands, {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
	main()
