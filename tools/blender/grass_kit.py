"""Grass building blocks (docs/style/grass.md), shared by tools/blender/grass_bench.py and vale_beauty.py.

Community practice built in: blade normals point straight up (both faces) so grass shades like the ground under it, and
grass casts no shadows (its own object, shadow visibility off), as in Roblox; each instance
takes the ground colour under it (Sample Nearest Surface -> instance attribute "ground_col", read by the material as an
Instancer attribute) times the clump's own grey root-to-tip gradient; clumps, not single blades; dense only near the
camera. In Roblox the same idea is a MeshPart tuft whose Color is set to the ground colour under it.
"""

import math
import os

import bpy
from mathutils import Vector

import kit

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def lin(h):
	return kit.to_linear(kit.srgb(h))


def blade_clump(name, seed, blades, height, width, spread, grey=True, chunky=False, low=0.55, high=1.3):
	"""geometry like kv.field_grass; with grey=True the colours are multipliers (low at the root to high at the tip, 0.55
	to 1.3 by default; about 0.85 to 1.1 makes blades that melt into the ground) for a material that brings the ground
	colour; normals point up"""
	p = kit.Piece(seed)
	r = p.rng
	for _ in range(blades):
		a = r.uniform(0, math.tau)
		dd = r.uniform(0, spread)
		root = Vector((math.cos(a) * dd, math.sin(a) * dd, -0.05))
		h = height * r.uniform(0.55, 1.15)
		bend = r.uniform(0.15, 0.55)
		lean = Vector((math.cos(a + r.uniform(-0.6, 0.6)), math.sin(a + r.uniform(-0.6, 0.6)), 0))
		w = width * r.uniform(0.75, 1.25)
		side = Vector((-lean.y, lean.x, 0)) * w
		tip = root + lean * h * bend + Vector((0, 0, h))
		if chunky:
			p.poly([root - side * 1.6, root + side * 1.6, tip], "999999")
			continue
		m1 = root + lean * h * bend * 0.3 + Vector((0, 0, h * 0.55))
		p.poly([root - side, root + side, m1 + side * 0.6, m1 - side * 0.6], "999999")
		p.poly([m1 - side * 0.6, m1 + side * 0.6, tip], "999999")
	p.bm.normal_update()
	tint = lambda t: (low + (high - low) * t,) * 3
	for f in p.bm.faces:
		for lp in f.loops:
			t = max(0.0, min(1.0, lp.vert.co.z / height))
			lp[p.col] = (*tint(t), 1.0) if grey else (*kit.to_linear(kit.mix("grass_base", "grass_tip", t)), 1.0)
	obj = p.finish(name, None, smooth=True)
	obj.data.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(obj.data.vertices))
	return obj


def fern(name, seed, fronds=8, length=1.8, grey=True):
	"""a fern for the forest floor: a rosette of arching fronds, each a tapering strip with leaflets cut as zigzag
	triangles along it; grey multipliers (0.7 at the heart to 1.15 at the tips) for the matched material; normals up"""
	p = kit.Piece(seed)
	r = p.rng
	for _ in range(fronds):
		a = r.uniform(0, math.tau)
		L = length * r.uniform(0.7, 1.15)
		lift = r.uniform(0.45, 0.8)
		d = Vector((math.cos(a), math.sin(a), 0))
		side = Vector((-d.y, d.x, 0))
		n = 5
		pts = [d * (L * t) + Vector((0, 0, L * lift * math.sin(math.pi * t * 0.85))) for t in (k / n for k in range(n + 1))]
		for k in range(n):  # leaflets: a triangle each side of every segment, shrinking toward the tip
			w = L * 0.22 * (1 - k / n) + 0.05
			mid = (pts[k] + pts[k + 1]) / 2
			for sd in (-1, 1):
				p.poly([pts[k], pts[k + 1], mid + side * sd * w + Vector((0, 0, -0.05))][:: sd], "999999")
	p.bm.normal_update()
	for f in p.bm.faces:
		for lp in f.loops:
			t = min(1.0, (lp.vert.co.xy.length / length))
			lp[p.col] = ((0.7 + 0.45 * t,) * 3 + (1.0,)) if grey else (0.2, 0.4, 0.15, 1.0)
	obj = p.finish(name, None, smooth=True)
	obj.data.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(obj.data.vertices))
	return obj


def card_tuft(name, seed):
	"""two crossed vertical cards (a tuft texture), normals up"""
	p = kit.Piece(seed)
	uvl = p.bm.loops.layers.uv.new("UV")
	for k in range(2):
		a = k * math.pi / 2 + 0.3
		s = Vector((math.cos(a), math.sin(a), 0)) * 0.9
		f = p.bm.faces.new([p.bm.verts.new(q) for q in (-s + Vector((0, 0, -0.05)), s + Vector((0, 0, -0.05)), s + Vector((0, 0, 1.4)), -s + Vector((0, 0, 1.4)))])
		for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
			lp[uvl].uv = uv
			lp[p.col] = (1, 1, 1, 1)
	obj = p.finish(name, None, smooth=True)
	obj.data.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(obj.data.vertices))
	return obj


