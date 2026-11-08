"""The colossal tree: a massive fused trunk with root buttresses and distinct tiers of huge limbs, each carrying flat pads of leaves with open air between tiers. Built from foliage_kit's parts.
Three meshes: Trunk (own bark sheet, more texture low down, where the player stands), Limbs (own bark sheet), Crown. Writes <out>/Colossal<seed>/Tree.glb, trunk_tubes.json, limbs/trunk_tubes.json;
paint with tools/art/paint_trunk.py on the folder and on its limbs subfolder.

  blender --background --python tools/blender/colossal_tree.py -- <out folder>
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foliage_kit as kit  # noqa: E402

SETTINGS = {
	"Height": (300.0, 350.0),
	"LeaderRadius": 19.0,  # three leaders overlap into one trunk about 60 studs across
	"Roots": 8,
	# share of the height, limbs, limb length, limb base radius, leaf pad radius
	"Tiers": [
		(0.36, 7, 165.0, 7.5, 34.0),
		(0.5, 7, 145.0, 6.5, 31.0),
		(0.63, 6, 120.0, 5.5, 28.0),
		(0.76, 6, 95.0, 4.5, 25.0),
		(0.88, 5, 68.0, 3.5, 22.0),
	],
	"SubBranches": (2, 3),
	"CardsPerPad": 15,
	"Squash": 0.36,  # flat pads are what make the tiers read as layers
	"TrunkTexture": 0.6,  # below 1: lower trunk gets more of the texture
}
SEEDS = (7, 23, 41)
GOLDEN = 2.39996


def leaders(r):
	S = SETTINGS
	tubes, tips = [], []
	H = r.uniform(*S["Height"])
	R = S["LeaderRadius"]
	off = r.uniform(0, math.tau)
	for i in range(3):
		a = off + i * math.tau / 3 + r.uniform(-0.15, 0.15)
		out = Vector((math.cos(a), math.sin(a), 0))
		height = H * (1.0 if i == 0 else r.uniform(0.86, 0.95))
		foot = out * R * 0.72 + Vector((0, 0, -4.0))
		pts = kit.path(r, foot, Vector((0, 0, 1)), out, height, r.uniform(16, 30), 0.72, 7.0, 26)
		radii = []
		for j in range(len(pts)):
			t = j / (len(pts) - 1)
			radii.append(R * (1 - t) ** 0.58 * (1 - 0.3 * kit.smooth(0.55, 1.0, t)) + 0.05)
		tube = kit.Tube(pts, radii, 14, "leader")
		tube.vpower = S["TrunkTexture"]
		tubes.append(tube)
		tips.append(pts[-2])
	return tubes, tips, H


def roots(r):
	"""buttresses: thick where they leave the trunk, running out and down into the ground"""
	tubes = []
	count = SETTINGS["Roots"]
	R = SETTINGS["LeaderRadius"]
	for i in range(count):
		a = i * math.tau / count + r.uniform(-0.2, 0.2)
		out = Vector((math.cos(a), math.sin(a), 0))
		reach = r.uniform(62, 95)
		top = r.uniform(30, 52)
		pts = []
		for j in range(11):
			t = j / 10
			along = R * 0.7 + reach * t ** 1.35
			z = top * (1 - t) ** 2.1 - 5 * t - 1
			pts.append(out * along + Vector((0, 0, z)) + Vector((-out.y, out.x, 0)) * math.sin(t * 3.1) * r.uniform(3, 7))
		radii = [(9.5 * (1 - j / 10) ** 0.8 + 1.1) for j in range(11)]
		tubes.append(kit.Tube(pts, radii, 8, "root"))
	return tubes


def limb_path(r, start, dirn, L, segs):
	"""a natural limb, not a spoke: it leaves the trunk climbing, bends away to level out, sags or lifts near its end, and wanders sideways with an elbow or two"""
	side = dirn.cross(Vector((0, 0, 1)))
	climb = L * r.uniform(0.1, 0.34)
	sag = L * r.uniform(-0.05, 0.16)
	sway, phase, freq = L * r.uniform(0.08, 0.2), r.uniform(0, math.tau), r.uniform(0.8, 1.6)
	elbow_at, elbow = r.uniform(0.3, 0.65), L * r.uniform(-0.09, 0.09)
	pts = []
	for j in range(segs + 1):
		t = j / segs
		up = climb * (1 - (1 - t) ** 2.2) - sag * t * t
		across = math.sin(t * math.tau * freq * 0.5 + phase) * sway * t + elbow * kit.smooth(elbow_at - 0.12, elbow_at + 0.12, t)
		pts.append(start + dirn * (L * t) + Vector((0, 0, up)) + side * across)
	return pts


def on_trunk(tubes, z, dirn):
	"""the middle of the main limb on this side at this height: a limb starts inside it, so its open end is never seen"""
	best = None
	for tube in tubes:
		p = min(tube.pts, key=lambda q: abs(q.z - z))
		score = p.x * dirn.x + p.y * dirn.y
		if best is None or score > best[0]:
			best = (score, p)
	return best[1]


def limbs(r, H, main):
	"""the tiers: limbs irregularly spaced round the trunk, each with a thick collar where it leaves, with sub-branches; every limb and sub-branch tip gets a leaf pad"""
	S = SETTINGS
	tubes, pads = [], []
	turn = r.uniform(0, math.tau)
	for tier, (share, count, length, radius, pad) in enumerate(S["Tiers"]):
		z = H * share
		for i in range(count):
			turn += GOLDEN + r.uniform(-0.6, 0.6)
			dirn = Vector((math.cos(turn), math.sin(turn), 0))
			L = length * r.uniform(0.68, 1.22)
			start = on_trunk(main, z + r.uniform(-H * 0.045, H * 0.045), dirn)
			pts = limb_path(r, start, dirn, L, 11)
			thick = radius * r.uniform(0.8, 1.2)
			radii = [thick * (1 - j / 11) ** 1.05 * (1 + 0.75 * math.exp(-j * 0.95)) + 0.2 for j in range(12)]
			tubes.append(kit.Tube(pts, radii, 7, "branch"))
			pads.append((pts[-1], pad * r.uniform(0.9, 1.15), tier))
			for _ in range(r.randint(*S["SubBranches"])):
				j = r.randint(4, 9)
				side = dirn.cross(Vector((0, 0, 1))) * r.choice((-1, 1))
				sub = (dirn * r.uniform(0.35, 0.9) + side).normalized()
				SL = L * r.uniform(0.26, 0.48)
				spts = limb_path(r, pts[j], sub, SL, 5)
				sradii = [radii[j] * 0.6 * (1 - q / 5) ** 1.1 + 0.1 for q in range(6)]
				tubes.append(kit.Tube(spts, sradii, 5, "branch"))
				pads.append((spts[-1], pad * r.uniform(0.72, 0.95), tier))
	return tubes, pads


def build(out, seed):
	folder = os.path.join(out, f"Colossal{seed}")
	os.makedirs(os.path.join(folder, "limbs"), exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	r = random.Random(seed)
	main_tubes, tips, H = leaders(r)
	trunk_tubes = main_tubes + roots(r)
	limb_tubes, pads = limbs(r, H, main_tubes)
	kit.pack(trunk_tubes)
	trunk = kit.Builder()
	for t in trunk_tubes:
		t.build(trunk)
	kit.pack(limb_tubes)
	limb = kit.Builder()
	for t in limb_tubes:
		t.build(limb)
	for path, tubes in ((folder, trunk_tubes), (os.path.join(folder, "limbs"), limb_tubes)):
		with open(os.path.join(path, "trunk_tubes.json"), "w", encoding="utf-8") as f:
			json.dump({"height": H, "tubes": [t.data() for t in tubes]}, f)
	crown = kit.Builder()
	kit.CARD_SCALE = 1.1
	kit.CLUMP_SQUASH = SETTINGS["Squash"]
	for c, radius, tier in pads:
		kit.clump(crown, r, c, radius, SETTINGS["CardsPerPad"], c.z - radius * 0.3, c.z + radius * 0.3)
	# a rounded top over the leaders' tips
	kit.CLUMP_SQUASH = 0.7
	for c in tips:
		kit.clump(crown, r, c, 30, 22, c.z - 22, c.z + 22)
	kit.CLUMP_SQUASH = 1.0
	objs = (trunk.finish("Trunk"), limb.finish("Limbs"), crown.finish("Crown"))
	for o in objs:
		o.select_set(True)
		print(f"Colossal{seed}", o.name, "triangles", sum(len(p.vertices) - 2 for p in o.data.polygons))
	bpy.ops.export_scene.gltf(filepath=os.path.join(folder, "Tree.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)


def main():
	out = sys.argv[sys.argv.index("--") + 1]
	for seed in SEEDS:
		build(out, seed)


main()
