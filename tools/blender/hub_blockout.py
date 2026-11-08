"""The hub island blockout (2026-11-08): a floating saucer after the user's two references (the saucer's shape from the
"Silent" poster, the sunny, very-high-up ambience of the tree-stump city painting). Shape only: no buildings on top.
Chunky bevelled clay forms in flat colours; plain context (sky, land far below, clouds, a distant giant tree silhouette)
only so height and scale read.

  blender --background --python tools/blender/hub_blockout.py -- art/hub [--views hero,rim] [--no-render] [--no-plots]

Units are studs. Bearings: 0 = north (+Y), clockwise. The deck's rim is at z = 0. Saves art/hub/hub_blockout.blend and
renders art/hub/blockout/<view>.png.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["art/hub"]
FOLDER = os.path.abspath(ARGS[0])
VIEWS = None
if "--views" in ARGS:
	VIEWS = set(ARGS[ARGS.index("--views") + 1].split(","))
RENDER = "--no-render" not in ARGS
PLOTS = "--no-plots" not in ARGS
TERRACED = "--flat-deck" not in ARGS
OUT = os.path.join(FOLDER, "blockout")
os.makedirs(OUT, exist_ok=True)
TAU = math.tau

# ---- the hub's numbers (studs)
WOBBLE = 0.016  # rings are hand-made: up to about 1.6% out of round, the same wave on every ring so they stay concentric
DOME = 24  # the deck rises this much to its middle
DECK_R = 468  # flat-ish walkable top, about 940 across
BAND_R = 505  # the arcade's face
RECESS_R = 498
STRING = (-16.5, -23)  # string course under the grass lip
ARCADE = (-23, -58)
BASE = (-58, -64.5)
FLANGE_OUT = 523  # the widest point, about 1,050 across
FLANGE_BLOCKS = 40
SKIRT_ROCKS = 76
BAND2_R = 366
BOWL_TOP, BOWL_R, BOWL_DEPTH = -236, 252, 160  # slimmer and shallower, like the poster: bottom at about 0.76 of the radius
DOCKS = [22.5 + 45 * k for k in range(8)]  # bridge heads to the player plots; north (the tree) stays open
FALLS = [(186, 12), (158, 6)]  # waterfalls (bearing, width) pour off the side the hero view sees
PLOT_DISTANCE, PLOT_SCALE, PLOT_DROP = 940, 0.235, -70  # plot islands: centre distance, size vs the hub, deck height (below the hub: you look down on them)
GROUND = -3200
CLOUD_LAYER = -1650
TREE = (32, 42000)  # bearing, distance: the giant tree silhouette
TERRACES = [(150, 26), (300, 12)]  # the deck steps up toward the middle: inside radius r the ground is about z (for the town to climb)
TERRACE_CENTRE, TERRACE_WOBBLE = (0, 90), 0.07  # off-centre toward the back, and less round than the rim

# sRGB clay colours
GRASS = (0.62, 0.79, 0.30)
GRASS_PLOT = (0.56, 0.76, 0.32)
STONE = (0.87, 0.83, 0.73)
STONE_SHADE = (0.80, 0.78, 0.74)
RECESS = (0.52, 0.54, 0.62)
ROCK_DARK = (0.42, 0.46, 0.58)
SOFFIT = (0.38, 0.42, 0.55)
GREY = (0.64, 0.66, 0.70)
UNDER = (0.42, 0.47, 0.60)
KNOB = (0.34, 0.38, 0.52)
WOOD = (0.55, 0.40, 0.28)
WATER = (0.86, 0.95, 1.0)
CLOUD = (0.98, 0.985, 1.0)
GROUND_C = (0.56, 0.80, 0.30)
LAKE = (0.50, 0.66, 0.80)
FIGURE = (0.95, 0.30, 0.20)
HORIZON = (0.80, 0.90, 0.985)
ZENITH = (0.12, 0.36, 0.84)
HAZE_DISTANCE = 15000.0

bpy.ops.wm.read_factory_settings(use_empty=True)
for o in list(bpy.data.objects):
	bpy.data.objects.remove(o)
scene = bpy.context.scene
_mats = {}
_haze_nodes = []  # each material's haze strength, so a view can turn haze off


def lin(c):
	return tuple(x**2.2 for x in c)


def mat(colour, emit=0.0, haze=True):
	key = (tuple(round(x, 3) for x in colour), emit, haze)
	if key in _mats:
		return _mats[key]
	m = bpy.data.materials.new("C%d" % len(_mats))
	m.use_nodes = True
	t = m.node_tree
	t.nodes.clear()
	out = t.nodes.new("ShaderNodeOutputMaterial")
	if emit:
		base = t.nodes.new("ShaderNodeEmission")
		base.inputs["Strength"].default_value = emit
	else:
		base = t.nodes.new("ShaderNodeBsdfDiffuse")
	base.inputs["Color"].default_value = (*lin(colour), 1)
	if not haze:
		t.links.new(base.outputs[0], out.inputs["Surface"])
	else:
		# aerial perspective: mix toward the horizon colour by distance from the camera
		cam = t.nodes.new("ShaderNodeCameraData")
		k = t.nodes.new("ShaderNodeMath")
		k.operation = "MULTIPLY"
		k.inputs[1].default_value = -1.0 / HAZE_DISTANCE
		_haze_nodes.append(k)
		e = t.nodes.new("ShaderNodeMath")
		e.operation = "EXPONENT"
		f = t.nodes.new("ShaderNodeMath")
		f.operation = "SUBTRACT"
		f.inputs[0].default_value = 1.0
		h = t.nodes.new("ShaderNodeEmission")
		h.inputs["Color"].default_value = (*lin(HORIZON), 1)
		mix = t.nodes.new("ShaderNodeMixShader")
		t.links.new(cam.outputs["View Distance"], k.inputs[0])
		t.links.new(k.outputs[0], e.inputs[0])
		t.links.new(e.outputs[0], f.inputs[1])
		t.links.new(f.outputs[0], mix.inputs[0])
		t.links.new(base.outputs[0], mix.inputs[1])
		t.links.new(h.outputs[0], mix.inputs[2])
		t.links.new(mix.outputs[0], out.inputs["Surface"])
	_mats[key] = m
	return m


def falls_material():
	"""the waterfalls: bright at the lip, fading to clear as they fall"""
	m = bpy.data.materials.new("Falls")
	m.use_nodes = True
	t = m.node_tree
	t.nodes.clear()
	out = t.nodes.new("ShaderNodeOutputMaterial")
	em = t.nodes.new("ShaderNodeEmission")
	em.inputs["Color"].default_value = (*lin(WATER), 1)
	em.inputs["Strength"].default_value = 0.95
	clear = t.nodes.new("ShaderNodeBsdfTransparent")
	tc = t.nodes.new("ShaderNodeTexCoord")
	sep = t.nodes.new("ShaderNodeSeparateXYZ")
	mr = t.nodes.new("ShaderNodeMapRange")
	mr.inputs["From Min"].default_value = -1250
	mr.inputs["From Max"].default_value = -200
	mix = t.nodes.new("ShaderNodeMixShader")
	t.links.new(tc.outputs["Object"], sep.inputs[0])
	t.links.new(sep.outputs["Z"], mr.inputs["Value"])
	t.links.new(mr.outputs[0], mix.inputs[0])
	t.links.new(clear.outputs[0], mix.inputs[1])
	t.links.new(em.outputs[0], mix.inputs[2])
	t.links.new(mix.outputs[0], out.inputs["Surface"])
	return m


def finish(bm, name, colour, bevel=0.0, smooth=False, emit=0.0, haze=True, segments=2, recalc=True):
	if recalc:
		bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
	for f in bm.faces:
		f.smooth = smooth
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	me.materials.append(mat(colour, emit, haze))
	o = bpy.data.objects.new(name, me)
	scene.collection.objects.link(o)
	if bevel:
		b = o.modifiers.new("Bevel", "BEVEL")
		b.width = bevel
		b.segments = segments
		b.limit_method = "ANGLE"
		b.angle_limit = math.radians(30)
		b.use_clamp_overlap = True
	return o


class Frame:
	"""An island's frame: centre, scale and its own out-of-round wave. p(bearing, r, z) gives a world point."""

	def __init__(self, centre, scale, seed, amp=WOBBLE):
		rng = random.Random(seed)
		self.c = Vector(centre)
		self.s = scale
		self.amp = amp
		self.waves = [(3, rng.uniform(0, TAU), 0.55), (5, rng.uniform(0, TAU), 0.30), (9, rng.uniform(0, TAU), 0.15)]

	def k(self, th):
		return 1 + self.amp * sum(w * math.sin(n * th + ph) for n, ph, w in self.waves)

	def p(self, th, r, z):
		k = self.k(th) * self.s
		return self.c + Vector((math.sin(th) * r * k, math.cos(th) * r * k, z * self.s))


