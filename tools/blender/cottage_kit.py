"""The cottage in Blender (run headless): imports the OBJs from tools/art/cottage_kit.py, exports Cottage.glb (one mesh per painted sheet) and renders the review views.
Back-face culling is on in the renders, as in Roblox, so an inside-out face shows up here too.
  blender --background --python tools/blender/cottage_kit.py -- art/kit/cottage [--views front,back] [--quick]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(args[0])
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
QUICK = "--quick" in args
FLAT = "--flat" in args  # leave the normal map off, to compare
VIEWS_ON = args[args.index("--views") + 1].split(",") if "--views" in args else None
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, path=None, colour=None, normal=None):
	mat = bpy.data.materials.new(name)
	mat.use_nodes = True
	mat.use_backface_culling = True
	tree = mat.node_tree
	bsdf = tree.nodes["Principled BSDF"]
	bsdf.inputs["Roughness"].default_value = 1
	if path:
		tex = tree.nodes.new("ShaderNodeTexImage")
		tex.image = bpy.data.images.load(path)
		tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
	else:
		bsdf.inputs["Base Color"].default_value = colour
	if normal and os.path.exists(normal) and not FLAT:
		nt = tree.nodes.new("ShaderNodeTexImage")
		nt.image = bpy.data.images.load(normal)
		nt.image.colorspace_settings.name = "Non-Color"
		nm = tree.nodes.new("ShaderNodeNormalMap")
		tree.links.new(nt.outputs["Color"], nm.inputs["Color"])
		tree.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
	return mat


def load(obj_path, name, mat):
	bpy.ops.wm.obj_import(filepath=obj_path, forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.name = name
	o.data.name = name
	o.data.materials.clear()
	o.data.materials.append(mat)
	return o


parts = []
for n in ("Frame", "Joinery", "Walls", "Roof"):
	parts.append(load(os.path.join(OUT, f"Cottage_{n}.obj"), f"Cottage_{n}", material(f"Cottage_{n}", os.path.join(OUT, f"Cottage_{n}.png"), normal=os.path.join(OUT, f"Cottage_{n}_Normal.png"))))
bpy.ops.object.select_all(action="DESELECT")
for p in parts:
	p.select_set(True)
if not QUICK:
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Cottage.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_tangents=True)

# studs are metres here: x along the ridge, Blender z up, the door faces Blender -y
# the approved fence beside the house for style and scale, and a 5.2-stud stand-in
fence_dir = os.path.join(ROOT, "art", "kit", "fence")
fmat = material("Fence", os.path.join(fence_dir, "Fence_Color.png"))
for name, loc, rot in (("FenceA", (20.5, -9.0, 0), -14), ("FenceLean", (-18.5, -8.5, 0), 11)):
	f = load(os.path.join(fence_dir, name + ".obj"), name, fmat)
	f.location = loc
	f.rotation_euler = (math.radians(90), 0, math.radians(rot))  # the importer stands y-up meshes with this x turn
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.95, depth=4.0, location=(13.8, -9.5, 2.0))
body = bpy.context.object
body.data.materials.append(material("Stand", colour=(0.32, 0.36, 0.5, 1)))
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.68, location=(13.8, -9.5, 4.55))
bpy.context.object.data.materials.append(material("Skin", colour=(0.75, 0.6, 0.45, 1)))
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, 0))
ground = bpy.context.object
ground.data.materials.append(material("Ground", colour=(0.05, 0.3, 0.1, 1)))
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.2
sun.color = (1, 0.96, 0.88)
sun.angle = math.radians(2)
so = bpy.data.objects.new("Sun", sun)
bpy.context.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(-30))
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.65, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
s = bpy.context.scene
s.world = w
cam = bpy.data.cameras.new("C")
co = bpy.data.objects.new("C", cam)
bpy.context.collection.objects.link(co)
s.camera = co
s.render.engine = "BLENDER_EEVEE"
s.view_settings.view_transform = "Standard"
s.render.image_settings.file_format = "PNG"
os.makedirs(os.path.join(OUT, "views"), exist_ok=True)


def shoot(name, eye, at, lens=35, res=(1100, 1000), sun_z=None):
	if VIEWS_ON and name not in VIEWS_ON:
		return
	co.location = eye
	d = Vector(at) - Vector(eye)
	co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
	cam.lens = lens
	if sun_z is not None:
		so.rotation_euler = (math.radians(50), 0, math.radians(sun_z))
	s.render.resolution_x, s.render.resolution_y = res
	s.render.filepath = os.path.join(OUT, "views", name + ".png")
	bpy.ops.render.render(write_still=True)


# the door faces -y in Blender
shoot("front", (-14, -38, 12), (0, 0, 10), sun_z=-30)
shoot("back", (20, 36, 15), (0, 0, 10), sun_z=150)
shoot("gable", (40, -6, 10), (0, 0, 10), sun_z=70)
shoot("above", (-26, -26, 40), (0, 0, 9), sun_z=-30)
shoot("straight", (0, -46, 9), (0.8, 0, 10.2), lens=42, res=(1100, 1000), sun_z=-30)
shoot("walk", (-9.5, -21.5, 6.4), (-1, 0, 7.2), lens=24.5, res=(1500, 850), sun_z=-30)  # FieldOfView 70-ish over the shoulder
shoot("door", (-3.3, -13.5, 5), (-1.56, -6, 3.8), lens=30, res=(1100, 1000), sun_z=-30)
shoot("window", (8.1, -12, 7), (5.5, -6, 5.5), lens=38, res=(1100, 1000), sun_z=-30)
shoot("stones_flat" if FLAT else "stones", (1.5, 15.5, 3.4), (-1.0, 6.3, 1.5), lens=30, res=(1100, 700), sun_z=120)
shoot("dormer", (3.2, -14, 20), (5.5, 3, 16), lens=50, res=(1100, 1000), sun_z=-30)
