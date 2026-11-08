"""Small stone pieces for placing all round the hub (docs/style/cobble-kit.md): edging stones round flower beds and planters, and
compact cut setts that border a paved area. Each piece is a run of several stones sharing one painted texture per style, so a bed's
border is a handful of drags instead of dozens.

  blender --background --python tools/blender/cobble_kit.py -- build     art/kit/cobbles: cobble_kit.blend, bake.npz, kit.json
  python tools/art/paint_cobble_kit.py                                   Cobble_<Style>_Color.png (+ _Moss) and Paving_Color.png
  blender --background --python tools/blender/cobble_kit.py -- render    lineup.png and the garden scenes per style
  blender --background --python tools/blender/cobble_kit.py -- export    CobbleKit.glb

Styles (the user is iterating on the look):
- Pebble: soft rounded stones (superellipsoids with gentle lumps), smooth shading, blue-grey slate like the user's reference.
- Chisel: the stylized rock kit's stones (flat planes, bevels that catch a painted edge), smaller, in its pale grey.
- Sett: cut paving stones, bevelled boxes in tidy courses, warm grey, for the border round a paved area.

How pieces chain (studs, Z up, origin at the start of a run, on the ground): straights run 8 along +X. A curve turns left by its angle
round a centre on +Y; turned 180 degrees it runs backwards, so it turns right. Curves are cut so whole circles come out even:
radius 6 takes 8 pieces, 12 takes 12, 24 takes 24 (setts: radius 8, 16 and 32, 8, 16 and 32 pieces).
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import rock_kit as rk  # noqa: E402

OUT = os.path.join(ROOT, "art", "kit", "cobbles")
ARGS = sys.argv[sys.argv.index("--") + 1 :]
# how far stones sit into the ground: edging well down (the user: "shorter and more into the ground"), setts just enough that
# none floats on a slope
SINKS = {"Pebble": 0.32, "Chisel": 0.32, "Sett": 0.12}


def spow(x, e):
	return math.copysign(abs(x) ** e, x)


# ---------------------------------------------------------------------------------------------------------------- one stone per style
def pebble(L, W, H, seed):
	"""a soft rounded stone: a superellipsoid (rounded box) with low lumps and a slight lean. No bevel faces: smooth all over"""
	SINK = SINKS["Pebble"]
	r = random.Random(seed)
	eh, ev = r.uniform(0.42, 0.55), r.uniform(0.55, 0.72)  # under 1 squares it off: the plan a rounded box, the profile a dome
	bumps = [(k, r.uniform(0.02, 0.05), r.uniform(0, 2 * math.pi)) for k in (2, 3, 5)]
	lean = (r.uniform(-0.05, 0.05) * L, r.uniform(-0.05, 0.05) * W)
	crown = r.uniform(0.0, 0.08)
	nu, nv = 20, 7
	bm = bmesh.new()
	rings = []
	for j in range(nv):
		phi = -0.25 + (math.pi / 2 + 0.25) * j / nv
		ring = []
		for i in range(nu):
			th = 2 * math.pi * i / nu
			k = 1 + sum(a * math.cos(n * th + ph) for n, a, ph in bumps)
			c = spow(math.cos(phi), ev)
			x = L / 2 * k * c * spow(math.cos(th), eh)
			y = W / 2 * k * c * spow(math.sin(th), eh)
			z = (H + SINK) * spow(math.sin(phi), ev) * (1 + crown * c) - SINK
			t = max(z, 0) / H
			ring.append(bm.verts.new((x + lean[0] * t, y + lean[1] * t, z)))
		rings.append(ring)
	top = bm.verts.new((lean[0], lean[1], H))
	for j in range(nv - 1):
		for i in range(nu):
			bm.faces.new((rings[j][i], rings[j][(i + 1) % nu], rings[j + 1][(i + 1) % nu], rings[j + 1][i]))
	for i in range(nu):
		bm.faces.new((rings[-1][i], rings[-1][(i + 1) % nu], top))
	bm.faces.layers.int.new("bevel")
	bm.normal_update()
	return bm


def chisel(L, W, H, seed):
	"""the rock kit's stone (flat planes, bevelled edges flagged for the painted highlight), sunk well in"""
	SINK = SINKS["Chisel"]
	bm, _ = rk.rock_bmesh((L, W, H + SINK), seed, 1)
	bmesh.ops.translate(bm, vec=Vector((0, 0, -SINK)), verts=list(bm.verts))
	return bm


