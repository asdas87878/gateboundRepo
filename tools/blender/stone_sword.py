"""A giant stone sword stuck in the ground, after the user's concept (docs/style/stone-sword.md). Geometry, UVs and previews; the paint is tools/art/paint_sword.py.

  blender --background --python tools/blender/stone_sword.py -- build             art/kit/sword/sword.blend, bake.npz + layout.json for the painter
  blender --background --python tools/blender/stone_sword.py -- render <tag>      views_<tag>_*.png (clay until the sheets exist)
  blender --background --python tools/blender/stone_sword.py -- export            StoneSword.glb, each part a MeshPart

Units are studs. x is across the blade, -y is the front, z is up, the ground is z = 0.
Each face is projected flat onto a canvas (front, back, right, left, up, down; a wrap for the grip), so the painter's strokes run straight along the blade.
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rock_kit as old  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "sword")
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["build"]

W = 20.0  # blade width
LB = 116.0  # blade seen above the ground
BURY = 12.0
OUTLINE = 0.42  # ink thickness, studs
SHEET = 1024
PAD = 10
CUTS = (LB / 3, 2 * LB / 3)
BLADE_PARTS = ("BladeLow", "BladeMid", "BladeTop")
GRIP_R = 0.235 * W


def wobble(seed, length):
	"""a smooth bend, about -1..1, that never repeats exactly"""
	r = random.Random(seed)
	waves = [(r.uniform(0.7, 1.3) * 2 * math.pi / (length / (k + 1)), r.uniform(0, 6.28), 1 / (k + 1)) for k in range(3)]
	return lambda x: sum(a * math.sin(f * x + p) for f, p, a in waves) / 1.5


W_RIGHT, W_LEFT, W_RIDGE, W_T, W_TB = (wobble(s, 95) for s in (11, 12, 13, 14, 15))


def blade_section(z):
	"""ten corners round the blade at a height: a ridge down each side's middle, two big faces, a blunt bevelled edge"""
	k = (z + BURY) / (LB + BURY)
	right = W / 2 * (0.85 + 0.15 * k) * (1 + 0.022 * W_RIGHT(z))
	left = W / 2 * (0.85 + 0.15 * k) * (1 + 0.022 * W_LEFT(z))
	cx = 0.02 * W * math.sin(z / LB * 2.4 + 0.7)
	rx = cx + 0.022 * W * W_RIDGE(z)
	t = W * 0.165 * (0.86 + 0.14 * k) * (1 + 0.05 * W_T(z))
	tb = W * 0.165 * (0.86 + 0.14 * k) * (1 + 0.05 * W_TB(z))
	e, f, b = 0.072 * W, 0.04 * W, 0.055 * W
	return [(rx, -t), (cx + right - b, -e), (cx + right, -f), (cx + right, f), (cx + right - b, e), (rx, tb), (cx - left + b, e), (cx - left, f), (cx - left, -f), (cx - left + b, -e)]


def to_object(bm, name):
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	return obj


def hull(points):
	bm = bmesh.new()
	verts = [bm.verts.new(q) for q in points]
	res = bmesh.ops.convex_hull(bm, input=verts)
	bmesh.ops.delete(bm, geom=[v for v in set(res["geom_interior"]) | set(res["geom_unused"]) if isinstance(v, bmesh.types.BMVert)], context="VERTS")
	return bm


def cutter(rng, centre, radii, count=14):
	"""a chunky random solid: what it takes out of the stone is a chip with flat chiselled sides"""
	points = []
	for _ in range(count):
		v = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
		points.append(Vector((centre[0] + v.x * radii[0], centre[1] + v.y * radii[1], centre[2] + v.z * radii[2])))
	return hull(points)


def carve(obj, cutters):
	bpy.context.view_layer.objects.active = obj
	for bm_c in cutters:
		c = to_object(bm_c, "Cutter")
		mod = obj.modifiers.new("Cut", "BOOLEAN")
		mod.operation = "DIFFERENCE"
		mod.solver = "EXACT"
		mod.object = c
		bpy.ops.object.modifier_apply(modifier=mod.name)
		me = c.data
		bpy.data.objects.remove(c)
		bpy.data.meshes.remove(me)


