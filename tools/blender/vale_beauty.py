"""Verdant Vale beauty pass (docs/style/botw-study.md, docs/lands/land1-verdant-vale.md): the block-out's terrain dressed
in the BotW-study look. Ground colours by zone, dense grass and flowers near the camera (instanced, like BotW and Roblox
terrain grass), forests and groves, mossy boulders, the castle town of Brightwater, the Gate with its light beam, the
ruins, the bandit camp, the cave, the stone circle, far mountain layers and a floating island. Renders hero views.

  blender --background --python tools/blender/vale_beauty.py -- art/lands/land1/map.json <out dir> [--views a,b] [--quick] [--save]

Per view: <out>/<view>/beauty.png, depth.png, placements.json (camera meta for tools/art/look_post.py). Settings live in
map.json's "Beauty" block. Map coordinates: x east, y south; Blender: X east, Y north, Z up.
"""

import json
import math
import os
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
import kit  # noqa: E402
import kit_vale as kv  # noqa: E402
import land_blockout as lb  # noqa: E402
import sky_paint  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(ARGS[1])
FLAGS = ARGS[2:]
M = lb.M
BT = M["Beauty"]
T0 = time.time()
R = random.Random(BT.get("Seed", 7))


def log(*a):
	print(f"[vale {time.time() - T0:6.1f}s]", *a, flush=True)


def flag_value(name, default=None):
	return FLAGS[FLAGS.index(name) + 1] if name in FLAGS else default


def lin(h):
	return np.array(kit.to_linear(kit.srgb(h)))


