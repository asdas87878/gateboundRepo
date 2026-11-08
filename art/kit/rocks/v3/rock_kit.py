"""The modular rock kit for the stylized look (research/stylized_lesson, private reference): big pale blocks with clean
flat planes and bevelled edges that catch a painted highlight. All pieces share one texture (tools/art/paint_rock_kit.py).

  blender --background --python tools/blender/rock_kit.py -- build     art/kit/rocks: rock_kit.blend, bake.npz, kit.json
  python tools/art/paint_rock_kit.py                                   art/kit/rocks/RockKit_Color.png
  blender --background --python tools/blender/rock_kit.py -- render    art/kit/rocks: lineup.png, pile.png
  blender --background --python tools/blender/rock_kit.py -- export    art/kit/rocks/RockKit.glb

Each piece: one or more convex hulls of chipped, sheared boxes, faces merged into big planes, real edges bevelled,
area-weighted normals so planes stay flat and bevels read as rounded. Origin at the base centre, studs, Z up. The open bottom sits buried.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import kit  # noqa: E402

OUT = os.path.join(ROOT, "art", "kit", "rocks")
ARGS = sys.argv[sys.argv.index("--") + 1 :]

# name: (length, width, height), seed, big chips, lumps. Boulders and slabs for banks and scatter, blocks to stack into
# walls, cliffs as tall backdrop pieces. A lump (x, y, size x, size y, size z, all fractions of the piece's size) is one
# hull; lumps overlap, so a piece has real crevices and a chunky outline instead of one big convex shape.
ONE = [(0, 0, 1, 1, 1)]
SPECS = {
	"Chip": ((2.4, 1.9, 1.1), 11, 1, ONE),
	"BoulderSmall": ((4.5, 3.8, 2.8), 12, 1, ONE),
	"Boulder": ((7.5, 6.0, 4.8), 13, 2, ONE),
	"SlabSmall": ((7.0, 4.2, 1.7), 14, 1, ONE),
	"Slab": ((11.0, 6.5, 2.6), 15, 2, ONE),
	"BlockSmall": ((8.0, 6.5, 6.0), 16, 1, [(-0.08, 0, 0.8, 0.95, 1), (0.3, -0.12, 0.42, 0.65, 0.6)]),
	"Block": ((12.0, 8.0, 9.5), 17, 1, [(-0.08, 0.04, 0.78, 0.9, 1), (0.3, -0.14, 0.42, 0.65, 0.62), (-0.2, -0.32, 0.5, 0.36, 0.36)]),
	"CliffWide": ((24.0, 12.0, 14.0), 18, 1, [(-0.24, 0.04, 0.52, 0.85, 1), (0.2, 0.08, 0.56, 0.8, 0.8), (-0.02, -0.28, 0.42, 0.44, 0.46), (0.38, -0.22, 0.26, 0.5, 0.36), (-0.38, -0.32, 0.24, 0.36, 0.3)]),
	"CliffTall": ((15.0, 11.0, 24.0), 19, 1, [(0, 0.06, 0.66, 0.82, 1), (-0.27, 0.02, 0.46, 0.7, 0.66), (0.28, -0.1, 0.44, 0.68, 0.48), (-0.04, -0.32, 0.56, 0.38, 0.27)]),
	# detail: chips and small stones, to break up edges
	"ChipFlat": ((3.4, 2.3, 0.7), 31, 1, ONE),
	"ChipTall": ((1.8, 1.5, 1.9), 32, 2, ONE),
	"Stone": ((3.1, 2.6, 3.6), 33, 2, ONE),
	# boulders: free-standing, in the water and on the banks
	"BoulderRound": ((6.2, 5.6, 3.8), 34, 3, ONE),
	"BoulderTall": ((5.0, 4.4, 7.2), 35, 2, ONE),
	"BoulderWide": ((10.5, 7.0, 5.0), 36, 2, [(-0.14, 0.03, 0.72, 0.95, 1), (0.28, -0.08, 0.46, 0.72, 0.6)]),
	# foot rocks: flat and stubby, where a wall meets the ground
	"FootStub": ((8.0, 5.0, 2.6), 37, 2, ONE),
	"FootWide": ((13.0, 6.0, 3.3), 38, 1, [(-0.18, 0.04, 0.66, 1, 1), (0.28, -0.04, 0.46, 0.8, 0.68)]),
	"FootWedge": ((9.5, 6.5, 3.2), 39, 2, ONE),
	# slabs: shore rocks and steps
	"SlabLong": ((16.0, 5.2, 2.3), 40, 2, ONE),
	"SlabStack": ((12.5, 8.5, 4.8), 41, 1, [(0, 0, 1, 1, 0.48), (-0.1, 0.08, 0.66, 0.66, 1)]),
	"SlabBroken": ((14.0, 8.0, 2.8), 42, 1, [(-0.24, 0.05, 0.54, 0.9, 1), (0.25, -0.05, 0.5, 0.8, 0.72)]),
	# blocks: stack these into walls
	"BlockTall": ((7.5, 6.5, 11.5), 43, 1, [(-0.05, 0.03, 0.82, 0.92, 1), (0.3, -0.15, 0.4, 0.62, 0.42)]),
	"BlockLean": ((9.5, 7.5, 10.5), 44, 2, ONE),
	"BlockChunk": ((11.0, 9.0, 7.5), 45, 3, [(-0.1, 0.05, 0.8, 0.9, 1), (0.28, -0.2, 0.46, 0.55, 0.55)]),
	# walls: large wide rocks that fill a cliff face without lots of mini rocks
	"WallMid": ((17.0, 9.0, 12.0), 46, 1, [(-0.14, 0.04, 0.72, 0.9, 1), (0.28, 0.02, 0.48, 0.82, 0.74), (0.02, -0.3, 0.46, 0.4, 0.34)]),
	"WallWide": ((31.0, 12.0, 16.0), 47, 1, [(-0.28, 0.05, 0.46, 0.86, 1), (0.04, 0.08, 0.44, 0.8, 0.8), (0.32, 0.03, 0.38, 0.84, 0.94), (-0.1, -0.3, 0.36, 0.4, 0.36), (0.24, -0.3, 0.3, 0.38, 0.28)]),
	"WallLong": ((42.0, 13.0, 18.0), 48, 1, [(-0.34, 0.06, 0.34, 0.84, 0.86), (-0.08, 0.08, 0.36, 0.82, 1), (0.16, 0.04, 0.3, 0.86, 0.72), (0.37, 0.06, 0.28, 0.82, 0.9), (-0.22, -0.3, 0.3, 0.4, 0.3), (0.2, -0.32, 0.26, 0.36, 0.34)]),
	"WallHigh": ((22.0, 12.0, 28.0), 49, 1, [(-0.16, 0.05, 0.62, 0.86, 1), (0.28, 0.02, 0.46, 0.84, 0.72), (-0.3, -0.26, 0.36, 0.42, 0.4), (0.14, -0.3, 0.4, 0.38, 0.28)]),
	"WallStep": ((27.0, 14.0, 20.0), 50, 1, [(-0.28, 0.08, 0.46, 0.8, 1), (0.04, 0.02, 0.42, 0.86, 0.66), (0.32, -0.04, 0.38, 0.86, 0.38), (-0.26, -0.32, 0.38, 0.32, 0.4)]),
	# shapes: for variety and corners
	"Corner": ((18.0, 18.0, 20.0), 51, 1, [(-0.14, 0.14, 0.72, 0.72, 1), (0.26, -0.06, 0.44, 0.72, 0.62), (-0.2, -0.28, 0.5, 0.42, 0.5)]),
	"Spire": ((8.5, 7.5, 22.0), 52, 2, [(0, 0.03, 0.9, 0.9, 1), (0.3, -0.2, 0.42, 0.5, 0.3)]),
	"CapSlab": ((21.0, 12.0, 4.2), 53, 2, [(-0.2, 0.04, 0.64, 0.94, 1), (0.24, -0.03, 0.54, 0.88, 0.8)]),
}
# optional shape changes per piece: top scale (under 1 narrows the top), and how far the top leans (fractions of length and width)
SHAPE = {
	"BoulderRound": (0.72, (0.02, -0.03)),
	"BoulderTall": (0.74, (0.06, 0.03)),
	"FootStub": (0.68, (0.0, 0.1)),
	"FootWide": (0.74, (0.0, 0.08)),
	"FootWedge": (0.68, (0.14, 0.05)),
	"BlockLean": (0.86, (0.22, 0.08)),
	"Spire": (0.55, (0.08, 0.05)),
	"CapSlab": (1.0, (0.0, 0.0)),
	"WallStep": (0.92, (0.0, 0.05)),
}
ROW_WIDTH = 120  # studs across a row of the lineup
# chunkier: every piece a bit lower, deeper and wider than it was first drawn
CHUNK = (1.1, 1.25, 0.72)
TALL = {"Spire"}  # keep their height
SPECS = {n: (((v[0][0] * CHUNK[0], v[0][1] * CHUNK[1], v[0][2] * (1 if n in TALL else CHUNK[2]))), *v[1:]) for n, v in SPECS.items()}
TILT = (0.14, 0.34)  # how far the top plane falls on its low side, share of the height: the wedge in the reference's rocks
INSET = (0.72, 0.86)  # the top's width against the foot's
SHOULDER = (0.92, 1.02)  # how far out the sides' break sits
FOOT_SQUARE = 3.2  # 2 is an ellipse, higher a box
PLANE_MERGE = 12  # degrees: facets closer than this become one plane
EDGE_ANGLE = 32  # degrees: edges over this get a bevel and a highlight
LUMP_FUSE = 1.3  # lumps are this much wider than drawn
BEVEL = (0.14, 0.62, 0.085)  # edge bevel in studs: smallest, largest, share of the lump's smallest side
# Roblox cuts every texture to 1024, so big rocks can't all share one map. Each sheet gets its own 1024
ATLASES = {
	"A": ["WallLong", "WallWide"],
	"B": ["WallHigh", "WallStep", "Corner"],
	"C": ["CliffWide", "CliffTall", "WallMid", "Spire", "CapSlab"],
	"D": ["Block", "BlockTall", "BlockLean", "BlockChunk", "BlockSmall", "BoulderWide", "SlabStack", "SlabBroken"],
	"E": ["Chip", "ChipFlat", "ChipTall", "Stone", "BoulderSmall", "BoulderRound", "BoulderTall", "Boulder", "FootStub", "FootWide", "FootWedge", "SlabSmall", "Slab", "SlabLong"],
}
ATLAS_OF = {n: a for a, ns in ATLASES.items() for n in ns}
CHART_COS = math.cos(math.radians(48))  # how far a face may turn from its chart before it starts a new one
PAD = 0.005  # gap between charts, share of the sheet


def rock_bmesh(size, seed, big, taper=1.0, lean=(0.0, 0.0)):
	"""one lump, a wide cobble as in the reference: an irregular 5-7 sided footprint, sides leaning in, and a flat top plane that tilts, so one
	side sits lower. Returns the bmesh and the hull's planes (to find hidden faces)."""
	L, W, H = size
	r = random.Random(seed)
	small = min(L, W, H)
	n = r.randint(5, 7)
	turn = r.uniform(0, math.tau)
	angles = sorted((turn + (i + r.uniform(-0.32, 0.32)) * math.tau / n) % math.tau for i in range(n))
	tilt = r.uniform(0, math.tau)
	tilt_dir = (math.cos(tilt), math.sin(tilt))
	drop = r.uniform(*TILT)
	inset = r.uniform(*INSET) * taper
	shift = (r.uniform(-0.08, 0.08) * L + lean[0] * L, r.uniform(-0.08, 0.08) * W + lean[1] * W)
	pts = []
	for k, a0 in enumerate(angles):
		ca, sa = math.cos(a0), math.sin(a0)
		e = (abs(ca) ** FOOT_SQUARE + abs(sa) ** FOOT_SQUARE) ** (1 / FOOT_SQUARE)  # a soft box, not an ellipse
		bx, by = ca / e * L / 2 * r.uniform(0.9, 1.0), sa / e * W / 2 * r.uniform(0.9, 1.0)
		pts.append(Vector((bx, by, 0)))
		# the shoulder: partway up, still wide, so sides are two planes rather than one flat lean
		sh = r.uniform(*SHOULDER)
		out = sh * (1 - (1 - inset) * 0.55)
		pts.append(Vector((bx * out + shift[0] * 0.5, by * out + shift[1] * 0.5, H * r.uniform(0.34, 0.5))))
		tx, ty = bx * inset + shift[0], by * inset + shift[1]
		side = (ca * tilt_dir[0] + sa * tilt_dir[1]) * 0.5 + 0.5  # 0 at the low side, 1 at the high side
		tz = H * (1 - drop * (1 - side)) * r.uniform(0.97, 1.0)
		if k < big:  # a broken corner
			tx, ty, tz = tx * 0.86, ty * 0.86, tz * r.uniform(0.8, 0.9)
		pts.append(Vector((tx, ty, tz)))
	bm = bmesh.new()
	verts = [bm.verts.new(q) for q in pts]
	res = bmesh.ops.convex_hull(bm, input=verts)
	bmesh.ops.delete(bm, geom=[v for v in set(res["geom_interior"]) | set(res["geom_unused"]) if isinstance(v, bmesh.types.BMVert)], context="VERTS")
	bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(PLANE_MERGE), verts=list(bm.verts), edges=list(bm.edges))
	bm.normal_update()
	planes = [(f.normal.copy(), f.verts[0].co.copy()) for f in bm.faces]
	layer = bm.faces.layers.int.new("bevel")
	edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(EDGE_ANGLE)]  # only real edges get a highlight
	res = bmesh.ops.bevel(bm, geom=edges, offset=max(BEVEL[0], min(BEVEL[1], small * BEVEL[2])), offset_type="OFFSET", segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
	for f in res["faces"]:
		f[layer] = 1
	bm.normal_update()
	bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.8 and f.calc_center_median().z < H * 0.1], context="FACES")
	return bm, planes


