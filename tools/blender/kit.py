"""The environment kit, v2 (look-matching passes, docs/look-passes.md): props built in code, flat-shaded, coloured per face
(vertex colours, no textures). Units are studs, Z up, each prop's origin at its base centre.

Imported by tools/blender/look_match.py (the reference copy) and tools/blender/starter_kit.py (lineup, glb export).
PAL holds the albedo of each material as sRGB hex; a scene can override any entry (look_match's spec "Palette").
"""

import math
import random

import bmesh
import bpy
from mathutils import Color, Vector

PAL = {
	"pine": "3b6a5c",
	"pine_dark": "24443d",
	"bark": "4a382c",
	"rock": "9a9c96",
	"rock_dark": "7d817d",
	"moss": "71874f",
	"stone": "aaa598",
	"stone_dark": "8e897e",
	"banner": "8f2621",
	"banner_dark": "5e1916",
	"cream": "e2cfa0",
	"wood": "4b3628",
	"blade": "4e7436",
	"blade_tip": "86a24e",
	"flower_white": "f2f0e6",
	"flower_yellow": "e9c13c",
	"leaf": "4f7d3c",
	"mountain": "8796a6",
	"cloak": "2c5778",
	"cloak_trim": "d9b44a",
	"leather": "3e3229",
	"skin": "c99a76",
	"golem": "6f6a62",
	"golem_glow": "ffb53a",
}


# ---------------------------------------------------------------- colour


def srgb(c):
	if isinstance(c, Color):
		return c.copy()
	hex_ = PAL.get(c, c)
	col = Color()
	col.r, col.g, col.b = (int(hex_[i : i + 2], 16) / 255 for i in (0, 2, 4))
	return col


def to_linear(c):
	f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
	return f(c.r), f(c.g), f(c.b)


def jitter(c, rng, v=0.05, h=0.008, s=0.03):
	"""the colour with a small random shift in hue/saturation/value: each facet a slightly different tint"""
	c = srgb(c)
	c.h = (c.h + rng.uniform(-h, h)) % 1
	c.s = min(1, max(0, c.s + rng.uniform(-s, s)))
	c.v = min(1, max(0, c.v * (1 + rng.uniform(-v, v))))
	return c


def mix(a, b, t):
	a, b = srgb(a), srgb(b)
	return Color((a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t))


def scale_v(c, k):
	c = srgb(c)
	c.v = min(1, c.v * k)
	return c


# ---------------------------------------------------------------- building meshes


