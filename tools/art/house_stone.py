"""A house's stone base, built from the stone bridge's parts (tools/art/bridge_kit.py, loaded, not changed), in the bridge house's colour: laid courses, a cap along the top, corner blocks and door jambs that join them, a doorstep.
It follows the house's own lean. Writes art/kit/<house>/<House>_Stone.png and .obj.

  python tools/art/house_stone.py cottage|townhouse|farmhouse
"""
import copy
import importlib
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stone_extras as E  # noqa: E402

HOUSE = sys.argv[1]
STYLE = sys.argv[2] if len(sys.argv) > 2 else None  # Rich or Muted: multi-coloured dark brick, written beside the plain stone as <House>_Stone_<style>
OUT = os.environ.get("HOUSE_OUT") or os.path.join("art", "kit", HOUSE)
RIM = os.environ.get("HOUSE_RIM") == "1"  # the framing test: stones towards the outer corners go darker and warmer, on their own copies of the cards, so no draw and no stone moves
RIM_STRONG, RIM_SOFT = (0.84, 0.78, 0.73), (0.93, 0.89, 0.86)
RIM_FAR = 2.2  # studs along a wall from the corner
sys.argv = [HOUSE, OUT]
M = importlib.import_module(HOUSE + "_kit")
CFG = getattr(M, "STONE", None)  # newer houses say all this themselves
if CFG:
	CFG.setdefault("bases", [CFG])
	_b = CFG["bases"][0]
	XA, XB, ZB, ZF, FOOT, DU, warp = _b["xa"], _b["xb"], _b["zb"], _b["zf"], _b["foot"], _b.get("du"), M.warp
elif HOUSE == "cottage":
	XA, XB, ZB, ZF, FOOT, DU, warp = -M.HX, M.HX, -M.HZ, M.HZ, M.FOOT_Y, -1.56, M.warp
elif HOUSE == "townhouse":
	XA, XB, ZB, ZF, FOOT, DU, warp = -M.X0, M.X0, M.Z_BACK, M.Z0, M.FOOT_Y, -2.3, M.warp
else:
	XA, XB, ZB, ZF, FOOT, DU, warp = -M.HX, M.HX, -M.HZ, M.HZ, M.FOOT_Y, -4.6, M.warp
DW = CFG.get("dw", 3.5) if CFG else 3.5
PIECE = HOUSE.capitalize() + "_Stone"
SUFFIX = "_" + STYLE if STYLE else ""
SCHEME = {"BASE": (150, 146, 158), "LIGHT": (178, 174, 180), "WARM": (168, 156, 150), "DUSK": (122, 120, 142), "COOL": (134, 140, 160), "CRACK": (92, 88, 110), "MORTAR": (84, 78, 104), "SHADOW": (112, 108, 124), "WET": (116, 122, 138), "DECK_BASE": (170, 164, 160), "DECK_LIGHT": (192, 186, 176), "DECK_DUSK": (140, 138, 150)}
_argv = sys.argv
sys.argv = ["bridge_kit", OUT]
src = open(os.path.join(HERE, "bridge_kit.py"), encoding="utf-8").read()
old = 'SCHEME = sys.argv[2] if len(sys.argv) > 2 else "Sandstone"'
assert old in src, "bridge_kit.py changed"
src = src.replace(old, f'SCHEMES["HouseStone"] = dict(**{SCHEME!r})\nSCHEME = "HouseStone"')
K = {"__name__": "bridge_parts"}
exec(compile(src[: src.index("def main():")], "bridge_kit.py", "exec"), K)
sys.argv = _argv
K["EDGE"] = np.array((206, 200, 196), float)
K["EDGE_PALE"] = np.array((186, 180, 178), float)
K["COURSE"] = 1.15
K["WIDTHS"] = (1.3, 1.9, 2.5, 3.2)
COURSE, WIDTHS = K["COURSE"], K["WIDTHS"]
Sheet, Card, BeamCard, Tile, Builder = K["Sheet"], K["Card"], K["BeamCard"], K["Tile"], K["Builder"]
SS, SHEET = K["SS"], K["SHEET"]
TX = 52
OFF = 0.42  # how far the stone stands out from the wall
TOP = FOOT - 0.3  # the top of the laid courses


def level_at(y):
	return "mid" if y > FOOT - 1.0 else "low" if y > 0.25 else "water"