def matched_material(name, texture=None, tint="ffffff", vary=None):
	"""ground colour (from each instance) x the clump's own grey gradient (or a card texture) x tint, lit exactly like
	the ground: the shading normal is straight up on both faces of every blade (a blade seen from behind would otherwise
	get its normal flipped downward and lose the sun). vary = {"Light": l, "Hue": h}: each instance's "vary" attribute
	(0..1) makes it up to l lighter or darker and h warmer or cooler, averaging exactly the ground colour."""
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
	bsdf.inputs["Roughness"].default_value = 0.85
	if "Specular IOR Level" in bsdf.inputs:
		bsdf.inputs["Specular IOR Level"].default_value = 0.15
	up = nt.nodes.new("ShaderNodeCombineXYZ")
	up.inputs["Z"].default_value = 1.0
	nt.links.new(up.outputs["Vector"], bsdf.inputs["Normal"])
	gc = nt.nodes.new("ShaderNodeAttribute")
	gc.attribute_type = "INSTANCER"
	gc.attribute_name = "ground_col"
	mul = nt.nodes.new("ShaderNodeMix")
	mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
	mul.inputs["Factor"].default_value = 1.0
	nt.links.new(gc.outputs["Color"], mul.inputs["A"])
	if texture:
		img = nt.nodes.new("ShaderNodeTexImage")
		img.image = bpy.data.images.load(os.path.join(ROOT, "art", "kit", "textures", texture), check_existing=True)
		nt.links.new(img.outputs["Color"], mul.inputs["B"])
		cut = nt.nodes.new("ShaderNodeMath")
		cut.operation = "GREATER_THAN"
		cut.inputs[1].default_value = 0.5
		nt.links.new(img.outputs["Alpha"], cut.inputs[0])
		nt.links.new(cut.outputs["Value"], bsdf.inputs["Alpha"])
		try:
			m.surface_render_method = "DITHERED"
		except AttributeError:
			pass
		m.use_backface_culling = False
	else:
		vc = nt.nodes.new("ShaderNodeVertexColor")
		vc.layer_name = "Col"
		nt.links.new(vc.outputs["Color"], mul.inputs["B"])
	t2 = nt.nodes.new("ShaderNodeMix")
	t2.data_type, t2.blend_type = "RGBA", "MULTIPLY"
	t2.inputs["Factor"].default_value = 1.0
	t2.inputs["B"].default_value = (*lin(tint), 1)
	nt.links.new(mul.outputs["Result"], t2.inputs["A"])
	last = t2.outputs["Result"]
	if vary:  # s = -1..1 per instance: (1 + l*s) lighter/darker, (1 + h*s, 1, 1 - h*s) warmer/cooler; mean 1
		va = nt.nodes.new("ShaderNodeAttribute")
		va.attribute_type = "INSTANCER"
		va.attribute_name = "vary"
		sgn = nt.nodes.new("ShaderNodeMath")
		sgn.operation = "MULTIPLY_ADD"
		sgn.inputs[1].default_value, sgn.inputs[2].default_value = 2.0, -1.0
		nt.links.new(va.outputs["Fac"], sgn.inputs[0])

		def lin_term(k):
			q = nt.nodes.new("ShaderNodeMath")
			q.operation = "MULTIPLY_ADD"
			q.inputs[1].default_value, q.inputs[2].default_value = k, 1.0
			nt.links.new(sgn.outputs["Value"], q.inputs[0])
			return q.outputs["Value"]

		light = lin_term(vary.get("Light", 0.05))
		comb = nt.nodes.new("ShaderNodeCombineColor")
		for ch, k in (("Red", vary.get("Hue", 0.04)), ("Blue", -vary.get("Hue", 0.04))):
			q = nt.nodes.new("ShaderNodeMath")
			q.operation = "MULTIPLY"
			nt.links.new(lin_term(k), q.inputs[0])
			nt.links.new(light, q.inputs[1])
			nt.links.new(q.outputs["Value"], comb.inputs[ch])
		nt.links.new(light, comb.inputs["Green"])
		t3 = nt.nodes.new("ShaderNodeMix")
		t3.data_type, t3.blend_type = "RGBA", "MULTIPLY"
		t3.inputs["Factor"].default_value = 1.0
		nt.links.new(last, t3.inputs["A"])
		nt.links.new(comb.outputs["Color"], t3.inputs["B"])
		last = t3.outputs["Result"]
	nt.links.new(last, bsdf.inputs["Base Color"])
	nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
	return m