class Piece:
	"""a bmesh being built, with a face-corner colour layer; faces are coloured as they are added. Faces added with
	glow=True get material 1 (emissive in renders, a Neon part in Roblox)."""

	def __init__(self, seed):
		self.bm = bmesh.new()
		self.col = self.bm.loops.layers.color.new("Col")
		self.rng = random.Random(seed)
		self.glow = []

	def paint(self, faces, fn):
		for f in faces:
			f.normal_update()
			c = fn(f) if callable(fn) else fn
			lin = (*to_linear(srgb(c)), 1.0)
			for loop in f.loops:
				loop[self.col] = lin

	def hull(self, pts, fn, dissolve=0.0, glow=False):
		before = set(self.bm.faces)
		verts = [self.bm.verts.new(p) for p in pts]
		res = bmesh.ops.convex_hull(self.bm, input=verts)
		junk = set(res["geom_interior"]) | set(res["geom_unused"])
		bmesh.ops.delete(self.bm, geom=[v for v in junk if isinstance(v, bmesh.types.BMVert)], context="VERTS")
		new = [f for f in self.bm.faces if f not in before]
		if dissolve:
			bmesh.ops.dissolve_limit(self.bm, angle_limit=math.radians(dissolve), verts=list({v for f in new for v in f.verts}),
									 edges=list({e for f in new for e in f.edges}))
			new = [f for f in self.bm.faces if f not in before]
		self.paint(new, fn)
		if glow:
			self.glow += new
		return new

	def poly(self, pts, fn):
		f = self.bm.faces.new([self.bm.verts.new(p) for p in pts])
		self.paint([f], fn)
		return f

	def fan(self, apex, ring, fn, flip=False):
		"""triangles from apex to each edge of a closed ring (a cone without its base)"""
		a = self.bm.verts.new(apex)
		vs = [self.bm.verts.new(p) for p in ring]
		faces = []
		for i in range(len(vs)):
			j = (i + 1) % len(vs)
			faces.append(self.bm.faces.new((a, vs[j], vs[i]) if flip else (a, vs[i], vs[j])))
		self.paint(faces, fn)
		return faces

	def quad_strip(self, rows, fn, close=False):
		"""faces between consecutive rings of points (lists of Vectors of equal length)"""
		vs = [[self.bm.verts.new(q) for q in ring_] for ring_ in rows]
		n = len(rows[0])
		faces = []
		for a, b in zip(vs, vs[1:]):
			for i in range(n if close else n - 1):
				j = (i + 1) % n
				faces.append(self.bm.faces.new((a[i], a[j], b[j], b[i])))
		self.paint(faces, fn)
		return faces

	def block(self, centre, along, out, size, fn, chamfer=0.0):
		"""a box: size = (length along `along`, depth along `out`, height); the face toward +out is inset by `chamfer` on
		all four edges, so from the front each block reads as a bevelled stone"""
		up = Vector((0, 0, 1))
		l, d, h = size
		pts = []
		for sd in (-1, 1):
			inset = chamfer if sd > 0 else 0.0
			for sl in (-1, 1):
				for sh in (-1, 1):
					pts.append(centre + along * (sl * (l / 2 - inset)) + out * (sd * d / 2) + up * (sh * (h / 2 - inset)))
		return self.hull(pts, fn)

	def paint_loops(self, faces, fn):
		"""colour per face corner: fn(loop) -> colour (gradients across a face)"""
		for f in faces:
			for loop in f.loops:
				loop[self.col] = (*to_linear(srgb(fn(loop))), 1.0)

	def finish(self, name, collection, smooth=False, sharp=None):
		if smooth and sharp is not None:
			edges = [e for e in self.bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(sharp)]
			bmesh.ops.split_edges(self.bm, edges=edges)
		for f in self.bm.faces:
			f.smooth = smooth
		glow = set(self.glow)
		for f in self.bm.faces:
			f.material_index = 1 if f in glow else 0
		mesh = bpy.data.meshes.new(name)
		self.bm.to_mesh(mesh)
		self.bm.free()
		obj = bpy.data.objects.new(name, mesh)
		if collection:
			collection.objects.link(obj)
		obj.data.materials.append(vertex_material())
		obj.data.materials.append(glow_material())
		return obj


def ring(z, radius, n, off=0.0, squash=1.0):
	return [Vector((math.cos(off + i * math.tau / n) * radius, math.sin(off + i * math.tau / n) * radius * squash, z)) for i in range(n)]


_MATS = {}


def vertex_material():
	"""the vertex colour as a matte surface (renders only; Roblox shows the vertex colours on SmoothPlastic)"""
	if "v" in _MATS:
		return _MATS["v"]
	m = bpy.data.materials.new("KitVertexColour")
	m.use_nodes = True
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
	bsdf.inputs["Roughness"].default_value = 0.9
	if "Specular IOR Level" in bsdf.inputs:
		bsdf.inputs["Specular IOR Level"].default_value = 0.1
	attr = nt.nodes.new("ShaderNodeVertexColor")
	attr.layer_name = "Col"
	nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
	nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
	_MATS["v"] = m
	return m


def glow_material():
	if "g" in _MATS:
		return _MATS["g"]
	m = bpy.data.materials.new("KitGlow")
	m.use_nodes = True
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	em = nt.nodes.new("ShaderNodeEmission")
	attr = nt.nodes.new("ShaderNodeVertexColor")
	attr.layer_name = "Col"
	nt.links.new(attr.outputs["Color"], em.inputs["Color"])
	em.inputs["Strength"].default_value = 3.0
	nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
	_MATS["g"] = m
	return m


# ---------------------------------------------------------------- nature


