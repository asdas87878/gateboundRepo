"""Verdant Vale beauty pass (docs/style/look-direction.md, docs/lands/land1-verdant-vale.md): the block-out's terrain
dressed in the target look. Ground colours by zone, farm fields and hedgerows, grass tufts and flowers near the camera
(instanced; docs/style/grass.md), forests and groves, pine-forested mountains, mossy boulders, the castle town of
Brightwater in coursed stone with banners, the Gate with its light beam, the ruins, the bandit camp, the cave, the stone
circle, far mountain layers and a floating island. Renders hero views.

  blender --background --python tools/blender/vale_beauty.py -- art/lands/land1/map.json <out dir> [--views a,b] [--quick]
      [--grass <style>] [--save]

Per view: <out>/<view>/beauty.png, depth.png, placements.json (camera meta for tools/art/look_post.py). Settings live in
map.json's "Beauty" block. Map coordinates: x east, y south; Blender: X east, Y north, Z up.
"""

import hashlib
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
from grass_kit import blade_clump, fern, matched_material  # noqa: E402
from grass_kit import scatter as gk_scatter  # noqa: E402
import ground_textures  # noqa: E402
import land_blockout as lb  # noqa: E402
import noise2d  # noqa: E402
import sky_paint  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(ARGS[1])
FLAGS = ARGS[2:]
M = lb.M
BT = M["Beauty"]
T0 = time.time()
R = random.Random(BT.get("Seed", 7))


def log(*a):
	line = f"[vale {time.time() - T0:6.1f}s] " + " ".join(str(x) for x in a)
	print(line, flush=True)
	os.makedirs(OUT, exist_ok=True)
	with open(os.path.join(OUT, "log.txt"), "a", encoding="utf-8") as f:  # readable while a long render runs
		f.write(line + "\n")


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
		half = BT["Ground"].get("PathHalf", 3.2)
		widths = BT.get("Trails", {}).get("Width", {})  # road hierarchy: lanes narrower than the main roads
		for k, line in enumerate(M["Paths"]):
			self.d_path = np.minimum(self.d_path, lb.seg_dist(X, Y, line) - half * widths.get(str(k), 1.0) + half)
		hub = self.hub = next(p for p in M["Places"] if p["Icon"] == "castle")["At"]
		isl = lb.B.get("Island", {"Radius": 90, "Height": 7, "Moat": 26})
		self.island = isl
		self.dh = np.hypot(X - hub[0], Y - hub[1])
		rw = lb.B.get("RiverWidth", 28)
		river = lb.river_dist(X, Y, self.dh, isl)
		moat = np.abs(self.dh - isl["Radius"] - isl["Moat"] / 2 - 4)
		self.d_water = np.minimum(river, moat * (rw / isl["Moat"])) - rw / 2
		gy, gx = np.gradient(self.Z, lb.STEP)
		self.slope = np.hypot(gx, gy)
		# curvature at the scale of crests and gullies (positive in hollows), from a blurred copy of the heights
		Zs = self.Z.copy()
		for _ in range(4):
			Zs = (Zs * 2 + np.roll(Zs, 1, 0) + np.roll(Zs, -1, 0) + np.roll(Zs, 1, 1) + np.roll(Zs, -1, 1)) / 6
		k = 3
		self.curv = (np.roll(Zs, k, 0) + np.roll(Zs, -k, 0) + np.roll(Zs, k, 1) + np.roll(Zs, -k, 1) - 4 * Zs) / (k * lb.STEP) ** 2
		self.edge = np.minimum.reduce([X, lb.W - X, Y, lb.H - Y])  # studs inside the Land's edge (negative: the rim)
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


def farm_fields(G):
	"""strip fields around the mill and along the river (Beauty.Fields): blocks of long narrow fields in a shared
	direction, each its own crop colour with faint rows, stopping short of paths and water; hedgerow points along each
	block's edge. Sets G.fields (0..1), G.field_col (linear colour) and G.hedges [(x, y)]."""
	fs = BT.get("Fields")
	G.fields = np.zeros(G.X.shape)
	G.field_col = np.zeros(G.X.shape + (3,))
	G.hedges = []
	G.crop = {k: np.zeros(G.X.shape) for k in ("wheat", "greens")}  # where each crop grows (planted rows)
	G.no_grass = np.zeros(G.X.shape)  # fields that aren't fallow: no meadow grass
	if not fs:
		return
	rr = random.Random(fs.get("Seed", 3))
	X, Y = G.X, G.Y
	cols = [lin(h) for h in fs["Colours"]]
	keep_out = smoothstep(fs.get("PathGap", 5), fs.get("PathGap", 5) + 3, G.d_path) * smoothstep(8, 12, G.d_water) * (G.dh > G.island["Radius"] + 30)
	for blk in fs["Blocks"]:
		cx, cy = blk["At"]
		a = math.radians(blk.get("Angle", rr.uniform(0, 180)))
		ca, sa = math.cos(a), math.sin(a)
		L, Wd = blk["Size"]
		u = (X - cx) * ca + (Y - cy) * sa
		v = -(X - cx) * sa + (Y - cy) * ca
		n = blk.get("Strips", 5)
		edges = sorted([-Wd / 2] + [-Wd / 2 + Wd * (k + rr.uniform(-0.2, 0.2)) / n for k in range(1, n)] + [Wd / 2])
		for k, (v0, v1) in enumerate(zip(edges, edges[1:])):
			l0, l1 = -L / 2 + rr.uniform(0, L * 0.15), L / 2 - rr.uniform(0, L * 0.15)  # ragged ends
			m = smoothstep(l0, l0 + 1.5, u) * smoothstep(l1, l1 - 1.5, u) * smoothstep(v0 + 0.4, v0 + 1.4, v) * smoothstep(v1 - 0.4, v1 - 1.4, v)
			ci = rr.randrange(len(cols))
			c = cols[ci] * rr.uniform(0.93, 1.07)
			kind = fs.get("Kinds", ["wheat", "wheat", "greens", "greens", "bare", "fallow", "greens"])[ci]
			wave = np.sin(v * math.tau / fs.get("RowSpacing", 2.2))
			rows = 1 + 0.07 * wave  # furrows
			m = m * keep_out
			G.field_col = G.field_col * (1 - m[..., None]) + (c[None, None] * rows[..., None]) * m[..., None]
			G.fields = np.maximum(G.fields, m)
			if kind != "fallow":
				G.no_grass = np.maximum(G.no_grass, m)
			if kind in G.crop:  # plants on the ridges between furrows (wheat nearly solid, greens in clear rows)
				ridge = smoothstep(-0.6, 0.2, wave) if kind == "wheat" else smoothstep(0.1, 0.6, wave)
				G.crop[kind] = np.maximum(G.crop[kind], m * ridge)
		# hedgerow points around the block
		step = fs.get("HedgeStep", 5.5)
		for side in range(4):
			if rr.random() < fs.get("HedgeGaps", 0.25):
				continue
			for t in np.arange(-0.5, 0.5, step / (L if side % 2 == 0 else Wd)):
				if side % 2 == 0:
					lu, lv = t * L, (Wd / 2 + 1.5) * (1 if side == 0 else -1)
				else:
					lu, lv = (L / 2 + 1.5) * (1 if side == 1 else -1), t * Wd
				x, y = cx + lu * ca - lv * sa, cy + lu * sa + lv * ca
				if G.at(G.d_path, x, y) > 6 and G.at(G.d_water, x, y) > 4 and G.at(G.dh, x, y) > G.island["Radius"] + 25:
					G.hedges.append((x + rr.uniform(-0.8, 0.8), y + rr.uniform(-0.8, 0.8)))
	log(f"fields: {len(fs['Blocks'])} blocks, {len(G.hedges)} hedge bushes")