def build_blade():
	rng = random.Random(41)
	bm = bmesh.new()
	zs, z = [-BURY], -BURY
	while z < LB + 2:
		z += rng.uniform(9, 15)
		zs.append(z)
	zs[-1] = LB + 5
	rings = [[bm.verts.new((x, y, q)) for x, y in blade_section(q)] for q in zs]
	n = len(rings[0])
	for a, b in zip(rings, rings[1:]):
		for i in range(n):
			j = (i + 1) % n
			bm.faces.new((a[i], a[j], b[j], b[i]))
	bm.faces.new(rings[0][::-1])
	bm.faces.new(rings[-1])
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	obj = to_object(bm, "Blade")

	cutters = []
	# chips out of the two long edges, more and bigger toward the foot
	for side in (1, -1):
		z = rng.uniform(3, 9)
		while z < LB - 6:
			foot = 1 - z / LB
			c = blade_section(z)
			edge = c[2][0] if side > 0 else c[8][0]
			big = rng.uniform(0.7, 1.3 + 0.8 * foot)
			cutters.append(cutter(rng, (edge + side * 0.35, rng.uniform(-1.2, 1.2), z), (big, rng.uniform(2.4, 4.0), rng.uniform(2.5, 5 + 4 * foot))))
			z += rng.uniform(24, 52)
	uncut = obj.data.copy()
	carve(obj, cutters)
	return obj, uncut


def inset(points, amount):
	"""the outline moved inward; points run anticlockwise seen from the front (-y), as (x, z)"""
	out = []
	n = len(points)
	for i in range(n):
		ax, az = points[i - 1]
		bx, bz = points[i]
		cx, cz = points[(i + 1) % n]
		n1 = Vector((bz - az, -(bx - ax))).normalized()
		n2 = Vector((cz - bz, -(cx - bx))).normalized()
		m = (n1 + n2)
		if m.length < 1e-4:
			m = n1
		m = m.normalized()
		miter = min(amount / max(m.dot(n1), 0.3), amount * 2)
		out.append((bx - m.x * miter, bz - m.y * miter))
	return out


