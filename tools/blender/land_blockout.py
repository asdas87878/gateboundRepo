"""Grey-box a whole Land from its map (art/lands/<land>/map.json + its "Blockout" heights): terrain per zone, the river
and the hub island, carved paths, block stand-ins for buildings, cone trees and boulders, then clay renders.

  blender --background --python tools/blender/land_blockout.py -- art/lands/land1/map.json [--no-render]

Writes art/lands/<land>/blockout/: aerial.png, top.png, eye_<name>.png, labels.json (aerial label positions, for
tools/art/land_labels.py), travel.json (path lengths and walking times), blockout.blend.
Map coordinates: x east, y south (studs). Blender: X east, Y north (= -y), Z up.
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "art"))
import kit  # noqa: E402
import noise2d  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1 :]
MAP_PATH = os.path.abspath(ARGS[0])
M = json.load(open(MAP_PATH, encoding="utf-8"))
B = M["Blockout"]
OUT = os.path.join(os.path.dirname(MAP_PATH), "blockout")
W, H = M["Size"]
STEP = B.get("Step", 4.0)
WALK = 16.0  # Roblox default WalkSpeed, studs per second


def smoothstep(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


def noise(X, Y, scale, seed):
	r = np.random.RandomState(seed)
	out = np.zeros_like(X)
	for o in range(3):
		for _ in range(3):
			a, ph = r.uniform(0, math.tau), r.uniform(0, math.tau)
			f = math.tau / scale * 2 ** o
			out += np.sin((X * math.cos(a) + Y * math.sin(a)) * f + ph) / 2 ** o
	return out / 3.5


def seg_dist(X, Y, pts):
	best = np.full_like(X, 1e9)
	for (ax, ay), (bx, by) in zip(pts, pts[1:]):
		dx, dy = bx - ax, by - ay
		L2 = dx * dx + dy * dy or 1e-9
		t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
		best = np.minimum(best, np.hypot(X - ax - dx * t, Y - ay - dy * t))
	return best


def rim_mountains(X, Y, edge):
	"""the ring of mountains around a Land as ridged ranges: crests, saddles and gullies running down into the Land,
	high sections and low passes along the ring, foothills that fade out inside the edge. Rises from Rim.From studs
	inside the edge to full height Rim.To studs outside."""
	rc = B.get("Rim", {})
	wall = B.get("Wall", 160)
	p = smoothstep(rc.get("From", 60), -rc.get("To", 230), edge)
	sc = rc.get("Scale", 240.0)
	m = noise2d.ridged(X / sc, Y / sc, rc.get("Seed", 7), 5, 0.5, rc.get("Sharp", 2.0), warp=rc.get("Warp", 0.6))
	lo, hi = np.percentile(m[p > 0.5], [5, 97]) if np.any(p > 0.5) else (0.0, 1.0)
	m = np.clip((m - lo) / max(hi - lo, 1e-6), 0, 1.15)
	big = noise2d.fbm(X / 900, Y / 900, rc.get("Seed", 7) + 40, 2) * 0.5 + 0.5  # high sections and low passes
	z = wall * p ** 1.2 * (rc.get("Low", 0.35) + rc.get("Peak", 1.05) * m) * (0.75 + 0.5 * big)
	feet = smoothstep(rc.get("FootIn", 150), 20, edge) * smoothstep(-80, 20, edge)  # foothills just inside the edge
	z += noise2d.ridged(X / 90, Y / 90, rc.get("Seed", 7) + 70, 4, 0.5, 2.0, warp=0.4) * rc.get("Foothills", 26) * feet
	return z


def river_dist(X, Y, dh, isl):
	"""distance to the river, which splits into the moat around the hub island instead of crossing it"""
	return np.where(dh < isl["Radius"] + 4, 1e9, seg_dist(X, Y, M["River"]))


def ellipse_d(X, Y, z):
	cx, cy = z["At"]
	rx, ry = z["Radius"]
	return np.hypot((X - cx) / rx, (Y - cy) / ry)  # 1 at the zone's edge


def build_heights():
	xs = np.arange(-B.get("Border", 300), W + B.get("Border", 300) + 1, STEP)
	ys = np.arange(-B.get("Border", 300), H + B.get("Border", 300) + 1, STEP)
	X, Y = np.meshgrid(xs, ys)
	Z = noise(X, Y, 220, 1) * B.get("Roll", 3.0) + B.get("Base", 4.0)  # dry land sits well above the water
	zone_id = np.full(X.shape, -1)
	zones = {z["Name"]: z for z in M["Zones"]}
	weight_best = np.zeros_like(X)
	for k, z in enumerate(M["Zones"]):
		h = B["Zones"].get(z["Name"], {})
		d = ellipse_d(X, Y, z)
		w = smoothstep(1.25, 0.75, d)
		shape = h.get("Shape", "rolling")
		if shape == "plateau":
			Z += h["Height"] * smoothstep(1.0, h.get("Top", 0.6), d)
		elif shape == "hill":
			Z += h["Height"] * np.clip(1 - d, 0, 1) ** 1.2 + h.get("Plateau", 0) * smoothstep(0.35, 0.25, d)
		elif shape == "ridge":
			a = math.radians(h.get("Angle", 90))
			cx, cy = z["At"]
			across = np.abs(-(X - cx) * math.sin(a) + (Y - cy) * math.cos(a))
			along = np.abs((X - cx) * math.cos(a) + (Y - cy) * math.sin(a))
			Z += h["Height"] * smoothstep(h["Width"], h["Width"] * 0.35, across) * smoothstep(max(z["Radius"]) * 1.05, max(z["Radius"]) * 0.6, along)
		Z += noise(X, Y, h.get("NoiseScale", 90), 10 + k) * h.get("Noise", 2.0) * w
		better = w > weight_best
		zone_id[better & (w > 0.2)] = k
		weight_best = np.maximum(weight_best, w)
	# mountains closing the Vale in
	edge = np.minimum.reduce([X, W - X, Y, H - Y])
	if B.get("RimStyle") == "natural":
		Z += rim_mountains(X, Y, edge)
	else:
		Z += smoothstep(40, -220, edge) * (B.get("Wall", 160) + noise(X, Y, 160, 99) * 50)
	# the hub island: a raised plateau ringed by water
	hub = next(p for p in M["Places"] if p["Icon"] == "castle")["At"]
	dh = np.hypot(X - hub[0], Y - hub[1])
	isl = B.get("Island", {"Radius": 90, "Height": 7, "Moat": 26})
	Z = np.where(dh < isl["Radius"] + 40, Z * smoothstep(isl["Radius"], isl["Radius"] + 40, dh) + isl["Height"] * smoothstep(isl["Radius"] + 4, isl["Radius"] - 10, dh), Z)
	water = np.zeros_like(X, bool)
	moat = np.abs(dh - isl["Radius"] - isl["Moat"] / 2 - 4)
	river = river_dist(X, Y, dh, isl)
	rw = B.get("RiverWidth", 28)
	cut = np.minimum(river, moat * (rw / isl["Moat"]))
	bed = -6.0
	wcut = smoothstep(rw / 2 + 14, rw / 2, cut)
	Z = Z * (1 - wcut) + bed * wcut
	water = cut < rw / 2
	# paths: flattened toward a smoothed line, a little sunken
	path_mask = np.zeros_like(X, bool)
	for line in M["Paths"]:
		d = seg_dist(X, Y, line)
		k = smoothstep(9, 3, d)
		Zs = Z.copy()
		for _ in range(3):  # cheap smoothing so paths don't follow every bump
			Zs = (Zs + np.roll(Zs, 1, 0) + np.roll(Zs, -1, 0) + np.roll(Zs, 1, 1) + np.roll(Zs, -1, 1)) / 5
		Z = np.where(water, Z, Z * (1 - k) + (Zs - 0.4) * k)
		path_mask |= (d < 4) & ~water
	return xs, ys, X, Y, Z, zone_id, water, path_mask


def height_at(xs, ys, Z, x, y):
	i = int(np.clip(round((x - xs[0]) / STEP), 0, len(xs) - 1))
	j = int(np.clip(round((y - ys[0]) / STEP), 0, len(ys) - 1))
	return float(Z[j, i])


def to_b(x, y, z=0.0):
	return Vector((x, -y, z))


def terrain_mesh(xs, ys, X, Y, Z, zone_id, water, path_mask, coll):
	ny, nx = X.shape
	verts = np.stack([X, -Y, Z], -1).reshape(-1, 3)
	idx = np.arange(nx * ny).reshape(ny, nx)
	quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
	mesh = bpy.data.meshes.new("Terrain")
	mesh.vertices.add(len(verts))
	mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
	mesh.loops.add(len(quads) * 4)
	mesh.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
	mesh.polygons.add(len(quads))
	mesh.polygons.foreach_set("loop_start", np.arange(0, len(quads) * 4, 4, dtype=np.int32))
	mesh.update(calc_edges=True)
	mesh.polygons.foreach_set("use_smooth", np.ones(len(quads), bool))
	base = np.array(kit.to_linear(kit.srgb("a9c08a")))  # grassland between zones
	col = np.tile(base, (ny, nx, 1))
	for k, z in enumerate(M["Zones"]):
		c = np.array(kit.to_linear(kit.srgb(z["Colour"])))
		col[zone_id == k] = base * 0.45 + c * 0.55
	slope = np.hypot(*np.gradient(Z, STEP))
	rock = np.clip((slope - 0.6) / 0.6, 0, 1)[..., None]
	col = col * (1 - rock) + np.array(kit.to_linear(kit.srgb("8c8a84"))) * rock
	col[path_mask] = kit.to_linear(kit.srgb("d6c39a"))
	col[water] = kit.to_linear(kit.srgb("6aa6c8"))
	high = smoothstep(60, 140, Z)[..., None]
	col = col * (1 - high) + np.array(kit.to_linear(kit.srgb("a7acb4"))) * high
	attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	attr.data.foreach_set("color", np.concatenate([col.reshape(-1, 3), np.ones((nx * ny, 1))], 1).astype(np.float32).ravel())
	mesh.materials.append(kit.vertex_material())
	obj = bpy.data.objects.new("Terrain", mesh)
	coll.objects.link(obj)
	# a flat water plane over the river and moat
	wm = bpy.data.meshes.new("Water")
	S = 3000
	wm.from_pydata([(-S, -S, -1.5), (S, -S, -1.5), (S, S, -1.5), (-S, S, -1.5)], [], [(0, 1, 2, 3)])
	wa = wm.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	for dv in wa.data:
		dv.color = (*kit.to_linear(kit.srgb("5f9fc4")), 1)
	wm.materials.append(kit.vertex_material())
	coll.objects.link(bpy.data.objects.new("Water", wm))


def box(coll, name, centre, size, colour, yaw=0.0):
	p = kit.Piece(hash(name) & 0xFFFF)
	c = Vector(centre)
	sx, sy, sz = size
	along, out = Vector((math.cos(yaw), math.sin(yaw), 0)), Vector((-math.sin(yaw), math.cos(yaw), 0))
	p.block(c + Vector((0, 0, sz / 2)), along, out, (sx, sy, sz), colour)
	return p.finish(name, coll)


def cone(coll, name, height, radius, colour, sides=7):
	p = kit.Piece(1)
	p.hull(kit.ring(0, radius, sides) + [Vector((0, 0, height))], colour)
	return p.finish(name, coll)


def place_copy(src, coll, loc, yaw=0.0, scale=1.0):
	o = bpy.data.objects.new(src.name + "_i", src.data)
	o.location = loc
	o.rotation_euler = (0, 0, yaw)
	o.scale = (scale,) * 3
	coll.objects.link(o)
	return o


def structures(xs, ys, Z, coll):
	hz = lambda x, y: height_at(xs, ys, Z, x, y)
	stone, roof, wood = "d9d5c8", "5d6f8e", "8a6a42"
	for s in B.get("Structures", []):
		x, y = s["At"]
		z = hz(x, y)
		kind = s["Kind"]
		if kind == "castle_town":
			r = random.Random(4)
			box(coll, "Keep", to_b(x + 25, y - 30, z), (28, 28, 60), stone)
			box(coll, "KeepRoof", to_b(x + 25, y - 30, z + 60), (30, 30, 6), roof)
			box(coll, "KeepSpire", to_b(x + 25, y - 30, z + 66), (8, 8, 26), roof)  # the landmark seen from every zone
			for k in range(4):
				a = k * math.tau / 4 + 0.4
				box(coll, f"KeepTower{k}", to_b(x + 25 + math.cos(a) * 22, y - 30 + math.sin(a) * 22, z), (9, 9, 36), stone)
			for k in range(26):  # town houses on the island
				a, d = r.uniform(0, math.tau), r.uniform(28, 72)
				hx, hy = x + math.cos(a) * d, y + math.sin(a) * d
				if math.hypot(hx - x - 25, hy - y + 30) < 30:
					continue
				hh = r.uniform(8, 13)
				box(coll, f"House{k}", to_b(hx, hy, hz(hx, hy)), (r.uniform(9, 14), r.uniform(8, 12), hh), "efe8da", a)
				box(coll, f"HouseRoof{k}", to_b(hx, hy, hz(hx, hy) + hh), (r.uniform(10, 15), r.uniform(9, 13), 4), roof, a)
			box(coll, "Fountain", to_b(x, y + 10, z), (10, 10, 3), stone)
			for k in range(24):  # town wall round the island edge
				a = k * math.tau / 24
				wx, wy = x + math.cos(a) * 84, y + math.sin(a) * 84
				box(coll, f"Wall{k}", to_b(wx, wy, hz(wx, wy)), (23, 3, 9), stone, a + math.pi / 2)
		elif kind == "gate":
			box(coll, "GateTowerL", to_b(x - 18, y, z), (10, 10, 30), stone)
			box(coll, "GateTowerR", to_b(x + 18, y, z), (12, 12, 38), stone)
			box(coll, "GateArch", to_b(x, y, z + 24), (26, 6, 6), stone)
			for k in range(7):  # the ring of ruined watchtowers: the arena
				a = k * math.tau / 7
				tx, ty = x + math.cos(a) * 55, y + 25 + math.sin(a) * 45
				box(coll, f"ArenaTower{k}", to_b(tx, ty, hz(tx, ty)), (8, 8, random.Random(k).uniform(10, 22)), "c4beb0")
		elif kind == "camp":
			for k in range(8):
				a = k * math.tau / 8
				cx, cy = x + math.cos(a) * 26, y + math.sin(a) * 26
				box(coll, f"Tent{k}", to_b(cx, cy, hz(cx, cy)), (9, 7, 6), "a8623a", a)
			for k in range(3):
				tx, ty = x - 40 + k * 40, y - 60
				box(coll, f"Watchtower{k}", to_b(tx, ty, hz(tx, ty)), (7, 7, 22), wood)
		elif kind == "ruins":
			for k in range(5):
				box(coll, f"Ruin{k}", to_b(x + k * 14, y + (k % 2) * 10, hz(x + k * 14, y)), (10, 4, 8 + 4 * (k % 3)), "c4beb0")
		elif kind == "cave":
			box(coll, "CaveCliff", to_b(x, y - 12, z - 2), (70, 18, 30), "77756f")
			box(coll, "CaveMouth", to_b(x, y - 1, z), (14, 4, 12), "2a2633")
		elif kind == "start":
			for k in range(8):
				a = k * math.tau / 8
				box(coll, f"Standing{k}", to_b(x + math.cos(a) * 14, y + math.sin(a) * 14, z), (2.5, 2, 7), "b8b4a6", a)
		elif kind == "shrine":
			box(coll, "Shrine", to_b(x, y, z), (8, 8, 9), "e0d6b0")
	for w in M.get("Waystones", []):
		box(coll, "Waystone", to_b(w[0], w[1], hz(*w)), (2, 2, 6), "5fb3c9")


def nature(xs, ys, X, Y, Z, zone_id, water, path_mask, coll):
	r = random.Random(7)
	pine = cone(coll, "TreeCone", 30, 7, "4f7a63")
	pine.hide_render = pine.hide_viewport = True
	round_tree = kit.bush("TreeRound", 3, size=14.0, coll=coll)
	round_tree.hide_render = round_tree.hide_viewport = True
	rock = kit.boulder("Rock", 21, size=(9, 7, 5), coll=coll)
	rock.hide_render = rock.hide_viewport = True
	dens = {z["Name"]: B["Zones"].get(z["Name"], {}).get("Trees", 0.0) for z in M["Zones"]}
	rocks = {z["Name"]: B["Zones"].get(z["Name"], {}).get("Rocks", 0.0) for z in M["Zones"]}
	n_trees = n_rocks = 0
	clear = [(p["At"], 70 if p["Icon"] in ("castle", "gate") else 60 if p["Icon"] == "start" else 30) for p in M["Places"]]
	for _ in range(int(W * H / 400)):
		x, y = r.uniform(0, W), r.uniform(0, H)
		i, j = int((x - xs[0]) / STEP), int((y - ys[0]) / STEP)
		k = zone_id[j, i]
		if water[j, i] or path_mask[j, i]:
			continue
		if k < 0:  # the grassland between zones: a few trees so nothing reads as empty
			if r.random() < B.get("GapTrees", 0.0):
				place_copy(pine if r.random() < 0.5 else round_tree, coll, to_b(x, y, float(Z[j, i]) - 0.5), r.uniform(0, math.tau), r.uniform(0.7, 1.2))
				n_trees += 1
			continue
		if any(math.hypot(x - a[0], y - a[1]) < c for a, c in clear):
			continue
		name = M["Zones"][k]["Name"]
		z = float(Z[j, i])
		if r.random() < dens[name]:
			src = pine if r.random() < B["Zones"].get(name, {}).get("PineShare", 0.6) else round_tree
			place_copy(src, coll, to_b(x, y, z - 0.5), r.uniform(0, math.tau), r.uniform(0.7, 1.25))
			n_trees += 1
		elif r.random() < rocks[name]:
			place_copy(rock, coll, to_b(x, y, z - 0.5), r.uniform(0, math.tau), r.uniform(0.6, 1.8))
			n_rocks += 1
	print(f"[blockout] {n_trees} trees, {n_rocks} rocks")


def travel(xs, ys, Z):
	hub = next(p for p in M["Places"] if p["Icon"] == "castle")["At"]
	out = {}
	for p in M["Places"]:
		if p["Icon"] == "castle":
			continue
		# straight-line distance and a rough path distance (x1.3 for bends), with the climb
		d = math.hypot(p["At"][0] - hub[0], p["At"][1] - hub[1])
		climb = height_at(xs, ys, Z, *p["At"]) - height_at(xs, ys, Z, *hub)
		out[p["Name"]] = {"Straight": round(d), "Walk": round(d * 1.3), "Seconds": round(d * 1.3 / WALK), "Climb": round(climb, 1)}
	return out


def render_views(xs, ys, Z, coll):
	sc = bpy.context.scene
	sc.render.engine = "BLENDER_EEVEE"
	sc.eevee.taa_render_samples = 16
	sc.view_settings.view_transform = "Standard"
	w = bpy.data.worlds.new("Sky")
	sc.world = w
	w.use_nodes = True
	w.node_tree.nodes["Background"].inputs["Color"].default_value = (*kit.to_linear(kit.srgb("a9c8dc")), 1)
	w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.4
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = 2.6
	sun.angle = math.radians(3)
	so = bpy.data.objects.new("Sun", sun)
	so.rotation_euler = (math.radians(50), 0, math.radians(-40))
	sc.collection.objects.link(so)
	cam = bpy.data.cameras.new("Cam")
	cam.clip_end = 20000
	co = bpy.data.objects.new("Cam", cam)
	sc.collection.objects.link(co)
	sc.camera = co

	def shoot(name, loc, look, lens=24, res=(1600, 900), ortho=None):
		cam.type = "ORTHO" if ortho else "PERSP"
		if ortho:
			cam.ortho_scale = ortho
		cam.lens = lens
		co.location = loc
		co.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
		sc.render.resolution_x, sc.render.resolution_y = res
		sc.render.filepath = os.path.join(OUT, f"{name}.png")
		bpy.ops.render.render(write_still=True)

	hz = lambda x, y: height_at(xs, ys, Z, x, y)
	# aerial from the south-west, with label positions
	aerial_loc, aerial_look = to_b(W * 0.2, H * 1.75, 1050), to_b(W * 0.55, H * 0.42, 0)
	shoot("aerial", aerial_loc, aerial_look, lens=28)
	bpy.context.view_layer.update()
	labels = []
	for z in M["Zones"]:
		v = world_to_camera_view(sc, co, to_b(*z["At"], hz(*z["At"]) + 20))
		labels.append({"Text": z["Name"], "X": v.x, "Y": 1 - v.y, "Kind": "zone"})
	for p in M["Places"]:
		if p["Icon"] in ("castle", "gate", "dungeon", "start", "camp"):
			v = world_to_camera_view(sc, co, to_b(*p["At"], hz(*p["At"]) + 45))
			labels.append({"Text": p["Name"], "X": v.x, "Y": 1 - v.y, "Kind": "place"})
	json.dump(labels, open(os.path.join(OUT, "labels.json"), "w"), indent=1)
	shoot("top", to_b(W / 2, H / 2, 3000), to_b(W / 2, H / 2 + 0.01, 0), res=(1400, 1200), ortho=max(W, H) * 1.15)
	# eye level (a player's view: 5 studs up, slightly behind) for each named view
	for v in B.get("Views", []):
		fx, fy = v["From"]
		tx, ty = v["To"]
		shoot("eye_" + v["Name"], to_b(fx, fy, hz(fx, fy) + v.get("Up", 8)), to_b(tx, ty, hz(tx, ty) + v.get("LookUp", 10)), lens=18)


def main():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	coll = bpy.data.collections.new("Land")
	bpy.context.scene.collection.children.link(coll)
	xs, ys, X, Y, Z, zone_id, water, path_mask = build_heights()
	print(f"[blockout] grid {X.shape}, height {Z.min():.0f}..{Z.max():.0f}")
	terrain_mesh(xs, ys, X, Y, Z, zone_id, water, path_mask, coll)
	structures(xs, ys, Z, coll)
	nature(xs, ys, X, Y, Z, zone_id, water, path_mask, coll)
	tr = travel(xs, ys, Z)
	json.dump(tr, open(os.path.join(OUT, "travel.json"), "w"), indent=1)
	for k, v in tr.items():
		print(f"[travel] hub -> {k}: {v}")
	if "--no-render" not in ARGS:
		render_views(xs, ys, Z, coll)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "blockout.blend"))


if __name__ == "__main__":
	main()