PATCH_KINDS = ("clover", "dry", "bare", "flowers", "stones")


def ground_patches(G):
	"""randomised patches over the meadows (Beauty.Patches, docs/style/ground.md): clover (richer green, denser short
	grass, white clover flowers), dry straw (yellow, sparser, taller straw clumps), bare earth (small worn scrapes as
	crisp decals, no grass), flower beds (one flower per bed) and stony ground (rock clusters, sparse grass). Each patch
	is an irregular blob; the mix of kinds depends on the zone. Keeps off trails, water, the town, fields and steep
	ground. Sets G.patch (kind -> 0..1 on the ground grid) and G.patch_list [(kind, x, y, r, seed)]."""
	pc = BT.get("Patches")
	G.patch = {k: np.zeros(G.X.shape) for k in PATCH_KINDS}
	G.patch_list = []
	if not pc:
		return
	rr = random.Random(pc.get("Seed", 17))
	half = BT["Ground"].get("PathHalf", 3.2)
	X, Y = G.X, G.Y
	xs0, xs1 = 0, lb.W
	ys0, ys1 = 0, lb.H
	mixes = pc["Mix"]
	tries = 0
	while len(G.patch_list) < pc.get("Count", 450) and tries < pc.get("Count", 450) * 6:
		tries += 1
		x, y = rr.uniform(xs0, xs1), rr.uniform(ys0, ys1)
		if (G.at(G.d_path, x, y) < half + 4 or G.at(G.d_water, x, y) < 6 or G.at(G.dh, x, y) < G.island["Radius"] + 25
				or G.at(G.fields, x, y) > 0.05 or G.at(G.slope, x, y) > 0.6 or G.at(G.edge, x, y) < 20):
			continue
		mix = mixes.get(G.zone_name(x, y) or "_gap", mixes["_gap"])
		kind = rr.choices(list(mix), weights=list(mix.values()))[0]
		r = rr.uniform(*pc["Radius"][kind])
		G.patch_list.append((kind, x, y, r, rr.randrange(1 << 20)))
	for kind, x, y, r, sd in G.patch_list:  # irregular blobs: radius wobbles with direction and a little noise
		R2 = r * 1.6
		i0, i1 = np.searchsorted(G.xs, [x - R2, x + R2])
		j0, j1 = np.searchsorted(G.ys, [y - R2, y + R2])
		if i1 <= i0 or j1 <= j0:
			continue
		dx, dy = X[j0:j1, i0:i1] - x, Y[j0:j1, i0:i1] - y
		a = np.arctan2(dy, dx)
		q = random.Random(sd)
		wob = 1 + sum(q.uniform(0.05, 0.16) * np.sin(a * k + q.uniform(0, math.tau)) for k in (2, 3, 5))
		d = np.hypot(dx, dy) / (r * wob)
		m = smoothstep(1.0, 0.7, d)
		G.patch[kind][j0:j1, i0:i1] = np.maximum(G.patch[kind][j0:j1, i0:i1], m)
	counts = {k: sum(1 for p in G.patch_list if p[0] == k) for k in PATCH_KINDS}
	log("patches:", counts)


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
	# randomised patches (ground_patches): their colour, before fields, rock and paths paint over them
	pc = BT.get("Patches")
	if pc:
		for kind, key in (("clover", "Clover"), ("dry", "Dry"), ("bare", "Bare"), ("stones", "Stones")):
			m = (G.patch[kind] * pc["Strength"].get(kind, 1.0))[..., None]
			if kind == "clover":  # a richer, deeper green: the same hue, more of it
				col = col * (1 - m) + (col * np.array(pc["Clover"])) * m
			else:
				col = col * (1 - m) + lin(pc[key]) * (0.92 + 0.16 * n1[..., None]) * m
	# farm fields (strip crops) over the grass
	if G.fields.any():
		fm = G.fields[..., None]
		col = col * (1 - fm) + (G.field_col / np.maximum(G.fields, 1e-4)[..., None]) * fm
	# the mountains' slopes: darker, cooler grass than the Vale floor, so the ring reads as a separate, deeper layer
	rim_g = gc.get("Rim")
	if rim_g:
		rw = smoothstep(rim_g.get("From", 20), rim_g.get("To", -150), G.edge)[..., None]
		rcol = lin(rim_g["A"]) * (1 - n1[..., None]) + lin(rim_g["B"]) * n1[..., None]
		col = col * (1 - rw) + rcol * rw
	# rock on steep ground: light on crests, dark in gullies (curvature), two greys in broad patches, mossy ledges where
	# it levels off for a moment
	rn = noise2d.fbm(X / 45, Y / 45, 24, 3) * 0.5 + 0.5
	rock = smoothstep(gc.get("RockFrom", 0.55), gc.get("RockTo", 0.95), G.slope + (rn - 0.5) * 0.35)[..., None]
	t = smoothstep(0.35, 0.65, noise2d.fbm(X / 70, Y / 70, 25, 3) * 0.5 + 0.5)[..., None]
	rc = lin(gc["RockA"]) * (1 - t) + lin(gc["RockB"]) * t
	rc = rc * (1 + np.clip(-G.curv * gc.get("CurvLight", 9.0), -0.45, 0.3))[..., None]
	ledge = (smoothstep(0.5, 0.75, noise2d.fbm(X / 14, Y / 22, 28, 3) * 0.5 + 0.5) * smoothstep(1.5, 0.9, G.slope))[..., None] * 0.7
	rc = rc * (1 - ledge) + lin(gc.get("Moss", "6f8f3e")) * ledge
	col = col * (1 - rock) + rc * rock
	# paths: warm dirt with a soft, wobbly edge and grass creeping in. With trail meshes (Beauty.Trails) the painted band
	# is narrower than the mesh, which draws the crisp edge.
	e = G.d_path - gc.get("PathPaint", gc.get("PathHalf", 3.2)) + lb.noise(X, Y, 6, 25) * (0.4 if BT.get("Trails") else 1.1)
	w = (smoothstep(0.6, -0.6, e) if BT.get("Trails") else smoothstep(1.4, -1.2, e))[..., None] * (1 - rock)
	dn = lb.noise(X, Y, 9, 26) * 0.5 + 0.5
	dirt = lin(gc["Dirt"]) * (1 - dn[..., None]) + lin(gc["DirtDark"]) * dn[..., None]
	creep = smoothstep(0.55, 0.8, lb.noise(X, Y, 3.5, 27) * 0.5 + 0.5)[..., None] * 0.6
	col = col * (1 - w * (1 - creep)) + dirt * w * (1 - creep)
	# river banks: a band of pale sand and pebbles; under the water a dark teal bed
	bank = (smoothstep(6.5, 1.0, G.d_water) * (G.d_water > 0))[..., None]
	col = col * (1 - bank) + lin(gc["Bank"]) * bank
	G.rockw = rock[..., 0]  # which detail texture the ground shader uses where (grass by default)
	G.dirtw = np.clip(w[..., 0] + bank[..., 0], 0, 1)
	col[G.d_water < 0] = lin(gc["Bed"])
	# the town island is cobbled where the town stands
	town = smoothstep(G.island["Radius"] - 2, G.island["Radius"] - 12, G.dh)[..., None]
	col = col * (1 - town) + lin(gc.get("Cobble", "b5a88f")) * town * (0.9 + 0.1 * dn[..., None]) + col * 0 * town
	# overall colour strength (the GPT-6.2 target's grass is about a quarter less saturated than plain albedo greens)
	sat = gc.get("Saturation", 1.0)
	if sat != 1.0:
		y = (col @ np.array([0.2126, 0.7152, 0.0722]))[..., None]
		col = y + (col - y) * sat
	# painted occlusion at the feet of trees, rocks and buildings
	occ = np.ones(X.shape)
	G.shelter = np.zeros(X.shape)
	for x, y, rad, k in ao:
		R2 = rad * 1.6
		i0, i1 = np.searchsorted(G.xs, [x - R2, x + R2])
		j0, j1 = np.searchsorted(G.ys, [y - R2, y + R2])
		if i1 > i0 and j1 > j0:
			d = np.hypot(X[j0:j1, i0:i1] - x, Y[j0:j1, i0:i1] - y) / rad
			occ[j0:j1, i0:i1] *= 1 - k * bell(d)
			# a ring just outside the object's footprint: grass the feet and mowers don't reach
			ring = np.clip(1 - np.abs(d - 0.95) / 0.5, 0, 1)
			G.shelter[j0:j1, i0:i1] = np.maximum(G.shelter[j0:j1, i0:i1], ring)
	col *= occ[..., None]
	G.under_trees = np.clip(1 - occ, 0, 1)
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
	for name in ("grass", "drift", "accent", "flowers", "pebbles", "wheat", "greens", "ferns", "bed_white", "bed_yellow"):
		mesh.attributes.new(name, "FLOAT", "POINT")
	for name, arr in (("rockw", G.rockw), ("dirtw", G.dirtw)):
		at = mesh.attributes.new(name, "FLOAT", "POINT")
		at.data.foreach_set("value", arr.astype(np.float32).ravel())
	gdt = BT.get("GroundDetail")
	if gdt:  # crisp close-up detail from tiling textures (docs/style/ground.md)
		mesh.materials.append(detail_material("GroundMat", (gdt["Grass"], gdt["GrassTile"]),
											  ((gdt["Rock"], gdt["RockTile"], "rockw"), (gdt["Dirt"], gdt["DirtTile"], "dirtw")), gdt.get("Strength", 1.0)))
	else:
		mesh.materials.append(kit.vertex_material())
	obj = bpy.data.objects.new("Ground", mesh)
	coll.objects.link(obj)
	return obj