def pine(name, seed, height=30.0, coll=None, slender=1.0, tiers=None, spikes=11):
	"""a tall pine of stacked drooping skirts. Each tier's rim alternates ragged drooping spikes and short notches, and
	its underside is a dark inverted cone, so every tier edge reads as a jagged dark line (the reference's sawtooth tiers).
	Smooth-shaded, a soft gradient from a darker rim to a lighter top on each tier."""
	p = Piece(seed)
	r = p.rng
	tw = height * 0.022
	p.hull(ring(0, tw * 1.3, 6, 0.3) + ring(height * 0.45, tw * 0.6, 6, 0.3), lambda f: jitter("bark", r))
	n = tiers or r.randint(8, 10)
	crown_base = height * r.uniform(0.08, 0.12)
	span = height - crown_base
	lean = Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * height * 0.006  # a slight lean up the trunk
	for k in range(n):
		t = k / (n - 1)
		z0 = crown_base + span * ((k + r.uniform(-0.15, 0.15) * (k > 0)) / n) * 0.9
		radius = height * 0.185 * slender * (1 - 0.84 * t) * r.uniform(0.88, 1.1)
		tier_h = min(height - z0, span / n * 2.4)
		off_c = lean * k + Vector((r.uniform(-0.03, 0.03) * radius, r.uniform(-0.03, 0.03) * radius, 0))
		apex = off_c + Vector((r.uniform(-0.04, 0.04) * radius, r.uniform(-0.04, 0.04) * radius, z0 + tier_h))
		off = r.uniform(0, math.tau)
		rim = []
		for i in range(spikes):
			a = off + i * math.tau / spikes + r.uniform(-0.14, 0.14)
			rr = radius * r.uniform(0.84, 1.14)
			droop = tier_h * r.uniform(0.1, 0.28)
			rim.append(off_c + Vector((math.cos(a) * rr, math.sin(a) * rr, z0 - droop)))
			a2 = a + math.tau / spikes / 2
			rn = radius * r.uniform(0.6, 0.72)
			rim.append(off_c + Vector((math.cos(a2) * rn, math.sin(a2) * rn, z0 + tier_h * r.uniform(0.08, 0.16))))
		shade = 0.84 + 0.16 * t  # lower tiers a little darker: painted occlusion
		base = jitter("pine", r, v=0.04, h=0.005, s=0.02)
		tip = scale_v(base, 1.18)
		faces = p.fan(apex, rim, base)
		p.paint_loops(faces, lambda lp, z0=z0, th=tier_h, base=base, tip=tip, sh=shade: scale_v(mix(base, tip, max(0.0, min(1.0, (lp.vert.co.z - z0) / th))), sh))
		under = off_c + Vector((0, 0, z0 + tier_h * 0.22))
		p.fan(under, rim, lambda f: jitter("pine_dark", r, v=0.03), flip=True)
	return p.finish(name, coll, smooth=True)


def boulder(name, seed, size=(6, 5, 4), coll=None, mossy=0.0, sink=0.3):
	"""a rounded boulder of a few big flat facets"""
	p = Piece(seed)
	r = p.rng
	pts = []
	for _ in range(34):
		v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
		v.x *= size[0] / 2 * r.uniform(0.85, 1.05)
		v.y *= size[1] / 2 * r.uniform(0.85, 1.05)
		v.z *= size[2] / 2 * r.uniform(0.85, 1.05)
		pts.append(v)
	z_off = size[2] * (0.5 - sink)  # the bottom `sink` of the rock is buried

	def fn(f):
		c = mix(jitter("rock_dark", r, v=0.025), jitter("rock", r, v=0.025), 0.5 + 0.5 * f.normal.z)
		if mossy and f.normal.z > 0.6 and r.random() < mossy:
			c = mix(c, jitter("moss", r), 0.7)
		return c

	p.hull([q + Vector((0, 0, z_off)) for q in pts], fn, dissolve=4)
	return p.finish(name, coll, smooth=True, sharp=38)