def prism(outline, thick, chamfer, bm=None):
	"""a thick slab from an outline: two rings each side make a soft rounded edge. thick(x, z) is the half thickness"""
	bm = bm or bmesh.new()
	profile = [(0.0, chamfer), (0.42 * chamfer, 0.34 * chamfer), (chamfer, 0.0)]  # how far in, how far back from the face
	rings_f = []
	rings_b = []
	for amount, back in profile:
		pts = inset(outline, amount) if amount else outline
		# a folded ring means wrong-facing triangles in the face: holes in Roblox
		n = len(pts)
		for i in range(n):
			j = (i + 1) % n
			a = (outline[j][0] - outline[i][0], outline[j][1] - outline[i][1])
			b = (pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
			assert a[0] * b[0] + a[1] * b[1] > 0, f"inset folds at corner {i}: an edge is shorter than the chamfer"
		rings_f.append([bm.verts.new((x, -(thick(x, z) - back), z)) for x, z in pts])
		rings_b.append([bm.verts.new((x, thick(x, z) - back, z)) for x, z in pts])
	n = len(outline)
	stack = rings_f[::-1] + rings_b
	for a, b in zip(stack, stack[1:]):
		for i in range(n):
			j = (i + 1) % n
			bm.faces.new((a[i], a[j], b[j], b[i]))
	front = bm.faces.new(rings_f[-1])  # anticlockwise from the front faces -y
	back_face = bm.faces.new(rings_b[-1][::-1])
	# triangulating uses the face's stored normal: without it a concave outline fills wrongly, with triangles outside it and holes inside
	front.normal_update()
	back_face.normal_update()
	made = bmesh.ops.triangulate(bm, faces=[front, back_face], quad_method="BEAUTY", ngon_method="EAR_CLIP")["faces"]
	bm.normal_update()
	for f in made:
		assert abs(f.normal.y) < 1e-3 or (f.calc_center_median().y < 0) == (f.normal.y < 0), "a triangle in the face points inward"
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	return bm


def build_guard():
	rng = random.Random(53)
	u = W
	right = [(0.94, -0.1), (1.06, -0.09), (1.14, 0.06), (1.14, 0.3), (1.04, 0.46), (0.9, 0.48), (0.72, 0.45), (0.5, 0.46), (0.22, 0.5), (0.0, 0.51)]
	under = [(0.0, -0.56), (0.14, -0.43), (0.29, -0.27), (0.43, -0.06), (0.6, -0.01), (0.76, -0.03)]
	# anticlockwise from the tongue's point: right along the underside, round the right end, along the top, then the left mirrored
	half = under + right[:-1]
	points = [(x * u + rng.uniform(-0.25, 0.25), LB + z * u + rng.uniform(-0.2, 0.2)) for x, z in half]
	points.append((0.0 + rng.uniform(-0.2, 0.2), LB + 0.51 * u))
	left = [(-x, z) for x, z in half[1:]][::-1]
	points += [(x * u + rng.uniform(-0.25, 0.25), LB + (z - 0.015) * u + rng.uniform(-0.2, 0.2)) for x, z in left]

	def thick(x, z):
		return W * 0.285

	obj = to_object(prism(points, thick, 0.08 * W), "Guard")
	uncut = obj.data.copy()
	cutters = []
	for x, z, rx, rz in ((1.08, 0.44, 2.4, 2.0), (-1.1, -0.06, 2.4, 2.2), (0.66, 0.47, 2.8, 1.5), (-0.6, 0.47, 3.4, 1.4), (-1.08, 0.42, 2.0, 2.4)):
		for sign in (-1, 1):
			if rng.random() < 0.72:
				cutters.append(cutter(rng, (x * u, sign * rng.uniform(2.0, 4.6), LB + z * u), (rx, rng.uniform(1.8, 3.2), rz)))
	carve(obj, cutters)
	return obj, uncut


def build_hilt():
	rng = random.Random(67)
	u = W
	base = LB + 0.38 * u
	profile = [
		(-0.04, 0.24), (0.05, 0.26), (0.09, 0.315), (0.2, 0.32), (0.25, 0.265),
		(0.45, 0.25), (0.7, 0.242), (0.94, 0.232), (0.98, 0.278), (1.1, 0.284), (1.14, 0.232),
		(1.34, 0.222), (1.62, 0.212), (1.66, 0.262), (1.77, 0.268), (1.84, 0.2), (1.92, 0.16),
	]  # fmt: skip
	sides = 16
	bm = bmesh.new()
	rings = []
	for h, radius in profile:
		cx = 0.018 * u * math.sin(h * 1.9 + 0.4)
		cy = 0.012 * u * math.sin(h * 1.3 + 2.0)
		ring = []
		for i in range(sides):
			a = 2 * math.pi * i / sides
			r = radius * u * (1 + rng.uniform(-0.016, 0.016))
			ring.append(bm.verts.new((cx + r * math.sin(a), cy - r * math.cos(a), base + h * u)))
		rings.append(ring)
	for a, b in zip(rings, rings[1:]):
		for i in range(sides):
			j = (i + 1) % sides
			bm.faces.new((a[i], a[j], b[j], b[i]))
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

	# the pommel: a spade, thick, with a raised boss each side
	centre = base + (1.92 + 0.27) * u
	half = [(0.1, -0.36), (0.2, -0.27), (0.31, -0.08), (0.335, 0.06), (0.26, 0.22), (0.13, 0.38)]
	outline = [(x * u + rng.uniform(-0.12, 0.12), centre + z * u + rng.uniform(-0.12, 0.12)) for x, z in half]
	outline.append((rng.uniform(-0.1, 0.1), centre + 0.495 * u))
	outline += [(-x * u + rng.uniform(-0.12, 0.12), centre + z * u + rng.uniform(-0.12, 0.12)) for x, z in half[::-1]]

	def thick(x, z):
		return 0.175 * u

	prism(outline, thick, 0.065 * u, bm)

	def boss(x, z):
		return 0.175 * u + 0.02 * u

	disc = [(0.165 * u * math.cos(2 * math.pi * i / 12), centre + 0.03 * u + 0.205 * u * math.sin(2 * math.pi * i / 12)) for i in range(12)]
	prism(disc, boss, 0.02 * u, bm)
	return to_object(bm, "Hilt")


def outline_shell(objs):
	"""every part again, pushed out and turned inside out: Roblox only draws its faces behind the object, which shows as an ink line round the silhouette.
	Faces a chip made are left out (they're not on the uncut surface): their shell would stand in the chip as a black wedge"""
	out = bmesh.new()
	for obj, uncut in objs:
		bm = bmesh.new()
		bm.from_mesh(obj.data)
		bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
		bm.normal_update()
		chips = []
		if uncut is not None:
			src = bmesh.new()
			src.from_mesh(uncut)
			bmesh.ops.triangulate(src, faces=src.faces)
			tree = BVHTree.FromBMesh(src)
			chips = [f for f in bm.faces if tree.find_nearest(f.calc_center_median())[3] > 0.1]
			src.free()
		before = {f: f.normal.copy() for f in bm.faces}
		for v in bm.verts:
			v.co += v.normal * OUTLINE
		bm.normal_update()
		flipped = [f for f, n in before.items() if f.normal.dot(n) < 0.5]
		bmesh.ops.delete(bm, geom=list(set(chips) | set(flipped)), context="FACES")
		bmesh.ops.reverse_faces(bm, faces=bm.faces)
		me = bpy.data.meshes.new("tmp")
		bm.to_mesh(me)
		bm.free()
		out.from_mesh(me)
		bpy.data.meshes.remove(me)
	bmesh.ops.triangulate(out, faces=out.faces)
	return to_object(out, "Outline")


def split_blade(obj):
	"""three parts, so each gets its own whole texture"""
	bm = bmesh.new()
	bm.from_mesh(obj.data)
	# the two ends are never seen
	bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.95 and (f.calc_center_median().z < -BURY + 0.2 or f.calc_center_median().z > LB + 4.5)], context="FACES")
	for z in CUTS:
		bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-4, plane_co=(0, 0, z), plane_no=(0, 0, 1))
	parts = []
	bounds = (-1e9, CUTS[0], CUTS[1], 1e9)
	for i, name in enumerate(BLADE_PARTS):
		copy = bm.copy()
		bmesh.ops.delete(copy, geom=[f for f in copy.faces if not bounds[i] <= f.calc_center_median().z < bounds[i + 1]], context="FACES")
		parts.append(to_object(copy, name))
	bm.free()
	me = obj.data
	bpy.data.objects.remove(obj)
	bpy.data.meshes.remove(me)
	return parts


