"""Tree kit in Blender (headless): imports the OBJs from tools/art/tree_kit.py and renders the views for judging. Back faces are culled, as Roblox does.
  blender --background --python tools/blender/tree_kit.py -- art/kit/trees/test test
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(args[0])
MODE = args[1] if len(args) > 1 else "test"
bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, image, alpha=False):
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	t = m.node_tree
	b = t.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 1
	tex = t.nodes.new("ShaderNodeTexImage")
	tex.image = bpy.data.images.load(os.path.join(OUT, image))
	t.links.new(tex.outputs["Color"], b.inputs["Base Color"])
	if alpha:
		t.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
	m.use_backface_culling = True
	return m


LEAF = material("Leaves", "Tree_Leaves.png", alpha=True)
SOLID = material("LeavesSolid", "Tree_Leaves_Solid.png")
BARK = material("Bark", "Tree_Bark.png")


def load(name, mat, at=(0, 0, 0), cast=True):
	bpy.ops.wm.obj_import(filepath=os.path.join(OUT, name + ".obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.name = name
	o.data.materials.clear()
	o.data.materials.append(mat)
	o.location = at
	o.visible_shadow = cast
	return o


def world():
	bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, 0))
	g = bpy.context.object
	gm = bpy.data.materials.new("G")
	gm.use_nodes = True
	gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.42, 0.13, 1)
	gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1
	g.data.materials.append(gm)
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = 1.5
	sun.color = (1, 0.96, 0.88)
	sun.angle = math.radians(4)
	so = bpy.data.objects.new("Sun", sun)
	bpy.context.collection.objects.link(so)
	so.rotation_euler = (math.radians(45), 0, math.radians(30))
	w = bpy.data.worlds.new("W")
	w.use_nodes = True
	w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.68, 0.98, 1)
	w.node_tree.nodes["Background"].inputs[1].default_value = 0.62
	bpy.context.scene.world = w
	s = bpy.context.scene
	s.render.engine = "BLENDER_EEVEE"
	s.view_settings.view_transform = "Standard"


def shot(name, loc, target, res=(1000, 800), fov=None, lens=40):
	cam = bpy.data.cameras.new(name)
	cam.clip_end = 3000
	if fov:
		cam.lens_unit = "FOV"
		cam.angle_y = math.radians(fov)
		cam.sensor_fit = "VERTICAL"
	else:
		cam.lens = lens
	co = bpy.data.objects.new(name, cam)
	bpy.context.collection.objects.link(co)
	co.location = loc
	co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
	s = bpy.context.scene
	s.camera = co
	s.render.resolution_x, s.render.resolution_y = res
	s.render.filepath = os.path.join(OUT, "view_" + name + ".png")
	bpy.ops.render.render(write_still=True)


world()
if MODE == "test":
	A, B = (-26, 0, 0), (26, 0, 0)
	load("TestA_Crown", LEAF, A, cast=False)
	load("TestA_Trunk", BARK, A)
	load("TestB_Crown", SOLID, B, cast=False)
	load("TestB_Trunk", BARK, B)
	load("TestABush_Crown", LEAF, (-12, -14, 0), cast=False)
	load("TestABush_Core", BARK, (-12, -14, 0))
	load("TestBBush_Crown", SOLID, (40, -14, 0), cast=False)
	load("TestBBush_Core", BARK, (40, -14, 0))
	shot("wide", (0, -96, 16), (0, 0, 14), res=(1500, 800), lens=38)
	for tag, x in (("a", -26), ("b", 26)):
		shot("walk_" + tag, (x + 5, -19, 5), (x, 0, 13), fov=70)
		shot("close_" + tag, (x + 3, -19, 19), (x + 3, 0, 18), res=(800, 800), lens=38)
		shot("under_" + tag, (x + 1, -5, 3), (x, 0, 18), res=(800, 800), fov=70)