def detail_material(name, base_tex, extra=(), strength=1.0):
	"""vertex colour ("Col") x a tiling detail texture in world space, normalised to average 1 (tools/art/ground_textures.py
	paints them at DETAIL_MEAN); extra = (texture, studs per tile, weight attribute) blended in by that attribute;
	strength 0 = plain vertex colour, 1 = the texture's full contrast. Roblox: the textures are Terrain MaterialVariant
	colour maps at the same studs per tile."""
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
	bsdf.inputs["Roughness"].default_value = 0.9
	if "Specular IOR Level" in bsdf.inputs:
		bsdf.inputs["Specular IOR Level"].default_value = 0.1
	vc = nt.nodes.new("ShaderNodeVertexColor")
	vc.layer_name = "Col"
	geo = nt.nodes.new("ShaderNodeNewGeometry")

	def tex(fname, studs):
		sc = nt.nodes.new("ShaderNodeVectorMath")
		sc.operation = "SCALE"
		sc.inputs["Scale"].default_value = 1.0 / studs
		nt.links.new(geo.outputs["Position"], sc.inputs[0])
		im = nt.nodes.new("ShaderNodeTexImage")
		im.image = bpy.data.images.load(os.path.join(ROOT, "art", "kit", "textures", fname), check_existing=True)
		im.image.colorspace_settings.name = "Non-Color"
		im.interpolation = "Cubic"
		nt.links.new(sc.outputs["Vector"], im.inputs["Vector"])
		return im.outputs["Color"]

	cur = tex(*base_tex)
	for fname, studs, attr in extra:
		wa = nt.nodes.new("ShaderNodeAttribute")
		wa.attribute_name = attr
		mx = nt.nodes.new("ShaderNodeMix")
		mx.data_type = "RGBA"
		nt.links.new(wa.outputs["Fac"], mx.inputs["Factor"])
		nt.links.new(cur, mx.inputs["A"])
		nt.links.new(tex(fname, studs), mx.inputs["B"])
		cur = mx.outputs["Result"]
	norm = nt.nodes.new("ShaderNodeVectorMath")
	norm.operation = "SCALE"
	norm.inputs["Scale"].default_value = 1.0 / ground_textures.DETAIL_MEAN
	nt.links.new(cur, norm.inputs[0])
	st = nt.nodes.new("ShaderNodeMix")
	st.data_type = "RGBA"
	st.inputs["Factor"].default_value = strength
	st.inputs["A"].default_value = (1, 1, 1, 1)
	nt.links.new(norm.outputs["Vector"], st.inputs["B"])
	mul = nt.nodes.new("ShaderNodeMix")
	mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
	mul.inputs["Factor"].default_value = 1.0
	nt.links.new(vc.outputs["Color"], mul.inputs["A"])
	nt.links.new(st.outputs["Result"], mul.inputs["B"])
	nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
	nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
	return m


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
	sc.inputs[0].default_value = scale[0]
	sc.inputs[1].default_value = scale[1]
	sc.inputs["Seed"].default_value = seed + 2
	idx = n.new("FunctionNodeRandomValue")
	idx.data_type = "INT"
	idx.inputs[0].default_value = 0
	idx.inputs[1].default_value = 99
	idx.inputs["Seed"].default_value = seed + 3
	link(dist.outputs["Points"], iop.inputs["Points"])
	link(ci.outputs[0], iop.inputs["Instance"])
	link(idx.outputs[0], iop.inputs["Instance Index"])
	link(rot.outputs[0], iop.inputs["Rotation"])
	link(sc.outputs[0], iop.inputs["Scale"])
	join = n.new("GeometryNodeJoinGeometry")
	link(iop.outputs["Instances"], join.inputs[0])
	link(gi.outputs[0], join.inputs[0])
	link(join.outputs[0], go.inputs[0])
	mod = obj.modifiers.new(name, "NODES")
	mod.node_group = ng
	return mod


def grass_style():
	"""GrassDensity, with the chosen style's numbers on top (--grass <style> or Beauty.GrassStyle; styles in
	Beauty.GrassStyles, docs/style/grass.md)"""
	gd = dict(BT["GrassDensity"])
	st = flag_value("--grass", BT.get("GrassStyle"))
	if st:
		gd.update(BT.get("GrassStyles", {})[st])
	return gd