def lathe(bm, fr, prof, segs):
	"""a surface of revolution; prof runs from the top middle outward and down, so faces point out. r=0 is a pole"""
	rings = []
	for r, z in prof:
		if r < 0.01:
			rings.append(bm.verts.new(fr.p(0, 0, z)))
		else:
			rings.append([bm.verts.new(fr.p(i / segs * TAU, r, z)) for i in range(segs)])
	for a, b in zip(rings, rings[1:]):
		for i in range(segs):
			j = (i + 1) % segs
			if isinstance(a, list) and isinstance(b, list):
				bm.faces.new((a[i], a[j], b[j], b[i]))
			elif isinstance(b, list):
				bm.faces.new((a, b[j], b[i]))
			elif isinstance(a, list):
				bm.faces.new((a[i], a[j], b))


def loop_solid(bm, fr, poly, a0, a1, steps):
	"""a closed (r, z) outline swept from bearing a0 to a1; whole ring when a1 - a0 is a full turn"""
	full = abs(a1 - a0 - TAU) < 1e-6
	n = steps if full else steps + 1
	rings = [[bm.verts.new(fr.p(a0 + (a1 - a0) * i / steps, r, z)) for r, z in poly] for i in range(n)]
	m = len(poly)
	for i in range(steps):
		A, B = rings[i], rings[(i + 1) % n]
		for q in range(m):
			bm.faces.new((A[q], A[(q + 1) % m], B[(q + 1) % m], B[q]))
	if not full:
		bm.faces.new(rings[0])
		bm.faces.new(list(reversed(rings[-1])))


