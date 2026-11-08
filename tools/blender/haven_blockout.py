"""The Haven's composition as plain shapes (art/haven/layout.json): circles for size, simple forms for everything else. Renders eye-level views from the game's camera, with a character for scale,
to give to an image model for concept art. Bearings: 0 = north (+Y), clockwise. Heights: main island's top = 0.

  blender --background --python tools/blender/haven_blockout.py -- art/haven
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

FOLDER = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
S = json.load(open(os.path.join(FOLDER, "layout.json"), encoding="utf-8"))
OUT = os.path.join(FOLDER, "composition")
os.makedirs(OUT, exist_ok=True)
HAZE = (0.74, 0.85, 0.94)
HAZE_DISTANCE = 11000.0

GRASS = (0.40, 0.62, 0.34)
GRASS_YOURS = (0.47, 0.72, 0.36)
ROCK = (0.46, 0.44, 0.50)
STONE = (0.74, 0.72, 0.68)
PLAZA = (0.82, 0.79, 0.72)
TOWER = (0.70, 0.66, 0.62)
WOOD = (0.50, 0.36, 0.26)
ROOF = (0.66, 0.34, 0.28)
SLOT = (0.62, 0.70, 0.46)
WATER = (0.42, 0.78, 0.86)
FOAM = (0.94, 0.98, 1.0)
GLOW = (0.45, 0.95, 1.0)
DARK = (0.24, 0.24, 0.30)
FIGURE = (0.95, 0.30, 0.20)
CLOUD = (0.96, 0.97, 0.98)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
materials = {}


def mat(colour, emit=0.0):
	key = (round(colour[0], 3), round(colour[1], 3), round(colour[2], 3), emit)
	if key in materials:
		return materials[key]
	colour = tuple(c**2.2 for c in colour)
	m = bpy.data.materials.new(str(key))
	m.use_nodes = True
	tree = m.node_tree
	tree.nodes.clear()
	out = tree.nodes.new("ShaderNodeOutputMaterial")
	if emit:
		n = tree.nodes.new("ShaderNodeEmission")
		n.inputs["Color"].default_value = (*colour, 1)
		n.inputs["Strength"].default_value = emit
	else:
		n = tree.nodes.new("ShaderNodeBsdfDiffuse")
		n.inputs["Color"].default_value = (*colour, 1)
	tree.links.new(n.outputs[0], out.inputs["Surface"])
	materials[key] = m
	return m


def hazed(colour, distance):
	t = 1 - math.exp(-distance / HAZE_DISTANCE)
	return tuple(c * (1 - t) + h * t for c, h in zip(colour, HAZE))


def at(bearing, distance):
	a = math.radians(bearing)
	return math.sin(a) * distance, math.cos(a) * distance


def obj_from(bm, name, mats):
	mesh = bpy.data.meshes.new(name)
	bm.to_mesh(mesh)
	bm.free()
	for m in mats:
		mesh.materials.append(m)
	o = bpy.data.objects.new(name, mesh)
	scene.collection.objects.link(o)
	return o


def cyl(x, y, z, r0, r1, h, colour, segs=32, emit=0.0, name="Cyl"):
	bm = bmesh.new()
	bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r0, radius2=r1, depth=h)
	bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, z + h / 2))
	return obj_from(bm, name, [mat(colour, emit)])


def ball(x, y, z, rx, ry, rz, colour, emit=0.0, name="Ball"):
	bm = bmesh.new()
	bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
	for f in bm.faces:
		f.smooth = True
	bmesh.ops.scale(bm, verts=bm.verts, vec=(rx, ry, rz))
	bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, z))
	return obj_from(bm, name, [mat(colour, emit)])


def box(x, y, z, w, d, h, yaw, colour, emit=0.0, name="Box"):
	"""w along its local x, centred; z is its base; yaw in radians, counter-clockwise"""
	bm = bmesh.new()
	bmesh.ops.create_cube(bm, size=1.0)
	bmesh.ops.scale(bm, verts=bm.verts, vec=(w, d, h))
	o = obj_from(bm, name, [mat(colour, emit)])
	o.location = (x, y, z + h / 2)
	o.rotation_euler = (0, 0, yaw)
	return o


def island(x, y, top, r, depth, top_colour, under_colour, seed, name="Island"):
	"""the top is a true circle, so its size reads; the underside tapers away in rough steps"""
	rng = random.Random(seed)
	segs = 72
	rings = [(0.0, 1.0, 0.0), (0.09, 0.97, 0.03), (0.28, 0.76, 0.06), (0.6, 0.44, 0.1), (0.86, 0.18, 0.14)]
	bm = bmesh.new()
	waves = [(rng.randint(3, 9), rng.uniform(0, 6.28), rng.uniform(0.4, 1.0)) for _ in range(5)]
	grid = []
	for down, scale, amp in rings:
		ring = []
		for k in range(segs):
			a = k / segs * math.tau
			n = sum(w[2] * math.sin(a * w[0] + w[1]) for w in waves) / 2.5
			rr = r * scale * (1 + amp * n)
			ring.append(bm.verts.new((x + math.sin(a) * rr, y + math.cos(a) * rr, top - depth * down)))
		grid.append(ring)
	tip = bm.verts.new((x, y, top - depth))
	top_face = bm.faces.new(grid[0])
	top_face.material_index = 0
	for band, (r0, r1) in enumerate(zip(grid, grid[1:])):
		for k in range(segs):
			f = bm.faces.new((r0[k], r0[(k + 1) % segs], r1[(k + 1) % segs], r1[k]))
			f.material_index = 0 if band == 0 else 1
	for k in range(segs):
		f = bm.faces.new((grid[-1][k], grid[-1][(k + 1) % segs], tip))
		f.material_index = 1
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	return obj_from(bm, name, [mat(top_colour), mat(under_colour)])


def strip(p0, p1, width, colour, emit=0.0, name="Strip"):
	"""a flat ribbon between two points, facing out sideways: bridges' decks, streams, falling water"""
	a, b = Vector(p0), Vector(p1)
	along = (b - a).normalized()
	side = along.cross(Vector((0, 0, 1)))
	if side.length < 0.01:
		side = Vector((1, 0, 0))
	side = side.normalized() * width / 2
	bm = bmesh.new()
	vs = [bm.verts.new(v) for v in (a - side, a + side, b + side, b - side)]
	bm.faces.new(vs)
	return obj_from(bm, name, [mat(colour, emit)])


