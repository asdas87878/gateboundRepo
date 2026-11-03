"""The Verdant Vale kit (docs/lands/land1-verdant-vale.md, docs/style/botw-study.md): low-poly pieces for the beauty
pass, built in code on kit.Piece. Smooth-shaded where forms are soft (canopies, grass, rocks), flat where they are cut
(stone, timber, roofs). Colour lives in vertex colours: soft gradients (dark, cool undersides to light, warm tops) do the
work a painted texture would, at no texture cost.

Every piece: origin at its base centre, studs, Z up, front = -Y.
"""

import math
import random

import bmesh
from mathutils import Matrix, Vector

import kit
from kit import Piece, jitter, mix, scale_v, srgb

VPAL = {
	"leaf_dark": "2f5a3a",
	"leaf_mid": "4f8a3f",
	"leaf_light": "a8c95a",
	"leaf_autumn_dark": "8a3a1c",
	"leaf_autumn_light": "f0b04a",
	"bark": "5a4636",
	"plaster": "efe7d6",
	"timber": "5b4130",
	"slate": "4d6584",
	"tile": "b0573a",
	"stone_light": "d8d3c6",
	"stone_mid": "b9b3a5",
	"window": "2c3542",
	"moss": "7aa83f",
	"cloth_red": "b8402e",
	"cloth_cream": "eadcb8",
	"cloth_blue": "3d6aa8",
	"rune": "6fe6ff",
	"snow": "f4f7fa",
	"rock_cool": "8e959b",
	"grass_base": "3d6a2c",
	"grass_tip": "c4d870",
	"water_fall": "eaf6ff",
}
kit.PAL.update(VPAL)


def vgrad(p, faces, lo, hi, z0, z1, noise=0.0, seed=0, up_bias=0.35):
	"""colour each corner by its height between z0 and z1 (lo at the bottom, hi at the top), lifted a little on
	up-facing parts, with a soft mottle: a painted canopy gradient without a texture"""
	r = random.Random(seed)
	ph = [r.uniform(0, 6.28) for _ in range(3)]

	p.bm.normal_update()

	def fn(lp):
		co, n = lp.vert.co, lp.vert.normal
		t = (co.z - z0) / max(1e-4, z1 - z0)
		t = max(0.0, min(1.0, t * (1 - up_bias) + max(0.0, n.z) * up_bias))
		m = math.sin(co.x * 0.9 + ph[0]) * math.sin(co.y * 0.8 + ph[1]) * math.sin(co.z * 0.7 + ph[2])
		return scale_v(mix(lo, hi, t), 1 + m * noise)

	p.paint_loops(faces, fn)


def blob(p, centre, radius, squash=(1.0, 1.0, 0.85), subdiv=1, lump=0.16, seed=0):
	"""a lumpy smooth ball: an icosphere pushed in and out a little"""
	r = random.Random(seed)
	before = set(p.bm.faces)
	res = bmesh.ops.create_icosphere(p.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4), calc_uvs=False)
	ph = [r.uniform(0, 6.28) for _ in range(4)]
	for v in res["verts"]:
		d = v.co.normalized()
		k = 1 + lump * (math.sin(d.x * 3.1 + ph[0]) * math.sin(d.y * 2.7 + ph[1]) + 0.6 * math.sin(d.z * 4.3 + ph[2]) * math.cos(d.x * 2.2 + ph[3]))
		v.co = centre + Vector((d.x * squash[0], d.y * squash[1], d.z * squash[2])) * radius * k
	return [f for f in p.bm.faces if f not in before]


def tube(p, pts, radii, colour, sides=6):
	rings = []
	for i, (c, rad) in enumerate(zip(pts, radii)):
		d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
		a = d.orthogonal().normalized()
		b = d.cross(a)
		rings.append([p.bm.verts.new(c + (a * math.cos(t) + b * math.sin(t)) * rad) for t in (k * math.tau / sides for k in range(sides))])
	faces = []
	for ra, rb in zip(rings, rings[1:]):
		for k in range(sides):
			faces.append(p.bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k])))
	p.paint(faces, lambda f: jitter(colour, p.rng, v=0.05))
	return faces


# ---------------------------------------------------------------- trees and plants


