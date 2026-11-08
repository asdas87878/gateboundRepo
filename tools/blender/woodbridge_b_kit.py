"""The second set of wooden bridges in Blender (run headless): imports the OBJs from tools/art/woodbridge_b_kit.py, exports Woodbridge_B.glb, and renders the views for the comparison sheet.
Back faces culled as in Roblox. iso_* show each bridge alone on a pale ground, framed like the user's concept; the rest stand over water with a 5.2-stud stand-in.
  blender --background --python tools/blender/woodbridge_b_kit.py -- art/kit/woodbridge_b [--only view,view] [--fast]
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(args[0])
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


sheets = json.load(open(os.path.join(OUT, "kit.json")))["Sheets"]  # each bridge has its own
objs = {n: load(OUT, n, textured(n + "Wood", os.path.join(OUT, f))) for n, f in sheets.items()}
bpy.ops.object.select_all(action="DESELECT")
for o in objs.values():
	o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Woodbridge_B.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)

stand_mat = flat_mat("Stand", (0.2, 0.26, 0.5))
bank_mat = flat_mat("Bank", (0.03, 0.46, 0.11))  # about the Studio grass
water_mat = flat_mat("Water", (0.12, 0.62, 0.68))  # about the Studio river
pale_mat = flat_mat("Pale", (0.86, 0.85, 0.83))


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


SITES = {"BridgeChunky": (0, 17.5, -7), "BridgeLattice": (300, 17.5, -7), "BridgeRope": (600, 17.0, -8)}
ISO_Y = 3000
for i, (name, (cx, half, water)) in enumerate(SITES.items()):
	objs[name].location = (cx, 0, 0)
	box(cx - half, cx + half, -140, 140, water - 4, water, water_mat)
	for sign in (-1, 1):
		x0, x1 = (cx + sign * half, cx + sign * (half + 120))
		box(min(x0, x1), max(x0, x1), -140, 140, water - 4, -0.7, bank_mat)
	iso = objs[name].copy()
	iso.location = (cx, ISO_Y, 0)
	bpy.context.collection.objects.link(iso)
pale = box(-2000, 3000, ISO_Y - 2000, ISO_Y + 3000, -14, -13, pale_mat)
player(-13, -2.2, 0.0)
player(300 - 22, 2)
player(300 - 3, 0.3, 3.1)
player(600 - 24, 1)
player(600 + 2, 0.2, -0.5)

sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.2
sun.color = (1, 0.96, 0.88)
sun.angle = math.radians(2)
so = bpy.data.objects.new("Sun", sun)
bpy.context.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(35))
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.52, 0.95, 1)
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


A, B, C = 0, 300, 600
VIEWS = {
	"iso_chunky": ((A + 18, ISO_Y - 150, 54), (A, ISO_Y, 0.6), 118, (1100, 260)),
	"iso_lattice": ((B + 18, ISO_Y - 150, 48), (B, ISO_Y, 2.0), 118, (1100, 240)),
	"iso_rope": ((C + 16, ISO_Y - 150, 40), (C, ISO_Y, 2.2), 112, (1100, 260)),
	"far_chunky": ((A - 42, -96, 7), (A, 0, 0.5), 42, (1100, 420)),
	"far_lattice": ((B - 42, -96, 7), (B, 0, 1.2), 42, (1100, 420)),
	"far_rope": ((C - 42, -96, 7), (C, 0, 1.2), 42, (1100, 420)),
	"hero_chunky": ((A - 28, -32, 9), (A - 2, 0, 0), 30, (1100, 680)),
	"hero_lattice": ((B - 28, -30, 9), (B - 1, 0, 1), 30, (1100, 680)),
	"hero_rope": ((C - 30, -30, 10), (C - 1, 0, 1), 30, (1100, 680)),
	"walk_chunky": ((A - 19, 2.4, 4.4), (A, 0, 2.8), 21, (1100, 680)),
	"walk_lattice": ((B - 22, 0.6, 4.4), (B - 2, 0, 5.2), 21, (1100, 680)),
	"walk_rope": ((C - 22, 0.4, 4.3), (C, 0, 1.6), 21, (1100, 680)),
	"close_post": ((A - 5.5, -11, 3.8), (A + 0.5, 0, 0.6), 30, (1100, 680)),
	"close_lattice": ((B + 3, -12.5, 7), (B + 7, 0, 3.8), 30, (1100, 680)),
	"close_rope": ((C - 23, -9.5, 5.5), (C - 17.5, 0, 3), 30, (1100, 680)),
	"above_rope": ((C + 12, 36, 24), (C, 0, 0), 30, (1100, 680)),
}
for name, (loc, target, lens, res) in VIEWS.items():
	if ONLY and name not in ONLY:
		continue
	look(loc, target, lens, res)
	pale.hide_render = not name.startswith("iso_")  # it shows on the horizon from the river scenes
	s.render.filepath = os.path.join(REND, name + ".png")
	bpy.ops.render.render(write_still=True)
print("rendered", list(VIEWS))
