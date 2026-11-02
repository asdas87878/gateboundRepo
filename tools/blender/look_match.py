"""Rebuild the reference frame in Blender from a scene spec (docs/look-passes.md).

  blender --background --python tools/blender/look_match.py -- <spec.json> <out_dir> [--save] [--no-depth] [--quick]

Writes <out_dir>/beauty.png (16-bit, Standard view), depth.png (16-bit, linear, distance / DepthRange; sky = 1),
placements.json (every placed object in studs: the data the further terrains reuse) and, with --save, scene.blend.
tools/art/look_post.py then adds haze, bloom and the grade; tools/look_pass.py runs the whole pass.

Placement is by the reference image: an object's "Px" is where its base touches the ground in the reference frame
(1336 x 752 px); a ray from the camera through that pixel is marched onto the terrain. "TopPx" is where its top is, and
the object is scaled until its top lands there. So the spec reads like notes on the screenshot.
"""

import json
import math
import os
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
import card_trees  # noqa: E402
import kit  # noqa: E402
import sky_paint  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1 :]
SPEC = json.load(open(ARGS[0], encoding="utf-8"))
OUT = os.path.abspath(ARGS[1])
FLAGS = set(ARGS[2:])
for _k, _v in SPEC.get("Palette", {}).items():
	kit.PAL[_k] = _v
FW, FH = SPEC["Frame"]
T0 = time.time()


def log(*a):
	print(f"[look {time.time() - T0:6.1f}s]", *a, flush=True)


# ---------------------------------------------------------------- camera


class Cam:
	"""a pinhole camera in reference pixels. "HorizonPx" moves the principal point (a lens shift, Blender's shift_y): the
	reference keeps verticals straight with a level camera and the horizon high in the frame, which a tilted camera can't."""

	def __init__(self, c):
		self.pos = Vector((c.get("X", 0.0), c.get("Y", 0.0), c["Height"]))
		self.pitch, self.yaw, self.fov = math.radians(c["Pitch"]), math.radians(c.get("Yaw", 0.0)), math.radians(c["FovV"])
		self.f = (FH / 2) / math.tan(self.fov / 2)
		self.cy = c["HorizonPx"] + self.f * math.tan(self.pitch) if "HorizonPx" in c else FH / 2
		cp, sp = math.cos(self.pitch), math.sin(self.pitch)
		self.fwd = Vector((-math.sin(self.yaw) * cp, math.cos(self.yaw) * cp, -sp))
		self.right = Vector((math.cos(self.yaw), math.sin(self.yaw), 0.0))
		self.up = self.right.cross(self.fwd)

	def ray(self, x, y):
		return (self.fwd * self.f + self.right * (x - FW / 2) + self.up * (self.cy - y)).normalized()

	def project(self, p):
		d = Vector(p) - self.pos
		z = d.dot(self.fwd)
		if z <= 1e-4:
			return None
		return FW / 2 + self.f * d.dot(self.right) / z, self.cy - self.f * d.dot(self.up) / z, z


CAM = Cam(SPEC["Camera"])


# ---------------------------------------------------------------- terrain


def smooth_noise(X, Y, scale, seed, octaves=3):
	r = np.random.RandomState(seed)
	out = np.zeros_like(X)
	amp, tot = 1.0, 0.0
	for o in range(octaves):
		for _ in range(4):
			a, ph = r.uniform(0, math.tau), r.uniform(0, math.tau)
			f = math.tau / scale * (2 ** o) * r.uniform(0.7, 1.3)
			out += amp * np.sin((X * math.cos(a) + Y * math.sin(a)) * f + ph)
			tot += amp
		amp *= 0.5
	return out / tot * 1.8


def bell(t):
	t = np.clip(t, 0, 1)
	return 0.5 * (1 + np.cos(np.pi * t))


