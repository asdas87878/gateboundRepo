"""Props kit in Blender (run headless): imports the OBJs from tools/art/props_kit.py, exports Props.glb, and renders the views for the comparison sheet.
Back faces are culled, as Roblox does, and the fence stands in the same scene with its own sheet.
  blender --background --python tools/blender/props_kit.py -- art/kit/props [--only view,view] [--fast]
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


def load(folder, name, mat):
	bpy.ops.wm.obj_import(filepath=os.path.join(folder, name + ".obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.name = name
	o.data.name = name
	o.data.materials.clear()
	o.data.materials.append(mat)
	# the importer leaves its axis swap as an object rotation; bake it so placing the object can't undo it
	bpy.ops.object.select_all(action="DESELECT")
	o.select_set(True)
	bpy.context.view_layer.objects.active = o
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
	return o


props_mat = textured("Props", os.path.join(OUT, "Props_Color.png"))
fence_mat = textured("FenceRef", os.path.join(FENCE, "Fence_Color.png"))
names = list(json.load(open(os.path.join(OUT, "kit.json")))["Triangles"])
objs = {n: load(OUT, n, props_mat) for n in names}
bpy.ops.object.select_all(action="DESELECT")
for o in objs.values():
	o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Props.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
for n in ("FenceA", "FenceLean", "FenceBroken"):
	objs[n] = load(FENCE, n, fence_mat)
# the fence copies used in the scatter view
extra = {}


def clone(name, new):
	o = objs[name].copy()
	o.name = new
	bpy.context.collection.objects.link(o)
	extra[new] = o
	return o


# a plain stand-in for the player, 5.2 tall, only for scale
stand_mat = bpy.data.materials.new("Stand")
stand_mat.use_nodes = True
stand_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.26, 0.5, 1)


def player(x, y):
	bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.72, depth=4.0, location=(x, y, 2.0))
	body = bpy.context.object
	bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.62, location=(x, y, 4.58))
	head = bpy.context.object
	for o in (body, head):
		o.data.materials.append(stand_mat)
	return body, head


bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, 0))
g = bpy.context.object
gm = bpy.data.materials.new("G")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.35, 0.12, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1
g.data.materials.append(gm)
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

# layout: world x along the row, y into the screen (the OBJ's +z front faces -y, toward the camera). Each row is far off to the side of the others, so backgrounds stay clean
ROW2 = 300.0
LAYOUT = {
	"FenceA": (-27, 2.5, 0),
	"BarrelA": (-15.5, 0, 0),
	"BarrelOpen": (-10.5, 0, 0),
	"BarrelPile": (-3, 0, 0),
	"CrateA": (6, 0, 0),
	"CrateSmall": (11, 0, 0),
	"CrateBroken": (17.5, 0, 0),
	"CrateStack": (27.5, 0, 0),
	"Cart": (ROW2 - 26, 0, 0),
	"CartBroken": (ROW2 - 3, 0, 32),
	"FenceLean": (ROW2 + 14, 2, 0),
	"SignPost": (ROW2 + 26, 0, 0),
	"SignLean": (ROW2 + 35, 0, 0),
	"FenceBroken": (ROW2 + 49, 2, 0),
}
for name, (x, y, r) in LAYOUT.items():
	objs[name].location = (x, y, 0)
	objs[name].rotation_euler = (0, 0, math.radians(r))
player(-20.5, 0.5)
player(ROW2 + 7.5, 2)
# the scatter view for distance
SC = -500.0  # scatter view, off along x
for new, src, x, y, r in (
	("sc_f1", "FenceA", -30, 8, 4),
	("sc_f2", "FenceLean", -18, 7, -6),
	("sc_f3", "FenceBroken", 18, 8, 3),
	("sc_c", "Cart", -6, 0, 18),
	("sc_b", "BarrelPile", 8, -2, -30),
	("sc_s", "SignPost", -24, -3, 8),
	("sc_st", "CrateStack", 24, -2, 40),
	("sc_a", "BarrelA", 15, 6, 0),
	("sc_br", "CrateBroken", 33, 4, 20),
	("sc_l", "SignLean", 40, -6, 0),
):
	o = clone(src, new)
	o.location = (SC + x, y, 0)
	o.rotation_euler = (0, 0, math.radians(r))
player(SC - 12, 1)


def look(loc, target, lens=35, res=(1500, 700)):
	co.location = loc
	d = Vector(target) - Vector(loc)
	co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
	cam.lens = lens
	s.render.resolution_x, s.render.resolution_y = res


VIEWS = {
	"lineup_a": dict(loc=(0.5, -74, 8), target=(0.5, 0, 3.8), lens=44, res=(1800, 480)),
	"lineup_b": dict(loc=(ROW2 + 10, -80, 8), target=(ROW2 + 10, 0, 4.4), lens=44, res=(1800, 480)),
	"close_barrels": dict(loc=(-9, -19, 5.2), target=(-8, 0, 2.4), lens=30, res=(1100, 720)),
	"close_crates": dict(loc=(12, -19, 5.2), target=(12, 0, 2.2), lens=30, res=(1100, 720)),
	"close_cart": dict(loc=(ROW2 - 29, -17, 5.2), target=(ROW2 - 23, 0, 2.8), lens=24, res=(1100, 720)),
	"close_broken_cart": dict(loc=(ROW2 - 8, -17, 5.2), target=(ROW2 - 2, 0, 2.6), lens=24, res=(1100, 720)),
	"close_signs": dict(loc=(ROW2 + 31, -13, 5.2), target=(ROW2 + 30, 0, 3.9), lens=24, res=(1100, 720)),
	"close_stack": dict(loc=(23, -13, 5.2), target=(27, 0, 3), lens=24, res=(1100, 720)),
	"zoom_crate": dict(loc=(3, -8, 4.6), target=(6, 0, 1.5), lens=30, res=(1000, 700)),
	"zoom_barrel": dict(loc=(-15, -8, 4.6), target=(-15.5, 0, 1.8), lens=30, res=(1000, 700)),
	"zoom_crate_top": dict(loc=(1.5, -5.5, 8.6), target=(6, 0, 2.7), lens=30, res=(1000, 700)),
	"back_above": dict(loc=(-1, 36, 26), target=(-1, 0, 1.8), lens=30, res=(1100, 500)),
	"back_above_b": dict(loc=(ROW2 + 8, 40, 26), target=(ROW2 + 8, 0, 1.8), lens=26, res=(1100, 500)),
	"distance": dict(loc=(SC + 4, -70, 5.2), target=(SC + 4, 0, 5.8), lens=30, res=(1800, 520)),
}
for name, v in VIEWS.items():
	if ONLY and name not in ONLY:
		continue
	look(v["loc"], v["target"], v["lens"], v["res"])
	s.render.filepath = os.path.join(REND, name + ".png")
	bpy.ops.render.render(write_still=True)
print("rendered", list(VIEWS))