def panel(bm, fr, th0, r_ref, outline, r_in, r_out):
	"""a flat (u, v) outline laid on the curved wall: u along the wall from bearing th0, v = height; extruded radially"""
	front = [bm.verts.new(fr.p(th0 + u / r_ref, r_out, v)) for u, v in outline]
	back = [bm.verts.new(fr.p(th0 + u / r_ref, r_in, v)) for u, v in outline]
	bm.faces.new(front)
	bm.faces.new(list(reversed(back)))
	m = len(outline)
	for q in range(m):
		bm.faces.new((front[q], back[q], back[(q + 1) % m], front[(q + 1) % m]))


def hull(bm, pts):
	vs = [bm.verts.new(p) for p in pts]
	ret = bmesh.ops.convex_hull(bm, input=vs)
	dead = list({g for g in ret["geom_interior"] + ret["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
	if dead:
		bmesh.ops.delete(bm, geom=dead, context="VERTS")


def dome_profile(top_r, dome, rim):
	pts = [(0.0, dome)]
	for i in range(1, 9):
		r = top_r * i / 8
		pts.append((r, dome * (1 - (r / top_r) ** 2)))
	return pts + rim


def bowl_profile(top, a, b, steps=((0.36, 7), (0.70, 7)), knob=0):
	"""a quarter ellipse with stepped rings, ending in a rounded bottom (or a knob)"""
	pts = []
	inset = 0.0
	todo = list(steps)
	n = 22
	for i in range(n + 1):
		t = (math.pi / 2) * i / n
		r = (a - inset) * math.cos(t)
		z = top - b * math.sin(t)
		if knob and r < knob:
			break
		if todo and t >= todo[0][0]:
			pts.append((r, z))
			inset += todo[0][1]
			pts.append(((a - inset) * math.cos(t), z - 1.5))
			todo.pop(0)
			continue
		pts.append((r, z))
	if not knob:
		return pts[:-1] + [(0.0, pts[-1][1])]
	zr = pts[-1][1]
	return pts + [(knob * 0.92, zr - 6), (knob * 0.78, zr - 17), (knob * 0.44, zr - 26), (0.0, zr - 29)]


def build_island(fr, name, grass, arches=True, docks=(), falls=(), drips=26, seed=1, terraced=False):
	rng = random.Random(seed)
	S = fr.s
	segs = 256 if S > 0.5 else 96

	# grass cap: the walkable dome, rolling over the shoulder into a lip
	bm = bmesh.new()
	rim = [(DECK_R, 0.0), (482, -2.6), (495, -7), (504.5, -11.5), (510, -15), (510.5, -17.5), (503, -17.5)]
	if terraced:
		# terraces stepping up toward the middle, each held by a stone retaining wall with a coping
		walls = bmesh.new()
		T = Frame((fr.c.x + TERRACE_CENTRE[0] * fr.s, fr.c.y + TERRACE_CENTRE[1] * fr.s, fr.c.z), fr.s, 31, amp=TERRACE_WOBBLE)
		n = 7
		edges = [r for r, _ in TERRACES]
		heights = [h for _, h in TERRACES] + [2.5]
		start_r, start_z = 0.0, heights[0] + 2
		for i, r in enumerate(edges):
			h, below = heights[i], heights[i + 1]
			prof = [(start_r, start_z)] + [(start_r + (r - 4 - start_r) * q / n, start_z - (start_z - (h - 1)) * (q / n) ** 2) for q in range(1, n + 1)]
			lathe(bm, T, prof, segs)
			loop_solid(walls, T, [(r - 4, h - 1.6), (r + 4, h - 1.6), (r + 4.5, below - 2), (r - 4, below - 2)], 0, TAU, segs)
			loop_solid(walls, T, [(r - 5.5, h - 1.7), (r + 6, h - 1.7), (r + 6, h + 0.6), (r - 5.5, h + 0.6)], 0, TAU, segs)
			start_r, start_z = r + 3, below + (2 if i + 1 < len(edges) else 0)
		# the outer deck runs from the last terrace wall (its own frame) out to the rim (the hub's frame)
		rings = []
		for q in range(n + 1):
			w = q / n
			z = start_z * (1 - w * w)
			rings.append([bm.verts.new(T.p(i / segs * TAU, start_r, z).lerp(fr.p(i / segs * TAU, DECK_R, z), w)) for i in range(segs)])
		for r, z in rim[1:]:
			rings.append([bm.verts.new(fr.p(i / segs * TAU, r, z)) for i in range(segs)])
		for A, B in zip(rings, rings[1:]):
			for i in range(segs):
				j = (i + 1) % segs
				bm.faces.new((A[i], A[j], B[j], B[i]))
		finish(walls, name + "_Terraces", STONE, bevel=1.2)
	else:
		lathe(bm, fr, dome_profile(DECK_R, DOME, rim), segs)
	finish(bm, name + "_Cap", grass, bevel=0.0, recalc=False)

	# drips: grass hanging over the lip in grouped tongues, longest in the middle of each group
	if drips:
		bm = bmesh.new()
		centres = sorted(rng.uniform(0, TAU) for _ in range(drips))
		for c in centres:
			count = rng.randint(3, 7)
			spread = count * rng.uniform(9, 13)
			for d in range(count):
				t = d / max(count - 1, 1)
				u0 = (t - 0.5) * spread
				bell = math.exp(-((t - 0.5) ** 2) / 0.08)
				length = 5 + 26 * bell * rng.uniform(0.6, 1.0)
				w = rng.uniform(5, 11)
				top = -15.5
				bottom = top - length
				out = [(u0 - w / 2, top), (u0 + w / 2, top), (u0 + w * 0.42, bottom + w * 0.45)]
				for k in range(1, 6):
					a = math.pi * k / 6
					out.append((u0 + w * 0.42 * math.cos(a), bottom + w * 0.45 - w * 0.45 * math.sin(a)))
				out.append((u0 - w * 0.42, bottom + w * 0.45))
				panel(bm, fr, c, BAND_R, out, 505.5, 509.5)
		finish(bm, name + "_Drips", grass, bevel=0.7)

	# stone: string course, recess wall, arcade frames, keystones, base course
	bm = bmesh.new()
	loop_solid(bm, fr, [(497, STRING[0]), (508, STRING[0]), (508.5, STRING[1]), (497, STRING[1])], 0, TAU, segs)
	loop_solid(bm, fr, [(497, BASE[0]), (508, BASE[0]), (508, BASE[1]), (497, BASE[1])], 0, TAU, segs)
	if arches:
		h = ARCADE[0] - ARCADE[1]
		radius = 0.52 * h
		pil = 0.33 * h
		bays = round(TAU * BAND_R / (2 * radius + pil))
		bay = TAU * BAND_R / bays
		radius = (bay - pil) / 2
		spring = ARCADE[1] + 0.36 * h
		for k in range(bays):
			th = k / bays * TAU
			panel(bm, fr, th, BAND_R, [(0, ARCADE[1]), (pil, ARCADE[1]), (pil, ARCADE[0]), (0, ARCADE[0])], RECESS_R, BAND_R)
			arch = [(pil, spring)]
			cx = pil + radius
			for q in range(1, 12):
				a = math.pi - math.pi * q / 12
				arch.append((cx + radius * math.cos(a), spring + radius * math.sin(a)))
			arch += [(bay, spring), (bay, ARCADE[0]), (pil, ARCADE[0])]
			panel(bm, fr, th, BAND_R, arch, RECESS_R, BAND_R)
			crown = spring + radius
			panel(bm, fr, th, BAND_R, [(cx - 3.2, crown - 4), (cx + 3.2, crown - 4), (cx + 3.8, ARCADE[0] + 0.5), (cx - 3.8, ARCADE[0] + 0.5)], BAND_R - 1, BAND_R + 2.4)
	finish(bm, name + "_Stone", STONE, bevel=1.1)

	bm = bmesh.new()
	lathe(bm, fr, [(RECESS_R, ARCADE[0]), (RECESS_R, ARCADE[1])], segs)
	finish(bm, name + "_Recess", RECESS if arches else STONE_SHADE, recalc=False)

	# flange: the widest ring, chunky blocks with small dark joints
	bm = bmesh.new()
	n = FLANGE_BLOCKS if S > 0.5 else 16
	gap = math.radians(0.55 if S > 0.5 else 1.4)
	for k in range(n):
		a0 = k / n * TAU + gap / 2
		a1 = (k + 1) / n * TAU - gap / 2
		o = rng.uniform(-2.2, 2.2)
		d = rng.uniform(-2.0, 2.0)
		poly = [(496, -62), (513, -63.5), (FLANGE_OUT + o, -67.5), (FLANGE_OUT + 0.5 + o, -77 + d * 0.3), (514 + o * 0.5, -84 + d), (496, -88 + d)]
		loop_solid(bm, fr, poly, a0, a1, 6 if S > 0.5 else 3)
	finish(bm, name + "_Flange", STONE_SHADE, bevel=2.2)
	bm = bmesh.new()
	lathe(bm, fr, [(497, -61), (497, -89)], segs)  # joints show this darker core
	finish(bm, name + "_FlangeCore", RECESS, recalc=False)

	# soffit and ragged rock skirt under the flange
	bm = bmesh.new()
	lathe(bm, fr, [(497, -86), (470, -97), (420, -125), (378, -148), (372, -150)], segs)
	finish(bm, name + "_Soffit", SOFFIT, recalc=False)
	bm = bmesh.new()
	rocks = SKIRT_ROCKS if S > 0.5 else 26
	ph = rng.uniform(0, TAU)
	for k in range(rocks):
		th = (k + rng.uniform(-0.25, 0.25)) / rocks * TAU
		bottom = -150 + 20 * math.sin(3 * th + ph) + 9 * math.sin(7 * th + 2 * ph) + rng.uniform(-6, 6)
		top = -84
		half = TAU * 480 / rocks * 0.62
		pts = []
		for zf in (0.0, 0.35, 0.7, 1.0):
			z = top + (bottom - top) * zf
			taper = 1 - 0.55 * zf**1.5
			r_out = 494 - 34 * zf**1.3
			r_in = 455 - 20 * zf
			for uf in (-1, -0.4, 0.4, 1):
				u = uf * half * taper * rng.uniform(0.8, 1.1)
				for r in (r_in, r_out + rng.uniform(-3, 2)):
					pts.append(fr.p(th + u / r, r, z + rng.uniform(-3, 3)))
		pts.append(fr.p(th, 470 - 30 * 1, bottom - rng.uniform(4, 10)))
		hull(bm, pts)
	finish(bm, name + "_Skirt", ROCK_DARK, recalc=True)

	# lower bands, the stepped bowl and the knob
	bm = bmesh.new()
	prof = [(372, -150), (366, -152), (366, -167), (360, -169), (360, -173), (366, -175), (366, -189), (360, -191), (360, -195), (366, -197), (366, -204), (360, -208), (312, -208)]
	lathe(bm, fr, prof, segs)
	finish(bm, name + "_Band2", GREY, bevel=1.5, recalc=False)
	bm = bmesh.new()
	prof = [(312, -208), (305, -211), (305, -227), (298, -232)] + bowl_profile(BOWL_TOP, BOWL_R, BOWL_DEPTH, steps=((0.36, 7), (0.70, 7)) if S > 0.5 else ())
	lathe(bm, fr, prof, segs)
	finish(bm, name + "_Bowl", UNDER, bevel=2.0, recalc=False)

	# docks: stone platforms jutting from the rim, each a bridge head
	if docks:
		bm = bmesh.new()
		for b in docks:
			th = math.radians(b)
			# deck slab, swept so it follows the bearing
			for r0, r1, z0, z1 in ((462, 562, -11, -3),):
				pts = []
				for u in (-23, 23):
					for r in (r0, r1):
						for z in (z0, z1):
							pts.append(fr.p(th + u / r, r, z))
				hull(bm, pts)
			# buttress pier on the arcade and two brackets under the deck
			pts = []
			for u in (-17, 17):
				for r in (BAND_R - 2, BAND_R + 9):
					for z in (-11, -66):
						pts.append(fr.p(th + u / r, r, z))
			hull(bm, pts)
			for u in (-15, 15):
				pts = []
				for du in (-4, 4):
					for r, z in ((BAND_R + 8, -64), (BAND_R + 8, -11), (552, -11)):
						pts.append(fr.p(th + (u + du) / r, r, z))
				hull(bm, pts)
			# gate posts at the bridge head
			for u in (-17, 17):
				pts = []
				for du in (-3.5, 3.5):
					for r in (548, 556):
						for z in (-3, 13):
							pts.append(fr.p(th + (u + du) / r, r, z))
				hull(bm, pts)
		finish(bm, name + "_Docks", STONE, bevel=1.4)

	# waterfalls: a ribbon arcing clear of the flange, widening as it falls
	if falls:
		bm = bmesh.new()
		for b, width in falls:
			th = math.radians(b)
			rows = []
			for i in range(40):
				drop = (i / 39) ** 1.6 * 1300
				r = 510 + 3.1 * math.sqrt(drop + 1) + drop * 0.02
				w = width * (1 + drop * 0.0025)
				rows.append([bm.verts.new(fr.p(th + u * w / r, r, -15 - drop)) for u in (-1, 1)])
			for a, c in zip(rows, rows[1:]):
				bm.faces.new((a[0], a[1], c[1], c[0]))
		o = finish(bm, name + "_Falls", WATER, emit=0.95, recalc=False)
		o.data.materials[0] = falls_material()


def build_plot(k, bearing):
	"""a player's plot island: the same family, simpler, lower than the hub so you look down on what others built"""
	th = math.radians(bearing)
	cx, cy = math.sin(th) * PLOT_DISTANCE, math.cos(th) * PLOT_DISTANCE
	fr = Frame((cx, cy, PLOT_DROP), PLOT_SCALE, 50 + k, amp=0.03)
	build_island(fr, "Plot%d" % (k + 1), GRASS_PLOT, arches=False, drips=8, seed=50 + k)
	# rope bridge from the dock's gate to the plot's rim, sagging a little
	hub = Frame((0, 0, 0), 1.0, 7)
	a = hub.p(th, 556, -3)
	near = Vector((cx, cy, PLOT_DROP)) - Vector((math.sin(th), math.cos(th), 0)) * (DECK_R * PLOT_SCALE - 2)
	b = Vector((near.x, near.y, PLOT_DROP + 0.2))
	bm = bmesh.new()
	run = b - a
	length = run.length
	fwd = run.normalized()
	side = fwd.cross(Vector((0, 0, 1))).normalized()
	planks = int(length / 3.2)
	for i in range(planks):
		t = (i + 0.5) / planks
		c = a + run * t - Vector((0, 0, 7 * math.sin(math.pi * t)))
		pts = []
		for s in (-6.5, 6.5):
			for f in (-1.3, 1.3):
				for z in (-1.0, 0.0):
					pts.append(c + side * (s + random.uniform(-0.3, 0.3)) + fwd * f + Vector((0, 0, z)))
		hull(bm, pts)
	for s in (-6.8, 6.8):
		for i in range(planks):
			t0, t1 = i / planks, (i + 1) / planks
			p0 = a + run * t0 - Vector((0, 0, 7 * math.sin(math.pi * t0))) + side * s + Vector((0, 0, 3.6))
			p1 = a + run * t1 - Vector((0, 0, 7 * math.sin(math.pi * t1))) + side * s + Vector((0, 0, 3.6))
			pts = [p + side * dx + Vector((0, 0, dz)) for p in (p0, p1) for dx in (-0.35, 0.35) for dz in (-0.35, 0.35)]
			hull(bm, pts)
	finish(bm, "Plot%d_Bridge" % (k + 1), WOOD, recalc=True)


random.seed(3)
hub = Frame((0, 0, 0), 1.0, 7)
build_island(hub, "Hub", GRASS, arches=True, docks=DOCKS, falls=FALLS, drips=30, seed=11, terraced=TERRACED)
if PLOTS:
	for k, b in enumerate(DOCKS):
		build_plot(k, b)

# ---- context: land far below, lakes, cloud layers, the giant tree
ctx = bpy.data.collections.new("Context")
scene.collection.children.link(ctx)


def to_ctx(o):
	scene.collection.objects.unlink(o)
	ctx.objects.link(o)
	return o


bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=110000)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, GROUND))
to_ctx(finish(bm, "Ground", GROUND_C, recalc=False))
lrng = random.Random(21)
bm = bmesh.new()
for _ in range(16):
	d = lrng.uniform(4000, 30000)
	a = lrng.uniform(0, TAU)
	rx, ry = lrng.uniform(400, 1800), lrng.uniform(250, 900)
	ret = bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1)
	vs = ret["verts"]
	rot = lrng.uniform(0, TAU)
	for v in vs:
		x, y = v.co.x * rx, v.co.y * ry
		v.co = Vector((math.sin(a) * d + x * math.cos(rot) - y * math.sin(rot), math.cos(a) * d + x * math.sin(rot) + y * math.cos(rot), GROUND + 2))
