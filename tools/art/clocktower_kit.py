"""The clock tower: a prop landmark. A tall square tower with a painted clock on two faces, a long hall beside it. Built on the house kit.
  python tools/art/clocktower_kit.py art/kit/clocktower
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2:
	sys.argv.append("art/kit/clocktower")
import house_base as B  # noqa: E402

K = B.K
B.setup("Clocktower")
B.slate()
TX, THX, THZ = -10.5, 5.6, 5.6
HALLX, HHX, HHZ = 7.0, 12.0, 6.4
F1, F2 = B.F1, B.F1 + B.FLOOR
F3 = F2 + B.FLOOR
F4 = F3 + 7.2  # the clock's storey
K.FOOT_Y = B.FOOT
K.GRAD_Y = (2.5, 36)
K.warp = B.make_warp(TX - 7, HALLX + 13, lean=0.006, sag=0.4)
warp = K.warp
STONE = dict(bases=[dict(xa=TX - THX, xb=TX + THX, zb=-THZ, zf=THZ, foot=B.FOOT), dict(xa=HALLX - HHX, xb=HALLX + HHX, zb=-HHZ, zf=HHZ, foot=B.FOOT, du=HALLX + 2.5)], chimneys=[[(13.0, -2.0, 1.18, 1.38, 18.0, 25.5)]])


def paint_clock(r):
	"""a pale dial on a dark board: twelve chunky marks, two hands, a ring"""
	S = 4
	W = r.w * K.SS * S // 2
	im = Image.new("RGB", (W, W), (88, 66, 72))
	d = ImageDraw.Draw(im)
	c = W / 2
	for rad, col in ((0.49, (60, 56, 84)), (0.455, (226, 212, 180)), (0.415, (240, 230, 204))):
		d.ellipse((c - W * rad, c - W * rad, c + W * rad, c + W * rad), fill=col)
	for i in range(12):
		a = math.tau * i / 12
		big = i % 3 == 0
		r0, r1, wd = (0.3, 0.4, 0.045) if big else (0.345, 0.4, 0.024)
		dx, dy = math.sin(a), -math.cos(a)
		d.line((c + dx * W * r0, c + dy * W * r0, c + dx * W * r1, c + dy * W * r1), fill=(58, 54, 84), width=int(W * wd))
	for a, ln, wd in ((math.tau * 0.84, 0.23, 0.04), (math.tau * 0.04, 0.34, 0.026)):
		d.line((c, c, c + math.sin(a) * W * ln, c - math.cos(a) * W * ln), fill=(46, 44, 72), width=int(W * wd))
	d.ellipse((c - W * 0.04, c - W * 0.04, c + W * 0.04, c + W * 0.04), fill=(170, 130, 70))
	img = np.array(im.resize((r.w * K.SS, r.h * K.SS), Image.LANCZOS), float)
	yy = (np.arange(img.shape[0]) / img.shape[0])[:, None, None]
	return np.clip(img * (0.86 + 0.16 * yy), 0, 255)


def clock(face):
	v = F3 + (F4 - F3) / 2
	size = 4.4
	rect = K.JOIN.add((size, size), paint_clock)
	corners = [face.at(-size / 2, v - size / 2, 0.22), face.at(size / 2, v - size / 2, 0.22), face.at(size / 2, v + size / 2, 0.22), face.at(-size / 2, v + size / 2, 0.22)]
	K.emit.append(lambda c=corners, o=face.out: K.plate(c, rect, o, 0.1))
	face.block(-size / 2, v - size / 2, size / 2, v + size / 2)
	t = size / 2 + 0.24
	face.beam((-t - 0.2, v + t), (t + 0.2, v + t + 0.03), w=0.56, h=0.48, d=0.3, unique=True, hero=True)
	face.beam((-t - 0.2, v - t), (t + 0.2, v - t + 0.03), w=0.56, h=0.48, d=0.3, unique=True)
	for s in (-1, 1):
		face.beam((s * t, v - t), (s * t, v + t), w=0.5, h=0.44, d=0.26, unique=True)


def build():
	tower = B.block(TX, 0, THX, THZ, [F1, F2, F3, F4], ridge="z", pitch=1.55, eave_over=1.3, courses=9, sun=(0.5, 0.4), hide=("right",),
		windows={"front": [(0, B.WIN0, False), (0, B.above(F1), True), (0, B.above(F2), False)], "left": [(0, B.WIN0, False), (0, B.above(F1), False), (0, B.above(F2), True)], "back": [(0, B.above(F1), False), (0, B.above(F2), False)]})
	clock(tower["faces"]["front"])
	clock(tower["faces"]["left"])
	# the tower's right side above the hall's roof
	r = K.Face("right", (TX + THX, 0, 0), (0, 0, -1), (1, 0, 0))
	for fl in (F2, F3, F4):
		r.beam((-THZ - 0.3, fl), (THZ + 0.3, fl + 0.05), w=0.7, h=B.JETTY_H, d=0.14)
	for u in (-THZ + 0.1, THZ - 0.1):
		r.beam((u, F2), (u, F4), w=B.POST_DEPTH, h=B.POST, d=0.18)
	K.wall(r, -THZ, THZ, F1, tower["roofat"] if False else (lambda u: F4 + 0.1), shade_y=F4, shadow_depth=0.8, cols=5, rows=5)
	K.window(r, 0, B.above(F2), B.WIN, B.WIN, shutters=False)
	clock(r)
	B.block(HALLX, 0, HHX, HHZ, [F1, F2], ridge="x", pitch=0.95, courses=7, door_u=2.5, sun=(0.7, 0.45), moss=0.25, hide=("left",),
		windows={"front": [(-7.4, B.WIN0, False), (8.2, B.WIN0, True), (-4.8, B.above(F1), True), (5.6, B.above(F1), True)], "back": [(-5.5, B.WIN0, False), (5.5, B.WIN0, False), (0, B.above(F1), False)], "right": [(0, B.WIN0, True), (0, B.above(F1), False), (0, B.above(F2), False)]})
	B.chimney(13.0, -2.0, 0, 25.5)


if __name__ == "__main__":
	K.main(build)
