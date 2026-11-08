"""The rock pack: every rock shape for hand-building scenes, in one set with one paint (docs/style/rock-pack.md).

  blender --background --python tools/blender/rock_pack.py -- build [--only A,B] [--out <folder>]    rock_pack.blend, bake.npz, kit.json
  python tools/art/paint_rock_pack.py [--out <folder>]                                                Pack_<sheet>_Moss.png, Pack_<sheet>_Clean.png
  blender --background --python tools/blender/rock_pack.py -- render <group|all> <Moss|Clean> [--out <folder>]    lineup_<group>_<variant>.png
  blender --background --python tools/blender/rock_pack.py -- export [--out <folder>]                 RockPack.glb

A piece is one or more lumps. A lump is a chunky block: a box, its top tapered, tilted or leaning, cut by a few planes, so it keeps big flat faces
with chipped corners. Lumps overlap; a face fully inside another lump is left out. Real edges are bevelled, so paint has an edge to catch.
Origin at the base centre, studs, Z up. Front is -Y on cliffs: their backs are rarely seen. Faces at the ground on grounded lumps are removed.
"""

import json
import math
import os
import random
import sys
import zlib

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import rock_kit as old  # noqa: E402  (the earlier kit: its shapes, UV layout and stage)

ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def option(name, default=None):
	return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = os.path.join(ROOT, option("--out", os.path.join("art", "kit", "rock_pack")))
NATURAL = os.path.join(ROOT, "art", "kit", "rocks_natural", "rock_kit.blend")

# texels a stud per group, and so how many sheets. Roblox cuts every texture to 1024, so a bigger group means more sheets rather than a bigger one.
DENSITY = {"Chips": 30, "Boulders": 22, "Slabs": 20, "Cubes": 20, "Modular": 17, "Spires": 14, "Clusters": 15, "Cliffs": 8.5, "Classic": 13, "Natural": 13}
SHEET_FILL = 0.56  # the share of a sheet the shelf packer really fills

PIECES = {}  # name: (group, lumps)
CORNERS = ((-1, -1), (1, -1), (1, 1), (-1, 1))


def b(x, y, L, W, H, z=0.0, yaw=0.0, pitch=0.0, roll=0.0, **shape):
	"""one lump: centre x, y; size L, W, H; z its base; turned yaw degrees, then tipped. shape: see chunk()"""
	return {"x": x, "y": y, "z": z, "L": L, "W": W, "H": H, "yaw": yaw, "pitch": pitch, "roll": roll, "shape": shape}


def add(group, name, lumps):
	PIECES[name] = (group, lumps)


def hull(points):
	bm = bmesh.new()
	verts = [bm.verts.new(q) for q in points]
	res = bmesh.ops.convex_hull(bm, input=verts)
	bmesh.ops.delete(bm, geom=[v for v in set(res["geom_interior"]) | set(res["geom_unused"]) if isinstance(v, bmesh.types.BMVert)], context="VERTS")
	return bm


def cut(points, co, no):
	"""keep what's behind a plane"""
	bm = hull(points)
	bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
	out = [v.co.copy() for v in bm.verts]
	bm.free()
	return out


def chunk(L, W, H, seed, chips=2, edge=1, vert=1, facets=None, taper=0.92, lean=(0.0, 0.0), tilt=(0.0, 0.0), ramp=0.0, exact=False, bite=1.0, rough=0.04, segments=2, bevel=(0.1, 0.6, 0.034)):
	"""a chunky block. chips: top corners cut off; edge: top edges chamfered; vert: upright edges chamfered; taper: top's size against the foot;
	lean: how far the top slides, fractions of L and W; tilt: top slope along L and W, fractions of H; ramp: the top falls by this share from -x to +x;
	exact: straight flat top and exact footprint, for stacking; bite: how deep the cuts go; facets: how many side faces get a plane cut across them.
	Returns the bmesh and the hull's planes."""
	r = random.Random(seed)
	j = 0.0 if exact else rough
	top = []
	pts = []
	for sx, sy in CORNERS:
		pts.append(Vector((sx * L / 2 * (1 - r.uniform(0, j)), sy * W / 2 * (1 - r.uniform(0, j)), 0)))
		tz = H * (1 + tilt[0] * sx + tilt[1] * sy + (0 if exact else r.uniform(-0.035, 0.035)))
		tz -= H * ramp * (sx + 1) / 2
		c = Vector((sx * L / 2 * taper * (1 - r.uniform(0, j * 1.6)) + lean[0] * L, sy * W / 2 * taper * (1 - r.uniform(0, j * 1.6)) + lean[1] * W, tz))
		top.append(c)
		pts.append(c)
	small = min(L, W, H)
	order = list(range(4))
	r.shuffle(order)
	for i in order[:chips]:
		c = top[i]
		sx, sy = CORNERS[i]
		no = Vector((sx * r.uniform(0.55, 1.0), sy * r.uniform(0.55, 1.0), r.uniform(0.7, 1.15))).normalized()
		pts = cut(pts, c - no * small * r.uniform(0.09, 0.2) * bite, no)
	sides = [(1, 0), (-1, 0), (0, 1), (0, -1)]
	r.shuffle(sides)
	for sx, sy in sides[:edge]:
		mid = sum((top[i] for i, k in enumerate(CORNERS) if (sx and k[0] == sx) or (sy and k[1] == sy)), Vector()) / 2
		no = Vector((sx * r.uniform(0.7, 1.1), sy * r.uniform(0.7, 1.1), 1)).normalized()
		pts = cut(pts, mid - no * small * r.uniform(0.05, 0.12) * bite, no)
	r.shuffle(order)
	for i in order[:vert]:
		sx, sy = CORNERS[i]
		c = Vector((sx * L / 2, sy * W / 2, H / 2))
		no = Vector((sx, sy, r.uniform(-0.12, 0.2))).normalized()
		pts = cut(pts, c - no * small * r.uniform(0.07, 0.17) * bite, no)
	# facets: each one tips part of a side face back by about 10-25 degrees, starting partway across it, so one face becomes two planes
	if facets is None:
		facets = 0 if exact else (2 + int(max(L, W, H) > 9) + int(max(L, W, H) > 18))
	for _ in range(facets):
		sx, sy = r.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
		along = Vector((sy, sx, 0))
		reach = (W if sx else L) / 2
		u, v = r.choice(((1, 0.25), (-1, 0.25), (0.3, 1), (-0.3, 1), (0.7, 0.7), (-0.7, 0.7)))
		steep = r.uniform(0.2, 0.42)
		no = (Vector((sx, sy, 0)) + (along * u + Vector((0, 0, v))).normalized() * steep).normalized()
		point = Vector((sx * L / 2 * (1 if sx else 0), sy * W / 2 * (1 if sy else 0), H * 0.5))
		point = point * 0.97 + along * u * reach * r.uniform(0.1, 0.5) + Vector((0, 0, v * H * r.uniform(0.04, 0.26)))
		pts = cut(pts, point, no)
	bm = hull(pts)
	bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
	bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(4), verts=list(bm.verts), edges=list(bm.edges))
	bm.normal_update()
	planes = [(f.normal.copy(), f.verts[0].co.copy()) for f in bm.faces]
	layer = bm.faces.layers.int.new("bevel")
	edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(25)]
	res = bmesh.ops.bevel(bm, geom=edges, offset=max(bevel[0], min(bevel[1], small * bevel[2])), offset_type="OFFSET", segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True)
	for f in res["faces"]:
		f[layer] = 1
	bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
	if signed_volume(bm) < 0:
		bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
	bm.normal_update()
	return bm, planes


