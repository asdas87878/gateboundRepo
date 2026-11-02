"""Card-branch trees (the "billboard branch" method most games use for soft, full trees): a real trunk plus flat cards
carrying painted foliage with transparent cut-outs (art/kit/textures, from tools/art/foliage_textures.py). The cards'
normals are bent outward from the crown's centre so the crown shades as one soft round shape instead of flat planes.

Each tree is one mesh with two materials: 0 = trunk (vertex colour, like the rest of the kit), 1 = foliage cards (UVs
on the foliage texture). For Roblox it splits into <Name>_Trunk (MeshPart, collides) and <Name>_Crown (MeshPart +
SurfaceAppearance with AlphaMode Transparency, no collision, ignored by the camera).

Used by tools/blender/look_match.py (kits "CardPine", "CardLeafy") and run alone:
  blender --background --python tools/blender/card_trees.py -- [--export]   -> art/kit/glb/Card*_Trunk.glb / _Crown.glb
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TEX = os.path.join(ROOT, "art", "kit", "textures")
_MATS = {}


def card_material(tex):
	if tex in _MATS:
		return _MATS[tex]
	m = bpy.data.materials.new(f"Card_{tex}")
	m.use_nodes = True
	try:
		m.surface_render_method = "DITHERED"
	except AttributeError:
		m.blend_method = "CLIP"
	m.use_backface_culling = False
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
	bsdf.inputs["Roughness"].default_value = 0.85
	if "Specular IOR Level" in bsdf.inputs:
		bsdf.inputs["Specular IOR Level"].default_value = 0.1
	img = nt.nodes.new("ShaderNodeTexImage")
	img.image = bpy.data.images.load(os.path.join(TEX, f"{tex}.png"), check_existing=True)
	cut = nt.nodes.new("ShaderNodeMath")  # hard cut-out, like Roblox's transparency mode
	cut.operation = "GREATER_THAN"
	cut.inputs[1].default_value = 0.45
	nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
	nt.links.new(img.outputs["Alpha"], cut.inputs[0])
	nt.links.new(cut.outputs["Value"], bsdf.inputs["Alpha"])
	nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
	_MATS[tex] = m
	return m


class Tree:
	def __init__(self, seed):
		self.bm = bmesh.new()
		self.col = self.bm.loops.layers.color.new("Col")
		self.uv = self.bm.loops.layers.uv.new("UV")
		self.r = random.Random(seed)
		self.normal_of = {}  # vert -> bent normal

	def trunk(self, pts, radii, colour, sides=7):
		rings = []
		for p, rad in zip(pts, radii):
			rings.append([self.bm.verts.new(p + Vector((math.cos(a) * rad, math.sin(a) * rad, 0))) for a in (i * math.tau / sides for i in range(sides))])
		for a, b in zip(rings, rings[1:]):
			for i in range(sides):
				j = (i + 1) % sides
				f = self.bm.faces.new((a[i], a[j], b[j], b[i]))
				f.material_index = 0
				c = kit.jitter(colour, self.r, v=0.06)
				for lp in f.loops:
					lp[self.col] = (*kit.to_linear(c), 1)
		for ring_, p in zip(rings, pts):
			for v in ring_:
				self.normal_of[v] = (v.co - p).normalized()

	def card(self, corners, uvs, normal_fn):
		vs = [self.bm.verts.new(c) for c in corners]
		f = self.bm.faces.new(vs)
		f.material_index = 1
		for lp, uv in zip(f.loops, uvs):
			lp[self.uv].uv = uv
			lp[self.col] = (1, 1, 1, 1)
		for v in vs:
			self.normal_of[v] = normal_fn(v.co)
		return f

	def finish(self, name, coll, tex):
		for f in self.bm.faces:
			f.smooth = True
		mesh = bpy.data.meshes.new(name)
		self.bm.verts.index_update()
		order = list(self.bm.verts)
		self.bm.to_mesh(mesh)
		self.bm.free()
		mesh.materials.append(kit.vertex_material())
		mesh.materials.append(card_material(tex))
		normals = [tuple(self.normal_of.get(v, Vector((0, 0, 1)))) for v in order]
		mesh.normals_split_custom_set_from_vertices(normals)
		obj = bpy.data.objects.new(name, mesh)
		if coll:
			coll.objects.link(obj)
		return obj


def card_pine(name, seed, height=30.0, coll=None, whorl_gap=0.8, per_whorl=8, spread=0.24):
	"""a spruce: a tapered trunk to the top, then whorls of drooping branch cards, two crossed cards per branch (one
	flat-ish, one rolled up) so the crown is full from any side"""
	t = Tree(seed)
	r = t.r
	H = height
	base_r = H * 0.022
	t.trunk([Vector((0, 0, z)) for z in (-0.5, H * 0.3, H * 0.7, H)], [base_r * 1.25, base_r * 0.8, base_r * 0.45, 0.05], "5b4a3c")
	z = H * 0.13
	k = 0
	while z < H * 0.98:
		u = (z - H * 0.13) / (H * 0.85)  # 0 at the lowest whorl, 1 at the top
		length = (H * spread * (1 - u) ** 0.85 + 0.9) * r.uniform(0.85, 1.12)
		n = max(3, int(round(per_whorl * (1 - 0.45 * u))))
		off = r.uniform(0, math.tau)
		for i in range(n):
			a = off + i * math.tau / n + r.uniform(-0.25, 0.25)
			droop = math.radians(r.uniform(8, 18) + 22 * (1 - u))  # lower branches hang more
			d = Vector((math.cos(a) * math.cos(droop), math.sin(a) * math.cos(droop), -math.sin(droop)))
			side = Vector((-math.sin(a), math.cos(a), 0))
			root = Vector((0, 0, z)) + d * (base_r * 0.5)
			w = length * 0.66
			for roll in (math.radians(r.uniform(-15, 15)), math.radians(r.uniform(50, 70)), math.radians(-r.uniform(50, 70))):
				up = Matrix.Rotation(roll, 3, d) @ d.cross(side).normalized() * -1
				across = d.cross(up).normalized() * w / 2
				tip = root + d * length + Vector((0, 0, -length * 0.08))
				corners = [root - across, tip - across, tip + across, root + across]
				centre_z = z - length * 0.35

				def bent(co, cz=centre_z):
					v = Vector((co.x, co.y, (co.z - cz) * 0.6))
					return (v.normalized() + Vector((0, 0, 0.35))).normalized()

				t.card(corners, [(0, 0), (1, 0), (1, 1), (0, 1)], bent)
			k += 1
		z += whorl_gap * r.uniform(0.85, 1.15) * (1 - 0.35 * u)
	# a tuft of small upright cards at the very top
	for i in range(3):
		a = i * math.tau / 3
		d = Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 1)).normalized()
		side = Vector((-math.sin(a), math.cos(a), 0)) * 0.45
		root = Vector((0, 0, H * 0.93))
		tip = root + d * H * 0.09
		t.card([root - side, tip - side, tip + side, root + side], [(0, 0), (1, 0), (1, 1), (0, 1)], lambda co: Vector((co.x, co.y, 0.6)).normalized())
	return t.finish(name, coll, "needles")


def card_leafy(name, seed, height=18.0, coll=None, autumn=False, clusters=14):
	"""a broadleaf tree: a trunk splitting into a few limbs, each ending in clusters of leaf cards facing every way;
	normals point out from the crown's centre so it shades like one soft ball"""
	t = Tree(seed)
	r = t.r
	H = height
	base_r = H * 0.035
	fork = H * r.uniform(0.38, 0.45)
	t.trunk([Vector((0, 0, -0.5)), Vector((0, 0, fork * 0.6)), Vector((0, 0, fork))], [base_r * 1.3, base_r, base_r * 0.85], "5a4636")
	crown_c = Vector((0, 0, H * 0.66))
	crown_r = H * 0.33
	limbs = r.randint(3, 4)
	for i in range(limbs):
		a = i * math.tau / limbs + r.uniform(-0.3, 0.3)
		end = crown_c + Vector((math.cos(a) * crown_r * 0.55, math.sin(a) * crown_r * 0.55, r.uniform(-0.1, 0.25) * crown_r))
		mid = (Vector((0, 0, fork)) + end) / 2 + Vector((0, 0, crown_r * 0.1))
		t.trunk([Vector((0, 0, fork - 0.3)), mid, end], [base_r * 0.6, base_r * 0.4, base_r * 0.2], "5a4636", sides=5)
	centres = []
	for _ in range(clusters):
		v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 0.8))).normalized() * crown_r * r.uniform(0.35, 0.8)
		centres.append(crown_c + v)
	centres.append(crown_c + Vector((0, 0, crown_r * 0.55)))
	for c in centres:
		size = crown_r * r.uniform(0.85, 1.15)
		for _ in range(6):
			n = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
			a = n.orthogonal().normalized()
			b = n.cross(a).normalized()
			rot = r.uniform(0, math.tau)
			a, b = a * math.cos(rot) + b * math.sin(rot), -a * math.sin(rot) + b * math.cos(rot)
			h = size / 2
			corners = [c - a * h - b * h, c + a * h - b * h, c + a * h + b * h, c - a * h + b * h]
			t.card(corners, [(0, 0), (1, 0), (1, 1), (0, 1)], lambda co: ((co - crown_c).normalized() + Vector((0, 0, 0.25))).normalized())
	return t.finish(name, coll, "leaves_autumn" if autumn else "leaves")


