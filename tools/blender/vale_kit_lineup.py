"""Render the Vale kit pieces side by side (art/kit/renders/vale_lineup.png) and print triangle counts.

  blender --background --python tools/blender/vale_kit_lineup.py
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

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def main():
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	coll = bpy.data.collections.new("Lineup")
	sc.collection.children.link(coll)
	pieces = [
		("Oak", lambda n: kv.broadleaf(n, 1, 16, kind="oak")),
		("Poplar", lambda n: kv.broadleaf(n, 2, 18, kind="poplar")),
		("Round", lambda n: kv.broadleaf(n, 3, 13, kind="round")),
		("Autumn", lambda n: kv.broadleaf(n, 4, 15, kind="oak", autumn=True)),
		("Pine", lambda n: kit.pine(n, 110, 26)),
		("Grass", lambda n: kv.field_grass(n, 5, 14, 1.3)),
		("DryGrass", lambda n: kv.field_grass(n, 6, 14, 1.3, dry=True)),
		("Boulder", lambda n: kv.mossy_boulder(n, 7, (7, 6, 5))),
		("Stone", lambda n: kv.standing_stone(n, 8)),
		("House", lambda n: kv.house(n, 9, 10, 8, 8)),
		("HouseTile", lambda n: kv.house(n, 10, 12, 8, 9, roof="tile")),
		("Tower", lambda n: kv.round_tower(n, 11, 4, 20)),
		("Wall", lambda n: kv.crenel_wall(n, 12, 20, 10)),
		("Keep", lambda n: kv.keep(n, 13)),
		("Bridge", lambda n: kv.stone_bridge(n, 14, 34, 7)),
		("Windmill", lambda n: kv.windmill(n, 15)),
		("Wheel", lambda n: kv.waterwheel(n, 16)),
		("Stall", lambda n: kv.stall(n, 17)),
		("Tent", lambda n: kv.tent(n, 18)),
		("Palisade", lambda n: kv.palisade(n, 19, 12)),
		("Gate", lambda n: kv.grand_gate(n, 20, height=64)),
	]
	x = 0.0
	tris = {}
	for name, fn in pieces:
		o = fn(name)
		coll.objects.link(o)
		xs = [v.co.x for v in o.data.vertices]
		o.location = (x - min(xs), 0, 0)
		x += max(xs) - min(xs) + 4
		tris[name] = sum(len(p.vertices) - 2 for p in o.data.polygons)
	print("[vale kit] triangles:", tris)
	w = bpy.data.worlds.new("W")
	sc.world = w
	w.use_nodes = True
	w.node_tree.nodes["Background"].inputs["Color"].default_value = (*kit.to_linear(kit.srgb("9ec4e6")), 1)
	w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.3
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = 3.0
	sun.color = kit.to_linear(kit.srgb("fff0d8"))
	so = bpy.data.objects.new("Sun", sun)
	so.rotation_euler = (math.radians(45), 0, math.radians(-60))
	sc.collection.objects.link(so)
	ground = bpy.data.meshes.new("G")
	ground.from_pydata([(-50, -60, 0), (x + 50, -60, 0), (x + 50, 60, 0), (-50, 60, 0)], [], [(0, 1, 2, 3)])
	ga = ground.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	for d in ga.data:
		d.color = (*kit.to_linear(kit.srgb("8fb04e")), 1)
	ground.materials.append(kit.vertex_material())
	coll.objects.link(bpy.data.objects.new("Ground", ground))
	cam = bpy.data.cameras.new("Cam")
	cam.type = "ORTHO"
	cam.ortho_scale = x * 0.5 + 10
	co = bpy.data.objects.new("Cam", cam)
	sc.collection.objects.link(co)
	sc.camera = co
	sc.render.engine = "BLENDER_EEVEE"
	sc.view_settings.view_transform = "Standard"
	sc.render.resolution_x, sc.render.resolution_y = 2400, 700
	out = os.path.join(ROOT, "art", "kit", "renders")
	os.makedirs(out, exist_ok=True)
	half = x / 2
	for k, (x0, x1) in enumerate(((0, half), (half, x))):  # two rows' worth: render the left and right halves
		cam.ortho_scale = (x1 - x0) + 8
		co.location = ((x0 + x1) / 2, -300, 40)
		co.rotation_euler = (Vector(((x0 + x1) / 2, 0, 26)) - co.location).to_track_quat("-Z", "Y").to_euler()
		sc.render.filepath = os.path.join(out, f"vale_lineup_{k}.png")
		bpy.ops.render.render(write_still=True)


main()