def beam(p0, p1, width, height, colour, name="Beam"):
	"""a solid bar between two points, its top following the slope: bridge decks and rails"""
	a, b = Vector(p0), Vector(p1)
	flat = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
	side = Vector((flat.y, -flat.x, 0)) * (width / 2)
	up = Vector((0, 0, height))
	bm = bmesh.new()
	vs = [bm.verts.new(q) for q in (a - side, a + side, b + side, b - side, a - side + up, a + side + up, b + side + up, b - side + up)]
	for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
		bm.faces.new([vs[i] for i in f])
	bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	return obj_from(bm, name, [mat(colour)])


def fall(x, y, z, bearing, width, length, colour, emit=0.75):
	"""falling water hanging off an edge, facing outward along its bearing"""
	a = math.radians(bearing)
	tx, ty = math.cos(a) * width / 2, -math.sin(a) * width / 2
	bm = bmesh.new()
	vs = [bm.verts.new(v) for v in ((x - tx, y - ty, z), (x + tx, y + ty, z), (x + tx * 1.5, y + ty * 1.5, z - length), (x - tx * 1.5, y - ty * 1.5, z - length))]
	bm.faces.new(vs)
	return obj_from(bm, "Fall", [mat(colour, emit)])


# ---- main island
M = S["Main"]
island(0, 0, 0, M["Radius"], M["Depth"], GRASS, ROCK, 3, "Main")
cyl(0, 0, -1, M["Plaza"]["Radius"], M["Plaza"]["Radius"] * 0.9, M["Plaza"]["Height"] + 1, PLAZA, 48, name="Plaza")
# a stone promenade along the north rim, where the arches stand
bm = bmesh.new()
steps = 36
inner, outer = [], []
for k in range(steps + 1):
	b = -74 + 148 * k / steps
	x, y = at(b, 120)
	inner.append(bm.verts.new((x, y, 0.5)))
	x, y = at(b, 176)
	outer.append(bm.verts.new((x, y, 0.5)))