def signed_volume(bm):
	bm2 = bm.copy()
	bmesh.ops.triangulate(bm2, faces=bm2.faces)
	total = 0.0
	for f in bm2.faces:
		a, b, c = (v.co for v in f.verts)
		total += a.dot(b.cross(c)) / 6
	bm2.free()
	return total


def finish(obj):
	"""triangles, then the user's standard shading: hard edges (15 degrees, 25 on the round hilt), weighted normals"""
	bm = bmesh.new()
	bm.from_mesh(obj.data)
	bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.004)
	bmesh.ops.dissolve_degenerate(bm, dist=0.004, edges=bm.edges)
	bmesh.ops.triangulate(bm, faces=bm.faces)
	bm.to_mesh(obj.data)
	bm.free()
	me = obj.data
	me.shade_smooth()
	me.set_sharp_from_angle(angle=math.radians(25 if obj.name == "Hilt" else 15))
	bpy.context.view_layer.objects.active = obj
	mod = obj.modifiers.new("Weighted", "WEIGHTED_NORMAL")
	mod.keep_sharp = True
	bpy.ops.object.modifier_apply(modifier=mod.name)


def face_canvas(prefix, n):
	x, y, z = abs(n.x), abs(n.y), abs(n.z)
	if z >= x and z >= y:
		return prefix + ("U" if n.z > 0 else "D")
	if y >= x:
		return prefix + ("F" if n.y < 0 else "B")
	return prefix + ("R" if n.x > 0 else "L")


def project(canvas, p):
	"""a point onto its canvas, and how near it is to the viewer of that canvas"""
	kind = canvas[-1]
	if kind == "F":
		return p.x, p.z, -p.y
	if kind == "B":
		return -p.x, p.z, p.y
	if kind == "R":
		return p.y, p.z, p.x
	if kind == "L":
		return -p.y, p.z, -p.x
	if kind == "U":
		return p.x, p.y, p.z
	return p.x, -p.y, -p.z


def pack(islands, scale):
	"""rows of rectangles on one sheet; None if they don't fit"""
	placed = {}
	x, y, row = PAD, PAD, 0
	for name, (u0, v0, u1, v1, k) in sorted(islands.items(), key=lambda it: -(it[1][3] - it[1][1]) * it[1][4]):
		w = math.ceil((u1 - u0) * scale * k)
		h = math.ceil((v1 - v0) * scale * k)
		if x + w + PAD > SHEET:
			x, y = PAD, y + row + PAD
			row = 0
		if x + w + PAD > SHEET or y + h + PAD > SHEET:
			return None
		placed[name] = (x, y)
		x += w + PAD
		row = max(row, h)
	return placed