def smooth_area_weighted(me):
	"""all smooth, vertex normals weighted by face area: big planes keep their flat normal, bevels round off between them"""
	me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
	acc = [Vector() for _ in me.vertices]
	for p in me.polygons:
		w = p.normal * p.area
		for v in p.vertices:
			acc[v] += w
	me.normals_split_custom_set_from_vertices([tuple(a.normalized()) for a in acc])


def layout_uvs(me, sheets):
	"""our own UV layout. Blender's packer shrank everything to under 1% once there were many small islands. Each sheet: faces flood into
	charts of about the same facing, each chart is flattened and turned so its long side lies across, then charts are shelf-packed at one
	even density, as large as will fit. Returns nothing; writes the active UV layer."""
	bm = bmesh.new()
	bm.from_mesh(me)
	uv_layer = bm.loops.layers.uv.verify()
	piece = bm.faces.layers.int["piece"]
	bm.normal_update()
	for atlas, ids in sheets.items():
		todo = {f for f in bm.faces if f[piece] in ids}
		charts = []
		while todo:
			seed = max(todo, key=lambda f: f.calc_area())
			todo.remove(seed)
			chart, stack, axis = [seed], [seed], seed.normal.copy()
			while stack:
				f = stack.pop()
				for e in f.edges:
					for g in e.link_faces:
						if g in todo and g.normal.dot(axis) > CHART_COS:
							todo.remove(g)
							chart.append(g)
							stack.append(g)
			u = axis.orthogonal().normalized()
			v = axis.cross(u).normalized()
			pts = {}
			for f in chart:
				for lv in f.verts:
					pts[lv] = (lv.co.dot(u), lv.co.dot(v))
			# turn to the narrowest box among a few angles
			best = None
			for k in range(12):
				a0 = k * math.pi / 12
				ca, sa = math.cos(a0), math.sin(a0)
				xs = [p[0] * ca + p[1] * sa for p in pts.values()]
				ys = [-p[0] * sa + p[1] * ca for p in pts.values()]
				w, h = max(xs) - min(xs), max(ys) - min(ys)
				if best is None or h * w < best[0]:
					best = (h * w, ca, sa, min(xs), min(ys), w, h)
			_, ca, sa, x0, y0, w, h = best
			if h > w:  # long side across
				flat = {lv: (p[0] * -sa + p[1] * ca - y0, p[0] * ca + p[1] * sa - x0) for lv, p in pts.items()}
				w, h = h, w
			else:
				flat = {lv: (p[0] * ca + p[1] * sa - x0, -p[0] * sa + p[1] * ca - y0) for lv, p in pts.items()}
			charts.append((chart, flat, w, h))
		charts.sort(key=lambda c: -c[3])
		# the largest scale at which the shelves fit
		def fits(sc):
			x = y = row = PAD
			out = []
			for _, _, w, h in charts:
				cw, ch = w * sc, h * sc
				if cw + 2 * PAD > 1:
					return None
				if x + cw + PAD > 1:
					x, y, row = PAD, y + row + PAD, 0.0
				if y + ch + PAD > 1:
					return None
				out.append((x, y))
				x += cw + PAD
				row = max(row, ch)
			return out
		lo, hi = 0.0, 1.0
		for _ in range(30):
			mid = (lo + hi) / 2
			if fits(mid):
				lo = mid
			else:
				hi = mid
		places = fits(lo)
		for (chart, flat, _, _), (x, y) in zip(charts, places):
			for f in chart:
				for lp in f.loops:
					fx, fy = flat[lp.vert]
					lp[uv_layer].uv = (x + fx * lo, y + fy * lo)
		print(f"[rocks] sheet {atlas}: {len(charts)} charts, {lo * 1024:.1f} texels a stud at 1024", flush=True)
	bm.to_mesh(me)
	bm.free()


