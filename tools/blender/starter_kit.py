"""Starter environment kit: low-poly flat-shaded props coloured per face (vertex colours, no textures).

blender --background --python tools/blender/starter_kit.py -- [--render] [--export]

--render  builds a test scene (road to a ruined gate) and renders art/kit/renders/scene.png + lineup.png
--export  writes each prop to art/kit/glb/<Name>.glb (studs, vertex colours, no materials) for Roblox
Saves art/kit/StarterKit.blend either way. Units are studs; Blender Z is up (Roblox Y).
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Color, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit")
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []

# palette (sRGB hex) picked from the reference
PAL = {
	"pine": "3a6c5a",
	"pine_lit": "6a9a72",
	"bark": "5a4232",
	"rock": "8c929a",
	"rock_dark": "6c727c",
	"moss": "6f8f4c",
	"grass": "7fa947",
	"grass_dark": "55823c",
	"grass_tip": "a2b955",
	"flower": "e8c84a",
	"stone": "a19d94",
	"stone_dark": "86837c",
	"banner": "9c2a24",
	"gold": "d8a53c",
	"wood": "6b4a33",
	"leaf": "4f7d3c",
	"dirt": "c8b48a",
	"mountain": "7d93a8",
}


def srgb(hex_):
	c = Color()
	c.r, c.g, c.b = (int(hex_[i : i + 2], 16) / 255 for i in (0, 2, 4))
	return c


def jitter(hex_, rng, v=0.05, h=0.01, s=0.04):
	"""the palette colour with a small random shift in hue/saturation/value: each facet a slightly different tint"""
	c = srgb(hex_)
	c.h = (c.h + rng.uniform(-h, h)) % 1
	c.s = min(1, max(0, c.s + rng.uniform(-s, s)))
	c.v = min(1, max(0, c.v * (1 + rng.uniform(-v, v))))
	return c


def mix(a, b, t):
	return Color((a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t))


class Piece:
	"""a bmesh being built, with a face-corner colour layer; faces are coloured as they are added"""

	def __init__(self, seed):
		self.bm = bmesh.new()
		self.col = self.bm.loops.layers.color.new("Col")
		self.rng = random.Random(seed)

	def paint(self, faces, fn):
		for f in faces:
			f.normal_update()
			c = fn(f)
			for loop in f.loops:
				# the layer holds linear colours; glTF stores COLOR_0 linear too, Roblox shows it as authored
				loop[self.col] = (*srgb_to_linear(c), 1.0)

	def hull(self, pts, fn, dissolve=0.0):
		before = set(self.bm.faces)
		verts = [self.bm.verts.new(p) for p in pts]
		res = bmesh.ops.convex_hull(self.bm, input=verts)
		junk = set(res["geom_interior"]) | set(res["geom_unused"])
		bmesh.ops.delete(self.bm, geom=[v for v in junk if isinstance(v, bmesh.types.BMVert)], context="VERTS")
		if dissolve:
			new = [f for f in self.bm.faces if f not in before]
			edges = list({e for f in new for e in f.edges})
			bmesh.ops.dissolve_limit(self.bm, angle_limit=math.radians(dissolve), verts=list({v for f in new for v in f.verts}), edges=edges)
		new = [f for f in self.bm.faces if f not in before]
		self.paint(new, fn)
		return new

	def quad_strip(self, rows, fn, close=False):
		"""faces between consecutive rings of points (lists of Vectors of equal length)"""
		before = set(self.bm.faces)
		vs = [[self.bm.verts.new(p) for p in ring] for ring in rows]
		n = len(rows[0])
		for a, b in zip(vs, vs[1:]):
			for i in range(n if close else n - 1):
				j = (i + 1) % n
				self.bm.faces.new((a[i], a[j], b[j], b[i]))
		new = [f for f in self.bm.faces if f not in before]
		self.paint(new, fn)
		return new

	def tri(self, a, b, c, colour):
		f = self.bm.faces.new([self.bm.verts.new(p) for p in (a, b, c)])
		self.paint([f], lambda _f: colour)
		return f

	def finish(self, name, collection):
		for f in self.bm.faces:
			f.smooth = False
		mesh = bpy.data.meshes.new(name)
		self.bm.to_mesh(mesh)
		self.bm.free()
		obj = bpy.data.objects.new(name, mesh)
		collection.objects.link(obj)
		obj.data.materials.append(kit_material())
		return obj


def srgb_to_linear(c):
	def f(x):
		return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

	return f(c.r), f(c.g), f(c.b)


def up_tint(base, lit, rng, strength=1.0):
	"""colour a facet by how much it faces up: lit tint on tops, base on the sides/underside"""

	def fn(f):
		t = max(0.0, f.normal.z) ** 1.5 * strength
		return mix(jitter(base, rng), jitter(lit, rng), t)

	return fn


# ---------------------------------------------------------------- props


def pine(name, seed, height=22.0, coll=None):
	p = Piece(seed)
	r = p.rng
	trunk_h = height * 0.22
	tw = height * 0.035
	ring = lambda z, w: [Vector((math.cos(a) * w, math.sin(a) * w, z)) for a in (i * math.tau / 6 + 0.3 for i in range(6))]
	p.hull(ring(0, tw * 1.2) + ring(trunk_h + 1.5, tw * 0.8), lambda f: jitter(PAL["bark"], r))
	tiers = r.randint(4, 6)
	z = trunk_h
	top = height
	for t in range(tiers):
		k = t / (tiers - 1)
		radius = height * (0.30 - 0.20 * k) * r.uniform(0.92, 1.08)
		tier_h = (top - trunk_h) / tiers * 1.9
		n = r.randint(7, 9)
		pts = []
		off = r.uniform(0, math.tau)
		for i in range(n):
			a = off + i * math.tau / n + r.uniform(-0.15, 0.15)
			rr = radius * r.uniform(0.85, 1.1)
			pts.append(Vector((math.cos(a) * rr, math.sin(a) * rr, z + r.uniform(-0.4, 0.2))))
		apex_z = min(top, z + tier_h)
		pts.append(Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), apex_z)))
		pts.append(Vector((0, 0, z + tier_h * 0.12)))  # underside centre so the tier bottom is a shallow cone
		p.hull(pts, up_tint(PAL["pine"], PAL["pine_lit"], r, 0.9))
		z += (top - trunk_h) / tiers * 0.95
	return p.finish(name, coll)


def boulder(name, seed, size=(6, 5, 4), mossy=True, coll=None):
	p = Piece(seed)
	r = p.rng
	pts = []
	for _ in range(22):
		v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
		v.x *= size[0] / 2 * r.uniform(0.8, 1.05)
		v.y *= size[1] / 2 * r.uniform(0.8, 1.05)
		v.z *= size[2] / 2 * r.uniform(0.8, 1.05)
		pts.append(v)
	moss = mossy and r.random() < 0.8

	def fn(f):
		c = mix(jitter(PAL["rock_dark"], r), jitter(PAL["rock"], r), 0.5 + 0.5 * f.normal.z)
		if moss and f.normal.z > 0.75 and r.random() < 0.7:
			c = jitter(PAL["moss"], r)
		return c

	p.hull(pts, fn, dissolve=8)
	p.bm.transform(_mat_translate(Vector((0, 0, size[2] * 0.32))))  # sunk a little: sits in the ground
	return p.finish(name, coll)


def _mat_translate(v):
	from mathutils import Matrix

	return Matrix.Translation(v)


def grass_tuft(name, seed, blades=9, flowers=0, coll=None):
	p = Piece(seed)
	r = p.rng
	for _ in range(blades):
		a = r.uniform(0, math.tau)
		d = r.uniform(0, 0.5)
		base = Vector((math.cos(a) * d, math.sin(a) * d, -0.1))
		h = r.uniform(0.6, 1.25)
		lean = Vector((math.cos(a) * h * 0.35, math.sin(a) * h * 0.35, h))
		w = r.uniform(0.1, 0.16)
		side = Vector((-math.sin(a + 1.2), math.cos(a + 1.2), 0)) * w
		tip = base + lean
		p.tri(base - side, base + side, tip, mix(jitter(PAL["grass_dark"], r), jitter(PAL["grass_tip"], r), r.uniform(0.3, 0.8)))
	for _ in range(flowers):
		a = r.uniform(0, math.tau)
		d = r.uniform(0.2, 0.7)
		c = Vector((math.cos(a) * d, math.sin(a) * d, r.uniform(0.45, 0.85)))
		s = 0.13
		pts = [c + Vector((x, y, 0)) * s for x, y in ((1, 0), (0, 1), (-1, 0), (0, -1))] + [c + Vector((0, 0, s * 0.6))]
		p.hull(pts, lambda f: jitter(PAL["flower"], r, v=0.08))
		p.tri(c - Vector((0.03, 0, 0)), c + Vector((0.03, 0, 0)), Vector((c.x * 0.6, c.y * 0.6, -0.1)), jitter(PAL["grass_dark"], r))
	return p.finish(name, coll)


def bush(name, seed, size=3.0, coll=None):
	p = Piece(seed)
	r = p.rng
	for i in range(r.randint(3, 5)):
		c = Vector((r.uniform(-1, 1) * size * 0.35, r.uniform(-1, 1) * size * 0.35, size * r.uniform(0.25, 0.45)))
		rad = size * r.uniform(0.3, 0.45)
		pts = []
		for _ in range(14):
			v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized() * rad * r.uniform(0.85, 1.05)
			v.z *= 0.8
			pts.append(c + v)
		p.hull(pts, up_tint(PAL["grass_dark"], PAL["leaf"], r, 1.2), dissolve=4)
	return p.finish(name, coll)


def brick(p, centre, size, colour_fn):
	"""a chipped stone block: a box with its corners cut back by random amounts"""
	r = p.rng
	sx, sy, sz = size
	m = min(size)
	pts = []
	for cx in (-1, 1):
		for cy in (-1, 1):
			for cz in (-1, 1):
				corner = Vector((cx * sx / 2, cy * sy / 2, cz * sz / 2))
				if r.random() < 0.5:  # half the corners stay sharp: fewer triangles
					pts.append(centre + corner)
					continue
				cut = r.uniform(0.08, 0.2) * m
				for axis in range(3):
					q = corner.copy()
					q[axis] -= (cx, cy, cz)[axis] * cut * r.uniform(0.5, 1.4)
					pts.append(centre + q)
	return p.hull(pts, colour_fn, dissolve=3)


def stone_fn(p):
	r = p.rng

	def fn(f):
		return mix(jitter(PAL["stone_dark"], r, v=0.06), jitter(PAL["stone"], r, v=0.06), 0.55 + 0.45 * max(0, f.normal.z))

	return fn


def tower(name, seed, height=30.0, width=7.0, ruined=False, coll=None):
	"""a square stone column laid course by course, wider plinth, crenellated top (or a broken top when ruined)"""
	p = Piece(seed)
	r = p.rng
	fn = stone_fn(p)
	course = 2.4
	depth = 1.2
	z = 0.0
	n_courses = int(height / course)
	for c in range(n_courses):
		plinth = c < 2
		w = width + (1.4 if plinth else 0)
		n = 3 if plinth else 2
		for side in range(4):
			ang = side * math.pi / 2
			along = Vector((math.cos(ang), math.sin(ang), 0))
			out = Vector((math.cos(ang - math.pi / 2), math.sin(ang - math.pi / 2), 0))
			# corners interlock: each course, one pair of opposite sides runs the full width over the other pair's ends
			length = w if (side + c) % 2 == 0 else w - 2 * depth
			offset = 0.5 * (c % 2) * length / n
			cuts = sorted({-length / 2, length / 2} | {-length / 2 + offset + i * length / n for i in range(1, n) if offset + i * length / n < length - 0.6})
			for a, b in zip(cuts, cuts[1:]):
				if ruined and c > n_courses * 0.7 and r.random() < (c - n_courses * 0.7) / (n_courses * 0.3):
					continue
				centre = along * ((a + b) / 2) + out * (w / 2 - depth / 2) + Vector((0, 0, z + course / 2))
				size = ((b - a) - 0.1, depth, course * r.uniform(0.93, 0.97))
				# local x runs along the side, local y outward
				brick(p, centre, size if side % 2 == 0 else (size[1], size[0], size[2]), fn)
		z += course
	# core so you never see through the gaps
	core = width - 1.6
	p.hull([Vector((x * core / 2, y * core / 2, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (0, z)], lambda f: jitter(PAL["stone_dark"], r))
	if not ruined:
		cap = width + 0.8
		p.hull([Vector((x * cap / 2, y * cap / 2, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (z, z + 1.0)], fn)
		z += 1.0
		for side in range(4):
			ang = side * math.pi / 2
			along = Vector((math.cos(ang), math.sin(ang), 0))
			out = Vector((math.cos(ang - math.pi / 2), math.sin(ang - math.pi / 2), 0))
			for i in (-1, 1):
				centre = along * (i * cap / 3) + out * (cap / 2 - 0.6) + Vector((0, 0, z + 1.2))
				brick(p, centre, (1.8, 1.8, 2.4), fn)
	return p.finish(name, coll)


def banner(name, seed, length=8.0, coll=None):
	"""a cloth banner hanging from a wooden bar: red, a gold diamond, a notched tail. Origin = bar centre."""
	p = Piece(seed)
	r = p.rng
	w = 2.6
	bar = Vector((w / 2 + 0.4, 0.2, 0.2))
	p.hull([Vector((x * bar.x, y * bar.y, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (-0.2, 0.2)], lambda f: jitter(PAL["wood"], r))
	rows = []
	steps = 6
	for k in range(steps + 1):
		t = k / steps
		z = -0.2 - t * length
		wave = math.sin(t * 2.4 + 0.5) * 0.25 * t
		ring = [Vector((x, 0.25 + wave + (abs(x) / w) * 0.1, z)) for x in (-w / 2, 0, w / 2)]
		rows.append(ring)
	p.quad_strip(rows, lambda f: jitter(PAL["banner"], r, v=0.04))
	# notched tail
	last = rows[-1]
	notch = Vector((0, last[1].y, last[1].z + 0.9))
	p.tri(last[0], notch, last[0] + Vector((0, 0.05, -1.2)), jitter(PAL["banner"], r))
	p.tri(notch, last[2], last[2] + Vector((0, 0.05, -1.2)), jitter(PAL["banner"], r))
	# gold diamond, just proud of the cloth
	cz = -length * 0.35
	cy = 0.25 + math.sin(0.35 * 2.4 + 0.5) * 0.25 * 0.35 + 0.08
	d = 0.75
	gold = jitter(PAL["gold"], r)
	c = Vector((0, cy, cz))
	pts = [c + Vector((0, 0, d * 1.4)), c + Vector((d, 0, 0)), c + Vector((0, 0, -d * 1.4)), c + Vector((-d, 0, 0))]
	f = p.bm.faces.new([p.bm.verts.new(q) for q in reversed(pts)])
	p.paint([f], lambda _f: gold)
	return p.finish(name, coll)


def banner_pole(name, seed, height=10.0, coll=None):
	p = Piece(seed)
	r = p.rng
	s = 0.3
	p.hull([Vector((x * s, y * s, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (0, height)], lambda f: jitter(PAL["wood"], r))
	return p.finish(name, coll)


def arch(name, seed, span=10.0, pier_h=9.0, coll=None):
	"""two stone piers and a semicircle of wedge blocks, standing in the XZ plane (walk through along Y)"""
	p = Piece(seed)
	r = p.rng
	fn = stone_fn(p)
	depth = 2.4
	pier_w = 2.6
	for sx in (-1, 1):
		x = sx * (span / 2 + pier_w / 2)
		z = 0.0
		while z < pier_h - 0.1:
			h = min(1.8, pier_h - z)
			brick(p, Vector((x, 0, z + h / 2)), (pier_w * r.uniform(0.95, 1.0), depth, h * 0.96), fn)
			z += h
	radius_in = span / 2
	radius_out = span / 2 + pier_w
	n = 9
	for i in range(n):
		a0 = math.pi * i / n + 0.012
		a1 = math.pi * (i + 1) / n - 0.012
		pts = []
		for a in (a0, a1):
			for rad in (radius_in, radius_out * r.uniform(0.97, 1.0)):
				for y in (-depth / 2, depth / 2):
					pts.append(Vector((math.cos(a) * rad, y * r.uniform(0.92, 1.0), pier_h + math.sin(a) * rad)))
		p.hull(pts, fn)
	return p.finish(name, coll)


def stele(name, seed, coll=None):
	p = Piece(seed)
	r = p.rng
	w, d, h = 2.2, 0.8, 4.2
	pts = []
	for x in (-1, 1):
		for y in (-1, 1):
			pts.append(Vector((x * w / 2 * r.uniform(0.9, 1), y * d / 2, -0.4)))
			pts.append(Vector((x * w / 2 * r.uniform(0.85, 0.95), y * d / 2 * 0.9, h - r.uniform(0, 0.5))))
	pts.append(Vector((r.uniform(-0.3, 0.3), 0, h + 0.2)))
	p.hull(pts, stone_fn(p))
	return p.finish(name, coll)


def mountain(name, seed, radius=180.0, height=140.0, coll=None):
	p = Piece(seed)
	r = p.rng
	pts = []
	n = 11
	for i in range(n):
		a = i * math.tau / n + r.uniform(-0.2, 0.2)
		rr = radius * r.uniform(0.7, 1.1)
		pts.append(Vector((math.cos(a) * rr, math.sin(a) * rr, 0)))
		pts.append(Vector((math.cos(a) * rr * 0.5, math.sin(a) * rr * 0.5, height * r.uniform(0.45, 0.7))))
	pts.append(Vector((r.uniform(-20, 20), r.uniform(-20, 20), height)))

	def fn(f):
		c = mix(jitter(PAL["mountain"], r, v=0.08), Color((0.9, 0.93, 0.97)), 0.25 if f.normal.z > 0.6 and f.calc_center_median().z > height * 0.6 else 0)
		return c

	p.hull(pts, fn, dissolve=5)
	return p.finish(name, coll)


# ---------------------------------------------------------------- material / scene

_MAT = None


def kit_material():
	"""render-only material: the vertex colour, matte, faded toward the haze colour with distance"""
	global _MAT
	if _MAT:
		return _MAT
	m = bpy.data.materials.new("KitVertexColour")
	m.use_nodes = True
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
	bsdf.inputs["Roughness"].default_value = 0.85
	if "Specular IOR Level" in bsdf.inputs:
		bsdf.inputs["Specular IOR Level"].default_value = 0.15
	attr = nt.nodes.new("ShaderNodeVertexColor")
	attr.layer_name = "Col"
	cam = nt.nodes.new("ShaderNodeCameraData")
	rng = nt.nodes.new("ShaderNodeMapRange")
	rng.inputs["From Min"].default_value = 60
	rng.inputs["From Max"].default_value = 420
	rng.inputs["To Max"].default_value = 0.7
	mixn = nt.nodes.new("ShaderNodeMix")
	mixn.data_type = "RGBA"
	mixn.inputs["B"].default_value = (*srgb_to_linear(srgb("b4c8dc")), 1)
	nt.links.new(cam.outputs["View Distance"], rng.inputs["Value"])
	nt.links.new(rng.outputs["Result"], mixn.inputs["Factor"])
	nt.links.new(attr.outputs["Color"], mixn.inputs["A"])
	nt.links.new(mixn.outputs["Result"], bsdf.inputs["Base Color"])
	# haze also glows a little so far things go pale instead of dark in shade
	emit = nt.nodes.new("ShaderNodeMix")
	emit.data_type = "RGBA"
	emit.inputs["A"].default_value = (0, 0, 0, 1)
	emit.inputs["B"].default_value = (*srgb_to_linear(srgb("b4c8dc")), 1)
	nt.links.new(rng.outputs["Result"], emit.inputs["Factor"])
	nt.links.new(emit.outputs["Result"], bsdf.inputs["Emission Color"])
	bsdf.inputs["Emission Strength"].default_value = 0.9
	nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
	_MAT = m
	return m


def build_kit(coll):
	kit = {}
	for i in range(3):
		kit[f"Pine{i + 1}"] = pine(f"Pine{i + 1}", 10 + i, height=(20, 26, 16)[i], coll=coll)
	for i, size in enumerate(((7, 6, 5), (4, 3.5, 2.5), (10, 7, 4), (2.5, 2, 1.8))):
		kit[f"Boulder{i + 1}"] = boulder(f"Boulder{i + 1}", 20 + i, size=size, coll=coll)
	kit["GrassTuft1"] = grass_tuft("GrassTuft1", 30, blades=9, coll=coll)
	kit["GrassTuft2"] = grass_tuft("GrassTuft2", 31, blades=14, coll=coll)
	kit["FlowerClump"] = grass_tuft("FlowerClump", 32, blades=7, flowers=4, coll=coll)
	kit["Bush1"] = bush("Bush1", 40, coll=coll)
	kit["Bush2"] = bush("Bush2", 41, size=4.5, coll=coll)
	kit["Tower"] = tower("Tower", 50, coll=coll)
	kit["TowerRuined"] = tower("TowerRuined", 51, height=24, ruined=True, coll=coll)
	kit["Banner"] = banner("Banner", 60, coll=coll)
	kit["BannerPole"] = banner_pole("BannerPole", 61, coll=coll)
	kit["Arch"] = arch("Arch", 70, coll=coll)
	kit["Stele"] = stele("Stele", 80, coll=coll)
	kit["Mountain"] = mountain("Mountain", 90, coll=coll)
	return kit


def place(src, loc, yaw=0.0, scale=1.0, coll=None):
	o = bpy.data.objects.new(src.name + "_copy", src.data)
	o.location = loc
	o.rotation_euler = (0, 0, yaw)
	o.scale = (scale,) * 3
	coll.objects.link(o)
	return o


def ground(coll, road):
	"""a gently rolling floor; faces near the road polyline are dirt, the rest grass (render stand-in for Terrain)"""
	p = Piece(5)
	r = p.rng
	size, n = 600, 120
	step = size / n
	rows = []
	for j in range(n + 1):
		y = -size / 2 + j * step
		rows.append([Vector((-size / 2 + i * step, y, 0)) for i in range(n + 1)])
	for row in rows:
		for v in row:
			v.z = 0.6 * math.sin(v.x * 0.05) * math.cos(v.y * 0.04) + r.uniform(-0.15, 0.15)

	def road_dist(c):
		best = 1e9
		for a, b in zip(road, road[1:]):
			ab = b - a
			t = max(0, min(1, (c - a).dot(ab) / ab.length_squared))
			best = min(best, (a + ab * t - c).length)
		return best

	def fn(f):
		c = f.calc_center_median()
		d = road_dist(Vector((c.x, c.y, 0)))
		if d < 5 + r.uniform(-0.8, 0.8):
			return jitter(PAL["dirt"], r, v=0.04)
		g = mix(jitter(PAL["grass"], r, v=0.06), jitter(PAL["grass_dark"], r), 0.2 + 0.3 * (0.5 + 0.5 * math.sin(c.x * 0.03 + c.y * 0.05)))
		return g

	before = set(p.bm.faces)
	vs = [[p.bm.verts.new(v) for v in row] for row in rows]
	for a, b in zip(vs, vs[1:]):
		for i in range(n):
			p.bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
	p.paint([f for f in p.bm.faces if f not in before], fn)
	return p.finish("Ground", coll)


def figure(coll):
	"""a 5-stud hooded stand-in for scale (render only)"""
	p = Piece(7)
	r = p.rng
	cloak = lambda f: jitter("3a6288", r)
	p.hull([Vector((math.cos(a) * w, math.sin(a) * w * 0.7, z)) for a in (i * math.tau / 8 for i in range(8)) for z, w in ((0, 1.1), (3.4, 0.9))], cloak)
	p.hull([Vector((math.cos(a) * 0.65, math.sin(a) * 0.65, z)) for a in (i * math.tau / 8 for i in range(8)) for z in (3.4, 4.5)] + [Vector((0, 0, 5.0))], cloak)
	return p.finish("Hero", coll)


def scene(kit):
	sc = bpy.context.scene
	coll = bpy.data.collections.new("Scene")
	sc.collection.children.link(coll)
	rng = random.Random(3)
	# road: from the camera, gently bending, through the arch at y=70
	road = [Vector(v) for v in ((0, -40, 0), (2, 10, 0), (-1, 45, 0), (0, 70, 0), (6, 120, 0), (25, 200, 0))]
	ground(coll, road)
	place(kit["Arch"], (0, 70, 0), 0, 1.0, coll)
	for sx in (-1, 1):
		place(kit["Tower"], (sx * 15, 72, 0), rng.uniform(-0.1, 0.1), 1.0, coll)
		b = place(kit["Banner"], (sx * 15, 68.0, 24), 0, 1.0, coll)
		b.rotation_euler.z = math.pi
	place(kit["TowerRuined"], (-34, 92, 0), 0.4, 1.0, coll)
	for x, y in ((9, 48), (-8, 30)):
		place(kit["BannerPole"], (x, y, 0), 0, 1.0, coll)
		bn = place(kit["Banner"], (x, y - 0.5, 9.6), 0, 0.8, coll)
		bn.rotation_euler.z = math.pi
	place(kit["Stele"], (-7, 8, 0), 0.3, 1.0, coll)
	place(kit["Stele"], (-11, 14, 0), -0.2, 0.8, coll)
	# trees: dense on the left, a line on the right, thinning past the gate
	pines = [kit["Pine1"], kit["Pine2"], kit["Pine3"]]
	for _ in range(140):
		x = rng.uniform(-160, 160)
		y = rng.uniform(-20, 260)
		near_road = min((Vector((x, y, 0)) - v).length for v in road)
		if near_road < 14 or (abs(x) < 30 and 55 < y < 90):
			continue
		if x > 0 and rng.random() < 0.35:
			continue
		place(rng.choice(pines), (x, y, 0), rng.uniform(0, math.tau), rng.uniform(0.8, 1.3), coll)
	boulders = [kit[f"Boulder{i}"] for i in (1, 2, 3, 4)]
	for _ in range(40):
		x = rng.uniform(-60, 60)
		y = rng.uniform(-10, 140)
		if min((Vector((x, y, 0)) - v).length for v in road) < 7:
			continue
		place(rng.choice(boulders), (x, y, 0), rng.uniform(0, math.tau), rng.uniform(0.7, 1.4), coll)
	place(kit["Boulder3"], (-14, 4, 0), 0.5, 1.0, coll)
	tufts = [kit["GrassTuft1"], kit["GrassTuft2"], kit["FlowerClump"], kit["FlowerClump"]]
	for _ in range(900):
		x = rng.uniform(-45, 45)
		y = rng.uniform(-30, 110)
		if min((Vector((x, y, 0)) - v).length for v in road) < 5.5:
			continue
		place(rng.choice(tufts), (x, y, 0), rng.uniform(0, math.tau), rng.uniform(0.8, 1.4), coll)
	for _ in range(30):
		x = rng.uniform(-50, 50)
		y = rng.uniform(0, 120)
		if min((Vector((x, y, 0)) - v).length for v in road) < 8:
			continue
		place(rng.choice([kit["Bush1"], kit["Bush2"]]), (x, y, 0), rng.uniform(0, math.tau), rng.uniform(0.8, 1.2), coll)
	for i in range(9):
		a = math.radians(-70 + i * 18)
		d = rng.uniform(420, 560)
		place(kit["Mountain"], (math.sin(a) * d, math.cos(a) * d, -10), rng.uniform(0, math.tau), rng.uniform(0.8, 1.4), coll)
	hero = figure(coll)
	hero.location = (1, -4, 0)
	return coll


def lights_and_world():
	sc = bpy.context.scene
	world = bpy.data.worlds.new("Sky")
	sc.world = world
	world.use_nodes = True
	nt = world.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputWorld")
	bg = nt.nodes.new("ShaderNodeBackground")
	tc = nt.nodes.new("ShaderNodeTexCoord")
	sep = nt.nodes.new("ShaderNodeSeparateXYZ")
	ramp = nt.nodes.new("ShaderNodeValToRGB")
	ramp.color_ramp.elements[0].position = 0.0
	ramp.color_ramp.elements[0].color = (*srgb_to_linear(srgb("dfe7ee")), 1)
	ramp.color_ramp.elements[1].position = 0.45
	ramp.color_ramp.elements[1].color = (*srgb_to_linear(srgb("7fa7d6")), 1)
	nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
	nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
	nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
	bg.inputs["Strength"].default_value = 1.9
	nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = 3.6
	sun.color = (1.0, 0.93, 0.82)
	sun.angle = math.radians(3)
	so = bpy.data.objects.new("Sun", sun)
	so.rotation_euler = (math.radians(42), 0, math.radians(200))  # high, ahead and a little left: soft backlight
	sc.collection.objects.link(so)


def setup_render(path, w=1600, h=900):
	sc = bpy.context.scene
	for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
		try:
			sc.render.engine = eng
			break
		except TypeError:
			continue
	sc.render.resolution_x, sc.render.resolution_y = w, h
	sc.render.filepath = path
	sc.view_settings.view_transform = "Standard"
	sc.view_settings.look = "None"
	sc.view_settings.exposure = 0.15
	try:
		sc.eevee.taa_render_samples = 32
		sc.eevee.use_shadows = True
	except AttributeError:
		pass


def camera(loc, look, lens=24):
	cam = bpy.data.cameras.new("Cam")
	cam.lens = lens
	cam.clip_end = 3000
	o = bpy.data.objects.new("Cam", cam)
	bpy.context.scene.collection.objects.link(o)
	o.location = loc
	d = Vector(look) - Vector(loc)
	o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
	bpy.context.scene.camera = o
	return o


def lineup(kit):
	"""every prop in a row on a plain floor, for a quick look at each one"""
	coll = bpy.data.collections.new("Lineup")
	bpy.context.scene.collection.children.link(coll)
	order = ["Pine1", "Pine2", "Pine3", "Tower", "TowerRuined", "Arch", "BannerPole", "Banner", "Stele", "Boulder1", "Boulder2", "Boulder3", "Boulder4", "Bush1", "Bush2", "GrassTuft1", "GrassTuft2", "FlowerClump"]
	x = 0.0
	for name in order:
		o = kit[name]
		bb = [Vector(c) for c in o.bound_box]
		wid = max(v.x for v in bb) - min(v.x for v in bb)
		z = 10 if name == "Banner" else 0
		place(o, (x - min(v.x for v in bb), 1000, z), math.pi if name == "Banner" else 0, 1.0, coll)
		x += wid + 3
	return coll, x


def main():
	bpy.ops.wm.read_factory_settings(use_empty=True)
	kit_coll = bpy.data.collections.new("Kit")
	bpy.context.scene.collection.children.link(kit_coll)
	kit = build_kit(kit_coll)
	# kit masters sit far away, out of the shots
	for i, o in enumerate(kit.values()):
		o.location = (i * 40, -5000, 0)
	os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
	tri = {n: sum(len(p.vertices) - 2 for p in o.data.polygons) for n, o in kit.items()}
	print("[kit] triangles:", tri)

	if "--export" in ARGS:
		gdir = os.path.join(OUT, "glb")
		os.makedirs(gdir, exist_ok=True)
		for name, o in kit.items():
			if name == "Mountain":
				pass
			loc = o.location.copy()
			o.location = (0, 0, 0)
			bpy.ops.object.select_all(action="DESELECT")
			o.select_set(True)
			bpy.context.view_layer.objects.active = o
			bpy.ops.export_scene.gltf(filepath=os.path.join(gdir, f"{name}.glb"), export_format="GLB", use_selection=True,
									  export_materials="NONE", export_vertex_color="ACTIVE", export_normals=True, export_apply=True)
			o.location = loc
		print("[kit] exported", len(kit), "props to", gdir)

	if "--render" in ARGS:
		lights_and_world()
		scene(kit)
		setup_render(os.path.join(OUT, "renders", "scene.png"))
		camera((2, -16, 7.5), (0, 60, 7), lens=22)
		bpy.ops.render.render(write_still=True)
		coll, width = lineup(kit)
		haze = kit_material().node_tree.nodes["Map Range"]
		haze.inputs["From Min"].default_value, haze.inputs["From Max"].default_value = 1e5, 2e5
		floor = Piece(1)
		floor.hull([Vector((x, y, zz)) for x in (-20, width + 20) for y in (960, 1040) for zz in (-0.5, 0)], lambda f: jitter(PAL["grass"], floor.rng, v=0))
		floor.finish("LineupFloor", coll)
		cam = camera((width / 2, 1000 - 200, 60), (width / 2, 1000, 12))
		cam.data.type = "ORTHO"
		cam.data.ortho_scale = width + 10
		setup_render(os.path.join(OUT, "renders", "lineup.png"), 2400, 600)
		bpy.ops.render.render(write_still=True)

	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "StarterKit.blend"))


main()
