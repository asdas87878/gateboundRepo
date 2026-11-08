"""The terrace: a large prop. Three joined narrow houses of different heights and widths, gables to the street. Built on the house kit.
  python tools/art/terrace_kit.py art/kit/terrace
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/terrace")
import house_base as B  # noqa: E402

K = B.K
B.setup("Terrace")
B.slate()
F1, F2, F3 = B.F1, B.F1 + B.FLOOR, B.F1 + 2 * B.FLOOR
K.FOOT_Y = B.FOOT
K.GRAD_Y = (2.5, 30)
A, BX, C = (-13.0, 6.4, -2.6, 3.1), (0.0, 6.6, -2.6, 3.2), (13.2, 6.6, -2.6, 3.2)
HZ = 6.2
K.warp = B.make_warp(-20, 20, lean=0.01, sag=0.5)
warp = K.warp
STONE = dict(bases=[dict(xa=cx - hx, xb=cx + hx, zb=-HZ, zf=HZ, foot=B.FOOT, du=cx + du) for cx, hx, du, _w in (A, BX, C)], chimneys=[[(A[0] - 1.6, -2.8, 1.1, 1.3, 15.0, 25.6)], [(BX[0] + 1.6, -2.8, 1.1, 1.3, 24.0, 36.0)], [(C[0] - 1.4, -2.8, 1.1, 1.3, 15.0, 26.0)]])


def build():
	def house(spec, floors, hide, sun=None, moss=0.0, shutters=(True, False)):
		cx, hx, du, wu = spec
		w = {"front": [(wu, B.WIN0, False)], "back": [(-2.6, B.WIN0, False), (2.6, B.above(F1), False)]}
		for i, fl in enumerate(floors[:-1]):
			w["front"].append((0.0, B.above(fl), shutters[i % 2]))
		w["front"].append((0.0, B.above(floors[-1]), False))
		side = next((n for n in ("left", "right") if n not in hide), None)
		if side:
			w[side] = [(0.0, B.above(F1), False)]
		B.block(cx, 0, hx, HZ, floors, ridge="z", pitch=1.4, eave_over=0.95, courses=8, door_u=du, hide=hide, sun=sun, moss=moss, windows=w)

	house(A, [F1, F2], ("right",), sun=(0.5, 0.4))
	house(BX, [F1, F2, F3], ("left", "right"), shutters=(False, True), sun=(0.3, 0.4))
	house(C, [F1, F2], ("left",), moss=0.25)
	B.chimney(A[0] - 1.6, -2.8, 0, 25.6)
	B.chimney(BX[0] + 1.6, -2.8, 0, 36.0)
	B.chimney(C[0] - 1.4, -2.8, 0, 26.0)


if __name__ == "__main__":
	K.main(build)