def signed_volume(bm):
	v = 0.0
	for f in bm.calc_loop_triangles():
		a, c, d = (l.vert.co for l in f)
		v += a.dot(c.cross(d)) / 6
	return v


def build_lump(spec, seed, segments):
	s = dict(spec["shape"])
	s.setdefault("segments", segments)
	bm, planes = chunk(spec["L"], spec["W"], spec["H"], seed, **s)
	assert signed_volume(bm) > 0, f"inside out or empty: {seed} {spec['L']} {spec['W']} {spec['H']} {s}"
	M = Matrix.Translation((spec["x"], spec["y"], spec["z"])) @ Matrix.Rotation(math.radians(spec["yaw"]), 4, "Z") @ Matrix.Rotation(math.radians(spec["pitch"]), 4, "X") @ Matrix.Rotation(math.radians(spec["roll"]), 4, "Y")
	bmesh.ops.transform(bm, matrix=M, verts=list(bm.verts))
	rot = M.to_3x3()
	planes = [((rot @ n).normalized(), M @ q) for n, q in planes]
	bm.normal_update()
	if spec["z"] <= 0.01 and spec["pitch"] == 0 and spec["roll"] == 0:
		bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.8 and f.calc_center_median().z < spec["z"] + 0.1 * spec["H"]], context="FACES")
	return bm, planes


# ---- single blocks: irregular, with big flat faces
for name, (L, W, H, shape) in {
	"CubeSmallA": (5, 5, 4.5, {}),
	"CubeSmallB": (6, 4.6, 5, {"chips": 3}),
	"CubeSmallC": (4.6, 4.4, 3.4, {"chips": 1, "edge": 2}),
	"CubeA": (8, 8, 7, {"chips": 1, "edge": 1}),
	"CubeB": (9, 7, 8, {"chips": 2, "vert": 2}),
	"CubeC": (8, 7, 6, {"chips": 3, "bite": 1.4}),
	"CubeD": (10, 8, 7.5, {"chips": 2, "tilt": (0.05, -0.04)}),
	"CubeLargeA": (12, 11, 10, {"chips": 2, "edge": 2}),
	"CubeLargeB": (14, 10, 11, {"chips": 1, "vert": 2}),
	"CubeHugeA": (18, 15, 15, {"chips": 2, "edge": 1, "vert": 2}),
	"CubeHugeB": (20, 14, 13, {"chips": 3, "edge": 1, "bite": 1.2}),
	"TallA": (6, 6, 12, {"taper": 0.88}),
	"TallB": (8, 7, 16, {"taper": 0.86, "chips": 1}),
	"TallC": (10, 8, 20, {"taper": 0.86, "chips": 2, "vert": 2}),
	"TallD": (12, 10, 26, {"taper": 0.82, "chips": 2, "vert": 2}),
	"WideA": (14, 7, 6, {"chips": 2}),
	"WideB": (18, 9, 7, {"chips": 2, "edge": 2}),
	"WideC": (24, 10, 8, {"chips": 3, "edge": 2, "vert": 2}),
	"FlatA": (12, 9, 3, {"chips": 2, "edge": 1}),
	"FlatB": (18, 11, 4, {"chips": 3, "edge": 1}),
	"FlatC": (26, 13, 4.5, {"chips": 3, "edge": 2, "vert": 2}),
	"WedgeA": (10, 8, 8, {"ramp": 0.55, "chips": 1}),
	"WedgeB": (14, 10, 11, {"ramp": 0.6, "chips": 2}),
	"WedgeC": (20, 13, 12, {"ramp": 0.55, "tilt": (0, 0.06), "chips": 2}),
	"LeanA": (8, 7, 12, {"lean": (0.16, 0.05), "taper": 0.85}),
	"LeanB": (10, 8, 16, {"lean": (-0.2, 0.06), "taper": 0.82, "chips": 2}),
}.items():
	add("Cubes", name, [b(0, 0, L, W, H, **shape)])
add("Cubes", "NotchA", [b(-1.5, 1.5, 8, 7, 9), b(3.2, -1, 4.6, 5.5, 5.2, yaw=4), b(-2, -3.2, 5, 3.4, 4, yaw=-6)])
add("Cubes", "NotchB", [b(-2, 2, 11, 9, 13), b(4.5, -0.5, 6.5, 7.5, 7.5, yaw=-5), b(-3, -4.3, 7, 4.2, 5.4, yaw=7)])
add("Cubes", "StepA", [b(-2.5, 0, 7.5, 8, 8), b(3.5, -0.2, 6, 7.4, 4.4, yaw=3)])
add("Cubes", "StepB", [b(-4.5, 0.3, 8, 10, 11), b(1.8, 0, 6.5, 9, 7, yaw=-3), b(6.4, -0.3, 5, 8, 3.8, yaw=4)])
add("Cubes", "StepC", [b(-7, 0.5, 9, 12, 14), b(0, 0, 8, 11, 9.5, yaw=3), b(6.8, -0.3, 8, 10.5, 5, yaw=-4)])
add("Cubes", "SplitA", [b(-2.7, 0, 5, 8, 9, roll=-2, lean=(-0.03, 0)), b(2.7, 0.2, 5, 7.6, 7.6, roll=3, lean=(0.04, 0))])
add("Cubes", "SplitB", [b(-3.9, 0, 7, 10, 14, roll=-2, lean=(-0.03, 0)), b(3.9, 0.3, 7.2, 9.6, 11.5, roll=3, lean=(0.05, 0)), b(0.2, -3.6, 3, 2.6, 3.2, yaw=20)])

