"""A stylized tree and bush by the leaf-card method.

Trunk: a bundle of leaders fused from the ground up (so the trunk has long grooves and tight V crotches), rising together and
then parting, on long S-curves that taper to points; side branches leave along the leaders, not at their ends. Rings use parallel
transport so tubes don't twist. Every tube gets its own area of one UV atlas, sized by its real surface, so the trunk can carry a
unique painted texture: tools/art/paint_trunk.py paints it from trunk_tubes.json, written here.

Crown: flat cards of white leaf clusters in round clumps on the branch tips, normals from a sphere around each clump leaning up.
Cards get real back faces. Height and depth pick each card's atlas cell: dark low and inside, light on top.

Units are studs, Z up, base at the origin. Output: FoliageTest.glb (TreeTrunk, TreeCrown, BushCrown) + trunk_tubes.json.

  blender --background --python tools/blender/foliage_kit.py -- <out folder>
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

# UV cells of leaves_white.png, from tools/art/make_foliage_textures.py
CELL_DARK, CELL_MID, CELL_LIGHT, CELL_SPARSE = 0, 1, 2, 3
TREE = {
	"Leaders": 3,
	"LeaderHeight": (27.0, 34.0),
	"LeaderRadius": 1.6,  # at the base; they overlap, so the trunk reads about twice this
	"FootSpacing": 0.8,  # leaders' feet from the centre: the skirt
	"WaistPinch": 0.55,  # how far they draw back in by the waist
	"WaistAt": 0.2,  # share of the height
	"Spread": (7.0, 13.0),  # how far each leans out by its tip
	"PartAt": 0.36,  # height (share of the leader) where the leaders start to part
	"Wiggle": 1.4,
	"Branches": (3, 4),  # side branches per leader
	"BranchLength": (7.0, 13.0),
	"Clumps": 9,
	"CardsPerClump": 42,
	"ClumpRadius": (6.5, 9.0),
	"Seed": 7,
}
BUSH = {"Clumps": 3, "Radius": 3.4, "CardsPerClump": 30, "Seed": 12}
CARD_SCALE = 1.0  # bigger leaf clusters per crown
CLUMP_SQUASH = 1.0  # below 1 flattens a clump: canopy layers
UP_LEAN = 0.72  # how much crown normals lean up: high, so a clump lit from above stays bright all round
TRUNK_UP = 0.82  # how much trunk normals lean up: the painted texture carries the form, as in the video's flattened trunk
FACET_CHISEL = 0.13  # how far columns move in and out
FACET_TWIST = 0.035  # radians per stud, scaled by thickness
ATLAS_MARGIN = 0.006  # of the atlas, between islands


def smooth(a, b, x):
	t = min(max((x - a) / (b - a), 0.0), 1.0)
	return t * t * (3 - 2 * t)


class Builder:
	def __init__(self):
		self.bm = bmesh.new()
		self.uv = self.bm.loops.layers.uv.new("UV")
		self.normal = {}

	def finish(self, name):
		for f in self.bm.faces:
			f.smooth = True
		self.bm.verts.index_update()
		order = list(self.bm.verts)
		mesh = bpy.data.meshes.new(name)
		self.bm.to_mesh(mesh)
		self.bm.free()
		mesh.normals_split_custom_set_from_vertices([tuple(self.normal[v]) for v in order])
		obj = bpy.data.objects.new(name, mesh)
		bpy.context.scene.collection.objects.link(obj)
		return obj


class Tube:
	"""a tapered path, as rings with one steady frame along it"""

	def __init__(self, pts, radii, sides, kind):
		self.pts, self.radii, self.sides, self.kind = pts, radii, sides, kind
		self.frames = []
		prev = None
		for i, p in enumerate(pts):
			d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
			a = d.orthogonal() if prev is None else prev - d * prev.dot(d)  # parallel transport: no twist
			a = a.normalized()
			self.frames.append((a, d.cross(a).normalized()))
			prev = a
		self.along = [0.0]
		for i in range(len(pts) - 1):
			self.along.append(self.along[-1] + (pts[i + 1] - pts[i]).length)
		self.length = self.along[-1]
		self.mean_round = sum(radii) / len(radii) * math.tau
		self.box = None
		self.vpower = 1.0  # below 1: the low end of the tube gets more of the texture

	def build(self, b):
		"""faceted: each quad has its own vertices and leans its normal toward its own flat face; columns are chiselled in and out and
		twist slowly up the limb, so planes and their edges run on the diagonal"""
		x0, y0, w, h = self.box
		r = random.Random(int(self.length * 1000) + self.sides)
		columns = [r.uniform(-1, 1) for _ in range(self.sides)]
		rings = []
		for p, rad, (a, c), s in zip(self.pts, self.radii, self.frames, self.along):
			ring = []
			twist = s * FACET_TWIST / max(rad, 0.5)
			for k in range(self.sides + 1):
				t = k / self.sides * math.tau + twist
				out = a * math.cos(t) + c * math.sin(t)
				size = 1 + FACET_CHISEL * columns[k % self.sides] + r.uniform(-1, 1) * FACET_CHISEL * 0.35
				ring.append((p + out * rad * size, (x0 + w * k / self.sides, y0 + h * (s / self.length) ** self.vpower)))
			ring[-1] = (ring[0][0], ring[-1][1])  # closed, though the UV column differs
			rings.append(ring)
		up = Vector((0, 0, 1))
		for r0, r1 in zip(rings, rings[1:]):
			for k in range(self.sides):
				corners = (r0[k], r0[k + 1], r1[k + 1], r1[k])
				vs = [b.bm.verts.new(c[0]) for c in corners]
				f = b.bm.faces.new(vs)
				f.normal_update()
				n = (f.normal * (1 - TRUNK_UP) + up * TRUNK_UP).normalized()
				for v in vs:
					b.normal[v] = n
				for lp, c in zip(f.loops, corners):
					lp[b.uv].uv = c[1]

	def data(self):
		return {
			"kind": self.kind,
			"vpower": self.vpower,
			"box": self.box,
			"sides": self.sides,
			"along": self.along,
			"radii": self.radii,
			"pts": [tuple(p) for p in self.pts],
			"a": [tuple(f[0]) for f in self.frames],
			"b": [tuple(f[1]) for f in self.frames],
		}


def path(r, start, up, out, length, reach, part, wiggle, segs):
	"""points along a long S: up first, leaning out later, with a slow sideways wave; the tip keeps climbing"""
	side = up.cross(out).normalized()
	phase, freq = r.uniform(0, math.tau), r.uniform(0.75, 1.15)  # slow bends: fewer kinks
	pts = []
	for i in range(segs + 1):
		t = i / segs
		lean = smooth(part, 1.0, t) ** 0.8 * reach
		wave = math.sin(t * math.tau * freq + phase) * wiggle * smooth(part * 0.5, part + 0.25, t)
		pts.append(start + up * (length * t) + out * lean + side * wave)
	return pts


def trunk_tubes(r):
	"""the leaders, their side branches and twigs; returns the tubes and the clump sites"""
	tubes, sites = [], []
	n = TREE["Leaders"]
	off = r.uniform(0, math.tau)
	R = TREE["LeaderRadius"]
	for i in range(n):
		a = off + i * math.tau / n + r.uniform(-0.25, 0.25)
		out = Vector((math.cos(a), math.sin(a), 0))
		H = r.uniform(*TREE["LeaderHeight"]) * (1.0 if i else 0.92)
		foot = out * TREE["FootSpacing"] * R + Vector((0, 0, -1.0))
		pts = path(r, foot, Vector((0, 0, 1)), out, H, r.uniform(*TREE["Spread"]), TREE["PartAt"], TREE["Wiggle"], 18)
		for j in range(len(pts)):  # skirt, then a pinched waist, then the Y
			pts[j] = pts[j] - out * TREE["WaistPinch"] * R * smooth(0.0, TREE["WaistAt"], j / (len(pts) - 1))
		radii = []
		for j, p in enumerate(pts):
			t = j / (len(pts) - 1)
			flare = 0.5 * math.exp(-max(p.z, 0) / (1.5 * max(R / 1.6, 1)))  # the root flare
			radii.append(R * (1 - t) ** 0.62 * (1 - 0.42 * smooth(0.5, 1.0, t)) * (1 + flare) + 0.001)  # thick well into the fork, then to a point
		tubes.append(Tube(pts, radii, 9, "leader"))
		sites.append(pts[-2])
		# side branches leave along the upper part of the leader
		count = r.randint(*TREE["Branches"])
		for k in range(count):
			t0 = TREE.get("BranchFrom", 0.5) + TREE.get("BranchSpan", 0.36) * (k + r.uniform(0.1, 0.8)) / count  # above the fork, which stays a clean V
			j = int(t0 * (len(pts) - 1))
			root = pts[j]
			turn = r.uniform(-1.4, 1.4)
			dirn = (out * math.cos(turn) + Vector((-out.y, out.x, 0)) * math.sin(turn)).normalized()
			if n <= 2:
				round_turn = off + i * 1.1 + k * 2.39996
				dirn = Vector((math.cos(round_turn), math.sin(round_turn), 0))
			L = r.uniform(*TREE["BranchLength"]) * (1.15 - 0.5 * t0)
			bpts = path(r, root, Vector((0, 0, 1)), dirn, L * TREE.get("BranchRise", 0.65), L * 0.85, 0.0, 0.8, 6)
			start_r = radii[j] * TREE.get("BranchThick", 0.62)  # stays inside the parent where it starts
			bradii = [start_r * (1 - m / 6) ** 1.25 + 0.001 for m in range(7)]
			tubes.append(Tube(bpts, bradii, 5, "branch"))
			sites.append(bpts[-2])
			# one twig off each branch
			m = r.randint(3, 4)
			tdir = (dirn + Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * 0.9).normalized()
			tpts = path(r, bpts[m], Vector((0, 0, 1)), tdir, L * 0.3, L * 0.32, 0.0, 0.3, 4)
			tradii = [bradii[m] * 0.6 * (1 - q / 4) ** 0.9 + 0.001 for q in range(5)]
			tubes.append(Tube(tpts, tradii, 4, "twig"))
	return tubes, sites


def pack(tubes):
	"""lay the tubes into the atlas as upright strips, at the same texel density, scaled until they fit"""
	ordered = sorted(tubes, key=lambda t: -t.length)
	density = 1.0
	boxes = []
	for _ in range(250):
		x = y = row = 0.0
		ok = True
		boxes = []
		for t in ordered:
			w, h = max(t.mean_round * density, 0.008), t.length * density
			if h > 1:
				ok = False
				break
			if x + w > 1:
				x, y, row = 0.0, y + row + ATLAS_MARGIN, 0.0
			if y + h > 1 or w > 1:
				ok = False
				break
			boxes.append((x, y, w, h))
			x += w + ATLAS_MARGIN
			row = max(row, h)
		if ok:
			break
		density *= 0.93
	for t, box in zip(ordered, boxes):
		t.box = box
	print("trunk atlas: studs per atlas", round(1 / density, 1), "tubes", len(tubes))


def card(b, r, centre, size, cell, sphere_c, up_lean):
	"""one leaf card, front and back, facing a random way"""
	n = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
	a = n.orthogonal().normalized()
	c = n.cross(a).normalized()
	turn = r.uniform(0, math.tau)
	a, c = a * math.cos(turn) + c * math.sin(turn), -a * math.sin(turn) + c * math.cos(turn)
	h = size / 2
	corners = [centre - a * h - c * h, centre + a * h - c * h, centre + a * h + c * h, centre - a * h + c * h]
	u0, v0 = (cell % 2) * 0.5, (cell // 2) * 0.5
	uvs = [(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.5), (u0, v0 + 0.5)]
	for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
		vs = [b.bm.verts.new(corners[i]) for i in order]
		f = b.bm.faces.new(vs)
		for lp, i in zip(f.loops, order):
			lp[b.uv].uv = uvs[i]
		for v in vs:
			b.normal[v] = ((v.co - sphere_c).normalized() * (1 - up_lean) + Vector((0, 0, up_lean))).normalized()


def clump(b, r, c, radius, count, low_z, high_z):
	for _ in range(count):
		d = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 0.8) * CLUMP_SQUASH)).normalized()
		depth = r.uniform(0.2, 0.8)
		p = c + d * radius * depth
		size = radius * r.uniform(1.0, 1.45) * CARD_SCALE
		height = (p.z - low_z) / max(high_z - low_z, 0.01)
		score = height * 0.65 + depth * 0.2 + d.z * 0.3 + r.uniform(-0.12, 0.12)
		if score < 0.32:
			cell = CELL_DARK
		elif score < 0.62:
			cell = CELL_MID
		elif depth > 0.6:
			cell = CELL_SPARSE  # the sparse cluster on the outside breaks up the silhouette
		else:
			cell = CELL_LIGHT
		card(b, r, p, size, cell, c, UP_LEAN)


def pick_sites(sites, count, first=None):
	"""the sites furthest from each other, so clumps spread evenly round the crown"""
	chosen = list(first) if first else [max(sites, key=lambda s: s.z)]
	while len(chosen) < min(count, len(sites)):
		chosen.append(max(sites, key=lambda s: min((s - c).length for c in chosen)))
	return chosen


def build_tree(out):
	r = random.Random(TREE["Seed"])
	tubes, sites = trunk_tubes(r)
	pack(tubes)
	trunk = Builder()
	for t in tubes:
		t.build(trunk)
	height = max(p.z for t in tubes for p in t.pts)
	with open(os.path.join(out, "trunk_tubes.json"), "w", encoding="utf-8") as f:
		json.dump({"height": height, "tubes": [t.data() for t in tubes]}, f)
	crown = Builder()
	spots = pick_sites(sites, TREE["Clumps"], [t.pts[-2] for t in tubes if t.kind == "leader"])
	low, high = min(s.z for s in spots) - 7, max(s.z for s in spots) + 7
	for s in spots:
		clump(crown, r, s, r.uniform(*TREE["ClumpRadius"]), TREE["CardsPerClump"], low, high)
	print("tree tubes", len(tubes), "clumps", len(spots), "height", round(high, 1))
	return trunk.finish("TreeTrunk"), crown.finish("TreeCrown")


def build_bush():
	r = random.Random(BUSH["Seed"])
	b = Builder()
	high = BUSH["Radius"] * 2.1
	for i in range(BUSH["Clumps"]):
		a = i * math.tau / BUSH["Clumps"]
		c = Vector((math.cos(a) * 2.1, math.sin(a) * 2.1, BUSH["Radius"] * r.uniform(0.75, 1.05)))
		clump(b, r, c, BUSH["Radius"] * r.uniform(0.85, 1.1), BUSH["CardsPerClump"], 0, high)
	return b.finish("BushCrown")


def main():
	out = sys.argv[sys.argv.index("--") + 1]
	os.makedirs(out, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	objs = [*build_tree(out), build_bush()]
	for o in objs:
		o.select_set(True)
		print(o.name, "triangles", sum(len(p.vertices) - 2 for p in o.data.polygons))
	bpy.ops.export_scene.gltf(filepath=os.path.join(out, "FoliageTest.glb"), export_format="GLB", use_selection=True, export_materials="NONE",
							  export_normals=True, export_apply=False, export_texcoords=True)
	print("exported", out)


if __name__ == "__main__":
	main()