def broadleaf(name, seed, height=16.0, coll=None, kind="oak", autumn=False):
	"""a BotW-style broadleaf: a trunk forking into limbs under a canopy of a few lumpy smooth masses. kind: oak (wide,
	5-7 masses), poplar (tall and narrow), round (one big soft ball and a few small ones)"""
	p = Piece(seed)
	r = p.rng
	H = height
	crown_z = H * (0.62 if kind != "poplar" else 0.6)
	tr = H * (0.045 if kind != "poplar" else 0.035)
	fork = H * r.uniform(0.32, 0.4)
	tube(p, [Vector((0, 0, -0.5)), Vector((r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2), fork * 0.6)), Vector((0, 0, fork))], [tr * 1.35, tr, tr * 0.85], "bark")
	masses = []
	if kind == "oak":
		n = r.randint(5, 7)
		R = H * 0.3
		for i in range(n):
			a = i * math.tau / n + r.uniform(-0.3, 0.3)
			d = R * r.uniform(0.35, 0.65)
			masses.append((Vector((math.cos(a) * d, math.sin(a) * d, crown_z + r.uniform(-0.12, 0.1) * H)), R * r.uniform(0.5, 0.68)))
		masses.append((Vector((0, 0, crown_z + H * 0.17)), R * 0.62))
	elif kind == "poplar":
		for i in range(3):
			masses.append((Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), H * (0.42 + 0.19 * i))), H * (0.2 - 0.03 * i)))
	else:
		masses.append((Vector((0, 0, crown_z)), H * 0.34))
		for i in range(3):
			a = r.uniform(0, math.tau)
			masses.append((Vector((math.cos(a) * H * 0.22, math.sin(a) * H * 0.22, crown_z - H * 0.08)), H * 0.18))
	for c, rad in masses:  # limbs reaching each mass
		if (c - Vector((0, 0, fork))).length > rad * 0.6:
			tube(p, [Vector((0, 0, fork - 0.2)), (Vector((0, 0, fork)) + c) / 2 + Vector((0, 0, rad * 0.15)), c], [tr * 0.6, tr * 0.45, tr * 0.25], "bark", 5)
	dark, light = ("leaf_autumn_dark", "leaf_autumn_light") if autumn else ("leaf_dark", "leaf_light")
	zlo = min(c.z - rad for c, rad in masses)
	zhi = max(c.z + rad for c, rad in masses)
	for k, (c, rad) in enumerate(masses):
		sq = (1.0, 1.0, 0.85 if kind != "poplar" else 1.35)
		faces = blob(p, c, rad, sq, subdiv=1, lump=0.18, seed=seed * 31 + k)
		lo = jitter(dark, r, v=0.05, h=0.01)
		hi = jitter(light, r, v=0.05, h=0.012)
		vgrad(p, faces, lo, hi, zlo, zhi, noise=0.06, seed=seed + k)
	return p.finish(name, coll, smooth=True)


def field_grass(name, seed, blades=14, height=1.3, coll=None, dry=False):
	"""BotW field grass: blades wide at the root, tapering and curving over, dark at the base, light at the tip; two
	segments each (5 triangles)"""
	p = Piece(seed)
	r = p.rng
	base, tip = ("6e7a3a", "e2d68a") if dry else ("grass_base", "grass_tip")
	for _ in range(blades):
		a = r.uniform(0, math.tau)
		d = r.uniform(0, 0.35)
		root = Vector((math.cos(a) * d, math.sin(a) * d, -0.05))
		h = height * r.uniform(0.55, 1.15)
		bend = r.uniform(0.15, 0.5)
		lean = Vector((math.cos(a), math.sin(a), 0))
		w = r.uniform(0.06, 0.1) * height / 1.3
		side = Vector((-lean.y, lean.x, 0)) * w
		m1 = root + lean * h * bend * 0.25 + Vector((0, 0, h * 0.55))
		m2 = root + lean * h * bend * 0.7 + Vector((0, 0, h * 0.88))
		t = root + lean * h * bend * 1.25 + Vector((0, 0, h * 1.0))
		cb = jitter(base, r, v=0.08)
		ct = mix(cb, jitter(tip, r, v=0.06), r.uniform(0.55, 1.0))
		cm = mix(cb, ct, 0.55)
		f1 = p.poly([root - side, root + side, m1 + side * 0.7, m1 - side * 0.7], cb)
		f2 = p.poly([m1 - side * 0.7, m1 + side * 0.7, m2 + side * 0.35, m2 - side * 0.35], cm)
		f3 = p.poly([m2 - side * 0.35, m2 + side * 0.35, t], ct)
		for f, c0, c1 in ((f1, cb, cm), (f2, cm, ct), (f3, ct, ct)):  # gradient along each blade
			zs = [lp.vert.co.z for lp in f.loops]
			z0, z1 = min(zs), max(zs) + 1e-4
			p.paint_loops([f], lambda lp, c0=c0, c1=c1, z0=z0, z1=z1: mix(c0, c1, (lp.vert.co.z - z0) / (z1 - z0)))
	obj = p.finish(name, coll, smooth=False)
	for poly in obj.data.polygons:  # blades shade as if they face up: soft, bright fields (BotW's grass is lit like ground)
		poly.use_smooth = True
	obj.data.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(obj.data.vertices))
	return obj


def mossy_boulder(name, seed, size=(7, 6, 5), coll=None, moss=0.6):
	"""a big rounded boulder with a moss cap on its top (the anime meadow reference): grey sides, bright green top"""
	p = Piece(seed)
	r = p.rng
	pts = []
	for _ in range(30):
		v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
		pts.append(Vector((v.x * size[0] / 2, v.y * size[1] / 2, v.z * size[2] / 2 + size[2] * 0.25)))
	faces = p.hull(pts, "rock_cool", dissolve=5)
	p.bm.normal_update()

	def fn(lp):
		n = lp.vert.normal
		up = max(0.0, n.z)
		g = jitter("rock_cool", r, v=0.04)
		g = scale_v(g, 0.82 + 0.3 * up)
		if moss and up > 0.55 - moss * 0.3:
			t = min(1.0, (up - (0.55 - moss * 0.3)) / 0.25)
			g = mix(g, jitter("moss", r, v=0.05), t)
		return g

	p.paint_loops(faces, fn)
	return p.finish(name, coll, smooth=True, sharp=42)


