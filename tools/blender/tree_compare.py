"""Broadleaf styles side by side from a player's eye height, with a 5.2-stud figure for scale (docs/style/look-direction.md).

  blender --background --python tools/blender/tree_compare.py -- <out.png>

One image per style: <out>_smooth.png and <out>_facet.png (kv.broadleaf style="facet"); oak, round, poplar, autumn oak.
Light as in the Vale (side sun, warm), ground in the Vale's meadow green.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import kit_vale as kv  # noqa: E402

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
kit.PAL.update({"leaf_dark": "2a4a38", "leaf_light": "93b05a"})


def main():
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	coll = bpy.data.collections.new("Trees")
	sc.collection.children.link(coll)
	kinds = [("oak", 16, False), ("round", 13, False), ("poplar", 18, False), ("oak", 15, True)]
	sets = {}
	for style in ("smooth", "facet"):
		sets[style] = []
		for i, (kind, h, autumn) in enumerate(kinds):
			o = kv.broadleaf(f"{style}_{kind}{i}", 100 + i, h, coll, kind=kind, autumn=autumn, style=style)
			o.location = (i * 17 - 26, 4 + (i % 2) * 6, 0)
			sets[style].append(o)
	hero = kit.hero("Hero", 7, coll)
	hero.location = (-14, -10, 0)
	p = kit.Piece(1)
	p.poly([Vector((-200, -200, 0)), Vector((200, -200, 0)), Vector((200, 200, 0)), Vector((-200, 200, 0))], "7f9a4e")
	p.finish("Ground", coll)
	w = bpy.data.worlds.new("W")
	sc.world = w
	w.use_nodes = True
	w.node_tree.nodes["Background"].inputs["Color"].default_value = (*kit.to_linear(kit.srgb("9fbfd3")), 1)
	w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.1
	sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
	sun.data.energy = 3.8
	sun.data.color = kit.to_linear(kit.srgb("ffedcc"))
	sun.data.angle = math.radians(2.5)
	sun.rotation_euler = (Vector((-0.85, 0.25, -0.5))).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(sun)
	cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
	cam.data.sensor_fit = "VERTICAL"
	cam.data.angle_y = math.radians(70)
	cam.location = (-2, -38, 6.6)
	cam.rotation_euler = (Vector((-2, 10, 9)) - cam.location).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(cam)
	sc.camera = cam
	sc.render.engine = "BLENDER_EEVEE"
	sc.render.resolution_x, sc.render.resolution_y = 1600, 900
	sc.eevee.taa_render_samples = 32
	sc.view_settings.view_transform = "Standard"
	for style in ("smooth", "facet"):
		for st, objs in sets.items():
			for o in objs:
				o.hide_render = st != style
		sc.render.filepath = OUT.replace(".png", f"_{style}.png")
		bpy.ops.render.render(write_still=True)


main()