def build():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	joined = bmesh.new()
	piece = joined.faces.layers.int.new("piece")
	bevel = joined.faces.layers.int.new("bevel")
	sub = joined.faces.layers.int.new("sub")
	x = 0.0
	offsets = {}
	for k, (name, (size, seed, big, lumps)) in enumerate(SPECS.items()):
		x += size[0] / 2 + 8
		offsets[name] = x
		built = []
		for j, (lx, ly, sx, sy, sz) in enumerate(lumps):
			off = Vector((x + lx * size[0], ly * size[1], 0))
			taper, lean = SHAPE.get(name, (1.0, (0.0, 0.0)))
			fuse = LUMP_FUSE if len(lumps) > 1 else 1.0  # lumps overlap, so a piece reads as one rock, not teeth
			bm, planes = rock_bmesh((size[0] * sx * fuse, size[1] * sy * fuse, size[2] * sz), seed + j * 37, big if j == 0 else 1, taper, lean)
			bmesh.ops.translate(bm, vec=off, verts=list(bm.verts))
			built.append((bm, [(n, q + off) for n, q in planes]))
		for j, (bm, _) in enumerate(built):
			src = bm.faces.layers.int["bevel"]
			others = [pl for i, (_, pl) in enumerate(built) if i != j]
			vm = {}
			for f in bm.faces:
				# a face fully inside another lump is never seen: leave it out
				if any(all(all((v.co - q).dot(n) < 0 for n, q in pl) for v in f.verts) for pl in others):
					continue
				for v in f.verts:
					if v not in vm:
						vm[v] = joined.verts.new(v.co)
				nf = joined.faces.new([vm[v] for v in f.verts])
				nf[piece], nf[bevel], nf[sub] = k, f[src], j
			bm.free()
		x += size[0] / 2 + 8
	joined.normal_update()
	me = bpy.data.meshes.new("RockKitAll")
	joined.to_mesh(me)
	joined.free()
	obj = bpy.data.objects.new("RockKitAll", me)
	sc.collection.objects.link(obj)
	bpy.context.view_layer.objects.active = obj
	obj.select_set(True)
	names = list(SPECS)
	layout_uvs(me, {a: {names.index(n) for n in ns} for a, ns in ATLASES.items()})
	# what the painter needs, per triangle
	me.calc_loop_triangles()
	tris = me.loop_triangles
	uvd = me.uv_layers.active.data
	pa, ba, sa = me.attributes["piece"].data, me.attributes["bevel"].data, me.attributes["sub"].data
	names = list(SPECS)
	pos, uv, nor, pc, bv, fc, sb = [], [], [], [], [], [], []
	for t in tris:
		pos.append([me.vertices[v].co[:] for v in t.vertices])
		uv.append([uvd[li].uv[:] for li in t.loops])
		nor.append(me.polygons[t.polygon_index].normal[:])
		pc.append(pa[t.polygon_index].value)
		bv.append(ba[t.polygon_index].value)
		fc.append(t.polygon_index)
		sb.append(sa[t.polygon_index].value)
	np.savez_compressed(os.path.join(OUT, "bake.npz"), pos=np.array(pos, np.float32), uv=np.array(uv, np.float32), nor=np.array(nor, np.float32),
						piece=np.array(pc), bevel=np.array(bv), face=np.array(fc), sub=np.array(sb), names=np.array(names), atlas=np.array([ATLAS_OF[n] for n in names]),
						offset=np.array([offsets[n] for n in names]), height=np.array([SPECS[n][0][2] for n in names]))
	# the pieces, back at their own origins, sharing the atlas
	meta = {}
	for k, name in enumerate(names):
		bm = bmesh.new()
		bm.from_mesh(me)
		layer = bm.faces.layers.int["piece"]
		bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != k], context="FACES")
		bmesh.ops.translate(bm, vec=Vector((-offsets[name], 0, 0)), verts=list(bm.verts))
		pm = bpy.data.meshes.new(name)
		bm.to_mesh(pm)
		bm.free()
		smooth_area_weighted(pm)
		po = bpy.data.objects.new(name, pm)
		sc.collection.objects.link(po)
		pm.calc_loop_triangles()
		meta[name] = {"Size": list(SPECS[name][0]), "Tris": len(pm.loop_triangles), "Atlas": ATLAS_OF[name]}
	bpy.data.objects.remove(obj)
	json.dump(meta, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "rock_kit.blend"))
	print("[rocks] built", meta, "total tris", sum(m["Tris"] for m in meta.values()), flush=True)