to_ctx(finish(bm, "Lakes", LAKE, recalc=False))


def puff(bm, c, r, rng):
	ret = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
	for v in ret["verts"]:
		x, y, z = v.co
		z = max(z, -0.25)
		v.co = Vector((c[0] + x * r * 1.25, c[1] + y * r * rng.uniform(1.0, 1.3), c[2] + z * r * 0.42))


crng = random.Random(5)
bm = bmesh.new()
# clouds hugging the hub's middle, as in the poster
for b in (105, 248, 292):
	a = math.radians(b) + crng.uniform(-0.1, 0.1)
	d = crng.uniform(470, 560)
	z = crng.uniform(-330, -270)
	c = (math.sin(a) * d, math.cos(a) * d, z)
	big = crng.uniform(40, 70)
	puff(bm, c, big, crng)
	for _ in range(crng.randint(3, 5)):
		o = (c[0] + crng.uniform(-1.6, 1.6) * big, c[1] + crng.uniform(-1.6, 1.6) * big, c[2] + crng.uniform(-0.2, 0.5) * big)
		puff(bm, o, big * crng.uniform(0.45, 0.8), crng)
# a broken cloud layer far below: the land shows through the gaps
for k in range(80):
	a = crng.uniform(0, TAU)
	d = 1600 + crng.random() ** 0.8 * 18000
	c = (math.sin(a) * d, math.cos(a) * d, CLOUD_LAYER + crng.uniform(-150, 150))
	big = crng.uniform(300, 700)
	puff(bm, c, big, crng)
	for _ in range(crng.randint(2, 5)):
		o = (c[0] + crng.uniform(-1.8, 1.8) * big, c[1] + crng.uniform(-1.8, 1.8) * big, c[2] + crng.uniform(-0.1, 0.4) * big)
		puff(bm, o, big * crng.uniform(0.4, 0.8), crng)
