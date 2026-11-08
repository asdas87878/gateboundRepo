"""Bakes a Land's block-out heights and materials into one PNG, which Studio reads back through an EditableImage (tools/studio/build_land_greybox.luau).

Red and green = height (16 bits, (height + 40) * 100), blue = material id, one pixel per 4-stud terrain column.
Material ids: 0 grass, 1 dark grass (Whisperwood), 2 dry ground (Bandit Ridge), 3 pale stone (Gatehill), 4 rock (steep), 5 sand, 6 path, 7 water, 8 town.

  blender --background --python tools/blender/export_land_terrain.py -- art/lands/land1/map.json art/lands/land1/greybox/terrain.png
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import land_blockout as lb  # noqa: E402

out = sys.argv[sys.argv.index("--") + 2]
lb.STEP = 4.0
lb.B["Border"] = 200
xs, ys, X, Y, Z, zone, water, path = lb.build_heights()
names = [z["Name"] for z in lb.M["Zones"]]
gy, gx = np.gradient(Z, 4.0)
slope = np.hypot(gx, gy)
mat = np.zeros(Z.shape, np.uint8)
for k, n in enumerate(names):
	mat[zone == k] = {"Whisperwood": 1, "Bandit Ridge": 2, "Gatehill": 3}.get(n, 0)
water_near = lb.smoothstep(14.0, 2.0, np.minimum(lb.seg_dist(X, Y, lb.M["River"]), 1e9) - lb.B["RiverWidth"] / 2)
mat[(water_near > 0.5) & (Z < 3)] = 5
mat[slope > 0.85] = 4
hub = next(p for p in lb.M["Places"] if p["Icon"] == "castle")["At"]
isl = lb.B["Island"]
dh = np.hypot(X - hub[0], Y - hub[1])
mat[(dh < isl["Radius"]) & (slope <= 0.85)] = 8
mat[path] = 6
mat[water] = 7
enc = np.clip(np.round((Z + 40) * 100), 0, 65535).astype(np.uint32)
img = np.zeros((*Z.shape, 4), np.uint8)
img[..., 0] = enc >> 8
img[..., 1] = enc & 255
img[..., 2] = mat
img[..., 3] = 255

# write the PNG without PIL, which Blender's Python lacks
import struct  # noqa: E402
import zlib  # noqa: E402

h, w = img.shape[:2]
raw = b"".join(b"\x00" + img[j].tobytes() for j in range(h))


def chunk(tag, data):
	return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
with open(out, "wb") as f:
	f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
print("[land] size", w, h, "from x", xs[0], "y", ys[0], "heights", round(float(Z.min()), 1), round(float(Z.max()), 1), "mats", np.bincount(mat.ravel()).tolist(), flush=True)