def scatter(ground_obj, name, attr, objs, density, scale=(0.75, 1.3), seed=1, match=False, material=None, vary=False):
	"""instances of objs over ground_obj where its float attribute attr is above 0 (density = attr x density per square
	stud), on a new object of their own (tagged "grass_scatter") that casts no shadows: grass neither shades itself nor
	darkens the ground, as in Roblox. It still receives the shadows the ground receives, so it keeps the ground's colour."""
	coll = bpy.data.collections.new(name + "Src")
	for o in objs:
		if material:
			o.data.materials.clear()
			o.data.materials.append(material)
		o.visible_shadow = False
		coll.objects.link(o)
	obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
	obj["grass_scatter"] = True
	obj.visible_shadow = False
	for c in ground_obj.users_collection:
		c.objects.link(obj)
	ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
	ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
	ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
	n, link = ng.nodes, ng.links.new
	gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
	oi = n.new("GeometryNodeObjectInfo")
	oi.inputs["Object"].default_value = ground_obj
	oi.transform_space = "RELATIVE"
	ground = oi.outputs["Geometry"]
	dist = n.new("GeometryNodeDistributePointsOnFaces")
	dist.distribute_method = "RANDOM"
	dist.inputs["Seed"].default_value = seed
	na = n.new("GeometryNodeInputNamedAttribute")
	na.data_type = "FLOAT"
	na.inputs["Name"].default_value = attr
	mul = n.new("ShaderNodeMath")
	mul.operation = "MULTIPLY"
	mul.inputs[1].default_value = density
	link(na.outputs["Attribute"], mul.inputs[0])
	link(mul.outputs["Value"], dist.inputs["Density"])
	# only the faces where this layer grows (usually a small area near the camera): distributing over, and building a
	# colour-lookup tree for, the whole ground for every layer and every render was the slow part
	cmp = n.new("FunctionNodeCompare")
	cmp.data_type, cmp.operation = "FLOAT", "GREATER_THAN"
	cmp.inputs[1].default_value = 0.001
	link(na.outputs["Attribute"], cmp.inputs[0])
	sep = n.new("GeometryNodeSeparateGeometry")
	sep.domain = "FACE"
	link(ground, sep.inputs["Geometry"])
	link(cmp.outputs["Result"], sep.inputs["Selection"])
	area = sep.outputs["Selection"]
	link(area, dist.inputs["Mesh"])
	ci = n.new("GeometryNodeCollectionInfo")
	ci.inputs["Collection"].default_value = coll
	ci.inputs["Separate Children"].default_value = True
	ci.inputs["Reset Children"].default_value = True
	iop = n.new("GeometryNodeInstanceOnPoints")
	iop.inputs["Pick Instance"].default_value = True
	rot = n.new("FunctionNodeRandomValue")
	rot.data_type = "FLOAT_VECTOR"
	rot.inputs[0].default_value = (-0.08, -0.08, 0)
	rot.inputs[1].default_value = (0.08, 0.08, math.tau)
	rot.inputs["Seed"].default_value = seed + 1
	sc = n.new("FunctionNodeRandomValue")
	sc.data_type = "FLOAT"
	sc.inputs[0].default_value, sc.inputs[1].default_value = scale
	sc.inputs["Seed"].default_value = seed + 2
	ix = n.new("FunctionNodeRandomValue")
	ix.data_type = "INT"
	ix.inputs[0].default_value, ix.inputs[1].default_value = 0, 99
	ix.inputs["Seed"].default_value = seed + 3
	link(dist.outputs["Points"], iop.inputs["Points"])
	link(ci.outputs[0], iop.inputs["Instance"])
	link(ix.outputs[0], iop.inputs["Instance Index"])
	link(rot.outputs[0], iop.inputs["Rotation"])
	link(sc.outputs[0], iop.inputs["Scale"])
	last = iop.outputs["Instances"]
	if match:  # each instance carries the ground colour under it
		snn = n.new("GeometryNodeSampleNearestSurface")
		snn.data_type = "FLOAT_COLOR"
		col = n.new("GeometryNodeInputNamedAttribute")
		col.data_type = "FLOAT_COLOR"
		col.inputs["Name"].default_value = "Col"
		link(area, snn.inputs["Mesh"])
		link(col.outputs["Attribute"], snn.inputs["Value"])
		st = n.new("GeometryNodeStoreNamedAttribute")
		st.data_type, st.domain = "FLOAT_COLOR", "INSTANCE"
		st.inputs["Name"].default_value = "ground_col"
		link(last, st.inputs["Geometry"])
		link(snn.outputs["Value"], st.inputs["Value"])
		last = st.outputs["Geometry"]
	if vary:
		rv = n.new("FunctionNodeRandomValue")
		rv.data_type = "FLOAT"
		rv.inputs[0].default_value, rv.inputs[1].default_value = 0.0, 1.0  # Blender 5.2: Min/Max are inputs 0/1 for every type
		rv.inputs["Seed"].default_value = seed + 4
		sv = n.new("GeometryNodeStoreNamedAttribute")
		sv.data_type, sv.domain = "FLOAT", "INSTANCE"
		sv.inputs["Name"].default_value = "vary"
		link(last, sv.inputs["Geometry"])
		link(rv.outputs[0], sv.inputs["Value"])
		last = sv.outputs["Geometry"]
	link(last, go.inputs[0])
	mod = obj.modifiers.new(name, "NODES")
	mod.node_group = ng
	return mod


