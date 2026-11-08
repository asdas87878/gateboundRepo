"""Tree species and understory by the leaf-card method: tools/blender/foliage_kit.py's trunks and crowns, with its TREE settings per species. Forest types and what they need: docs/style/forests.md.
Writes <out>/<Species><Seed>/Tree.glb (Trunk, Crown) + trunk_tubes.json; paint each tree with tools/art/paint_trunk.py <that folder>. Understory pieces are one mesh, Crown only.

  blender --background --python tools/blender/foliage_species.py -- <out folder>
"""
import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foliage_kit as kit  # noqa: E402

BASE = dict(kit.TREE)
SPECIES = {
	# broad and rounded, big leaves: the deep wood's mass and general use
	"Oak": {"Scale": 1.3, "Clumps": 11, "CardsPerClump": 26, "ClumpRadius": (7.5, 10.0)},
	# huge and tall with a heavy trunk: landmarks and the deep wood's canopy
	"Elm": {"Scale": 1.3, "Leaders": 3, "LeaderHeight": (40.0, 48.0), "LeaderRadius": 2.2, "FootSpacing": 0.85, "WaistPinch": 0.55, "WaistAt": 0.2, "Spread": (9.0, 15.0), "PartAt": 0.52, "Wiggle": 1.6, "Branches": (3, 4), "BranchLength": (9.0, 14.0), "Clumps": 13, "CardsPerClump": 28, "ClumpRadius": (8.0, 11.0)},
	# tall and slender, an airy crown of small leaves high up: glades
	"Birch": {"Scale": 1.05, "Leaders": 2, "LeaderHeight": (34.0, 41.0), "LeaderRadius": 1.05, "FootSpacing": 0.6, "WaistPinch": 0.4, "WaistAt": 0.15, "Spread": (3.0, 6.0), "PartAt": 0.58, "Wiggle": 1.1, "Branches": (2, 3), "BranchLength": (5.0, 8.5), "Clumps": 9, "CardsPerClump": 34, "ClumpRadius": (5.0, 6.8)},
	# short, round and full: orchards and fields
	"Apple": {"Scale": 1.15, "Leaders": 3, "LeaderHeight": (20.0, 25.0), "LeaderRadius": 1.05, "FootSpacing": 0.7, "WaistPinch": 0.45, "WaistAt": 0.2, "Spread": (6.0, 9.0), "PartAt": 0.5, "Wiggle": 0.9, "Branches": (3, 4), "BranchFrom": 0.68, "BranchSpan": 0.26, "BranchRise": 0.35, "BranchLength": (5.0, 8.0), "Clumps": 11, "CardsPerClump": 32, "ClumpRadius": (4.6, 6.2)},
	# one straight trunk, tiers of level branches, a pointed top
	"Pine": {"Scale": 1.0, "Leaders": 1, "LeaderHeight": (54.0, 64.0), "LeaderRadius": 1.8, "FootSpacing": 0.0, "WaistPinch": 0.0, "Spread": (0.0, 1.0), "PartAt": 0.95, "Wiggle": 0.5, "Branches": (11, 13), "BranchFrom": 0.26, "BranchSpan": 0.7, "BranchRise": 0.14, "BranchThick": 0.26, "BranchLength": (9.0, 16.0), "Clumps": 18, "CardsPerClump": 26, "ClumpRadius": (4.2, 6.0)},
	# huge and thick, reaching far up, with layers of branches and leaves: the wood's giants
	"Giant": {"Scale": 1.25, "Leaders": 4, "LeaderHeight": (135.0, 170.0), "LeaderRadius": 7.5, "FootSpacing": 0.95, "WaistPinch": 0.5, "WaistAt": 0.14, "Spread": (14.0, 26.0), "PartAt": 0.6, "Wiggle": 3.5, "Branches": (7, 8), "BranchFrom": 0.34, "BranchSpan": 0.62, "BranchRise": 0.2, "BranchThick": 0.46, "BranchLength": (42.0, 72.0), "Clumps": 36, "CardsPerClump": 24, "ClumpRadius": (13.0, 19.0)},
	# a young tree for wood edges and gaps
	"Sapling": {"Scale": 1.0, "Leaders": 1, "LeaderHeight": (11.0, 14.0), "LeaderRadius": 0.42, "FootSpacing": 0.0, "WaistPinch": 0.0, "Spread": (1.5, 3.0), "PartAt": 0.4, "Wiggle": 0.5, "Branches": (2, 3), "BranchLength": (3.0, 5.0), "Clumps": 5, "CardsPerClump": 20, "ClumpRadius": (2.8, 3.8)},
}
SEEDS = {"Sapling": (7,)}
# canopy layers: a wide flat mass of leaves with no trunk, hung high between trees to close the ceiling. Radius of the whole, clump radius, squash
CANOPY = {"Canopy7": (54.0, 15.0, 7), "Canopy23": (38.0, 13.0, 23)}
UNDERSTORY = {
	"ShrubBig": {"Clumps": 5, "Radius": 4.6, "CardsPerClump": 26, "Seed": 12, "Scale": 1.2},
	"ShrubLow": {"Clumps": 3, "Radius": 2.9, "CardsPerClump": 20, "Seed": 31, "Scale": 1.2},
	"Fern": {"Clumps": 2, "Radius": 2.2, "CardsPerClump": 12, "Seed": 44, "Scale": 1.2},
}


