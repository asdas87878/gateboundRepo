"""The hut: a small thatched prop house with a lean-to shed on its side. Built on the house kit.
  python tools/art/hut_kit.py art/kit/hut
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/hut")
import house_base as B  # noqa: E402

K = B.K
B.setup("Hut")
HX, HZ = 7.2, 5.2
LX, LHZ = 4.6, 4.3  # the lean-to: how far it stands out, half its depth
K.FOOT_Y = B.FOOT
K.GRAD_Y = (2.5, 14)
B.tiles((136, 120, 88), (140, 122, 84), (130, 114, 88), (118, 104, 84), (150, 134, 100), (82, 70, 62), (92, 80, 68), (0.22, 0.42), (0.0, 0.03))
K.TILE_SIDE = 0.28
K.TILE_PLANE = 0.3
K.SCHEMES["Straw"] = {"BASE": (136, 112, 72), "LIGHT": (150, 128, 84), "WARM": (142, 114, 68), "DUSK": (112, 92, 68), "COOL": (118, 100, 74), "GRAIN": (86, 68, 50)}
K.warp = B.make_warp(-HX - 1, HX + LX + 1, lean=0.018, sag=0.6)
warp = K.warp
SHED_HI, SHED_LO = B.F1 - 0.3, 6.1
STONE = dict(bases=[dict(xa=-HX, xb=HX, zb=-HZ, zf=HZ, foot=B.FOOT, du=-1.9), dict(xa=HX, xb=HX + LX, zb=-LHZ, zf=LHZ, foot=B.FOOT)], chimneys=[[(-3.8, -1.3, 1.05, 1.2, 12.0, 18.7)]])


def build():
	B.block(0, 0, HX, HZ, [B.F1], ridge="x", pitch=1.25, eave_over=1.7, courses=5, lift=0.3, moss=0.1, ridge_scheme="Straw",
		door_u=-1.9, windows={"front": [(3.6, B.WIN0, False)], "back": [(0.0, B.WIN0, False)], "left": [(0.0, B.WIN0, False), (0.0, B.above(B.F1), False)], "right": [(0.0, B.above(B.F1), False)]})
	line = lambda d: SHED_HI + (SHED_LO - SHED_HI) * d / LX
	for z, right, out in ((LHZ, 1, 1), (-LHZ, -1, -1)):
		f = K.Face("shed", (HX + LX / 2, 0, z), (right, 0, 0), (0, 0, out))
		f.beam((right * (LX / 2 - 0.1), B.FOOT), (right * (LX / 2 - 0.1), SHED_LO), w=0.6, h=0.7, d=0.16)
		K.wall(f, -LX / 2, LX / 2, B.FOOT - 0.5, lambda u, r=right: line(LX / 2 + r * u), cols=2, rows=3, shadow_depth=0.5)
	s = K.Face("shed", (HX + LX, 0, 0), (0, 0, -1), (1, 0, 0))
	s.beam((-LHZ - 0.2, SHED_LO - 0.2), (LHZ + 0.2, SHED_LO - 0.18), w=0.66, h=0.6, d=0.14)
	K.window(s, 0.0, 2.95, B.WIN * 0.72, B.WIN * 0.72, shutters=False)
	K.wall(s, -LHZ, LHZ, B.FOOT - 0.5, lambda u: SHED_LO, cols=4, rows=2, shadow_depth=0.6)
	K.tiled((HX - 0.1, SHED_HI + 0.3, LHZ + 0.7), (HX - 0.1, SHED_HI + 0.3, -LHZ - 0.7), (HX + LX + 1.0, SHED_LO - 0.25, LHZ + 0.7), 3, (1, 1, 0), lift=0.26, nx=5, moss=0.15)
	B.chimney(-3.8, -1.3, 0, 18.7)


if __name__ == "__main__":
	K.main(build)