def grass_layers(ground):
	"""grass from the bench's methods and the Vale tests (docs/style/grass.md): a carpet of short blades, taller clumps in
	patches and at the feet of rocks, trees and walls, a few darker accent tufts, flowers in patches, pebbles by trails and
	water. Grass takes the ground colour under each clump; "matched" styles keep the blades within a few percent of it, each
	clump nudged cooler/darker or warmer/lighter (Roblox: terrain decoration grass, which takes the ground's MaterialColor,
	plus a few MeshPart tufts tinted to the ground)."""
	gd = grass_style()
	h = BT.get("GrassHeight", 1.25)
	vary = gd.get("Vary") or None
	if gd.get("Carpet", 0) > 0:
		carpet = [blade_clump(f"Carpet{k}", 330 + k, gd.get("CarpetBlades", 26), h * gd.get("CarpetHeight", 0.45), gd.get("CarpetWidth", 0.035), 0.6,
							  low=gd.get("Root", 0.55), high=gd.get("Tip", 1.3)) for k in range(3)]
		gk_scatter(ground, "Carpet", "grass", carpet, gd["Carpet"], (0.8, 1.25), 1, match=True,
				   material=matched_material("CarpetMat", tint=gd.get("Tint", "f2ffd8"), vary=vary), vary=bool(vary))
	if gd.get("Drift", 0) > 0:
		drift = [blade_clump(f"Drift{k}", 350 + k, gd.get("DriftBlades", 18), h * gd.get("DriftHeight", 1.2), gd.get("DriftWidth", 0.07), gd.get("DriftSpread", 0.4),
							 low=gd.get("DriftRoot", gd.get("Root", 0.55)), high=gd.get("DriftTip", gd.get("Tip", 1.3))) for k in range(4)]
		gk_scatter(ground, "Drifts", "drift", drift, gd["Drift"], (0.8, 1.4), 5, match=True,
				   material=matched_material("DriftMat", tint=gd.get("DriftTint", "f6ffe0"), vary=vary), vary=bool(vary))
	if gd.get("Accent", 0) > 0:  # the dark tufts, now only a sprinkle
		acc = [blade_clump(f"Accent{k}", 370 + k, 12, h * gd.get("AccentHeight", 1.0), 0.08, 0.35) for k in range(3)]
		gk_scatter(ground, "Accents", "accent", acc, gd["Accent"], (0.8, 1.3), 7, match=True, material=matched_material("AccentMat", tint=gd.get("AccentTint", "b4c89a")))
	fl = [kit.flowers(f"Flower{k}", 400 + k, kind=kind, count=12 if kind == "white" else 4) for k, kind in enumerate(("white", "yellow", "white", "yellow"))]
	blue = kit.flowers("FlowerBlue", 410, kind="white", count=9)
	for lp in blue.data.color_attributes["Col"].data:
		c = lp.color
		if c[0] > 0.6 and c[1] > 0.6:
			lp.color = (*kit.to_linear(kit.srgb("7b93e8")), 1)
	gk_scatter(ground, "Flowers", "flowers", fl + [blue], 1.0, (0.8, 1.3), 11)
	pebbles = [brighten(kit.boulder(f"Pebble{k}", 450 + k, size=(0.7, 0.55, 0.4)), BT.get("PebbleLight", 1.0)) for k in range(3)]
	gk_scatter(ground, "Pebbles", "pebbles", pebbles, 1.0, (0.5, 1.6), 21)
	fu = BT.get("Undergrowth")
	if fu:  # ferns under the trees, in the forest floor's own colour (slightly fresher)
		ferns = [fern(f"Fern{k}", 520 + k, fronds=7 + k, length=fu.get("Length", 1.8)) for k in range(3)]
		gk_scatter(ground, "Ferns", "ferns", ferns, fu.get("Density", 0.35), (0.8, 1.4), 41, match=True,
				   material=matched_material("FernMat", tint=fu.get("Tint", "eef8dc"), vary=fu.get("Vary") or None),
				   vary=bool(fu.get("Vary")))
	if BT.get("Patches"):  # flower beds: one kind per bed
		bw = [kit.flowers(f"BedWhite{k}", 420 + k, kind="white", count=14) for k in range(2)]
		gk_scatter(ground, "BedsWhite", "bed_white", bw, BT["Patches"].get("BedDensity", 1.6), (0.8, 1.2), 51)
		by = [kit.flowers(f"BedYellow{k}", 430 + k, kind="yellow", count=10) for k in range(2)]
		gk_scatter(ground, "BedsYellow", "bed_yellow", by, BT["Patches"].get("BedDensity", 1.6), (0.8, 1.2), 53)
	cr = BT.get("Fields", {}).get("Crops")
	if cr:  # crops take the field's colour under them: golden wheat, green leafy rows
		wheat = [blade_clump(f"Wheat{k}", 480 + k, 9, cr.get("WheatHeight", 2.2), 0.05, 0.22, low=0.85, high=1.25) for k in range(3)]
		gk_scatter(ground, "WheatField", "wheat", wheat, cr.get("Wheat", 4.0), (0.85, 1.15), 31, match=True, material=matched_material("WheatMat", tint="fff8e8"))
		greens = [blade_clump(f"Greens{k}", 490 + k, 7, cr.get("GreensHeight", 0.9), 0.24, 0.22, low=0.8, high=1.15) for k in range(3)]
		gk_scatter(ground, "GreenRows", "greens", greens, cr.get("Greens", 2.5), (0.8, 1.2), 33, match=True, material=matched_material("GreensMat", tint="f4fbe8"))