def export(folder, objs):
	for o in objs:
		o.select_set(True)
	bpy.ops.export_scene.gltf(filepath=os.path.join(folder, "Tree.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)


def main():
	out = sys.argv[sys.argv.index("--") + 1]
	for name, settings in SPECIES.items():
		for seed in SEEDS.get(name, (7, 23)):
			folder = os.path.join(out, f"{name}{seed}")
			os.makedirs(folder, exist_ok=True)
			bpy.ops.wm.read_factory_settings(use_empty=True)
			kit.TREE.clear()
			kit.TREE.update(BASE)
			kit.TREE.update(settings)
			kit.TREE["Seed"] = seed
			kit.CARD_SCALE = settings["Scale"]
			trunk, crown = kit.build_tree(folder)
			trunk.name, crown.name = "Trunk", "Crown"
			trunk.data.name, crown.data.name = "Trunk", "Crown"
			print(name, seed, "triangles", sum(len(p.vertices) - 2 for o in (trunk, crown) for p in o.data.polygons))
			export(folder, (trunk, crown))
	for name, settings in UNDERSTORY.items():
		folder = os.path.join(out, name)
		os.makedirs(folder, exist_ok=True)
		bpy.ops.wm.read_factory_settings(use_empty=True)
		kit.BUSH.clear()
		kit.BUSH.update(settings)
		kit.CARD_SCALE = settings["Scale"]
		crown = kit.build_bush()
		crown.name = "Crown"
		crown.data.name = "Crown"
		print(name, "triangles", sum(len(p.vertices) - 2 for p in crown.data.polygons))
		export(folder, (crown,))
	for name, (radius, clump_radius, seed) in CANOPY.items():
		folder = os.path.join(out, name)
		os.makedirs(folder, exist_ok=True)
		bpy.ops.wm.read_factory_settings(use_empty=True)
		kit.CARD_SCALE = 1.25
		kit.CLUMP_SQUASH = 0.4
		r = random.Random(seed)
		b = kit.Builder()
		for i in range(11):
			a, d = r.uniform(0, 6.283), radius * r.random() ** 0.55
			c = kit.Vector((math.cos(a) * d, math.sin(a) * d, r.uniform(-5, 5)))
			kit.clump(b, r, c, clump_radius * r.uniform(0.8, 1.15), 20, -9, 9)
		kit.CLUMP_SQUASH = 1.0
		crown = b.finish("Crown")
		print(name, "triangles", sum(len(p.vertices) - 2 for p in crown.data.polygons))
		export(folder, (crown,))


main()