def sett(L, W, H, seed):
	"""a cut paving stone: a box with a softly domed top and bevelled edges, a touch out of square"""
	SINK = SINKS["Sett"]
	r = random.Random(seed)
	bm = bmesh.new()
	bmesh.ops.create_cube(bm, size=1.0)
	for v in bm.verts:
		x, y, z = v.co
		sx = L / 2 * (1 + r.uniform(-0.03, 0.03))
		sy = W / 2 * (1 + r.uniform(-0.05, 0.05))
		v.co = Vector((x * 2 * sx, y * 2 * sy, (z + 0.5) * (H + SINK) * (1 + (r.uniform(-0.06, 0.04) if z > 0 else 0)) - SINK))
	layer = bm.faces.layers.int.new("bevel")
	res = bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(L, W, H) * 0.22, offset_type="OFFSET", segments=2, profile=0.6, affect="EDGES", clamp_overlap=True)
	for f in res["faces"]:
		f[layer] = 1
	top = [v for v in bm.verts if v.co.z > H - 0.02]
	cx, cy = sum((v.co.x for v in top), 0.0) / len(top), sum((v.co.y for v in top), 0.0) / len(top)
	for v in top:  # a gentle dome: the middle stands a little proud of the corners
		d = math.hypot((v.co.x - cx) / (L / 2), (v.co.y - cy) / (W / 2))
		v.co.z += 0.05 * max(0.0, 1 - d)
	bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.9], context="FACES")
	bm.normal_update()
	return bm


SHAPES = {"Pebble": pebble, "Chisel": chisel, "Sett": sett}


# ---------------------------------------------------------------------------------------------------------------- runs of stones
def along_line(length, stones, r, gap=(0.08, 0.28), lateral=0.1, yaw=7.0, y=0.0):
	"""stones (length, width, height) packed along +X from 0 to `length`, each nudged sideways and turned a little.
	Returns placements (x, y, yaw, (L, W, H))."""
	out, x = [], 0.0
	sizes = []
	while x < length - 0.3:
		L, W, H = stones(r)
		g = r.uniform(*gap)
		if x + L > length:
			L = length - x - 0.05
			if L < 0.55:
				break
		sizes.append((x + L / 2, (L, W, H), g))
		x += L + g
	slack = length - x
	for i, (cx, s, g) in enumerate(sizes):  # spread the leftover so the run ends at `length`
		cx += slack * (i + 0.5) / max(len(sizes), 1)
		out.append((cx, y + r.uniform(-lateral, lateral), math.radians(r.uniform(-yaw, yaw)), s))
	return out


def along_arc(radius, angle, stones, r, gap=(0.08, 0.28), lateral=0.1, yaw=7.0, offset=0.0):
	"""the same along a left-turning arc that starts at the origin heading +X (centre at (0, radius)); offset moves the row
	toward the centre (positive) or away"""
	R = radius - offset
	length = R * math.radians(angle)
	out = []
	for s, y, a, size in along_line(length, stones, r, gap, lateral, yaw):
		t = s / R
		rr = R - y  # a sideways nudge toward the centre shortens the radius
		out.append((rr * math.sin(t), radius - rr * math.cos(t), t + a, size))
	return out


def edging(r):
	"""bed edging: low, long stones (visible height 0.5 to 0.8, the rest in the ground)"""
	return (r.uniform(1.6, 2.5), r.uniform(0.72, 0.98), r.uniform(0.5, 0.8))


ROW_W = 1.3  # a paving border's width: one row of stones