# ---- modular: exact sizes on a 4-stud grid, flat tops and straight sides, so they stack and line up
M = {"exact": True, "taper": 0.985, "chips": 1, "edge": 0, "vert": 1, "bite": 0.45, "bevel": (0.12, 0.34, 0.035)}
for L, W, H in ((4, 4, 4), (8, 8, 4), (8, 8, 8), (12, 12, 8), (12, 12, 12), (16, 16, 8), (16, 16, 16), (24, 12, 8), (24, 12, 12), (32, 16, 8), (32, 16, 16), (8, 4, 4), (16, 8, 4), (16, 4, 8)):
	add("Modular", f"Mod{L}x{W}x{H}", [b(0, 0, L, W, H, **M)])
add("Modular", "ModPillar8x24", [b(0, 0, 8, 8, 24, **{**M, "taper": 0.96})])
add("Modular", "ModPillar12x36", [b(0, 0, 12, 12, 36, **{**M, "taper": 0.95})])
add("Modular", "ModCap16", [b(0, 0, 16, 16, 4, **{**M, "chips": 2, "vert": 2, "bite": 0.8})])
add("Modular", "ModCap32", [b(0, 0, 32, 16, 4, **{**M, "chips": 3, "vert": 2, "bite": 0.8})])
add("Modular", "ModCorner16", [b(0, 4, 16, 8, 16, **M), b(-4, -4, 8, 8.2, 16, **M)])
add("Modular", "ModCorner24", [b(0, 6, 24, 12, 16, **M), b(-6, -6, 12, 12.2, 16, **M)])
add("Modular", "ModStep16", [b(-4, 0, 8, 16, 16, **M), b(4, 0, 8.2, 16, 8, **M)])
add("Modular", "ModStep24", [b(-8, 0, 8, 12, 12, **M), b(0, 0, 8.2, 12, 8, **M), b(8, 0, 8.2, 12, 4, **M)])
add("Modular", "ModRamp16", [b(0, 0, 16, 8, 8, ramp=0.85, **{k: v for k, v in M.items() if k != "chips"}, chips=0)])
add("Modular", "ModRamp24", [b(0, 0, 24, 12, 12, ramp=0.85, **{k: v for k, v in M.items() if k != "chips"}, chips=0)])
add("Modular", "ModEnd16", [b(0, 0, 16, 16, 16, taper=0.985, exact=True, chips=2, edge=1, vert=2, bite=2.6, bevel=M["bevel"])])
add("Modular", "ModBroken16", [b(0, 0, 16, 16, 16, taper=0.985, exact=True, chips=3, edge=2, vert=2, bite=3.4, bevel=M["bevel"])])

# ---- clusters: already composed, one piece each. Bigger and taller at the back, small ones breaking the foot in front
add("Clusters", "ClusterTallA", [b(-2, 3, 12, 9, 18, tilt=(0.02, -0.02), chips=2), b(7, 3.5, 9, 8, 14, yaw=6), b(-7.5, -1.5, 6, 6, 9.5, yaw=-8), b(-1, -3.5, 8, 6, 6.5, yaw=10), b(6, -2.5, 6.5, 5.5, 8, yaw=-6), b(11.5, -1, 5, 5, 5, yaw=14), b(2.5, -6.5, 5, 3.5, 2.6, yaw=20), b(-8.5, -5.5, 3.5, 3, 2.5, yaw=-25)])
add("Clusters", "ClusterTallB", [b(0, 2, 9, 9, 24, taper=0.88), b(-6.5, 1, 6, 7, 15, yaw=-10), b(6, 1.5, 6, 6, 18, yaw=8), b(-3, -4, 6, 5, 8, yaw=12), b(3.5, -4.5, 5, 4.5, 5.5, yaw=-14), b(9, -2, 4, 4, 6, yaw=20), b(-8, -4.5, 3.5, 3, 3)])
add("Clusters", "ClusterTallC", [b(0, 3, 14, 9, 16), b(-9, 1.5, 7, 7, 11, yaw=-7), b(8.5, 0, 7, 7, 9, yaw=9), b(1, -3.5, 9, 4.5, 7, yaw=-5), b(-5.5, -5, 5, 4, 4.5), b(5.5, -5.5, 4.5, 3.5, 3, yaw=18), b(-3, 3, 7, 6, 5, z=15, yaw=12)])
add("Clusters", "ClusterLowA", [b(-5, 1, 9, 8, 7), b(4, 2, 8, 7, 8.5, yaw=8), b(-1, -4, 7, 5, 4, yaw=-10), b(8.5, -2, 5, 5, 3.5, yaw=18), b(-9.5, -2.5, 4, 4, 3), b(3.5, -5.5, 4, 3, 2)])
add("Clusters", "ClusterLowB", [b(-9, 0, 10, 8, 5), b(0, 1, 9, 9, 7, yaw=6), b(9, 0, 10, 8, 4.5, yaw=-5), b(-4, -5, 6, 4, 2.6, yaw=12), b(5, -5, 5, 4, 3, yaw=-16), b(13, -3, 3.5, 3, 2)])
add("Clusters", "ClusterStackA", [b(0, 1, 7, 6, 7), b(-5.5, 0, 5, 5, 4.5, yaw=10), b(5.5, 0, 5, 5, 5.5, yaw=-8), b(1, 2, 5, 4.5, 4.5, z=6.6, yaw=18), b(-2, -4, 4.5, 3.5, 2.8), b(3.5, -4, 3.5, 3, 3.2, yaw=25), b(8.5, -1.5, 3, 3, 2.5), b(-7.5, -3, 3, 2.6, 2)])
add("Clusters", "ClusterStackB", [b(-3, 1, 9, 8, 9), b(5, 1, 8, 7, 7, yaw=-6), b(-2, 2, 7, 5.5, 5.5, z=8.7, yaw=14), b(-8.5, -1, 4.5, 4.5, 4), b(2, -4.5, 6, 4, 3.5, yaw=10), b(9.5, -2.5, 4, 3.5, 2.8, yaw=30)])
add("Clusters", "ClusterTwinA", [b(-6, 1, 8, 8, 15), b(6, 2, 9, 8, 19, yaw=7), b(0, -1.5, 5, 5, 6), b(-10, -2.5, 4.5, 4.5, 5), b(10.5, -2, 5, 5, 7, yaw=-9), b(1, -6, 5, 3.5, 2.6, yaw=20)])
add("Clusters", "ClusterTwinB", [b(-4, 1, 8, 8, 14, lean=(0.09, 0)), b(4.5, 1, 8, 8, 12, lean=(-0.08, 0)), b(-9, -1, 5, 5, 5), b(9, -1, 5, 5, 4), b(0, -5, 6, 4, 3)])
add("Clusters", "ClusterStepA", [b(-10, 0, 8, 8, 4), b(-3, 0.5, 8, 9, 8, yaw=4), b(4.5, 1, 8, 10, 13, yaw=-5), b(11.5, 1.5, 8, 10, 18, yaw=6), b(-4, -5.5, 5, 3, 2, yaw=14), b(6, -5.5, 4, 3, 3.5)])
add("Clusters", "ClusterWideA", [b(-13, 1, 10, 8, 10), b(-4, 2, 10, 8, 13, yaw=5), b(6, 1.5, 11, 8, 11, yaw=-4), b(15, 1, 9, 8, 8, yaw=7), b(-9, -4, 6, 4, 4.5), b(1, -4.5, 7, 4, 5.5, yaw=-8), b(11, -4, 5, 4, 3.5, yaw=12), b(18, -3.5, 3.5, 3, 2.4)])
_ring = random.Random(4)
add("Clusters", "ClusterRing", [b(math.sin(a) * 10, math.cos(a) * 10, _ring.uniform(5, 8), _ring.uniform(4.5, 6.5), _ring.uniform(3.5, 9), yaw=math.degrees(-a) + _ring.uniform(-12, 12)) for a in (k * 6.283 / 7 + 0.25 for k in range(7))])
add("Clusters", "ClusterSmallA", [b(0, 0, 5, 4.5, 4.5), b(3.8, -1, 3.2, 3, 2.6, yaw=20), b(-3.2, -1.4, 2.6, 2.4, 1.8, yaw=-12)])
add("Clusters", "ClusterSmallB", [b(0, 0, 4, 4, 6.5), b(3.4, 0, 3.5, 3.5, 3.4, yaw=12), b(-2.6, -1.6, 3, 2.6, 2.2, yaw=-15), b(1, -3, 2, 1.8, 1.2, yaw=30)])
add("Clusters", "ClusterSmallC", [b(-2, 0, 5.5, 4, 3), b(2.5, 0.5, 4.5, 4, 4.2, yaw=8), b(0, -3, 3, 2, 1.5, yaw=-20)])