to_ctx(finish(bm, "Clouds", CLOUD, smooth=True, recalc=False))

# the giant tree: a flat-shaded silhouette, darker blue at the top and paling into the haze below
tb, td = TREE
tx, ty = math.sin(math.radians(tb)) * td, math.cos(math.radians(tb)) * td
trng = random.Random(9)
bm = bmesh.new()
ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=2600, radius2=1300, depth=4000)
bmesh.ops.translate(bm, verts=ret["verts"], vec=(0, 0, 2000))  # root flare, 0 to 4000
ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=1300, radius2=950, depth=9000)
bmesh.ops.translate(bm, verts=ret["verts"], vec=(0, 0, 8400))  # trunk, 3900 to 12900
for k in range(5):
	a = k / 5 * TAU + 0.4
	ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=650, radius2=200, depth=5200)
	for v in ret["verts"]:
		x, y, z = v.co.x, v.co.y, v.co.z + 2600  # 0 to 5200 along the branch
		lean = z / 5200
		v.co = Vector((x + math.cos(a) * 4200 * lean, y + math.sin(a) * 2100 * lean, 8600 + z * 0.75))
for k in range(18):
	a = trng.uniform(0, TAU)
	rad = trng.uniform(0, 1) ** 0.6 * 8500
	c = (math.cos(a) * rad, math.sin(a) * rad * 0.5, 11500 + trng.uniform(-1800, 2600) - rad * 0.25)
	r = trng.uniform(2600, 4200)
	ret = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
	for v in ret["verts"]:
		x, y, z = v.co
		v.co = Vector((c[0] + x * r, c[1] + y * r, c[2] + z * r * 0.62))
