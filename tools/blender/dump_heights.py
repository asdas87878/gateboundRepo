"""Dump a Land's terrain heights to an npz for the checks outside Blender (tools/art/walk_review.py).

  blender --background --python tools/blender/dump_heights.py -- art/lands/land1/map.json art/lands/land1/beauty/_cache/heights.npz
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import land_blockout as lb  # noqa: E402

out = sys.argv[sys.argv.index("--") + 2]
lb.STEP = lb.M["Beauty"].get("Step", 2.5)
for zname, ov in lb.M["Beauty"].get("ZoneOverrides", {}).items():
	lb.B["Zones"].setdefault(zname, {}).update(ov)
xs, ys, X, Y, Z, zone, water, path = lb.build_heights()
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
np.savez_compressed(out, xs=xs, ys=ys, Z=Z.astype(np.float32), water=water)
print("saved", Z.shape, float(Z.min()), float(Z.max()))