def grass_clump(name, seed, blades=12, height=1.6, spread=0.6, coll=None):
	"""thin tall blades fanning out of one spot, dark at the base, lighter at the tips (each blade one triangle; render
	two-sided, Roblox DoubleSided)"""
	p = Piece(seed)
	r = p.rng
	for _ in range(blades):
		a = r.uniform(0, math.tau)
		d = r.uniform(0, spread * 0.4)
		base = Vector((math.cos(a) * d, math.sin(a) * d, -0.1))
		h = height * r.uniform(0.5, 1.15)
		lean = r.uniform(0.12, 0.55)
		tip = base + Vector((math.cos(a) * h * lean, math.sin(a) * h * lean, h))
		w = r.uniform(0.022, 0.04) * height / 1.6
		side = Vector((-math.sin(a + 1.3), math.cos(a + 1.3), 0)) * w
		mid = base + (tip - base) * 0.45 + Vector((math.cos(a), math.sin(a), 0)) * h * lean * 0.08
		c0 = jitter("blade", r, v=0.08)
		c1 = mix(c0, jitter("blade_tip", r, v=0.06), r.uniform(0.4, 0.9))
		p.poly([base - side, base + side, mid + side * 0.6, mid - side * 0.6], c0)
		p.poly([mid - side * 0.6, mid + side * 0.6, tip], c1)
	return p.finish(name, coll)


def flowers(name, seed, kind="white", count=6, coll=None):
	"""a small patch of flowers: white = tiny four-petal heads in a cluster, yellow = five-petal daisies on stems"""
	p = Piece(seed)
	r = p.rng
	for _ in range(count):
		a = r.uniform(0, math.tau)
		d = r.uniform(0, 0.45 if kind == "white" else 0.7)
		c = Vector((math.cos(a) * d, math.sin(a) * d, r.uniform(0.3, 0.6) if kind == "white" else r.uniform(0.6, 1.0)))
		stem_w = 0.03
		p.poly([Vector((c.x - stem_w, c.y, -0.05)), Vector((c.x + stem_w, c.y, -0.05)), c + Vector((0, 0, -0.02))], jitter("blade", r))
		n, rad = (5, 0.09) if kind == "white" else (5, 0.2)
		col = jitter("flower_white" if kind == "white" else "flower_yellow", r, v=0.05)
		tilt = Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 1)).normalized()
		pts = []
		for i in range(n * 2):
			ang = i * math.pi / n
			rr = rad if i % 2 == 0 else rad * 0.35
			v = Vector((math.cos(ang) * rr, math.sin(ang) * rr, 0))
			v = v - tilt * v.dot(tilt)
			pts.append(c + v)
		p.poly(pts, col)
		if kind == "yellow":
			p.poly([q + Vector((0, 0, 0.015)) for q in pts[::2]], mix(col, "a8761c", 0.5))
	return p.finish(name, coll)


def bush(name, seed, size=3.0, coll=None):
	p = Piece(seed)
	r = p.rng
	for _ in range(r.randint(3, 5)):
		c = Vector((r.uniform(-1, 1) * size * 0.35, r.uniform(-1, 1) * size * 0.35, size * r.uniform(0.25, 0.45)))
		rad = size * r.uniform(0.3, 0.45)
		pts = [c + Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1) * 0.8)).normalized() * rad * r.uniform(0.85, 1.05) for _ in range(14)]
		p.hull(pts, lambda f: mix(jitter("pine_dark", r, v=0.03), jitter("leaf", r, v=0.03), 0.3 + 0.7 * max(0, f.normal.z)), dissolve=4)
	return p.finish(name, coll, smooth=True, sharp=50)


def mountain(name, seed, width=900.0, height=320.0, depth=420.0, coll=None, peaks=2):
	"""a faceted mountain mass: a coarse heightfield with a few peaks and ridges falling away from them"""
	p = Piece(seed)
	r = p.rng
	nx, ny = 14, 8
	tops = [(r.uniform(-0.3, 0.3), r.uniform(-0.15, 0.15), r.uniform(0.75, 1.0)) for _ in range(peaks)]
	grid = []
	for j in range(ny + 1):
		row = []
		for i in range(nx + 1):
			u, v = i / nx - 0.5, j / ny - 0.5
			z = 0.0
			for (px, py, ph) in tops:
				d = math.hypot((u - px) * 1.6, (v - py) * 1.2)
				z = max(z, ph * max(0.0, 1 - d * 1.9) ** 1.3)
			edge = min(i, nx - i, j, ny - j)
			z = z * (1 if edge > 0 else 0) * height + r.uniform(-0.04, 0.04) * height * (edge > 0)
			row.append(Vector((u * width + r.uniform(-0.3, 0.3) * width / nx, v * depth, max(-20.0, z))))
		grid.append(row)
	for j in range(ny):
		for i in range(nx):
			a, b, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
			col = jitter("mountain", r, v=0.04)
			if (i + j) % 2:
				p.poly([a, b, c], col)
				p.poly([a, c, d], jitter("mountain", r, v=0.04))
			else:
				p.poly([a, b, d], col)
				p.poly([b, c, d], jitter("mountain", r, v=0.04))
	return p.finish(name, coll)


