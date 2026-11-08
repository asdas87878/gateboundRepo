"""Renders the two houses in every colour look from tools/art/house_looks.py, with one lighting and one camera per view, so only colour changes.
  blender --background --python tools/blender/house_looks.py
"""
import json
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOOKS = os.path.join(ROOT, "art", "kit", "looks")
bpy.ops.wm.read_factory_settings(use_empty=True)
images = {}


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
		images[key] = tex.image
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


for house, folder, loc in (("Cottage", "cottage", (-16, 0, 0)), ("Townhouse", "townhouse", (10, 0, 0))):
	d = os.path.join(ROOT, "art", "kit", folder)
	for n in ("Frame", "Joinery", "Walls", "Roof"):
		bpy.ops.wm.obj_import(filepath=os.path.join(d, f"{house}_{n}.obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
		o = bpy.context.selected_objects[0]
		o.data.materials.clear()
		o.data.materials.append(material(f"{house}_{n}", os.path.join(d, f"{house}_{n}.png"), normal=os.path.join(d, f"{house}_{n}_Normal.png")))
		o.location = loc
bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, 0))
bpy.context.object.data.materials.append(material("Ground", colour=(0.05, 0.3, 0.1, 1)))
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


def shoot(path, eye, at, lens, res):
	co.location = eye
	co.rotation_euler = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
	cam.lens = lens
	s.render.resolution_x, s.render.resolution_y = res
	s.render.filepath = path
	bpy.ops.render.render(write_still=True)


# the same houses with the sun behind them, so the door side is in shade: with and without blue point lights in that shade
lights = []
for x, y, z, watts in ((-22, -7.4, 8.0, 110), (-10, -7.4, 8.0, 110), (6.5, -6.6, 7.6, 100), (13.5, -6.6, 7.6, 100), (10, -8.4, 14.6, 120)):
	pl = bpy.data.lights.new("Blue", "POINT")
	pl.color = (0.42, 0.58, 1.0)
	pl.energy = watts
	pl.shadow_soft_size = 1.0
	po = bpy.data.objects.new("Blue", pl)
	bpy.context.collection.objects.link(po)
	po.location = (x, y, z)
	po.hide_render = True
	lights.append(po)


for look in json.load(open(os.path.join(LOOKS, "looks.json"))):
	for key, img in images.items():
		img.filepath = os.path.join(LOOKS, look, key + ".png")
		img.reload()
	shoot(os.path.join(LOOKS, look, "pair.png"), (-10, -72, 13), (-3, 0, 12.5), 42, (1200, 720))
	shoot(os.path.join(LOOKS, look, "close.png"), (-16, -22, 6.5), (-16.5, -6, 5.5), 32, (760, 720))
	shoot(os.path.join(LOOKS, look, "close_town.png"), (11, -26, 12), (10.8, -6, 12.5), 34, (760, 720))
	shoot(os.path.join(LOOKS, look, "door_close.png"), (-16.2, -14.5, 5.2), (-15.2, -6, 4.2), 40, (760, 720))
	shoot(os.path.join(LOOKS, look, "far.png"), (-18, -190, 16), (-3, 0, 11), 50, (1200, 720))
	so.rotation_euler = (math.radians(50), 0, math.radians(150))
	shoot(os.path.join(LOOKS, look, "shade.png"), (-10, -72, 13), (-3, 0, 12.5), 42, (1200, 720))
	for po in lights:
		po.hide_render = False
	shoot(os.path.join(LOOKS, look, "shade_lights.png"), (-10, -72, 13), (-3, 0, 12.5), 42, (1200, 720))
	for po in lights:
		po.hide_render = True
	so.rotation_euler = (math.radians(50), 0, math.radians(-30))