def setts(r):
	"""paving border stones: one row of larger, rectangular, varied stones, the same low height as before"""
	return (r.uniform(1.5, 2.6), r.uniform(ROW_W - 0.14, ROW_W + 0.1), r.uniform(0.38, 0.46))


SETT_GAP = (0.02, 0.06)  # tight: the stones fit against each other


def broken(r):
	"""pieces of a broken border stone, for the loose cluster"""
	return (r.uniform(0.7, 1.3), r.uniform(0.6, 1.0), r.uniform(0.3, 0.42))


def kerb(kind, length_or_arc, seed):
	"""a paving border: one row of fitted stones along a line or a left-turning arc"""
	r = random.Random(seed)
	if kind == "line":
		return along_line(length_or_arc, setts, r, SETT_GAP, 0.025, 1.2)
	radius, angle = length_or_arc
	return along_arc(radius, angle, setts, r, SETT_GAP, 0.025, 1.2)


def corner_block(seed):
	"""one square stone where two border rows meet"""
	r = random.Random(seed)
	return [(0.0, 0.0, math.radians(r.uniform(-2, 2)), (ROW_W, ROW_W, 0.44))]


def cluster(seed, n, stones, spread):
	"""a few loose stones, for broken edges and to scatter where a path wears into the grass"""
	r = random.Random(seed)
	out = []
	for _ in range(n):
		for _try in range(30):
			x, y = r.uniform(-spread, spread), r.uniform(-spread * 0.6, spread * 0.6)
			if all(math.hypot(x - o[0], y - o[1]) > 1.6 for o in out):
				break
		out.append((x, y, r.uniform(0, math.pi), stones(r)))
	return out


def singles():
	return {
		"Stone1": [(0, 0, 0.2, (1.4, 0.75, 0.45))],
		"Stone2": [(0, 0, -0.4, (1.9, 0.95, 0.6))],
		"Stone3": [(0, 0, 0.9, (2.4, 1.1, 0.7))],
		"Stone4": [(0, 0, 0.1, (3.0, 1.35, 0.85))],
		"Stone5": [(0, 0, 1.4, (1.6, 1.0, 0.75))],
	}


def pieces():
	"""name -> (style, placements, tilt amount). Placement: (x, y, yaw, (L, W, H))"""
	P = {}
	for style, base in (("Pebble", 100), ("Chisel", 200)):
		for name, pl in singles().items():
			P[f"{style}_{name}"] = (style, pl, 3.0)
		r = random.Random(base + 1)
		P[f"{style}_Straight8A"] = (style, along_line(8.0, edging, r), 3.0)
		r = random.Random(base + 2)
		P[f"{style}_Straight8B"] = (style, along_line(8.0, edging, r), 3.0)
		for radius, angle in ((6, 45.0), (12, 30.0), (24, 15.0)):
			r = random.Random(base + radius)
			P[f"{style}_Curve{radius}"] = (style, along_arc(radius, angle, edging, r), 3.0)
		r = random.Random(base + 90)
		P[f"{style}_Corner"] = (style, along_arc(2.5, 90.0, edging, r, gap=(0.06, 0.16)), 3.0)
		P[f"{style}_Cluster"] = (style, cluster(base + 7, 4, edging, 2.2), 9.0)
	P["Sett_Single"] = ("Sett", [(0, 0, 0.0, (1.9, ROW_W, 0.42))], 0.0)
	P["Sett_Row8A"] = ("Sett", kerb("line", 8.0, 301), 1.0)
	P["Sett_Row8B"] = ("Sett", kerb("line", 8.0, 302), 1.0)
	P["Sett_Row4"] = ("Sett", kerb("line", 4.0, 303), 1.0)
	P["Sett_Row2"] = ("Sett", kerb("line", 2.0, 304), 1.0)
	for radius, angle in ((8, 45.0), (16, 22.5), (32, 11.25)):
		P[f"Sett_Curve{radius}"] = ("Sett", kerb("arc", (radius, angle), 300 + radius), 1.0)
	P["Sett_Corner"] = ("Sett", corner_block(340), 1.0)
	P["Sett_Cluster"] = ("Sett", cluster(341, 5, broken, 2.2), 8.0)
	return P