# ---- boulders: more cuts, so they read as rounder
for name, (L, W, H, seedless) in {"RoundA": (4, 3.6, 2.8, 4), "RoundB": (6, 5.4, 4, 5), "RoundC": (8, 7, 5.5, 5), "RoundD": (11, 9, 7, 6), "RoundE": (15, 12, 9, 6), "RoundF": (20, 16, 12, 6)}.items():
	add("Boulders", name, [b(0, 0, L, W, H, chips=4, edge=3, vert=4, taper=0.78, bite=1.5, rough=0.07, bevel=(0.14, 1.0, 0.07))])
add("Boulders", "EggA", [b(0, 0, 6, 5, 8, chips=4, edge=3, vert=4, taper=0.66, bite=1.3, bevel=(0.14, 1.0, 0.07))])
add("Boulders", "EggB", [b(0, 0, 9, 7.5, 13, chips=4, edge=3, vert=4, taper=0.62, lean=(0.05, 0.03), bite=1.3, bevel=(0.14, 1.0, 0.07))])

# ---- slabs: flat rocks for shores and steps
for name, (L, W, H, shape) in {
	"ShelfA": (7, 4.4, 1.6, {"chips": 2}),
	"ShelfB": (11, 6.5, 2.2, {"chips": 3, "tilt": (0.14, 0.08)}),
	"ShelfC": (15, 8, 2.6, {"chips": 3, "tilt": (-0.12, 0.06), "edge": 2}),
	"ShelfD": (22, 10, 3.2, {"chips": 3, "edge": 2, "vert": 2}),
	"SteppingA": (4.5, 4, 1.1, {"chips": 3, "vert": 3, "taper": 0.86, "bite": 1.6}),
	"SteppingB": (6, 5, 1.2, {"chips": 3, "vert": 3, "taper": 0.86, "bite": 1.6}),
}.items():
	add("Slabs", name, [b(0, 0, L, W, H, **shape)])
add("Slabs", "ShelfStack", [b(0, 0, 13, 9, 2.4), b(-1, 0.5, 9, 6, 2.2, z=2.2, yaw=9), b(-1.5, 0.5, 5.5, 4, 1.8, z=4.2, yaw=-7)])
add("Slabs", "ShelfBroken", [b(-3.8, 0, 7, 8, 2.4, roll=-3, z=-0.2), b(3.4, 0.3, 6.6, 7.6, 2.2, roll=4, z=-0.2, yaw=4)])

# ---- spires and arches
add("Spires", "SpireA", [b(0, 0, 6, 5.5, 14, taper=0.6, chips=2)])
add("Spires", "SpireB", [b(0, 0, 9, 8, 24, taper=0.55, chips=2, vert=2, lean=(0.06, 0.03)), b(2.8, -1, 4.5, 4, 8, taper=0.7)])
add("Spires", "SpireC", [b(0, 0, 13, 11, 38, taper=0.5, chips=2, vert=2, lean=(-0.05, 0.03)), b(-4.4, -1.4, 7, 6, 14, taper=0.7, yaw=10), b(4.5, 0.5, 5.6, 5.6, 9, taper=0.75, yaw=-14)])
add("Spires", "FangA", [b(0, 0, 7, 6, 18, taper=0.42, lean=(0.26, 0.04), chips=1)])
add("Spires", "FangB", [b(0, 0, 10, 8, 26, taper=0.4, lean=(-0.3, 0.05), chips=2), b(-3, 0, 5, 5, 8, taper=0.7, yaw=12)])
add("Spires", "NeedleGroup", [b(-3, 0, 4.5, 4.5, 20, taper=0.5), b(2.2, 1, 4, 4, 14, taper=0.52, yaw=20), b(0, -3, 3.4, 3.4, 9, taper=0.55, yaw=-14), b(4.8, -2, 2.6, 2.6, 5, taper=0.6)])
add("Spires", "ArchSmall", [b(-8, 0, 6, 7, 14, taper=0.94), b(8, 0, 6, 7, 13, taper=0.94, yaw=5), b(0, 0, 22, 7.5, 5.4, z=12.4, roll=2, chips=2)])
add("Spires", "ArchLow", [b(-5.5, 0, 5, 6, 7.5), b(5.5, 0, 5, 6, 7, yaw=-5), b(0, 0, 15, 6.5, 4, z=6.4, roll=-2, chips=2)])
add("Spires", "Gateposts", [b(-9, 0, 5, 5, 15, taper=0.82, chips=2), b(9, 0, 5, 5, 13, taper=0.8, yaw=9, chips=2), b(-5.4, -1.6, 3, 3, 3, yaw=18), b(6, -1.8, 2.6, 2.6, 2.2, yaw=-20)])