def lin(h):
	return kit.to_linear(kit.srgb(h))


def rock_material(atlas):
	m = bpy.data.materials.new("RockKit" + atlas)
	m.use_nodes = True
	nt = m.node_tree
	b = nt.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.85
	b.inputs["Specular IOR Level"].default_value = 0.2
	im = nt.nodes.new("ShaderNodeTexImage")
	im.image = bpy.data.images.load(os.path.join(OUT, f"RockKit_{atlas}_Moss.png"))
	nt.links.new(im.outputs["Color"], b.inputs["Base Color"])
	return m


def flat_material(name, colour):
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	b = m.node_tree.nodes["Principled BSDF"]
	b.inputs["Base Color"].default_value = (*lin(colour), 1)
	b.inputs["Roughness"].default_value = 0.9
	b.inputs["Specular IOR Level"].default_value = 0.1
	return m


def place(coll, name, x, y, yaw=0.0, s=1.0, z=0.0, tilt=(0.0, 0.0)):
	o = bpy.data.objects.new(name, bpy.data.meshes[name])
	o.location = (x, y, z)
	o.rotation_euler = (tilt[0], tilt[1], yaw)
	o.scale = (s, s, s)
	coll.objects.link(o)
	return o


def stage(sc, sky="74c6ea"):
	w = bpy.data.worlds.new("Sky")
	sc.world = w
	w.use_nodes = True
	nt = w.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputWorld")
	seen, fill = nt.nodes.new("ShaderNodeBackground"), nt.nodes.new("ShaderNodeBackground")
	seen.inputs["Color"].default_value = (*lin(sky), 1)
	fill.inputs["Color"].default_value = (*lin("c9d8dc"), 1)  # what lights the scene: only a little blue, so stone stays stone
	fill.inputs["Strength"].default_value = 0.8
	lp, mx = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
	nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs["Fac"])
	nt.links.new(fill.outputs["Background"], mx.inputs[1])
	nt.links.new(seen.outputs["Background"], mx.inputs[2])
	nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
	sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
	sun.data.energy = 3.0
	sun.data.color = lin("fff3dc")
	sun.data.angle = math.radians(3)
	sun.rotation_euler = Vector((-0.55, 0.45, -0.7)).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(sun)
	sc.render.engine = "BLENDER_EEVEE"
	sc.render.resolution_x, sc.render.resolution_y = 1600, 900
	sc.eevee.taa_render_samples = 32
	sc.view_settings.view_transform = "Standard"
	sc.render.image_settings.file_format = "PNG"