ATLASES = ("Pebble", "Chisel", "Sett")


# ---------------------------------------------------------------------------------------------------------------- build
def build():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	P = pieces()
	names = list(P)
	joined = bmesh.new()
	piece_l = joined.faces.layers.int.new("piece")
	bevel_l = joined.faces.layers.int.new("bevel")
	sub_l = joined.faces.layers.int.new("sub")
	offsets, meta = {}, {}
	x0 = 0.0
	for k, name in enumerate(names):
		style, places, tilt = P[name]
		shape = SHAPES[style]
		xs = [p[0] for p in places]
		span = (max(xs) - min(xs)) + 4 if xs else 4
		x0 += span / 2 + 6
		offsets[name] = x0
		r = random.Random(1000 + k)
		for j, (px, py, yaw, size) in enumerate(places):
			bm = shape(*size, seed=5000 + k * 50 + j)
			turn = Euler((math.radians(r.uniform(-tilt, tilt)), math.radians(r.uniform(-tilt, tilt)), yaw))
			for v in bm.verts:
				v.co.rotate(turn)
				v.co += Vector((px + x0, py, 0))
			src = bm.faces.layers.int["bevel"]
			vm = {}
			for f in bm.faces:
				for v in f.verts:
					if v not in vm:
						vm[v] = joined.verts.new(v.co)
				nf = joined.faces.new([vm[v] for v in f.verts])
				nf[piece_l], nf[bevel_l], nf[sub_l] = k, f[src], j
			bm.free()
		x0 += span / 2 + 6
		lo = min(p[0] - p[3][0] for p in places), min(p[1] - p[3][1] for p in places)
		hi = max(p[0] + p[3][0] for p in places), max(p[1] + p[3][1] for p in places)
		meta[name] = {"Style": style, "Stones": len(places), "Bounds": [round(lo[0], 2), round(lo[1], 2), round(hi[0], 2), round(hi[1], 2)], "Height": round(max(p[3][2] for p in places), 2)}
	joined.normal_update()
	me = bpy.data.meshes.new("CobbleKitAll")
	joined.to_mesh(me)
	joined.free()
	obj = bpy.data.objects.new("CobbleKitAll", me)
	sc.collection.objects.link(obj)
	rk.layout_uvs(me, {a: {names.index(n) for n in names if P[n][0] == a} for a in ATLASES})
	# what the painter needs, per triangle: corner positions, uvs and smooth normals
	me.calc_loop_triangles()
	smooth = vertex_normals(me)
	uvd = me.uv_layers.active.data
	pa, ba, sa = me.attributes["piece"].data, me.attributes["bevel"].data, me.attributes["sub"].data
	pos, uv, nor, cn, pc, bv, fc, sb = [], [], [], [], [], [], [], []
	for t in me.loop_triangles:
		pos.append([me.vertices[v].co[:] for v in t.vertices])
		uv.append([uvd[li].uv[:] for li in t.loops])
		nor.append(me.polygons[t.polygon_index].normal[:])
		cn.append([smooth[v] for v in t.vertices])
		pc.append(pa[t.polygon_index].value)
		bv.append(ba[t.polygon_index].value)
		fc.append(t.polygon_index)
		sb.append(sa[t.polygon_index].value)
	np.savez_compressed(os.path.join(OUT, "bake.npz"), pos=np.array(pos, np.float32), uv=np.array(uv, np.float32), nor=np.array(nor, np.float32), cnor=np.array(cn, np.float32),
						piece=np.array(pc), bevel=np.array(bv), face=np.array(fc), sub=np.array(sb), names=np.array(names), atlas=np.array([P[n][0] for n in names]),
						offset=np.array([offsets[n] for n in names]))
	for k, name in enumerate(names):
		bm = bmesh.new()
		bm.from_mesh(me)
		layer = bm.faces.layers.int["piece"]
		bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != k], context="FACES")
		bmesh.ops.translate(bm, vec=Vector((-offsets[name], 0, 0)), verts=list(bm.verts))
		pm = bpy.data.meshes.new(name)
		bm.to_mesh(pm)
		bm.free()
		rk.smooth_area_weighted(pm)
		sc.collection.objects.link(bpy.data.objects.new(name, pm))
		pm.calc_loop_triangles()
		meta[name]["Tris"] = len(pm.loop_triangles)
	bpy.data.objects.remove(obj)
	json.dump(meta, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "cobble_kit.blend"))
	print("[cobbles] built", len(names), "pieces, tris", sum(m["Tris"] for m in meta.values()), {s: sum(m["Tris"] for m in meta.values() if m["Style"] == s) for s in ATLASES}, flush=True)