def best_scale(islands):
	low, high = 1.0, 64.0
	for _ in range(24):
		mid = (low + high) / 2
		if pack(islands, mid):
			low = mid
		else:
			high = mid
	return low


def build():
	os.makedirs(OUT, exist_ok=True)
	for o in list(bpy.data.objects):  # the default cube, camera and light too
		bpy.data.objects.remove(o)

	blade, blade_uncut = build_blade()
	guard, guard_uncut = build_guard()
	hilt = build_hilt()
	shell = outline_shell([(blade, blade_uncut), (guard, guard_uncut), (hilt, None)])
	bpy.data.meshes.remove(blade_uncut)
	bpy.data.meshes.remove(guard_uncut)
	parts = split_blade(blade) + [guard, hilt]
	# ends of the grip nobody sees are open already; the outline stays closed
	for obj in parts + [shell]:
		finish(obj)

	# which canvas each triangle paints from
	tris = {}  # canvas -> list of (owner, uvw[3], pos[3], nor[3], face normal)
	for obj in parts:
		me = obj.data
		me.calc_loop_triangles()
		normals = np.zeros((len(me.loops), 3), dtype=np.float32)
		me.corner_normals.foreach_get("vector", normals.ravel())
		prefix = "B" if obj.name.startswith("Blade") else "G" if obj.name == "Guard" else "H"
		for poly in me.polygons:
			verts = [me.vertices[i].co for i in poly.vertices]
			centre = sum(verts, Vector()) / 3
			is_grip = prefix == "H" and centre.z < LB + 0.38 * W + 1.93 * W
			if is_grip:
				canvas = "HW"
				angles = [math.atan2(v.x, -v.y) for v in verts]
				if max(angles) - min(angles) > math.pi:
					angles = [a + 2 * math.pi if a < 0 else a for a in angles]
				uvw = [(a * GRIP_R, v.z, 0.0) for a, v in zip(angles, verts)]
			else:
				canvas = face_canvas(prefix, poly.normal)
				uvw = [project(canvas, v) for v in verts]
			nor = [tuple(normals[l]) for l in poly.loop_indices]
			tris.setdefault(canvas, []).append((obj.name, poly.index, uvw, [tuple(v) for v in verts], nor, tuple(poly.normal)))

	# islands: one window per canvas per part
	windows = {}
	for canvas, items in tris.items():
		for owner, _, uvw, *_rest in items:
			w = windows.setdefault((owner, canvas), [1e9, 1e9, -1e9, -1e9])
			for u, v, _d in uvw:
				w[0], w[1] = min(w[0], u), min(w[1], v)
				w[2], w[3] = max(w[2], u), max(w[3], v)
	small = {"BU", "BD", "GD", "HU", "HD", "HL", "HR"}
	sheets = {}
	for (owner, canvas), w in windows.items():
		margin = 0.25
		k = 0.5 if canvas in small else 1.0
		sheets.setdefault(owner, {})[canvas] = (w[0] - margin, w[1] - margin, w[2] + margin, w[3] + margin, k)
	scales = {name: best_scale(isl) * 0.995 for name, isl in sheets.items()}
	blade_scale = min(scales[n] for n in BLADE_PARTS)
	for n in BLADE_PARTS:
		scales[n] = blade_scale

	layout = {"Sheets": {}, "Canvases": {}, "Params": {"W": W, "LB": LB, "BURY": BURY, "GripR": GRIP_R}, "Size": SHEET}
	for name, isl in sheets.items():
		placed = pack(isl, scales[name])
		assert placed, name
		islands = []
		for canvas, (u0, v0, u1, v1, k) in isl.items():
			px, py = placed[canvas]
			islands.append({"Canvas": canvas, "U0": u0, "V0": v0, "U1": u1, "V1": v1, "PX": px, "PY": py, "K": k})
			c = layout["Canvases"].setdefault(canvas, {"U0": u0, "V0": v0, "U1": u1, "V1": v1, "Scale": scales[name] * k})
			c["U0"], c["V0"] = min(c["U0"], u0), min(c["V0"], v0)
			c["U1"], c["V1"] = max(c["U1"], u1), max(c["V1"], v1)
		layout["Sheets"][name] = {"Scale": scales[name], "Islands": islands}

	# UVs on the meshes
	lookup = {name: {i["Canvas"]: i for i in s["Islands"]} for name, s in layout["Sheets"].items()}
	objs = {o.name: o for o in parts}
	for obj in parts:
		obj.data.uv_layers.new(name="UVMap")
	for canvas, items in tris.items():
		for owner, index, uvw, *_ in items:
			isl = lookup[owner][canvas]
			s = scales[owner] * isl["K"]
			me = objs[owner].data
			poly = me.polygons[index]
			uv = me.uv_layers[0].data
			for l, (u, v, _d) in zip(poly.loop_indices, uvw):
				col = isl["PX"] + (u - isl["U0"]) * s
				row = isl["PY"] + (isl["V1"] - v) * s
				uv[l].uv = (col / SHEET, 1 - row / SHEET)

	# what the painter needs
	arrays = {}
	for canvas, items in tris.items():
		arrays[canvas + "_uvw"] = np.array([it[2] for it in items], dtype=np.float32)
		arrays[canvas + "_pos"] = np.array([it[3] for it in items], dtype=np.float32)
		arrays[canvas + "_nor"] = np.array([it[4] for it in items], dtype=np.float32)
		arrays[canvas + "_fn"] = np.array([it[5] for it in items], dtype=np.float32)
	np.savez(os.path.join(OUT, "bake.npz"), **arrays)
	json.dump(layout, open(os.path.join(OUT, "layout.json"), "w"), indent=1)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "sword.blend"))

	counts = {o.name: len(o.data.polygons) for o in parts + [shell]}
	for o in parts:
		bm = bmesh.new()
		bm.from_mesh(o.data)
		print("[sword]", o.name, "tris", counts[o.name], "scale", round(scales[o.name], 2), "volume sign", round(signed_volume(bm)), flush=True)
		bm.free()
	print("[sword] outline tris", counts["Outline"], "total", sum(counts.values()), flush=True)


