"""The bridge house's stone base, built from the stone bridge's own parts (tools/art/bridge_kit.py: painted stone cards, hand-laid courses, pillow stones, voussoirs, long stones), in a cooler colour.
bridge_kit.py is loaded, not changed. Writes art/kit/bridgehouse/Bridgehouse_Stone.png and .obj: world positions, y up, the street along z.

  python tools/art/bridgehouse_stone.py art/kit/bridgehouse
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bridgehouse_shape as Z  # noqa: E402
import stone_extras as E  # noqa: E402

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/bridgehouse")
STYLE = sys.argv[2] if len(sys.argv) > 2 else None  # Rich or Muted: multi-coloured dark brick, written beside the plain stone
SUFFIX = "_" + STYLE if STYLE else ""
SCHEME = {"BASE": (150, 146, 158), "LIGHT": (178, 174, 180), "WARM": (168, 156, 150), "DUSK": (122, 120, 142), "COOL": (134, 140, 160), "CRACK": (92, 88, 110), "MORTAR": (84, 78, 104), "SHADOW": (112, 108, 124), "WET": (116, 122, 138), "DECK_BASE": (170, 164, 160), "DECK_LIGHT": (192, 186, 176), "DECK_DUSK": (140, 138, 150)}
_argv = sys.argv
sys.argv = ["bridgehouse", OUT]
import bridgehouse_kit as H  # noqa: E402  (its lean and ridge; its timber is built when run by itself)

sys.argv = ["bridge_kit", OUT]
src = open(os.path.join(HERE, "bridge_kit.py"), encoding="utf-8").read()
old = 'SCHEME = sys.argv[2] if len(sys.argv) > 2 else "Sandstone"'
assert old in src, "bridge_kit.py changed"
src = src.replace(old, f'SCHEMES["HouseStone"] = dict(**{SCHEME!r})\nSCHEME = "HouseStone"')
K = {"__name__": "bridge_parts"}
exec(compile(src[: src.index("def main():")], "bridge_kit.py", "exec"), K)
sys.argv = _argv

K["EDGE"] = np.array((206, 200, 196), float)  # the bridge's near-white highlights blow out on the smaller steps and plinth
K["EDGE_PALE"] = np.array((186, 180, 178), float)
K["COURSE"] = 1.7  # the house's stones are smaller than the big bridge's
K["WIDTHS"] = (1.5, 2.3, 3.0, 3.8)
COURSE, WIDTHS = K["COURSE"], K["WIDTHS"]
Sheet, Card, BeamCard, Tile, Builder = K["Sheet"], K["Card"], K["BeamCard"], K["Tile"], K["Builder"]
unit, SS, SHEET = K["unit"], K["SS"], K["SHEET"]
PIECE = "Bridgehouse_Stone"
TX = 40  # texels a stud
R, SPRING, RING, Y0, XO, ZS = Z.R, Z.SPRING, Z.RING, Z.Y0, Z.XO, Z.ZS
LEVELS = ("lit", "mid", "low", "water")
TONES = ("base", "pale", "dark")


def level_at(y):
	return "lit" if y > 8.5 else "mid" if y > 4.5 else "low" if y > 1.6 else "water"


def main():
	rng = np.random.default_rng(83)
	s = Sheet()
	C = {"mortar": Tile(s, 16, 16, "mortar", rng), "soffit": Tile(s, 170, 96, "soffit", rng), "cap": Tile(s, 60, 60, "cap", rng), "end": Tile(s, 24, 24, "end", rng)}
	C["wall"] = {}
	for level in LEVELS if not STYLE else ():
		for tone in TONES:
			for w in WIDTHS:
				if w == WIDTHS[0] and tone != "base":
					continue
				C["wall"][(level, tone, w)] = Card(s, f"w_{level}_{tone}_{w}", w, COURSE, 0.17, TX, f"{level}/{tone}", rng)
	C["vous"] = {st: [Card(s, f"v_{st}{i}", 1.5, 1.9, 0.18, TX, paint, rng) for i in range(2)] for st, paint in (("lit", "lit/base"), ("mid", "mid/base"))}
	C["band"] = [BeamCard(s, f"band{i}", 5.0, 1.15, 0.72, 0.16, 34, "string", rng, C["end"]) for i in range(2)]
	C["plinth"] = [BeamCard(s, f"plinth{i}", 5.0, 1.3, 1.5, 0.2, 30, "plain", rng, C["end"]) for i in range(2)]
	for c_ in C["plinth"][:1]:
		E.paint_moss(s.img, c_.x, c_.y + c_.rows[4], c_.W, c_.rows[5] - c_.rows[4], 0.72, rng, SS)
		E.paint_moss(s.img, c_.x, c_.y, c_.W, c_.rows[1], 0.72, rng, SS)
	C["block"] = [Card(s, f"block{i}", 2.3, 1.7, 0.17, TX, "low/base", rng) for i in range(2)]
	C["block_mid"] = [Card(s, f"blockm{i}", 1.7, 1.0, 0.17, TX, "mid/base", rng) for i in range(2)]
	C["step"] = [BeamCard(s, f"step{i}", 5.0, Z.STEP_Z + 0.12, Z.STEP_H, 0.13, 34, "plain", rng, C["end"]) for i in range(3)]
	C["moss"] = {}
	for level, cover in (("water", 0.7), ("low", 0.26)):
		for w in WIDTHS:
			C["moss"][(level, w)] = [Card(s, f"m_{level}_{w}", w, COURSE, 0.17, TX, f"{level}/base", rng)]
			c_ = C["moss"][(level, w)][0]
			E.paint_moss(s.img, c_.x, c_.y, c_.W, c_.H, cover, rng, SS)
	C["deck"] = [Card(s, f"deck{i}", 2.6, 2.2, 0.17, TX, "deck", rng) for i in range(3)]
	multi = None
	if STYLE:
		pal = E.PALETTES[STYLE]
		multi = E.Multi(s, Card, WIDTHS, COURSE, 0.17, TX, pal, rng, SS)
		for pool in C["moss"].values():
			for c_ in pool:
				E.tint_card(s, c_, pal["slate_dark"], SS)
		for c_ in C["block"]:
			E.tint_card(s, c_, pal["frame"], SS)
		for c_ in C["block_mid"]:
			E.tint_card(s, c_, pal["frame"], SS)
		for c_ in C["plinth"]:
			E.tint(s, c_.x, c_.y, c_.W, c_.H, pal["frame"], SS)
		for c_ in C["band"]:
			E.tint(s, c_.x, c_.y, c_.W, c_.H, pal["cap"], SS)
		for c_ in C["step"]:
			E.tint(s, c_.x, c_.y, c_.W, c_.H, pal["slate"], SS)
		for c_ in C["deck"]:
			E.tint_card(s, c_, pal["umber"], SS)
		E.tint(s, C["soffit"].x, C["soffit"].y, C["soffit"].W, C["soffit"].H, (0.66, 0.64, 0.72), SS)
		E.tint(s, C["mortar"].x, C["mortar"].y, C["mortar"].W, C["mortar"].H, (0.6, 0.6, 0.66), SS)
		# the arch: two tones in turn round a rust keystone, its own frame in the wall
		C["vous_a"] = [Card(s, "v_a", 1.5, 1.9, 0.18, TX, "mid/base", rng)]
		C["vous_b"] = [Card(s, "v_b", 1.5, 1.9, 0.18, TX, "mid/base", rng)]
		C["vous_key"] = [Card(s, "v_k", 1.5, 1.9, 0.18, TX, "lit/base", rng)]
		E.tint_card(s, C["vous_a"][0], pal["frame"], SS)
		E.tint_card(s, C["vous_b"][0], pal["umber"], SS)
		E.tint_card(s, C["vous_key"][0], pal["rust"], SS)
	b = Builder(C, rng)
	K["COURSE"] = COURSE

	def card(w, y, u=None, k=0, near_end=None):
		ws = min(WIDTHS, key=lambda v: abs(v - w))
		if y < 3.3 and level_at(y) in ("water", "low") and rng.random() < (0.5 if level_at(y) == "water" else 0.2):
			return C["moss"][(level_at(y), ws)][0]
		if multi:
			return multi.pick(w, y, u, near_end, foot_y=2.4)
		f = rng.normal(0, 0.55)
		tone = "base" if ws == WIDTHS[0] else "pale" if f > 0.5 else "dark" if f < -0.5 else "base"
		return C["wall"][(level_at(y), tone, ws)]

	centre = np.array((0.0, SPRING))
	rc = R + RING + 0.03  # the wall is laid round the whole ring: the arch sits in the wall, not on it

	def arch_clips(zw, side):
		def clips(u0, u1, y0, y1):
			sa, sb = sorted((u0 * side, u1 * side))
			if sb <= -R or sa >= R + RING + 0.1 or sb <= -(R + RING + 0.1) and y0 >= SPRING:
				if not (sb <= -R and y0 >= SPRING and sb > -(R + RING + 0.1)):
					return []
			if y0 < SPRING - 0.01:  # below the springing: the pier's stones stop at the opening
				if sa > -R and sb < R:
					return None
				if sb <= -R or sa >= R:
					return []
				if sa <= -R:
					return [(np.array((-R, 0, zw)), np.array((-1.0, 0, 0)))]
				return [(np.array((R, 0, zw)), np.array((1.0, 0, 0)))]
			pts = [np.array((u, v)) for u in (sa, sb) for v in (y0, y1)]
			if max(np.linalg.norm(q - centre) for q in pts) < rc:
				return None
			near = np.array((np.clip(0.0, sa, sb), np.clip(SPRING, y0, y1)))
			dist = np.linalg.norm(near - centre)
			if dist >= rc:
				return []
			d = (near - centre) / max(dist, 1e-6)
			return [(np.array((d[0] * rc, SPRING + d[1] * rc, zw)), np.array((d[0], d[1], 0.0)))]

		return clips

	anchor = SPRING + round((Y0 - SPRING) / COURSE) * COURSE  # a course ends exactly where the arch springs; the top row runs up behind the floor
	piece = lambda _m: PIECE
	no_shear = lambda _u: 0.0
	# ---- the two big faces, the arch cut through them
	for side in (1, -1):
		zw = side * ZS
		b.courses(piece, np.array((0, 0, zw), float), np.array((side, 0, 0), float), np.array((0, 0, side), float), -XO, XO, anchor, -1.2, no_shear, lambda w, y, u, k: card(w, y, u, k, XO - abs(u)), arch_clips(zw, side))
		cols = np.linspace(-XO, XO, 25)
		cols = sorted(set(list(cols) + [-R, R]))
		for a, c in zip(cols, cols[1:]):
			m = (a + c) / 2
			low = lambda u: SPRING + math.sqrt(max(R * R - u * u, 0)) if -R - 1e-6 <= m <= R + 1e-6 else -1.2
			q = [np.array((u, h, side * (ZS - 0.04))) for u, h in ((a, low(a)), (c, low(c)), (c, anchor), (a, anchor))]
			b.plain_quad(PIECE, q, (0, 0, side), C["mortar"])
	# ---- the outer ends of the piers; the right one mostly hidden by the stair
	for sign in (1, -1):
		b.courses(piece, np.array((sign * XO, 0, 0), float), np.array((0, 0, -sign), float), np.array((sign, 0, 0), float), -ZS, ZS, anchor, -1.2, no_shear, lambda w, y, u, k: card(w, y, u, k, ZS - abs(u)), lambda *_a: [], depth=0.16)
		q = [np.array((sign * (XO - 0.04), -1.2, z)) for z in (-ZS, ZS)] + [np.array((sign * (XO - 0.04), anchor, z)) for z in (ZS, -ZS)]
		b.plain_quad(PIECE, q, (sign, 0, 0), C["mortar"])
	# ---- the arch: barrel, pier faces, voussoirs on both faces with a big keystone
	segs = 12
	P = lambda t, z: np.array((R * math.sin(t), SPRING + R * math.cos(t), z))
	for i in range(segs):
		t0, t1 = -math.pi / 2 + math.pi * i / segs, -math.pi / 2 + math.pi * (i + 1) / segs
		nA, nB = -unit(P(t0, 0) - np.array((0, SPRING, 0))), -unit(P(t1, 0) - np.array((0, SPRING, 0)))
		q = [P(t0, -ZS), P(t1, -ZS), P(t1, ZS), P(t0, ZS)]
		v0 = (i % 4) / 4
		uv = [C["soffit"].uv(0, v0), C["soffit"].uv(0, v0 + 0.25), C["soffit"].uv(1, v0 + 0.25), C["soffit"].uv(1, v0)]
		b.m.quad(PIECE, q, uv, (nA, nB, nB, nA), -unit(P((t0 + t1) / 2, 0) - np.array((0, SPRING, 0))))
	for x, d in ((-R, 1), (R, -1)):
		q = [np.array((x, -1.2, -ZS)), np.array((x, -1.2, ZS)), np.array((x, SPRING + 0.2, ZS)), np.array((x, SPRING + 0.2, -ZS))]
		b.plain_quad(PIECE, q, (d, 0, 0), C["soffit"])
	# behind the wall stones where they meet the curve: a band of plain stone colour, so what shows between them reads as a joint, not a hole
	fill = multi.cards[("slate", WIDTHS[2])] if multi else C["wall"][("mid", "base", WIDTHS[2])]
	fill_uv = fill.uv(0.5, 0.5)
	for side in (1, -1):
		for i in range(20):
			t0, t1 = -math.pi / 2 + math.pi * i / 20, -math.pi / 2 + math.pi * (i + 1) / 20
			F = lambda r, t: np.array((r * math.sin(t), SPRING + r * math.cos(t), side * (ZS - 0.02)))
			q = [F(R + RING - 0.1, t0), F(R + RING - 0.1, t1), F(R + RING + 1.5, t1), F(R + RING + 1.5, t0)]
			nz = np.array((0, 0, float(side)))
			b.m.quad(PIECE, q, [fill_uv] * 4, [nz] * 4, nz)
	n = 11
	edges = np.cumsum(np.concatenate(([0], rng.uniform(0.96, 1.04, n))))
	edges = edges / edges[-1] * math.pi - math.pi / 2
	for i in range(n):
		t0, t1 = edges[i], edges[i + 1]
		key = i == n // 2
		for side in (1, -1):
			z = side * ZS
			R0, R1 = R, R + RING + (0.2 if key else 0)
			V = lambda r, t: np.array((r * math.sin(t), SPRING + r * math.cos(t), z))
			gap = 0.035 / R
			rim = [V(R0, t0 + gap), V(R0, t1 - gap), V(R1, t1 - gap), V(R1, t0 + gap)]
			if side == 1:
				rim = [V(R0, t1 - gap), V(R0, t0 + gap), V(R1, t0 + gap), V(R1, t1 - gap)]
			pool = C["vous"]["lit" if (rim[0][1] + rim[2][1]) / 2 > 6.5 else "mid"]
			if multi:
				pool = (C["vous_key"] if key else C["vous_a"] if i % 2 == 0 else C["vous_b"]) * 2
			b.pillow(PIECE, rim, (0, 0, side), pool[int(rng.integers(2))], 0.18, 0.28 if key else 0.2)

	def run(p0, p1, cards, w, h, up=(0, 1, 0)):
		"""long stones end to end along p0..p1"""
		p0, p1 = np.array(p0, float), np.array(p1, float)
		ln = np.linalg.norm(p1 - p0)
		at = 0.0
		while at < ln - 0.3:
			step = float(rng.uniform(2.6, 3.8))
			if at + step > ln - 1.0:
				step = ln - at
			b.beam(PIECE, p0 + (p1 - p0) * at / ln, p0 + (p1 - p0) * (at + step - 0.05) / ln, w, h, cards[int(rng.integers(len(cards)))], up=up)
			at += step

	def block(cx, cy, cz, hx, hy, hz, cards):
		"""a chunky corner stone with finished faces: it takes in the ends of the long stones meeting there"""
		c = np.array((cx, cy, cz), float)
		Y = np.array((0, 1.0, 0))
		for N, hn, U, hu, V, hv in (((1, 0, 0), hx, (0, 0, -1), hz, Y, hy), ((-1, 0, 0), hx, (0, 0, 1), hz, Y, hy), ((0, 0, 1), hz, (1, 0, 0), hx, Y, hy), ((0, 0, -1), hz, (-1, 0, 0), hx, Y, hy), ((0, 1, 0), hy, (1, 0, 0), hx, (0, 0, -1), hz)):
			N, U, V = np.array(N, float), np.array(U, float), np.array(V, float)
			o = c + N * hn
			rim = [o - U * hu - V * hv, o + U * hu - V * hv, o + U * hu + V * hv, o - U * hu + V * hv]
			b.pillow(PIECE, rim, N, cards[int(rng.integers(len(cards)))], 0.14, 0.08, tilt=0.01)

	# ---- round each pier: a plinth at the foot and a ledge the arch stands on. On the stair's side they stop against the stair
	for sign in (1, -1):
		for y, h, off, cards, w, by, bhy, bh, inn, inner_cards in ((-0.5, 1.5, 0.3, C["plinth"], 1.3, 0.12, 1.14, 0.95, R + 0.05, C["block"]), (SPRING - 0.72, 0.72, 0.18, C["band"], 1.15, SPRING - 0.33, 0.39, 0.72, R + 0.3, C["block_mid"])):
			xi = sign * inn
			xo = sign * (XO + off)
			z = ZS + off
			open_end = sign > 0  # the stair takes the outer end
			x_end = sign * XO if open_end else xo
			for side in (1, -1):
				run((xi, y, side * z), (x_end, y, side * z), cards, w, h)
				block(xi, by, side * z, bh, bhy, bh, inner_cards)
				if not open_end:
					block(xo, by, side * z, bh, bhy, bh, inner_cards)
			run((xi, y, -z), (xi, y, z), cards, w, h)
			if not open_end:
				run((xo, y, -z), (xo, y, z), cards, w, h)
	# ---- the stair: long steps, a laid stone side cut to the slope, a stone back, flags on the landing
	x0, x1 = XO, XO + Z.STAIR_W
	h = Y0 / Z.STEPS
	for i in range(Z.STEPS):
		top = Y0 - i * h
		z = Z.LANDING_Z + (i + 0.5) * Z.STEP_Z
		b.beam(PIECE, (x0 - 0.05, top - h - 0.1, z), (x1 + 0.2, top - h - 0.1, z), Z.STEP_Z + 0.12, h + 0.1, C["step"][int(rng.integers(3))])
	top_at_ = lambda z: Y0 if z <= Z.LANDING_Z else Y0 * (Z.Z_END - z) / (Z.Z_END - Z.LANDING_Z)
	slope_pt = np.array((x1, Y0, Z.LANDING_Z))
	slope_n = unit(np.array((0, -(Z.Z_END - Z.LANDING_Z), -Y0)))

	def stair_clip(_u0, _u1, _y0, _y1):
		return [(slope_pt, slope_n)]

	b.courses(piece, np.array((x1, 0, 0), float), np.array((0, 0, -1), float), np.array((1, 0, 0), float), -Z.Z_END, -Z.BACK, anchor - 0.12, -1.2, no_shear, lambda w, y, u, k: card(w, y, u), stair_clip)
	inner_o = np.array((x0, 0, 0), float)
	b.courses(piece, inner_o, np.array((0, 0, 1), float), np.array((-1, 0, 0), float), ZS, Z.Z_END, anchor - 0.12, -1.2, no_shear, lambda w, y, u, k: card(w, y), lambda *_a: [(np.array((x0, Y0, Z.LANDING_Z)), slope_n)])
	zi = np.linspace(ZS, Z.Z_END, 8)
	for a, c in zip(zi, zi[1:]):
		q = [np.array((x0 + 0.04, -1.2, a)), np.array((x0 + 0.04, -1.2, c)), np.array((x0 + 0.04, top_at_(c), c)), np.array((x0 + 0.04, top_at_(a), a))]
		b.plain_quad(PIECE, q, (-1, 0, 0), C["mortar"])
	cols = np.linspace(Z.BACK, Z.Z_END, 12)
	top_at = lambda z: Y0 if z <= Z.LANDING_Z else Y0 * (Z.Z_END - z) / (Z.Z_END - Z.LANDING_Z)
	for a, c in zip(cols, cols[1:]):
		q = [np.array((x1 - 0.04, -1.2, c)), np.array((x1 - 0.04, -1.2, a)), np.array((x1 - 0.04, top_at(a), a)), np.array((x1 - 0.04, top_at(c), c))]
		b.plain_quad(PIECE, q, (1, 0, 0), C["mortar"])
	back_o = np.array((x1, 0, Z.BACK), float)
	b.courses(piece, back_o, np.array((-1, 0, 0), float), np.array((0, 0, -1), float), 0, Z.STAIR_W, anchor - 0.12, -1.2, no_shear, lambda w, y, u, k: card(w, y), lambda *_a: [])
	q = [np.array((x1, -1.2, Z.BACK + 0.04)), np.array((x0, -1.2, Z.BACK + 0.04)), np.array((x0, Y0, Z.BACK + 0.04)), np.array((x1, Y0, Z.BACK + 0.04))]
	b.plain_quad(PIECE, q, (0, 0, -1), C["mortar"])
	# flags: rows across the landing, over a dark bed
	q = [np.array((x0, Y0 - 0.1, Z.LANDING_Z)), np.array((x1, Y0 - 0.1, Z.LANDING_Z)), np.array((x1, Y0 - 0.1, Z.BACK)), np.array((x0, Y0 - 0.1, Z.BACK))]
	b.plain_quad(PIECE, q, (0, 1, 0), C["mortar"])
	zs = np.linspace(Z.BACK, Z.LANDING_Z, 4)
	for za, zc in zip(zs, zs[1:]):
		rim = [np.array((x0 + 0.03, Y0 - 0.02, zc - 0.04)), np.array((x1 - 0.03, Y0 - 0.02, zc - 0.04)), np.array((x1 - 0.03, Y0 - 0.02, za + 0.04)), np.array((x0 + 0.03, Y0 - 0.02, za + 0.04))]
		b.pillow(PIECE, rim, (0, 1, 0), C["deck"][int(rng.integers(3))], 0.17, 0.1, tilt=0.01)
	E.chimney(b, C, lambda w, y_: card(w, 9.0), block, PIECE, [(7.8, -1.9, 1.18, 1.38, H.RIDGE_Y - 6.0, H.RIDGE_Y + 2.6)])
	b.m.check()
	# ---- write: world positions, not centred like the big bridge's pieces
	Image.fromarray(np.clip(s.img * K["GRADE"], 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS).save(os.path.join(OUT, PIECE + SUFFIX + ".png"))
	lines_, faces, vi = [f"o {PIECE}"], [], 1
	tris = b.m.tris[PIECE]
	for tri, uv, normals in tris:
		for q_, t, n_ in zip(tri, uv, normals):
			n_ = np.asarray(n_, float)
			n_ = n_ / (np.linalg.norm(n_) + 1e-9)
			lines_.append("v %.4f %.4f %.4f" % tuple(H.warp(tuple(q_))))
			lines_.append("vt %.5f %.5f" % (t[0] / SHEET, 1 - t[1] / SHEET))
			lines_.append("vn %.4f %.4f %.4f" % tuple(n_))
		faces.append(f"f {vi}/{vi}/{vi} {vi + 1}/{vi + 1}/{vi + 1} {vi + 2}/{vi + 2}/{vi + 2}")
		vi += 3
	open(os.path.join(OUT, PIECE + SUFFIX + ".obj"), "w").write("\n".join(lines_ + faces) + "\n")
	print("stone triangles", len(tris), "sheet used to row", s.y + s.row, "of", SHEET)


main()