# ---- chips: little stones, to break up edges
add("Chips", "PebbleA", [b(0, 0, 1.6, 1.3, 0.8, chips=3, vert=3, taper=0.76, bite=1.5)])
add("Chips", "PebbleB", [b(0, 0, 2.4, 1.9, 1.2, chips=3, vert=3, taper=0.76, bite=1.5)])
add("Chips", "ChipCube", [b(0, 0, 2.6, 2.4, 2.2, chips=2)])
add("Chips", "ChipFlatA", [b(0, 0, 3.4, 2.4, 0.8, chips=2)])
add("Chips", "ChipWedge", [b(0, 0, 3, 2.4, 2.2, ramp=0.6, chips=1)])
add("Chips", "ChipTallA", [b(0, 0, 1.8, 1.6, 3.2, taper=0.72, chips=2)])
_s = random.Random(9)
for name, count, spread in (("ScatterA", 6, 5.0), ("ScatterB", 9, 8.0), ("ScatterC", 13, 12.0)):
	add("Chips", name, [b(_s.uniform(-spread, spread), _s.uniform(-spread * 0.6, spread * 0.6), _s.uniform(0.9, 2.4), _s.uniform(0.8, 2.0), _s.uniform(0.5, 1.3), yaw=_s.uniform(0, 180), chips=3, vert=2, taper=0.76, bite=1.5) for _ in range(count)])


# ---- cliffs: big pieces for rock faces, front at -Y. Scale them up in Studio for more; painted at about 8 texels a stud
def face_detail(big, seed, count):
	"""blocks standing in front of a big lump, from its base up, so it reads as a huge rock rather than a small one scaled up"""
	r = random.Random(seed)
	out = []
	for _ in range(count):
		w, h, d = r.uniform(0.24, 0.5) * big["L"], r.uniform(0.3, 0.72) * big["H"], r.uniform(2.5, 6)
		x = big["x"] + r.uniform(-0.4, 0.4) * big["L"]
		front = big["y"] - big["W"] / 2
		out.append(b(x, front + (5 - d) / 2, w, d + 5, h, z=big["z"], yaw=r.uniform(-6, 6), chips=3, edge=2, taper=0.8, tilt=(r.uniform(-0.08, 0.08), r.uniform(-0.03, 0.08)), bite=1.2))
	return out


def foot(L, front, seed, count, height=5.0):
	"""low blocks along a cliff's foot"""
	r = random.Random(seed)
	return [b(r.uniform(-L * 0.48, L * 0.48), front - r.uniform(0, 3), r.uniform(4, 11), r.uniform(3.5, 6.5), r.uniform(1.6, height), yaw=r.uniform(-22, 22), chips=2) for _ in range(count)]


def columns(L, W, H, count, seed, low=0.55, shape=None):
	r = random.Random(seed)
	share = [r.uniform(0.45, 1.5) for _ in range(count)]
	total = sum(share)
	x = -L / 2
	out = []
	for k, s in enumerate(share):
		w = L * s / total
		envelope = 0.72 + 0.28 * math.sin(k / max(1, count - 1) * math.pi)
		h = H * envelope * r.uniform(low + (1 - low) * 0.35, 1.0)
		d = W * r.uniform(0.7, 1.0)
		lower = h * r.uniform(0.42, 0.74)
		out.append(b(x + w / 2, (W - d) / 2, w * 1.06, d, lower, yaw=r.uniform(-3, 3), taper=0.97, chips=1, edge=1, **(shape or {})))
		out.append(b(x + w / 2 + r.uniform(-0.05, 0.05) * w, (W - d) / 2 + r.uniform(0, 2), w * r.uniform(0.82, 1.0), d * 0.94, h - lower + 1, z=lower - 1, yaw=r.uniform(-5, 5), taper=0.86, chips=2, edge=1, tilt=(r.uniform(-0.1, 0.1), r.uniform(-0.04, 0.08)), **(shape or {})))
		if r.random() < 0.62:
			out.append(b(x + w / 2 + r.uniform(-1, 1), (W - d) / 2 - d / 2 + 1, w * r.uniform(0.55, 0.9), r.uniform(4, 7), h * r.uniform(0.2, 0.42), yaw=r.uniform(-8, 8), chips=2))
		x += w
	return out


def strata(L, W, H, layers, seed, setback=2.2):
	"""level beds of rock, each set back from the one below, split into a few blocks"""
	r = random.Random(seed)
	out = []
	z = 0.0
	for k in range(layers):
		h = H / layers * r.uniform(0.8, 1.2)
		x = -L / 2 * (1 - k * 0.03)
		right = L / 2 * (1 - k * 0.04)
		while x < right - 2:
			w = r.uniform(0.18, 0.36) * L
			w = min(w, right - x + 1)
			d = W - k * setback + r.uniform(-2.2, 2.2)
			y = (W - d) / 2
			out.append(b(x + w / 2, y, w * 1.03, d, h * r.uniform(0.92, 1.08) + 0.5, z=z, yaw=r.uniform(-1.6, 1.6), taper=0.97, chips=1, edge=1, vert=1, bite=0.7))
			x += w
		z += h
	return out


