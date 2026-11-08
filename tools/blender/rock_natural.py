"""Natural rocks by the displace method (the low poly rocks tutorial, private copy in research/rock_video), adapted to our kit and paint.

His steps: bevelled cube, subdivide 4 times, Displace with a Voronoi texture (distance squared, big size, low contrast), Decimate in steps.
Ours adds: a wide flat foot, per-piece shaping (long, flat, leaning), a fixed triangle target, dissolve of near-flat facets into big planes,
real bevels on the edges left, then the same bake.npz + paint_rock_kit.py + five-sheet route as the block kit. Voronoi is done in numpy so each
seed is repeatable. Origin at the base centre, studs, Z up.

  blender --background --python tools/blender/rock_natural.py -- build   art/kit/rocks_natural: rock_kit.blend, bake.npz, kit.json
  python tools/art/paint_rock_kit.py --kit rocks_natural
  blender --background --python tools/blender/rock_natural.py -- render  art/kit/rocks_natural: lineup.png
  blender --background --python tools/blender/rock_natural.py -- export  art/kit/rocks_natural/RockKit.glb
"""

import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rock_kit  # noqa: E402

OUT = os.path.join(rock_kit.ROOT, "art", "kit", "rocks_natural")
ARGS = sys.argv[sys.argv.index("--") + 1 :]

# name: (length, width, height), seed, cell size as a share of the smallest side, displace strength as a share of it, target triangles before bevel
SPECS = {
	"NatPebble": ((2.6, 2.2, 1.5), 2, 0.92, 0.34, 60),
	"NatStone": ((4.2, 3.4, 3.0), 3, 0.86, 0.37, 80),
	"NatRound": ((7.0, 6.0, 4.6), 5, 0.83, 0.39, 110),
	"NatChunk": ((9.0, 7.5, 6.5), 7, 0.80, 0.43, 130),
	"NatFlat": ((12.0, 8.0, 3.2), 8, 1.03, 0.34, 110),
	"NatLong": ((15.0, 7.0, 5.0), 11, 0.92, 0.40, 130),
	"NatBlock": ((12.0, 9.5, 9.5), 13, 0.75, 0.43, 150),
	"NatTall": ((8.5, 7.5, 13.0), 17, 0.71, 0.42, 140),
	"NatWall": ((20.0, 11.0, 13.0), 19, 0.63, 0.40, 180),
	"NatWide": ((30.0, 13.0, 16.0), 23, 0.57, 0.40, 230),
	"NatCrag": ((16.0, 12.0, 22.0), 29, 0.57, 0.46, 200),
	"NatLong2": ((40.0, 14.0, 17.0), 31, 0.52, 0.39, 280),
}
ATLASES = {"A": ["NatWide", "NatLong2"], "B": ["NatWall", "NatCrag", "NatTall", "NatBlock"], "C": ["NatPebble", "NatStone", "NatRound", "NatChunk", "NatFlat", "NatLong"]}
ATLAS_OF = {n: a for a, ns in ATLASES.items() for n in ns}
FLAT_ANGLE = 16  # degrees: facets closer than this merge into one plane
BEVEL = (0.12, 0.55, 0.07)  # smallest, largest, share of the smallest side
SEGMENTS = 2
SOFT_ANGLE = 20  # edges over this get a soft bevel
HIGHLIGHT_ANGLE = 40  # only edges over this get a painted highlight: lower, and the lines form a web
TARGET_SHARE = 0.32  # of each piece's target triangles: few, big planes
BOX = 5.5  # higher keeps more of the box, lower is a potato