def camera(sc, pos, target, fov=70):
	c = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
	c.data.sensor_fit = "VERTICAL"
	c.data.angle_y = math.radians(fov)
	c.data.clip_end = 5000
	c.location = pos
	c.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(c)
	sc.camera = c


def ground_plane(coll, colour):
	me = bpy.data.meshes.new("Floor")
	me.from_pydata([(-400, -400, 0), (400, -400, 0), (400, 400, 0), (-400, 400, 0)], [], [(0, 1, 2, 3)])
	me.materials.append(flat_material("Floor", colour))
	coll.objects.link(bpy.data.objects.new("Floor", me))


def stream_ground(coll):
	"""a stand-in setting for the pile: a stream with sand banks between grass, flat colours with crisp borders"""
	n, step = 161, 1.0
	xs = (np.arange(n) - n // 2) * step
	X, Y = np.meshgrid(xs, xs + 40)
	wob = np.sin(Y * 0.09) * 2.2 + np.sin(Y * 0.23 + 1) * 0.8
	d = np.abs(X - wob)
	Z = np.clip((d - 7) / 6, 0, 1) ** 1.2 * 2.6 + np.clip((d - 22) / 30, 0, 1) * 7
	verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
	idx = np.arange(n * n).reshape(n, n)
	quads = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
	me = bpy.data.meshes.new("Stream")
	me.from_pydata(verts.tolist(), [], quads.tolist())
	me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
	uvl = me.uv_layers.new(name="UV")
	lo, span = xs[0], xs[-1] - xs[0]
	uvs = np.stack([(verts[:, 0] - lo) / span, (verts[:, 1] - lo - 40) / span], -1)
	li = np.zeros(len(me.loops), np.int64)
	me.loops.foreach_get("vertex_index", li)
	uvl.data.foreach_set("uv", uvs[li].astype(np.float32).ravel())
	N = 2048  # flat colours with crisp borders, 0.08 studs a pixel
	gx = lo + (np.arange(N) + 0.5) / N * span
	PX, PY = np.meshgrid(gx, gx + 40)
	pw = np.sin(PY * 0.09) * 2.2 + np.sin(PY * 0.23 + 1) * 0.8
	dp = np.abs(PX - pw)
	edge = 13 + np.sin(PY * 0.31) * 1.2 + np.sin(PY * 0.77 + PX * 0.3) * 0.5
	pa = (np.sin(PX * 0.21 + np.sin(PY * 0.17)) * np.sin(PY * 0.13) * 0.5 + 0.5)[..., None]
	sand, grass, grass2 = np.array(lin("efdc86")), np.array(lin("27a85a")), np.array(lin("3cc06a"))
	col = np.where((dp < edge)[..., None], sand, grass * (1 - pa) + grass2 * pa)
	img = bpy.data.images.new("StreamCol", N, N, alpha=False, float_buffer=True)
	img.pixels.foreach_set(np.concatenate([col, np.ones((N, N, 1))], -1).astype(np.float32).ravel())
	img.pack()
	m = flat_material("StreamMat", "ffffff")
	tx = m.node_tree.nodes.new("ShaderNodeTexImage")
	tx.image = img
	m.node_tree.links.new(tx.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
	me.materials.append(m)
	coll.objects.link(bpy.data.objects.new("Stream", me))
	wm = bpy.data.meshes.new("Water")
	wm.from_pydata([(-90, -60, 0.45), (90, -60, 0.45), (90, 140, 0.45), (-90, 140, 0.45)], [], [(0, 1, 2, 3)])
	wm.materials.append(flat_material("Water", "66d9cf"))
	coll.objects.link(bpy.data.objects.new("Water", wm))


def render():
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "rock_kit.blend"))
	sc = bpy.context.scene
	mats = {a: rock_material(a) for a in ATLASES}
	for name in SPECS:
		me = bpy.data.meshes[name]
		me.materials.clear()
		me.materials.append(mats[ATLAS_OF[name]])
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	stage(sc)
	# lineup, smallest to biggest, the 5.2-stud figure in front
	line = bpy.data.collections.new("Lineup")
	sc.collection.children.link(line)
	ground_plane(line, "2bab5e")
	order = sorted(SPECS, key=lambda n: SPECS[n][0][0] * SPECS[n][0][1] * SPECS[n][0][2])
	rows, cur, used = [], [], 0.0
	for name in order:
		w = SPECS[name][0][0] + 3
		if cur and used + w > ROW_WIDTH:
			rows.append(cur)
			cur, used = [], 0.0
		cur.append(name)
		used += w
	rows.append(cur)
	y = -24.0
	for row in rows:
		x = -sum(SPECS[n][0][0] + 3 for n in row) / 2
		for name in row:
			x += SPECS[name][0][0] / 2 + 1.5
			place(line, name, x, y, 0.3)
			x += SPECS[name][0][0] / 2 + 1.5
		y += max(SPECS[n][0][1] for n in row) + 8
	kit.hero("Hero", 7, line).location = (-ROW_WIDTH / 2 - 4, -26, 0)
	camera(sc, (0, -112, 48), (0, y * 0.35, 6), 45)
	sc.render.filepath = os.path.join(OUT, "lineup.png")
	bpy.ops.render.render(write_still=True)
	for o in list(line.objects):
		o.hide_render = True
	sc.camera = None
	bpy.data.objects.remove(bpy.data.objects["Cam"])
	# the same pieces put together: a stream bank, built only by repeating and turning the kit
	pile = bpy.data.collections.new("Pile")
	sc.collection.children.link(pile)
	stream_ground(pile)
	# left: a cliff wall stepping down to shore slabs
	for name, x, y, yaw, s, z in (
		("CliffTall", -36, 48, 0.3, 1.25, 2), ("CliffWide", -44, 22, 1.3, 1.2, 3), ("CliffTall", -34, 6, 2.5, 0.9, 3), ("CliffWide", -40, 76, 0.2, 1.1, 2),
		("Block", -23, 34, 0.5, 1.0, 2), ("Block", -24, 13, 2.2, 0.85, 2), ("BlockSmall", -19, 24, 1.1, 1.0, 2), ("Block", -25, 56, 3.4, 1.1, 2),
		("BlockSmall", -21, 45, 4.2, 0.9, 2), ("BoulderSmall", -17, 38, 0.4, 1.1, 1.6), ("Slab", -15.5, 14, 0.5, 1.0, 1.1), ("Slab", -14, 27, 2.6, 0.9, 1.0),
		("SlabSmall", -13, 4, 0.9, 1.1, 0.9), ("Slab", -14, 47, 0.2, 1.0, 0.9), ("Boulder", -18, -2, 1.9, 0.9, 1.4), ("SlabSmall", -12.5, 37, 3.6, 0.9, 0.7),
		("Chip", -11, 20, 1.0, 1.2, 0.5), ("Chip", -12, 10, 2.0, 0.9, 0.5),
		# right bank
		("Boulder", 15, 6, 0.8, 1.0, 1.0), ("Slab", 13, 18, 2.0, 0.9, 0.8), ("BoulderSmall", 12, 28, 0.1, 1.2, 0.8), ("SlabSmall", 14, 34, 1.3, 1.1, 1.0),
		("Block", 22, 44, 1.0, 0.9, 2), ("Boulder", 20, 58, 2.4, 1.2, 2), ("BlockSmall", 26, 26, 0.3, 0.8, 3), ("Chip", 11, 13, 0.4, 1.1, 0.5),
		# in the water
		("Boulder", -2, 16, 0.6, 0.65, 0.0), ("SlabSmall", -3, 15.5, 2.1, 0.8, 0.1), ("BoulderSmall", 5, 38, 1.4, 0.8, 0.0), ("Chip", 3, 27, 0.2, 1.3, 0.2),
	):
		place(pile, name, x, y, yaw, s, z)
	hero = kit.hero("Hero2", 7)
	hero.location = (17, 1, 1.9)
	pile.objects.link(hero)
	camera(sc, (1, -24, 11), (-2, 26, 5), 70)
	sc.render.filepath = os.path.join(OUT, "pile.png")
	bpy.ops.render.render(write_still=True)
	print("[rocks] rendered", flush=True)


def export():
	"""every piece into one glb for upload: each its own MeshPart, base at its origin"""
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "rock_kit.blend"))
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "RockKit.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	print("[rocks] exported", len(bpy.data.objects), flush=True)


if __name__ == "__main__":
	if ARGS[0] == "build":
		build()
	elif ARGS[0] == "export":
		export()
	else:
		render()