A = b(-15, 2, 30, 22, 38, tilt=(0.03, -0.02), chips=2)
B = b(16, 3, 30, 20, 30, yaw=-4, chips=2)
add("Cliffs", "CliffSlabA", [A, B, b(1, -7, 18, 8, 14, yaw=4), b(-21, -8, 12, 7, 8, yaw=-6), b(24, -8, 12, 6, 6, yaw=9)] + face_detail(A, 3, 2) + face_detail(B, 4, 2))
A = b(0, 0, 44, 24, 44, taper=0.88, chips=3, edge=2, vert=2, bite=1.1)
add("Cliffs", "CliffSlabB", [A] + face_detail(A, 5, 4) + foot(44, -12, 6, 7))
add("Cliffs", "CliffColumnsA", columns(60, 22, 54, 9, 7))
add("Cliffs", "CliffColumnsB", columns(38, 18, 72, 6, 8, low=0.66))
add("Cliffs", "CliffStrataA", strata(64, 26, 38, 5, 9) + foot(64, -13, 10, 6))
add("Cliffs", "CliffStrataB", strata(48, 26, 58, 7, 11, 1.8))
A, B, C = b(0, 8, 60, 16, 36, chips=2), b(0, -6, 62, 14, 22, chips=2, yaw=1), b(0, -18, 64, 11, 10, chips=2, yaw=-1)
add("Cliffs", "CliffTerrace", [A, B, C] + face_detail(A, 12, 2) + face_detail(B, 13, 2) + face_detail(C, 14, 2))
A = b(0, -2, 26, 30, 62, taper=0.72, chips=3, edge=2, vert=2)
L_, R_ = b(-20, 5, 18, 18, 42, yaw=-5, taper=0.86), b(20, 6, 18, 16, 36, yaw=6, taper=0.86)
add("Cliffs", "CliffButtress", [A, L_, R_] + face_detail(A, 15, 3) + face_detail(L_, 16, 1) + face_detail(R_, 17, 1) + foot(46, -15, 18, 5, 7))
A, B = b(-2, 14, 44, 16, 44, chips=2), b(14, -6, 16, 28, 40, chips=2, yaw=-3)
add("Cliffs", "CliffCornerOut", [A, B, b(16, 12, 16, 18, 46, chips=3, vert=3, bite=1.8)] + face_detail(A, 19, 2) + foot(40, 3, 20, 4))
A, B = b(0, 16, 44, 14, 44, chips=2), b(-16, -4, 14, 28, 42, chips=2, yaw=3)
add("Cliffs", "CliffCornerIn", [A, B, b(-14, 13, 16, 16, 48, chips=2)] + face_detail(A, 21, 2) + foot(36, 4, 22, 5))
A, B = b(0, 6, 52, 20, 26, taper=0.96, chips=2), b(0, -2, 56, 30, 20, z=24, chips=3, edge=2, tilt=(0.02, 0.03))
add("Cliffs", "CliffOverhang", [A, B, b(-18, -6, 10, 8, 26, yaw=-5), b(14, -6, 8, 7, 18, yaw=8), b(-2, -9, 7, 5, 8)] + face_detail(A, 23, 2))
_c = random.Random(24)
add("Cliffs", "CliffCrag", [b(x, _c.uniform(-2, 3), _c.uniform(12, 18), _c.uniform(16, 24), _c.uniform(26, 56), yaw=_c.uniform(-5, 5), taper=0.55, ramp=_c.uniform(0.12, 0.3), lean=(_c.uniform(-0.1, 0.1), 0), chips=2, vert=2) for x in (-24, -14, -5, 5, 14, 24)] + foot(58, -11, 25, 7, 6))
A, B = b(-17, 0, 14, 20, 26, taper=0.94, chips=2), b(17, 0, 14, 20, 24, taper=0.94, chips=2, yaw=4)
C = b(0, 0, 50, 22, 16, z=22, chips=3, edge=2, roll=1, tilt=(0.02, 0))
add("Cliffs", "CliffArch", [A, B, C, b(-24, -2, 8, 8, 10, yaw=9), b(25, -2, 7, 8, 8, yaw=-6)] + face_detail(C, 26, 2))
add("Cliffs", "CliffShelf", [b(-16, 0, 22, 16, 9, tilt=(0, 0.02), chips=3), b(3, 0.4, 20, 15, 10, yaw=2, chips=3), b(20, 0, 16, 14, 8, yaw=-3, chips=3)])
add("Cliffs", "CliffCap", [b(-17, 0, 24, 22, 11, chips=3, edge=2), b(4, 1, 22, 24, 13, yaw=3, chips=3, edge=2), b(23, -1, 18, 20, 9, yaw=-4, chips=3, edge=2), b(-6, 0, 14, 12, 5, z=10, yaw=10), b(14, 2, 12, 10, 4, z=12, yaw=-9)])
add("Cliffs", "CliffFoot", foot(66, 2, 27, 16, 10) + foot(66, -5, 28, 11, 5))
A = b(0, 0, 22, 20, 44, taper=0.8, chips=2, vert=2)
add("Cliffs", "CliffSpire", [A, b(1, 0, 16, 15, 28, z=41, taper=0.72, chips=2, yaw=8), b(0.5, 0.5, 10, 10, 18, z=66, taper=0.55, chips=2, yaw=-7), b(-13, -3, 9, 9, 16, yaw=-8), b(12, -2, 8, 9, 11, yaw=9)] + face_detail(A, 29, 2))
_m = random.Random(30)
add("Cliffs", "CliffMesa", [b(0, 0, 52, 44, 32, taper=0.86, chips=3, edge=1, vert=3), b(-4, 3, 40, 32, 5, z=31, chips=3, edge=2, yaw=4)] + [b(math.sin(a) * 27, math.cos(a) * 23, _m.uniform(10, 18), _m.uniform(8, 12), _m.uniform(9, 24), yaw=math.degrees(-a) + _m.uniform(-9, 9), chips=2) for a in (k * 6.283 / 9 + 0.3 for k in range(9))])
add("Cliffs", "CliffWallLong", columns(112, 24, 40, 9, 31, low=0.7) + foot(112, -11, 32, 9))
A, B, C = b(0, 2, 40, 24, 46, chips=2, taper=0.94), b(-2, 5, 32, 19, 34, z=44, yaw=3, chips=2, taper=0.92), b(3, 7, 22, 14, 24, z=76, yaw=-5, chips=3, taper=0.82)
add("Cliffs", "CliffTall", [A, B, C] + face_detail(A, 33, 2) + face_detail(B, 34, 2) + face_detail(C, 35, 1))
_b = random.Random(36)
add("Cliffs", "CliffBroken", [b(_b.uniform(-24, 24), _b.uniform(-13, 13), _b.uniform(11, 20), _b.uniform(10, 16), _b.uniform(8, 16), z=-1.5, yaw=_b.uniform(0, 180), pitch=_b.uniform(-13, 13), roll=_b.uniform(-13, 13), chips=3, edge=1) for _ in range(11)] + foot(56, -13, 37, 5))
A, B = b(-17, 0, 24, 24, 50, chips=2, roll=-1, taper=0.9), b(17, 1, 24, 22, 44, chips=2, roll=1, taper=0.9, yaw=3)
add("Cliffs", "CliffSplit", [A, B, b(0, 8, 10, 8, 18, yaw=8), b(-1, 7, 6, 6, 8, z=17, yaw=-6)] + face_detail(A, 38, 2) + face_detail(B, 39, 2) + foot(52, -13, 40, 5))

# ---- the earlier kit's approved shapes and the natural rocks, into the same paint
for name in old.SPECS:
	add("Classic", name, None)
NATURAL_NAMES = ("NatPebble", "NatStone", "NatRound", "NatChunk", "NatFlat", "NatLong", "NatBlock", "NatTall", "NatWall", "NatWide", "NatCrag", "NatLong2")
for name in NATURAL_NAMES:
	add("Natural", name, None)