def smoothstep(a, b, x):
	t = np.clip((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)


class Ground:
	def __init__(self, t):
		self.t = t
		x0, y0, x1, y1 = t["Extent"]
		self.s = t.get("Step", 1.0)
		self.xs = np.arange(x0, x1 + 1e-6, self.s)
		self.ys = np.arange(y0, y1 + 1e-6, self.s)
		self.X, self.Y = np.meshgrid(self.xs, self.ys)
		self.Z = np.zeros_like(self.X)
		self.far_z = t.get("FarZ", -6.0)
		n = t.get("Noise")
		if n:
			self.Z += smooth_noise(self.X, self.Y, n["Scale"], n.get("Seed", 1)) * n["Amp"]
		self.road_d = np.full_like(self.X, 1e9)  # distance to the nearest road edge (negative inside)
		self.road_half = np.ones_like(self.X)  # that road's half width there
		self.road_t = np.zeros_like(self.X)  # along-road position (for rut stripes)
		self.road_cfg = np.full(self.X.shape, -1, np.int32)

	def height(self, x, y):
		fx = (np.asarray(x, np.float64) - self.xs[0]) / self.s
		fy = (np.asarray(y, np.float64) - self.ys[0]) / self.s
		inside = (fx >= 0) & (fy >= 0) & (fx <= len(self.xs) - 1) & (fy <= len(self.ys) - 1)
		fx = np.clip(fx, 0, len(self.xs) - 1.001)
		fy = np.clip(fy, 0, len(self.ys) - 1.001)
		i, j = fx.astype(int), fy.astype(int)
		u, v = fx - i, fy - j
		Z = self.Z
		z = (Z[j, i] * (1 - u) * (1 - v) + Z[j, i + 1] * u * (1 - v) + Z[j + 1, i] * (1 - u) * v + Z[j + 1, i + 1] * u * v)
		return np.where(inside, z, self.far_z)

	def hit(self, o, d, max_t=4000.0):
		t = 0.3
		prev = t
		while t < max_t:
			p = o + d * t
			if p.z <= float(self.height(p.x, p.y)):
				lo, hi = prev, t
				for _ in range(30):
					mid = (lo + hi) / 2
					q = o + d * mid
					if q.z <= float(self.height(q.x, q.y)):
						hi = mid
					else:
						lo = mid
				return o + d * hi
			prev = t
			t += max(0.15, t * 0.006)
		return None

	def hit_px(self, px):
		return self.hit(CAM.pos, CAM.ray(*px))

	def apply_features(self):
		for f in self.t.get("Features", []):
			kind = f["Kind"]
			if kind in ("Hill", "Plateau"):
				c = self.anchor(f)
				sx, sy = f.get("Squash", (1.0, 1.0))
				ang = math.radians(f.get("Angle", 0.0))
				dx, dy = self.X - c[0], self.Y - c[1]
				rx = (dx * math.cos(ang) + dy * math.sin(ang)) / sx
				ry = (-dx * math.sin(ang) + dy * math.cos(ang)) / sy
				d = np.hypot(rx, ry) / f["Radius"]
				if kind == "Hill":
					self.Z += f["Height"] * bell(d) ** f.get("Power", 1.0)
				else:
					top = f.get("Top", 0.6)
					self.Z += f["Height"] * smoothstep(1.0, top, d)
			elif kind == "Ridge":
				pts = self.line(f)
				dist, _ = self.line_dist(pts, f["Width"] / 2 + 1)
				self.Z += f["Height"] * bell(dist / (f["Width"] / 2)) ** f.get("Power", 1.0)
			elif kind == "Tilt":
				a = math.radians(f["Dir"])
				c = self.anchor(f)
				along = (self.X - c[0]) * math.cos(a) + (self.Y - c[1]) * math.sin(a)
				w = 1.0
				if "Radius" in f:
					w = bell(np.hypot(self.X - c[0], self.Y - c[1]) / f["Radius"])
				self.Z += np.clip(along, f.get("Min", -1e9), f.get("Max", 1e9)) * f["Slope"] * w

	def anchor(self, f):
		if "At" in f:
			return f["At"]
		p = flat_px(f["Px"], f.get("Z", 0.0))
		return (p.x, p.y)

	def line(self, f):
		if "Line" in f:
			pts = [Vector((x, y, 0)) for x, y in f["Line"]]
		else:
			pts = []
			for px in f["PxLine"]:
				h = self.hit_px(px)
				pts.append(h if h is not None else flat_px(px, 0.0))
		return densify(pts, 1.0)

	def window(self, x0, y0, x1, y1):
		i0, i1 = np.searchsorted(self.xs, [x0, x1])
		j0, j1 = np.searchsorted(self.ys, [y0, y1])
		return slice(max(0, j0), min(len(self.ys), j1 + 1)), slice(max(0, i0), min(len(self.xs), i1 + 1))

	def line_dist(self, pts, reach):
		"""distance from grid vertices within `reach` of a polyline to it, and the along-line distance of the nearest
		point (1e9 / 0 further away)"""
		best = np.full_like(self.X, 1e9)
		along = np.zeros_like(self.X)
		acc = 0.0
		for a, b in zip(pts, pts[1:]):
			ab = b - a
			L2 = ab.x * ab.x + ab.y * ab.y
			if L2 < 1e-9:
				continue
			wj, wi = self.window(min(a.x, b.x) - reach, min(a.y, b.y) - reach, max(a.x, b.x) + reach, max(a.y, b.y) + reach)
			X, Y = self.X[wj, wi], self.Y[wj, wi]
			t = np.clip(((X - a.x) * ab.x + (Y - a.y) * ab.y) / L2, 0, 1)
			d = np.hypot(X - (a.x + ab.x * t), Y - (a.y + ab.y * t))
			bw, aw = best[wj, wi], along[wj, wi]
			m = d < bw
			bw[m] = d[m]
			aw[m] = acc + t[m] * math.sqrt(L2)
			acc += math.sqrt(L2)
		return best, along

	def pad(self, x, y, z, radius, blend):
		"""level the ground to z within radius, easing back over `blend` (a base for a structure)"""
		wj, wi = self.window(x - radius - blend, y - radius - blend, x + radius + blend, y + radius + blend)
		d = np.hypot(self.X[wj, wi] - x, self.Y[wj, wi] - y)
		w = smoothstep(radius + blend, radius, d)
		self.Z[wj, wi] = self.Z[wj, wi] * (1 - w) + z * w

	def carve_roads(self, roads):
		self.roads = []
		for k, r in enumerate(roads):
			if r.get("Off"):
				continue
			raw = r["Line"] if "Line" in r else r["PxLine"]
			# a point may carry its own width as a third number: [x, y, width]
			ctrl_w = [q[2] if len(q) > 2 else None for q in raw]
			if "Line" in r:
				ctrl = [Vector((q[0], q[1], 0)) for q in raw]
			else:
				ctrl = [self.hit_px(q[:2]) or flat_px(q[:2], 0) for q in raw]
			ctrl_cum = np.concatenate([[0], np.cumsum([(b - a).length for a, b in zip(ctrl, ctrl[1:])])])
			pts = densify(chaikin(ctrl, 3), 1.5)
			# centre heights from the terrain, smoothed along the road
			zc = np.array([float(self.height(p.x, p.y)) for p in pts])
			win = max(1, int(r.get("Smooth", 9)))
			zc = np.convolve(np.pad(zc, win, mode="edge"), np.ones(win) / win, mode="same")[win : win + len(zc)]
			for p, z in zip(pts, zc):
				p.z = z - r.get("Depth", 0.4)
			self.roads.append((pts, r))
			wd = r.get("Width", 6.0)
			w0, w1 = (wd, wd) if not isinstance(wd, list) else wd
			bank = r.get("Bank", 4.0)
			cum = np.concatenate([[0], np.cumsum([(b - a).length for a, b in zip(pts, pts[1:])])])
			if any(w is not None for w in ctrl_w):
				# widths given per control point: spread along the smoothed line by relative length
				ws = [w if w is not None else w0 for w in ctrl_w]
				rel = ctrl_cum / max(ctrl_cum[-1], 1e-6)
				dist, along = self.line_dist(pts, max(ws) / 2 + bank + 4)
				half = np.interp(np.clip(along / max(cum[-1], 1e-6), 0, 1), rel, ws) / 2
			else:
				dist, along = self.line_dist(pts, max(w0, w1) / 2 + bank + 4)
				half = (w0 + (w1 - w0) * np.clip(along / max(cum[-1], 1e-6), 0, 1)) / 2
			zline = np.interp(along, cum, [p.z for p in pts])
			w = smoothstep(half + bank, half * 0.8, dist)
			self.Z = self.Z * (1 - w) + zline * w
			edge = dist - half
			m = edge < self.road_d
			self.road_d[m] = edge[m]
			self.road_half[m] = (half * np.ones_like(edge))[m]
			self.road_t[m] = along[m]
			self.road_cfg[m] = k


def densify(pts, step):
	out = [pts[0].copy()]
	for a, b in zip(pts, pts[1:]):
		n = max(1, int((b - a).length / step))
		for i in range(1, n + 1):
			out.append(a.lerp(b, i / n))
	return out


def chaikin(pts, it):
	for _ in range(it):
		new = [pts[0]]
		for a, b in zip(pts, pts[1:]):
			new += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
		new.append(pts[-1])
		pts = new
	return pts


def flat_px(px, z=0.0):
	d = CAM.ray(*px)
	if d.z >= -1e-6:
		return CAM.pos + d * 3000
	t = (z - CAM.pos.z) / d.z
	return CAM.pos + d * t


# ---------------------------------------------------------------- terrain colours and mesh


def hexlin(h):
	return np.array(kit.to_linear(kit.srgb(h)), np.float64)


def terrain_colours(G, ao_spots):
	t = G.t["Colour"]
	X, Y = G.X, G.Y
	n1 = smooth_noise(X, Y, t.get("PatchScale", 28), 11) * 0.5 + 0.5
	n2 = smooth_noise(X, Y, t.get("PatchScale", 28) * 0.35, 12) * 0.5 + 0.5
	n3 = smooth_noise(X, Y, 3.0, 13)
	a, b, c = hexlin(t["GrassA"]), hexlin(t["GrassB"]), hexlin(t.get("GrassC", t["GrassB"]))
	col = a[None, None] * (1 - n1[..., None]) + b[None, None] * n1[..., None]
	dark = smoothstep(0.55, 0.85, n2)[..., None] * t.get("PatchDark", 0.3)
	col = col * (1 - dark) + c[None, None] * dark
	if "GrassLight" in t:  # sunny yellow-green patches
		n4 = smooth_noise(X, Y, t.get("PatchScale", 28) * 0.6, 14) * 0.5 + 0.5
		light = smoothstep(0.6, 0.9, n4)[..., None] * t.get("PatchLight", 0.4)
		col = col * (1 - light) + hexlin(t["GrassLight"])[None, None] * light
	col *= (1 + n3 * t.get("Grain", 0.04))[..., None]
	# roads: colour with a soft, wobbly edge and a worn halo of paler grass outside it
	if G.roads:
		wob = smooth_noise(X, Y, t.get("EdgeScale", 6.0), 21) * t.get("EdgeWobble", 0.6)
		e = G.road_d + wob
		rc = hexlin(t["Road"])
		re = hexlin(t.get("RoadEdge", t["Road"]))
		soft = t.get("EdgeSoft", 1.2)
		w_road = smoothstep(soft / 2, -soft / 2, e)[..., None]
		inner = smoothstep(-0.2, -t.get("EdgeBand", 2.5), e)[..., None]  # 0 at the edge, 1 well inside
		rn = smooth_noise(X, Y, 9.0, 31) * 0.5 + 0.5
		rcol = re[None, None] * (1 - inner) + rc[None, None] * inner
		rcol *= (1 + (rn[..., None] - 0.5) * t.get("RoadVar", 0.08))
		if t.get("Ruts"):  # two worn wheel tracks, a little darker, at 45% of the half width from the middle
			centre_d = np.abs(G.road_half + G.road_d)  # distance from the road's centre line
			rut = np.exp(-((centre_d - G.road_half * 0.45) / np.maximum(0.25, G.road_half * 0.1)) ** 2)
			rcol *= (1 - rut * t["Ruts"])[..., None]
		worn = (smoothstep(t.get("WornWidth", 2.5), 0.0, e) * (1 - w_road[..., 0]))[..., None] * t.get("Worn", 0.35)
		col = col * (1 - worn) + hexlin(t.get("WornColour", t["Road"]))[None, None] * worn
		col = col * (1 - w_road) + rcol * w_road
	# painted occlusion at the feet of trees, rocks and walls
	ao = np.ones(X.shape)
	for x, y, r, k in ao_spots:
		i0, i1 = np.searchsorted(G.xs, [x - r, x + r])
		j0, j1 = np.searchsorted(G.ys, [y - r, y + r])
		if i1 <= i0 or j1 <= j0:
			continue
		d = np.hypot(X[j0:j1, i0:i1] - x, Y[j0:j1, i0:i1] - y) / r
		ao[j0:j1, i0:i1] *= 1 - k * bell(d)
	col *= ao[..., None]
	return col


def build_terrain(G, coll, ao_spots):
	ny, nx = G.X.shape
	verts = np.stack([G.X, G.Y, G.Z], -1).reshape(-1, 3)
	idx = np.arange(nx * ny).reshape(ny, nx)
	quads = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
	mesh = bpy.data.meshes.new("Terrain")
	mesh.vertices.add(len(verts))
	mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
	mesh.loops.add(len(quads) * 4)
	mesh.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
	mesh.polygons.add(len(quads))
	mesh.polygons.foreach_set("loop_start", np.arange(0, len(quads) * 4, 4, dtype=np.int32))
	mesh.update(calc_edges=True)
	mesh.validate()
	mesh.polygons.foreach_set("use_smooth", np.ones(len(quads), bool))
	col = terrain_colours(G, ao_spots).reshape(-1, 3)
	attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	rgba = np.concatenate([col, np.ones((len(col), 1))], 1).astype(np.float32)
	attr.data.foreach_set("color", rgba.ravel())
	mesh.materials.append(kit.vertex_material())
	obj = bpy.data.objects.new("Terrain", mesh)
	coll.objects.link(obj)
	# far ground: one big plane under everything, beyond the grid
	far = bpy.data.meshes.new("FarGround")
	S = 6000
	far.from_pydata([(-S, -S, G.far_z), (S, -S, G.far_z), (S, S, G.far_z), (-S, S, G.far_z)], [], [(0, 1, 2, 3)])
	fa = far.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
	fc = (*hexlin(G.t["Colour"].get("Far", G.t["Colour"]["GrassB"])), 1.0)
	for d in fa.data:
		d.color = fc
	far.materials.append(kit.vertex_material())
	fo = bpy.data.objects.new("FarGround", far)
	coll.objects.link(fo)
	return obj


# ---------------------------------------------------------------- kit instances

MASTERS = {}
MASTER_COLL = None
PLACED = []


def master(kind, args, seed):
	key = (kind, json.dumps(args, sort_keys=True), seed)
	if key in MASTERS:
		return MASTERS[key]
	name = f"M_{kind}_{len(MASTERS)}"
	fn = {
		"Pine": kit.pine, "Boulder": kit.boulder, "Grass": kit.grass_clump, "Flowers": kit.flowers, "Bush": kit.bush,
		"Mountain": kit.mountain, "Tower": kit.tower, "Arch": kit.arch, "RuinArches": kit.ruin_arches, "Stele": kit.stele,
		"Banner": kit.banner, "BannerPole": kit.banner_pole, "Hero": kit.hero, "Golem": kit.golem,
		"CardPine": card_trees.card_pine, "CardLeafy": card_trees.card_leafy,
	}[kind]
	obj = fn(name, seed, coll=MASTER_COLL, **args)
	obj.hide_render = True
	obj.hide_viewport = True
	zs = [v.co.z for v in obj.data.vertices]
	MASTERS[key] = (obj, max(zs), min(zs))
	return MASTERS[key]


def instance(kind, args, seed, loc, yaw, scale, coll, name=None, tag=None):
	src, top, bottom = master(kind, args, seed)
	o = bpy.data.objects.new(name or kind, src.data)
	o.location = loc
	o.rotation_euler = (0, 0, yaw)
	o.scale = scale if isinstance(scale, tuple) else (scale, scale, scale)
	coll.objects.link(o)
	s = o.scale[2]
	PLACED.append({"Name": o.name, "Kit": kind, "Tag": tag, "At": [round(loc[0], 2), round(loc[1], 2), round(loc[2], 2)],
				   "Yaw": round(math.degrees(yaw), 1), "Scale": round(s, 3), "Height": round(top * s, 2)})
	return o


def solve_scale(base, h0, top_px):
	"""the scale at which an object of height h0 standing at `base` has its top at reference row top_px"""
	lo, hi = 0.01, 60.0
	for _ in range(50):
		mid = (lo + hi) / 2
		pr = CAM.project(base + Vector((0, 0, h0 * mid)))
		if pr is None or pr[1] < top_px:
			hi = mid
		else:
			lo = mid
	return (lo + hi) / 2


def face_camera_yaw(p):
	v = CAM.pos - p
	return math.atan2(v.x, -v.y)


def on_ray_at_depth(px, depth):
	d = CAM.ray(*px)
	return CAM.pos + d * (depth / d.dot(CAM.fwd))


def base_point(G, item):
	if "Px" in item and "Depth" in item:
		p = on_ray_at_depth(item["Px"], item["Depth"])
	elif "Px" in item:
		p = G.hit_px(item["Px"])
		if p is None:
			raise ValueError(f"{item.get('Kit', item.get('Kind'))} at {item['Px']}: ray misses the ground")
	elif "At3" in item:
		p = Vector(item["At3"])
	else:
		x, y = item["At"]
		p = Vector((x, y, float(G.height(x, y))))
	return p + Vector((0, 0, item.get("Lift", 0.0)))


def yaw_for(item, p):
	if item.get("Face") == "camera":
		return face_camera_yaw(p) + math.radians(item.get("Yaw", 0.0))
	return math.radians(item.get("Yaw", 0.0))


def place_item(G, item, coll, ao_spots, foot):
	kind = item["Kit"]
	args = item.get("Args", {})
	seed = item.get("Seed", 1)
	p = base_point(G, item)
	yaw = yaw_for(item, p)
	_, top, _ = master(kind, args, seed)
	if "TopPx" in item:
		s = solve_scale(p, top, item["TopPx"])
	elif "Height" in item:
		s = item["Height"] / top
	else:
		s = item.get("Scale", 1.0)
	o = instance(kind, args, seed, p, yaw, s, coll, item.get("Id"), item.get("Tag", kind))
	if "Pad" in item:
		G.pad(p.x, p.y, p.z, item["Pad"].get("Radius", 4.0), item["Pad"].get("Blend", 10.0))
	r = item.get("AO")
	if r is None:
		r = {"Pine": 0.13, "Boulder": 0.7, "Tower": 0.62, "Stele": 0.9, "BannerPole": 0.0, "Golem": 0.5, "Hero": 0.45, "RuinArches": 0.2, "Bush": 0.8}.get(kind, 0.0)
	if r:
		ao_spots.append((p.x, p.y, max(1.0, r * top * s), item.get("AOStrength", 0.35)))
	foot.append((p.x, p.y, item.get("Clear", {"Pine": 1.2, "Boulder": 2.5, "Tower": 9, "Stele": 1.5, "Golem": 2.5, "Hero": 1.5}.get(kind, 1.0) * max(1.0, s))))
	if kind == "BannerPole" and "Banner" in item:
		b = item["Banner"]
		side = args.get("side", 1)
		arm = args.get("arm", 4.6)
		h = args.get("height", 12.0)
		local = Vector((side * arm * 0.55, -0.05, h - 0.25))
		wp = p + Matrix.Rotation(yaw, 4, "Z") @ (local * s)
		bargs = {"width": b.get("Width", 3.6), "length": b.get("Length", 7.5)}
		instance("Banner", bargs, b.get("Seed", seed + 1), wp, yaw, s, coll, None, "Banner")
	return o, p, s, yaw


def place_gate(G, g, coll, ao_spots, foot):
	"""two towers (each its own size) joined by a round arch, facing the camera square-on. With "Depth" both bases sit on
	their pixel rays at that distance along the view and the ground is levelled under them."""
	seed = g.get("Seed", 50)
	bases, towers = {}, {}
	if "CentrePx" in g:
		# the gate stands in a vertical plane through its centre, turned to face the camera; each tower's base is where
		# its pixel ray meets that plane
		C = on_ray_at_depth(g["CentrePx"], g["Depth"])
		nn = Vector((CAM.pos.x - C.x, CAM.pos.y - C.y, 0)).normalized()
		turn = math.radians(g.get("Turn", 0.0))
		nn = Vector((nn.x * math.cos(turn) - nn.y * math.sin(turn), nn.x * math.sin(turn) + nn.y * math.cos(turn), 0))
		for side in ("Left", "Right"):
			d = CAM.ray(*g[side]["Px"])
			bases[side] = CAM.pos + d * ((C - CAM.pos).dot(nn) / d.dot(nn))
	else:
		for side in ("Left", "Right"):
			spec = g[side]
			bases[side] = on_ray_at_depth(spec["Px"], g["Depth"]) if "Depth" in g else base_point(G, spec)
	L, R = bases["Left"], bases["Right"]
	u = Vector((R.x - L.x, R.y - L.y, 0)).normalized()
	n = Vector((-u.y, u.x, 0))
	mid = (L + R) / 2
	if n.dot(CAM.pos - mid) < 0:
		n = -n
	yaw = math.atan2(n.x, -n.y)
	for k, side in enumerate(("Left", "Right")):
		spec = g[side]
		targs = dict(g.get("Tower", {}), **spec.get("Args", {}))
		_, top, _ = master("Tower", targs, seed + k)
		P = bases[side]
		s = solve_scale(P, top, spec["TopPx"]) if "TopPx" in spec else spec.get("Scale", 1.0)
		instance("Tower", targs, seed + k, P, yaw + math.radians(spec.get("Yaw", 0.0)), s, coll, f"{g.get('Id', 'Gate')}{side}", "GateTower")
		width = targs.get("width", 14.0)
		towers[side] = (P, s, top * s, width * s)
		pad = g.get("Pad", {"Radius": width * s * 0.75, "Blend": 12})
		G.pad(P.x, P.y, P.z, pad["Radius"], pad["Blend"])
		ao_spots.append((P.x, P.y, width * s * 0.95, 0.4))
		foot.append((P.x, P.y, width * s * 0.8))
	(PL, sL, HL, WL), (PR, sR, HR, WR) = towers["Left"], towers["Right"]
	gap = Vector((PR.x - PL.x, PR.y - PL.y, 0)).length - WL / 2 - WR / 2
	a = g.get("Arch", {})
	thick = a.get("Thick", 0.13) * gap
	depth = a.get("Depth", 0.3) * gap
	span = gap
	ground = min(PL.z, PR.z) - 0.3
	top_z = (PL.z + PR.z) / 2 + a.get("TopFrac", 0.7) * min(HL, HR)
	c = (PL + u * (WL / 2) + PR - u * (WR / 2)) / 2
	if "TopPx" in a:  # the arch's crown at this reference row, straight above the gap's middle
		lo, hi = c.z, c.z + 200
		for _ in range(40):
			m = (lo + hi) / 2
			pr = CAM.project(Vector((c.x, c.y, m)))
			lo, hi = (m, hi) if pr[1] > a["TopPx"] else (lo, m)
		top_z = lo
	pier_h = max(0.5, top_z - ground - span / 2 - thick)
	centre = c.copy()
	centre.z = ground
	args = {"span": round(span, 2), "thick": round(thick, 2), "depth": round(depth, 2), "pier_h": round(pier_h, 2), "piers": False}
	instance("Arch", args, seed + 2, centre, math.atan2(u.y, u.x), 1.0, coll, f"{g.get('Id', 'Gate')}Arch", "GateArch")
	G.pad(centre.x, centre.y, ground + 0.3, span / 2, 6)
	for b in g.get("Banners", []):
		P, s, H, W = towers[b["On"]]
		bw, bl = b.get("Width", 0.32) * W, b.get("Length", 0.3) * H
		at = P + n * (W / 2 + 0.25) + Vector((0, 0, b.get("Top", 0.84) * H)) + u * (b.get("Offset", 0.0) * W)
		instance("Banner", {"width": round(bw, 2), "length": round(bl, 2)}, b.get("Seed", 61), at, yaw, 1.0, coll, None, "Banner")
	log(f"gate: towers {HL:.1f} / {HR:.1f} studs tall, {WL:.1f} / {WR:.1f} wide, gap {gap:.1f}, arch crown {top_z:.1f}, pier {pier_h:.1f}, "
		f"bases {tuple(round(v, 1) for v in PL)} {tuple(round(v, 1) for v in PR)}")


def point_in_poly(x, y, poly):
	inside = False
	n = len(poly)
	for i in range(n):
		x1, y1 = poly[i]
		x2, y2 = poly[(i + 1) % n]
		if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
			inside = not inside
	return inside


def forest(G, f, coll, ao_spots, foot):
	rng = random.Random(f.get("Seed", 5))
	if "PxPoly" in f:
		poly = []
		for px in f["PxPoly"]:
			h = G.hit_px(px)
			h = h if h is not None else flat_px(px, f.get("Z", 0.0))
			poly.append((h.x, h.y))
	else:
		poly = f["Poly"]
	xs, ys = [q[0] for q in poly], [q[1] for q in poly]
	sp = f.get("Spacing", 9.0)
	variants = f.get("Variants", 5)
	hmin, hmax = f.get("Height", [26, 40])
	count = 0
	y = min(ys)
	while y < max(ys):
		x = min(xs)
		while x < max(xs):
			px, py = x + rng.uniform(-0.45, 0.45) * sp, y + rng.uniform(-0.45, 0.45) * sp
			x += sp
			if not point_in_poly(px, py, poly) or rng.random() > f.get("Fill", 1.0):
				continue
			if near_road(G, px, py, f.get("RoadClear", 6.0)):
				continue
			if any(math.hypot(px - fx, py - fy) < fr for fx, fy, fr in foot):
				continue
			z = float(G.height(px, py))
			h = rng.uniform(hmin, hmax)
			seed = f.get("SeedBase", 100) + rng.randrange(variants)
			kinds = f.get("Kinds", [{"Kit": f.get("Kit", "Pine"), "Args": f.get("Args", {})}])
			pick = rng.choices(kinds, weights=[k.get("Weight", 1.0) for k in kinds])[0]
			args = pick.get("Args", {})
			_, top, _ = master(pick["Kit"], args, seed)
			hh = h * pick.get("HeightMul", 1.0)
			instance(pick["Kit"], args, seed, Vector((px, py, z - 0.2)), rng.uniform(0, math.tau), hh / top, coll, None, "Forest" + pick["Kit"])
			ao_spots.append((px, py, h * 0.14, f.get("AOStrength", 0.3)))
			count += 1
		y += sp
	log(f"forest {f.get('Name', '')}: {count} trees")


def near_road(G, x, y, clear):
	i = int(round((x - G.xs[0]) / G.s))
	j = int(round((y - G.ys[0]) / G.s))
	if 0 <= i < len(G.xs) and 0 <= j < len(G.ys):
		return G.road_d[j, i] < clear
	return False


def scatter(G, sc, coll, foot):
	rng = random.Random(sc.get("Seed", 9))
	x0, y0, x1, y1 = sc.get("Area", G.t["Extent"])
	area = (x1 - x0) * (y1 - y0)
	n = int(area * sc["Density"])
	kinds = sc["Kinds"]
	placed = 0
	pz = sc.get("Patches", {})
	for _ in range(n):
		x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
		dist = math.hypot(x - CAM.pos.x, y - CAM.pos.y)
		if dist > sc.get("MaxDist", 150) or dist < sc.get("MinDist", 1.5):
			continue
		if dist > sc.get("ThinFrom", 1e9) and rng.random() < (dist - sc["ThinFrom"]) / (sc.get("MaxDist", 150) - sc["ThinFrom"]):
			continue
		z = float(G.height(x, y))
		pr = CAM.project(Vector((x, y, z)))
		if pr is None or not (-60 < pr[0] < FW + 60 and -60 < pr[1] < FH + 80):
			continue
		if near_road(G, x, y, sc.get("RoadClear", 0.3)):
			continue
		if "Patches" in sc:
			v = math.sin(x * 0.11 + 1.3) * math.sin(y * 0.13 + 0.4) + 0.6 * math.sin(x * 0.27 - y * 0.21)
			if v < pz.get("Threshold", 0.4):
				continue
		if any(math.hypot(x - fx, y - fy) < fr for fx, fy, fr in foot):
			continue
		near = sc.get("Near")
		if near:  # only along road edges and around the feet of rocks, trees and walls
			ok = False
			if "Road" in near:
				i, j = int(round((x - G.xs[0]) / G.s)), int(round((y - G.ys[0]) / G.s))
				if 0 <= i < len(G.xs) and 0 <= j < len(G.ys):
					ok = near["Road"][0] <= G.road_d[j, i] <= near["Road"][1]
			if not ok and "Foot" in near:
				ok = any(math.hypot(x - fx, y - fy) < fr * near["Foot"] + near.get("FootAdd", 1.5) for fx, fy, fr in foot)
			if not ok:
				continue
		k = kinds[rng.randrange(len(kinds))]
		seed = k.get("SeedBase", 300) + rng.randrange(k.get("Variants", 4))
		lo, hi = k.get("Scale", [0.8, 1.2])
		instance(k["Kit"], k.get("Args", {}), seed, Vector((x, y, z)), rng.uniform(0, math.tau), rng.uniform(lo, hi), coll, None, k["Kit"])
		placed += 1
	log(f"scatter {sc.get('Name', '')}: {placed}")


# ---------------------------------------------------------------- world, light, render


def sun_dir_from(c):
	if "Px" in c:
		return CAM.ray(*c["Px"])
	az, el = math.radians(c["Azimuth"]), math.radians(c["Elevation"])
	# azimuth relative to the camera's forward, positive = to the right
	fwd_az = math.atan2(CAM.fwd.y, CAM.fwd.x)
	a = fwd_az - az
	return Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))