for v in bm.verts:
	v.co = Vector((v.co.x + tx, v.co.y + ty, v.co.z))
tree_me = bpy.data.meshes.new("GiantTree")
bm.to_mesh(tree_me)
bm.free()
tm = bpy.data.materials.new("TreeSilhouette")
tm.use_nodes = True
t = tm.node_tree
t.nodes.clear()
out = t.nodes.new("ShaderNodeOutputMaterial")
em = t.nodes.new("ShaderNodeEmission")
tc = t.nodes.new("ShaderNodeTexCoord")
sep = t.nodes.new("ShaderNodeSeparateXYZ")
mr = t.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = -1200
mr.inputs["From Max"].default_value = 15000
ramp = t.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (*lin((0.74, 0.85, 0.97)), 1)
ramp.color_ramp.elements[1].color = (*lin((0.42, 0.57, 0.86)), 1)
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[1].position = 0.8
t.links.new(tc.outputs["Object"], sep.inputs[0])
t.links.new(sep.outputs["Z"], mr.inputs["Value"])
t.links.new(mr.outputs[0], ramp.inputs["Fac"])
t.links.new(ramp.outputs[0], em.inputs["Color"])
t.links.new(em.outputs[0], out.inputs["Surface"])
tree_me.materials.append(tm)
tree = bpy.data.objects.new("GiantTree", tree_me)
tree.location = (0, 0, GROUND)
ctx.objects.link(tree)

