"""Flower beds to fill the cobble kit's edging (docs/style/flower-beds.md): a solid painted leaf mound (soft overlapping blobs) with
painted cards on it, flower heads on top facing up and out, leaf clusters round the sides breaking up the outline. The foliage
method's findings carry over (docs/style/foliage-method.md): cards double-sided, normals leaning up, no cast shadow, so a bed reads
soft and bright. One card atlas layout for all colourways: cells 0-7 are leaves, 8-15 flowers, so white, pink and mixed beds are the
same meshes with another texture.

  blender --background --python tools/blender/flower_kit.py -- build     art/kit/flowers: flower_kit.blend, FlowerKit.glb, kit.json
  python tools/art/paint_flower_kit.py                                   FlowerMound_Color.png, FlowerCards_<White|Pink|Mixed>.png

Pieces (studs, origin on the ground; each has a <Piece>_Mound and a <Piece>_Cards mesh):
  BedRound  fills an edging ring of 8 Curve6 (radius 4.7), centred on its origin
  BedLong   8 long x 3.8 wide along +X from the origin, to chain between two straight edging runs 5 apart
  BedEnd    the rounded end of a long bed: a half disc of radius 2.1 on the +X side of its origin
  Clump, ClumpWide  loose clumps to dot about (radius 1.3 and 2.2)
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "flowers")
ARGS = sys.argv[sys.argv.index("--") + 1 :]
UP = Vector((0, 0, 1))
GRID = 4  # the card atlas is GRID x GRID cells
LEAF_CELLS, FLOWER_CELLS = list(range(0, 8)), list(range(8, 16))
UP_LEAN = 0.65  # how far every normal leans to straight up: soft even light, no black undersides
SINK = 0.3

PIECES = {
	"BedRound": {"Shape": ("disc", 4.7), "Blob": (1.4, 2.1), "Height": 0.85, "Seed": 11},
	"BedLong": {"Shape": ("rect", 8.0, 3.8), "Blob": (1.2, 1.8), "Height": 0.85, "Seed": 12},
	"BedEnd": {"Shape": ("half", 2.1), "Blob": (1.0, 1.5), "Height": 0.8, "Seed": 13},
	"Clump": {"Shape": ("disc", 1.3), "Blob": (0.8, 1.1), "Height": 0.9, "Seed": 14},
	"ClumpWide": {"Shape": ("disc", 2.2), "Blob": (0.9, 1.4), "Height": 0.75, "Seed": 15},
}
FLOWER_DENSITY = 1.15  # flower cards per square stud of mound top
LEAF_SPACING = 0.75  # studs between leaf cards round a blob's side


def inside(shape, x, y, margin=0.0):
	kind = shape[0]
	if kind == "disc":
		return math.hypot(x, y) <= shape[1] - margin
	if kind == "half":
		return x >= margin * 0.5 and math.hypot(x, y) <= shape[1] - margin
	L, W = shape[1], shape[2]
	return -0.2 <= x <= L + 0.2 and abs(y) <= W / 2 - margin


def bounds(shape):
	kind = shape[0]
	if kind == "disc":
		return -shape[1], shape[1], -shape[1], shape[1]
	if kind == "half":
		return 0, shape[1], -shape[1], shape[1]
	return 0, shape[1], -shape[2] / 2, shape[2] / 2


def blobs_for(spec):
	"""soft overlapping mounds covering the shape: biggest first, each new one where the cover is thinnest"""
	r = random.Random(spec["Seed"])
	shape = spec["Shape"]
	x0, x1, y0, y1 = bounds(shape)
	out = []
	for _ in range(60):
		best = None
		for _try in range(40):
			x, y = r.uniform(x0, x1), r.uniform(y0, y1)
			rb = r.uniform(*spec["Blob"])
			if not inside(shape, x, y, rb * 0.55):
				continue
			gap = min((math.hypot(x - b[0], y - b[1]) - b[2] * 0.7 for b in out), default=9.0)
			if best is None or gap > best[0]:
				best = (gap, x, y, rb)
		if best is None or best[0] < 0.15:
			break
		_, x, y, rb = best
		out.append((x, y, rb, rb * spec["Height"] * r.uniform(0.85, 1.15), r.uniform(0.8, 1.0)))
	return out


def lean(n):
	return (n.normalized() * (1 - UP_LEAN) + UP * UP_LEAN).normalized()


def mound_mesh(name, blobs):
	"""each blob a squashed half-ellipsoid sunk into the ground; u runs round it (repeating, so leaves keep their size), v up it"""
	bm = bmesh.new()
	uv = bm.loops.layers.uv.new("UV")
	normals = {}
	nu, nv = 16, 7
	for bx, by, rb, h, ry in blobs:
		reps = max(1, round(2 * math.pi * rb / 3.2))
		rings = []
		for j in range(nv + 1):
			phi = -0.35 + (math.pi / 2 + 0.35) * j / nv
			ring = []
			for i in range(nu + 1):  # a seam column, so u can run past 1
				th = 2 * math.pi * i / nu
				c, s = math.cos(phi), math.sin(phi)
				p = Vector((bx + rb * c * math.cos(th), by + rb * ry * c * math.sin(th), h * s - SINK * (1 - s)))
				v = bm.verts.new(p)
				nrm = Vector((c * math.cos(th) / rb, c * math.sin(th) / (rb * ry), s / h))
				normals[v] = lean(nrm)
				ring.append((v, i / nu * reps, 0.04 + 0.92 * max(0.0, min(1.0, (p.z + SINK) / (h + SINK)))))
			rings.append(ring)
		for j in range(nv):
			for i in range(nu):
				a, b, c2, d = rings[j][i], rings[j][i + 1], rings[j + 1][i + 1], rings[j + 1][i]
				f = bm.faces.new((a[0], b[0], c2[0], d[0]))
				for loop, info in zip(f.loops, (a, b, c2, d)):
					loop[uv].uv = (info[1], info[2])
	return finish(name, bm, normals)


def finish(name, bm, normals, per_loop=None):
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	order = list(bm.verts)
	bm.free()
	me.shade_smooth()
	if per_loop is None:
		vn = [tuple(normals[v]) for v in order]
		me.normals_split_custom_set_from_vertices(vn)
	else:
		me.normals_split_custom_set(per_loop)
	o = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(o)
	return o


def cell_uv(cell):
	u0, v1 = (cell % GRID) / GRID, 1 - (cell // GRID) / GRID
	pad = 0.004
	return [(u0 + pad, v1 - 1 / GRID + pad), (u0 + 1 / GRID - pad, v1 - 1 / GRID + pad), (u0 + 1 / GRID - pad, v1 - pad), (u0 + pad, v1 - pad)]


def hidden(p, blobs, own):
	for k, (bx, by, rb, h, ry) in enumerate(blobs):
		if k == own:
			continue
		q = ((p.x - bx) / rb) ** 2 + ((p.y - by) / (rb * ry)) ** 2 + ((p.z + SINK) / (h + SINK)) ** 2
		if q < 0.92:
			return True
	return False


def cards_mesh(name, blobs, seed):
	"""flower cards on the tops, facing up and a little outward; leaf cards round the sides, their foot on the mound, leaning out"""
	r = random.Random(seed)
	bm = bmesh.new()
	uv = bm.loops.layers.uv.new("UV")
	per_loop = []
	count = {"flower": 0, "leaf": 0}

	def card(centre, n, t1, size, cell, aspect=1.0):
		t2 = n.cross(t1).normalized()
		hw, hh = size / 2, size / 2 * aspect
		pts = [centre - t1 * hw - t2 * hh, centre + t1 * hw - t2 * hh, centre + t1 * hw + t2 * hh, centre - t1 * hw + t2 * hh]
		uvs = cell_uv(cell)
		for side, order in ((n, (0, 1, 2, 3)), (-n, (3, 2, 1, 0))):  # both faces (their own vertices), each lit as if it leaned to the sky
			vs = [bm.verts.new(p) for p in pts]
			f = bm.faces.new([vs[i] for i in order])
			for loop, i in zip(f.loops, order):
				loop[uv].uv = uvs[i]
				per_loop.append(tuple(lean(side)))

	for k, (bx, by, rb, h, ry) in enumerate(blobs):
		# flowers over the top
		n_top = max(2, int(math.pi * rb * rb * ry * 0.55 * FLOWER_DENSITY))
		for _ in range(n_top):
			for _try in range(10):
				th, rad = r.uniform(0, 2 * math.pi), math.sqrt(r.random()) * 0.78
				px, py = bx + rb * rad * math.cos(th), by + rb * ry * rad * math.sin(th)
				pz = h * math.sqrt(max(0.0, 1 - rad * rad)) - 0.02
				p = Vector((px, py, pz))
				if not hidden(p, blobs, k):
					break
			else:
				continue
			out = Vector((math.cos(th), math.sin(th), 0)) * rad
			a = r.uniform(0, 2 * math.pi)
			tilt = Vector((math.cos(a), math.sin(a), 0)) * r.uniform(0.25, 0.6) + out * 0.5
			n = (UP + tilt).normalized()
			t1 = n.cross(Vector((math.cos(a + 1.3), math.sin(a + 1.3), 0.3))).normalized()
			size = r.uniform(0.85, 1.35)
			card(p + n * 0.12 + UP * r.uniform(0.0, 0.25), n, t1, size, r.choice(FLOWER_CELLS))
			count["flower"] += 1
		# leaves round the side, a frilly edge
		n_side = max(4, int(2 * math.pi * rb / LEAF_SPACING))
		for i in range(n_side):
			th = 2 * math.pi * (i + r.uniform(-0.3, 0.3)) / n_side
			phi = r.uniform(0.05, 0.55)
			p = Vector((bx + rb * math.cos(phi) * math.cos(th), by + rb * ry * math.cos(phi) * math.sin(th), h * math.sin(phi) - SINK * (1 - math.sin(phi))))
			if hidden(p, blobs, k) or p.z < -0.1:
				continue
			out = Vector((math.cos(th), math.sin(th), 0))
			n = (out * 0.85 + UP * r.uniform(0.25, 0.6)).normalized()
			t1 = UP.cross(n).normalized()
			size = r.uniform(0.9, 1.4)
			centre = p + n.cross(t1).normalized() * (size * 0.3) + out * 0.08
			card(centre, n, t1, size, r.choice(LEAF_CELLS))
			count["leaf"] += 1
	o = finish(name, bm, None, per_loop)
	return o, count


def build():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	meta = {}
	for name, spec in PIECES.items():
		blobs = blobs_for(spec)
		mound = mound_mesh(name + "_Mound", blobs)
		cards, count = cards_mesh(name + "_Cards", blobs, spec["Seed"] + 100)
		meta[name] = {"Blobs": len(blobs), "Cards": count, "Parts": {}}
		for o in (mound, cards):
			vs = [v.co for v in o.data.vertices]
			o.data.calc_loop_triangles()
			meta[name]["Parts"][o.name] = {"Box": [round(min(v[i] for v in vs), 4) for i in range(3)] + [round(max(v[i] for v in vs), 4) for i in range(3)], "Tris": len(o.data.loop_triangles)}
	json.dump(meta, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "flower_kit.blend"))
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "FlowerKit.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	print("[flowers] built", {n: (m["Blobs"], m["Cards"], sum(p["Tris"] for p in m["Parts"].values())) for n, m in meta.items()}, flush=True)


if __name__ == "__main__":
	{"build": build}[ARGS[0]]()