def world_and_light():
	sc = bpy.context.scene
	sky = dict(SPEC["Sky"])
	sd = sun_dir_from(sky["Sun"]) if "Sun" in sky else Vector((0, 1, 0.3)).normalized()
	sky["SunDir"] = [sd.x, sd.y, sd.z]
	W, H = sky.get("Size", (4096, 2048))
	lin = sky_paint.paint(sky, (W, H))
	img = bpy.data.images.new("PaintedSky", W, H, alpha=False, float_buffer=True)
	rgba = np.concatenate([lin[::-1], np.ones((H, W, 1), np.float32)], -1)  # Blender rows run bottom to top
	img.pixels.foreach_set(rgba.ravel())
	img.pack()
	world = bpy.data.worlds.new("Sky")
	sc.world = world
	world.use_nodes = True
	nt = world.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputWorld")
	env = nt.nodes.new("ShaderNodeTexEnvironment")
	env.image = img
	cam_bg = nt.nodes.new("ShaderNodeBackground")
	light_bg = nt.nodes.new("ShaderNodeBackground")
	amb = SPEC["Light"].get("Ambient", {})
	light_bg.inputs["Strength"].default_value = amb.get("Strength", 1.0)
	tint = nt.nodes.new("ShaderNodeMix")
	tint.data_type = "RGBA"
	tint.blend_type = "MULTIPLY"
	tint.inputs["Factor"].default_value = 1.0
	tint.inputs["B"].default_value = (*kit.to_linear(kit.srgb(amb.get("Tint", "ffffff"))), 1)
	nt.links.new(env.outputs["Color"], cam_bg.inputs["Color"])
	nt.links.new(env.outputs["Color"], tint.inputs["A"])
	nt.links.new(tint.outputs["Result"], light_bg.inputs["Color"])
	lp = nt.nodes.new("ShaderNodeLightPath")
	mixs = nt.nodes.new("ShaderNodeMixShader")
	nt.links.new(lp.outputs["Is Camera Ray"], mixs.inputs["Fac"])
	nt.links.new(light_bg.outputs["Background"], mixs.inputs[1])
	nt.links.new(cam_bg.outputs["Background"], mixs.inputs[2])
	nt.links.new(mixs.outputs["Shader"], out.inputs["Surface"])
	s = SPEC["Light"]["Sun"]
	ld = sun_dir_from(s)
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = s["Strength"]
	sun.color = kit.to_linear(kit.srgb(s["Colour"]))
	sun.angle = math.radians(s.get("Angle", 4.0))
	so = bpy.data.objects.new("Sun", sun)
	so.rotation_euler = (-ld).to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(so)
	log(f"sky sun dir {tuple(round(v, 3) for v in sd)}  light from {tuple(round(v, 3) for v in ld)}")
	return sd, ld