# the pack: 50 pieces, the user's number. --all builds everything defined above (about 170), to pick from
KEEP = (
	"ClusterTallA", "ClusterTallB", "ClusterTallC", "ClusterLowA", "ClusterLowB", "ClusterStackA", "ClusterTwinA", "ClusterStepA", "ClusterWideA", "ClusterSmallA", "ClusterSmallB",
	"CubeSmallA", "CubeA", "CubeLargeA", "CubeHugeA", "TallB", "TallD", "WideB", "WedgeB", "NotchB", "SplitB",
	"Mod8x8x8", "Mod16x16x8", "Mod16x16x16", "Mod32x16x8", "ModCorner16", "ModStep16",
	"CliffSlabA", "CliffColumnsA", "CliffStrataA", "CliffTerrace", "CliffButtress", "CliffCornerOut", "CliffOverhang", "CliffCrag", "CliffArch", "CliffWallLong", "CliffFoot",
	"RoundC", "RoundE", "ShelfB", "ShelfStack", "SpireB", "ScatterB",
	"WallWide", "WallStep", "FootWide", "SlabLong", "BoulderWide", "Corner",
)
assert len(KEEP) == 50 and all(n in PIECES for n in KEEP)
if "--all" not in ARGS:
	PIECES = {n: PIECES[n] for n in KEEP}


def seed_of(name):
	return zlib.crc32(name.encode()) % 100000


def classic_lumps(name):
	size, seed, big, lumps = old.SPECS[name]
	out = []
	for j, (lx, ly, sx, sy, sz) in enumerate(lumps):
		off = Vector((lx * size[0], ly * size[1], 0))
		taper, lean = old.SHAPE.get(name, (1.0, (0.0, 0.0)))
		bm, planes = old.rock_bmesh((size[0] * sx, size[1] * sy, size[2] * sz), seed + j * 37, big if j == 0 else 1, taper, lean)
		bmesh.ops.translate(bm, vec=off, verts=list(bm.verts))
		out.append((bm, [(n, q + off) for n, q in planes]))
	return out


def bounds(planes):
	"""a loose box round a lump, from its plane points (only for skipping far-off lumps)"""
	xs = [q for _, q in planes]
	return Vector((min(q.x for q in xs), min(q.y for q in xs), min(q.z for q in xs))), Vector((max(q.x for q in xs), max(q.y for q in xs), max(q.z for q in xs)))


def build():
	os.makedirs(OUT, exist_ok=True)
	only = set(option("--only").split(",")) if option("--only") else None
	names = [n for n in PIECES if not only or n in only]
	if any(PIECES[n][0] == "Natural" for n in names):
		with bpy.data.libraries.load(NATURAL) as (src, dst):
			dst.meshes = [m for m in src.meshes if m in NATURAL_NAMES]
	sc = bpy.context.scene
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	joined = bmesh.new()
	piece = joined.faces.layers.int.new("piece")
	bevel = joined.faces.layers.int.new("bevel")
	sub = joined.faces.layers.int.new("sub")
	x = 0.0
	offsets, sizes, areas = {}, {}, {}
	for k, name in enumerate(names):
		group, lumps = PIECES[name]
		if group == "Natural":
			temp = bmesh.new()
			temp.from_mesh(bpy.data.meshes[name])
			bpy.data.meshes.remove(bpy.data.meshes[name])  # or the piece's own mesh would come out named <name>.001
			built = [(temp, [])]
		elif group == "Classic":
			built = classic_lumps(name)
		else:
			segments = 1 if group == "Cliffs" else 2
			built = [build_lump(s, seed_of(name) + j * 37, segments) for j, s in enumerate(lumps)]
		boxes = [bounds(pl) if pl else None for _, pl in built]
		lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
		for bm, _ in built:
			for v in bm.verts:
				for a in range(3):
					lo[a] = min(lo[a], v.co[a])
					hi[a] = max(hi[a], v.co[a])
		centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0))
		width = hi.x - lo.x
		x += width / 2 + 6
		offsets[name] = x
		sizes[name] = [width, hi.y - lo.y, hi.z]
		area = 0.0
		for j, (bm, _) in enumerate(built):
			src = bm.faces.layers.int["bevel"]
			src_sub = bm.faces.layers.int.get("sub")
			others = [(pl, boxes[i]) for i, (_, pl) in enumerate(built) if i != j and pl]
			vm = {}
			for f in bm.faces:
				co = [v.co for v in f.verts]
				inside = False
				for pl, (a, c) in others:
					if all(a.x <= q.x <= c.x and a.y <= q.y <= c.y and a.z <= q.z <= c.z for q in co) and all(all((q - p).dot(n) < 0 for n, p in pl) for q in co):
						inside = True
						break
				if inside:
					continue
				for v in f.verts:
					if v not in vm:
						vm[v] = joined.verts.new(v.co - centre + Vector((x, 0, 0)))
				nf = joined.faces.new([vm[v] for v in f.verts])
				nf[piece], nf[bevel], nf[sub] = k, f[src], f[src_sub] if src_sub else j
				area += f.calc_area()
			bm.free()
		areas[name] = area
		x += width / 2 + 6
	joined.normal_update()
	me = bpy.data.meshes.new("RockPackAll")
	joined.to_mesh(me)
	joined.free()
	obj = bpy.data.objects.new("RockPackAll", me)
	sc.collection.objects.link(obj)
	bpy.context.view_layer.objects.active = obj
	obj.select_set(True)
	# sheets, per group: as many as it takes to keep the group's texels a stud
	sheets = {}
	sheet_of = {}
	groups = sorted({PIECES[n][0] for n in names}, key=list(DENSITY).index)
	for group in groups:
		limit = SHEET_FILL * 1024 * 1024 / DENSITY[group] ** 2
		bins = []
		for n in sorted((n for n in names if PIECES[n][0] == group), key=lambda n: -areas[n]):
			for bin_ in bins:
				if bin_[0] + areas[n] <= limit:
					bin_[0] += areas[n]
					bin_[1].append(n)
					break
			else:
				bins.append([areas[n], [n]])
		for i, (_, ns) in enumerate(bins):
			label = f"{group}{i + 1:02d}"
			sheets[label] = {names.index(n) for n in ns}
			for n in ns:
				sheet_of[n] = label
	old.layout_uvs(me, sheets)
	me.calc_loop_triangles()
	uvd = me.uv_layers.active.data
	pa, ba, sa = me.attributes["piece"].data, me.attributes["bevel"].data, me.attributes["sub"].data
	pos, uv, nor, pc, bv, fc, sb = [], [], [], [], [], [], []
	for t in me.loop_triangles:
		pos.append([me.vertices[v].co[:] for v in t.vertices])
		uv.append([uvd[li].uv[:] for li in t.loops])
		nor.append(me.polygons[t.polygon_index].normal[:])
		pc.append(pa[t.polygon_index].value)
		bv.append(ba[t.polygon_index].value)
		fc.append(t.polygon_index)
		sb.append(sa[t.polygon_index].value)
	np.savez_compressed(os.path.join(OUT, "bake.npz"), pos=np.array(pos, np.float32), uv=np.array(uv, np.float32), nor=np.array(nor, np.float32), piece=np.array(pc), bevel=np.array(bv), face=np.array(fc), sub=np.array(sb), names=np.array(names), sheet=np.array([sheet_of[n] for n in names]), group=np.array([PIECES[n][0] for n in names]), offset=np.array([offsets[n] for n in names]), height=np.array([sizes[n][2] for n in names]))
	# the pieces, back at their own origins, sharing their sheets. Split by a fast pass over the mesh's arrays
	meta = {}
	polys = me.polygons
	piece_ids = np.zeros(len(polys), np.int32)
	pa.foreach_get("value", piece_ids)
	by_piece = {k: [] for k in range(len(names))}
	for i, pid in enumerate(piece_ids):
		by_piece[int(pid)].append(i)
	coords = [v.co.copy() for v in me.vertices]
	uvs = [d.uv.copy() for d in uvd]
	for k, name in enumerate(names):
		vmap, verts, faces, face_uvs = {}, [], [], []
		for i in by_piece[k]:
			p = polys[i]
			row = []
			for li in p.loop_indices:
				v = me.loops[li].vertex_index
				if v not in vmap:
					vmap[v] = len(verts)
					verts.append((coords[v].x - offsets[name], coords[v].y, coords[v].z))
				row.append(vmap[v])
				face_uvs.append(uvs[li])
			faces.append(row)
		pm = bpy.data.meshes.new(name)
		pm.from_pydata(verts, [], faces)
		layer = pm.uv_layers.new(name="UV")
		for li, value in enumerate(face_uvs):
			layer.data[li].uv = value
		old.smooth_area_weighted(pm)
		sc.collection.objects.link(bpy.data.objects.new(name, pm))
		pm.calc_loop_triangles()
		meta[name] = {"Group": PIECES[name][0], "Size": [round(s, 1) for s in sizes[name]], "Tris": len(pm.loop_triangles), "Sheet": sheet_of[name]}
	bpy.data.objects.remove(obj)
	json.dump(meta, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "rock_pack.blend"))
	count = {}
	for m in meta.values():
		count[m["Group"]] = count.get(m["Group"], 0) + 1
	print("[pack]", len(meta), "pieces", count, "tris", sum(m["Tris"] for m in meta.values()), "sheets", len(sheets), flush=True)