def set_density(G, ground, cam_map, fwd_map, view):
	"""write this view's grass/flower/pebble density into the ground mesh: zone amount x distance falloff x in front.
	Placement (docs/style/grass.md): nothing on the trails; the carpet comes back short and thin at a trail's edge and fills
	in over a few studs (worn verge); taller clumps keep further off, gather in patches and in a ring at the feet of rocks,
	trees and walls (shelter); flowers in patches, off the trails."""
	X, Y = G.X, G.Y
	dx, dy = X - cam_map[0], Y - cam_map[1]
	d = np.hypot(dx, dy) + 1e-6
	front = smoothstep(-0.35, 0.1, (dx * fwd_map[0] + dy * fwd_map[1]) / d)
	gd = grass_style()
	maxd = view.get("GrassDist", gd.get("Dist", 230))
	fall = np.clip(1 - d / maxd, 0, 1) ** gd.get("FallPower", 0.9)
	base = zone_table(G, "Grass", 0.9)
	clear = (G.d_water > 1.5) & (G.slope < 0.9) & (G.dh > G.island["Radius"] - 2)
	clear = clear * (1 - G.no_grass)
	half = BT["Ground"].get("PathHalf", 3.2)
	verge = smoothstep(half + gd.get("VergeFrom", 0.2), half + gd.get("VergeTo", 4.0), G.d_path)  # 0 on the trail
	g = base * fall * front * clear * verge ** 0.7
	off_trail = smoothstep(half + 2.0, half + 7.0, G.d_path)
	fl = smoothstep(0.55, 0.8, lb.noise(X, Y, 18, 61) * 0.5 + 0.5) * clear * front * np.clip(1 - d / (maxd * 0.6), 0, 1) * (G.zone != 2) * smoothstep(half + 1, half + 3, G.d_path)
	pebbles = (smoothstep(1.6, 0.0, np.abs(G.d_path - half - 0.4)) + smoothstep(4, 0.5, G.d_water) * (G.d_water > 0)) * fall * front
	pebbles = pebbles * (G.dh > G.island["Radius"] + 4)  # not on the town's cobbles
	patch = smoothstep(0.55, 0.75, noise2d.fbm(X / 16, Y / 16, 62, 3) * 0.5 + 0.5)
	db = gd.get("DriftBase", 0.0)  # clumps outside the patches too
	shelter = G.shelter * gd.get("Shelter", 0.0)
	drift = np.clip((db + patch * (1 - db)) * (1 - gd.get("Shelter", 0.0) * 0.5) + shelter, 0, 1) * clear * front * fall * base * off_trail * view.get("Drift", 1.0)
	accent = smoothstep(0.7, 0.85, noise2d.fbm(X / 11, Y / 11, 63, 3) * 0.5 + 0.5) * clear * front * fall * base * off_trail
	pt = getattr(G, "patch", None)
	beds = []
	if pt is not None and BT.get("Patches"):
		pk = BT["Patches"]
		g = g * (1 - pt["bare"]) * (1 + pk.get("CloverGrass", 0.25) * pt["clover"]) * (1 - pk.get("DryThin", 0.35) * pt["dry"]) * (1 - 0.5 * pt["stones"])
		drift = drift * (1 - pt["bare"]) * (1 - 0.3 * pt["clover"]) + pk.get("DryClumps", 0.6) * pt["dry"] * fall * front * clear
		accent = accent * (1 - pt["bare"])
		fl = fl * (1 - pt["bare"]) + pk.get("CloverFlowers", 0.35) * pt["clover"] * fall * front
		# flower beds: each bed one kind (by its seed), dense, fading toward its edge
		bed_w, bed_y = np.zeros(X.shape), np.zeros(X.shape)
		for kind, x, y, r, sd in G.patch_list:
			if kind != "flowers":
				continue
			R2 = r * 1.4
			i0, i1 = np.searchsorted(G.xs, [x - R2, x + R2])
			j0, j1 = np.searchsorted(G.ys, [y - R2, y + R2])
			if i1 <= i0 or j1 <= j0:
				continue
			m = smoothstep(1.0, 0.4, np.hypot(X[j0:j1, i0:i1] - x, Y[j0:j1, i0:i1] - y) / r)
			tgt = bed_w if sd % 2 else bed_y
			tgt[j0:j1, i0:i1] = np.maximum(tgt[j0:j1, i0:i1], m)
		beds = [("bed_white", bed_w * fall * front * clear * pk.get("Beds", 1.0)), ("bed_yellow", bed_y * fall * front * clear * pk.get("Beds", 1.0))]
	me = ground.data
	crops = [(k, G.crop[k] * fall * front * (G.d_path > half + 1)) for k in ("wheat", "greens")] + beds
	fu = BT.get("Undergrowth", {})
	# ferns where trees shade the floor (the painted occlusion), more in the named forests, off the trails
	shade = np.clip(G.under_trees * 1.5, 0, 1) if hasattr(G, "under_trees") else 0
	forest = zone_table(G, "Ferns", 0.0)
	crops.append(("ferns", np.clip(shade * 0.6 + forest, 0, 1) * smoothstep(half + 1.5, half + 4, G.d_path) * fall * front * clear * fu.get("On", 1.0)))
	for name, arr in [("grass", g), ("drift", drift), ("accent", accent), ("flowers", fl * gd.get("Flowers", 0.25)), ("pebbles", np.clip(pebbles, 0, 1) * gd.get("Pebbles", 0.2))] + crops:
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
		out = yaw_toward(x, y, 2 * x - hx, 2 * y - hy)  # banners face out over the moat
		if t % 2:
			put("WallTowerB", lambda: kv.round_tower("WallTowerB", 12, 4.2, 17, banner=True), coll, x, y, out, sink=1.0)
		else:
			put("WallTower", lambda: kv.round_tower("WallTower", 11, 4.2, 17), coll, x, y, out, sink=1.0)
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


TREE_STYLE = BT.get("TreeStyle", "smooth")  # broadleaf canopies: smooth blobs or flat-shaded clumps (--trees facet)
BUSH_COLOURS = {"dark": BT.get("Bush", {}).get("Dark", "pine_dark"), "light": BT.get("Bush", {}).get("Light", "leaf")}


def brighten(obj, k):
	"""scale an object's vertex colours (linear) by k: small stones that read too dark against light grass"""
	for d in obj.data.color_attributes["Col"].data:
		c = d.color
		d.color = (min(1.0, c[0] * k), min(1.0, c[1] * k), min(1.0, c[2] * k), c[3])
	return obj


def trees_and_rocks(coll, ao):
	ts = BT["Trees"]
	species = {
		"oak": [lambda i=i: kv.broadleaf(f"Oak{i}", 100 + i, 16, kind="oak", style=TREE_STYLE) for i in range(4)],
		"round": [lambda i=i: kv.broadleaf(f"Round{i}", 110 + i, 13, kind="round", style=TREE_STYLE) for i in range(3)],
		"poplar": [lambda i=i: kv.broadleaf(f"Poplar{i}", 120 + i, 18, kind="poplar", style=TREE_STYLE) for i in range(2)],
		"autumn": [lambda i=i: kv.broadleaf(f"Autumn{i}", 130 + i, 15, kind="oak", autumn=True, style=TREE_STYLE) for i in range(2)],
		"pine": [lambda i=i: kit.pine(f"Pine{i}", 140 + i, 26) for i in range(4)],
		"bush": [lambda i=i: kit.bush(f"Bush{i}", 150 + i, size=4.0, **BUSH_COLOURS) for i in range(3)],
	}
	X0, Y0 = -lb.B.get("Border", 300) + 60, -lb.B.get("Border", 300) + 60
	X1, Y1 = lb.W + lb.B.get("Border", 300) - 60, lb.H + lb.B.get("Border", 300) - 60
	counts = {}
	cell = BT.get("TreeCell", 9.0)
	for v in BT["Views"]:  # random trees keep clear of the hero cameras (framing props are placed on purpose)
		at = v.get("Player") or v["From"]  # walk views: just off the player's own spot
		AVOID.append((at[0], at[1], v.get("Clear", 8 if "Player" in v else 22)))
		if "Player" in v:  # and off the camera behind them, so it never sits inside a canopy
			px, py = v["Player"]
			fx_, fy_ = v["Facing"][0] - px, v["Facing"][1] - py
			n_ = math.hypot(fx_, fy_)
			back = v.get("Cam", {}).get("Back", 10)
			AVOID.append((px - fx_ / n_ * back, py - fy_ / n_ * back, 10))
		ahead = v.get("ClearAhead", 0)  # vistas: a widening lane along the view kept open too
		if ahead and "From" in v:
			fx, fy = v["From"]
			dx, dy = v["To"][0] - fx, v["To"][1] - fy
			n = math.hypot(dx, dy)
			for d in np.arange(15, ahead, 12):
				AVOID.append((fx + dx / n * d, fy + dy / n * d, 10 + d * 0.3))
	y = Y0
	while y < Y1:
		x = X0
		while x < X1:
			px, py = x + R.uniform(-0.45, 0.45) * cell, y + R.uniform(-0.45, 0.45) * cell
			x += cell
			zn = G.zone_name(px, py) or "_gap"
			spec = ts.get(zn, ts["_gap"])
			rim = G.at(G.edge, px, py) < ts.get("_rim", {}).get("From", -1e9)
			if rim:  # the mountains' lower slopes: pine forest up to a wandering tree line
				spec = ts["_rim"]
			grove = float(lb.noise(np.array(px), np.array(py), spec.get("GroveScale", 120), 71)) * 0.5 + 0.5
			p = spec["Density"] * smoothstep(spec.get("GroveFrom", 0.0), spec.get("GroveFrom", 0.0) + 0.25, grove)
			if rim:
				tl = spec.get("Treeline", 90) + float(lb.noise(np.array(px), np.array(py), 150, 72)) * spec.get("TreelineVar", 35)
				p *= float(smoothstep(tl + 12, tl - 12, G.z(px, py)))
			if R.random() > p:
				continue
			if G.at(G.d_water, px, py) < 5 or G.at(G.d_path, px, py) < ts.get("PathClear", 7) or G.at(G.slope, px, py) > spec.get("MaxSlope", 1.1):
				continue
			if G.at(G.dh, px, py) < G.island["Radius"] + 22 or not free(px, py, 2) or G.at(G.fields, px, py) > 0.3:
				continue
			kind = R.choices(list(spec["Mix"]), weights=list(spec["Mix"].values()))[0]
			v = R.randrange(len(species[kind]))
			hmin, hmax = spec.get("Height", [0.8, 1.25])
			put(f"T_{kind}{v}", species[kind][v], coll, px, py, R.uniform(0, 6.28), scale=R.uniform(hmin, hmax), sink=0.5)
			ao.append((px, py, 6 if kind != "bush" else 3, 0.35 if kind != "bush" else 0.25))
			counts[kind] = counts.get(kind, 0) + 1
		y += cell
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
	outcrops(coll, ao)