def camera_object():
	sc = bpy.context.scene
	cam = bpy.data.cameras.new("Cam")
	cam.sensor_fit = "VERTICAL"
	cam.angle_y = CAM.fov
	cam.clip_start = 0.2
	cam.clip_end = 8000
	# lens shift: with a vertical sensor fit Blender measures shift in frame heights
	cam.shift_y = (CAM.cy - FH / 2) / FH
	o = bpy.data.objects.new("Cam", cam)
	o.location = CAM.pos
	o.rotation_euler = CAM.fwd.to_track_quat("-Z", "Y").to_euler()
	sc.collection.objects.link(o)
	sc.camera = o
	# check the Blender camera against our projection on a few points
	from bpy_extras.object_utils import world_to_camera_view

	sc.render.resolution_x, sc.render.resolution_y = FW, FH
	bpy.context.view_layer.update()
	worst = 0.0
	for px in ((100, 100), (1200, 650), (668, 262), (900, 500)):
		w = CAM.pos + CAM.ray(*px) * 50
		v = world_to_camera_view(sc, o, w)
		worst = max(worst, abs(v.x * FW - px[0]), abs((1 - v.y) * FH - px[1]))
	log(f"camera check: worst pixel error {worst:.2f}")
	return o


def render_settings(quick):
	sc = bpy.context.scene
	r = SPEC.get("Render", {})
	sc.render.engine = "BLENDER_EEVEE"
	sc.render.resolution_x, sc.render.resolution_y = r.get("Res", [FW, FH])
	sc.render.resolution_percentage = 50 if quick else 100
	sc.render.film_transparent = False
	sc.view_settings.view_transform = "Standard"
	sc.view_settings.look = "None"
	sc.view_settings.exposure = r.get("Exposure", 0.0)
	sc.view_settings.gamma = 1.0
	ee = sc.eevee
	ee.taa_render_samples = 16 if quick else r.get("Samples", 64)
	for k, v in r.get("Eevee", {}).items():
		try:
			setattr(ee, k, v)
		except Exception as e:  # noqa: BLE001
			log("eevee setting", k, e)
	sc.render.image_settings.file_format = "PNG"
	sc.render.image_settings.color_depth = "16"
	sc.render.image_settings.color_mode = "RGB"


