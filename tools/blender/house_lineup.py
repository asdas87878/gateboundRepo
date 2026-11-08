"""All the houses together in the chosen colour look (art/kit/looks/chosen, from tools/art/house_looks.py), with back faces hidden as in Roblox.
  blender --background --python tools/blender/house_lineup.py
Writes art/kit/looks/chosen/lineup/*.png
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOOK = os.path.join(ROOT, "art", "kit", "looks", "chosen")
OUT = os.path.join(LOOK, "lineup")
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
HOUSES = (("Cottage", "cottage", -46), ("Townhouse", "townhouse", -21), ("Farmhouse", "farmhouse", 5), ("Bridgehouse", "bridgehouse", 38), ("Inn", "inn", (-34, 220)), ("Mill", "mill", (4, 220)), ("Smithy", "smithy", (62, 220)), ("Clocktower", "clocktower", (-62, 440)), ("Manor", "manor", (-12, 440)), ("Terrace", "terrace", (42, 440)), ("Hut", "hut", (84, 440)), ("Tattered", "tattered", (112, 440)))


def material(key, path=None, colour=None, normal=None):
	mat = bpy.data.materials.new(key)
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


for house, folder, x in HOUSES:
	d = os.path.join(ROOT, "art", "kit", folder)
	for n in ("Frame", "Joinery", "Walls", "Roof"):
		bpy.ops.wm.obj_import(filepath=os.path.join(d, f"{house}_{n}.obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
		o = bpy.context.selected_objects[0]
		o.data.materials.clear()
		o.data.materials.append(material(f"{house}_{n}", os.path.join(LOOK, f"{house}_{n}.png"), normal=os.path.join(d, f"{house}_{n}_Normal.png")))
		o.location = (x[0], x[1], 0) if isinstance(x, tuple) else (x, 0, 0)
	stone = os.path.join(d, f"{house}_Stone.obj")  # a base built from the stone bridge's parts, with its own sheet
	if os.path.exists(stone):
		bpy.ops.wm.obj_import(filepath=stone, forward_axis="NEGATIVE_Z", up_axis="Y")
		o = bpy.context.selected_objects[0]
		o.data.materials.clear()
		o.data.materials.append(material(f"{house}_Stone", os.path.join(d, f"{house}_Stone.png")))
		o.location = (x[0], x[1], 0) if isinstance(x, tuple) else (x, 0, 0)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.95, depth=4.0, location=(38, -3, 2.0))
bpy.context.object.data.materials.append(material("Stand", colour=(0.32, 0.36, 0.5, 1)))
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.68, location=(38, -3, 4.55))
bpy.context.object.data.materials.append(material("Skin", colour=(0.75, 0.6, 0.45, 1)))
bpy.ops.mesh.primitive_plane_add(size=1000, location=(0, 0, 0))
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


ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None


def shoot(name, eye, at, lens, res, sun_z=-30):
	if ONLY and name not in ONLY:
		return
	co.location = eye
	co.rotation_euler = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
	cam.lens = lens
	so.rotation_euler = (math.radians(50), 0, math.radians(sun_z))
	s.render.resolution_x, s.render.resolution_y = res
	s.render.filepath = os.path.join(OUT, name + ".png")
	bpy.ops.render.render(write_still=True)


shoot("lineup", (-3, -125, 17), (-3, 0, 13), 34, (2000, 620))
shoot("farm_34", (-16, -44, 13), (5, 0, 9), 38, (1000, 720))
shoot("farm_back", (28, 44, 15), (5, 0, 9), 38, (1000, 720), 150)
shoot("farm_walk", (0, -22, 6.4), (2, 0, 8), 24.5, (1000, 720))
shoot("bridge_34", (58, -56, 13), (40, 0, 14.5), 36, (1000, 900))
shoot("bridge_left", (14, -52, 13), (38, 0, 14.5), 36, (1000, 900))
shoot("bridge_back", (58, 48, 14), (38, 0, 13), 36, (1000, 720), 150)
shoot("bridge_walk", (44, -26, 6.4), (44, -6, 8), 24.5, (1000, 720))
shoot("bridge_under", (38, -22, 5), (38, 0, 6.5), 26, (1000, 720))
R2 = 220
shoot("row2", (12, R2 - 125, 18), (12, R2, 13), 34, (2000, 620))
shoot("inn_34", (-58, R2 - 46, 14), (-34, R2, 13), 36, (1000, 720))
shoot("inn_walk", (-30, R2 - 27, 6.4), (-33, R2 - 7, 10), 24.5, (1000, 720))
shoot("mill_34", (28, R2 - 44, 14), (8, R2, 12), 36, (1000, 720))
shoot("mill_wheel", (40, R2 - 8, 9), (14, R2, 8), 36, (1000, 720), 60)
shoot("mill_back", (30, R2 + 46, 15), (8, R2, 12), 36, (1000, 720), 150)
shoot("smith_34", (44, R2 - 42, 11), (62, R2, 9), 36, (1000, 720))
shoot("smith_in", (58, R2 - 25, 6.4), (63, R2 - 4, 4.5), 26, (1000, 720))
R3 = 440
shoot("row3", (25, R3 - 190, 24), (25, R3, 18), 34, (2200, 680))
shoot("clock_34", (-82, R3 - 62, 18), (-60, R3, 20), 36, (1000, 900))
shoot("manor_34", (-38, R3 - 62, 16), (-12, R3, 12), 36, (1000, 720))
shoot("terrace_34", (22, R3 - 54, 15), (42, R3, 14), 36, (1000, 720))
shoot("hut_34", (74, R3 - 32, 10), (86, R3, 7), 36, (1000, 720))
shoot("tatter_34", (100, R3 - 34, 12), (112, R3, 11), 36, (1000, 720))
shoot("tatter_above", (92, R3 - 24, 34), (112, R3, 16), 36, (1000, 720))