def part_material(name):
	path = os.path.join(OUT, f"Sword_{name}.png")
	m = bpy.data.materials.new("Sword" + name)
	m.use_nodes = True
	nt = m.node_tree
	b = nt.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.9
	b.inputs["Specular IOR Level"].default_value = 0.15
	if os.path.exists(path):
		im = nt.nodes.new("ShaderNodeTexImage")
		im.image = bpy.data.images.load(path)
		nt.links.new(im.outputs["Color"], b.inputs["Base Color"])
	else:
		b.inputs["Base Color"].default_value = (0.55, 0.56, 0.5, 1)
	return m


VIEWS = {
	"whole": ((62, -240, 56), (0, 0, 84), 46),
	"guard": ((26, -66, 128), (0, 0, 132), 52),
	"foot": ((20, -46, 7), (0, 0, 26), 62),
	"blade": ((14, -58, 56), (0, 0, 56), 58),
	"back": ((-60, 240, 56), (0, 0, 84), 46),
	"above": ((52, -80, 200), (0, 0, 136), 55),
}


def render():
	tag = ARGS[1] if len(ARGS) > 1 else "clay"
	wanted = ARGS[2].split(",") if len(ARGS) > 2 else list(VIEWS)
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "sword.blend"))
	sc = bpy.context.scene
	for obj in list(sc.collection.objects):
		obj.data.materials.clear()
		if obj.name == "Outline":
			obj.data.materials.append(old.flat_material("Ink", "1c2a2c"))
			obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))
			mat = obj.data.materials[0]
			mat.use_backface_culling = True
			obj.visible_shadow = False
		else:
			obj.data.materials.append(part_material(obj.name))
	old.ground_plane(sc.collection, "79b65a")
	old.stage(sc)
	sc.render.resolution_x, sc.render.resolution_y = 900, 1100
	for name in wanted:
		pos, target, fov = VIEWS[name]
		old.camera(sc, pos, target, fov)
		sc.render.filepath = os.path.join(OUT, "views", f"{tag}_{name}.png")
		bpy.ops.render.render(write_still=True)
		print("[sword] rendered", name, flush=True)


def export():
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "sword.blend"))
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "StoneSword.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	bounds = {}
	for obj in bpy.data.objects:
		c = [Vector(v) for v in obj.bound_box]
		bounds[obj.name] = [min(v.x for v in c), min(v.y for v in c), min(v.z for v in c), max(v.x for v in c), max(v.y for v in c), max(v.z for v in c)]
	json.dump(bounds, open(os.path.join(OUT, "bounds.json"), "w"), indent=1)
	print("[sword] exported", list(bounds), flush=True)


if __name__ == "__main__":
	if ARGS[0] == "build":
		build()
	elif ARGS[0] == "render":
		render()
	elif ARGS[0] == "export":
		export()