# ---------------------------------------------------------------- town (7DS pastoral: white plaster, timber, blue slate)


def _box(p, c, size, colour, yaw=0.0, chamfer=0.0):
	along = Vector((math.cos(yaw), math.sin(yaw), 0))
	out = Vector((-math.sin(yaw), math.cos(yaw), 0)) * -1
	return p.block(Vector(c) + Vector((0, 0, size[2] / 2)), along, out, size, colour, chamfer=chamfer)


def _gable(p, c, w, d, wall_h, rise, colour, overhang=0.6, ridge_col=None):
	"""a gable roof over a w x d footprint (ridge along X) from wall_h up: two slabs with overhang, plaster gable ends"""
	c = Vector(c)
	x, y = w / 2 + overhang, d / 2 + overhang
	t = 0.35
	for sy in (-1, 1):
		top = [c + Vector((-x, sy * y, wall_h)), c + Vector((x, sy * y, wall_h)), c + Vector((x, 0, wall_h + rise)), c + Vector((-x, 0, wall_h + rise))]
		p.hull(top + [q - Vector((0, 0, t)) for q in top], jitter(colour, p.rng, v=0.04))
	for sx in (-1, 1):
		tri = [c + Vector((sx * w / 2, -d / 2, wall_h)), c + Vector((sx * w / 2, d / 2, wall_h)), c + Vector((sx * w / 2, 0, wall_h + rise - 0.2))]
		p.poly(tri if sx > 0 else tri[::-1], jitter("plaster", p.rng, v=0.03))
	if ridge_col:
		p.hull([c + Vector((sx * (x + 0.1), sy * 0.3, wall_h + rise + dz)) for sx in (-1, 1) for sy in (-1, 1) for dz in (-0.1, 0.25)], ridge_col)