def main():
	rng = np.random.default_rng(sum(map(ord, HOUSE)))
	s = Sheet()
	C = {"mortar": Tile(s, 16, 16, "mortar", rng), "end": Tile(s, 24, 24, "end", rng), "wall": {}}
	for level in ("mid", "low", "water") if not STYLE else ():
		for tone in ("base", "pale", "dark"):
			for w in WIDTHS:
				if w == WIDTHS[0] and tone != "base":
					continue
				C["wall"][(level, tone, w)] = Card(s, f"w_{level}_{tone}_{w}", w, COURSE, 0.14, TX, f"{level}/{tone}", rng)
	C["cap"] = [BeamCard(s, f"cap{i}", 5.0, 0.86, 0.34, 0.1, 40, "string", rng, C["end"]) for i in range(2)]
	C["block"] = [Card(s, f"block{i}", 1.5, 2.2, 0.15, TX, "low/base", rng) for i in range(3)]
	# stones with moss painted on: most on the row at the ground, a little on the row above
	C["moss"] = {}
	for level, cover in (("water", 0.82), ("low", 0.32)):
		for w in WIDTHS:
			C["moss"][(level, w)] = [Card(s, f"m_{level}_{w}_{i}", w, COURSE, 0.14, TX, f"{level}/base", rng) for i in range(2)]
			for c_ in C["moss"][(level, w)]:
				E.paint_moss(s.img, c_.x, c_.y, c_.W, c_.H, cover * float(rng.uniform(0.82, 1.1)), rng, SS)
	C["step"] = [Card(s, f"step{i}", 3.0, 1.2, 0.15, TX, "deck", rng) for i in range(2)]
	multi = None
	if STYLE:
		pal = E.PALETTES[STYLE]
		multi = E.Multi(s, Card, WIDTHS, COURSE, 0.14, TX, pal, rng, SS)
		for pool in C["moss"].values():
			for c_ in pool:
				E.tint_card(s, c_, pal["slate_dark"], SS)
		for c_ in C["block"]:
			E.tint_card(s, c_, pal["frame"], SS)
		for c_ in C["cap"]:
			E.tint(s, c_.x, c_.y, c_.W, c_.H, pal["cap"], SS)
		for c_ in C["step"]:
			E.tint_card(s, c_, pal["umber"], SS)
		E.tint(s, C["mortar"].x, C["mortar"].y, C["mortar"].W, C["mortar"].H, (0.6, 0.6, 0.66), SS)
	b = Builder(C, rng)
	twins = {}

	def twin(c, tone):
		"""the same painted stone in a darker, warmer copy"""
		if (id(c), tone) not in twins:
			t = copy.copy(c)
			t.x, t.y = s.place(c.W, c.H)
			s.img[t.y * SS : (t.y + c.H) * SS, t.x * SS : (t.x + c.W) * SS] = s.img[c.y * SS : (c.y + c.H) * SS, c.x * SS : (c.x + c.W) * SS] * np.array(tone, np.float32)
			twins[(id(c), tone)] = t
		return twins[(id(c), tone)]

	def rimmed(c, corner):
		"""stones near a corner take one darker tone, and the corner stones themselves the strongest. One copy per stone size, so the sheet has room"""
		if not RIM or corner > RIM_FAR:
			return c
		if corner == 0:
			return twin(c, RIM_STRONG)
		n = c.name.split("_")
		if n[0] == "w":
			c = C["wall"].get((n[1], "base", float(n[3])), c)
		elif n[0] == "m":
			c = C["moss"][(n[1], float(n[2]))][0]
		elif n[0].startswith("cap"):
			c = C["cap"][0]
		return twin(c, RIM_SOFT)

	def card(w, y, near_end=None, u=None):
		"""near_end: how far along the wall from its nearest end. Moss gathers near the ends and leaves bare stretches between"""
		ws = min(WIDTHS, key=lambda v: abs(v - w))
		level = level_at(y)
		if near_end is not None and level in ("water", "low"):
			chance = (0.1 + 0.8 * np.exp(-near_end / 2.6)) * (1.0 if level == "water" else 0.45)
			if rng.random() < chance:
				pool = C["moss"][(level, ws)]
				return pool[int(rng.integers(len(pool)))]
		if multi:
			return multi.pick(w, y, u, near_end)
		f = rng.normal(0, 0.55)
		tone = "base" if ws == WIDTHS[0] else "pale" if f > 0.5 else "dark" if f < -0.5 else "base"
		return C["wall"][(level_at(y), tone, ws)]

	def block(cx, cy, cz, hx, hy, hz, cards):
		"""a chunky stone with finished faces: it takes in the ends of what meets there"""
		c = np.array((cx, cy, cz), float)
		Y = np.array((0, 1.0, 0))
		for N, hn, U, hu, V, hv in (((1, 0, 0), hx, (0, 0, -1), hz, Y, hy), ((-1, 0, 0), hx, (0, 0, 1), hz, Y, hy), ((0, 0, 1), hz, (1, 0, 0), hx, Y, hy), ((0, 0, -1), hz, (-1, 0, 0), hx, Y, hy), ((0, 1, 0), hy, (1, 0, 0), hx, (0, 0, -1), hz)):
			N, U, V = np.array(N, float), np.array(U, float), np.array(V, float)
			o = c + N * hn
			rim = [o - U * hu - V * hv, o + U * hu - V * hv, o + U * hu + V * hv, o - U * hu + V * hv]
			b.pillow(PIECE, rim, N, cards[int(rng.integers(len(cards)))], 0.13, 0.07, tilt=0.008)

	def run(p0, p1, cards, w, h, near=(True, True)):
		p0, p1 = np.array(p0, float), np.array(p1, float)
		ln = np.linalg.norm(p1 - p0)
		at = 0.0
		while at < ln - 0.2:
			step = float(rng.uniform(2.6, 3.8))
			if at + step > ln - 1.0:
				step = ln - at
			c_ = cards[int(rng.integers(len(cards)))]
			if RIM:
				c_ = rimmed(c_, min(at + step / 2 if near[0] else 99, ln - at - step / 2 if near[1] else 99))
			b.beam(PIECE, p0 + (p1 - p0) * at / ln, p0 + (p1 - p0) * (at + step - 0.05) / ln, w, h, c_)
			at += step

	def laid(o, U, N, u0, u1, near=(True, True)):
		o, U, N = np.array(o, float), np.array(U, float), np.array(N, float)
		if multi:
			multi.new_wall()
		b.courses(lambda _m: PIECE, o, U, N, u0, u1, TOP, -1.2, lambda _u: 0.0, lambda w, y, u, k: rimmed(card(w, y, min(u - u0, u1 - u), u), min(u - u0 if near[0] else 99, u1 - u if near[1] else 99)), lambda *_a: [], b=0.16, depth=0.13)
		q = [o + U * u0 + np.array((0, -1.2, 0)) - N * 0.03, o + U * u1 + np.array((0, -1.2, 0)) - N * 0.03, o + U * u1 + np.array((0, TOP + 0.05, 0)) - N * 0.03, o + U * u0 + np.array((0, TOP + 0.05, 0)) - N * 0.03]
		b.plain_quad(PIECE, q, N, C["mortar"])

	def one_base(XA, XB, ZB, ZF, DU, DW, step=True, floor=False):
		ZERO_MID = (XA + XB) / 2
		xa, xb, zb, zf = XA - OFF, XB + OFF, ZB - OFF, ZF + OFF
		dl, dr = (DU - DW / 2 - 0.78, DU + DW / 2 + 0.78) if DU is not None else (ZERO_MID, ZERO_MID)
		# the courses, four walls, the front in two lengths either side of the door
		laid((0, 0, zf), (1, 0, 0), (0, 0, 1), xa, dl, (True, False))
		laid((0, 0, zf), (1, 0, 0), (0, 0, 1), dr, xb, (False, True))
		laid((0, 0, zb), (-1, 0, 0), (0, 0, -1), -xb, -xa)
		laid((xb, 0, 0), (0, 0, -1), (1, 0, 0), -zf, -zb)
		laid((xa, 0, 0), (0, 0, 1), (-1, 0, 0), zb, zf)
		# the cap along the top, tying the stone to the wall
		y = TOP - 0.03
		cz, cx = OFF * 0.45, OFF * 0.45
		run((xa, y, ZF + cz), (dl, y, ZF + cz), C["cap"], 0.86, 0.34, (True, False))
		run((dr, y, ZF + cz), (xb, y, ZF + cz), C["cap"], 0.86, 0.34, (False, True))
		run((xa, y, ZB - cz), (xb, y, ZB - cz), C["cap"], 0.86, 0.34)
		run((XB + cx, y, zb), (XB + cx, y, zf), C["cap"], 0.86, 0.34)
		run((XA - cx, y, zb), (XA - cx, y, zf), C["cap"], 0.86, 0.34)
		# the joins: corner stones the full height, and jambs at the door
		mid, hy = (TOP + 0.14 - 1.2) / 2, (TOP + 0.14 + 1.2) / 2
		# quoins: two rows laid long and short in turn, set into the courses, stopping at the cap
		yc = (TOP + 0.3 - 1.2) / 2
		h2 = (TOP + 0.3 + 1.2) / 4
		for x, sx in ((xa, 1), (xb, -1)):
			for z, sz in ((zb, 1), (zf, -1)):
				for row in range(2):
					long_x = (row + (sx > 0) + (sz > 0)) % 2 == 0
					hx_, hz_ = (0.85, 0.48) if long_x else (0.48, 0.85)
					block(x + sx * (hx_ - 0.2), yc + (row - 0.5) * 2 * h2, z + sz * (hz_ - 0.2), hx_, h2 - 0.01, hz_, [rimmed(c_, 0) for c_ in C["block"]])
		for x in ((dl, dr) if DU is not None else ()):
			block(x, mid, zf, 0.3, hy, 0.5, C["block"])
		if floor:  # flags across an open floor, level with the ground
			q = [np.array((XA, 0.03, ZF)), np.array((XB, 0.03, ZF)), np.array((XB, 0.03, ZB)), np.array((XA, 0.03, ZB))]
			b.plain_quad(PIECE, q, (0, 1, 0), C["mortar"])
			for i, x0 in enumerate(np.arange(XA, XB - 1, 3.6)):
				for j, z0 in enumerate(np.arange(ZB, ZF - 0.5, 2.4)):
					x1, z1 = min(x0 + 3.55, XB), min(z0 + 2.35, ZF)
					rim = [np.array((x0, 0.06, z1)), np.array((x1, 0.06, z1)), np.array((x1, 0.06, z0)), np.array((x0, 0.06, z0))]
					b.pillow(PIECE, rim, (0, 1, 0), C["step"][(i + j) % 2], 0.13, 0.06, tilt=0.01)
		# the doorstep: one big slab
		if DU is not None and step:
			block(DU, 0.05, zf + 0.6, DW / 2 + 0.55, 0.55, 0.85, C["step"])
	if CFG:
		for c_ in CFG["bases"]:
			one_base(c_["xa"], c_["xb"], c_["zb"], c_["zf"], c_.get("du"), c_.get("dw", 3.5), c_.get("step", True), c_.get("floor", False))
	else:
		one_base(XA, XB, ZB, ZF, DU, DW)
	# chimney
	if CFG:
		pass
	elif HOUSE == "cottage":
		cx, cz = M.CHIMNEY
		sections = [(cx, cz, 1.85, 1.35, -1.0, 9.6), (cx + 0.2, cz, 1.17, 0.85, 9.84, 21.0)]
	elif HOUSE == "townhouse":
		sections = [(0.75, -2.7, 1.18, 1.38, M.RIDGE_Y - 6.6, M.RIDGE_Y + 2.7)]
	else:
		sections = [(6.2, -1.7, 1.18, 1.38, M.RIDGE_Y - 6.0, M.RIDGE_Y + 2.9)]
	for sec in CFG["chimneys"] if CFG else [sections]:
		E.chimney(b, C, lambda w, y_: card(w, 9.0), block, PIECE, sec)
	b.m.check()
	Image.fromarray(np.clip(s.img * K["GRADE"], 0, 255).astype(np.uint8)).resize((SHEET, SHEET), Image.LANCZOS).save(os.path.join(OUT, PIECE + SUFFIX + ".png"))
	lines_, faces, vi = [f"o {PIECE}"], [], 1
	tris = b.m.tris[PIECE]
	for tri, uv, normals in tris:
		for q_, t, n_ in zip(tri, uv, normals):
			n_ = np.asarray(n_, float)
			n_ = n_ / (np.linalg.norm(n_) + 1e-9)
			lines_.append("v %.4f %.4f %.4f" % tuple(warp(tuple(q_))))
			lines_.append("vt %.5f %.5f" % (t[0] / SHEET, 1 - t[1] / SHEET))
			lines_.append("vn %.4f %.4f %.4f" % tuple(n_))
		faces.append(f"f {vi}/{vi}/{vi} {vi + 1}/{vi + 1}/{vi + 1} {vi + 2}/{vi + 2}/{vi + 2}")
		vi += 3
	open(os.path.join(OUT, PIECE + SUFFIX + ".obj"), "w").write("\n".join(lines_ + faces) + "\n")
	print(PIECE, "triangles", len(tris), "sheet used to row", s.y + s.row, "of", SHEET)


main()