def render_depth(path, depth_range):
	sc = bpy.context.scene
	m = bpy.data.materials.new("DepthOverride")
	m.use_nodes = True
	nt = m.node_tree
	nt.nodes.clear()
	out = nt.nodes.new("ShaderNodeOutputMaterial")
	em = nt.nodes.new("ShaderNodeEmission")
	cd = nt.nodes.new("ShaderNodeCameraData")
	dv = nt.nodes.new("ShaderNodeMath")
	dv.operation = "DIVIDE"
	dv.inputs[1].default_value = depth_range
	nt.links.new(cd.outputs["View Distance"], dv.inputs[0])
	nt.links.new(dv.outputs["Value"], em.inputs["Color"])
	em.inputs["Strength"].default_value = 1.0
	nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
	vl = sc.view_layers[0]
	vl.material_override = m
	w = bpy.data.worlds.new("DepthWorld")
	w.use_nodes = True
	bg = w.node_tree.nodes.get("Background")
	bg.inputs["Color"].default_value = (1, 1, 1, 1)
	bg.inputs["Strength"].default_value = 1.0
	old_world = sc.world
	sc.world = w
	sc.view_settings.view_transform = "Raw"
	sc.view_settings.exposure = 0.0
	old_samples = sc.eevee.taa_render_samples
	sc.eevee.taa_render_samples = 1
	for o in sc.objects:
		if o.type == "LIGHT":
			o.hide_render = True
	sc.render.filepath = path
	bpy.ops.render.render(write_still=True)
	vl.material_override = None
	sc.world = old_world
	sc.eevee.taa_render_samples = old_samples


