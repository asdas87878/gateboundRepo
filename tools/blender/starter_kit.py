"""Kit lineup and Roblox export (docs/look-rules.md): builds every kit piece from tools/blender/kit.py with the look's
palette (the "Palette" of art/look/ashen_ref/scene.json), renders a lineup sheet and writes one glb per piece.

blender --background --python tools/blender/starter_kit.py -- [--render] [--export]

--render  art/kit/renders/lineup.png
--export  art/kit/glb/<Name>.glb (studs, vertex colours, no materials; Roblox: SmoothPlastic, Color white)
Saves art/kit/StarterKit.blend either way. Units are studs; Blender Z is up (Roblox Y).
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "art", "kit")
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
SPEC = json.load(open(os.path.join(ROOT, "art", "look", "ashen_ref", "scene.json"), encoding="utf-8"))
kit.PAL.update(SPEC.get("Palette", {}))

# name: (generator, seed, args) - sizes are the reference copy's, in studs
PIECES = {
	"Pine1": (kit.pine, 110, {"height": 30}),
	"Pine2": (kit.pine, 111, {"height": 30}),
	"PineWide": (kit.pine, 112, {"height": 30, "slender": 1.25}),
	"Boulder1": (kit.boulder, 21, {"size": [9, 6, 4.5]}),
	"Boulder2": (kit.boulder, 22, {"size": [6, 5, 3.5]}),
	"Boulder3": (kit.boulder, 23, {"size": [4, 3.5, 2.2]}),
	"Boulder4": (kit.boulder, 25, {"size": [6, 5, 3.5]}),
	"GrassTuft": (kit.grass_clump, 300, {"blades": 16, "height": 1.9}),
	"GrassShort": (kit.grass_clump, 330, {"blades": 10, "height": 0.8}),
	"WhiteFlowers": (kit.flowers, 400, {"kind": "white", "count": 14}),
	"YellowFlowers": (kit.flowers, 420, {"kind": "yellow", "count": 3}),
	"Bush": (kit.bush, 160, {"size": 3.0}),
	"GateTowerBig": (kit.tower, 51, {"height": 40, "width": 14}),
	"GateTowerSmall": (kit.tower, 50, {"height": 36, "width": 13}),
	"TowerRuined": (kit.tower, 55, {"height": 40, "width": 12, "ruined": True}),
	"Arch": (kit.arch, 52, {"span": 11.2, "thick": 1.5, "depth": 3.4, "pier_h": 7.2}),
	"RuinArches": (kit.ruin_arches, 57, {"bays": 3, "bay": 12, "height": 14}),
	"Banner": (kit.banner, 61, {"width": 3.2, "length": 8.0}),
	"BannerPole": (kit.banner_pole, 71, {"height": 12, "arm": 4.6, "side": 1}),
	"Stele": (kit.stele, 80, {}),
	"Golem": (kit.golem, 90, {}),
	"Hero": (kit.hero, 7, {}),
}


def lineup(objs):
	sc = bpy.context.scene
	coll = bpy.data.collections.new("Lineup")
	sc.collection.children.link(coll)
	x = 0.0
	for name, o in objs.items():
		xs = [v.co.x for v in o.data.vertices]
		c = bpy.data.objects.new(name + "_lineup", o.data)
		c.location = (x - min(xs), 0, 10 if name == "Banner" else 0)
		coll.objects.link(c)
		x += max(xs) - min(xs) + 3
	w = bpy.data.worlds.new("W")
	sc.world = w
	w.use_nodes = True
	w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.7, 0.75, 1)
	w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.6
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = 2.4
	sun.color = kit.to_linear(kit.srgb("ffe8c2"))
	so = bpy.data.objects.new("Sun", sun)
	so.rotation_euler = (math.radians(45), 0, math.radians(-70))
	sc.collection.objects.link(so)
	cam = bpy.data.cameras.new("Cam")
	cam.type = "ORTHO"
	cam.ortho_scale = x + 6
	co = bpy.data.objects.new("Cam", cam)
	co.location = (x / 2, -200, 24)
	co.rotation_euler = (Vector((x / 2, 0, 22)) - co.location).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(co)
	sc.camera = co
	sc.render.engine = "BLENDER_EEVEE"
	sc.render.resolution_x, sc.render.resolution_y = 2600, 520
	sc.view_settings.view_transform = "Standard"
	sc.render.filepath = os.path.join(OUT, "renders", "lineup.png")
	bpy.ops.render.render(write_still=True)


def main():
	bpy.ops.wm.read_factory_settings(use_empty=True)
	coll = bpy.data.collections.new("Kit")
	bpy.context.scene.collection.children.link(coll)
	objs = {name: fn(name, seed, coll=coll, **args) for name, (fn, seed, args) in PIECES.items()}
	for i, o in enumerate(objs.values()):
		o.location = (i * 60, -5000, 0)
	tris = {n: sum(len(p.vertices) - 2 for p in o.data.polygons) for n, o in objs.items()}
	print("[kit] triangles:", tris)
	os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
	if "--export" in ARGS:
		gdir = os.path.join(OUT, "glb")
		os.makedirs(gdir, exist_ok=True)
		for name, o in objs.items():
			loc = o.location.copy()
			o.location = (0, 0, 0)
			bpy.ops.object.select_all(action="DESELECT")
			o.select_set(True)
			bpy.context.view_layer.objects.active = o
			bpy.ops.export_scene.gltf(filepath=os.path.join(gdir, f"{name}.glb"), export_format="GLB", use_selection=True,
									  export_materials="NONE", export_vertex_color="ACTIVE", export_normals=True, export_apply=True)
			o.location = loc
		json.dump(tris, open(os.path.join(gdir, "triangles.json"), "w"), indent=1)
		print("[kit] exported", len(objs), "pieces to", gdir)
	if "--render" in ARGS:
		lineup(objs)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "StarterKit.blend"))


main()