def outcrops(coll, ao):
	"""rock outcrops (Beauty.Outcrops, docs/style/landscape-review.md): the walk-scale landforms the rolling terrain lacks.
	Big boulders half-buried on slopes and crests, leaning with the hill, each with a few smaller stones around its foot;
	they break the grass into shapes, hide what's behind and give paths something to bend around"""
	oc = BT.get("Outcrops")
	if not oc:
		return
	X0, Y0 = -60, -60
	X1, Y1 = lb.W + 60, lb.H + 60
	half = BT["Ground"].get("PathHalf", 3.2)
	n, tries = 0, 0
	while n < oc.get("Count", 70) and tries < oc.get("Count", 70) * 40:
		tries += 1
		px, py = R.uniform(X0, X1), R.uniform(Y0, Y1)
		sl = G.at(G.slope, px, py)
		cv = G.at(G.curv, px, py)
		if (G.at(G.d_path, px, py) < half + oc.get("PathGap", 6) or G.at(G.d_water, px, py) < 6 or G.at(G.dh, px, py) < G.island["Radius"] + 30
				or G.at(G.fields, px, py) > 0.05 or not free(px, py, 6)):
			continue
		# slopes and crests: favour 0.2-0.9 slope and convex ground
		want = smoothstep(0.12, 0.35, sl) * smoothstep(1.2, 0.8, sl) * (0.5 + 0.5 * float(np.clip(-cv * 30, 0, 1)))
		if R.random() > float(want):
			continue
		big = R.uniform(*oc.get("Scale", (2.6, 5.0)))
		# lean with the slope: tilt toward downhill a little
		gx = G.z(px + 2, py) - G.z(px - 2, py)
		gy = G.z(px, py + 2) - G.z(px, py - 2)
		tilt = (max(-0.35, min(0.35, gy * 0.08)), max(-0.35, min(0.35, -gx * 0.08)))
		put(f"Outcrop{n % 4}", lambda n=n: brighten(kv.mossy_boulder(f"Outcrop{n % 4}", 240 + n % 4, (7, 6, 4.5), moss=0.55), oc.get("Light", 1.0)), coll, px, py, R.uniform(0, 6.28),
			scale=big, sink=big * oc.get("Bury", 1.6), tilt=tilt)
		ao.append((px, py, 4.5 * big, 0.35))
		AVOID.append((px, py, 3.2 * big))
		for _ in range(R.randint(2, 4)):
			a, d = R.uniform(0, math.tau), big * R.uniform(3.2, 5.5)
			sx, sy = px + math.cos(a) * d, py + math.sin(a) * d
			if G.at(G.d_path, sx, sy) < half + 1.5:
				continue
			sm = big * R.uniform(0.15, 0.35)
			put(f"Outcrop{(n + 2) % 4}", lambda n=n: brighten(kv.mossy_boulder(f"Outcrop{(n + 2) % 4}", 240 + (n + 2) % 4, (7, 6, 4.5), moss=0.55), oc.get("Light", 1.0)), coll, sx, sy,
				R.uniform(0, 6.28), scale=sm, sink=sm * 1.2)
			ao.append((sx, sy, 4 * sm, 0.25))
		n += 1
	log(f"outcrops: {n}")


def smooth_line(pts, iters=3):
	"""Chaikin corner cutting: a smooth line through a path's points (the ends stay put)"""
	p = [Vector((x, y)) for x, y in pts]
	for _ in range(iters):
		q = [p[0]]
		for a, b in zip(p, p[1:]):
			q += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
		q.append(p[-1])
		p = q
	return p


def resample(p, step):
	"""points every `step` studs along a polyline"""
	out, carry = [p[0]], 0.0
	for a, b in zip(p, p[1:]):
		seg = (b - a).length
		t = step - carry
		while t <= seg:
			out.append(a.lerp(b, t / seg))
			t += step
		carry = seg - (t - step)
	if (out[-1] - p[-1]).length > step * 0.3:
		out.append(p[-1])
	return out


def trails(coll, ao):
	"""the paths as ribbon meshes laid on the ground (Beauty.Trails, docs/style/ground.md): the crisp edge the terrain's
	soft vertex colour can't give, a worn dip with two wheel ruts, a grassy crown on country lanes, a scuffed margin, each
	face its own shade of dirt, stones half-sunk along the edges. Breaks for the town's cobbles and for water (bridges
	carry the road). Roblox: MeshParts with vertex colours laid on the terrain."""
	tc = BT.get("Trails")
	if not tc:
		return
	half = BT["Ground"].get("PathHalf", 3.2)
	lanes = [-1.0, -0.78, -0.5, -0.24, 0.24, 0.5, 0.78, 1.0]
	lift = [tc.get("EdgeLift", 0.03)] + [tc.get("Lift", 0.12)] * (len(lanes) - 2) + [tc.get("EdgeLift", 0.03)]
	mat = detail_material("TrailMat", (tc.get("Texture", "ground_dirt.png"), tc.get("Tile", 8.0)), (), tc.get("Strength", 0.8))
	crown = tc.get("Crown", {})
	n_runs, stones = 0, []
	for k, line in enumerate(M["Paths"]):
		pts = resample(smooth_line(line), tc.get("Step", 1.2))
		runs, cur = [], []
		for q in pts:
			if G.at(G.dh, q.x, q.y) > G.island["Radius"] + 4 and G.at(G.d_water, q.x, q.y) > 0.8:
				cur.append(q)
			elif cur:
				runs.append(cur)
				cur = []
		if cur:
			runs.append(cur)
		hk = half * tc.get("Width", {}).get(str(k), 1.0)
		for run in runs:
			if len(run) < 4:
				continue
			p = kit.Piece(800 + n_runs)
			r = p.rng
			rows, s_acc = [], 0.0
			wob = tc.get("Wobble", 0.12)
			for i, q in enumerate(run):
				t = (run[min(i + 1, len(run) - 1)] - run[max(i - 1, 0)]).normalized()
				nrm = Vector((-t.y, t.x))
				if i:
					s_acc += (q - run[i - 1]).length
				wl = hk * (1 + wob * math.sin(s_acc * 0.21 + k) * math.sin(s_acc * 0.057 + 2 * k))
				wr = hk * (1 + wob * math.sin(s_acc * 0.19 + 3 * k) * math.sin(s_acc * 0.061 + k))
				ring = []
				for f, lf in zip(lanes, lift):
					m = q + nrm * f * (wl if f < 0 else wr)
					ring.append(lb.to_b(m.x, m.y, G.z(m.x, m.y) + lf))
				rows.append(ring)
				if r.random() < tc.get("Stones", 0.06):  # a stone half-sunk at the edge
					side = r.choice((-1, 1))
					m = q + nrm * side * (wl if side < 0 else wr) * r.uniform(0.98, 1.15)
					stones.append((m.x, m.y, r.uniform(0.5, 1.3)))
			counter = iter(range(10**9))
			grassy = crown.get(str(k), False)

			def face_col(f, counter=counter, grassy=grassy, r=r):
				lane = next(counter) % (len(lanes) - 1)
				key = ("Edge", "Dirt", "Rut", "Crown" if grassy else "Dirt", "Rut", "Dirt", "Edge")[lane]
				return kit.jitter(tc["Colours"][key], r, v=0.05)

			p.quad_strip(rows, face_col)
			o = p.finish(f"Trail{k}_{n_runs}", coll, smooth=True)
			o.data.materials.clear()
			o.data.materials.append(mat)
			n_runs += 1
	for j, (x, y, sz) in enumerate(stones):
		put(f"EdgeStone{j % 4}", lambda j=j: kit.boulder(f"EdgeStone{j % 4}", 460 + j % 4, size=(1.6, 1.2, 0.7)), coll, x, y, R.uniform(0, 6.28), scale=sz, sink=0.35)
		ao.append((x, y, 1.6 * sz, 0.15))
	log(f"trails: {n_runs} runs, {len(stones)} edge stones")


