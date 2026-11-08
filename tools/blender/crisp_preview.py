"""Before and after for a crisp-paint sheet, headless, back faces hidden as in Roblox: every OBJ in a kit folder, close up, once per sheet given. Reads only.
  blender --background --python tools/blender/crisp_preview.py -- <kit folder> <out folder> <sheet.png> [<sheet.png> ...] [--only A,B] [--spread 9]
"""
import glob
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
only = args[args.index("--only") + 1].split(",") if "--only" in args else None
spread = float(args[args.index("--spread") + 1]) if "--spread" in args else 9.0
args = [a for i, a in enumerate(args) if a not in ("--only", "--spread") and (i == 0 or args[i - 1] not in ("--only", "--spread"))]
KIT, OUT, SHEETS = os.path.abspath(args[0]), os.path.abspath(args[1]), [os.path.abspath(a) for a in args[2:]]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
mat = bpy.data.materials.new("Sheet")
mat.use_nodes = True
mat.use_backface_culling = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 1
bsdf.inputs["Specular IOR Level"].default_value = 0
tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
paths = sorted(glob.glob(os.path.join(KIT, "*.obj")))
if only:
	paths = [p for p in paths if os.path.splitext(os.path.basename(p))[0] in only]
for i, path in enumerate(paths):
	bpy.ops.wm.obj_import(filepath=path, forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.data.materials.clear()
	o.data.materials.append(mat)
	o.location = (i * spread - (len(paths) - 1) * spread / 2, 0, 0)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
ground = bpy.data.materials.new("G")
ground.use_nodes = True
ground.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.35, 0.12, 1)
bpy.context.object.data.materials.append(ground)
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 2.6
sun.color = (1, 0.96, 0.88)
so = bpy.data.objects.new("Sun", sun)
bpy.context.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(35))
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.65, 0.9, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
bpy.context.scene.world = world
cam = bpy.data.cameras.new("C")
co = bpy.data.objects.new("C", cam)
bpy.context.collection.objects.link(co)
cam.lens = 45
reach = max(len(paths) * spread * 0.62, 6)
eye, target = Vector((0, -reach, reach * 0.34 + 1.5)), Vector((0, 0, 1.6))
co.location = eye
co.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
s = bpy.context.scene
s.camera = co
s.render.engine = "BLENDER_EEVEE"
s.render.resolution_x, s.render.resolution_y = 1600, 800
s.view_settings.view_transform = "Standard"
for path in SHEETS:
	tex.image = bpy.data.images.load(path)
	s.render.filepath = os.path.join(OUT, os.path.splitext(os.path.basename(path))[0] + ".png")
	bpy.ops.render.render(write_still=True)
	print("RENDERED", s.render.filepath)