def main():
	os.makedirs(OUT, exist_ok=True)
	bpy.ops.wm.read_factory_settings(use_empty=True)
	sc = bpy.context.scene
	global MASTER_COLL
	MASTER_COLL = bpy.data.collections.new("KitMasters")
	sc.collection.children.link(MASTER_COLL)
	scene_coll = bpy.data.collections.new("Scene")
	sc.collection.children.link(scene_coll)

	G = Ground(SPEC["Terrain"])
	G.apply_features()
	G.roads = []
	ao_spots, foot = [], []
	# phase 1: things pinned in space (the gate, anything with a Depth) level the ground under themselves first
	pinned = lambda it: it.get("Kind") == "Gate" or "Depth" in it
	for item in SPEC.get("Place", []):
		if item.get("Off") or not pinned(item):
			continue
		if item.get("Kind") == "Gate":
			place_gate(G, item, scene_coll, ao_spots, foot)
		else:
			place_item(G, item, scene_coll, ao_spots, foot)
	G.carve_roads(SPEC.get("Roads", []))
	log(f"terrain {G.X.shape[1]} x {G.X.shape[0]} verts, height {G.Z.min():.1f}..{G.Z.max():.1f}")
	# phase 2: everything else lands on the finished ground
	for item in SPEC.get("Place", []):
		if item.get("Off") or pinned(item):
			continue
		place_item(G, item, scene_coll, ao_spots, foot)
	for f in SPEC.get("Forests", []):
		if not f.get("Off"):
			forest(G, f, scene_coll, ao_spots, foot)
	for s in SPEC.get("Scatter", []):
		if not s.get("Off"):
			scatter(G, s, scene_coll, foot)
	build_terrain(G, scene_coll, ao_spots)
	log(f"placed {len(PLACED)} objects, {len(MASTERS)} kit meshes")

	camera_object()
	sd, ld = world_and_light()
	quick = "--quick" in FLAGS
	render_settings(quick)
	sc.render.filepath = os.path.join(OUT, "beauty.png")
	bpy.ops.render.render(write_still=True)
	log("beauty rendered")
	meta = {"SkySunDir": [sd.x, sd.y, sd.z], "LightFrom": [ld.x, ld.y, ld.z], "DepthRange": SPEC.get("Render", {}).get("DepthRange", 3000.0),
			"Camera": {"Pos": list(CAM.pos), "Fwd": list(CAM.fwd), "Right": list(CAM.right), "Up": list(CAM.up), "F": CAM.f, "Cy": CAM.cy, "Frame": [FW, FH]}}
	if "--no-depth" not in FLAGS:
		render_depth(os.path.join(OUT, "depth.png"), meta["DepthRange"])
		log("depth rendered")
	tris = {}
	for (kind, _, _), (obj, _, _) in MASTERS.items():
		tris[obj.name] = sum(len(p.vertices) - 2 for p in obj.data.polygons)
	json.dump({"Meta": meta, "Placed": PLACED, "KitTriangles": tris}, open(os.path.join(OUT, "placements.json"), "w"), indent=1)
	if "--save" in FLAGS:
		bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scene.blend"))
	log("done")


main()