def voronoi(p, cells, seed):
	"""distance-squared to the nearest of a jittered 3D grid of points, 0 at a point: his Voronoi"""
	r = np.random.RandomState(seed)
	g = np.floor(p / cells).astype(int)
	best = np.full(len(p), 1e9)
	lo, hi = g.min(0) - 1, g.max(0) + 1
	jit = {}
	for i in range(lo[0], hi[0] + 1):
		for j in range(lo[1], hi[1] + 1):
			for k in range(lo[2], hi[2] + 1):
				jit[(i, j, k)] = (np.array([i, j, k]) + r.uniform(0.1, 0.9, 3)) * cells
	pts = np.array(list(jit.values()))
	for chunk in np.array_split(np.arange(len(p)), max(1, len(p) // 4000)):
		d = ((p[chunk, None, :] - pts[None, :, :]) ** 2).sum(-1).min(1)
		best[chunk] = d
	return np.sqrt(best) / cells


def natural_bmesh(size, seed, cell_share, strength_share, target):
	L, W, H = size
	small = min(L, W, H)
	bm = bmesh.new()
	bmesh.ops.create_cube(bm, size=1.0)
	# his bevel + subdivide, as a rounded dense box: each point pushed out by a superellipse
	bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=26, use_grid_fill=True)
	bm.verts.ensure_lookup_table()
	P = np.array([v.co[:] for v in bm.verts]) * 2
	e = BOX
	n = (np.abs(P) ** e).sum(1) ** (1 / e)
	Q = P / n[:, None] * np.array([L / 2, W / 2, H / 2])
	Q[:, 2] = Q[:, 2] + H / 2  # 0 .. H
	# Displace: along the outward direction, by Voronoi
	out = Q - np.array([0, 0, H * 0.42])
	out /= np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-5)
	cells = small * cell_share
	v = np.clip(voronoi(Q, cells, seed), 0, 1)
	Q = Q - out * (1 - v)[:, None] * small * strength_share  # pits round each point leave ridges between them
	Q += out * small * strength_share * 0.5
	# a flat foot, wider than the top
	Q[:, 0] *= 1 + 0.16 * (1 - np.clip(Q[:, 2] / H, 0, 1))
	Q[:, 1] *= 1 + 0.16 * (1 - np.clip(Q[:, 2] / H, 0, 1))
	Q[:, 2] = np.maximum(Q[:, 2], 0)
	for vert, q in zip(bm.verts, Q):
		vert.co = q
	bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.01)
	# Decimate, in steps as he advises
	me = bpy.data.meshes.new("tmp")
	bm.to_mesh(me)
	bm.free()
	ob = bpy.data.objects.new("tmp", me)
	bpy.context.scene.collection.objects.link(ob)
	bpy.context.view_layer.objects.active = ob
	ob.select_set(True)
	bpy.ops.object.shade_flat()
	for step in (0.3, 0.3):
		m = ob.modifiers.new("d", "DECIMATE")
		m.ratio = step
		bpy.ops.object.modifier_apply(modifier=m.name)
	m = ob.modifiers.new("d", "DECIMATE")
	m.ratio = min(1.0, target * TARGET_SHARE / max(len(me.polygons), 1))
	bpy.ops.object.modifier_apply(modifier=m.name)
	bm = bmesh.new()
	bm.from_mesh(me)
	bpy.data.objects.remove(ob)
	bpy.data.meshes.remove(me)
	# facets into planes, then bevels on what's left: the same highlight rule as the block kit
	bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(FLAT_ANGLE), verts=list(bm.verts), edges=list(bm.edges))
	bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
	bm.normal_update()
	layer = bm.faces.layers.int.new("bevel")
	width = max(BEVEL[0], min(BEVEL[1], small * BEVEL[2]))
	soft = [ed for ed in bm.edges if ed.is_manifold and math.radians(SOFT_ANGLE) < ed.calc_face_angle(0) <= math.radians(HIGHLIGHT_ANGLE)]
	if soft:
		bmesh.ops.bevel(bm, geom=soft, offset=width * 0.7, offset_type="OFFSET", segments=SEGMENTS, profile=0.5, affect="EDGES", clamp_overlap=True)
		bm.normal_update()
	strong = [ed for ed in bm.edges if ed.is_manifold and ed.calc_face_angle(0) > math.radians(HIGHLIGHT_ANGLE)]
	res = bmesh.ops.bevel(bm, geom=strong, offset=width, offset_type="OFFSET", segments=SEGMENTS, profile=0.5, affect="EDGES", clamp_overlap=True)
	for f in res["faces"]:
		f[layer] = 1
	bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
	bm.normal_update()
	bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.8 and f.calc_center_median().z < H * 0.1], context="FACES")
	return bm


