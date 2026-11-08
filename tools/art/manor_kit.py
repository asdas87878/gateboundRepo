"""The manor: a large prop house. A wide centre range with its door, and two wings stepping forward with their own gables. Built on the house kit.
  python tools/art/manor_kit.py art/kit/manor
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/manor")
import house_base as B  # noqa: E402

K = B.K
B.setup("Manor")
F1, F2 = B.F1, B.F1 + B.FLOOR
CHX, CHZ = 11.5, 7.0
WX, WHX, WHZ = 17.0, 5.5, 9.2
K.FOOT_Y = B.FOOT
K.GRAD_Y = (2.5, 26)
K.warp = B.make_warp(-WX - 7, WX + 7, lean=0.012, sag=0.5)
warp = K.warp
STONE = dict(bases=[dict(xa=-CHX, xb=CHX, zb=-CHZ, zf=CHZ, foot=B.FOOT, du=0.0), dict(xa=-WX - WHX, xb=-WX + WHX, zb=-WHZ, zf=WHZ, foot=B.FOOT), dict(xa=WX - WHX, xb=WX + WHX, zb=-WHZ, zf=WHZ, foot=B.FOOT)], chimneys=[[(-WX, -3.6, 1.25, 1.45, 18.0, 30.0)], [(WX, 3.2, 1.18, 1.38, 18.0, 29.0)], [(-3.0, -1.5, 1.1, 1.3, 19.0, 28.0)]])


def build():
	B.block(0, 0, CHX, CHZ, [F1, F2], ridge="x", pitch=0.9, gable_over=0.0, courses=8, door_u=0.0, sun=(0.5, 0.4), hide=("left", "right"),
		windows={"front": [(-6.9, B.WIN0, False), (6.9, B.WIN0, False), (-6.9, B.above(F1), True), (0, B.above(F1), False), (6.9, B.above(F1), True)], "back": [(-6.0, B.WIN0, False), (6.0, B.WIN0, False), (-6.0, B.above(F1), False), (6.0, B.above(F1), False)]})
	for sign in (1, -1):
		B.block(sign * WX, 0, WHX, WHZ, [F1, F2], ridge="z", pitch=1.2, eave_over=1.3, courses=8, moss=0.2 if sign > 0 else 0, sun=(0.4, 0.4), hide=("left",) if sign > 0 else ("right",),
			windows={"front": [(0, B.WIN0, False), (0, B.above(F1), True), (0, B.above(F2), False)], "back": [(0, B.WIN0, False), (0, B.above(F1), False)], ("right" if sign > 0 else "left"): [(-4.0, B.WIN0, False), (4.0, B.WIN0, True), (0, B.above(F1), False)]})
	B.chimney(-WX, -3.6, 0, 30.0)
	B.chimney(WX, 3.2, 0, 29.0)
	B.chimney(-3.0, -1.5, 0, 28.0)


if __name__ == "__main__":
	K.main(build)
