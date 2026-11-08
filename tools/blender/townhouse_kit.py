"""The townhouse in Blender (run headless): imports the OBJs from tools/art/townhouse_kit.py, exports Townhouse.glb, renders the review views with back faces hidden, as in Roblox.
  blender --background --python tools/blender/townhouse_kit.py -- art/kit/townhouse [--quick] [--views a,b]
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
	if normal and os.path.exists(normal):
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
	parts.append(load(os.path.join(OUT, f"Townhouse_{n}.obj"), f"Townhouse_{n}", material(f"Townhouse_{n}", os.path.join(OUT, f"Townhouse_{n}.png"), normal=os.path.join(OUT, f"Townhouse_{n}_Normal.png"))))
bpy.ops.object.select_all(action="DESELECT")
for p in parts:
	p.select_set(True)
if not QUICK:
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Townhouse.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_tangents=True)

# the approved cottage beside it for style and scale, and a 5.2-stud stand-in. Door faces Blender -y
ck = os.path.join(ROOT, "art", "kit", "cottage")
for n in ("Frame", "Joinery", "Walls", "Roof"):
	c = load(os.path.join(ck, f"Cottage_{n}.obj"), f"Cottage_{n}", material(f"Cot_{n}", os.path.join(ck, f"Cottage_{n}.png"), normal=os.path.join(ck, f"Cottage_{n}_Normal.png")))
	c.location = (-25, 2, 0)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.95, depth=4.0, location=(9.5, -10, 2.0))
bpy.context.object.data.materials.append(material("Stand", colour=(0.32, 0.36, 0.5, 1)))
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.68, location=(9.5, -10, 4.55))
bpy.context.object.data.materials.append(material("Skin", colour=(0.75, 0.6, 0.45, 1)))
bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, 0))
bpy.context.object.data.materials.append(material("Ground", colour=(0.05, 0.3, 0.1, 1)))
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.2
sun.color = (1, 0.96, 0.88)
sun.angle = math.radians(2)
so = bpy.data.objects.new("Sun", sun)
bpy.context.collection.objects.link(so)
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


def shoot(name, eye, at, lens=35, res=(800, 1100), sun_z=-30):
	if VIEWS_ON and name not in VIEWS_ON:
		return
	co.location = eye
	co.rotation_euler = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
	cam.lens = lens
	so.rotation_euler = (math.radians(50), 0, math.radians(sun_z))
	s.render.resolution_x, s.render.resolution_y = res
	s.render.filepath = os.path.join(OUT, "views", name + ".png")
	bpy.ops.render.render(write_still=True)


shoot("three_quarter", (-20, -48, 12), (0, 0, 16))
shoot("straight", (0, -66, 14), (0.3, 0, 17))
shoot("side", (56, -3, 14), (0, 0, 17), sun_z=60)
shoot("back", (28, 48, 14), (0, 0, 17), sun_z=150)
shoot("elevation", (0.8, -80, 14), (0.8, 0, 14), lens=75, res=(1100, 1300))
shoot("back_elevation", (0.8, 80, 14), (0.8, 0, 14), lens=75, res=(1100, 1300), sun_z=150)
shoot("walk", (-7, -19, 6.4), (0, 0, 10), lens=24.5, res=(1200, 850))
shoot("beside_cottage", (-22, -76, 12), (-12, 0, 13), lens=38, res=(1200, 850))