def build():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	joined = bmesh.new()
	piece = joined.faces.layers.int.new("piece")
	bevel = joined.faces.layers.int.new("bevel")
	sub = joined.faces.layers.int.new("sub")
	names = list(SPECS)
	x = 0.0
	offsets = {}
	for k, name in enumerate(names):
		size, seed, cs, ss, target = SPECS[name]
		x += size[0] / 2 + 12
		offsets[name] = x
		bm = natural_bmesh(size, seed, cs, ss, target)
		src = bm.faces.layers.int["bevel"]
		vm = {}
		for f in bm.faces:
			for v in f.verts:
				if v not in vm:
					vm[v] = joined.verts.new(v.co + Vector((x, 0, 0)))
			nf = joined.faces.new([vm[v] for v in f.verts])
			nf[piece], nf[bevel], nf[sub] = k, f[src], 0
		bm.free()
		x += size[0] / 2 + 12
	joined.normal_update()
	me = bpy.data.meshes.new("All")
	joined.to_mesh(me)
	joined.free()
	me.uv_layers.new(name="UV")
	obj = bpy.data.objects.new("All", me)
	sc.collection.objects.link(obj)
	rock_kit.layout_uvs(me, {a: {names.index(n) for n in ns} for a, ns in ATLASES.items()})
	me.calc_loop_triangles()
	uvd = me.uv_layers.active.data
	pa, ba = me.attributes["piece"].data, me.attributes["bevel"].data
	pos, uv, nor, pc, bv, fc = [], [], [], [], [], []
	for t in me.loop_triangles:
		pos.append([me.vertices[v].co[:] for v in t.vertices])
		uv.append([uvd[li].uv[:] for li in t.loops])
		nor.append(me.polygons[t.polygon_index].normal[:])
		pc.append(pa[t.polygon_index].value)
		bv.append(ba[t.polygon_index].value)
		fc.append(t.polygon_index)
	np.savez_compressed(os.path.join(OUT, "bake.npz"), pos=np.array(pos, np.float32), uv=np.array(uv, np.float32), nor=np.array(nor, np.float32), piece=np.array(pc), bevel=np.array(bv), face=np.array(fc), sub=np.zeros(len(pc), int), names=np.array(names),
		atlas=np.array([ATLAS_OF[n] for n in names]), offset=np.array([offsets[n] for n in names]), height=np.array([SPECS[n][0][2] for n in names]))
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
		rock_kit.smooth_area_weighted(pm)
		sc.collection.objects.link(bpy.data.objects.new(name, pm))
		pm.calc_loop_triangles()
		meta[name] = {"Size": list(SPECS[name][0]), "Tris": len(pm.loop_triangles), "Atlas": ATLAS_OF[name]}
	bpy.data.objects.remove(obj)
	json.dump(meta, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "rock_kit.blend"))
	print("[natural] tris", {k: v["Tris"] for k, v in meta.items()}, "total", sum(v["Tris"] for v in meta.values()), flush=True)


def material(atlas):
	m = bpy.data.materials.new("Nat" + atlas)
	m.use_nodes = True
	b = m.node_tree.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.85
	b.inputs["Specular IOR Level"].default_value = 0.2
	im = m.node_tree.nodes.new("ShaderNodeTexImage")
	im.image = bpy.data.images.load(os.path.join(OUT, f"RockKit_{atlas}_Moss.png"))
	m.node_tree.links.new(im.outputs["Color"], b.inputs["Base Color"])
	return m


def render():
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "rock_kit.blend"))
	sc = bpy.context.scene
	mats = {a: material(a) for a in ATLASES}
	for name in SPECS:
		bpy.data.meshes[name].materials.clear()
		bpy.data.meshes[name].materials.append(mats[ATLAS_OF[name]])
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	rock_kit.stage(sc)
	line = bpy.data.collections.new("Lineup")
	sc.collection.children.link(line)
	rock_kit.ground_plane(line, "2bab5e")
	order = sorted(SPECS, key=lambda n: SPECS[n][0][0] * SPECS[n][0][1] * SPECS[n][0][2])
	rows, cur, used = [], [], 0.0
	for name in order:
		w = SPECS[name][0][0] + 4
		if cur and used + w > 76:
			rows.append(cur)
			cur, used = [], 0.0
		cur.append(name)
		used += w
	rows.append(cur)
	y = -16.0
	for row in rows:
		x = -sum(SPECS[n][0][0] + 4 for n in row) / 2
		for name in row:
			x += SPECS[name][0][0] / 2 + 2
			rock_kit.place(line, name, x, y, 0.3)
			x += SPECS[name][0][0] / 2 + 2
		y += max(SPECS[n][0][1] for n in row) + 7
	rock_kit.kit.hero("Hero", 7, line).location = (-42, -18, 0)
	rock_kit.camera(sc, (0, -74, 34), (0, y * 0.3, 6), 45)
	sc.render.filepath = os.path.join(OUT, "lineup.png")
	bpy.ops.render.render(write_still=True)
	print("[natural] rendered", flush=True)


def export():
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "rock_kit.blend"))
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "RockKit.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	print("[natural] exported", flush=True)


{"build": build, "render": render, "export": export}[ARGS[0]]()