def patch_props(coll, ao):
	"""the small things that make patches read up close: bare scrapes as flat irregular decals laid on the ground (a crisp
	edge the 2.5-stud vertex colours can't draw), and stony patches as a cluster: one bigger rock, a few smaller ones"""
	pc = BT.get("Patches")
	if not pc:
		return
	mat = detail_material("PatchMat", ("ground_dirt.png", 8.0), (), 0.8)
	nb, ns = 0, 0
	for kind, x, y, r, sd in G.patch_list:
		q = random.Random(sd)
		if kind == "bare":
			p = kit.Piece(sd)
			n = 14
			ph = [q.uniform(0, math.tau) for _ in range(3)]
			ring = []
			for k in range(n):
				a = k * math.tau / n
				rad = r * (1 + 0.18 * math.sin(a * 2 + ph[0]) + 0.1 * math.sin(a * 3 + ph[1]) + 0.08 * math.sin(a * 5 + ph[2]))
				mx, my = x + math.cos(a) * rad, y + math.sin(a) * rad
				ring.append(lb.to_b(mx, my, G.z(mx, my) + 0.06))
			ctr = lb.to_b(x, y, G.z(x, y) + 0.09)
			p.fan(ctr, ring, lambda f: kit.jitter(pc["Bare"], q, v=0.07), flip=True)
			o = p.finish(f"Bare{nb}", coll, smooth=True)
			o.data.materials.clear()
			o.data.materials.append(mat)
			nb += 1
			for _ in range(q.randint(1, 4)):  # a few pebbles on the scrape
				a, d = q.uniform(0, math.tau), q.uniform(0, r * 0.8)
				put(f"Pebble{nb % 3}", lambda: kit.boulder(f"Pebble{nb % 3}", 450 + nb % 3, size=(0.7, 0.55, 0.4)), coll, x + math.cos(a) * d, y + math.sin(a) * d,
					q.uniform(0, 6.28), scale=q.uniform(0.6, 1.4), sink=0.15)
		elif kind == "stones":
			big = q.uniform(1.1, 2.0)
			put(f"PatchRock{ns % 4}", lambda: kv.mossy_boulder(f"PatchRock{ns % 4}", 230 + ns % 4, (3.2, 2.6, 2.0), moss=0.5), coll, x, y, q.uniform(0, 6.28), scale=big, sink=0.5)
			ao.append((x, y, 2.5 * big, 0.3))
			for _ in range(q.randint(2, 5)):
				a, d = q.uniform(0, math.tau), q.uniform(r * 0.3, r)
				sx, sy = x + math.cos(a) * d, y + math.sin(a) * d
				sm = q.uniform(0.35, 0.8)
				put(f"PatchRock{ns % 4}", lambda: kv.mossy_boulder(f"PatchRock{ns % 4}", 230 + ns % 4, (3.2, 2.6, 2.0), moss=0.5), coll, sx, sy, q.uniform(0, 6.28), scale=sm, sink=0.3)
				ao.append((sx, sy, 2.2 * sm, 0.2))
			ns += 1
	log(f"patch props: {nb} scrapes, {ns} rock clusters")


def signposts(coll, ao):
	"""a signpost at every junction of the Land's paths, off the road's edge, an arrow board along each road leaving it
	(wayfinding without UI: docs/style/look-direction.md)"""
	ends = {}
	for line in M["Paths"]:
		for i, q in enumerate(line):
			nbrs = [line[j] for j in (i - 1, i + 1) if 0 <= j < len(line)]
			ends.setdefault(tuple(q), []).extend(nbrs)
	half = BT["Ground"].get("PathHalf", 3.2)
	n = 0
	for (x, y), nbrs in ends.items():
		if len(nbrs) < 3 or math.hypot(x - G.hub[0], y - G.hub[1]) < G.island["Radius"] + 30:
			continue  # only real junctions, and not in town
		dirs = [Vector((nx - x, ny - y)).normalized() for nx, ny in nbrs]
		# stand in the widest gap between the roads, just off the verge
		angs = sorted(math.atan2(d.y, d.x) for d in dirs)
		gaps = [(angs[(i + 1) % len(angs)] - a) % math.tau for i, a in enumerate(angs)]
		k = max(range(len(gaps)), key=lambda i: gaps[i])
		mid = angs[k] + gaps[k] / 2
		px, py = x + math.cos(mid) * (half + 3.0), y + math.sin(mid) * (half + 3.0)
		arms = tuple(math.atan2(d.x, d.y) for d in dirs)  # map (x, y south) -> Blender yaw about the post: atan2(bx, -by)
		put(f"Signpost{n}", lambda arms=arms, n=n: kv.signpost(f"Signpost{n}", 700 + n, arms), coll, px, py, 0.0, sink=0.3)
		ao.append((px, py, 1.5, 0.2))
		n += 1
	log(f"signposts: {n}")


def hedgerows(coll, ao):
	for k, (x, y) in enumerate(G.hedges):
		put(f"Hedge{k % 3}", lambda k=k: kit.bush(f"Hedge{k % 3}", 160 + k % 3, size=3.2, **BUSH_COLOURS), coll, x, y, R.uniform(0, 6.28), scale=R.uniform(0.75, 1.25), sink=0.5)
		ao.append((x, y, 3.5, 0.25))


FRAMING_KINDS = {
	"pine": lambda s: kit.pine(f"FramePine{s}", 170 + s, 26),
	"oak": lambda s: kv.broadleaf(f"FrameOak{s}", 180 + s, 16, kind="oak"),
	"round": lambda s: kv.broadleaf(f"FrameRound{s}", 190 + s, 13, kind="round"),
	"boulder": lambda s: kv.mossy_boulder(f"FrameRock{s}", 200 + s, (7, 6, 5), moss=0.6),
	"bush": lambda s: kit.bush(f"FrameBush{s}", 210 + s, size=4.0),
}