# ---- light and sky
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 3.4
sun.color = (1.0, 0.96, 0.88)
sun.angle = math.radians(1.5)
so = bpy.data.objects.new("Sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(45), 0, math.radians(-65))  # from the west-south-west, 45 degrees up: lights the hero side

world = bpy.data.worlds.new("Sky")
world.use_nodes = True
wt = world.node_tree
wt.nodes.clear()
wo = wt.nodes.new("ShaderNodeOutputWorld")
bg = wt.nodes.new("ShaderNodeBackground")
coord = wt.nodes.new("ShaderNodeTexCoord")
sep = wt.nodes.new("ShaderNodeSeparateXYZ")
mr = wt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = -0.02
mr.inputs["From Max"].default_value = 0.8
ramp = wt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (*lin(HORIZON), 1)
ramp.color_ramp.elements[1].color = (*lin(ZENITH), 1)
ramp.color_ramp.interpolation = "EASE"
wt.links.new(coord.outputs["Generated"], sep.inputs[0])
wt.links.new(sep.outputs["Z"], mr.inputs["Value"])
wt.links.new(mr.outputs[0], ramp.inputs["Fac"])
wt.links.new(ramp.outputs[0], bg.inputs["Color"])
fill = wt.nodes.new("ShaderNodeBackground")
fill.inputs["Color"].default_value = (0.46, 0.56, 0.78, 1)
fill.inputs["Strength"].default_value = 0.8
lp = wt.nodes.new("ShaderNodeLightPath")
mix = wt.nodes.new("ShaderNodeMixShader")
wt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
wt.links.new(fill.outputs[0], mix.inputs[1])
wt.links.new(bg.outputs[0], mix.inputs[2])
wt.links.new(mix.outputs[0], wo.inputs["Surface"])
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
cam_data.clip_end = 200000
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# a player-sized stand-in (5.2 studs)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=1.0, radius2=0.9, depth=3.6)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 1.8))
ret = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.85)
bmesh.ops.translate(bm, verts=ret["verts"], vec=(0, 0, 4.35))
figure = finish(bm, "Figure", FIGURE, smooth=True, haze=False, recalc=False)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(FOLDER, "hub_blockout.blend"))


