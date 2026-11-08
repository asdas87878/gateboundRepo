"""Grass experiments (docs/style/grass.md): the same patch of meadow, light and camera, with a different grass method
each time, so methods can be judged side by side. Bright warm sun, darkish shadows (the direction the user picked).

  blender --background --python tools/blender/grass_bench.py -- <out dir> [--methods a,b] [--res 960x540]

Methods (community practice: normals up so grass shades like the ground, root colour = ground colour, gradient to the
tips, clumps, density near the camera):
  none      ground only (baseline)
  clumps    the kit's field-grass clumps, own vertex colours (what the Vale used)
  matched   blade clumps whose colour comes from the ground under each clump, darker roots, lighter tips
  cards     crossed cards with a painted tuft texture, ground-matched colour, alpha cut-out
  carpet    a dense uniform carpet of short thin blades (stand-in for Roblox's terrain decoration grass)
  chunky    a few wide low-poly blades per tuft, ground-matched (stylised, fewest triangles)
  mixed     carpet everywhere + matched clumps in drifts + flowers (the layered look)
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
import kit  # noqa: E402
import kit_vale as kv  # noqa: E402
from grass_kit import blade_clump, card_tuft, matched_material, scatter  # noqa: E402
import sky_paint  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(ARGS[0])
FL = ARGS[1:]
METHODS = (FL[FL.index("--methods") + 1].split(",") if "--methods" in FL else ["none", "clumps", "matched", "cards", "carpet", "chunky", "mixed"])
RES = tuple(int(v) for v in (FL[FL.index("--res") + 1].split("x") if "--res" in FL else (960, 540)))
SIZE, STEP = 110.0, 0.5


def lin(h):
	return kit.to_linear(kit.srgb(h))


def noise(X, Y, scale, seed):
	r = np.random.RandomState(seed)
	out = np.zeros_like(X)
	for o in range(3):
		for _ in range(3):
			a, ph = r.uniform(0, math.tau), r.uniform(0, math.tau)
			f = math.tau / scale * 2 ** o
			out += np.sin((X * math.cos(a) + Y * math.sin(a)) * f + ph) / 2 ** o
	return out / 3.5


def ground(coll):
	xs = np.arange(-SIZE / 2, SIZE / 2 + 1e-6, STEP)
	X, Y = np.meshgrid(xs, xs)
	Z = noise(X, Y, 60, 1) * 1.6 + np.clip((Y - 10) * 0.05, 0, 2.5)
	# a dirt path curving away from the camera
	px = np.sin(Y * 0.045) * 9 + 4
	dpath = np.abs(X - px)
	Z -= np.clip(1 - dpath / 4, 0, 1) * 0.25
	a, b, dry = np.array(lin("8fbf45")), np.array(lin("6aa23a")), np.array(lin("c9b85a"))
	n1 = noise(X, Y, 40, 3) * 0.5 + 0.5
	col = a * (1 - n1[..., None]) + b * n1[..., None]
	d = np.clip((noise(X, Y, 22, 4) * 0.5 + 0.5 - 0.62) / 0.2, 0, 1)[..., None] * 0.35
	col = col * (1 - d) + dry * d
	col *= (1 + noise(X, Y, 4, 5) * 0.06)[..., None]
	w = np.clip((2.8 - dpath + noise(X, Y, 5, 6) * 0.9) / 1.5, 0, 1)[..., None]
	col = col * (1 - w) + np.array(lin("a8804c")) * w
	n = len(xs)
	verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
	idx = np.arange(n * n).reshape(n, n)
	quads = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
	me = bpy.data.meshes.new("Ground")
	me.vertices.add(len(verts))
	me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
	me.loops.add(len(quads) * 4)
	me.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
	me.polygons.add(len(quads))
	me.polygons.foreach_set("loop_start", np.arange(0, len(quads) * 4, 4, dtype=np.int32))
	me.update(calc_edges=True)
	me.polygons.foreach_set("use_smooth", np.ones(len(quads), bool))
	attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	attr.data.foreach_set("color", np.concatenate([col.reshape(-1, 3), np.ones((n * n, 1))], 1).astype(np.float32).ravel())
	g = np.clip(dpath - 2.2, 0, 1)  # grass everywhere but the path
	for name, arr in (("g", g), ("drift", np.clip((noise(X, Y, 14, 8) * 0.5 + 0.5 - 0.5) / 0.2, 0, 1) * g), ("fl", np.clip((noise(X, Y, 10, 9) * 0.5 + 0.5 - 0.62) / 0.15, 0, 1) * g)):
		at = me.attributes.new(name, "FLOAT", "POINT")
		at.data.foreach_set("value", arr.astype(np.float32).ravel())
	me.materials.append(kit.vertex_material())
	obj = bpy.data.objects.new("Ground", me)
	coll.objects.link(obj)
	return obj, (X, Y, Z)


def method(name, g):
	for mod in list(g.modifiers):
		g.modifiers.remove(mod)
	for o in [o for o in bpy.data.objects if o.get("grass_scatter")]:  # each method's instances live on their own objects
		bpy.data.objects.remove(o)
	if name == "none":
		return
	if name == "clumps":
		objs = [kv.field_grass(f"FG{k}", 300 + k, 14, 1.25) for k in range(4)]
		scatter(g, "S_clumps", "g", objs, 3.0)
	elif name == "matched":
		mat = matched_material("MatchedBlades", tint="f2ffd8")
		objs = [blade_clump(f"MB{k}", 310 + k, 16, 1.2, 0.07, 0.35) for k in range(4)]
		scatter(g, "S_matched", "g", objs, 3.0, match=True, material=mat)
	elif name == "cards":
		mat = matched_material("CardBlades", texture="grass_tuft.png", tint="f2ffd8")
		objs = [card_tuft(f"CT{k}", 320 + k) for k in range(2)]
		scatter(g, "S_cards", "g", objs, 1.6, (0.7, 1.4), match=True, material=mat)
	elif name == "carpet":
		mat = matched_material("CarpetBlades", tint="f2ffd8")
		objs = [blade_clump(f"CB{k}", 330 + k, 26, 0.55, 0.035, 0.6) for k in range(3)]
		scatter(g, "S_carpet", "g", objs, 3.5, (0.8, 1.2), match=True, material=mat)
	elif name == "chunky":
		mat = matched_material("ChunkyBlades", tint="f2ffd8")
		objs = [blade_clump(f"CK{k}", 340 + k, 5, 1.1, 0.12, 0.25, chunky=True) for k in range(4)]
		scatter(g, "S_chunky", "g", objs, 2.2, match=True, material=mat)
	elif name == "mixed":
		mat = matched_material("MixedCarpet", tint="f2ffd8")
		scatter(g, "S_carpet", "g", [blade_clump(f"MC{k}", 330 + k, 26, 0.55, 0.035, 0.6) for k in range(3)], 3.0, (0.8, 1.2), match=True, material=mat)
		mat2 = matched_material("MixedClumps", tint="f6ffe0")
		scatter(g, "S_drift", "drift", [blade_clump(f"MD{k}", 350 + k, 18, 1.5, 0.07, 0.4) for k in range(4)], 2.5, (0.8, 1.35), seed=5, match=True, material=mat2)
		fl = [kit.flowers(f"MF{k}", 400 + k, kind=("white", "yellow", "white")[k], count=10 if k != 1 else 4) for k in range(3)]
		scatter(g, "S_flowers", "fl", fl, 0.5, (0.8, 1.2), seed=9)


def setup(coll):
	sc = bpy.context.scene
	g, _ = ground(coll)
	tree = kv.broadleaf("Tree", 101, 16, kind="oak")
	tree.location = (-16, 26, 0)
	coll.objects.link(tree)
	rock = kv.mossy_boulder("Rock", 21, (6, 5, 4))
	rock.location = (9, 10, -0.5)
	coll.objects.link(rock)
	pine = kit.pine("Pine", 140, 26)
	pine.location = (22, 44, 0)
	coll.objects.link(pine)
	sky = {"Size": [1024, 512], "Gradient": [[-2, "c9d8de"], [2, "b9d2de"], [8, "98c2da"], [20, "6ea9d1"], [40, "4b90c7"], [90, "3677b7"]],
		   "SunDir": [0.6, 0.5, 0.62], "Cumulus": {"Seed": 3, "Count": 30, "Elevation": [3, 14], "Size": [3, 8], "Colour": "ffffff", "Shade": "b6c6d8"}}
	colr = sky_paint.paint(sky)
	H, W = colr.shape[:2]
	img = bpy.data.images.new("Sky", W, H, alpha=False, float_buffer=True)
	img.pixels.foreach_set(np.concatenate([colr[::-1], np.ones((H, W, 1), np.float32)], -1).ravel())
	w = bpy.data.worlds.new("W")
	sc.world = w
	w.use_nodes = True
	nt = w.node_tree
	env = nt.nodes.new("ShaderNodeTexEnvironment")
	env.image = img
	bg = nt.nodes["Background"]
	nt.links.new(env.outputs["Color"], bg.inputs["Color"])
	bg.inputs["Strength"].default_value = 0.85  # low fill: shadows stay dark
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = 4.2
	sun.color = lin("fff0d2")
	sun.angle = math.radians(2.5)
	so = bpy.data.objects.new("Sun", sun)
	so.rotation_euler = (Vector((-0.55, -0.35, -0.62))).to_track_quat("-Z", "Y").to_euler()  # from the front-right
	sc.collection.objects.link(so)
	cam = bpy.data.cameras.new("Cam")
	cam.sensor_fit = "VERTICAL"
	cam.angle_y = math.radians(55)
	co = bpy.data.objects.new("Cam", cam)
	co.location = (0, -30, 5.5)
	co.rotation_euler = (Vector((0, 18, 1.5)) - co.location).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(co)
	sc.camera = co
	sc.render.engine = "BLENDER_EEVEE"
	sc.render.resolution_x, sc.render.resolution_y = RES
	sc.eevee.taa_render_samples = 32
	sc.view_settings.view_transform = "Standard"
	return g


def main():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	coll = bpy.data.collections.new("Bench")
	bpy.context.scene.collection.children.link(coll)
	g = setup(coll)
	for m in METHODS:
		method(m, g)
		bpy.context.scene.render.filepath = os.path.join(OUT, f"{m}.png")
		bpy.ops.render.render(write_still=True)
		print(f"[grass] {m} rendered", flush=True)


main()
