"""Five houses in every colour variation from tools/art/house_looks.py, one light and one camera per view, so only colour changes. Back faces hidden, as in Roblox.
  blender --background --python tools/blender/house_variations.py -- 1_current,2_dark_cool_stone,...
Writes art/kit/looks/<look>/row.png and close.png
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOOKS = os.path.join(ROOT, "art", "kit", "looks")
names = sys.argv[sys.argv.index("--") + 1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True)
HOUSES = (("Cottage", "cottage", -62), ("Townhouse", "townhouse", -37), ("Farmhouse", "farmhouse", -10), ("Bridgehouse", "bridgehouse", 22), ("Tattered", "tattered", 50))
images = {}
plain, alts = [], {"Rich": [], "Muted": []}


def material(key, colour=None, normal=None, first=None):
	mat = bpy.data.materials.new(key)
	mat.use_nodes = True
	mat.use_backface_culling = True
	tree = mat.node_tree
	bsdf = tree.nodes["Principled BSDF"]
	bsdf.inputs["Roughness"].default_value = 1
	if colour:
		bsdf.inputs["Base Color"].default_value = colour
	else:
		tex = tree.nodes.new("ShaderNodeTexImage")
		tex.image = bpy.data.images.load(first)
		tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
		images[key] = tex.image
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
	for n in ("Frame", "Joinery", "Walls", "Roof", "Stone"):
		obj = os.path.join(d, f"{house}_{n}.obj")
		if not os.path.exists(obj):
			continue
		bpy.ops.wm.obj_import(filepath=obj, forward_axis="NEGATIVE_Z", up_axis="Y")
		o = bpy.context.selected_objects[0]
		o.data.materials.clear()
		o.data.materials.append(material(f"{house}_{n}", first=os.path.join(LOOKS, names[0], f"{house}_{n}.png"), normal=os.path.join(d, f"{house}_{n}_Normal.png")))
		o.location = (x, 0, 0)
		if n == "Stone":
			plain.append(o)
			for style in ("Rich", "Muted"):
				alt = os.path.join(d, f"{house}_Stone_{style}.obj")
				if os.path.exists(alt):
					bpy.ops.wm.obj_import(filepath=alt, forward_axis="NEGATIVE_Z", up_axis="Y")
					a = bpy.context.selected_objects[0]
					a.data.materials.clear()
					a.data.materials.append(material(f"{house}_Stone_{style}", first=os.path.join(d, f"{house}_Stone_{style}.png")))
					a.location = (x, 0, 0)
					a.hide_render = True
					alts[style].append(a)
bpy.ops.mesh.primitive_plane_add(size=1000, location=(0, 0, 0))
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


for look in names:
	for key, img in images.items():
		if key.endswith(("_Rich", "_Muted")):
			continue
		img.filepath = os.path.join(LOOKS, look, key + ".png")
		img.reload()
	style = "Rich" if "rich" in look else "Muted" if "muted" in look else None
	for o in plain:
		o.hide_render = style is not None
	for k, objs in alts.items():
		for o in objs:
			o.hide_render = k != style
	shoot(os.path.join(LOOKS, look, "row.png"), (-6, -128, 17), (-6, 0, 12), 36, (1600, 500))
	shoot(os.path.join(LOOKS, look, "close.png"), (-22, -30, 8), (-13, -6, 5), 34, (800, 500))