def shoot(name, pos, target, fov=70, fig=None, ortho=None, context=True, haze=True):
	if VIEWS and name not in VIEWS:
		return
	for k in _haze_nodes:
		k.inputs[1].default_value = -1.0 / HAZE_DISTANCE if haze else 0.0
	p, t = Vector(pos), Vector(target)
	cam.location = p
	cam.rotation_euler = (t - p).to_track_quat("-Z", "Y").to_euler()
	if ortho:
		cam_data.type = "ORTHO"
		cam_data.ortho_scale = ortho
	else:
		cam_data.type = "PERSP"
		cam_data.angle = math.radians(fov)
	if fig:
		figure.location = fig
		figure.hide_render = False
	else:
		figure.hide_render = True
	ctx.hide_render = not context
	scene.render.filepath = os.path.join(OUT, name + ".png")
	bpy.ops.render.render(write_still=True)
	print("rendered", name)


def at(bearing, r, z):
	a = math.radians(bearing)
	return (math.sin(a) * r, math.cos(a) * r, z)


def ground(x, y):
	"""the walkable surface under (x, y), by a ray from above (the figure is parked out of the way first)"""
	figure.location = (0, 0, 90000)
	dg = bpy.context.evaluated_depsgraph_get()
	hit, loc, *_ = scene.ray_cast(dg, Vector((x, y, 500)), Vector((0, 0, -1)))
	return Vector((x, y, loc.z if hit else 0.0))


def player_view(name, foot, look_bearing, pitch, back=15, fov=70):
	"""the game's over-the-shoulder camera: 15 studs behind and 7.5 up from the feet"""
	d = Vector((math.sin(math.radians(look_bearing)), math.cos(math.radians(look_bearing)), 0))
	eye = foot - d * back + Vector((0, 0, 7.5))
	shoot(name, eye, eye + d * 1000 + Vector((0, 0, 1000 * math.tan(math.radians(pitch)))), fov=fov, fig=foot)


if RENDER:
	# like the poster: from a little below, between two plots, the saucer against the sky
	shoot("hero", at(180, 2050, -300), (0, 0, -150), fov=36)
	# like the painting: very high, looking down past the hub at the land and the tree
	cam_at = Vector(at(205, 1550, 760))
	look = Vector((math.sin(math.radians(13)), math.cos(math.radians(13)), -math.tan(math.radians(15))))
	shoot("high", cam_at, cam_at + look * 1000, fov=74)
	# on the grass lip at the rim: the rim curving away right, a dock and its bridge, a plot below, the drop, the tree
	p = at(4, 490, 0)
	player_view("edge", ground(p[0], p[1]), 30, -17)
	# part way along a bridge, looking back at the hub's wall: the arcade and drips at player scale
	a, b = Vector(at(22.5, 556, -3)), Vector(at(22.5, PLOT_DISTANCE - DECK_R * PLOT_SCALE + 2, PLOT_DROP))
	mid = a.lerp(b, 0.45)
	player_view("bridge", Vector((mid.x, mid.y, mid.z - 7 * math.sin(math.pi * 0.45) + 0.2)), 22.5 + 180 + 38, 4)
	# across the deck toward the terraces and the far rim
	p = at(180, 380, 0)
	player_view("deck", ground(p[0], p[1]), 0, 2)
	# from below and outside: the underside's steps, skirt and the plots
	shoot("below", at(120, 1150, -900), (0, 0, -260), fov=58)
	# side elevation for proportions (no context, no haze)
	shoot("side", (0, -6000, -200), (0, 0, -200), ortho=1160, context=False, haze=False)  # 1160 studs tall = 0.776 px a stud
