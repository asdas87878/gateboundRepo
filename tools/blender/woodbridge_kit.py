"""Wooden bridges in Blender (run headless): imports the OBJs from tools/art/woodbridge_kit.py, exports Woodbridge.glb, and renders the views for the comparison sheet.
Each bridge stands over its own water between two banks, back faces culled as in Roblox, with the fence and a 5.2-stud stand-in for scale.
  blender --background --python tools/blender/woodbridge_kit.py -- art/kit/woodbridge [--only view,view] [--fast]
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(args[0])
FENCE = os.path.join(os.path.dirname(OUT), "fence")
ONLY = args[args.index("--only") + 1].split(",") if "--only" in args else None
FAST = "--fast" in args
REND = os.path.join(OUT, "renders")
os.makedirs(REND, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def textured(name, path):
	mat = bpy.data.materials.new(name)
	mat.use_nodes = True
	tree = mat.node_tree
	bsdf = tree.nodes["Principled BSDF"]
	bsdf.inputs["Roughness"].default_value = 1
	tex = tree.nodes.new("ShaderNodeTexImage")
	tex.image = bpy.data.images.load(path)
	tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
	mat.use_backface_culling = True
	return mat


def flat_mat(name, col):
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	b = m.node_tree.nodes["Principled BSDF"]
	b.inputs["Base Color"].default_value = (*col, 1)
	b.inputs["Roughness"].default_value = 1
	return m


def load(folder, name, mat):
	bpy.ops.wm.obj_import(filepath=os.path.join(folder, name + ".obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.name = name
	o.data.name = name
	o.data.materials.clear()
	o.data.materials.append(mat)
	bpy.ops.object.select_all(action="DESELECT")
	o.select_set(True)
	bpy.context.view_layer.objects.active = o
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
	return o


wood = textured("Wood", os.path.join(OUT, "Woodbridge_Color.png"))
fence_mat = textured("FenceRef", os.path.join(FENCE, "Fence_Color.png"))
names = list(json.load(open(os.path.join(OUT, "kit.json")))["Triangles"])
objs = {n: load(OUT, n, wood) for n in names}
bpy.ops.object.select_all(action="DESELECT")
for o in objs.values():
	o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Woodbridge.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)

stand_mat = flat_mat("Stand", (0.2, 0.26, 0.5))
bank_mat = flat_mat("Bank", (0.05, 0.35, 0.12))
water_mat = flat_mat("Water", (0.09, 0.3, 0.38))
earth_mat = flat_mat("Earth", (0.2, 0.13, 0.08))


def player(x, y, z=0.0):
	bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.72, depth=4.0, location=(x, y, z + 2.0))
	body = bpy.context.object
	bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.62, location=(x, y, z + 4.58))
	head = bpy.context.object
	for o in (body, head):
		o.data.materials.append(stand_mat)


def box(x0, x1, y0, y1, z0, z1, mat):
	bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
	o = bpy.context.object
	o.scale = (x1 - x0, y1 - y0, z1 - z0)
	o.data.materials.append(mat)
	return o


# each bridge alone: its centre x, the half width of the water, the water level
SITES = {"BridgeArched": (0, 15.2, -6), "BridgeFlat": (300, 12.2, -6), "BridgePlank": (600, 6.8, -2.6), "BridgeBroken": (900, 12.2, -6)}
for name, (cx, half, water) in SITES.items():
	objs[name].location = (cx, 0, 0)
	box(cx - half, cx + half, -140, 140, water - 4, water, water_mat)
	for sign in (-1, 1):
		x0, x1 = (cx + sign * half, cx + sign * (half + 120))
		box(min(x0, x1), max(x0, x1), -140, 140, water - 4, 0, bank_mat)
		x0, x1 = (cx + sign * (half - 2.2), cx + sign * (half + 0.2))
		for y0, y1 in ((-140, -9), (9, 140)):  # beside the bridge only, so it doesn't hide the footing
			box(min(x0, x1), max(x0, x1), y0, y1, water - 4, -2.4, earth_mat)
fence = load(FENCE, "FenceA", fence_mat)
fence.location = (317.5, 9, 0)
fence.rotation_euler = (0, 0, math.radians(84))
fence2 = fence.copy()
fence2.location = (-20, 10, 0)
fence2.rotation_euler = (0, 0, math.radians(95))
bpy.context.collection.objects.link(fence2)
player(-19, -1)
player(-2.5, 1.2, 4.3)
player(300 - 17, 2)
player(300 + 2, 0.5, -0.2)
player(600 - 11, -1)
player(900 - 9.5, 2.4, -0.15)

sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.2
sun.color = (1, 0.96, 0.88)
sun.angle = math.radians(2)
so = bpy.data.objects.new("Sun", sun)
bpy.context.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(35))
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.65, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
bpy.context.scene.world = w
cam = bpy.data.cameras.new("C")
co = bpy.data.objects.new("C", cam)
bpy.context.collection.objects.link(co)
bpy.context.scene.camera = co
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.view_settings.view_transform = "Standard"
s.eevee.taa_render_samples = 16 if FAST else 48


def look(loc, target, lens=30, res=(1100, 680)):
	co.location = loc
	d = Vector(target) - Vector(loc)
	co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
	cam.lens = lens
	s.render.resolution_x, s.render.resolution_y = res


A, F, K, B = 0, 300, 600, 900
VIEWS = {
	"hero_arched": ((A - 26, -32, 7), (A, 0, 1.5), 30),
	"hero_flat": ((F - 25, -26, 6), (F, 0, -1.5), 30),
	"hero_plank": ((K - 13, -15, 5), (K, 0, -0.3), 30),
	"hero_broken": ((B - 12, -29, 7), (B + 2, 0, -2), 30),
	"side_arched": ((A, -44, 1.5), (A, 0, 0.5), 33),
	"side_flat": ((F, -40, 0.5), (F, 0, -1.5), 33),
	"side_plank": ((K, -21, 1), (K, 0, -0.4), 33),
	"side_broken": ((B, -40, 0.5), (B, 0, -1.5), 33),
	"walk_arched": ((A - 19, 0.8, 4.6), (A - 2, 0, 4.8), 21),
	"walk_flat": ((F - 16, 0.8, 4.4), (F, 0, 1.6), 21),
	"walk_plank": ((K - 11, 0.5, 4.5), (K, 0, 0.6), 21),
	"walk_broken": ((B - 7, 1, 4.4), (B + 6, 0, -0.3), 21),
	"under_arched": ((A - 9, -19, -4.8), (A, 0, 2.6), 24),
	"under_flat": ((F - 8, -19, -5.2), (F + 1, 0, -2), 24),
	"above_arched": ((A + 10, 34, 25), (A, 0, 0), 30),
	"above_broken": ((B + 8, 33, 24), (B + 2, 0, -1), 30),
	"close_wood": ((F - 3.5, -11.5, -0.6), (F + 3, 0, 0.1), 30),
	"close_stone": ((A - 6.5, -12.5, -2.2), (A - 14.5, 0, -3.4), 30),
}
for name, (loc, target, lens) in VIEWS.items():
	if ONLY and name not in ONLY:
		continue
	look(loc, target, lens)
	s.render.filepath = os.path.join(REND, name + ".png")
	bpy.ops.render.render(write_still=True)
print("rendered", list(VIEWS))