def smoothstep(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def bell(t):
	t = np.clip(t, 0, 1)
	return 0.5 * (1 + np.cos(np.pi * t))


# ---------------------------------------------------------------- ground


class Ground:
	def __init__(self):
		lb.STEP = BT.get("Step", 2.5)
		for zname, ov in BT.get("ZoneOverrides", {}).items():
			lb.B["Zones"].setdefault(zname, {}).update(ov)
		self.xs, self.ys, self.X, self.Y, self.Z, self.zone, self.water, _ = lb.build_heights()
		X, Y = self.X, self.Y
		self.d_path = np.full_like(X, 1e9)
		for line in M["Paths"]:
			self.d_path = np.minimum(self.d_path, lb.seg_dist(X, Y, line))
		hub = self.hub = next(p for p in M["Places"] if p["Icon"] == "castle")["At"]
		isl = lb.B.get("Island", {"Radius": 90, "Height": 7, "Moat": 26})
		self.island = isl
		self.dh = np.hypot(X - hub[0], Y - hub[1])
		rw = lb.B.get("RiverWidth", 28)
		river = lb.seg_dist(X, Y, M["River"])
		moat = np.abs(self.dh - isl["Radius"] - isl["Moat"] / 2 - 4)
		self.d_water = np.minimum(river, moat * (rw / isl["Moat"])) - rw / 2
		gy, gx = np.gradient(self.Z, lb.STEP)
		self.slope = np.hypot(gx, gy)
		self.water_z = BT.get("WaterLevel", -1.5)
		log(f"ground {X.shape[1]} x {X.shape[0]}, height {self.Z.min():.0f}..{self.Z.max():.0f}")

	def z(self, x, y):
		fx = (x - self.xs[0]) / lb.STEP
		fy = (y - self.ys[0]) / lb.STEP
		i, j = int(np.clip(fx, 0, len(self.xs) - 2)), int(np.clip(fy, 0, len(self.ys) - 2))
		u, v = min(1.0, max(0.0, fx - i)), min(1.0, max(0.0, fy - j))
		Z = self.Z
		return float(Z[j, i] * (1 - u) * (1 - v) + Z[j, i + 1] * u * (1 - v) + Z[j + 1, i] * (1 - u) * v + Z[j + 1, i + 1] * u * v)

	def at(self, arr, x, y):
		i = int(np.clip(round((x - self.xs[0]) / lb.STEP), 0, len(self.xs) - 1))
		j = int(np.clip(round((y - self.ys[0]) / lb.STEP), 0, len(self.ys) - 1))
		return arr[j, i]

	def zone_name(self, x, y):
		k = int(self.at(self.zone, x, y))
		return M["Zones"][k]["Name"] if k >= 0 else None


def zone_table(G, key, default):
	"""per-vertex values from the Beauty "Ground" zone table (zone -1 = the grassland between zones)"""
	gc = BT["Ground"]
	rows = [gc["Default"].get(key, default)] + [gc["Zones"].get(z["Name"], {}).get(key, gc["Default"].get(key, default)) for z in M["Zones"]]
	if isinstance(rows[0], str):
		tab = np.array([lin(h) for h in rows])
	else:
		tab = np.array(rows, float)
	return tab[G.zone + 1]


def ground_colours(G, ao):
	gc = BT["Ground"]
	X, Y, Z = G.X, G.Y, G.Z
	A, B, Dry = zone_table(G, "A", "8fbf45"), zone_table(G, "B", "6fa83a"), zone_table(G, "Dry", "c9b85a")
	dry_amt = zone_table(G, "DryAmount", 0.3)
	n1 = lb.noise(X, Y, gc.get("PatchScale", 70), 21) * 0.5 + 0.5
	col = A * (1 - n1[..., None]) + B * n1[..., None]
	n2 = lb.noise(X, Y, gc.get("DryScale", 34), 22) * 0.5 + 0.5
	dry = (smoothstep(0.58, 0.85, n2) * dry_amt)[..., None]
	col = col * (1 - dry) + Dry * dry
	col *= (1 + lb.noise(X, Y, 7, 23) * gc.get("Grain", 0.07))[..., None]
	# rock on steep ground, in strata bands, mossy where it levels off
	rock = smoothstep(gc.get("RockFrom", 0.55), gc.get("RockTo", 0.95), G.slope)[..., None]
	band = 0.5 + 0.5 * np.sin(Z * 0.55 + lb.noise(X, Y, 40, 24) * 2.5)
	rc = lin(gc["RockA"]) * (1 - band[..., None]) + lin(gc["RockB"]) * band[..., None]
	col = col * (1 - rock) + rc * rock
	# paths: warm dirt with a soft, wobbly edge and grass creeping in
	e = G.d_path - gc.get("PathHalf", 3.2) + lb.noise(X, Y, 6, 25) * 1.1
	w = smoothstep(1.4, -1.2, e)[..., None] * (1 - rock)
	dn = lb.noise(X, Y, 9, 26) * 0.5 + 0.5
	dirt = lin(gc["Dirt"]) * (1 - dn[..., None]) + lin(gc["DirtDark"]) * dn[..., None]
	creep = smoothstep(0.55, 0.8, lb.noise(X, Y, 3.5, 27) * 0.5 + 0.5)[..., None] * 0.6
	col = col * (1 - w * (1 - creep)) + dirt * w * (1 - creep)
	# river banks: a band of pale sand and pebbles; under the water a dark teal bed
	bank = (smoothstep(6.5, 1.0, G.d_water) * (G.d_water > 0))[..., None]
	col = col * (1 - bank) + lin(gc["Bank"]) * bank
	col[G.d_water < 0] = lin(gc["Bed"])
	# the town island is cobbled where the town stands
	town = smoothstep(G.island["Radius"] - 2, G.island["Radius"] - 12, G.dh)[..., None]
	col = col * (1 - town) + lin(gc.get("Cobble", "b5a88f")) * town * (0.9 + 0.1 * dn[..., None]) + col * 0 * town
	# painted occlusion at the feet of trees, rocks and buildings
	occ = np.ones(X.shape)
	for x, y, rad, k in ao:
		i0, i1 = np.searchsorted(G.xs, [x - rad, x + rad])
		j0, j1 = np.searchsorted(G.ys, [y - rad, y + rad])
		if i1 > i0 and j1 > j0:
			d = np.hypot(X[j0:j1, i0:i1] - x, Y[j0:j1, i0:i1] - y) / rad
			occ[j0:j1, i0:i1] *= 1 - k * bell(d)
	col *= occ[..., None]
	return col


def ground_mesh(G, coll, ao):
	X, Y, Z = G.X, G.Y, G.Z
	ny, nx = X.shape
	verts = np.stack([X, -Y, Z], -1).reshape(-1, 3)
	idx = np.arange(nx * ny).reshape(ny, nx)
	quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
	mesh = bpy.data.meshes.new("Ground")
	mesh.vertices.add(len(verts))
	mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
	mesh.loops.add(len(quads) * 4)
	mesh.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
	mesh.polygons.add(len(quads))
	mesh.polygons.foreach_set("loop_start", np.arange(0, len(quads) * 4, 4, dtype=np.int32))
	mesh.update(calc_edges=True)
	mesh.polygons.foreach_set("use_smooth", np.ones(len(quads), bool))
	col = ground_colours(G, ao).reshape(-1, 3)
	attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	attr.data.foreach_set("color", np.concatenate([col, np.ones((len(col), 1))], 1).astype(np.float32).ravel())
	for name in ("grass", "flowers", "pebbles"):
		mesh.attributes.new(name, "FLOAT", "POINT")
	mesh.materials.append(kit.vertex_material())
	obj = bpy.data.objects.new("Ground", mesh)
	coll.objects.link(obj)
	return obj


def water_plane(G, coll):
	m = bpy.data.materials.new("Water")
	m.use_nodes = True
	nt = m.node_tree
	bsdf = nt.nodes.get("Principled BSDF")
	bsdf.inputs["Base Color"].default_value = (*lin(BT.get("WaterColour", "2f7d86")), 1)
	bsdf.inputs["Roughness"].default_value = 0.06
	if "Specular IOR Level" in bsdf.inputs:
		bsdf.inputs["Specular IOR Level"].default_value = 0.6
	wm = bpy.data.meshes.new("Water")
	S = 4000
	wm.from_pydata([(-S, -S, G.water_z), (S, -S, G.water_z), (S, S, G.water_z), (-S, S, G.water_z)], [], [(0, 1, 2, 3)])
	wm.materials.append(m)
	coll.objects.link(bpy.data.objects.new("Water", wm))


# ---------------------------------------------------------------- instanced grass and flowers (geometry nodes)


def scatter_modifier(obj, name, attr, coll, density_max, scale=(0.75, 1.3), seed=0):
	ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
	ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
	ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
	n, link = ng.nodes, ng.links.new
	gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
	dist = n.new("GeometryNodeDistributePointsOnFaces")
	dist.distribute_method = "RANDOM"
	dist.inputs["Seed"].default_value = seed
	na = n.new("GeometryNodeInputNamedAttribute")
	na.data_type = "FLOAT"
	na.inputs["Name"].default_value = attr
	mul = n.new("ShaderNodeMath")
	mul.operation = "MULTIPLY"
	mul.inputs[1].default_value = density_max
	link(na.outputs["Attribute"], mul.inputs[0])
	link(mul.outputs["Value"], dist.inputs["Density"])
	link(gi.outputs[0], dist.inputs["Mesh"])
	ci = n.new("GeometryNodeCollectionInfo")
	ci.inputs["Collection"].default_value = coll
	ci.inputs["Separate Children"].default_value = True
	ci.inputs["Reset Children"].default_value = True
	iop = n.new("GeometryNodeInstanceOnPoints")
	iop.inputs["Pick Instance"].default_value = True
	rot = n.new("FunctionNodeRandomValue")
	rot.data_type = "FLOAT_VECTOR"
	rot.inputs[0].default_value = (0, 0, 0)
	rot.inputs[1].default_value = (0.12, 0.12, math.tau)
	rot.inputs["Seed"].default_value = seed + 1
	sc = n.new("FunctionNodeRandomValue")
	sc.data_type = "FLOAT"
	sc.inputs[2].default_value = scale[0]
	sc.inputs[3].default_value = scale[1]
	sc.inputs["Seed"].default_value = seed + 2
	idx = n.new("FunctionNodeRandomValue")
	idx.data_type = "INT"
	idx.inputs[4].default_value = 0
	idx.inputs[5].default_value = 99
	idx.inputs["Seed"].default_value = seed + 3
	link(dist.outputs["Points"], iop.inputs["Points"])
	link(ci.outputs[0], iop.inputs["Instance"])
	link(idx.outputs[2], iop.inputs["Instance Index"])
	link(rot.outputs[0], iop.inputs["Rotation"])
	link(sc.outputs[1], iop.inputs["Scale"])
	join = n.new("GeometryNodeJoinGeometry")
	link(iop.outputs["Instances"], join.inputs[0])
	link(gi.outputs[0], join.inputs[0])
	link(join.outputs[0], go.inputs[0])
	mod = obj.modifiers.new(name, "NODES")
	mod.node_group = ng
	return mod


def clump_collections():
	"""grass and flower clumps: kept in collections not linked to the scene, so only their instances render"""
	cols = {}
	gr = bpy.data.collections.new("GrassClumps")
	for k in range(4):
		gr.objects.link(kv.field_grass(f"Grass{k}", 300 + k, blades=14, height=BT.get("GrassHeight", 1.25)))
	for k in range(2):
		gr.objects.link(kv.field_grass(f"GrassTall{k}", 320 + k, blades=10, height=BT.get("GrassHeight", 1.25) * 1.7))
	cols["grass"] = gr
	fl = bpy.data.collections.new("FlowerClumps")
	for k, kind in enumerate(("white", "white", "yellow", "white")):
		fl.objects.link(kit.flowers(f"Flower{k}", 400 + k, kind=kind, count=12 if kind == "white" else 4))
	blue = kit.flowers("FlowerBlue", 410, kind="white", count=9)
	for lp in blue.data.color_attributes["Col"].data:  # a blue variety: BotW's meadows have blue and yellow dots
		c = lp.color
		if c[0] > 0.6 and c[1] > 0.6:
			lp.color = (*kit.to_linear(kit.srgb("6f8fe0")), 1)
	fl.objects.link(blue)
	cols["flowers"] = fl
	pb = bpy.data.collections.new("Pebbles")
	for k in range(3):
		pb.objects.link(kit.boulder(f"Pebble{k}", 450 + k, size=(0.7, 0.55, 0.4)))
	cols["pebbles"] = pb
	return cols


def set_density(G, ground, cam_map, fwd_map, view):
	"""write this view's grass/flower/pebble density into the ground mesh: zone amount x distance falloff x in front"""
	X, Y = G.X, G.Y
	dx, dy = X - cam_map[0], Y - cam_map[1]
	d = np.hypot(dx, dy) + 1e-6
	front = smoothstep(-0.35, 0.1, (dx * fwd_map[0] + dy * fwd_map[1]) / d)
	gd = BT["GrassDensity"]
	maxd = view.get("GrassDist", gd.get("Dist", 230))
	fall = np.clip(1 - d / maxd, 0, 1) ** gd.get("FallPower", 0.9)
	base = zone_table(G, "Grass", 0.9)
	clear = (G.d_water > 1.5) & (G.slope < 0.9) & (G.dh > G.island["Radius"] - 2)
	path = smoothstep(0.0, 2.5, G.d_path - BT["Ground"].get("PathHalf", 3.2))
	g = base * fall * front * clear * (0.15 + 0.85 * path)
	fl = smoothstep(0.55, 0.8, lb.noise(X, Y, 18, 61) * 0.5 + 0.5) * clear * front * np.clip(1 - d / (maxd * 0.6), 0, 1) * (G.zone != 2)
	pebbles = (smoothstep(3.0, 0.0, np.abs(G.d_path - BT["Ground"].get("PathHalf", 3.2))) + smoothstep(4, 0.5, G.d_water) * (G.d_water > 0)) * fall * front
	me = ground.data
	for name, arr in (("grass", g), ("flowers", fl * gd.get("Flowers", 0.25)), ("pebbles", np.clip(pebbles, 0, 1) * 0.2)):
		me.attributes[name].data.foreach_set("value", arr.astype(np.float32).ravel())
	me.update()


# ---------------------------------------------------------------- props


MASTERS = {}


def master(key, fn):
	if key not in MASTERS:
		o = fn()
		o.hide_render = o.hide_viewport = True
		MASTER_COLL.objects.link(o)
		zs = [v.co.z for v in o.data.vertices]
		MASTERS[key] = (o, max(zs) - min(zs))
	return MASTERS[key]


def put(key, fn, coll, x, y, yaw=0.0, scale=1.0, z=None, sink=0.3, name=None, tilt=(0.0, 0.0)):
	src, h = master(key, fn)
	o = bpy.data.objects.new(name or key, src.data)
	zz = (G.z(x, y) if z is None else z) - sink
	o.location = lb.to_b(x, y, zz)
	o.rotation_euler = (tilt[0], tilt[1], yaw)
	o.scale = (scale, scale, scale) if not isinstance(scale, tuple) else scale
	coll.objects.link(o)
	return o


def yaw_toward(x, y, tx, ty):
	"""yaw that turns a piece's front (-Y local) toward map point (tx, ty)"""
	v = Vector((tx - x, -(ty - y)))
	return math.atan2(v.x, -v.y)


AVOID = []  # (x, y, r): keep trees and rocks off these


def free(x, y, r=0.0):
	return all(math.hypot(x - ax, y - ay) > ar + r for ax, ay, ar in AVOID)


def town(coll, ao):
	hx, hy = G.hub
	R_isl = G.island["Radius"]
	zt = G.z(hx, hy)
	# the keep on the island's high north-east side, facing the plaza
	kx, ky = hx + 22, hy - 30
	put("Keep", lambda: kv.keep("Keep", 13), coll, kx, ky, yaw_toward(kx, ky, hx, hy + 10), sink=0.5)
	AVOID.append((kx, ky, 34))
	ao.append((kx, ky, 36, 0.35))
	for k, (bx, bz) in enumerate(((-6, 30), (6, 30))):  # banners on the keep's front
		pass
	# plaza with a fountain and stalls
	px, py = hx - 4, hy + 16
	fountain(coll, px, py)
	for k in range(5):
		a = k * math.tau / 5 + 0.3
		sx, sy = px + math.cos(a) * 15, py + math.sin(a) * 15
		put(f"Stall{k % 3}", lambda k=k: kv.stall(f"Stall{k % 3}", 17 + k, colour=("cloth_red", "cloth_blue", "f2c94a")[k % 3]), coll, sx, sy, yaw_toward(sx, sy, px, py), sink=0.1)
	AVOID.append((px, py, 22))
	gates = BT["Town"]["Gates"]  # map angles (degrees, 0 = east, 90 = south)
	# houses in rings, facing the island's centre, clear of streets, keep and plaza
	rr = random.Random(5)
	n = 0
	for ring_r, count in ((38, 14), (55, 20), (70, 24)):
		for k in range(count):
			a = k * math.tau / count + rr.uniform(-0.08, 0.08) + ring_r * 0.01
			if any(abs(((math.degrees(a) - g) + 180) % 360 - 180) < 9 for g in gates):
				continue
			x, y = hx + math.cos(a) * ring_r, hy + math.sin(a) * ring_r
			if math.hypot(x - kx, y - ky) < 30 or math.hypot(x - px, y - py) < 22:
				continue
			w, d = rr.uniform(8, 12), rr.uniform(7, 9)
			hgt = rr.uniform(7, 10)
			roof = "tile" if rr.random() < 0.3 else "slate"
			key = f"House_{int(w)}_{int(hgt)}_{roof}_{n % 6}"
			put(key, lambda w=w, d=d, hgt=hgt, roof=roof, n=n: kv.house(key, 40 + n, w, d, hgt, roof=roof, storeys=2 if hgt > 7.5 else 1),
				coll, x, y, yaw_toward(x, y, hx, hy), sink=0.6)
			ao.append((x, y, 9, 0.3))
			n += 1
	log(f"town: {n} houses")
	# ring wall, towers, gatehouses and bridges
	wall_r = R_isl - 4
	tower_angles = [g + d for g in gates for d in (-7, 7)] + [45, 135, 200, 255, 315, 345]
	tower_angles = sorted(set(round(t) % 360 for t in tower_angles))
	for t in tower_angles:
		a = math.radians(t)
		x, y = hx + math.cos(a) * wall_r, hy + math.sin(a) * wall_r
		put("WallTower", lambda: kv.round_tower("WallTower", 11, 4.2, 17), coll, x, y, 0, sink=1.0)
	for t0, t1 in zip(tower_angles, tower_angles[1:] + [tower_angles[0] + 360]):
		gap = any(abs(((g - (t0 + t1) / 2) + 180) % 360 - 180) < 8 for g in gates)
		if gap:
			continue
		span = t1 - t0
		steps = max(1, int(span / 10))
		for s in range(steps):
			a0 = math.radians(t0 + span * s / steps)
			a1 = math.radians(t0 + span * (s + 1) / steps)
			x0, y0 = hx + math.cos(a0) * wall_r, hy + math.sin(a0) * wall_r
			x1, y1 = hx + math.cos(a1) * wall_r, hy + math.sin(a1) * wall_r
			L = math.hypot(x1 - x0, y1 - y0)
			mx, my = (x0 + x1) / 2, (y0 + y1) / 2
			yaw = math.atan2(-(y1 - y0), x1 - x0)
			put(f"Wall_{int(L)}", lambda L=L: kv.crenel_wall(f"Wall_{int(L)}", 12, L + 1.0, 10, 3), coll, mx, my, yaw, sink=1.0)
	for g in gates:  # a bridge across the moat at each gate
		a = math.radians(g)
		bx, by = hx + math.cos(a) * (R_isl + G.island["Moat"] / 2 + 4), hy + math.sin(a) * (R_isl + G.island["Moat"] / 2 + 4)
		yaw = math.atan2(-math.sin(a), math.cos(a))
		put("Bridge", lambda: kv.stone_bridge("Bridge", 14, 38, 8, arches=3, rise=7), coll, bx, by, yaw, z=G.water_z - 0.5, sink=0.0)
	# the mill by the river and the windmill out in the meadows
	wx, wy = BT["Town"]["Wheel"]
	put("Wheel", lambda: kv.waterwheel("Wheel", 16, 5.5, 2.2), coll, wx, wy, BT["Town"].get("WheelYaw", 0.6), z=G.water_z - 2.5, sink=0)
	put("Mill", lambda: kv.house("Mill", 77, 9, 8, 7, roof="tile", storeys=1), coll, wx + 9, wy + 4, BT["Town"].get("WheelYaw", 0.6))
	mx, my = BT["Town"]["Windmill"]
	put("Windmill", lambda: kv.windmill("Windmill", 15, height=20), coll, mx, my, yaw_toward(mx, my, hx, hy) + 0.5)
	AVOID.extend([(wx, wy, 14), (mx, my, 14)])
	ao.append((mx, my, 10, 0.35))


def fountain(coll, x, y):
	p = kit.Piece(91)
	p.hull(kit.ring(0, 5.0, 12) + kit.ring(1.4, 5.2, 12), "d8d3c6")
	p.hull(kit.ring(1.0, 4.4, 12) + kit.ring(1.25, 4.4, 12), "6aa4c8")
	p.hull(kit.ring(0, 0.9, 8) + kit.ring(4.5, 0.6, 8), "d8d3c6")
	p.hull(kit.ring(3.4, 1.9, 10) + kit.ring(3.9, 2.1, 10), "d8d3c6")
	o = p.finish("Fountain", coll)
	o.location = lb.to_b(x, y, G.z(x, y) - 0.2)


def gatehill(coll, ao):
	gx, gy = next(p for p in M["Places"] if p["Icon"] == "gate")["At"]
	hx, hy = G.hub
	yaw = yaw_toward(gx, gy, hx, hy)
	zg = G.z(gx, gy)
	put("Gate", lambda: kv.grand_gate("Gate", 20, height=BT["Gate"].get("Height", 64)), coll, gx, gy, yaw, sink=1.0)
	beam = kv.light_beam("Beam", height=1400, radius=BT["Gate"].get("BeamRadius", 3.2))
	coll.objects.link(beam)
	H = BT["Gate"].get("Height", 64)
	beam.location = lb.to_b(gx, gy, zg + H * 0.62)
	AVOID.append((gx, gy, 45))
	# the ring of ruined watchtowers: the arena, opening toward the approach
	front = Vector((hx - gx, hy - gy)).normalized()
	ac = Vector((gx, gy)) + front * 46
	for k in range(8):
		a = math.atan2(front.y, front.x) + math.pi + (k - 3.5) * 0.62
		if abs(((k - 3.5) * 0.62)) > 2.4:
			continue
		tx, ty = ac.x + math.cos(a) * 52, ac.y + math.sin(a) * 52
		hgt = random.Random(k).uniform(18, 30)
		put(f"ArenaTower{k % 3}", lambda k=k: kit.tower(f"ArenaTower{k % 3}", 55 + k, height=28, width=9, ruined=True), coll, tx, ty, R.uniform(0, 6.28), scale=hgt / 28, sink=1.0)
		AVOID.append((tx, ty, 8))
		ao.append((tx, ty, 9, 0.35))
	# the sleeping Warden: a huge mossy golem slumped in front of the Gate
	wx, wy = Vector((gx, gy)) + front * 16
	put("Warden", lambda: kv_golem_mossy(), coll, wx, wy, yaw, scale=3.6, sink=1.8, tilt=(math.radians(14), 0))
	ao.append((wx, wy, 14, 0.4))


def kv_golem_mossy():
	o = kit.golem("Warden", 93, height=5.5)
	cols = o.data.color_attributes["Col"].data
	o.data.calc_normals_split() if hasattr(o.data, "calc_normals_split") else None
	for poly in o.data.polygons:  # moss on everything that faces up
		if poly.normal.z > 0.45 and poly.material_index == 0:
			for li in poly.loop_indices:
				cols[li].color = (*kit.to_linear(kit.srgb("6f9a3c")), 1)
	return o


def ruins(coll, ao):
	rx, ry = next(p for p in M["Places"] if p["Icon"] == "ruin")["At"]
	put("Arcade", lambda: kit.ruin_arches("Arcade", 57, bays=4, bay=12, height=15), coll, rx, ry, 0.4, sink=0.8)
	put("RuinTower", lambda: kit.tower("RuinTower", 56, height=30, width=12, ruined=True), coll, rx + 34, ry - 14, 0.2, sink=1.0)
	put("RuinTower2", lambda: kit.tower("RuinTower2", 54, height=20, width=10, ruined=True), coll, rx - 30, ry + 12, 1.1, sink=1.0)
	for k in range(9):
		a, d = R.uniform(0, 6.28), R.uniform(8, 32)
		x, y = rx + math.cos(a) * d, ry + math.sin(a) * d
		put("FallenBlock", lambda: kit.boulder("FallenBlock", 66, size=(3, 2.2, 1.8)), coll, x, y, R.uniform(0, 6.28), scale=R.uniform(0.8, 1.6), sink=0.3)
	AVOID.append((rx, ry, 40))
	ao.append((rx, ry, 30, 0.25))


def camp(coll, ao):
	cx, cy = next(p for p in M["Places"] if p["Icon"] == "camp")["At"]
	for k in range(7):
		a = k * math.tau / 7
		x, y = cx + math.cos(a) * 22, cy + math.sin(a) * 22
		put(f"Tent{k % 2}", lambda k=k: kv.tent(f"Tent{k % 2}", 18 + k, colour=("cloth_red", "8a5a3a")[k % 2]), coll, x, y, a + math.pi / 2, sink=0.1)
	for k in range(5):
		a = k * math.tau / 5 + 0.3
		x, y = cx + math.cos(a) * 38, cy + math.sin(a) * 38
		put("Palisade", lambda: kv.palisade("Palisade", 19, 22, height=5), coll, x, y, -a + math.pi / 2, sink=0.4)
	for k in range(3):
		a = k * math.tau / 3 + 1.0
		x, y = cx + math.cos(a) * 30, cy + math.sin(a) * 30
		put("Watchtower", lambda: wood_tower(), coll, x, y, a, sink=0.3)
	put("Campfire", lambda: campfire(), coll, cx, cy, 0, sink=0.1)
	AVOID.append((cx, cy, 44))
	ao.append((cx, cy, 40, 0.2))


def wood_tower():
	p = kit.Piece(31)
	for sx in (-1, 1):
		for sy in (-1, 1):
			p.hull([Vector((sx * 2.2 + x, sy * 2.2 + y, z)) for x in (-0.25, 0.25) for y in (-0.25, 0.25) for z in (0, 15)], "6b4a33")
	p.hull([Vector((x, y, z)) for x in (-3, 3) for y in (-3, 3) for z in (11, 11.6)], "8a6a4a")
	p.hull([Vector((x, y, 11.6)) for x in (-3.2, 3.2) for y in (-3.2, 3.2)] + [Vector((0, 0, 16.5))], "a8623a")
	for z in (3.5, 7.5):
		for sx in (-1, 1):
			p.hull([Vector((sx * 2.2 + x, y, z + dz)) for x in (-0.15, 0.15) for y in (-2.4, 2.4) for dz in (0, 0.3)], "6b4a33")
	return p.finish("Watchtower", None)


def campfire():
	p = kit.Piece(32)
	for k in range(6):
		a = k * math.tau / 6
		p.hull([Vector((math.cos(a) * 1.2 + x, math.sin(a) * 1.2 + y, z)) for x in (-0.3, 0.3) for y in (-0.3, 0.3) for z in (0, 0.5)], "8c8a84")
	p.hull([Vector((0, 0, 1.6)), Vector((0.5, 0, 0)), Vector((-0.5, 0, 0)), Vector((0, 0.5, 0)), Vector((0, -0.5, 0))], "ffae42", glow=True)
	return p.finish("Campfire", None)


def cave(coll, ao):
	cx, cy = next(p for p in M["Places"] if p["Icon"] == "dungeon")["At"]
	for k in range(7):
		x, y = cx - 40 + k * 13 + R.uniform(-3, 3), cy - 10 + R.uniform(-4, 4)
		put(f"CliffRock{k % 3}", lambda k=k: kv.mossy_boulder(f"CliffRock{k % 3}", 70 + k, (16, 11, 22), moss=0.8), coll, x, y, R.uniform(0, 6.28), scale=R.uniform(1.0, 1.5), sink=2.0)
	p = kit.Piece(33)
	n = 10
	for k in range(n):  # a dark arch: the cave mouth
		a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
		p.poly([Vector((math.cos(a0) * 7, 0, math.sin(a0) * 9)), Vector((math.cos(a1) * 7, 0, math.sin(a1) * 9)), Vector((0, 0, 0))][::-1], "141a1c")
	for k in range(5):  # glowing mushrooms by the mouth
		x, z = R.uniform(-9, 9), 0
		c = Vector((x, -R.uniform(1.5, 4.0), 0))
		p.hull([c + Vector((0, 0, 0)), c + Vector((0, 0, 1.2))] + [c + Vector((math.cos(a) * 0.9, math.sin(a) * 0.9, 1.2)) for a in (0, 2.1, 4.2)] + [c + Vector((0, 0, 1.7))], "7af0c8", glow=True)
	o = p.finish("CaveMouth", coll)
	o.location = lb.to_b(cx, cy + 4, G.z(cx, cy + 4) - 0.3)
	AVOID.append((cx, cy, 30))


def start_circle(coll):
	sx, sy = next(p for p in M["Places"] if p["Icon"] == "start")["At"]
	for k in range(8):
		a = k * math.tau / 8
		x, y = sx + math.cos(a) * 15, sy + math.sin(a) * 15
		put(f"Standing{k % 3}", lambda k=k: kv.standing_stone(f"Standing{k % 3}", 80 + k, 7.5, rune=k % 2 == 0), coll, x, y, yaw_toward(x, y, sx, sy), sink=0.4)
	put("GateStone", lambda: kv.standing_stone("GateStone", 89, 11), coll, sx, sy, 0.3, sink=0.3)
	AVOID.append((sx, sy, 24))
	for w in M.get("Waystones", []):
		put("Waystone", lambda: kv.standing_stone("Waystone", 88, 5.5), coll, w[0], w[1], R.uniform(0, 6.28), sink=0.3)
		AVOID.append((w[0], w[1], 5))


def trees_and_rocks(coll, ao):
	ts = BT["Trees"]
	species = {
		"oak": [lambda i=i: kv.broadleaf(f"Oak{i}", 100 + i, 16, kind="oak") for i in range(4)],
		"round": [lambda i=i: kv.broadleaf(f"Round{i}", 110 + i, 13, kind="round") for i in range(3)],
		"poplar": [lambda i=i: kv.broadleaf(f"Poplar{i}", 120 + i, 18, kind="poplar") for i in range(2)],
		"autumn": [lambda i=i: kv.broadleaf(f"Autumn{i}", 130 + i, 15, kind="oak", autumn=True) for i in range(2)],
		"pine": [lambda i=i: kit.pine(f"Pine{i}", 140 + i, 26) for i in range(4)],
		"bush": [lambda i=i: kit.bush(f"Bush{i}", 150 + i, size=4.0) for i in range(3)],
	}
	X0, Y0 = -lb.B.get("Border", 300) + 60, -lb.B.get("Border", 300) + 60
	X1, Y1 = lb.W + lb.B.get("Border", 300) - 60, lb.H + lb.B.get("Border", 300) - 60
	counts = {}
	cell = BT.get("TreeCell", 9.0)
	y = Y0
	while y < Y1:
		x = X0
		while x < X1:
			px, py = x + R.uniform(-0.45, 0.45) * cell, y + R.uniform(-0.45, 0.45) * cell
			x += cell
			zn = G.zone_name(px, py) or "_gap"
			spec = ts.get(zn, ts["_gap"])
			grove = float(lb.noise(np.array(px), np.array(py), spec.get("GroveScale", 120), 71)) * 0.5 + 0.5
			p = spec["Density"] * smoothstep(spec.get("GroveFrom", 0.0), spec.get("GroveFrom", 0.0) + 0.25, grove)
			if R.random() > p:
				continue
			if G.at(G.d_water, px, py) < 5 or G.at(G.d_path, px, py) < 7 or G.at(G.slope, px, py) > 1.1:
				continue
			if G.at(G.dh, px, py) < G.island["Radius"] + 22 or not free(px, py, 2):
				continue
			kind = R.choices(list(spec["Mix"]), weights=list(spec["Mix"].values()))[0]
			v = R.randrange(len(species[kind]))
			hmin, hmax = spec.get("Height", [0.8, 1.25])
			put(f"T_{kind}{v}", species[kind][v], coll, px, py, R.uniform(0, 6.28), scale=R.uniform(hmin, hmax), sink=0.5)
			ao.append((px, py, 6 if kind != "bush" else 3, 0.35 if kind != "bush" else 0.25))
			counts[kind] = counts.get(kind, 0) + 1
	log("trees:", counts)
	nrock = 0
	for _ in range(BT.get("Rocks", 600)):
		px, py = R.uniform(X0, X1), R.uniform(Y0, Y1)
		zn = G.zone_name(px, py) or "_gap"
		amount = ts.get(zn, ts["_gap"]).get("Rocks", 0.2)
		if R.random() > amount or G.at(G.d_water, px, py) < 3 or G.at(G.d_path, px, py) < 5 or not free(px, py, 3):
			continue
		if G.at(G.dh, px, py) < G.island["Radius"] + 15:
			continue
		s = R.uniform(0.6, 1.9) if R.random() < 0.85 else R.uniform(2.2, 3.4)
		put(f"Boulder{nrock % 4}", lambda n=nrock: kv.mossy_boulder(f"Boulder{n % 4}", 200 + n % 4, (7, 6, 5), moss=0.6), coll, px, py, R.uniform(0, 6.28), scale=s, sink=0.8 * s)
		ao.append((px, py, 4 * s, 0.3))
		nrock += 1
	log("rocks:", nrock)


def far_world(coll):
	fw = BT["Far"]
	for k, rng_ in enumerate(fw["Ranges"]):
		cx, cy = rng_["At"]
		o = put(f"Range{k}", lambda r=rng_, k=k: kv.mountain_range(f"Range{k}", 500 + k, r["Width"], r["Depth"], r["Height"], peaks=r.get("Peaks", 5), snow=r.get("Snow", 0.62)),
				coll, cx, cy, math.radians(rng_.get("Yaw", 0)), z=rng_.get("Z", -40), sink=0)
	isl = fw.get("Island")
	if isl:
		put("FloatingIsland", lambda: kv.floating_island("FloatingIsland", 600, isl.get("Radius", 140)), coll, isl["At"][0], isl["At"][1], math.radians(isl.get("Yaw", 0)), z=isl["Z"], sink=0)


# ---------------------------------------------------------------- sky, light, cameras, render


def world_light(view):
	sc = bpy.context.scene
	sky = dict(BT["Sky"])
	sl = BT["Light"]["Sun"]
	az, el = math.radians(sl["Azimuth"]), math.radians(sl["Elevation"])
	# azimuth: compass in map terms (0 = north, 90 = east); light comes FROM that direction
	from_dir = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
	sky_sun = BT["Sky"].get("SunFrom")
	if sky_sun:
		a2, e2 = math.radians(sky_sun[0]), math.radians(sky_sun[1])
		sd = Vector((math.sin(a2) * math.cos(e2), math.cos(a2) * math.cos(e2), math.sin(e2)))
	else:
		sd = from_dir
	sky["SunDir"] = [sd.x, sd.y, sd.z]
	W, H = sky.get("Size", (4096, 2048))
	key = json.dumps(sky, sort_keys=True)
	img = bpy.data.images.get("PaintedSky")
	if not img or img.get("key") != key:
		col = sky_paint.paint(sky, (W, H))
		img = bpy.data.images.new("PaintedSky", W, H, alpha=False, float_buffer=True)
		img.pixels.foreach_set(np.concatenate([col[::-1], np.ones((H, W, 1), np.float32)], -1).ravel())
		img.pack()
		img["key"] = key
	world = sc.world or bpy.data.worlds.new("Sky")
	sc.world = world
	world.use_nodes = True
	nt = world.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputWorld")
	env = nt.nodes.new("ShaderNodeTexEnvironment")
	env.image = img
	cam_bg, light_bg = nt.nodes.new("ShaderNodeBackground"), nt.nodes.new("ShaderNodeBackground")
	amb = BT["Light"].get("Ambient", {})
	light_bg.inputs["Strength"].default_value = amb.get("Strength", 1.0)
	tint = nt.nodes.new("ShaderNodeMix")
	tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
	tint.inputs["Factor"].default_value = 1.0
	tint.inputs["B"].default_value = (*lin(amb.get("Tint", "ffffff")), 1)
	nt.links.new(env.outputs["Color"], cam_bg.inputs["Color"])
	nt.links.new(env.outputs["Color"], tint.inputs["A"])
	nt.links.new(tint.outputs["Result"], light_bg.inputs["Color"])
	lp, mixs = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
	nt.links.new(lp.outputs["Is Camera Ray"], mixs.inputs["Fac"])
	nt.links.new(light_bg.outputs["Background"], mixs.inputs[1])
	nt.links.new(cam_bg.outputs["Background"], mixs.inputs[2])
	nt.links.new(mixs.outputs["Shader"], out.inputs["Surface"])
	sun_o = bpy.data.objects.get("Sun")
	if not sun_o:
		sun = bpy.data.lights.new("Sun", "SUN")
		sun_o = bpy.data.objects.new("Sun", sun)
		sc.collection.objects.link(sun_o)
	sun_o.data.energy = sl["Strength"]
	sun_o.data.color = kit.to_linear(kit.srgb(sl["Colour"]))
	sun_o.data.angle = math.radians(sl.get("Angle", 3.0))
	sun_o.rotation_euler = (-from_dir).to_track_quat("-Z", "Y").to_euler()
	return sd


def camera(view):
	sc = bpy.context.scene
	cam_o = bpy.data.objects.get("Cam")
	if not cam_o:
		cam_o = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
		sc.collection.objects.link(cam_o)
	cam = cam_o.data
	cam.sensor_fit = "VERTICAL"
	cam.angle_y = math.radians(view.get("FovV", 60))
	cam.clip_start, cam.clip_end = 0.3, 20000
	fx, fy = view["From"]
	tx, ty = view["To"]
	pos = lb.to_b(fx, fy, (G.z(fx, fy) if "Z" not in view else 0) + view.get("Up", 7) + view.get("Z", 0))
	look = lb.to_b(tx, ty, (G.z(tx, ty) if "ToZ" not in view else 0) + view.get("ToUp", 10) + view.get("ToZ", 0))
	fwd = (look - pos).normalized()
	cam_o.location = pos
	cam_o.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
	sc.camera = cam_o
	bpy.context.view_layer.update()
	return cam_o, pos, fwd


def render_settings(quick):
	sc = bpy.context.scene
	r = BT.get("Render", {})
	sc.render.engine = "BLENDER_EEVEE"
	sc.render.resolution_x, sc.render.resolution_y = r.get("Res", [1600, 900])
	sc.render.resolution_percentage = 50 if quick else 100
	sc.view_settings.view_transform = "Standard"
	sc.view_settings.look = "None"
	sc.view_settings.exposure = r.get("Exposure", 0.0)
	ee = sc.eevee
	ee.taa_render_samples = 16 if quick else r.get("Samples", 48)
	for k, v in r.get("Eevee", {}).items():
		try:
			setattr(ee, k, v)
		except Exception as e:  # noqa: BLE001
			log("eevee setting", k, e)
	sc.render.image_settings.file_format = "PNG"
	sc.render.image_settings.color_depth = "16"
	sc.render.image_settings.color_mode = "RGB"


def depth_pass(path, rng_max):
	sc = bpy.context.scene
	m = bpy.data.materials.get("DepthOverride")
	if not m:
		m = bpy.data.materials.new("DepthOverride")
		m.use_nodes = True
		nt = m.node_tree
		nt.nodes.clear()
		out = nt.nodes.new("ShaderNodeOutputMaterial")
		em = nt.nodes.new("ShaderNodeEmission")
		cd = nt.nodes.new("ShaderNodeCameraData")
		dv = nt.nodes.new("ShaderNodeMath")
		dv.operation = "DIVIDE"
		dv.inputs[1].default_value = rng_max
		nt.links.new(cd.outputs["View Distance"], dv.inputs[0])
		nt.links.new(dv.outputs["Value"], em.inputs["Color"])
		nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
	vl = sc.view_layers[0]
	vl.material_override = m
	old_world = sc.world
	w = bpy.data.worlds.get("DepthWorld") or bpy.data.worlds.new("DepthWorld")
	w.use_nodes = True
	w.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
	sc.world = w
	vt, ex = sc.view_settings.view_transform, sc.view_settings.exposure
	sc.view_settings.view_transform, sc.view_settings.exposure = "Raw", 0.0
	samples = sc.eevee.taa_render_samples
	sc.eevee.taa_render_samples = 1
	sun = bpy.data.objects.get("Sun")
	sun.hide_render = True
	sc.render.filepath = path
	bpy.ops.render.render(write_still=True)
	sun.hide_render = False
	vl.material_override = None
	sc.world = old_world
	sc.view_settings.view_transform, sc.view_settings.exposure = vt, ex
	sc.eevee.taa_render_samples = samples


def main():
	global G, MASTER_COLL
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	MASTER_COLL = bpy.data.collections.new("Masters")
	sc.collection.children.link(MASTER_COLL)
	coll = bpy.data.collections.new("Vale")
	sc.collection.children.link(coll)
	G = Ground()
	ao = []
	start_circle(coll)
	town(coll, ao)
	gatehill(coll, ao)
	ruins(coll, ao)
	camp(coll, ao)
	cave(coll, ao)
	trees_and_rocks(coll, ao)
	far_world(coll)
	ground = ground_mesh(G, coll, ao)
	water_plane(G, coll)
	clumps = clump_collections()
	gd = BT["GrassDensity"]
	scatter_modifier(ground, "Grass", "grass", clumps["grass"], gd.get("Max", 3.0), (0.7, 1.35), 1)
	scatter_modifier(ground, "Flowers", "flowers", clumps["flowers"], 1.0, (0.8, 1.3), 11)
	scatter_modifier(ground, "Pebbles", "pebbles", clumps["pebbles"], 1.0, (0.5, 1.6), 21)
	log(f"scene built: {len(bpy.data.objects)} objects")
	quick = "--quick" in FLAGS
	render_settings(quick)
	want = flag_value("--views")
	views = [v for v in BT["Views"] if not want or v["Name"] in want.split(",")]
	for view in views:
		vdir = os.path.join(OUT, view["Name"])
		os.makedirs(vdir, exist_ok=True)
		cam_o, pos, fwd = camera(view)
		set_density(G, ground, (pos.x, -pos.y), (fwd.x, -fwd.y), view)
		sd = world_light(view)
		sc.render.filepath = os.path.join(vdir, "beauty.png")
		bpy.ops.render.render(write_still=True)
		rng_max = BT.get("Render", {}).get("DepthRange", 12000.0)
		depth_pass(os.path.join(vdir, "depth.png"), rng_max)
		res = BT.get("Render", {}).get("Res", [1600, 900])
		FW, FH = res
		f = (FH / 2) / math.tan(math.radians(view.get("FovV", 60)) / 2)
		right = fwd.cross(Vector((0, 0, 1))).normalized()
		up = right.cross(fwd).normalized()
		meta = {"SkySunDir": list(sd), "DepthRange": rng_max,
				"Camera": {"Pos": list(pos), "Fwd": list(fwd), "Right": list(right), "Up": list(up), "F": f, "Cy": FH / 2, "Frame": [FW, FH]}}
		json.dump({"Meta": meta}, open(os.path.join(vdir, "placements.json"), "w"), indent=1)
		log(f"view {view['Name']} rendered")
	if "--save" in FLAGS:
		bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "vale.blend"))
	log("done")


G = None
MASTER_COLL = None
main()