# ---------------------------------------------------------------- stonework


def stone_fn(r, base="stone", dark="stone_dark", spread=0.1):
	"""per block: a tone between dark and light stone, chosen once per block (so blocks read as separate stones)"""

	def make():
		t = r.uniform(0, 1)
		c = jitter(mix(dark, base, t), r, v=spread * 0.4)
		return lambda f: c

	return make


def tower(name, seed, height=48.0, width=14.0, coll=None, ruined=False, courses=None):
	"""a square stone tower: big blocks laid in courses with interlocking corners, a corbelled band near the top that
	steps out, and a parapet of chunky merlons (or a broken top when ruined). Front = -Y."""
	p = Piece(seed)
	r = p.rng
	tone = stone_fn(r)
	cap_h = height * 0.17 if not ruined else 0
	shaft_h = height - cap_h
	n = courses or max(6, round(shaft_h / (width * 0.27)))
	course = shaft_h / n
	depth = width * 0.12
	z = 0.0
	sides = [(Vector((1, 0, 0)), Vector((0, -1, 0))), (Vector((0, 1, 0)), Vector((1, 0, 0))),
			 (Vector((-1, 0, 0)), Vector((0, 1, 0))), (Vector((0, -1, 0)), Vector((-1, 0, 0)))]
	top_left = []
	for c in range(n):
		w = width * (1.06 if c == 0 else 1.0)
		for s, (along, out) in enumerate(sides):
			length = w if (s + c) % 2 == 0 else w - 2 * depth
			k = 3 if c % 2 == 0 else 2
			cuts = [-length / 2] + sorted(-length / 2 + length * (i + r.uniform(-0.12, 0.12)) / k for i in range(1, k)) + [length / 2]
			for a, b in zip(cuts, cuts[1:]):
				if ruined and c > n * 0.62:
					keep = 1 - (c - n * 0.62) / (n * 0.38)
					if r.random() > keep * (0.7 + 0.6 * (a + length / 2) / length):
						continue
				centre = along * ((a + b) / 2) + out * (w / 2 - depth / 2) + Vector((0, 0, z + course / 2))
				p.block(centre, along, out, ((b - a) - 0.08, depth, course - 0.08), tone(), chamfer=min(course, b - a) * 0.04)
		z += course
	core = width - 2 * depth + 0.2
	core_top = z if not ruined else z - course * n * 0.25
	p.hull([Vector((x * core / 2, y * core / 2, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (0, core_top)], "706c64")
	if ruined:
		return p.finish(name, coll)
	# corbel band: a row of small corbels, then a projecting course
	out_w = width * 1.16
	cor_h = cap_h * 0.18
	for s, (along, out) in enumerate(sides):
		for i in range(5):
			x = -width / 2 + width * (i + 0.5) / 5
			centre = along * x + out * (width / 2 + (out_w - width) / 4) + Vector((0, 0, z + cor_h / 2))
			p.block(centre, along, out, (width / 5 * 0.55, (out_w - width) / 2, cor_h), tone(), chamfer=0.1)
	z += cor_h
	band_h = cap_h * 0.3
	p.hull([Vector((x * out_w / 2, y * out_w / 2, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (z, z + band_h)], tone())
	z += band_h
	mer_h = cap_h - cor_h - band_h
	for s, (along, out) in enumerate(sides):
		for i in range(3):
			x = -out_w / 2 + out_w * (i * 2 + 0.5) / 5.5 + out_w * 0.04
			mw = out_w / 5.5 * (1.3 if i in (0, 2) else 1.0)
			centre = along * (x + mw / 2 - out_w * 0.02) + out * (out_w / 2 - depth * 0.6) + Vector((0, 0, z + mer_h / 2))
			p.block(centre, along, out, (mw, depth * 1.2, mer_h), tone(), chamfer=0.12)
	return p.finish(name, coll)


def arch(name, seed, span=20.0, thick=3.2, depth=6.0, pier_h=6.0, coll=None, stones=13, piers=True):
	"""a round arch spanning X (from -span/2 to +span/2), piers of stacked blocks up to pier_h, then a ring of wedge
	stones. Walk through along Y. piers=False when the arch springs from walls or towers on either side (the ring's
	feet then reach down to z=0 as plain wall so no gap shows)."""
	p = Piece(seed)
	r = p.rng
	tone = stone_fn(r)
	pier_w = thick * 1.1
	if not piers:
		for sx in (-1, 1):
			x = sx * (span / 2 + thick / 2)
			p.hull([Vector((x + dx, y, z)) for dx in (-thick / 2, thick / 2) for y in (-depth / 2, depth / 2) for z in (0, pier_h + 0.2)], tone())
	for sx in (-1, 1) if piers else ():
		x = sx * (span / 2 + pier_w / 2)
		z = 0.0
		while z < pier_h - 0.05:
			h = min(pier_h * 0.34, pier_h - z)
			p.block(Vector((x, 0, z + h / 2)), Vector((1, 0, 0)), Vector((0, -1, 0)), (pier_w, depth, h - 0.1), tone(), chamfer=0.15)
			z += h
	rad_in = span / 2
	rad_out = rad_in + thick
	for i in range(stones):
		a0 = math.pi * i / stones + 0.006
		a1 = math.pi * (i + 1) / stones - 0.006
		pts = []
		for a in (a0, a1):
			for rad in (rad_in, rad_out * r.uniform(0.98, 1.02)):
				for y in (-depth / 2, depth / 2):
					pts.append(Vector((math.cos(a) * rad, y, pier_h + math.sin(a) * rad)))
		p.hull(pts, tone())
	return p.finish(name, coll)


def ruin_arches(name, seed, bays=3, bay=12.0, height=14.0, thick=2.4, coll=None):
	"""a broken arcade wall (an old aqueduct): bays of round arches on square piers along X; the top course is ragged and
	the last bay is broken off"""
	p = Piece(seed)
	r = p.rng
	tone = stone_fn(r)
	pier = bay * 0.24
	open_w = bay - pier
	spring = height * 0.42
	length = bays * bay + pier
	for b in range(bays + 1):
		x = -length / 2 + pier / 2 + b * bay
		z = 0
		top = height if b < bays else height * r.uniform(0.45, 0.6)
		while z < spring + (0 if b < bays else 0) - 0.05:
			h = min(spring / 3, spring - z)
			p.block(Vector((x, 0, z + h / 2)), Vector((1, 0, 0)), Vector((0, -1, 0)), (pier - 0.1, thick, h - 0.08), tone(), chamfer=0.12)
			z += h
		if b == bays:
			p.block(Vector((x, 0, spring + (top - spring) / 2)), Vector((1, 0, 0)), Vector((0, -1, 0)), (pier - 0.1, thick, top - spring - 0.08), tone(), chamfer=0.12)
	for b in range(bays):
		cx = -length / 2 + pier + open_w / 2 + b * bay
		rad = open_w / 2
		n = 7
		for i in range(n):
			if b == bays - 1 and i >= n - 2:
				continue
			a0, a1 = math.pi * i / n + 0.01, math.pi * (i + 1) / n - 0.01
			pts = []
			for a in (a0, a1):
				for rr in (rad, rad + thick * 0.9):
					for y in (-thick / 2, thick / 2):
						pts.append(Vector((cx + math.cos(a) * rr, y, spring + math.sin(a) * rr)))
			p.hull(pts, tone())
		# spandrel wall above the arch up to a ragged top
		top = height - r.uniform(0, height * 0.18)
		if b == bays - 1:
			top = spring + rad * 0.9
		for side in (-1, 1):
			x0 = cx + side * (rad + thick * 0.5)
			pts = []
			for xx in (x0 - thick * 0.45 * side, cx + side * (bay / 2 + 0.01)):
				for y in (-thick / 2, thick / 2):
					pts.append(Vector((xx, y, spring + rad * 0.55)))
					pts.append(Vector((xx, y, top)))
			p.hull(pts, tone())
		if b < bays - 1:
			p.hull([Vector((cx + dx, y, zz)) for dx in (-rad * 0.6, rad * 0.6) for y in (-thick / 2, thick / 2) for zz in (spring + rad + thick * 0.85, top)], tone())
	return p.finish(name, coll)


def stele(name, seed, coll=None, w=1.7, d=0.8, h=3.4):
	"""a pale standing slab on a low plinth, edges slightly bevelled"""
	p = Piece(seed)
	r = p.rng
	pale = lambda f: jitter("c6c6c0", r, v=0.03)
	p.block(Vector((0, 0, 0.25)), Vector((1, 0, 0)), Vector((0, -1, 0)), (w * 1.5, d * 1.9, 0.6), pale, chamfer=0.12)
	p.block(Vector((0, 0, 0.55 + h / 2)), Vector((1, 0, 0)), Vector((0, -1, 0)), (w, d, h), pale, chamfer=0.1)
	p.block(Vector((0, 0, 0.55 + h - 0.05)), Vector((1, 0, 0)), Vector((0, -1, 0)), (w * 1.08, d * 1.15, 0.3), pale, chamfer=0.08)
	return p.finish(name, coll)


# ---------------------------------------------------------------- banners


def banner(name, seed, width=4.0, length=9.0, coll=None, wave=0.25):
	"""a hanging banner: dark red edging, red field, a cream diamond, two small cream marks near the top and a pointed
	(chevron) bottom. Hangs from z=0 down; the front faces -Y."""
	p = Piece(seed)
	r = p.rng
	red, dark, cream = jitter("banner", r, v=0.03), jitter("banner_dark", r, v=0.03), jitter("cream", r, v=0.03)
	tip = length * 0.22
	rows = 7

	def y_at(z):
		t = -z / length
		return -math.sin(t * 2.2 + 0.6) * wave * t

	def pt(x, z, dy=0.0):
		return Vector((x, y_at(z) - dy, z))

	edge = width * 0.1
	body = length - tip
	for k in range(rows):
		z0, z1 = -body * k / rows, -body * (k + 1) / rows
		p.poly([pt(-width / 2, z0), pt(-width / 2, z1), pt(-width / 2 + edge, z1), pt(-width / 2 + edge, z0)], dark)
		p.poly([pt(width / 2 - edge, z0), pt(width / 2 - edge, z1), pt(width / 2, z1), pt(width / 2, z0)], dark)
		p.poly([pt(-width / 2 + edge, z0), pt(-width / 2 + edge, z1), pt(width / 2 - edge, z1), pt(width / 2 - edge, z0)], red)
	zb = -body
	p.poly([pt(-width / 2, zb), pt(0, -length), pt(width / 2, zb)], dark)
	p.poly([pt(-width / 2 + edge * 1.5, zb), pt(0, -length + edge * 1.8), pt(width / 2 - edge * 1.5, zb)], red)
	# diamond and marks, just proud of the cloth
	cz = -length * 0.48
	dw, dh = width * 0.25, width * 0.36
	p.poly([pt(0, cz + dh, 0.03), pt(-dw, cz, 0.03), pt(0, cz - dh, 0.03), pt(dw, cz, 0.03)], cream)
	for sx in (-1, 1):
		mz = -length * 0.16
		mx = sx * width * 0.26
		p.poly([pt(mx - 0.18, mz + 0.22, 0.03), pt(mx - 0.18, mz - 0.22, 0.03), pt(mx + 0.18, mz - 0.22, 0.03), pt(mx + 0.18, mz + 0.22, 0.03)], cream)
	# top rod
	p.hull([Vector((x * (width / 2 + 0.3), y * 0.18, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (-0.15, 0.25)], jitter("wood", r))
	return p.finish(name, coll)


def banner_pole(name, seed, height=12.0, arm=4.6, side=1, coll=None):
	"""an L-shaped pole: an upright and a crossbar sticking out to one side (+X when side=1) at the top; origin at the
	foot. The banner hangs from the arm's middle (attach point printed by the scene)."""
	p = Piece(seed)
	r = p.rng
	s = 0.22
	wood = lambda f: jitter("wood", r, v=0.06)
	p.hull([Vector((x * s, y * s, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (0, height + 0.3)], wood)
	p.hull([Vector((x, y * s * 0.8, zz)) for x in (0, side * arm) for y in (-1, 1) for zz in (height - 0.35, height)], wood)
	p.hull([Vector((x * s * 2, y * s * 2, zz)) for x in (-1, 1) for y in (-1, 1) for zz in (0, 0.4)], jitter("stone_dark", r))
	return p.finish(name, coll)


# ---------------------------------------------------------------- characters (stand-ins for the renders)


def hero(name, seed, coll=None):
	"""a 5.2-stud hooded figure seen from behind (the reference's silhouette, about 2.3 studs across the shoulders): dark
	legs and boots, a blue cloak with a gold emblem, steel pauldrons, hood"""
	p = Piece(seed)
	r = p.rng
	leather = lambda f: jitter("leather", r, v=0.05)
	for sx in (-1, 1):
		p.hull([Vector((sx * 0.3 + x, y, z)) for x in (-0.22, 0.22) for y in (-0.25, 0.25) for z in (0, 2.2)], leather)
	p.hull([Vector((x, y, z)) for x in (-0.7, 0.7) for y in (-0.4, 0.4) for z in (2.1, 3.9)], leather)
	cloak = lambda f: jitter("cloak", r, v=0.04)
	back = [Vector((x, 0.45 + abs(x) * 0.1, z)) for z, xs in ((4.0, (-0.8, 0.8)), (1.1, (-0.95, 0.95))) for x in xs]
	p.hull(back + [Vector((x, 0.3, z)) for x in (-0.8, 0.8) for z in (1.1, 4.0)], cloak)
	p.poly([Vector((0, 0.66, 3.45)), Vector((-0.3, 0.66, 3.0)), Vector((0, 0.66, 2.7)), Vector((0.3, 0.66, 3.0))], "d9b44a")
	for sx in (-1, 1):
		p.hull([Vector((sx * 0.88 + x, y, z)) for x in (-0.28, 0.28) for y in (-0.3, 0.3) for z in (3.5, 4.0)], lambda f: jitter("8c95a0", r))
		p.hull([Vector((sx * 0.98 + x, y, z)) for x in (-0.18, 0.18) for y in (-0.2, 0.2) for z in (2.1, 3.6)], leather)
	p.hull(ring(4.0, 0.5, 8) + ring(4.95, 0.47, 8) + [Vector((0, 0.12, 5.2))], cloak)
	return p.finish(name, coll)


def golem(name, seed, height=5.5, coll=None, glow=True):
	"""a stone golem of stacked faceted rocks with glowing seams on the chest"""
	p = Piece(seed)
	r = p.rng
	k = height / 5.5
	stone = lambda f: mix(jitter("golem", r, v=0.05), scale_v("golem", 1.25), max(0, f.normal.z) * 0.5)

	def rock(c, s, n=14):
		pts = []
		for _ in range(n):
			v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
			pts.append(c + Vector((v.x * s[0], v.y * s[1], v.z * s[2])))
		return p.hull(pts, stone, dissolve=6)

	for sx in (-1, 1):
		rock(Vector((sx * 0.7 * k, 0, 0.8 * k)), (0.55 * k, 0.55 * k, 0.9 * k))
	rock(Vector((0, 0, 2.9 * k)), (1.5 * k, 1.1 * k, 1.3 * k), 18)
	rock(Vector((0, -0.1 * k, 4.6 * k)), (0.6 * k, 0.55 * k, 0.55 * k))
	for sx in (-1, 1):
		rock(Vector((sx * 1.9 * k, 0, 3.3 * k)), (0.7 * k, 0.65 * k, 0.6 * k))
		rock(Vector((sx * 2.1 * k, -0.1 * k, 1.9 * k)), (0.6 * k, 0.6 * k, 0.9 * k))
	if glow:
		g = jitter("golem_glow", r, v=0.02)
		for c, s in ((Vector((0, -1.12 * k, 3.1 * k)), 0.35 * k), (Vector((0.4 * k, -1.05 * k, 2.6 * k)), 0.18 * k), (Vector((-0.1 * k, -0.6 * k, 4.55 * k)), 0.12 * k)):
			p.hull([c + Vector((r.uniform(-1, 1) * s, r.uniform(-0.3, 0.3) * s, r.uniform(-1, 1) * s)) for _ in range(8)], g, glow=True)
	return p.finish(name, coll)