def vertex_normals(me):
	"""area-weighted vertex normals (what the exported piece shades with), for the painter's light"""
	acc = [Vector() for _ in me.vertices]
	for p in me.polygons:
		w = p.normal * p.area
		for v in p.vertices:
			acc[v] += w
	return [tuple(a.normalized()) for a in acc]


# ---------------------------------------------------------------------------------------------------------------- render
def kit_material(atlas, moss=False):
	m = bpy.data.materials.new(f"Cobble{atlas}{'Moss' if moss else ''}")
	m.use_nodes = True
	nt = m.node_tree
	b = nt.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.85
	b.inputs["Specular IOR Level"].default_value = 0.18
	im = nt.nodes.new("ShaderNodeTexImage")
	path = os.path.join(OUT, f"Cobble_{atlas}_{'Moss' if moss else 'Color'}.png")
	im.image = bpy.data.images.load(path)
	nt.links.new(im.outputs["Color"], b.inputs["Base Color"])
	return m


def tiled_material(name, path, studs):
	m = rk.flat_material(name, "ffffff")
	nt = m.node_tree
	tc, mp, im = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping"), nt.nodes.new("ShaderNodeTexImage")
	mp.inputs["Scale"].default_value = (1 / studs, 1 / studs, 1)
	im.image = bpy.data.images.load(path)
	nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
	nt.links.new(mp.outputs["Vector"], im.inputs["Vector"])
	nt.links.new(im.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
	return m


def plane(coll, name, x0, y0, x1, y1, z, mat):
	me = bpy.data.meshes.new(name)
	me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
	me.materials.append(mat)
	o = bpy.data.objects.new(name, me)
	coll.objects.link(o)
	return o


OVERRIDE = {}  # piece prefix -> material, for the garden being laid out (a colourway painted on the same meshes)


def put(coll, name, x, y, yaw):
	o = bpy.data.objects.new(name, bpy.data.meshes[name])
	o.location = (x, y, 0)
	o.rotation_euler = (0, 0, yaw)
	coll.objects.link(o)
	mat = OVERRIDE.get(name.split("_")[0])
	if mat:
		o.material_slots[0].link = "OBJECT"
		o.material_slots[0].material = mat
	return o


def chain(coll, names, x, y, heading, curve_spec):
	"""lay pieces end to end. names: piece names; curve_spec: name -> (radius, angle) for curves (turn left)"""
	for n in names:
		put(coll, n, x, y, heading)
		if n in curve_spec:
			R, A = curve_spec[n]
			a = math.radians(A)
			lx, ly = R * math.sin(a), R - R * math.cos(a)
		else:
			lx, ly, a = 8.0, 0.0, 0.0
		x += lx * math.cos(heading) - ly * math.sin(heading)
		y += lx * math.sin(heading) + ly * math.cos(heading)
		heading += a
	return x, y, heading


def garden(coll, style):
	"""the test patch: a round bed and a long rounded bed edged in `style`, a paved square with a stone border, a person"""
	import pink_cottage as pc

	curves = {f"{style}_Curve6": (6, 45.0), f"{style}_Corner": (2.5, 90.0), "Sett_Curve8": (8, 45.0)}
	# round bed, radius 6: eight curves
	chain(coll, [f"{style}_Curve6"] * 8, 14.0, 4.0, 0.0, curves)
	# a long bed: two straights, a corner, two straights back, a corner
	seq = [f"{style}_Straight8A", f"{style}_Straight8B", f"{style}_Corner", f"{style}_Corner", f"{style}_Straight8B", f"{style}_Straight8A", f"{style}_Corner", f"{style}_Corner"]
	chain(coll, seq, -20.0, 9.0, 0.0, curves)
	# the paved square 24 x 16 with its border, one row of fitted stones outside it, a square stone at each corner
	x0, y0, x1, y1 = -22.0, -16.0, 2.0, 0.0
	pav = tiled_material("Paving", os.path.join(OUT, "Paving_Color.png"), 16.0)
	plane(coll, "Paved", x0, y0, x1, y1, 0.03, pav)
	b = ROW_W / 2 + 0.03
	rows = ["Sett_Row8A", "Sett_Row8B"]
	for i in range(3):
		put(coll, rows[i % 2], x0 + 8 * i, y0 - b, 0.0)
		put(coll, rows[(i + 1) % 2], x1 - 8 * i, y1 + b, math.pi)
	for i in range(2):
		put(coll, rows[i % 2], x1 + b, y0 + 8 * i, math.pi / 2)
		put(coll, rows[(i + 1) % 2], x0 - b, y1 - 8 * i, -math.pi / 2)
	for cx, cy in ((x0 - b, y0 - b), (x1 + b, y0 - b), (x1 + b, y1 + b), (x0 - b, y1 + b)):
		put(coll, "Sett_Corner", cx, cy, 0.0)
	# a border path curving away from the square's corner
	chain(coll, ["Sett_Row8B", "Sett_Curve8", "Sett_Curve8"], x1 + b + ROW_W / 2 + 0.03, y0 - b, 0.0, curves)
	put(coll, f"{style}_Cluster", 6.5, -4.0, 0.6)
	put(coll, f"{style}_Stone3", 4.0, 12.5, 0.4)
	put(coll, f"{style}_Stone1", 5.6, 13.6, 1.4)
	put(coll, "Sett_Cluster", -9.0, 3.2, 0.3)
	# flowers: white daisies in the round bed, pink and white in the long one, over dark green leaves
	made = []
	rnd = random.Random(4)
	made += pc.blob("LeavesRound", (14.0, 10.0, 0.5), (4.7, 4.7, 0.9), 70, 0.62, 61, ("2f6e3c", "4f9a48", "86c06a"), up_lean=0.6)
	made.append(pc.flowers("DaisiesRound", [Vector((14 + rnd.gauss(0, 2.2), 10 + rnd.gauss(0, 2.2), 1.2 + rnd.random() * 0.5)) for _ in range(140)], "f6f4ea", size=0.26, seed=62))
	made += pc.blob("LeavesLong", (-12.0, 11.5, 0.5), (8.8, 1.7, 0.8), 70, 0.58, 63, ("2f6e3c", "4f9a48", "86c06a"), up_lean=0.6)
	made.append(pc.flowers("FlowersLong", [Vector((-12 + rnd.uniform(-8.6, 8.6), 11.5 + rnd.gauss(0, 0.8), 1.15 + rnd.random() * 0.4)) for _ in range(110)], "f2a6c0", size=0.26, seed=64))
	made.append(pc.flowers("FlowersLong2", [Vector((-12 + rnd.uniform(-8.6, 8.6), 11.5 + rnd.gauss(0, 0.8), 1.15 + rnd.random() * 0.4)) for _ in range(70)], "f6f4ea", size=0.24, seed=65))
	for o in made:
		if o.name in bpy.context.scene.collection.objects:
			bpy.context.scene.collection.objects.unlink(o)
		if o.name not in coll.objects:
			coll.objects.link(o)
		o.data.materials.clear()
		o.data.materials.append(pc.vcol_material())
	hero = kit.hero("Hero" + style, 7, coll)
	hero.location = (-4.0, -6.0, 0.03)


def render():
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cobble_kit.blend"))
	sc = bpy.context.scene
	P = json.load(open(os.path.join(OUT, "kit.json")))
	moss = "--moss" in ARGS
	mats = {a: kit_material(a, moss and a != "Sett") for a in ATLASES}
	for name, m in P.items():
		me = bpy.data.meshes[name]
		me.materials.clear()
		me.materials.append(mats[m["Style"]])
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	rk.stage(sc, sky="8cc8ee")
	grass = rk.flat_material("Grass", "4c9a4e")
	tag = "_moss" if moss else ""
	# the lineup: every piece, by style
	line = bpy.data.collections.new("Lineup")
	sc.collection.children.link(line)
	plane(line, "Floor", -200, -200, 200, 200, 0.0, grass)
	y = 0.0
	for style in ATLASES:
		row = [n for n, m in P.items() if m["Style"] == style]
		x = -(sum(P[n]["Bounds"][2] - P[n]["Bounds"][0] + 2.0 for n in row)) / 2
		for n in row:
			b = P[n]["Bounds"]
			w = b[2] - b[0]
			put(line, n, x - b[0], y - (b[1] + b[3]) / 2, 0.0)
			x += w + 2.0
		y += 7.0
	kit.hero("HeroLine", 7, line).location = (-52, 0, 0)
	rk.camera(sc, (0, -62, 40), (0, 7, 0), 42)
	sc.render.filepath = os.path.join(OUT, "renders", f"lineup{tag}.png")
	bpy.ops.render.render(write_still=True)
	for o in list(line.objects):
		o.hide_render = True
	cool = kit_material("SettCool")
	slate = kit_material("ChiselSlate", moss) if os.path.exists(os.path.join(OUT, "Cobble_ChiselSlate_Color.png")) else None
	gardens = [("Pebble", "Pebble", {"Sett": cool}), ("Chisel", "Chisel", {})]
	if slate:
		gardens.append(("ChiselSlate", "Chisel", {"Sett": cool, "Chisel": slate}))  # Chisel's painting in Pebble's colours
	for label, style, override in gardens:
		OVERRIDE.clear()
		OVERRIDE.update(override)
		g = bpy.data.collections.new("Garden" + label)
		sc.collection.children.link(g)
		plane(g, "Lawn" + label, -200, -200, 200, 200, 0.0, grass)
		garden(g, style)
		for view, pos, target, fov in (("high", (2, -48, 46), (-4, 0, 0), 38), ("eye", (-30, -30, 6.5), (-6, 2, 1.2), 55), ("close", (6.5, -9.0, 4.2), (10.5, 2.5, 0.4), 50)):
			for o in [o for o in sc.objects if o.type == "CAMERA"]:
				bpy.data.objects.remove(o)
			rk.camera(sc, pos, target, fov)
			sc.render.filepath = os.path.join(OUT, "renders", f"{label.lower()}_{view}{tag}.png")
			bpy.ops.render.render(write_still=True)
		for o in list(g.objects):
			o.hide_render = True
	print("[cobbles] rendered", flush=True)


def export():
	"""the chosen pieces into one glb for upload (`export Chisel,Sett`: only those styles), each its own MeshPart; each piece's exact
	box goes into kit.json, so Studio can put its pivot back at the start of its run, on the ground"""
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cobble_kit.blend"))
	keep = ARGS[1].split(",") if len(ARGS) > 1 else None
	meta = json.load(open(os.path.join(OUT, "kit.json")))
	bpy.ops.object.select_all(action="DESELECT")
	n = 0
	for o in bpy.data.objects:
		if o.type != "MESH" or (keep and o.name.split("_")[0] not in keep):
			continue
		o.select_set(True)
		vs = [v.co for v in o.data.vertices]
		meta[o.name]["Box"] = [round(min(v[i] for v in vs), 4) for i in range(3)] + [round(max(v[i] for v in vs), 4) for i in range(3)]
		n += 1
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "CobbleKit.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	json.dump(meta, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	print("[cobbles] exported", n, "pieces", flush=True)


if __name__ == "__main__":
	{"build": build, "render": render, "export": export}[ARGS[0]]()