def house(name, seed, w=10.0, d=8.0, h=8.0, coll=None, roof="slate", storeys=2):
	"""a timber-framed plaster house: stone footing, white walls with dark timber bands and posts, dark windows with
	flower boxes, a steep gable roof (blue slate or red tile), a stone chimney"""
	p = Piece(seed)
	r = p.rng
	foot = 0.9
	_box(p, (0, 0, -0.4), (w + 0.4, d + 0.4, foot + 0.4), jitter("stone_mid", r))
	_box(p, (0, 0, foot), (w, d, h - foot), jitter("plaster", r, v=0.02))
	tw = 0.32
	for z in [foot] + [foot + (h - foot) * k / storeys for k in range(1, storeys + 1)]:  # horizontal beams
		for sy in (-1, 1):
			_box(p, (0, sy * (d / 2 + 0.05), z - tw / 2), (w + 0.1, 0.12, tw), "timber")
		for sx in (-1, 1):
			_box(p, (sx * (w / 2 + 0.05), 0, z - tw / 2), (0.12, d + 0.1, tw), "timber")
	for sx in (-1, 1):
		for sy in (-1, 1):
			_box(p, (sx * (w / 2 + 0.02), sy * (d / 2 + 0.02), foot), (0.36, 0.36, h - foot), "timber")
	nwin = max(1, int(w // 3.5))
	for s in range(storeys):
		zc = foot + (h - foot) * (s + 0.45) / storeys
		for i in range(nwin):
			x = -w / 2 + w * (i + 0.5) / nwin
			if s == 0 and i == nwin // 2:  # the door
				_box(p, (x, -d / 2 - 0.08, foot), (1.5, 0.2, 2.6), "6b4a33")
				continue
			_box(p, (x, -d / 2 - 0.06, zc - 0.7), (1.2, 0.14, 1.4), "window")
			_box(p, (x, -d / 2 - 0.12, zc - 0.85), (1.5, 0.22, 0.18), "timber")
			if s == 0 or r.random() < 0.5:  # flower box: a dab of colour
				_box(p, (x, -d / 2 - 0.3, zc - 1.05), (1.4, 0.4, 0.3), "6b4a33")
				_box(p, (x, -d / 2 - 0.3, zc - 0.78), (1.3, 0.35, 0.25), r.choice(["d9435a", "e87d3e", "f2d04a", "c45ab0"]))
		for i in range(nwin):  # back windows (no boxes)
			x = -w / 2 + w * (i + 0.5) / nwin
			_box(p, (x, d / 2 + 0.06, zc - 0.7), (1.2, 0.14, 1.4), "window")
	rise = d * r.uniform(0.55, 0.75)
	_gable(p, (0, 0, 0), w, d, h, rise, "slate" if roof == "slate" else "tile", ridge_col="3a4a60" if roof == "slate" else "8a3f2a")
	if r.random() < 0.8:
		cx = r.uniform(-w * 0.3, w * 0.3)
		_box(p, (cx, d * 0.18, h), (1.1, 1.1, rise * 0.9), jitter("stone_mid", r))
	return p.finish(name, coll)


def round_tower(name, seed, radius=4.0, height=20.0, coll=None, roof_h=None, material="stone_light", sides=12, windows=3):
	"""a round tower: a band at the top, slit windows, a tall cone roof in blue slate with a finial"""
	p = Piece(seed)
	r = p.rng
	roof_h = roof_h or radius * 2.4
	p.hull(kit.ring(0, radius * 1.04, sides) + kit.ring(height, radius, sides), lambda f: jitter(material, r, v=0.03))
	p.hull(kit.ring(height - 0.2, radius * 1.12, sides) + kit.ring(height + 0.9, radius * 1.12, sides), lambda f: jitter("stone_mid", r, v=0.03))
	for k in range(windows):
		z = height * (0.3 + 0.55 * k / max(1, windows - 1))
		a = r.uniform(0, math.tau) if k else -math.pi / 2
		c = Vector((math.cos(a) * radius, math.sin(a) * radius, z))
		n = Vector((math.cos(a), math.sin(a), 0))
		t = Vector((-n.y, n.x, 0))
		p.block(c, t, n, (0.7, 0.4, 1.8), "window")
	cone = kit.ring(height + 0.9, radius * 1.25, sides) + [Vector((0, 0, height + 0.9 + roof_h))]
	p.hull(cone, lambda f: jitter("slate", r, v=0.04))
	p.hull([Vector((x * 0.12, y * 0.12, height + roof_h + 0.8 + z)) for x in (-1, 1) for y in (-1, 1) for z in (0, 1.6)], "c9a24a")
	return p.finish(name, coll)


def crenel_wall(name, seed, length=24.0, height=10.0, thick=3.0, coll=None):
	"""a town wall: coursed stone, a walkway lip and square merlons"""
	p = Piece(seed)
	r = p.rng
	_box(p, (0, 0, 0), (length, thick, height), jitter("stone_light", r, v=0.03))
	_box(p, (0, 0, height - 0.3), (length + 0.2, thick + 0.6, 0.6), "stone_mid")
	n = max(2, int(length / 3))
	for i in range(n):
		if i % 2 == 0:
			x = -length / 2 + length * (i + 0.5) / n
			_box(p, (x, -thick * 0.3, height + 0.3), (length / n * 0.9, thick * 0.4, 1.6), jitter("stone_light", r, v=0.04))
	return p.finish(name, coll)


def keep(name, seed, coll=None):
	"""Brightwater's castle keep: a tall white main block with a blue slate roof, four corner turrets with cone roofs, a
	taller spire tower on one side with a gold finial: the landmark seen from every zone (about 70 studs)"""
	p = Piece(seed)
	r = p.rng
	W, D, H = 26.0, 20.0, 34.0
	_box(p, (0, 0, -1), (W + 3, D + 3, 4), "stone_mid")
	_box(p, (0, 0, 3), (W, D, H - 3), jitter("stone_light", r, v=0.02))
	for z in (H * 0.45, H * 0.8):
		_box(p, (0, 0, z), (W + 0.4, D + 0.4, 0.6), "stone_mid")
	for k in range(5):  # tall arched windows on the front
		x = -W / 2 + W * (k + 0.5) / 5
		_box(p, (x, -D / 2 - 0.1, H * 0.55), (1.6, 0.3, 4.5), "window")
		_box(p, (x, -D / 2 - 0.1, H * 0.2), (1.4, 0.3, 3.2), "window")
	_box(p, (0, -D / 2 - 0.2, 3), (5, 0.6, 6.5), "4a3a2c")
	_gable(p, (0, 0, 0), W, D, H, D * 0.7, "slate", overhang=0.8, ridge_col="3a4a60")
	for sx in (-1, 1):
		for sy in (-1, 1):
			_place_tower(p, Vector((sx * W / 2, sy * D / 2, 0)), 3.6, H + 6, 9, r)
	_place_tower(p, Vector((W / 2 + 4, -D / 4, 0)), 5.0, H + 22, 16, r)
	return p.finish(name, coll)


def _place_tower(p, at, radius, height, roof_h, r, sides=12):
	ring = lambda z, rad: [at + v for v in kit.ring(z, rad, sides)]
	p.hull(ring(0, radius) + ring(height, radius * 0.97), lambda f: jitter("stone_light", r, v=0.03))
	p.hull(ring(height, radius * 1.12) + ring(height + 1.0, radius * 1.12), lambda f: jitter("stone_mid", r, v=0.03))
	p.hull(ring(height + 1.0, radius * 1.22) + [at + Vector((0, 0, height + 1.0 + roof_h))], lambda f: jitter("slate", r, v=0.04))
	p.hull([at + Vector((x * 0.14, y * 0.14, height + roof_h + 1.0 + z)) for x in (-1, 1) for y in (-1, 1) for z in (0, 2.0)], "c9a24a")
	for k in range(3):
		a = -math.pi / 2 + r.uniform(-0.6, 0.6)
		c = at + Vector((math.cos(a) * radius, math.sin(a) * radius, height * (0.35 + 0.22 * k)))
		n = Vector((math.cos(a), math.sin(a), 0))
		p.block(c, Vector((-n.y, n.x, 0)), n, (0.7, 0.4, 1.8), "window")


def stone_bridge(name, seed, length=34.0, width=7.0, coll=None, arches=3, rise=7.0):
	"""a coursed stone bridge: piers, true round arches with a ring of voussoirs, solid spandrels up to a deck that humps a
	little in the middle, and parapets"""
	p = Piece(seed)
	r = p.rng
	span = length / arches
	pier = span * 0.22
	rad = (span - pier) / 2
	spring = rise - rad - 0.9
	deck_z = lambda x: rise + 0.8 * math.cos(math.pi * x / (length + 4))
	for i in range(arches + 1):
		x = -length / 2 + i * span
		_box(p, (x, 0, -6), (pier, width, spring + 6), jitter("stone_light", r, v=0.04))
	for i in range(arches):
		cx = -length / 2 + span * (i + 0.5)
		n = 9
		for k in range(n):
			a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
			ring = [Vector((cx - math.cos(a) * rr, y, spring + math.sin(a) * rr)) for a in (a0, a1) for rr in (rad, rad + 1.0) for y in (-width / 2 - 0.05, width / 2 + 0.05)]
			p.hull(ring, jitter("stone_mid", r, v=0.05))
			for side in (-1, 1):  # spandrel: from the ring's outer edge straight up to the deck
				pts = []
				for a in (a0, a1):
					x = cx - math.cos(a) * (rad + 1.0)
					z = spring + math.sin(a) * (rad + 1.0)
					pts += [Vector((x, side * width / 2, z)), Vector((x, side * width / 2, deck_z(x)))]
				q = [pts[0], pts[2], pts[3], pts[1]]
				p.poly(q if side < 0 else q[::-1], jitter("stone_light", r, v=0.03))
	xs = [-length / 2 - 2 + (length + 4) * k / 10 for k in range(11)]
	for x0, x1 in zip(xs, xs[1:]):
		p.hull([Vector((x, y, deck_z(x) + dz)) for x in (x0, x1) for y in (-width / 2, width / 2) for dz in (-0.6, 0.0)], jitter("c8b48a", r, v=0.03))
		for side in (-1, 1):
			p.hull([Vector((x, side * (width / 2 - 0.3) + dy, deck_z(x) + dz)) for x in (x0, x1) for dy in (-0.3, 0.3) for dz in (0.0, 1.1)], jitter("stone_mid", r, v=0.03))
	return p.finish(name, coll)


def windmill(name, seed, coll=None, height=18.0):
	"""a tapered round mill (white plaster, stone foot), a cap roof and four lattice sails with cream cloth"""
	p = Piece(seed)
	r = p.rng
	p.hull(kit.ring(0, 4.6, 12) + kit.ring(2, 4.5, 12), lambda f: jitter("stone_mid", r, v=0.03))
	p.hull(kit.ring(2, 4.4, 12) + kit.ring(height, 3.0, 12), lambda f: jitter("plaster", r, v=0.02))
	p.hull(kit.ring(height, 3.5, 12) + [Vector((0, 0.6, height + 4.2))], lambda f: jitter("tile", r, v=0.04))
	_box(p, (0, -4.3, 0), (1.6, 0.4, 2.8), "6b4a33")
	hub = Vector((0, -3.8, height - 0.5))
	p.hull([hub + Vector((x, y, z)) for x in (-0.5, 0.5) for y in (-0.6, 0.2) for z in (-0.5, 0.5)], "timber")
	for k in range(4):
		a = k * math.tau / 4 + 0.35
		d = Vector((math.cos(a), 0, math.sin(a)))
		s = Vector((-math.sin(a), 0, math.cos(a)))
		L = height * 0.62
		p.hull([hub + d * t + s * w + Vector((0, y, 0)) for t in (0.4, L) for w in (-0.18, 0.18) for y in (-0.15, 0.15)], "timber")
		cloth = [hub + d * 2.0 + s * 0.2, hub + d * L + s * 0.2, hub + d * L + s * 2.6, hub + d * 2.0 + s * 2.2]
		p.poly([c + Vector((0, -0.25, 0)) for c in cloth], jitter("cloth_cream", r, v=0.03))
	return p.finish(name, coll)


def waterwheel(name, seed, radius=5.0, width=2.0, coll=None):
	"""a mill wheel standing in the XZ plane: two rims, six spokes, twelve paddles and an axle"""
	p = Piece(seed)
	n = 12
	Y = Vector((0, 1, 0))
	ctr = Vector((0, 0, radius))
	rad_dir = lambda a: Vector((math.cos(a), 0, math.sin(a)))
	tan_dir = lambda a: Vector((-math.sin(a), 0, math.cos(a)))
	for side in (-1, 1):
		for k in range(n):
			a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
			p.hull([ctr + rad_dir(a) * rr + Y * (side * width / 2 + dy) for a in (a0, a1) for rr in (radius - 0.5, radius) for dy in (-0.15, 0.15)], "timber")
		for k in range(6):
			a = k * math.tau / 6
			p.hull([ctr + rad_dir(a) * t + tan_dir(a) * w + Y * (side * width / 2 + dy) for t in (0.3, radius - 0.4) for w in (-0.15, 0.15) for dy in (-0.12, 0.12)], "timber")
	for k in range(n):
		a = (k + 0.5) * math.tau / n
		c = ctr + rad_dir(a) * (radius - 0.1)
		p.hull([c + rad_dir(a) * dr + tan_dir(a) * dt + Y * dy for dr in (-0.6, 0.6) for dt in (-0.08, 0.08) for dy in (-width / 2 - 0.1, width / 2 + 0.1)], "6b4a33")
	p.hull([ctr + Vector((x, y, z)) for x in (-0.35, 0.35) for y in (-width / 2 - 0.8, width / 2 + 0.8) for z in (-0.35, 0.35)], "timber")
	return p.finish(name, coll)


def stall(name, seed, coll=None, colour="cloth_red"):
	"""a market stall: four posts, a counter and a striped awning"""
	p = Piece(seed)
	r = p.rng
	for sx in (-1, 1):
		for sy in (-1, 1):
			_box(p, (sx * 2.2, sy * 1.4, 0), (0.25, 0.25, 3.4), "timber")
	_box(p, (0, -1.1, 0), (4.6, 1.2, 1.3), "8a6a4a")
	for k in range(6):
		x0 = -2.6 + 5.2 * k / 6
		c = colour if k % 2 == 0 else "cloth_cream"
		p.poly([Vector((x0, -2.2, 3.0)), Vector((x0 + 5.2 / 6, -2.2, 3.0)), Vector((x0 + 5.2 / 6, 1.7, 3.9)), Vector((x0, 1.7, 3.9))], jitter(c, r, v=0.03))
	for k in range(5):  # goods: little coloured lumps
		_box(p, (-1.8 + k * 0.9, -1.1, 1.3), (0.6, 0.6, 0.45), r.choice(["d9a13a", "c94a35", "6aa84a", "e8d6a0"]))
	return p.finish(name, coll)


# ---------------------------------------------------------------- landmarks


def grand_gate(name, seed, coll=None, height=64.0):
	"""the Gate: two massive stepped pillars of ancient stone with rune bands, a deep round arch of big voussoirs, a
	glowing crystal keystone and moss on every ledge. Rune faces are glow (Neon in Roblox)."""
	p = Piece(seed)
	r = p.rng
	pw, pd = height * 0.16, height * 0.2
	span = height * 0.42
	spring = height * 0.5

	def stone(f):
		c = jitter("stone_mid", r, v=0.05)
		if f.normal.z > 0.6:
			c = mix(c, jitter("moss", r, v=0.06), 0.85)
		return c

	for sx in (-1, 1):
		x = sx * (span / 2 + pw / 2)
		z = 0.0
		tiers = [(1.3, 0.1), (1.15, 0.12), (1.0, 0.5), (1.08, 0.06), (1.0, 0.22)]
		for k, (scale, frac) in enumerate(tiers):
			hh = spring * frac / sum(t[1] for t in tiers) * 1.0
			p.hull([Vector((x + dx * pw / 2 * scale, dy * pd / 2 * scale, z + dz)) for dx in (-1, 1) for dy in (-1, 1) for dz in (0, hh)], stone)
			if k == 2:  # the rune bands: three thin glowing bars on each face
				for side in (-1, 1):
					for b in (-1, 0, 1):
						bx = x + b * pw * 0.22
						p.hull([Vector((bx + dx * pw * 0.035, side * (pd / 2 * scale + 0.06) + dy, z + hh * (0.15 + 0.1 * abs(b)) + dz)) for dx in (-1, 1) for dy in (-0.05, 0.05) for dz in (0, hh * (0.7 - 0.2 * abs(b)))], "rune", glow=True)
			z += hh
	rad_in, rad_out = span / 2, span / 2 + height * 0.13
	n = 11
	for k in range(n):
		a0, a1 = math.pi * k / n + 0.004, math.pi * (k + 1) / n - 0.004
		pts = []
		for a in (a0, a1):
			for rr in (rad_in, rad_out * (1.04 if k == n // 2 else 1.0)):
				for y in (-pd / 2 * 0.92, pd / 2 * 0.92):
					pts.append(Vector((math.cos(a) * rr, y, spring + math.sin(a) * rr)))
		p.hull(pts, stone)
	# keystone crystal
	kc = Vector((0, -pd / 2 * 0.95, spring + rad_out + height * 0.02))
	p.hull([kc + Vector((x, y, z)) for x, y, z in ((0, 0, height * 0.07), (height * 0.03, 0, 0), (-height * 0.03, 0, 0), (0, -height * 0.025, 0), (0, height * 0.02, 0), (0, 0, -height * 0.05))], "rune", glow=True)
	# lintel band over the arch
	p.hull([Vector((x, y, z)) for x in (-(span / 2 + pw * 1.1), span / 2 + pw * 1.1) for y in (-pd / 2, pd / 2) for z in (spring + rad_out - 0.5, spring + rad_out + height * 0.06)], stone)
	return p.finish(name, coll, smooth=False)


def light_beam(name, height=900.0, radius=3.0, coll=None):
	"""the Gate's pillar of light: a tall open cylinder; renders with an additive fading material, Roblox: a Beam"""
	import bpy

	p = Piece(1)
	sides = 12
	rings = [kit.ring(z, radius * (1.0 + 0.6 * z / height), sides) for z in (0.0, height * 0.3, height)]
	p.quad_strip(rings, "rune", close=True)
	obj = p.finish(name, coll, smooth=True)
	m = bpy.data.materials.new("Beam")
	m.use_nodes = True
	try:
		m.surface_render_method = "BLENDED"
	except AttributeError:
		pass
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	em = nt.nodes.new("ShaderNodeEmission")
	em.inputs["Color"].default_value = (0.55, 0.9, 1.0, 1)
	em.inputs["Strength"].default_value = 3.0
	tr = nt.nodes.new("ShaderNodeBsdfTransparent")
	mixs = nt.nodes.new("ShaderNodeMixShader")
	geo = nt.nodes.new("ShaderNodeNewGeometry")
	sep = nt.nodes.new("ShaderNodeSeparateXYZ")
	ramp = nt.nodes.new("ShaderNodeMapRange")
	ramp.inputs["From Min"].default_value = 0.0
	ramp.inputs["From Max"].default_value = height
	ramp.inputs["To Min"].default_value = 0.45
	ramp.inputs["To Max"].default_value = 0.98
	fres = nt.nodes.new("ShaderNodeLayerWeight")
	fres.inputs["Blend"].default_value = 0.5
	addm = nt.nodes.new("ShaderNodeMath")
	addm.operation = "MAXIMUM"
	nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
	nt.links.new(sep.outputs["Z"], ramp.inputs["Value"])
	nt.links.new(ramp.outputs["Result"], addm.inputs[0])
	nt.links.new(fres.outputs["Facing"], addm.inputs[1])
	nt.links.new(addm.outputs["Value"], mixs.inputs["Fac"])
	nt.links.new(em.outputs["Emission"], mixs.inputs[1])
	nt.links.new(tr.outputs["BSDF"], mixs.inputs[2])
	nt.links.new(mixs.outputs["Shader"], out.inputs["Surface"])
	obj.data.materials.clear()
	obj.data.materials.append(m)
	return obj


def standing_stone(name, seed, height=7.0, coll=None, rune=True):
	p = Piece(seed)
	r = p.rng
	w, d = height * 0.32, height * 0.2
	pts = []
	for z in (0, height * 0.5, height):
		k = 1 - 0.25 * z / height
		for sx in (-1, 1):
			for sy in (-1, 1):
				pts.append(Vector((sx * w / 2 * k * r.uniform(0.85, 1.0), sy * d / 2 * k * r.uniform(0.85, 1.0), z + r.uniform(-0.3, 0.2) * (z > 0))))
	pts.append(Vector((r.uniform(-0.3, 0.3), 0, height + 0.5)))
	faces = p.hull([q + Vector((0, 0, -0.5)) for q in pts], "stone_mid", dissolve=3)
	p.bm.normal_update()
	p.paint_loops(faces, lambda lp: mix(jitter("stone_mid", r, v=0.03), "moss", 0.8) if lp.vert.normal.z > 0.7 else scale_v(jitter("stone_mid", r, v=0.03), 0.85 + 0.15 * lp.vert.co.z / height))
	if rune:
		p.hull([Vector((x, -d / 2 * 0.85 - 0.05 + y, z)) for x in (-w * 0.12, w * 0.12) for y in (0, 0.08) for z in (height * 0.3, height * 0.6)], "rune", glow=True)
	return p.finish(name, coll, smooth=True, sharp=35)


def tent(name, seed, coll=None, colour="cloth_red", length=6.0, width=4.5, height=3.6):
	"""a ridge tent: two sloped cloth sides and closed ends, a pole at each end"""
	p = Piece(seed)
	r = p.rng
	c = jitter(colour, r, v=0.05)
	L, W, H = length / 2, width / 2, height
	p.poly([Vector((-L, -W, 0)), Vector((L, -W, 0)), Vector((L, 0, H)), Vector((-L, 0, H))], c)
	p.poly([Vector((L, W, 0)), Vector((-L, W, 0)), Vector((-L, 0, H)), Vector((L, 0, H))], scale_v(c, 0.9))
	p.poly([Vector((L, -W, 0)), Vector((L, W, 0)), Vector((L, 0, H))], scale_v(c, 0.8))
	p.poly([Vector((-L, W, 0)), Vector((-L, -W, 0)), Vector((-L, 0, H))], scale_v(c, 0.8))
	for sx in (-1, 1):
		p.hull([Vector((sx * (L + 0.15) + x, y, z)) for x in (-0.1, 0.1) for y in (-0.1, 0.1) for z in (0, H + 0.6)], "timber")
	return p.finish(name, coll)


def palisade(name, seed, length=20.0, coll=None, height=5.0):
	p = Piece(seed)
	r = p.rng
	n = int(length / 0.9)
	for i in range(n):
		x = -length / 2 + length * (i + 0.5) / n
		h = height * r.uniform(0.85, 1.05)
		rad = 0.42
		pts = kit.ring(0, rad, 5, r.uniform(0, 1)) + kit.ring(h, rad, 5) + [Vector((0, 0, h + 0.9))]
		p.hull([q + Vector((x, 0, 0)) for q in pts], lambda f: jitter("8a6a4a", r, v=0.08))
	return p.finish(name, coll)


def mountain_range(name, seed, width=4000.0, depth=900.0, height=900.0, coll=None, peaks=5, snow=0.62, sharp=1.0):
	"""a faceted mountain range strip (for the far layers): a ridge line with peaks, snow above `snow` of the height,
	rock below. Flat-shaded big facets read as BotW's painted far mountains once hazed"""
	p = Piece(seed)
	r = p.rng
	nx, ny = 36, 9
	tops = [(r.uniform(-0.45, 0.45), r.uniform(0.55, 1.0)) for _ in range(peaks)]
	grid = []
	for j in range(ny + 1):
		v = j / ny
		row = []
		for i in range(nx + 1):
			u = i / nx - 0.5
			ridge = max(t[1] * max(0.0, 1 - abs(u - t[0]) * (3.2 + 2.0 * sharp)) ** 1.15 for t in tops)
			ridge = max(ridge, 0.28 + 0.1 * math.sin(u * 19 + seed))
			prof = math.sin(math.pi * v) ** 0.8
			z = height * ridge * prof * r.uniform(0.92, 1.08) if 0 < j < ny else -50
			row.append(Vector((u * width + r.uniform(-0.3, 0.3) * width / nx, (v - 0.5) * depth, z)))
		grid.append(row)
	for j in range(ny):
		for i in range(nx):
			a, b, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
			for tri in ((a, b, c), (a, c, d)) if (i + j) % 2 else ((a, b, d), (b, c, d)):
				zc = sum(q.z for q in tri) / 3
				nrm = (tri[1] - tri[0]).cross(tri[2] - tri[0]).normalized()
				if zc > height * snow * r.uniform(0.92, 1.05) and abs(nrm.z) > 0.35:
					col = jitter("snow", r, v=0.02)
				else:
					col = jitter("rock_cool", r, v=0.05)
				p.poly(list(tri), col)
	return p.finish(name, coll)


def floating_island(name, seed, radius=120.0, coll=None):
	"""a far floating island (the SAO-style promise of the next Land): an inverted cone of stratified rock with a grassy
	top, a few trees, a ruined spire and waterfalls pouring off the rim into nothing"""
	p = Piece(seed)
	r = p.rng
	n = 18
	rings = []
	for k, (z, rr) in enumerate(((0, 1.0), (-0.12, 0.97), (-0.3, 0.82), (-0.55, 0.6), (-0.8, 0.33), (-1.0, 0.1))):
		rings.append([Vector((math.cos(a) * radius * rr * r.uniform(0.9, 1.08), math.sin(a) * radius * rr * r.uniform(0.9, 1.08), z * radius * 1.1 + r.uniform(-3, 3))) for a in (i * math.tau / n for i in range(n))])
	bands = ["8d8072", "a29484", "7c7066", "958877", "6f665d"]
	for k, (ra, rb) in enumerate(zip(rings, rings[1:])):
		for i in range(n):
			j = (i + 1) % n
			p.poly([rb[i], rb[j], ra[j], ra[i]], jitter(bands[k % len(bands)], r, v=0.05))
	tip = Vector((r.uniform(-5, 5), r.uniform(-5, 5), -radius * 1.3))
	for i in range(n):
		p.poly([rings[-1][(i + 1) % n], rings[-1][i], tip], jitter("6f665d", r))
	top = rings[0]
	ctr = Vector((0, 0, 4))
	for i in range(n):
		p.poly([top[i], top[(i + 1) % n], ctr], jitter("6f9a45", r, v=0.06))
	for k in range(9):  # trees on top: cone pines and round broadleaves
		a, d = r.uniform(0, math.tau), r.uniform(0.15, 0.75) * radius
		c = Vector((math.cos(a) * d, math.sin(a) * d, 2))
		if r.random() < 0.6:
			p.hull([c + q for q in kit.ring(0, 6, 7)] + [c + Vector((0, 0, 22))], "35633f")
		else:
			p.hull([c + Vector((0, 0, 9)) + Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1) * 0.8)).normalized() * 9 for _ in range(12)], "4f8a3f")
	sp = Vector((radius * 0.2, -radius * 0.1, 2))  # a ruined spire: something to wonder about
	p.hull([sp + q for q in kit.ring(0, 7, 8) + kit.ring(48, 5, 8)], "c9c3b4")
	p.hull([sp + q for q in kit.ring(48, 6.5, 8) + [Vector((0, 0, 70))]], "5c7392")
	for k in range(3):  # waterfalls off the rim
		a = -math.pi / 2 + (k - 1) * 0.55 + r.uniform(-0.1, 0.1)
		c = Vector((math.cos(a) * radius * 0.98, math.sin(a) * radius * 0.98, 0))
		t = Vector((-math.sin(a), math.cos(a), 0)) * r.uniform(5, 9)
		o = Vector((math.cos(a), math.sin(a), 0)) * 2
		p.poly([c - t + o, c + t + o, c + t * 1.6 + o * 6 + Vector((0, 0, -radius * 1.6)), c - t * 1.6 + o * 6 + Vector((0, 0, -radius * 1.6))], "water_fall")
	return p.finish(name, coll)