def framing(view, coll, pos, fwd):
	"""props for one view only, at [right, forward] studs from the camera: a tree or rock at the frame's edge gives the
	shot a foreground (the classic framing device). Returns the objects, removed again after the render."""
	made = []
	right = Vector((fwd.y, -fwd.x, 0)).normalized()
	flat = Vector((fwd.x, fwd.y, 0)).normalized()
	if "Player" in view:  # the player stand-in: 5.2 studs, a Roblox avatar's height
		px, py = view["Player"]
		made.append(put("Hero", lambda: kit.hero("Hero", 7), coll, px, py, yaw_toward(px, py, *view["Facing"]), sink=0.05))
	for k, it in enumerate(view.get("Framing", [])):
		w = pos + right * it["At"][0] + flat * it["At"][1]
		kind, seed = it["Kind"], it.get("Seed", k)
		o = put(f"Frame_{kind}{seed}", lambda kind=kind, seed=seed: FRAMING_KINDS[kind](seed), coll, w.x, -w.y, it.get("Yaw", R.uniform(0, 6.28)),
				scale=it.get("Scale", 1.0), sink=it.get("Sink", 0.5))
		made.append(o)
		log(f"framing {kind} at map ({w.x:.0f}, {-w.y:.0f}), ground {G.z(w.x, -w.y):.1f}")
	return made


def far_world(coll):
	fw = BT["Far"]
	for k, rng_ in enumerate(fw["Ranges"]):
		cx, cy = rng_["At"]
		o = put(f"Range{k}", lambda r=rng_, k=k: kv.mountain_range(f"Range{k}", 500 + k, r["Width"], r["Depth"], r["Height"], peaks=r.get("Peaks", 5), snow=r.get("Snow", 0.62)),
				coll, cx, cy, math.radians(rng_.get("Yaw", 0)), z=rng_.get("Z", -40), sink=0)
	isl = fw.get("Island")
	if isl:  # tipped toward the hub so its top shows from the Vale
		ix, iy = isl["At"]
		yaw = yaw_toward(ix, iy, *G.hub) + math.radians(isl.get("Yaw", 0))
		put("FloatingIsland", lambda: kv.floating_island("FloatingIsland", 600, isl.get("Radius", 140)), coll, ix, iy, yaw, z=isl["Z"], sink=0,
			tilt=(math.radians(isl.get("Tilt", 0)), 0.0))


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
	key = json.dumps(sky, sort_keys=True) + f"{W}x{H}"
	img = bpy.data.images.get("PaintedSky")
	if not img or img.get("key") != key:
		cache = os.path.join(os.path.dirname(os.path.abspath(ARGS[0])), "beauty", "_cache", "sky_" + hashlib.sha1(key.encode()).hexdigest()[:16] + ".npy")
		if os.path.exists(cache):
			col = np.load(cache).astype(np.float32)
		else:
			col = sky_paint.paint(sky, (W, H))
			os.makedirs(os.path.dirname(cache), exist_ok=True)
			np.save(cache, col.astype(np.float16))
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
	fl = BT["Light"].get("Fill")
	if fl:  # Roblox's OutdoorAmbient: a flat fill that reaches under canopies (Blender's sky light is blocked by them)
		fill_o = bpy.data.objects.get("Fill")
		if not fill_o:
			fill_o = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))
			sc.collection.objects.link(fill_o)
		fill_o.data.energy = fl["Strength"]
		fill_o.data.color = kit.to_linear(kit.srgb(fl["Colour"]))
		fill_o.data.use_shadow = False
		fa, fe = math.radians(fl.get("Azimuth", 0)), math.radians(fl.get("Elevation", 90))
		fdir = Vector((math.sin(fa) * math.cos(fe), math.cos(fa) * math.cos(fe), math.sin(fe)))
		fill_o.rotation_euler = (-fdir).to_track_quat("-Z", "Y").to_euler()
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
	if "Player" in view:  # a walk view: over the shoulder of a player standing at Player, facing Facing (Roblox-like)
		px, py = view["Player"]
		fx_, fy_ = view["Facing"][0] - px, view["Facing"][1] - py
		n = math.hypot(fx_, fy_)
		fx_, fy_ = fx_ / n, fy_ / n
		rx, ry = -fy_, fx_  # the player's right, in map coordinates (y south)
		oc = view.get("Cam", {})
		cx, cy = px - fx_ * oc.get("Back", 10) + rx * oc.get("Right", 2.0), py - fy_ * oc.get("Back", 10) + ry * oc.get("Right", 2.0)
		gz = G.z(px, py)
		pos = lb.to_b(cx, cy, gz + oc.get("Up", 6.6))
		ax, ay = px + fx_ * oc.get("Ahead", 40), py + fy_ * oc.get("Ahead", 40)
		look = lb.to_b(ax, ay, gz + oc.get("LookUp", 3.0))
	else:
		fx, fy = view["From"]
		tx, ty = view["To"]
		pos = lb.to_b(fx, fy, (G.z(fx, fy) if "Z" not in view else 0) + view.get("Up", 7) + view.get("Z", 0))
		look = lb.to_b(tx, ty, (G.z(tx, ty) if "ToZ" not in view else 0) + view.get("ToUp", 10) + view.get("ToZ", 0))
	fwd = (look - pos).normalized()
	cam.shift_x, cam.shift_y = 0.0, 0.0
	if view.get("Level"):  # keep verticals upright: look level and slide the frame (lens shift) to aim up or down
		flat = Vector((fwd.x, fwd.y, 0)).normalized()
		pitch = math.atan2(fwd.z, Vector((fwd.x, fwd.y)).length)
		cam.shift_y = math.tan(pitch) / (2 * math.tan(cam.angle_y / 2))
		fwd = flat
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
	lights = [o for o in (bpy.data.objects.get("Sun"), bpy.data.objects.get("Fill")) if o]
	for o in lights:
		o.hide_render = True
	sc.render.filepath = path
	bpy.ops.render.render(write_still=True)
	for o in lights:
		o.hide_render = False
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
	farm_fields(G)
	ground_patches(G)
	ao = []
	for step in (start_circle, town, gatehill, ruins, camp, cave, trees_and_rocks, hedgerows, trails, signposts, patch_props):
		step(coll) if step is start_circle else step(coll, ao)
		log("step", step.__name__)
	far_world(coll)
	log("step far_world")
	ground = ground_mesh(G, coll, ao)
	log("step ground_mesh")
	water_plane(G, coll)
	grass_layers(ground)
	log("step grass_layers")
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
		extra = framing(view, coll, pos, fwd)
		sd = world_light(view)
		sc.render.filepath = os.path.join(vdir, "beauty.png")
		bpy.ops.render.render(write_still=True)
		rng_max = BT.get("Render", {}).get("DepthRange", 12000.0)
		depth_pass(os.path.join(vdir, "depth.png"), rng_max)
		for o in extra:
			bpy.data.objects.remove(o)
		res = BT.get("Render", {}).get("Res", [1600, 900])
		FW, FH = res
		f = (FH / 2) / math.tan(math.radians(view.get("FovV", 60)) / 2)
		right = fwd.cross(Vector((0, 0, 1))).normalized()
		up = right.cross(fwd).normalized()
		meta = {"SkySunDir": list(sd), "DepthRange": rng_max,
				"Camera": {"Pos": list(pos), "Fwd": list(fwd), "Right": list(right), "Up": list(up), "F": f, "Cy": FH / 2 + cam_o.data.shift_y * FH, "Frame": [FW, FH]}}
		json.dump({"Meta": meta}, open(os.path.join(vdir, "placements.json"), "w"), indent=1)
		log(f"view {view['Name']} rendered")
	if "--save" in FLAGS:
		bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "vale.blend"))
	log("done")


G = None
MASTER_COLL = None
kit.PAL.update(BT.get("Palette", {}))
main()