def export_split(obj, out_dir):
	"""<Name>_Trunk.glb (material 0) and <Name>_Crown.glb (material 1, UVs)"""
	for idx, suffix in ((0, "Trunk"), (1, "Crown")):
		dup = obj.copy()
		dup.data = obj.data.copy()
		bpy.context.scene.collection.objects.link(dup)
		bm = bmesh.new()
		bm.from_mesh(dup.data)
		bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != idx], context="FACES")
		bm.to_mesh(dup.data)
		bm.free()
		bpy.ops.object.select_all(action="DESELECT")
		dup.select_set(True)
		bpy.context.view_layer.objects.active = dup
		bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, f"{obj.name}_{suffix}.glb"), export_format="GLB", use_selection=True,
								  export_materials="NONE", export_vertex_color="ACTIVE", export_normals=True, export_apply=True)
		bpy.data.objects.remove(dup)


if __name__ == "__main__":
	args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
	bpy.ops.wm.read_factory_settings(use_empty=True)
	coll = bpy.data.collections.new("Trees")
	bpy.context.scene.collection.children.link(coll)
	trees = [card_pine("CardPine", 1), card_leafy("CardLeafy", 2), card_leafy("CardLeafyAutumn", 3, autumn=True)]
	for o in trees:
		coll.objects.link(o)
		print(o.name, "triangles", sum(len(p.vertices) - 2 for p in o.data.polygons))
	if "--export" in args:
		out = os.path.join(ROOT, "art", "kit", "glb")
		os.makedirs(out, exist_ok=True)
		for o in trees:
			export_split(o, out)
		print("exported to", out)