def material(sheet, variant):
	m = bpy.data.materials.new(f"Pack{sheet}{variant}")
	m.use_nodes = True
	m.use_backface_culling = True  # Roblox hides back faces: see them as Roblox would
	nt = m.node_tree
	p = nt.nodes["Principled BSDF"]
	p.inputs["Roughness"].default_value = 0.85
	p.inputs["Specular IOR Level"].default_value = 0.2
	im = nt.nodes.new("ShaderNodeTexImage")
	im.image = bpy.data.images.load(os.path.join(OUT, f"Pack_{sheet}_{variant}.png"))
	nt.links.new(im.outputs["Color"], p.inputs["Base Color"])
	return m


def render():
	which, variant = ARGS[1], ARGS[2]
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "rock_pack.blend"))
	sc = bpy.context.scene
	meta = json.load(open(os.path.join(OUT, "kit.json")))
	mats = {}
	for name, m in meta.items():
		me = bpy.data.meshes[name]
		me.materials.clear()
		if m["Sheet"] not in mats:
			mats[m["Sheet"]] = material(m["Sheet"], variant)
		me.materials.append(mats[m["Sheet"]])
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	old.stage(sc)
	line = bpy.data.collections.new("Lineup")
	sc.collection.children.link(line)
	old.ground_plane(line, "2bab5e")
	bpy.data.objects["Floor"].scale = (20, 20, 1)
	groups = sorted({m["Group"] for m in meta.values()}, key=list(DENSITY).index) if which == "all" else [which]
	for group in groups:
		names = [n for n, m in meta.items() if m["Group"] == group]
		names.sort(key=lambda n: meta[n]["Size"][0] * meta[n]["Size"][1] * meta[n]["Size"][2])
		total = sum(meta[n]["Size"][0] + 3 for n in names)
		row_width = max(max(meta[n]["Size"][0] for n in names) + 3, math.sqrt(total * max(meta[n]["Size"][1] + 6 for n in names)) * 1.5)
		rows, cur, used = [], [], 0.0
		for n in names:
			w = meta[n]["Size"][0] + 3
			if cur and used + w > row_width:
				rows.append(cur)
				cur, used = [], 0.0
			cur.append(n)
			used += w
		rows.append(cur)
		y = 0.0
		placed = []
		for row in rows:
			x = -sum(meta[n]["Size"][0] + 3 for n in row) / 2
			depth = max(meta[n]["Size"][1] for n in row)
			for n in row:
				x += meta[n]["Size"][0] / 2 + 1.5
				placed.append(old.place(line, n, x, y + depth / 2, 0.0))
				x += meta[n]["Size"][0] / 2 + 1.5
			y += depth + 6
		hero = kit.hero("Hero", 7, line)
		hero.location = (-row_width / 2 - 2, -3, 0)
		width = max(sum(meta[n]["Size"][0] + 3 for n in row) for row in rows) + 8
		tallest = max(meta[n]["Size"][2] for n in names)
		frame = max(width, (y + tallest) * 1.5)
		dist = frame * 0.5 / math.tan(math.radians(40 * 16 / 9 / 2 * 0.9)) + 6
		cam = (0, -dist * 0.86, dist * 0.42)
		for o in list(bpy.data.objects):
			if o.type == "CAMERA":
				bpy.data.objects.remove(o)
		old.camera(sc, cam, (0, y * 0.42, tallest * 0.25), 40)
		sc.render.filepath = os.path.join(OUT, f"lineup_{group}_{variant}.png")
		bpy.ops.render.render(write_still=True)
		for o in placed:
			bpy.data.objects.remove(o)
		bpy.data.objects.remove(hero)
		print("[pack] rendered", group, flush=True)


def export():
	"""all the pieces into one glb for upload: each its own MeshPart, named after its mesh"""
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "rock_pack.blend"))
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "RockPack.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	print("[pack] exported", len(bpy.data.objects), flush=True)


if __name__ == "__main__":
	if ARGS[0] == "build":
		build()
	elif ARGS[0] == "render":
		render()
	elif ARGS[0] == "export":
		export()