for k in range(steps):
	bm.faces.new((inner[k], inner[k + 1], outer[k + 1], outer[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
obj_from(bm, "Promenade", [mat(PLAZA)])

# the Climb
z = M["Plaza"]["Height"]
for r0, r1, h in S["Tower"]["Tiers"]:
	cyl(0, 0, z, r0, r1, h, TOWER, 32, name="Tower")
	cyl(0, 0, z + h - 2, r1 + 4, r1 + 4, 3, STONE, 32, name="TowerRing")
	z += h
cyl(0, 0, z, 13, 0.5, S["Tower"]["Cap"], ROOF, 16, name="TowerCap")
ball(0, 0, z + S["Tower"]["Cap"] + 4, 5, 5, 5, GLOW, 2.2, name="TowerGlow")
TOWER_TOP = z + S["Tower"]["Cap"] + 4

# arches: each stands on the line to its Land, so it frames that Land from the plaza
A = S["Arches"]
for i, b in enumerate(A["Bearings"]):
	x, y = at(b, A["Radius"])
	yaw = -math.radians(b)
	ca, sa = math.cos(yaw), math.sin(yaw)
	half = A["Width"] / 2 + A["Post"] / 2
	for side in (-1, 1):
		box(x + ca * side * half, y + sa * side * half, 0, A["Post"], A["Post"], A["Height"], yaw, STONE, name="ArchPost")
	opened = any(l.get("Open") and l["Bearing"] == b for l in S["Lands"])
	box(x, y, A["Height"], A["Width"] + A["Post"] * 3, A["Post"], 6, yaw, STONE, name="ArchTop")
	box(x, y, A["Height"] - 1.5, A["Width"], A["Post"] * 0.6, 1.5, yaw, GLOW if opened else DARK, 2.0 if opened else 0.0, name="ArchBand")

# market stalls
for b in S["Market"]["Bearings"]:
	x, y = at(b, S["Market"]["Radius"])
	cyl(x, y, 0, S["Market"]["Stall"], S["Market"]["Stall"], 7, WOOD, 16, name="Stall")
	cyl(x, y, 7, S["Market"]["Stall"] + 3, 2, 5, ROOF, 16, name="StallRoof")

# the stream, running from the plaza to the rim and off the edge
St = S["Stream"]
x0, y0 = at(St["Bearing"], St["From"])
x1, y1 = at(St["Bearing"], M["Radius"])
strip((x0, y0, 0.4), (x1, y1, 0.4), St["Width"], WATER, name="Stream")
fall(x1, y1, 0, St["Bearing"], St["Width"], St["Fall"], FOAM)

# ---- plots, each its own island, joined to the main island by a bridge
P = S["Plots"]
rng = random.Random(11)
plot_at = {}
for i, b in enumerate(P["Bearings"]):
	x, y = at(b, P["Ring"])
	top = P["Heights"][i]
	plot_at[b] = (x, y, top)
	yours = b == P["Yours"]
	island(x, y, top, P["Radius"], P["Depth"], GRASS_YOURS if yours else GRASS, ROCK, 20 + i, f"Plot{b}")
	# bridge from the main island's rim to the plot's rim
	bx0, by0 = at(b, M["Radius"] - 4)
	bx1, by1 = at(b, P["Ring"] - P["Radius"] + 4)
	beam((bx0, by0, -1.2), (bx1, by1, top - 1.2), S["BridgeWidth"], 1.7, WOOD, "Bridge")
	cx0, sx0 = math.cos(math.radians(b)), math.sin(math.radians(b))
	for side in (-1, 1):
		ox, oy = cx0 * side * S["BridgeWidth"] / 2, -sx0 * side * S["BridgeWidth"] / 2
		beam((bx0 + ox, by0 + oy, 0.5), (bx1 + ox, by1 + oy, top + 0.5), 0.8, 3, WOOD, "Rail")
	# building spots: plain circles, with a building-sized block on some, more on some plots than others
	hx, hy = at(b, P["Ring"] + 20)
	spots = [(hx, hy, P["CentreRadius"])]
	for k in range(P["Slots"]):
		a = math.radians(b + 180 + 66 + k * (228 / (P["Slots"] - 1)))
		spots.append((x + math.sin(a) * P["SlotRing"], y + math.cos(a) * P["SlotRing"], P["SlotRadius"]))
	first, rest = spots[0], spots[1:]
	rng.shuffle(rest)
	spots = [first] + rest
	for j, (sx, sy, sr) in enumerate(spots):
		cyl(sx, sy, top - 0.4, sr, sr, 0.8, SLOT, 24, name="Slot")
		if j < P["Buildings"][i]:
			w, d, h = S["Building"]
			yaw = rng.uniform(0, 3.14)
			box(sx, sy, top, w, d, h, yaw, STONE, name="House")
			roof = cyl(sx, sy, top + h, w * 0.72, 1, h * 0.55, ROOF, 4, name="HouseRoof")
			roof.rotation_euler = (0, 0, yaw + math.pi / 4)
			roof.location = (0, 0, 0)
			# rotate about the house's own centre
			roof.data.transform(__import__("mathutils").Matrix.Translation((-sx, -sy, 0)))
			roof.location = (sx, sy, 0)

# small rocks hanging in the gaps, for depth
for k in range(26):
	a, d = rng.uniform(0, 360), rng.uniform(240, 900)
	x, y = at(a, d)
	r = rng.uniform(7, 26)
	z = rng.uniform(-170, 60)
	if any(math.dist((x, y), q[:2]) < P["Radius"] + r + 12 for q in plot_at.values()):
		continue
	if z > -30 and math.dist((x, y), plot_at[P["Yours"]][:2]) < 420:
		continue
	island(x, y, z, r, r * 1.3, GRASS, ROCK, 60 + k, "Islet")

# ---- the Lands: 30 of them in six themes, stacked up the sky, fading with distance. What's on each one comes from
# its "Bits" in layout.json: plain shapes, sized for a Land of radius 800 and scaled to fit
NAMED = {
	"hill": (0.36, 0.58, 0.32),
	"tree": (0.26, 0.56, 0.34),
	"sand": (0.88, 0.78, 0.54),
	"water": WATER,
	"gold": (0.84, 0.70, 0.34),
	"red": (0.86, 0.30, 0.30),
	"stone": STONE,
	"willow": (0.20, 0.38, 0.34),
	"reed": (0.56, 0.62, 0.36),
	"mud": (0.12, 0.14, 0.16),
	"lamp": (1.0, 0.84, 0.46),
	"lava": (1.0, 0.46, 0.20),
	"petal": (0.92, 0.88, 0.96),
	"cap": (0.76, 0.40, 0.66),
	"capblue": (0.46, 0.52, 0.86),
	"capgold": (0.90, 0.72, 0.40),
	"mesa": (0.72, 0.46, 0.30),
	"dune": (0.92, 0.76, 0.50),
	"ember": (0.30, 0.18, 0.18),
	"glass": (0.72, 0.90, 0.92),
	"snow": (0.92, 0.95, 0.98),
	"ice": (0.70, 0.86, 0.96),
	"pine": (0.20, 0.38, 0.36),
}

for i, L in enumerate(S["Lands"]):
	x, y = at(L["Bearing"], L["Distance"])
	dist = L["Distance"]
	r, top = L["Radius"], L["Top"]
	lrng = random.Random(200 + i)
	island(x, y, top, r, r * lrng.uniform(0.62, 1.0), hazed(L["Colour"], dist), hazed(L["Rock"], dist), 100 + i, L["Name"])
	k = r / 800

	def spot(spread=0.75):
		a, d = lrng.uniform(0, 6.283), r * spread * math.sqrt(lrng.random())
		return x + math.sin(a) * d, y + math.cos(a) * d

	def U(lo, hi):
		return lrng.uniform(lo, hi) * k

	for bit in L["Bits"]:
		kind, n = bit[0], bit[1]
		c = hazed(NAMED[bit[2]], dist) if len(bit) > 2 else None
		for j in range(n):
			hx, hy = spot()
			if kind == "hills":
				cyl(hx, hy, top, U(90, 200), U(20, 60), U(50, 130), c, 16, name="Hill")
			elif kind == "patch":
				rad = U(70, 170)
				cyl(hx, hy, top, rad, rad, 8 * k, c, 20, name="Patch")
			elif kind == "trees":
				ball(hx, hy, top + 60 * k, 70 * k, 70 * k, 60 * k, c, name="Tree")
			elif kind == "giant":
				tx, ty = x + 90 * k, y + 40 * k
				cyl(tx, ty, top, 120 * k, 62 * k, 680 * k, hazed((0.42, 0.30, 0.24), dist), 16, name="ElderTrunk")
				crown = hazed((0.20, 0.50, 0.34), dist)
				ball(tx, ty, top + 780 * k, 420 * k, 420 * k, 200 * k, crown, name="ElderCrown")
				ball(tx - 260 * k, ty, top + 590 * k, 250 * k, 250 * k, 115 * k, crown, name="ElderCrown")
				ball(tx + 280 * k, ty - 40 * k, top + 610 * k, 240 * k, 240 * k, 110 * k, crown, name="ElderCrown")
			elif kind == "falls":
				edge = L["Bearing"] + 2 + j * 42
				fx, fy = at(edge, r)
				fall(x + fx * (-1), y - fy, top, edge + 180, 70 * k, 760 * k, hazed(FOAM, dist * 0.5), 0.85)
			elif kind == "mill":
				cyl(x - 100 * k, y, top + 40 * k, 42 * k, 30 * k, 190 * k, hazed(STONE, dist), 12, name="Mill")
				box(x - 100 * k, y - 40 * k, top + 190 * k, 240 * k, 14 * k, 18 * k, 0.5, hazed(WOOD, dist), name="Sail")
				box(x - 100 * k, y - 40 * k, top + 100 * k, 18 * k, 14 * k, 200 * k, 0.5, hazed(WOOD, dist), name="Sail")
			elif kind == "caps":
				h = U(90, 260)
				cyl(hx, hy, top, 22 * k, 16 * k, h, hazed((0.82, 0.78, 0.74), dist), 10, name="Stem")
				rad = U(80, 150)
				ball(hx, hy, top + h, rad, rad, 50 * k, c, name="Cap")
			elif kind == "peaks":
				hx, hy = spot(0.6)
				cyl(hx, hy, top, U(190, 360), 6 * k, U(300, 720), c, 7, name="Peak")
			elif kind == "crown":
				# the last Land: one enormous peak ringed by smaller ones
				cyl(x, y, top, 520 * k, 8 * k, 1500 * k, hazed(NAMED["snow"], dist), 7, name="CrownPeak")
				for m in range(6):
					mx, my = at(m * 60 + 15, 430 * k)
					cyl(x + mx, y + my, top, 170 * k, 6 * k, 620 * k, hazed(NAMED["snow"], dist), 7, name="CrownPeak")
			elif kind == "mesas":
				cyl(hx, hy, top, U(120, 240), U(90, 180), U(90, 320), c, 9, name="Mesa")
			elif kind == "spires":
				cyl(hx, hy, top, U(50, 95), 8 * k, U(280, 640), c, 7, name="Spire")
			elif kind == "pines":
				cyl(hx, hy, top, U(40, 70), 3 * k, U(120, 240), c, 8, name="Pine")
			elif kind == "terraces":
				cyl(x, y, top + j * 95 * k, r * (0.74 - 0.17 * j), r * (0.68 - 0.17 * j), 95 * k, hazed(L["Colour"], dist), 32, name="Terrace")
			elif kind == "stones":
				sx, sy = at(j / n * 360, r * 0.48)
				box(x + sx, y + sy, top, 34 * k, 34 * k, U(120, 210), lrng.uniform(0, 3), hazed(STONE, dist), name="Stone")
			elif kind == "glows":
				ball(hx, hy, top + U(30, 110), 22 * k, 22 * k, 22 * k, c, 1.6, name="Glow")
			elif kind == "dunes":
				rad = U(130, 240)
				ball(hx, hy, top, rad, rad, U(30, 80), c, name="Dune")
			elif kind == "stump":
				wood = hazed((0.46, 0.33, 0.25), dist)
				cyl(x, y, top, 330 * k, 250 * k, 210 * k, wood, 18, name="Stump")
				for m in range(7):
					mx, my = at(m * 51, 330 * k)
					cyl(x + mx, y + my, top, 95 * k, 12 * k, 60 * k, wood, 8, name="StumpRoot")
			elif kind == "roots":
				cyl(hx, hy, top, 40 * k, 24 * k, 300 * k, hazed((0.30, 0.26, 0.24), dist), 9, name="Root")
				ball(hx, hy, top + 310 * k, 130 * k, 130 * k, 60 * k, hazed(NAMED["willow"], dist), name="RootCrown")

# ---- the sea of cloud below, and a few banks rising out of it
cloud_rng = random.Random(5)
sea = cyl(0, 0, S["Clouds"], 30000, 30000, 1, hazed(CLOUD, 4000), 48, name="CloudSea")
for k in range(110):
	a, d = cloud_rng.uniform(0, 360), 500 + cloud_rng.random() ** 0.7 * 15000
	x, y = at(a, d)
	r = cloud_rng.uniform(260, 1100)
	bank = ball(x, y, S["Clouds"] + cloud_rng.uniform(0, 120), r, r, r * cloud_rng.uniform(0.2, 0.42), hazed(CLOUD, d * 0.6), name="CloudBank")
	try:
		bank.visible_shadow = False
	except AttributeError:
		pass

# ---- light and sky
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.0
sun.color = (1.0, 0.95, 0.84)
sun.angle = math.radians(2)
so = bpy.data.objects.new("Sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(52), 0, math.radians(-42))  # from the south-east: lights everything seen from the plots

world = bpy.data.worlds.new("Sky")
world.use_nodes = True
tree = world.node_tree
tree.nodes.clear()
out = tree.nodes.new("ShaderNodeOutputWorld")
bg = tree.nodes.new("ShaderNodeBackground")
coord = tree.nodes.new("ShaderNodeTexCoord")
sep = tree.nodes.new("ShaderNodeSeparateXYZ")
ramp = tree.nodes.new("ShaderNodeValToRGB")
map_range = tree.nodes.new("ShaderNodeMapRange")
map_range.inputs["From Min"].default_value = -0.05
map_range.inputs["From Max"].default_value = 0.75
tree.links.new(coord.outputs["Generated"], sep.inputs[0])
tree.links.new(sep.outputs["Z"], map_range.inputs["Value"])
tree.links.new(map_range.outputs[0], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (*(c**2.2 for c in HAZE), 1)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.05, 0.22, 0.66, 1)
tree.links.new(ramp.outputs[0], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0
fill = tree.nodes.new("ShaderNodeBackground")
fill.inputs["Color"].default_value = (0.42, 0.52, 0.72, 1)
fill.inputs["Strength"].default_value = 0.75
path = tree.nodes.new("ShaderNodeLightPath")
mix = tree.nodes.new("ShaderNodeMixShader")
tree.links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
tree.links.new(fill.outputs[0], mix.inputs[1])
tree.links.new(bg.outputs[0], mix.inputs[2])
tree.links.new(mix.outputs[0], out.inputs["Surface"])
scene.world = world

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.view_settings.view_transform = "Standard"
try:
	scene.eevee.taa_render_samples = 16
except AttributeError:
	pass

cam_data = bpy.data.cameras.new("Cam")
cam_data.sensor_fit = "VERTICAL"
cam_data.clip_start = 0.5
cam_data.clip_end = 60000
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# the character, moved into each view: where the game's over-the-shoulder camera would show them
head = ball(0, 0, 0, 0.85, 0.85, 0.85, FIGURE, name="FigureHead")
body = cyl(0, 0, 0, 1.0, 0.9, 3.6, FIGURE, 12, name="FigureBody")


def shoot(name, pos, target, fov=70, figure=True):
	p, t = Vector(pos), Vector(target)
	d = t - p
	cam.location = p
	cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
	cam_data.angle = math.radians(fov)
	if figure:
		flat = Vector((d.x, d.y, 0)).normalized()
		right = flat.cross(Vector((0, 0, 1)))
		ground = p + flat * 15 + right * 3.2
		z = p.z - 7
		body.location = (ground.x, ground.y, z)
		head.location = (ground.x, ground.y, z + 4.4)
	else:
		body.location = head.location = (0, 0, -5000)
	scene.render.filepath = os.path.join(OUT, name + ".png")
	bpy.ops.render.render(write_still=True)
	print("rendered", name)


yours = P["Yours"]
yx, yy, yz = plot_at[yours]
land1 = S["Lands"][0]
lx, ly = at(land1["Bearing"], land1["Distance"])
EYE = 7

# A. Standing on your own plot, looking across at the Haven: your island, the bridge, the plaza and tower, the Lands behind
px, py = at(yours, P["Ring"] + 66)
ox, oy = at(yours - 90, 30)
px, py = px + ox, py + oy
aim = (px + math.sin(math.radians(4)) * 1000, py + math.cos(math.radians(4)) * 1000, yz + EYE + 1000 * math.tan(math.radians(8)))
shoot("A_your_plot", (px, py, yz + EYE), aim)
# B. On the bridge, the tower growing ahead
bridge_at = (M["Radius"] + P["Ring"] - P["Radius"]) / 2 + 30
bridge_share = (bridge_at - M["Radius"]) / (P["Ring"] - P["Radius"] - M["Radius"])
bx, by = at(yours, bridge_at)
shoot("B_bridge", (bx, by, yz * bridge_share + EYE), (0, 0, 76))
# C. In the plaza, looking through Land 1's arch at Land 1
cx, cy = at(land1["Bearing"], 44)
shoot("C_arch_to_land", (cx, cy, S["Main"]["Plaza"]["Height"] + EYE), (lx, ly, 420))
# D. Along the promenade: the row of arches, the Lands out to the side, the tower behind them
dx, dy = at(-74, 112)
tx, ty = at(26, 170)
shoot("D_promenade", (dx, dy, EYE), (tx, ty, 34))
# E. From the edge of your plot, across the gap to your neighbours' islands
ex, ey = yx + 68, yy + 8
nx, ny = at(P["Bearings"][3], P["Ring"])
shoot("E_neighbours", (ex, ey, yz + EYE), (nx + 40, ny - 34, 12))
# F. The whole composition from high up: the establishing shot
shoot("F_establishing", (640, -1010, 430), (-60, 520, 300), fov=66, figure=False)
# G. From the lawn, between two arches: the whole sky of Lands, stacked one above another
gx, gy = at(-4, 1000)
shoot("G_sky", (0, 146, EYE), (gx, 146 + gy, EYE + 1000 * math.tan(math.radians(15))))
print("tower top", TOWER_TOP)
