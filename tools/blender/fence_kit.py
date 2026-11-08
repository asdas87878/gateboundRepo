"""Fence kit in Blender (run headless): imports the OBJs from tools/art/fence_kit.py, exports Fence.glb, and renders a quick preview on green.
  blender --background --python tools/blender/fence_kit.py -- art/kit/fence
"""
import math
import os
import sys

import bpy

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
mat = bpy.data.materials.new("Fence")
mat.use_nodes = True
tree = mat.node_tree
bsdf = tree.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 1
tex = tree.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(os.path.join(OUT, "Fence_Color.png"))
tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
objs = []
for i, name in enumerate(("FenceA", "FenceLean", "FenceBroken", "FencePost")):
	bpy.ops.wm.obj_import(filepath=os.path.join(OUT, name + ".obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.name = name
	o.data.name = name
	o.data.materials.clear()
	o.data.materials.append(mat)
	objs.append(o)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Fence.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
# preview: spread out on a green ground
for i, o in enumerate(objs):
	o.location = (-19 + i * 13, 0, 0)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
g = bpy.context.object
gm = bpy.data.materials.new("G")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.35, 0.12, 1)
g.data.materials.append(gm)
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.2
sun.color = (1, 0.96, 0.88)
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
cam.lens = 45
co.location = (2, -46, 9)
co.rotation_euler = (math.radians(80), 0, 0)
bpy.context.scene.camera = co
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.render.resolution_x, s.render.resolution_y = 1500, 620
s.view_settings.view_transform = "Standard"
s.render.filepath = os.path.join(OUT, "preview.png")
bpy.ops.render.render(write_still=True)
