"""Study: a pink sandstone cottage with a round tower, after an illustration the user shared (private; reference and every output in
research/pink_cottage, gitignored, never in the game). Built in studs, z up, the front wall faces -y.

Every face belongs to an island: a sheet (one texture), a kind (what the painter paints there: slate row, ashlar, plaster, planks...) and
paint coordinates in studs natural to its pattern (along a roof row and down it, round the tower and up it). Islands are packed per sheet
after the bevels, so tools/art/paint_pink_cottage.py can paint each one by its own rules with world positions and normals per texel.

  blender --background --python tools/blender/pink_cottage.py -- build          geometry, UVs, bake.npz, layout.json, cottage.blend
  blender --background --python tools/blender/pink_cottage.py -- render <tag> [--clay] [--small]
  blender --background --python tools/blender/pink_cottage.py -- export
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "research", "pink_cottage")
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["build"]
RES = (1200, 1694)  # the reference's size
SHEET = 1024
PAD = 3  # pixels between islands at sheet size

# camera, measured from the reference's ground lines (13 and 57 degrees on screen): pitch 36.6 down, the front wall 21.2 degrees off square.
# A long lens from far away, as Roblox would need (no orthographic camera, no lens shift).
CAM = {"Pitch": 20.0, "Yaw": 27.5, "FOV": 16.0, "Dist": 283.16, "Target": (10.184, 10.338, 12.274)}

Z_STREET = -3.4  # the lane, the door landing and the terrace
UP = Vector((0, 0, 1))


def smooth(a, b, x):
	t = min(max((x - a) / (b - a), 0.0), 1.0)
	return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------------------------- geometry store
class Geo:
	def __init__(self):
		self.objs = {}
		self.islands = []

	def island(self, sheet, kind, frame=None, **params):
		self.islands.append({"Sheet": sheet, "Kind": kind, "Frame": frame, "Params": params})
		return len(self.islands) - 1

	def face(self, obj, pts, isl, uvs=None):
		o = self.objs.setdefault(obj, {"v": [], "f": [], "isl": [], "uv": []})
		pts = [Vector(p) for p in pts]
		if uvs is None:
			org, au, av = self.islands[isl]["Frame"]
			uvs = [((p - org).dot(au), (p - org).dot(av)) for p in pts]
		base = len(o["v"])
		o["v"].extend(tuple(p) for p in pts)
		o["f"].append(tuple(range(base, base + len(pts))))
		o["isl"].append(isl)
		o["uv"].append([tuple(u) for u in uvs])

	def mark(self):
		"""how many vertices each object has now: pass to warp_since to move only what is built after this"""
		return {k: len(o["v"]) for k, o in self.objs.items()}

	def warp_since(self, mark, fn):
		"""apply fn((x, y, z)) -> (x, y, z) to every vertex added since mark (a window tilted, a dormer leaning)"""
		for k, o in self.objs.items():
			start = mark.get(k, 0)
			o["v"][start:] = [tuple(fn(Vector(p))) for p in o["v"][start:]]

	def tri_fill(self, obj, loops3d, normal, isl, uvs_of=None):
		"""a flat polygon with holes (first loop outer), triangulated and wound to face `normal`"""
		pts = [p for loop in loops3d for p in loop]
		for t in tessellate_polygon([[tuple(p) for p in loop] for loop in loops3d]):
			a, b, c = (pts[i] for i in t)
			if (b - a).cross(c - a).dot(normal) < 0:
				a, b, c = a, c, b
			self.face(obj, [a, b, c], isl, None if uvs_of is None else [uvs_of(a), uvs_of(b), uvs_of(c)])


def frame_of(org, au, av):
	return (Vector(org), Vector(au).normalized(), Vector(av).normalized())


def box(g, obj, sheet, kind, centre, size, yaw=0.0, skip=(), K=1.0, **params):
	"""a box turned about z by yaw (degrees). Each face its own island: sides read across (u) and up (v), top and bottom in plan."""
	c = Vector(centre)
	h = Vector(size) / 2
	R = Matrix.Rotation(math.radians(yaw), 3, "Z")
	X, Y = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0))

	def P(sx, sy, sz):
		return c + X * (sx * h.x) + Y * (sy * h.y) + UP * (sz * h.z)

	faces = {
		"-y": ([P(-1, -1, -1), P(1, -1, -1), P(1, -1, 1), P(-1, -1, 1)], X, UP),
		"+y": ([P(1, 1, -1), P(-1, 1, -1), P(-1, 1, 1), P(1, 1, 1)], -X, UP),
		"+x": ([P(1, -1, -1), P(1, 1, -1), P(1, 1, 1), P(1, -1, 1)], Y, UP),
		"-x": ([P(-1, 1, -1), P(-1, -1, -1), P(-1, -1, 1), P(-1, 1, 1)], -Y, UP),
		"+z": ([P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1)], X, Y),
		"-z": ([P(-1, 1, -1), P(1, 1, -1), P(1, -1, -1), P(-1, -1, -1)], X, -Y),
	}
	out = {}
	for key, (pts, au, av) in faces.items():
		if key in skip:
			continue
		isl = g.island(sheet, kind, frame_of(pts[0], au, av), Face=key, K=K, **params)
		g.face(obj, pts, isl)
		out[key] = isl
	return out


def prism(g, obj, sheet, kind, outline, z0, z1, K=1.0, top=True, bottom=False, **params):
	"""a vertical prism over a plan outline (counter-clockwise, x/y pairs): one island for the sides (u runs round), one for the top"""
	pts = [Vector((x, y, 0)) for x, y in outline]
	n = len(pts)
	for i in range(n):
		a, b = pts[i], pts[(i + 1) % n]
		L = (b - a).length
		pieces = max(1, math.ceil(L / 14.0))
		for k in range(pieces):
			pa, pb = a.lerp(b, k / pieces), a.lerp(b, (k + 1) / pieces)
			side = g.island(sheet, kind, None, Face="side", K=K, **params)
			l0, l1 = L * k / pieces, L * (k + 1) / pieces
			quad = [pa + UP * z0, pb + UP * z0, pb + UP * z1, pa + UP * z1]
			g.face(obj, quad, side, [(l0, z0), (l1, z0), (l1, z1), (l0, z1)])
	if top:
		isl = g.island(sheet, kind, frame_of((0, 0, z1), (1, 0, 0), (0, 1, 0)), Face="+z", K=K, **params)
		g.tri_fill(obj, [[p + UP * z1 for p in pts]], UP, isl)
	if bottom:
		isl = g.island(sheet, kind, frame_of((0, 0, z0), (1, 0, 0), (0, -1, 0)), Face="-z", K=0.3, **params)
		g.tri_fill(obj, [[p + UP * z0 for p in pts]], -UP, isl)


def signed_area(loop):
	n = len(loop)
	return 0.5 * sum(loop[i][0] * loop[(i + 1) % n][1] - loop[(i + 1) % n][0] * loop[i][1] for i in range(n))


def wall(g, obj, sheet, kind, org, au, outline, holes=(), thick=1.0, reveal_kind=None, K=1.0, edges=True, back=True, **params):
	"""a flat wall in the plane org + u*au + v*up, outward normal au x up; outline and holes are (u, v) loops.
	Holes get reveals (their own islands, u round the hole, v into the wall) so openings have depth."""
	org, au = Vector(org), Vector(au).normalized()
	av = UP
	n = au.cross(av)
	outline = dedupe(outline)
	holes = [dedupe(h) for h in holes]

	def to3(uv, depth=0.0):
		return org + au * uv[0] + av * uv[1] - n * depth

	front = g.island(sheet, kind, frame_of(org, au, av), Face="front", K=K, **params)
	g.tri_fill(obj, [[to3(p) for p in outline]] + [[to3(p) for p in h] for h in holes], n, front)
	if back:
		bk = g.island(sheet, kind, frame_of(org - n * thick, -au, av), Face="back", K=0.25, **params)
		g.tri_fill(obj, [[to3(p, thick) for p in outline]] + [[to3(p, thick) for p in h] for h in holes], -n, bk)
	loops = ([(outline, False)] if edges else []) + [(h, True) for h in holes]
	for loop, is_hole in loops:
		isl = g.island(sheet, reveal_kind or kind, None, Face="reveal" if is_hole else "edge", K=K, **params)
		ccw = signed_area(loop) > 0
		out_right = ccw if not is_hole else not ccw
		run = 0.0
		m = len(loop)
		for i in range(m):
			a, b = loop[i], loop[(i + 1) % m]
			L = math.dist(a, b)
			if L < 1e-6:
				continue
			du, dv = b[0] - a[0], b[1] - a[1]
			right = au * dv - av * du
			want = right if out_right else -right
			A, B = to3(a), to3(b)
			A2, B2 = to3(a, thick), to3(b, thick)
			quad, uv = [A, B, B2, A2], [(run, 0), (run + L, 0), (run + L, thick), (run, thick)]
			if (B - A).cross(A2 - A).dot(want) < 0:
				quad, uv = [A, A2, B2, B], [(run, 0), (run, thick), (run + L, thick), (run + L, 0)]
			g.face(obj, quad, isl, uv)
			run += L
	return front


def arc(cx, cy, r, a0, a1, steps):
	return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def arch_geom(u0, u1, spring, rise):
	"""centre height and radius of a segmental arch through both springs and the crown"""
	half = (u1 - u0) / 2
	r = (half * half + rise * rise) / (2 * rise)
	return (u0 + u1) / 2, spring + rise - r, r, math.degrees(math.asin(min(1.0, half / r)))


def arched_hole(u0, u1, bottom, spring, rise, steps=14):
	"""counter-clockwise loop: an opening with a segmental arch on top"""
	cu, cv, r, a = arch_geom(u0, u1, spring, rise)
	return [(u0, bottom), (u1, bottom)] + arc(cu, cv, r, 90 - a, 90 + a, steps)


def cylinder(g, obj, sheet, kind, cx, cy, r, z0, z1, segs=40, band=21.0, K=1.0, shape=None, **params):
	"""an upright round wall; one island per band of height (u = arc length from the front at the mean radius, v = z).
	shape(z) -> (radius, dx, dy) tapers and leans it (the tower); without it, a plain cylinder of radius r"""
	shape = shape or (lambda z: (r, 0.0, 0.0))
	z = z0
	while z < z1 - 1e-6:
		zt = min(z1, z + band)
		isl = g.island(sheet, kind, None, Face="round", K=K, Radius=r, Z0=z, **params)
		(ra, xa, ya), (rb, xb, yb) = shape(z), shape(zt)
		for i in range(segs):
			a0 = -math.pi / 2 + 2 * math.pi * i / segs
			a1 = -math.pi / 2 + 2 * math.pi * (i + 1) / segs
			q = [Vector((cx + xa + ra * math.cos(a0), cy + ya + ra * math.sin(a0), z)), Vector((cx + xa + ra * math.cos(a1), cy + ya + ra * math.sin(a1), z)), Vector((cx + xb + rb * math.cos(a1), cy + yb + rb * math.sin(a1), zt)), Vector((cx + xb + rb * math.cos(a0), cy + yb + rb * math.sin(a0), zt))]
			u0, u1 = r * (a0 + math.pi / 2), r * (a1 + math.pi / 2)
			g.face(obj, q, isl, [(u0, z), (u1, z), (u1, zt), (u0, zt)])
		z = zt


def disc(g, obj, sheet, kind, cx, cy, r, z, segs=40, down=False, K=1.0, **params):
	isl = g.island(sheet, kind, frame_of((cx, cy, z), (1, 0, 0), (0, -1 if down else 1, 0)), Face="-z" if down else "+z", K=K, **params)
	ring = [Vector((cx + r * math.cos(2 * math.pi * i / segs), cy + r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)]
	g.tri_fill(obj, [ring], -UP if down else UP, isl)


# ---------------------------------------------------------------------------------------------------------------- fish-scale slate
class Profile:
	"""roof height above the eave against plan distance in from the eave: steep, flaring out shallower at the foot (bell-cast)"""

	def __init__(self, pitch, eave_pitch, flare, depth):
		self.d = np.linspace(0, depth, 400)
		slope = math.tan(math.radians(eave_pitch)) + (math.tan(math.radians(pitch)) - math.tan(math.radians(eave_pitch))) * np.array([smooth(0, flare, x) for x in self.d])
		dz = np.concatenate([[0], np.cumsum((slope[1:] + slope[:-1]) / 2 * np.diff(self.d))])
		ds = np.concatenate([[0], np.cumsum(np.sqrt(1 + ((slope[1:] + slope[:-1]) / 2) ** 2) * np.diff(self.d))])
		self.z, self.s, self.slope = dz, ds, slope

	def scaled(self, k):
		"""the same curve squeezed k times in plan: z(d) of the new = z(d * k) of this"""
		out = Profile.__new__(Profile)
		out.d = self.d / k
		out.z = self.z.copy()
		out.slope = self.slope * k
		ds = np.concatenate([[0], np.cumsum(np.sqrt(1 + ((out.slope[1:] + out.slope[:-1]) / 2) ** 2) * np.diff(out.d))])
		out.s = ds
		return out

	def z_at(self, d):
		return float(np.interp(d, self.d, self.z))

	def d_at_s(self, s):
		return float(np.interp(s, self.s, self.d))

	def s_at(self, d):
		return float(np.interp(d, self.d, self.s))


def clip_convex(poly, clip):
	"""Sutherland-Hodgman: poly (any simple loop) against a convex counter-clockwise loop"""
	out = list(poly)
	m = len(clip)
	for i in range(m):
		a, b = clip[i], clip[(i + 1) % m]
		inp, out = out, []
		if not inp:
			break

		def inside(p):
			return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

		def cross(p, q):
			x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
			dx, dy = x2 - x1, y2 - y1
			ex, ey = b[0] - a[0], b[1] - a[1]
			den = dx * ey - dy * ex
			t = ((a[0] - x1) * ey - (a[1] - y1) * ex) / den
			return (x1 + t * dx, y1 + t * dy)

		for j in range(len(inp)):
			p, q = inp[j], inp[(j + 1) % len(inp)]
			if inside(q):
				if not inside(p):
					out.append(cross(p, q))
				out.append(q)
			elif inside(p):
				out.append(cross(p, q))
	return out


def slate_face(g, obj, name, eave_org, along, inward, prof, clip, tile=1.5, row=0.95, depth=0.62, thick=0.2, start=0.0, sheet="Roof", seg=6, lift0=0.0):
	"""rows of round-ended slates on one roof face. clip: convex loop in (x along the eave, plan distance d) the face covers.
	Each row is its own island (u = x, v = slant distance) and so is each row's lip, the cut edge that throws the step shadow."""
	E, ax, ai = Vector(eave_org), Vector(along).normalized(), Vector(inward).normalized()
	xs = [p[0] for p in clip]
	x_lo, x_hi = min(xs) - tile, max(xs) + tile
	d_max = max(p[1] for p in clip)
	s_max = prof.s_at(d_max)
	normal_up = None
	rows = []
	i = 0
	s = start
	while s < s_max + 0.01:
		rows.append(s)
		s += row
		i += 1
	for i, s0 in enumerate(rows):
		offset = (i % 2) * tile / 2
		# scalloped bottom edge, left to right; tips at s0, joints at s0 + depth
		k0 = math.floor((x_lo - offset) / tile)
		k1 = math.ceil((x_hi - offset) / tile)
		edge = []
		for k in range(k0, k1):
			xc = offset + (k + 0.5) * tile
			for j in range(seg):
				t = -1 + 2 * j / seg
				x = xc + t * tile / 2
				sv = s0 + depth * (1 - math.sqrt(max(0.0, 1 - t * t)))
				edge.append((x, sv))
		edge.append((offset + k1 * tile, s0 + depth))
		s_top = s0 + row + depth + 0.25  # tucked under the next row's joints
		loop_s = edge + [(edge[-1][0], s_top), (edge[0][0], s_top)]
		# to plan coordinates, clip, back
		loop_d = [(x, prof.d_at_s(sv)) for x, sv in loop_s]
		if s_top > s_max:
			pass
		cl = clip_convex(loop_d, clip)
		if len(cl) < 3:
			continue
		cl_s = [(x, prof.s_at(d)) for x, d in cl]

		def lift(sv):
			# the row rests on the one below: lifted by the slate's thickness at its foot, nothing at its top
			return thick * (1 - smooth(s0, s_top, sv)) + lift0

		def P(x, sv):
			d = prof.d_at_s(sv)
			slope = float(np.interp(d, prof.d, prof.slope))
			nrm = (UP - ai * slope).normalized()
			return E + ax * x + ai * d + UP * prof.z_at(d) + nrm * lift(sv)

		isl = g.island(sheet, "slate", None, Face="row", Row=i, Offset=offset, Tile=tile, RowH=row, Depth=depth, S0=s0, Roof=name)
		pts3 = [P(x, sv) for x, sv in cl_s]
		nrm0 = (UP - ai * float(np.interp(prof.d_at_s(s0 + row / 2), prof.d, prof.slope))).normalized()
		lookup = {tuple(round(c, 5) for c in p): uv for p, uv in zip(pts3, cl_s)}
		g.tri_fill(obj, [pts3], nrm0, isl, uvs_of=lambda p: lookup[tuple(round(c, 5) for c in p)])
		# lip: the scalloped edge's thickness, where it survived clipping
		lip = g.island(sheet, "slate_lip", None, Face="lip", Row=i, Roof=name, K=0.6)
		run = 0.0
		for j in range(len(edge) - 1):
			(xa, sa), (xb, sb) = edge[j], edge[j + 1]
			da, db = prof.d_at_s(sa), prof.d_at_s(sb)
			if not (point_in_convex((xa, da), clip) and point_in_convex((xb, db), clip)):
				run += math.dist((xa, sa), (xb, sb))
				continue
			A, B = P(xa, sa), P(xb, sb)
			dn = (UP - ai * float(np.interp(da, prof.d, prof.slope))).normalized() * (thick + lift0 * 0)
			A2, B2 = A - dn, B - dn
			L = (B - A).length
			quad = [A2, B2, B, A]
			if (B2 - A2).cross(A - A2).dot(-ai) < 0:
				quad = [A2, A, B, B2]
				uv = [(run, 0), (run, thick), (run + L, thick), (run + L, 0)]
			else:
				uv = [(run, 0), (run + L, 0), (run + L, thick), (run, thick)]
			g.face(obj, quad, lip, uv)
			run += L


def point_in_convex(p, clip):
	m = len(clip)
	for i in range(m):
		a, b = clip[i], clip[(i + 1) % m]
		if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) < -1e-6:
			return False
	return True


def cone_profile(z_eave, r_eave, height, flare=0.55, reach=0.6, steps=40):
	"""the tower's cone as (radius, z) from the eave to the apex: a straight steep cone that flares out over its last stud or so"""
	k = (r_eave - flare) / height  # radius per stud of height on the straight part, which meets the apex
	out = []
	for i in range(steps + 1):
		t = i / steps
		dz = height * t ** 1.6  # finer steps near the eave, where the flare bends
		out.append((max(0.0, (height - dz) * k + flare * math.exp(-dz / reach)), z_eave + dz))
	out[-1] = (0.0, z_eave + height)
	return out


def slate_cone(g, obj, name, cx, cy, profile, tile=1.35, row=0.85, depth=0.55, thick=0.18, seg=5, sheet="Roof"):
	"""rows of round-ended slates round a cone of revolution; profile = (radius, z) from the eave to the apex (it may flare).
	Tiles per row fall as it narrows. u = arc length at the row's foot, v = slant distance up the profile"""
	rs = np.array([p[0] for p in profile])
	zs = np.array([p[1] for p in profile])
	S = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(rs), np.diff(zs)))])
	slant = float(S[-1])

	def at(s):
		s = min(max(s, 0.0), slant)
		i = max(0, min(len(S) - 2, int(np.searchsorted(S, s)) - 1))
		t = (s - S[i]) / max(S[i + 1] - S[i], 1e-9)
		dr, dz = rs[i + 1] - rs[i], zs[i + 1] - zs[i]
		L = math.hypot(dr, dz)
		return rs[i] + dr * t, zs[i] + dz * t, dz / L, -dr / L  # radius, z, outward normal (radial, up)

	rows = int(slant / row)
	for i in range(rows):
		s0 = i * row
		r0 = at(s0)[0]
		if r0 < 0.35:
			break
		n = max(5, round(2 * math.pi * r0 / tile))
		w = 2 * math.pi / n
		off = (i % 2) * w / 2
		s_top = min(slant, s0 + row + depth + 0.25)

		def P(a, sv, lifted):
			r, z, nr_, nz_ = at(sv)
			nr = Vector((math.cos(a) * nr_, math.sin(a) * nr_, nz_))
			pos = Vector((cx + r * math.cos(a), cy + r * math.sin(a), z))
			return pos + nr * lifted

		isl = g.island(sheet, "slate", None, Face="cone", Row=i, Offset=off * r0, Tile=w * r0, RowH=row, Depth=depth, S0=s0, Roof=name, Radius=r0)
		lip = g.island(sheet, "slate_lip", None, Face="lip", Row=i, Roof=name, K=0.6)
		for k in range(n):
			a0 = off + k * w
			for j in range(seg):
				ta, tb = -1 + 2 * j / seg, -1 + 2 * (j + 1) / seg
				aa, ab = a0 + (ta + 1) / 2 * w, a0 + (tb + 1) / 2 * w
				sa = s0 + depth * (1 - math.sqrt(max(0, 1 - ta * ta)))
				sb = s0 + depth * (1 - math.sqrt(max(0, 1 - tb * tb)))
				la = thick * (1 - smooth(s0, s_top, sa))
				lb = thick * (1 - smooth(s0, s_top, sb))
				A, B = P(aa, sa, la), P(ab, sb, lb)
				C, D = P(ab, s_top, 0), P(aa, s_top, 0)
				g.face(obj, [A, B, C, D], isl, [(aa * r0, sa), (ab * r0, sb), (ab * r0, s_top), (aa * r0, s_top)])
				A2, B2 = P(aa, sa, la - thick), P(ab, sb, lb - thick)
				g.face(obj, [A2, B2, B, A], lip, [(aa * r0, 0), (ab * r0, 0), (ab * r0, thick), (aa * r0, thick)])
	return Vector((cx, cy, float(zs[-1])))




# ---------------------------------------------------------------------------------------------------------------- the scene
# Sizes measured from the reference through the camera above (tools: research/pink_cottage/README.md). Garden at z 0.
LANE = -13.8  # the lane, the annex door's landing and the terrace: the reference's annex door is nearly twice as tall as it is wide
HX0, HX1, HY1 = -4.7, 29.5, 20.0  # main block; its front wall is y = 0
WALL_TOP = 13.4
EAVE = 12.4  # foot of the lowest slates
# The main roof's eave outline and ridge, fitted to the reference's silhouette (left hip, ridge, both front corners) by back-projection:
# it reaches 4 studs past the left wall and the chimney stands on the ridge's left end; 2.3 over the front, 1.5 over the right.
RX0, RY0, RX1, RY1 = -8.6, -2.3, 31.0, 22.3
RIDGE_Y, RIDGE_L, RIDGE_R = 10.0, 2.6, 23.5
UPTURN = (0.35, 6.0)  # the left-front corner lifts a little: height at the corner, reach along each eave (the user: no more curl)
SWEEP = (0.95, 16.0, 31.0, 4.0)  # the right-front corner sweeps down: depth, from x, to x, gone by this y along the right eave


def corner_warp(x, y, z):
	"""the main roof's hand-made corners (reference): the left-front corner turns up, the right-front one sweeps down a little"""
	up, reach = UPTURN
	fx = min(1.0, max(0.0, 1 - (x - RX0) / reach))
	fy = min(1.0, max(0.0, 1 - (y - RY0) / reach))
	depth, x0, x1, y1 = SWEEP
	drop = depth * smooth(x0, x1, x) * (1 - smooth(RY0, y1, y))
	return (up * fx * fx * fy * fy - drop) * (1 - smooth(EAVE + 0.3, EAVE + 5.0, z))


WOBBLE = (0.22, 6.5)  # amplitude and wavelength (studs) of the hand-made waviness on everything built (the user: less rigid)
WOBBLE_OBJS = ("Walls", "Walls2", "Trim", "RoofA", "RoofB", "RoofC", "Tower")


def lean_about(pivot, deg):
	"""a turn about the y axis through pivot: positive leans the top toward +x (clockwise seen from the front)"""
	c = Vector(pivot)
	a = math.radians(deg)
	ca, sa = math.cos(a), math.sin(a)

	def fn(p):
		d = p - c
		return c + Vector((d.x * ca + d.z * sa, d.y, -d.x * sa + d.z * ca))

	return fn


def wobble(g):
	"""a smooth, low waviness over the house: straight lines bow a little and nothing is ruler-true, as in the painting. Vertices at
	one place move together, so seams stay closed; the ground, path and props stay put"""
	from mathutils import noise

	amp, wave = WOBBLE
	for name in WOBBLE_OBJS:
		o = g.objs.get(name)
		if not o:
			continue
		out = []
		for x, y, z in o["v"]:
			n = noise.noise_vector(Vector((x, y, z)) / wave + Vector((3.7, 1.3, 8.1)), noise_basis="PERLIN_ORIGINAL")
			out.append((x + amp * n.x, y + amp * n.y, z + amp * 0.6 * n.z))
		o["v"] = out


def apply_corners(g):
	"""bend the main roof (slates, lips, underlay, caps) at its two front corners; zero elsewhere"""
	for sheet in ("RoofA", "RoofB"):
		o = g.objs.get(sheet)
		if o:
			o["v"] = [(x, y, z + corner_warp(x, y, z)) for x, y, z in o["v"]]


# The tower, set into the house's right end (the main roof passes in front of its foot). Its silhouette fixes it across the view;
# its depth along the view comes from the box dormer, whose right wall meets it about 2 studs behind its front, as in the reference.
TOWER = (29.62, 14.04, 5.43)
TZ = 0.75  # the tower's details sit this much higher than first fitted, so they stay on the reference after the move along the view
T_WALL = 37.15 + TZ  # top of the tower's ashlar: the corbelled cream ring sits on it
RING_TOP = T_WALL + 0.85
CONE = (39.6 + TZ, 7.5, 9.0)  # rim height, rim radius, height: the eave hangs over the crown, steep slopes that flare at the foot
# The tower tapers (the user: smaller at the top, larger at the bottom) and leans a touch, cartoon-like; TOWER's radius is its mid-height.
TR_BASE, TR_TOP = 6.6, 5.0
T_LEAN = (-0.3, -0.16)  # the foot's offset from the top's centre (toward the screen's left)


def tower_shape(z):
	"""radius and centre offset of the tower's wall at height z"""
	t = min(max(z / T_WALL, 0.0), 1.0)
	return TR_BASE + (TR_TOP - TR_BASE) * t, T_LEAN[0] * (1 - t), T_LEAN[1] * (1 - t)
GARDEN_FRONT, GARDEN_RIGHT, GARDEN_BACK = -31.0, 42.0, 24.0
PLANTER_X = 14.6
CORNER = (33.5, -22.5, 8.5)  # the curb's round corner: centre and radius
ANNEX = (-2.0, 14.6, -2.5, 2.5)  # x0, x1, front y, top z: nearly flush with the wall above, as in the reference
ARCH = (11.6, 25.3, 7.2, 3.85)  # main arch: u0, u1 (x), spring z, rise; measured from the reference: narrower, lower and rounder
DOOR = (18.0, 23.5)
WIN = (11.9, 17.4)
COUNTER = (11.3, 18.3, 3.3, 4.9)  # the bay's counter: x0, x1, bottom, top
NEAR_SLATES = dict(tile=1.3, row=0.72, depth=0.65, thick=0.22, seg=5)  # the reference's small round slates, every row half a slate up


def lathe(g, obj, sheet, kind, cx, cy, z0, profile, segs=24, K=1.0, flip=False, **params):
	"""a solid of revolution; profile = (radius, height) pairs from the bottom up. u = angle x widest radius, v = length along the profile"""
	rmax = max(r for r, _ in profile)
	isl = g.island(sheet, kind, None, Face="lathe", K=K, Radius=rmax, **params)
	run = [0.0]
	for i in range(1, len(profile)):
		run.append(run[-1] + math.dist(profile[i - 1], profile[i]))
	for i in range(len(profile) - 1):
		(r0, h0), (r1, h1) = profile[i], profile[i + 1]
		for j in range(segs):
			a0, a1 = 2 * math.pi * j / segs, 2 * math.pi * (j + 1) / segs
			p = [
				Vector((cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0 + h0)),
				Vector((cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z0 + h0)),
				Vector((cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z0 + h1)),
				Vector((cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z0 + h1)),
			]
			uv = [(a0 * rmax, run[i]), (a1 * rmax, run[i]), (a1 * rmax, run[i + 1]), (a0 * rmax, run[i + 1])]
			if flip:
				p, uv = p[::-1], uv[::-1]
			if r0 < 1e-4:
				p, uv = [p[0], p[2], p[3]], [uv[0], uv[2], uv[3]]
			elif r1 < 1e-4:
				p, uv = p[:3], uv[:3]
			g.face(obj, p, isl, uv)
	return isl


def voussoirs(g, obj, sheet, kind, plane_y, cu, cv, r_in, depth_ring, a0, a1, count, proud=0.12, back=0.6, gap=0.05, au=(1, 0, 0), org=(0, 0, 0)):
	"""wedge stones round an arch in the wall plane y = plane_y (u = x, v = z), standing proud of the wall"""
	org, au = Vector(org), Vector(au).normalized()
	n = au.cross(UP)  # outward

	def P(u, v, d):
		return org + au * u + UP * v + n * d

	step = (a1 - a0) / count
	for i in range(count):
		b0, b1 = math.radians(a0 + i * step + gap * 10), math.radians(a0 + (i + 1) * step - gap * 10)
		r_out = r_in + depth_ring * (1.08 if i % 2 else 0.96)
		quad2d = [(cu + r_in * math.cos(b0), cv + r_in * math.sin(b0)), (cu + r_out * math.cos(b0), cv + r_out * math.sin(b0)), (cu + r_out * math.cos(b1), cv + r_out * math.sin(b1)), (cu + r_in * math.cos(b1), cv + r_in * math.sin(b1))]
		front = [P(u, v, proud) for u, v in quad2d]
		backp = [P(u, v, -back) for u, v in quad2d]
		isl = g.island(sheet, kind, frame_of(front[0], au, UP), Face="front", Stone=i)
		f = front if (front[1] - front[0]).cross(front[3] - front[0]).dot(n) > 0 else front[::-1]
		g.face(obj, f, isl)
		for k in range(4):
			a, b = front[k], front[(k + 1) % 4]
			c, d = backp[(k + 1) % 4], backp[k]
			quad = [a, b, c, d]
			mid = sum(quad, Vector()) / 4
			centre = sum(front, Vector()) / 4 + n * (-(proud + back) / 2)
			side = g.island(sheet, kind, None, Face="side", Stone=i)
			L = (b - a).length
			uv = [(0, 0), (L, 0), (L, proud + back), (0, proud + back)]
			if (quad[1] - quad[0]).cross(quad[3] - quad[0]).dot(mid - centre) < 0:
				quad, uv = quad[::-1], uv[::-1]
			g.face(obj, quad, side, uv)


def clip_x_range(clip, d):
	"""where a horizontal line at plan distance d crosses a convex loop: (x_lo, x_hi) or None"""
	xs = []
	m = len(clip)
	for i in range(m):
		(x0, d0), (x1, d1) = clip[i], clip[(i + 1) % m]
		if (d0 - d) * (d1 - d) <= 0 and abs(d1 - d0) > 1e-9:
			xs.append(x0 + (x1 - x0) * (d - d0) / (d1 - d0))
		elif abs(d0 - d) < 1e-9:
			xs.append(x0)
	return (min(xs), max(xs)) if xs else None


def underlay(g, obj, org, ax, ai, prof, clip, steps=28, drop=0.06):
	"""the roof's surface just under the slates, following the bell-cast curve, so nothing shows through between rows"""
	E, A, I = Vector(org), Vector(ax), Vector(ai)
	isl = g.island(obj, "slate_under", None, Face="under", K=0.15)
	d_max = max(p[1] for p in clip)
	levels = [d_max * k / steps for k in range(steps + 1)]
	levels[-1] -= 1e-6
	prev = None
	for d in levels:
		xr = clip_x_range(clip, d)
		if xr is None:
			continue
		z = prof.z_at(d) - drop
		cur = (E + A * xr[0] + I * d + UP * z, E + A * xr[1] + I * d + UP * z, d)
		if prev:
			# in short pieces along the eave, so a later bend (the sweep at the right corner) follows the slates
			n = max(1, math.ceil(max((prev[1] - prev[0]).length, (cur[1] - cur[0]).length) / 1.2))
			nrm = (UP - I * float(np.interp((prev[2] + d) / 2, prof.d, prof.slope))).normalized()
			for k in range(n):
				a0, a1 = prev[0].lerp(prev[1], k / n), prev[0].lerp(prev[1], (k + 1) / n)
				b0, b1 = cur[0].lerp(cur[1], k / n), cur[0].lerp(cur[1], (k + 1) / n)
				g.tri_fill(obj, [[a0, a1, b1, b0]], nrm, isl, uvs_of=lambda p: (p.dot(A), p.dot(I)))
		prev = cur


def tile_line(g, obj, sheet, kind, pts, radius, tile_len, sides=7, flare=0.22, **params):
	"""round ridge tiles along a 3D polyline (hips, ridges), laid from its first point on: each tile flares at its foot and steps over
	the one before, like the reference's rolled hips. One island: u along the line, v round the tile (Tile = the tile's length)."""
	pts = [Vector(p) for p in pts]
	run = [0.0]
	for i in range(1, len(pts)):
		run.append(run[-1] + (pts[i] - pts[i - 1]).length)
	total = run[-1]

	def at(s):
		s = min(max(s, 0.0), total)
		i = max(0, min(len(pts) - 2, int(np.searchsorted(run, s)) - 1))
		seg = run[i + 1] - run[i]
		t = (s - run[i]) / seg if seg > 1e-9 else 0.0
		return pts[i].lerp(pts[i + 1], t), (pts[i + 1] - pts[i]).normalized()

	def ring(s, r):
		p, t = at(s)
		side = t.cross(UP)
		side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
		upv = side.cross(t).normalized()
		return [p + (side * math.cos(math.pi * k / sides) + upv * math.sin(math.pi * k / sides)) * r for k in range(sides + 1)], p, t

	isl = g.island(sheet, kind, None, Face="cap", Tile=tile_len, **params)
	count = max(1, round(total / tile_len))
	step = total / count

	def put(quad, uv, want):
		n = (quad[1] - quad[0]).cross(quad[3] - quad[0])
		if n.dot(want) < 0:
			quad, uv = quad[::-1], uv[::-1]
		g.face(obj, quad, isl, uv)

	for k in range(count):
		s0, s1 = k * step, (k + 1) * step
		rings = [(s0 + (s1 - s0) * j / 4, ring(s0 + (s1 - s0) * j / 4, radius * (1 + flare * (1 - j / 4) ** 1.5))) for j in range(5)]
		# the tile's foot: a half-disc stepping down onto the tile before (or closing the line's end)
		foot, centre, t = rings[0][1]
		inner = ring(s0, radius if k > 0 else 0.0)[0]
		for m in range(sides):
			v0, v1 = m / sides * math.pi * radius, (m + 1) / sides * math.pi * radius
			put([inner[m], foot[m], foot[m + 1], inner[m + 1]], [(s0 - 0.05, v0), (s0, v0), (s0, v1), (s0 - 0.05, v1)], -t)
		for j in range(4):
			(sa, (ra, ca, ta)), (sb, (rb, _, _)) = rings[j], rings[j + 1]
			for m in range(sides):
				quad = [ra[m], rb[m], rb[m + 1], ra[m + 1]]
				mid = sum(quad, Vector()) / 4
				v0, v1 = m / sides * math.pi * radius, (m + 1) / sides * math.pi * radius
				put(quad, [(sa, v0), (sb, v0), (sb, v1), (sa, v1)], mid - ca)
	# close the top end
	top, centre, t = ring(total, radius)
	for m in range(sides):
		g.face(obj, [centre, top[m], top[m + 1]] if (top[m] - centre).cross(top[m + 1] - centre).dot(t) > 0 else [centre, top[m + 1], top[m]], isl, [(total, 0), (total, 0.1), (total + 0.1, 0.1)])


def roof_main(g):
	"""the hipped, bell-cast main roof: four faces of their own depths (the end hips steeper than the front), slate rows, an underlay,
	rolled hip and ridge tiles"""
	L, Dp = RX1 - RX0, RY1 - RY0
	DF, DB, DL, DR = RIDGE_Y - RY0, RY1 - RIDGE_Y, RIDGE_L - RX0, RX1 - RIDGE_R
	prof = Profile(52.0, 40.0, 3.0, DF + 0.6)  # a gentle bell: the user found a stronger flare curled the ends up too much
	far = dict(tile=1.8, row=1.22, depth=0.74, thick=0.3, seg=4)  # the back and the left are never seen: fewer triangles
	faces = [
		("Front", "RoofA", (RX0, RY0, EAVE), (1, 0, 0), (0, 1, 0), prof, [(0, 0), (L, 0), (RIDGE_R - RX0, DF), (RIDGE_L - RX0, DF)], NEAR_SLATES),
		("Back", "RoofB", (RX1, RY1, EAVE), (-1, 0, 0), (0, -1, 0), prof.scaled(DF / DB), [(0, 0), (L, 0), (RX1 - RIDGE_L, DB), (RX1 - RIDGE_R, DB)], far),
		("Left", "RoofB", (RX0, RY1, EAVE), (0, -1, 0), (1, 0, 0), prof.scaled(DF / DL), [(0, 0), (Dp, 0), (RY1 - RIDGE_Y, DL)], far),
		("Right", "RoofB", (RX1, RY0, EAVE), (0, 1, 0), (-1, 0, 0), prof.scaled(DF / DR), [(0, 0), (Dp, 0), (RIDGE_Y - RY0, DR)], NEAR_SLATES),
	]
	for name, sheet, org, ax, ai, pf, clip, sz in faces:
		slate_face(g, sheet, name, org, ax, ai, pf, clip, sheet=sheet, **sz)
		underlay(g, sheet, org, ax, ai, pf, clip)
	ridge_z = EAVE + prof.z_at(DF)
	for (cx, cy), (rx_, ry_) in (((RX0, RY0), (RIDGE_L, RIDGE_Y)), ((RX0, RY1), (RIDGE_L, RIDGE_Y)), ((RX1, RY0), (RIDGE_R, RIDGE_Y)), ((RX1, RY1), (RIDGE_R, RIDGE_Y))):
		pts = [(cx + (rx_ - cx) * t, cy + (ry_ - cy) * t, EAVE + prof.z_at(DF * t) + 0.18) for t in np.linspace(0, 1, 48)]
		tile_line(g, "RoofB", "RoofB", "slate_cap", pts, 0.42, 1.05, Line="hip")
	tile_line(g, "RoofB", "RoofB", "slate_cap", [(RIDGE_R + (RIDGE_L - RIDGE_R) * t, RIDGE_Y, ridge_z + 0.18) for t in np.linspace(0, 1, 12)], 0.46, 1.1, Line="ridge")
	return prof, ridge_z


def gable_roof(g, name, x0, x1, y_front, y_back, z_eave, z_ridge, sheet="RoofA"):
	"""a straight gable roof whose ridge runs in y, front at y_front: two slate faces"""
	half = (x1 - x0) / 2
	pitch = math.degrees(math.atan2(z_ridge - z_eave, half))
	prof = Profile(pitch, pitch, 0.01, half + 0.2)
	Lr = y_back - y_front
	sz = dict(tile=1.6, row=0.86, depth=0.8, thick=0.24, seg=5)  # the dormer's slates are big, as in the reference
	slate_face(g, sheet, name + "L", (x0, y_front, z_eave), (0, 1, 0), (1, 0, 0), prof, [(0, 0), (Lr, 0), (Lr, half), (0, half)], **sz)
	slate_face(g, sheet, name + "R", (x1, y_back, z_eave), (0, -1, 0), (-1, 0, 0), prof, [(0, 0), (Lr, 0), (Lr, half), (0, half)], **sz)
	tile_line(g, sheet, sheet, "slate_cap", [(x0 + half, y_front - 0.05, z_ridge + 0.12), (x0 + half, y_back, z_ridge + 0.12)], 0.34, 0.95, Line="ridge")
	return prof


def box_dormer_roof(g, x0, x1, y0, depth, z_eave, pitch, sheet="RoofC"):
	"""the box dormer's roof (reference): a ridge along x, a gable end at x0 (left), a hip down toward the tower at x1"""
	D = depth
	y1 = y0 + 2 * D
	prof = Profile(pitch, pitch - 8, 0.8, D + 0.4)
	L = x1 - x0
	xr = x1 - D
	sz = dict(tile=1.3, row=0.72, depth=0.65, thick=0.2, seg=5)
	slate_face(g, sheet, "BoxF", (x0, y0, z_eave), (1, 0, 0), (0, 1, 0), prof, [(0, 0), (L, 0), (xr - x0, D), (0, D)], **sz)
	slate_face(g, sheet, "BoxB", (x1, y1, z_eave), (-1, 0, 0), (0, -1, 0), prof, [(0, 0), (L, 0), (L, D), (x1 - xr, D)], **sz)
	slate_face(g, sheet, "BoxR", (x1, y0, z_eave), (0, 1, 0), (-1, 0, 0), prof, [(0, 0), (2 * D, 0), (D, D)], **sz)
	top = z_eave + prof.z_at(D)
	tile_line(g, sheet, sheet, "slate_cap", [(xr, y0 + D, top + 0.12), (x0 - 0.05, y0 + D, top + 0.12)], 0.34, 0.95, Line="ridge")
	for cx, cy in ((x1, y0), (x1, y1)):
		tile_line(g, sheet, sheet, "slate_cap", [(cx + (xr - cx) * t, cy + (y0 + D - cy) * t, z_eave + prof.z_at(D * t) + 0.12) for t in np.linspace(0, 1, 12)], 0.3, 0.9, Line="hip")
	return prof, top


def shed_slates(g, name, x0, x1, y_wall, y_lip, z_wall, z_lip, sheet="RoofC"):
	"""a lean-to of slates from a wall out to a lip (the awning): big round slates, as the reference's annex roof"""
	run = abs(y_wall - y_lip)
	pitch = math.degrees(math.atan2(z_wall - z_lip, run))
	prof = Profile(pitch, pitch, 0.01, run + 0.2)
	sgn = 1 if y_wall > y_lip else -1
	slate_face(g, sheet, name, (x0, y_lip, z_lip), (1, 0, 0), (0, sgn, 0), prof, [(0, 0), (x1 - x0, 0), (x1 - x0, run), (0, run)], tile=1.55, row=0.86, depth=0.76, thick=0.22, seg=5)


def obox(g, obj, sheet, kind, centre, ax, ay, size, skip=(), K=1.0, **params):
	"""a box on its own axes: ax and ay (perpendicular), the third is ax x ay. Faces named as box()'s, in that frame."""
	c = Vector(centre)
	X, Y = Vector(ax).normalized(), Vector(ay).normalized()
	Z = X.cross(Y).normalized()
	h = Vector(size) / 2

	def P(sx, sy, sz):
		return c + X * (sx * h.x) + Y * (sy * h.y) + Z * (sz * h.z)

	faces = {
		"-y": ([P(-1, -1, -1), P(1, -1, -1), P(1, -1, 1), P(-1, -1, 1)], X, Z),
		"+y": ([P(1, 1, -1), P(-1, 1, -1), P(-1, 1, 1), P(1, 1, 1)], -X, Z),
		"+x": ([P(1, -1, -1), P(1, 1, -1), P(1, 1, 1), P(1, -1, 1)], Y, Z),
		"-x": ([P(-1, 1, -1), P(-1, -1, -1), P(-1, -1, 1), P(-1, 1, 1)], -Y, Z),
		"+z": ([P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1)], X, Y),
		"-z": ([P(-1, 1, -1), P(1, 1, -1), P(1, -1, -1), P(-1, -1, -1)], X, -Y),
	}
	for key, (pts, au, av) in faces.items():
		if key in skip:
			continue
		g.face(obj, pts, g.island(sheet, kind, frame_of(pts[0], au, av), Face=key, K=K, **params))


def beam(g, obj, sheet, kind, a, b, width, thick, normal, **params):
	"""a plank from a to b: `width` across it in the plane whose normal is given, `thick` along that normal"""
	a, b, n = Vector(a), Vector(b), Vector(normal).normalized()
	d = b - a
	across = n.cross(d).normalized()
	obox(g, obj, sheet, kind, (a + b) / 2, d.normalized(), across, (d.length, width, thick), **params)


def pyramid(g, obj, sheet, kind, centre, wx, wy, h):
	"""a four-sided pyramid lid on a rectangle centred at `centre` (its base), with a flat underside"""
	c = Vector(centre)
	corners = [c + Vector((sx * wx / 2, sy * wy / 2, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
	apex = c + UP * h
	for i in range(4):
		a, b = corners[i], corners[(i + 1) % 4]
		mid = (a + b) / 2
		au = (b - a).normalized()
		av = (apex - mid).normalized()
		isl = g.island(sheet, kind, frame_of(a, au, av), Face="side")
		g.face(obj, [a, b, apex], isl)
	isl = g.island(sheet, kind, frame_of(corners[0], (1, 0, 0), (0, -1, 0)), Face="-z", K=0.3)
	g.face(obj, corners[::-1], isl)


def arc_block(g, obj, sheet, kind, cx, cy, r_in, r_out, a0, a1, z0, z1, segs=4, **params):
	"""a thick curved block between two radii and two angles (degrees): the crown's merlons. Outer face u = arc length, v = z."""
	A = [math.radians(a0 + (a1 - a0) * i / segs) for i in range(segs + 1)]

	def P(r, a, z):
		return Vector((cx + r * math.cos(a), cy + r * math.sin(a), z))

	outer = g.island(sheet, kind, None, Face="outer", Width=r_out * math.radians(a1 - a0), Z0=z0, Z1=z1, **params)
	inner = g.island(sheet, kind, None, Face="inner", K=0.3, **params)
	for i in range(segs):
		u0, u1 = r_out * (A[i] - A[0]), r_out * (A[i + 1] - A[0])
		g.face(obj, [P(r_out, A[i], z0), P(r_out, A[i + 1], z0), P(r_out, A[i + 1], z1), P(r_out, A[i], z1)], outer, [(u0, z0), (u1, z0), (u1, z1), (u0, z1)])
		g.face(obj, [P(r_in, A[i + 1], z0), P(r_in, A[i], z0), P(r_in, A[i], z1), P(r_in, A[i + 1], z1)], inner, [(u1, z0), (u0, z0), (u0, z1), (u1, z1)])
	for a, flip in ((A[0], False), (A[-1], True)):
		side = g.island(sheet, kind, None, Face="side", **params)
		q = [P(r_in, a, z0), P(r_out, a, z0), P(r_out, a, z1), P(r_in, a, z1)]
		uv = [(0, z0), (r_out - r_in, z0), (r_out - r_in, z1), (0, z1)]
		if not flip:
			q, uv = q[::-1], uv[::-1]
		g.face(obj, q, side, uv)


def build_scene(g):
	W, W2, T, G, P = "Walls", "Walls2", "Trim", "Ground", "Props"
	# ------------------------------------------------ ground: the lane, the terrace, the raised garden and its walls
	lane = [(-9.0, -47.0), (23.8, -47.0), (23.8, GARDEN_FRONT - 0.01), (19.0, GARDEN_FRONT - 0.01), (17.0, -21.0), (PLANTER_X, -18.0), (PLANTER_X, 2.0), (-2.5, 2.0), (-2.5, -10.0), (-9.0, -10.0)]
	prism(g, G, G, "paving", lane, LANE - 1.6, LANE, K=0.5)
	prism(g, G, G, "tiles", [(-8.0, -37.0), (12.5, -37.0), (12.5, -11.5), (-8.0, -11.5)], LANE, LANE + 0.06)
	cx, cy, cr = CORNER
	garden = [(PLANTER_X, 0.0), (PLANTER_X, -18.0), (17.0, -21.0), (19.0, GARDEN_FRONT)] + arc(cx, cy, cr, -90, 0, 10)[0:] + [(GARDEN_RIGHT, GARDEN_BACK), (HX1, GARDEN_BACK), (HX1, 0.0)]
	garden = dedupe(garden)
	prism(g, "Base", "Base", "retaining", garden, -1.7, 0.0, top=False)
	wall_strip = [(PLANTER_X, 0.0), (PLANTER_X, -18.0), (17.0, -21.0), (19.0, GARDEN_FRONT), (20.2, GARDEN_FRONT), (18.1, -20.6), (15.6, -17.4), (15.6, 0.0)]
	prism(g, "Base", "Base", "retaining", wall_strip, LANE, -1.7, top=False)
	isl = g.island("Garden", "grass", frame_of((0, 0, 0), (1, 0, 0), (0, 1, 0)), Face="+z")
	g.tri_fill("Garden", [[Vector((x, y, 0.0)) for x, y in garden]], UP, isl)
	# curb along the front, the round corner and the right side
	curb_path = [(23.6, GARDEN_FRONT + 0.55)] + [(cx + (cr - 0.55) * math.cos(math.radians(a)), cy + (cr - 0.55) * math.sin(math.radians(a))) for a in np.linspace(-90, 0, 9)] + [(GARDEN_RIGHT - 0.55, GARDEN_BACK)]
	curb_blocks(g, T, curb_path, width=1.35, z0=-0.35, z1=0.85, block=2.6)
	# the planter: a raised bed along the left with a stone rim
	bed = [(PLANTER_X, -18.0), (18.2, -18.0), (19.0, -4.0), (18.0, -0.1), (PLANTER_X, -0.1)]
	prism(g, "Garden", "Garden", "grass_bed", bed, 0.0, 1.05, K=1.0)
	curb_blocks(g, T, [(PLANTER_X + 0.2, -17.45), (17.7, -17.45), (18.45, -4.0), (17.6, -0.1)], width=0.95, z0=-0.3, z1=1.45, block=2.0)
	# the steps from the garden's front-left corner down to the lane
	steps = 18
	rise, run_ = -LANE / steps, 0.78
	for i in range(steps):
		top = -rise * i
		y_front = GARDEN_FRONT - run_ * (i + 1)
		box(g, T, T, "step", ((19.2 + 23.4) / 2, y_front + run_ / 2 + 0.75, (top + LANE) / 2), (4.4, run_ + 1.5, max(top - LANE, 0.3)), skip=("-z", "+y"))
	# ------------------------------------------------ the house: walls
	# upper left: rose plaster with timber, the green window
	gz0, gz1 = 5.1, 11.9  # the green window, tall as the reference's: shutters above a board, glazing below
	wall(g, W, W, "plaster_pink", (HX0, 0.0, ANNEX[3]), (1, 0, 0), [(0, 0), (9.9 - HX0, 0), (9.9 - HX0, WALL_TOP - ANNEX[3]), (0, WALL_TOP - ANNEX[3])], holes=[[(1.4 - HX0, gz0 - ANNEX[3]), (6.6 - HX0, gz0 - ANNEX[3]), (6.6 - HX0, gz1 - ANNEX[3]), (1.4 - HX0, gz1 - ANNEX[3])]], thick=1.0)
	# main front: ashlar round the big arch; its top stays under the eave where the roof sweeps down
	au0, au1, spring, rise = ARCH
	zb = -0.6
	hole = arched_hole(au0 - 9.9, au1 - 9.9, 0.6, spring - zb, rise)
	top_edge = [(x - 9.9, WALL_TOP - zb + min(0.0, corner_warp(x, 0.0, WALL_TOP)) - 0.35 * smooth(SWEEP[1], SWEEP[2], x)) for x in np.linspace(HX1, 9.9, 14)]
	wall(g, W, W, "ashlar", (9.9, 0.0, zb), (1, 0, 0), [(0, 0), (HX1 - 9.9, 0)] + top_edge, holes=[hole], thick=1.4, reveal_kind="ashlar_reveal")
	cu, cv, r, a = arch_geom(au0, au1, spring, rise)
	voussoirs(g, T, T, "voussoir", 0.0, cu, cv, r, 1.05, 90 - a - 1.5, 90 + a + 1.5, 13, proud=0.32, org=(0, 0, 0))
	for x_ in (au0 - 0.55, au1 + 0.55):  # cream imposts at the arch's feet
		box(g, T, T, "cream", (x_, -0.25, spring - 0.25), (1.9, 0.9, 0.55))
	# infill inside the arch, set back: the window bay and the door
	inset = 0.75
	infill_outline = [(au0, 0.0), (au1, 0.0)] + arc(cu, cv, r, 90 - a, 90 + a, 18)
	win_hole = [(WIN[0], COUNTER[3]), (WIN[1], COUNTER[3])] + [(u, cv + math.sqrt(max(0.0, (r - inset) ** 2 - (u - cu) ** 2))) for u in np.linspace(WIN[1], WIN[0], 8)]
	door_hole = [(DOOR[0], 1.5), (DOOR[1], 1.5)] + [(u, cv + math.sqrt(max(0.0, (r - inset) ** 2 - (u - cu) ** 2))) for u in np.linspace(DOOR[1], DOOR[0], 10)]
	wall(g, W, W, "ashlar_in", (0.0, 1.4, 0.0), (1, 0, 0), infill_outline, holes=[win_hole, door_hole], thick=0.8, edges=False, back=False, reveal_kind="ashlar_reveal")
	# sides and back of the main block (seen little): plain ashlar
	# the right side (seen in shade): its top follows the eave, low at the front corner where the roof sweeps down
	wall(g, W2, W2, "ashlar", (HX1, 0.0, -0.6), (0, 1, 0), [(0, 0), (HY1, 0), (HY1, WALL_TOP + 0.6), (4.0, WALL_TOP + 0.6), (0, WALL_TOP + 0.6 - 1.3)], thick=1.0, K=0.6, edges=False)
	box(g, W2, W2, "interior", (HX1 + 0.05, 6.2, 9.4), (0.1, 1.5, 1.6), skip=("-x",))
	for zz, hh in ((8.45, 0.3), (10.35, 0.3)):
		box(g, T, T, "cream", (HX1 + 0.18, 6.2, zz), (0.36, 2.1, hh))
	wall(g, W2, W2, "ashlar", (HX1, HY1, -0.6), (-1, 0, 0), [(0, 0), (HX1 - HX0, 0), (HX1 - HX0, WALL_TOP + 0.6), (0, WALL_TOP + 0.6)], thick=1.0, K=0.25, edges=False)
	wall(g, W2, W2, "plaster_pink", (HX0, HY1, LANE), (0, -1, 0), [(0, 0), (HY1, 0), (HY1, WALL_TOP - LANE), (0, WALL_TOP - LANE)], thick=1.0, K=0.25, edges=False)
	# the lower annex at the lane, its arched door, its ledge and awning
	ax0, ax1, ay, atop = ANNEX
	# the arched door, measured from the reference: 5.8 wide, 11 tall to the crown of its arch
	d0, d1, d_spring, d_rise = 1.6, 7.4, LANE + 9.2, 1.9
	dcu, dcv, dr, da = arch_geom(d0, d1, d_spring, d_rise)
	outline = [(0, 0), (d0 - ax0, 0), (d0 - ax0, d_spring - LANE)] + [(u - ax0, v - LANE) for u, v in arc(dcu, dcv, dr, 90 + da, 90 - da, 12)] + [(d1 - ax0, d_spring - LANE), (d1 - ax0, 0), (ax1 - ax0, 0), (ax1 - ax0, atop - LANE), (0, atop - LANE)]
	wall(g, W2, W2, "plaster", (ax0, ay, LANE), (1, 0, 0), outline, thick=1.0, reveal_kind="plaster_reveal")
	wall(g, W2, W2, "plaster", (ax1, ay, LANE), (0, 1, 0), [(0, 0), (-ay, 0), (-ay, atop - LANE), (0, atop - LANE)], thick=1.0, edges=False)
	voussoirs(g, T, T, "voussoir", ay, dcu, dcv, dr, 1.1, 90 - da - 2, 90 + da + 2, 11, proud=0.3, org=(0, ay, 0))
	for k in range(7):  # pink-and-cream quoins up the door's jambs
		z = LANE + 0.2 + k * 1.32
		box(g, T, T, "voussoir" if k % 2 else "cream", (d0 - 0.55, ay - 0.08, z + 0.6), (1.3 if k % 2 else 0.95, 0.5, 1.22), Stone=40 + k)
		box(g, T, T, "voussoir" if k % 2 == 0 else "cream", (d1 + 0.55, ay - 0.08, z + 0.6), (0.95 if k % 2 else 1.3, 0.5, 1.22), Stone=50 + k)
	box(g, W2, W2, "interior", ((d0 + d1) / 2, ay + 1.6, (LANE + d_spring + d_rise) / 2 + 0.2), (d1 - d0 + 0.4, 0.2, d_spring + d_rise - LANE + 0.6), skip=("+y", "-z", "+z"))
	box(g, T, T, "cream", ((ax0 + ax1) / 2, ay / 2 - 0.15, atop + 0.17), (ax1 - ax0 + 0.4, -ay + 0.3, 0.34))
	# the annex's lean-to: big round slates straight off the wall (no gutter), held up by a timber brace at its right end
	shed_slates(g, "Awning", -1.0, 11.5, ay, ay - 3.1, atop + 0.1, atop - 1.85)
	beam(g, T, T, "wood", (11.0, ay - 0.15, atop - 3.4), (11.0, ay - 2.75, atop - 1.95), 0.32, 0.32, (1, 0, 0))
	box(g, T, T, "wood", (11.0, ay - 0.1, atop - 3.2), (0.36, 0.3, 1.0))
	# ------------------------------------------------ roofs
	prof, ridge_z = roof_main(g)
	apply_corners(g)
	# front dormer (reference): walls up to its eaves, a light lintel beam across, a boarded gable framed by bargeboards, a window with
	# brick reveals, both shutters swung open (the left flat to the wall, the right toward the viewer), a thick cream sill
	dx0, dx1, dy = 7.6, 14.3, 0.4  # centred on x 10.95, measured from its bargeboards and apex
	d_eave, d_apex, zb_d = 19.7, 23.0, 13.9
	wx0, wx1, wz0, wz1 = 9.2, 12.8, 15.75, 19.25
	dcx = (dx0 + dx1) / 2
	half = (dx1 - dx0) / 2
	slope_d = (d_apex - d_eave) / half
	over_d = 0.15  # the roof barely passes the walls at the sides, as in the reference
	m_dormer = g.mark()
	gable_roof(g, "Dormer", dx0 - over_d, dx1 + over_d, dy - 1.0, 7.6, d_eave - over_d * slope_d + 0.28, d_apex + 0.28)
	wall(g, W2, W2, "planks", (dx0, dy, zb_d), (1, 0, 0), [(0, 0), (dx1 - dx0, 0), (dx1 - dx0, d_eave - zb_d), (half, d_apex - zb_d), (0, d_eave - zb_d)], holes=[[(wx0 - dx0, wz0 - zb_d), (wx1 - dx0, wz0 - zb_d), (wx1 - dx0, wz1 - zb_d), (wx0 - dx0, wz1 - zb_d)]], thick=0.9, reveal_kind="brick")
	wall(g, W2, W2, "brick", (dx1, dy, zb_d), (0, 1, 0), [(0, 0), (4.8, 0), (4.8, d_eave - zb_d), (0, d_eave - zb_d)], thick=0.5, edges=False, K=0.8)
	wall(g, W2, W2, "brick", (dx0, dy + 4.8, zb_d), (0, -1, 0), [(0, 0), (4.8, 0), (4.8, d_eave - zb_d), (0, d_eave - zb_d)], thick=0.5, edges=False, K=0.3)
	box(g, W2, W2, "interior", ((wx0 + wx1) / 2, dy + 1.0, (wz0 + wz1) / 2), (wx1 - wx0 + 0.4, 0.1, wz1 - wz0 + 0.4), skip=("+y",))
	box(g, T, T, "wood_light", (dcx, dy - 0.1, wz1 + 0.35), (dx1 - dx0 + 0.8, 1.0, 0.7))
	box(g, T, T, "cream", ((wx0 + wx1) / 2, dy - 0.35, wz0 - 0.42), (wx1 - wx0 + 1.0, 1.7, 0.85))
	for side in (-1, 1):  # bargeboards along the gable's front edge
		e = Vector((dcx + side * (half + over_d), dy - 0.95, d_eave - over_d * slope_d + 0.05))
		beam(g, T, T, "wood_light", e, (dcx, dy - 0.95, d_apex + 0.05), 0.55, 0.3, (0, 1, 0))
	for side, ang, sw in ((-1, 172.0, 2.2), (1, 160.0, 2.3)):  # shutters: planks with a Z of battens
		hx = wx0 if side < 0 else wx1
		th = math.radians(ang)
		d = Vector((-side * math.cos(th), -math.sin(th), 0))
		sh, st = wz1 - wz0 - 0.1, 0.18
		zc = (wz0 + wz1) / 2
		c_ = Vector((hx, dy - 0.12, zc)) + d * (sw / 2 + 0.05)
		box(g, T, T, "shutter", tuple(c_), (sw, st, sh), yaw=math.degrees(math.atan2(d.y, d.x)))
		n = Vector((d.y, -d.x, 0))
		for face in (1, -1):
			off = n * face * (st / 2 + 0.05)
			for zz in (zc - sh / 2 + 0.45, zc + sh / 2 - 0.45):
				obox(g, T, T, "shutter", tuple(c_ + off + UP * (zz - zc)), d, n, (sw - 0.16, 0.1, 0.3))
			diag = (d * (sw - 0.5) + UP * (sh - 1.2)).normalized()
			obox(g, T, T, "shutter", tuple(c_ + off), diag, n, (math.hypot(sw - 0.5, sh - 1.2), 0.1, 0.28))
	g.warp_since(m_dormer, lean_about((dcx, dy, zb_d), 1.6))  # the whole dormer leans a touch, hand-built
	# vent dormer, small, up the left
	box(g, W2, W2, "planks", (3.3, 4.8, 21.2), (3.2, 2.2, 1.8))
	box(g, W2, W2, "interior", (3.3, 3.68, 21.0), (2.2, 0.05, 0.7), skip=("+y",))
	obox(g, T, T, "wood_lid", (3.3, 4.45, 22.3), (1, 0, 0), (0, math.cos(math.radians(14)), math.sin(math.radians(14))), (3.9, 3.4, 0.34))
	# box dormer by the tower (reference): a pink brick front only 3 studs above the roof, a cream strip under its eave, a little
	# shuttered window; its roof has a gable end on the left and a hip down toward the tower on the right
	bx0, bx1, by, b_top, b_foot = 18.95, 26.9, 6.9, 26.8, 19.4
	wall(g, W2, W2, "brick", (bx0, by, b_foot), (1, 0, 0), [(0, 0), (bx1 - bx0, 0), (bx1 - bx0, b_top - b_foot), (0, b_top - b_foot)], holes=[[(3.05, 24.35 - b_foot), (4.65, 24.35 - b_foot), (4.65, 26.1 - b_foot), (3.05, 26.1 - b_foot)]], thick=0.7, reveal_kind="wood")
	wall(g, W2, W2, "brick", (bx1, by, b_foot), (0, 1, 0), [(0, 0), (4.3, 0), (4.3, b_top - b_foot), (0, b_top - b_foot)], thick=0.6, edges=False, K=0.7)
	box_prof, box_top = box_dormer_roof(g, bx0 - 0.5, bx1 + 0.5, by - 0.5, 2.7, 27.0, 46.0)

	def box_roof_h(y):
		return 27.0 + box_prof.z_at(min(y - (by - 0.5), (by - 0.5 + 5.4) - y))

	gw = 4.4  # the left gable wall, from the front wall back into the main roof, its top under the slates
	gable = [(0, 0), (gw, 0)] + [(u, box_roof_h(by + gw - u) - 0.12 - b_foot) for u in np.linspace(gw, 0, 13)]
	wall(g, W2, W2, "brick", (bx0, by + gw, b_foot), (0, -1, 0), dedupe(gable), thick=0.6, edges=False, K=0.3)
	# under its eave: a dark timber fascia of upright boards over a thin cream strip (reference)
	box(g, T, T, "planks", ((bx0 + bx1) / 2, by - 0.1, b_top + 0.12), (bx1 - bx0 + 0.3, 0.42, 0.72), Upright=1)
	box(g, T, T, "cream", ((bx0 + bx1) / 2, by - 0.08, b_top - 0.38), (bx1 - bx0 + 0.2, 0.36, 0.26))
	m_win = g.mark()
	box(g, W2, W2, "interior", (22.85, by + 0.62, 25.2), (1.8, 0.1, 1.95), skip=("+y",))
	box(g, T, T, "cream", (22.85, by - 0.25, 24.2), (2.3, 0.7, 0.3))
	box(g, T, T, "shutter", (22.35, by - 0.25, 25.2), (0.8, 0.18, 1.8), yaw=-28)
	g.warp_since(m_win, lean_about((22.85, by, 25.2), -3.0))
	# chimney: a pink brick stack, a cream cap slab, on it a little hooded box with a vent, a pyramid lid and a knob (reference); it
	# leans a touch
	m_chim = g.mark()
	box(g, W2, W2, "brick", (2.95, 8.7, 26.8), (2.4, 3.4, 11.6))
	box(g, T, T, "cream", (2.95, 8.7, 33.0), (3.1, 4.1, 0.8))
	box(g, T, T, "cream", (2.95, 8.7, 34.05), (1.9, 2.5, 1.3))
	box(g, W2, W2, "interior", (3.92, 8.7, 34.1), (0.06, 1.3, 0.62), skip=("-x",))
	pyramid(g, T, T, "cream", (2.95, 8.7, 34.7), 2.5, 3.1, 0.8)
	lathe(g, T, T, "cream", 2.95, 8.7, 35.45, [(0.0, 0.0), (0.2, 0.0), (0.24, 0.22), (0.12, 0.36), (0.22, 0.52), (0.0, 0.72)], segs=8)
	g.warp_since(m_chim, lean_about((2.95, 8.7, 22.0), -1.5))
	# ------------------------------------------------ the tower
	tx, ty, tr_mid = TOWER
	cylinder(g, "Tower", "Tower", "ashlar_round", tx, ty, tr_mid, -0.6, T_WALL, segs=44, band=3.2, shape=tower_shape)
	tr = TR_TOP  # the top: corbels, ring, crown and cone sit on the tapered tower's top
	# the top (reference): small cream corbels carry a projecting cream ring; on it the crown, nine dark openings between merlons that
	# carry brick chevrons; the cone's eave hangs low over it
	for k in range(30):
		a = 2 * math.pi * k / 30
		box(g, "Tower", "Tower", "corbel", (tx + (tr + 0.12) * math.cos(a), ty + (tr + 0.12) * math.sin(a), T_WALL - 0.24), (0.32, 0.36, 0.48), yaw=math.degrees(a) + 90, skip=("+z",), Corbel=k)
	lathe(g, "Tower", "Tower", "cream_ring", tx, ty, T_WALL, [(tr - 0.05, 0.0), (tr + 0.58, 0.06), (tr + 0.62, 0.58), (tr + 0.42, RING_TOP - T_WALL)], segs=48)
	cz, crad, ch = CONE
	cone = cone_profile(cz, crad, ch)
	cr_in, cr_out = tr - 0.45, tr + 0.18
	crown_top = float(np.interp(cr_out, [p[0] for p in cone][::-1], [p[1] for p in cone][::-1])) + 0.15  # meets the cone's underside
	cylinder(g, "Tower", "Tower", "interior", tx, ty, cr_in, RING_TOP, crown_top, segs=36, band=10)
	bays, a_front = 9, -60.0  # an opening faces the camera, as in the reference
	open_deg = math.degrees(1.75 / cr_out)
	for k in range(bays):
		a0 = a_front + open_deg / 2 + k * 360 / bays
		arc_block(g, "Tower", "Tower", "crown", tx, ty, cr_in, cr_out, a0, a0 + 360 / bays - open_deg, RING_TOP, crown_top, segs=4, Merlon=k)
	lathe(g, "Tower", "Tower", "cream", tx, ty, RING_TOP - 0.02, [(cr_in, 0.0), (cr_out + 0.05, 0.0), (cr_out + 0.05, 0.12), (cr_in, 0.12)], segs=36)
	slate_cone(g, "RoofC", "Cone", tx, ty, cone, tile=2.05, row=1.3, depth=1.0, thick=0.36, seg=5, sheet="RoofC")
	lathe(g, "RoofC", "RoofC", "slate_under", tx, ty, cz - 0.3, [(crad - 0.1, 0.0), (cr_in, 1.4)], segs=44, flip=True)
	lathe(g, T, T, "cream", tx, ty, cz + ch - 0.6, [(0.0, 0.0), (0.7, 0.0), (0.55, 0.5), (0.25, 0.8), (0.32, 1.1), (0.12, 1.6), (0.0, 2.1)], segs=12)
	# the tower window (reference): a deep cream lintel with a drip above it, a thick projecting sill, slim jambs, a timber frame;
	# set a few degrees off true, as a hand-built window would be
	ang = math.radians(-84.6)
	zc_w = 31.25 + TZ
	rw, ox, oy = tower_shape(zc_w)
	radial = Vector((math.cos(ang), math.sin(ang), 0))
	tang = Vector((-math.sin(ang), math.cos(ang), 0))
	centre_w = Vector((tx + ox, ty + oy, zc_w)) + radial * (rw + 0.05)
	tilt = math.radians(-4.0)
	Xw = tang * math.cos(tilt) + UP * math.sin(tilt)
	Zw = -tang * math.sin(tilt) + UP * math.cos(tilt)

	def on_tower(out, along, z, size, kind, obj=T, skip=()):
		c = centre_w + radial * out + Xw * along + Zw * (z - zc_w)
		obox(g, obj, obj, kind, tuple(c), Xw, -radial, size, skip=skip)

	on_tower(-0.1, 0.0, zc_w, (3.0, 0.3, 4.95), "interior", obj=W, skip=("+y",))
	on_tower(0.15, 0.0, 34.25 + TZ, (4.0, 0.9, 1.0), "cream")
	on_tower(0.25, 0.0, 34.98 + TZ, (3.3, 0.6, 0.2), "cream_ring")
	on_tower(0.35, 0.0, 28.5 + TZ, (3.8, 1.2, 0.62), "cream")
	for s in (-1, 1):
		on_tower(0.12, s * 1.68, zc_w, (0.36, 0.5, 4.95), "cream")
	for off in (-0.52, 0.52):
		on_tower(0.2, off, zc_w, (0.2, 0.22, 4.9), "wood")
	for zz in (29.0, 30.65, 32.3, 33.65):
		on_tower(0.2, 0.0, zz + TZ, (3.0, 0.22, 0.2), "wood")
	# ------------------------------------------------ front details: timber, the green window, the window box, the door, the window bay
	for x in (0.35, 8.4):
		box(g, T, T, "wood", (x, -0.1, (ANNEX[3] + WALL_TOP) / 2 + 0.2), (0.7, 0.35, WALL_TOP - ANNEX[3] - 0.2))
	box(g, T, T, "wood", (2.2, -0.1, ANNEX[3] + 0.9), (13.6, 0.3, 0.55))
	# the green window (reference): a green frame, two closed shutters with heart cut-outs above a light green board, glazing below
	gzb = 7.45  # the board
	m_green = g.mark()
	for x0_, x1_, z0_, z1_ in ((1.4, 6.6, gz0, gz0 + 0.4), (1.4, 6.6, gz1 - 0.4, gz1), (1.4, 1.8, gz0, gz1), (6.2, 6.6, gz0, gz1), (3.85, 4.15, gz0, gzb)):
		box(g, T, T, "green", ((x0_ + x1_) / 2, 0.45, (z0_ + z1_) / 2), (x1_ - x0_, 0.3, z1_ - z0_))
	box(g, W, W, "glass", (4.0, 0.62, (gz0 + 0.4 + gzb) / 2), (4.4, 0.05, gzb - gz0 - 0.4), skip=("+y",))
	for xc in (2.825, 5.175):
		box(g, T, T, "shutter_green", (xc, 0.48, (gzb + 0.5 + gz1 - 0.4) / 2), (2.3, 0.2, gz1 - 0.4 - gzb - 0.5), Heart=1)
	box(g, T, T, "green_light", (4.0, 0.05, gzb + 0.25), (5.6, 1.0, 0.5))
	g.warp_since(m_green, lean_about((4.0, 0.45, 8.5), 1.8))
	box(g, T, T, "window_box", (3.85, -0.75, 4.35), (6.3, 1.5, 1.1))
	for x in (2.3, 5.4):
		box(g, T, T, "metal", (x, -1.52, 4.35), (0.45, 0.06, 0.5))
	# door leaves and their glass, the bay's glass and its counter
	leaf_top = 6.2  # the reference's leaves stop low, under a tall fanlight
	for k, (x0_, x1_) in enumerate(((DOOR[0], (DOOR[0] + DOOR[1]) / 2), ((DOOR[0] + DOOR[1]) / 2, DOOR[1]))):
		box(g, T, T, "door", ((x0_ + x1_) / 2, 1.85, (1.5 + leaf_top) / 2), (x1_ - x0_ - 0.06, 0.3, leaf_top - 1.5), Leaf=k)
	glass_top = [(u, cv + math.sqrt(max(0.0, (r - inset) ** 2 - (u - cu) ** 2))) for u in np.linspace(DOOR[1], DOOR[0], 10)]
	isl = g.island(W, "glass", frame_of((0, 1.9, 0), (1, 0, 0), UP), Face="front")
	g.tri_fill(W, [[Vector((DOOR[0], 1.9, leaf_top)), Vector((DOOR[1], 1.9, leaf_top))] + [Vector((u, 1.9, v)) for u, v in glass_top]], Vector((0, -1, 0)), isl)
	box(g, T, T, "wood", ((DOOR[0] + DOOR[1]) / 2, 1.8, leaf_top + 0.05), (DOOR[1] - DOOR[0], 0.35, 0.3))
	box(g, T, T, "wood", ((DOOR[0] + DOOR[1]) / 2, 1.8, 8.7), (0.25, 0.3, 5.0))
	win_top = [(u, cv + math.sqrt(max(0.0, (r - inset) ** 2 - (u - cu) ** 2))) for u in np.linspace(WIN[1], WIN[0], 8)]
	isl = g.island(W, "glass", frame_of((0, 2.0, 0), (1, 0, 0), UP), Face="front")
	g.tri_fill(W, [[Vector((WIN[0], 2.0, COUNTER[3])), Vector((WIN[1], 2.0, COUNTER[3]))] + [Vector((u, 2.0, v)) for u, v in win_top]], Vector((0, -1, 0)), isl)
	box(g, T, T, "wood", ((WIN[0] + WIN[1]) / 2, 1.85, 7.9), (0.25, 0.3, 6.2))
	box(g, T, T, "wood", ((WIN[0] + WIN[1]) / 2, 1.85, 7.55), (WIN[1] - WIN[0], 0.3, 0.25))
	cx0, cx1, cz0, cz1 = COUNTER
	box(g, T, T, "window_box", ((cx0 + cx1) / 2, 0.0, (cz0 + cz1) / 2), (cx1 - cx0, 3.2, cz1 - cz0))
	box(g, T, T, "cream", ((WIN[0] + WIN[1]) / 2, 0.4, cz0 / 2), (WIN[1] - WIN[0] - 0.2, 2.2, cz0))
	# door steps and the round mat
	for k, (w_, y0_, z_) in enumerate(((7.0, 1.15, 1.26), (7.6, 0.38, 0.84), (8.2, -0.39, 0.42))):
		box(g, T, T, "step_pink", ((DOOR[0] + DOOR[1]) / 2, (y0_ + 1.9) / 2, z_ / 2 - 0.15), (w_, 1.9 - y0_, z_ + 0.3), skip=("-z",))
	build_props(g)
	mat = [((DOOR[0] + DOOR[1]) / 2 + 4.0 * math.cos(math.radians(a)), -0.39 + 3.4 * math.sin(math.radians(a))) for a in np.linspace(180, 360, 18)]
	isl = g.island(P, "mat", frame_of(((DOOR[0] + DOOR[1]) / 2 - 4.0, -3.8, 0.06), (1, 0, 0), (0, 1, 0)), Face="+z")
	g.tri_fill(P, [[Vector((x, y, 0.06)) for x, y in mat]], UP, isl)


def dedupe(pts):
	out = []
	for p in pts:
		if not out or math.dist(out[-1], p) > 1e-4:
			out.append(p)
	if math.dist(out[0], out[-1]) < 1e-4:
		out.pop()
	return out


def curb_blocks(g, obj, path, width, z0, z1, block, gap=0.08):
	"""stone blocks along a plan polyline (centre line), each turned to its stretch"""
	pts = [Vector((x, y, 0)) for x, y in path]
	total = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
	count = max(1, round(total / block))
	step = total / count

	def at(s):
		for i in range(len(pts) - 1):
			seg = (pts[i + 1] - pts[i]).length
			if s <= seg or i == len(pts) - 2:
				return pts[i] + (pts[i + 1] - pts[i]) * (s / seg)
			s -= seg

	for k in range(count):
		a, b = at(k * step + gap / 2), at((k + 1) * step - gap / 2)
		mid = (a + b) / 2
		yaw = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
		box(g, obj, obj, "curb", (mid.x, mid.y, (z0 + z1) / 2), ((b - a).length, width, z1 - z0), yaw=yaw, skip=("-z",), Block=k)


# ---------------------------------------------------------------------------------------------------------------- path, props
PATH = [(20.6, -4.6), (21.0, -9.0), (22.4, -15.0), (23.0, -21.0), (22.4, -27.0), (21.3, -31.2)]


def corridor(path, widths):
	"""a band round a polyline: left side out, right side back"""
	pts = [Vector((x, y, 0)) for x, y in path]
	left, right = [], []
	for i, p in enumerate(pts):
		t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
		n = Vector((-t.y, t.x, 0))
		w = widths[i] / 2
		left.append(p + n * w)
		right.append(p - n * w)
	return [(p.x, p.y) for p in left] + [(p.x, p.y) for p in reversed(right)]


def point_in_poly(p, poly):
	x, y = p
	inside = False
	n = len(poly)
	for i in range(n):
		(x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
		if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
			inside = not inside
	return inside


def chaikin(poly, it=2):
	for _ in range(it):
		out = []
		n = len(poly)
		for i in range(n):
			a, b = poly[i], poly[(i + 1) % n]
			out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
			out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
		poly = out
	return poly


def path_stones(g, obj="Path"):
	"""flagstones: Voronoi cells of dart-thrown points inside the path's band, shrunk and rounded, set on cream grout"""
	widths = [6.4, 6.0, 5.6, 5.2, 4.8, 4.4]
	band = corridor(PATH, widths)
	isl = g.island(obj, "grout", frame_of((0, 0, 0.03), (1, 0, 0), (0, 1, 0)), Face="+z")
	g.tri_fill(obj, [[Vector((x, y, 0.03)) for x, y in band]], UP, isl)
	r = random.Random(5)
	xs = [p[0] for p in band]
	ys = [p[1] for p in band]
	pts = []
	for _ in range(5000):
		p = (r.uniform(min(xs), max(xs)), r.uniform(min(ys), max(ys)))
		if point_in_poly(p, band) and p[1] > GARDEN_FRONT + 1.2 and all(math.dist(p, q) > 2.6 for q in pts):
			pts.append(p)
	for i, p in enumerate(pts):
		cell = [(p[0] - 2.4, p[1] - 2.4), (p[0] + 2.4, p[1] - 2.4), (p[0] + 2.4, p[1] + 2.4), (p[0] - 2.4, p[1] + 2.4)]
		for j, q in enumerate(pts):
			if i == j or math.dist(p, q) > 5.0:
				continue
			# keep the half-plane nearer p: clip by the bisector, as a big convex quad on p's side
			mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
			dx, dy = q[0] - p[0], q[1] - p[1]
			L = math.hypot(dx, dy)
			nx, ny = dx / L, dy / L
			tx, ty = -ny, nx
			half = [(mx + tx * 20, my + ty * 20), (mx - tx * 20, my - ty * 20), (mx - tx * 20 - nx * 20, my - ty * 20 - ny * 20), (mx + tx * 20 - nx * 20, my + ty * 20 - ny * 20)]
			if signed_area(half) < 0:
				half = half[::-1]
			cell = clip_convex(cell, half)
			if len(cell) < 3:
				break
		if len(cell) < 3:
			continue
		cx = sum(c[0] for c in cell) / len(cell)
		cy = sum(c[1] for c in cell) / len(cell)
		gap = 0.13
		shrunk = []
		for c in cell:
			d = math.dist(c, (cx, cy))
			k = max(0.2, (d - gap) / max(d, 1e-6))
			shrunk.append((cx + (c[0] - cx) * k, cy + (c[1] - cy) * k))
		poly = chaikin(shrunk, 1)
		top = 0.24 + r.uniform(0.0, 0.08)
		inset = 0.12
		inner = [(cx + (c[0] - cx) * (1 - inset / max(math.dist(c, (cx, cy)), 0.3)), cy + (c[1] - cy) * (1 - inset / max(math.dist(c, (cx, cy)), 0.3))) for c in poly]
		tilt = (r.uniform(-0.04, 0.04), r.uniform(-0.04, 0.04))

		def zt(x, y, base):
			return base + (x - cx) * tilt[0] + (y - cy) * tilt[1]

		t_isl = g.island(obj, "flag", frame_of((cx, cy, top), (1, 0, 0), (0, 1, 0)), Face="+z", Stone=i)
		g.tri_fill(obj, [[Vector((x, y, zt(x, y, top))) for x, y in inner]], UP, t_isl)
		s_isl = g.island(obj, "flag", None, Face="side", Stone=i)
		run = 0.0
		n = len(poly)
		for k in range(n):
			a, b = poly[k], poly[(k + 1) % n]
			ia, ib = inner[k], inner[(k + 1) % n]
			L = math.dist(a, b)
			A0, B0 = Vector((a[0], a[1], -0.1)), Vector((b[0], b[1], -0.1))
			A1, B1 = Vector((a[0], a[1], zt(a[0], a[1], top - 0.08))), Vector((b[0], b[1], zt(b[0], b[1], top - 0.08)))
			IA, IB = Vector((ia[0], ia[1], zt(ia[0], ia[1], top))), Vector((ib[0], ib[1], zt(ib[0], ib[1], top)))
			for quad, uv in (([A0, B0, B1, A1], [(run, 0), (run + L, 0), (run + L, 0.2), (run, 0.2)]), ([A1, B1, IB, IA], [(run, 0.2), (run + L, 0.2), (run + L, 0.34), (run, 0.34)])):
				if (quad[1] - quad[0]).cross(quad[3] - quad[0]).dot(Vector((a[0] - cx, a[1] - cy, 0.3))) < 0:
					quad, uv = quad[::-1], uv[::-1]
				g.face(obj, quad, s_isl, uv)
			run += L


def barrel(g, obj, cx, cy, z0, R, H, seed=0, lid=True):
	prof = [(R * 0.86, 0.0)] + [(R * (0.86 + 0.14 * math.sin(math.pi * t)), H * t) for t in np.linspace(0.08, 0.92, 7)] + [(R * 0.86, H)]
	lathe(g, obj, obj, "barrel", cx, cy, z0, prof, segs=18, Seed=seed, H=H)
	for t in (0.14, 0.38, 0.62, 0.86):
		rr = R * (0.86 + 0.14 * math.sin(math.pi * t)) + 0.05
		lathe(g, obj, obj, "hoop", cx, cy, z0 + H * t - 0.13, [(rr - 0.02, 0.0), (rr + 0.03, 0.02), (rr + 0.03, 0.24), (rr - 0.02, 0.26)], segs=18)
	if lid:
		disc(g, obj, obj, "barrel_lid", cx, cy, R * 0.84, z0 + H - 0.12, segs=18)


def pot(g, obj, kind, cx, cy, z0, prof, segs=20, inner=None):
	lathe(g, obj, obj, kind, cx, cy, z0, prof, segs=segs)
	if inner is not None:
		disc(g, obj, obj, "soil", cx, cy, inner[0], z0 + inner[1], segs=segs)


def lantern(g, obj, cx, cy, z, yaw=0.0, s=1.0):
	box(g, obj, obj, "metal", (cx, cy, z - 0.55 * s), (0.9 * s, 0.9 * s, 0.14 * s), yaw=yaw)
	box(g, obj, obj, "lamp", (cx, cy, z), (0.7 * s, 0.7 * s, 1.0 * s), yaw=yaw)
	for sx in (-1, 1):
		for sy in (-1, 1):
			R = Matrix.Rotation(math.radians(yaw), 3, "Z")
			o = R @ Vector((sx * 0.38 * s, sy * 0.38 * s, 0))
			box(g, obj, obj, "metal", (cx + o.x, cy + o.y, z), (0.1 * s, 0.1 * s, 1.1 * s), yaw=yaw)
	lathe(g, obj, obj, "metal", cx, cy, z + 0.5 * s, [(0.0, 0.0), (0.62 * s, 0.0), (0.0, 0.55 * s)], segs=4)
	lathe(g, obj, obj, "metal", cx, cy, z + 1.0 * s, [(0.0, 0.0), (0.1 * s, 0.0), (0.1 * s, 0.25 * s), (0.0, 0.3 * s)], segs=6)


def build_props(g):
	P, T = "Props", "Trim"
	path_stones(g)
	# barrels, the jug and the pots by the house's right corner and the tower's foot (measured from the reference)
	barrel(g, P, 30.2, 2.9, 0.0, 2.0, 4.3, seed=1)
	lathe(g, P, P, "pot_navy", 30.4, 2.7, 4.2, [(0.0, 0.0), (0.55, 0.0), (0.75, 0.45), (0.6, 0.95), (0.32, 1.15), (0.38, 1.35), (0.0, 1.4)], segs=12)
	barrel(g, P, 30.0, -2.2, 0.0, 1.15, 2.2, seed=2, lid=False)
	disc(g, P, P, "soil", 30.0, -2.2, 1.0, 1.95, segs=16)
	pot(g, P, "pot_navy", 29.4, -9.3, 0.0, [(1.2, 0.0), (2.0, 0.5), (2.35, 1.5), (2.2, 2.6), (1.7, 3.35), (1.45, 3.55), (1.55, 3.7), (1.35, 3.75)], inner=(1.35, 3.55))
	pot(g, P, "terracotta", 33.3, -5.5, 0.0, [(0.55, 0.0), (0.95, 0.5), (1.05, 1.3), (0.7, 2.0), (0.45, 2.3), (0.55, 2.55), (0.0, 2.6)])
	for (x, y, s) in ((34.0, -1.4, 0.9), (36.1, -4.1, 0.6), (32.0, -8.0, 0.85)):
		pot(g, P, "terracotta", x, y, 0.0, [(0.55 * s, 0.0), (0.9 * s, 0.9 * s), (1.0 * s, 1.0 * s), (0.88 * s, 1.0 * s)], inner=(0.82 * s, 0.85 * s))
	# the chalkboard sign on its easel
	cx, cy = 19.4, -13.4
	yaw = 22.0
	box(g, P, P, "chalkboard", (cx, cy, 3.6), (3.3, 0.16, 4.2), yaw=yaw)
	R = Matrix.Rotation(math.radians(yaw), 3, "Z")
	for sx in (-1, 1):
		o = R @ Vector((sx * 1.78, 0, 0))
		box(g, P, P, "wood_light", (cx + o.x, cy + o.y, 3.0), (0.28, 0.3, 6.0), yaw=yaw)
	for zz in (1.35, 5.85):
		box(g, P, P, "wood_light", (cx, cy, zz), (3.8, 0.3, 0.3), yaw=yaw)
	lathe(g, P, P, "wood_light", cx, cy, 5.95, [(0.0, 0.0), (0.3, 0.0), (0.12, 0.5), (0.0, 0.7)], segs=6)
	o = R @ Vector((0, 1.6, 0))
	box(g, P, P, "wood_light", (cx + o.x, cy + o.y, 2.8), (3.2, 0.16, 5.4), yaw=yaw)
	# lanterns: on the counter and beside the annex door
	lantern(g, P, 15.6, -0.5, COUNTER[3] + 0.8, yaw=8.0, s=1.25)
	box(g, P, P, "metal", (-0.9, -3.2, -2.4), (0.2, 1.4, 0.2))
	lathe(g, P, P, "metal", -0.9, -3.9, -2.85, [(0.0, 0.0), (0.25, 0.0), (0.25, 0.35), (0.0, 0.4)], segs=6)
	lantern(g, P, -0.9, -3.9, -4.4, s=2.1)
	box(g, P, P, "shutter", (HX0 + 0.25, -1.35, 9.6), (0.22, 2.5, 4.4))
	for zz in (8.2, 11.0):
		box(g, P, P, "metal", (HX0 + 0.25, -0.15, zz), (0.3, 0.5, 0.18))
	# the hanging sign at the front corner
	box(g, P, P, "metal", (HX0 + 0.35, -1.9, 13.0), (0.16, 3.8, 0.16))
	box(g, P, P, "sign", (HX0 + 0.35, -2.7, 11.75), (0.18, 2.3, 2.0))
	# the doormat, a book on the counter, the window box's pot
	box(g, P, P, "book", (13.2, -0.6, COUNTER[3] + 0.1), (1.2, 0.9, 0.2), yaw=12)
	pot(g, P, "terracotta", 2.0, -0.9, 4.9, [(0.4, 0.0), (0.62, 0.65), (0.7, 0.72), (0.6, 0.72)], inner=(0.58, 0.66))
	# the terrace's tall cream pot
	pot(g, P, "pot_cream", 6.1, -33.8, LANE, [(0.8, 0.0), (1.3, 0.6), (1.45, 1.6), (1.2, 2.6), (1.0, 3.0), (1.15, 3.2), (1.0, 3.25)], inner=(0.95, 3.1))


# ---------------------------------------------------------------------------------------------------------------- foliage
sys.path.insert(0, HERE)
import foliage_kit as fk  # noqa: E402


def blob(name, centre, radii, count, sphere_r, seed, colours, up_lean=0.35, subdiv=2, lumps=0.22, cards=0, card_cell=fk.CELL_SPARSE, card_size=1.0):
	"""the video's foliage cloud: many spheres on a lumpy emitter shape, shaded with the emitter's smooth normals (one soft volume),
	leaf cards on its rim for a frilly edge. Vertex colours: dark and cool low and inside, lighter and warmer up top."""
	r = random.Random(seed)
	c = Vector(centre)
	rx, ry, rz = radii
	bm = bmesh.new()
	col_layer = bm.loops.layers.float_color.new("Col")
	normals = {}
	dark, mid, light = (Vector(hex_lin(h)) for h in colours)

	def emitter_dir():
		v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1) * 0.9 + 0.15)).normalized()
		return v

	def lump(v):
		return 1 + lumps * math.sin(3.1 * v.x + seed) * math.cos(2.7 * v.y - seed * 0.5) + lumps * 0.6 * math.sin(4.3 * v.z + seed * 0.3)

	placed = []
	for _ in range(count * 8):
		if len(placed) >= count:
			break
		v = emitter_dir()
		if v.z < -0.55:
			continue
		p = c + Vector((v.x * rx, v.y * ry, v.z * rz)) * lump(v) * r.uniform(0.82, 1.0)
		if any((p - q).length < sphere_r * 0.55 for q in placed):
			continue
		placed.append(p)
	for p in placed:
		rr = sphere_r * r.uniform(0.75, 1.2)
		bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=rr, matrix=Matrix.Translation(p))
	bm.verts.index_update()
	for f in bm.faces:
		f.smooth = True
		for lp in f.loops:
			d = lp.vert.co - c
			hgt = max(0.0, min(1.0, (d.z / rz + 1) / 2))
			out = max(0.0, min(1.0, (Vector((d.x / rx, d.y / ry, d.z / rz)).length - 0.55) / 0.5))
			t = hgt * 0.75 + out * 0.25
			col = dark.lerp(mid, min(1.0, t / 0.55)) if t < 0.55 else mid.lerp(light, (t - 0.55) / 0.45)
			lp[col_layer] = (*col, 1.0)
	nlist = []
	for vert in bm.verts:
		d = vert.co - c
		n = Vector((d.x / (rx * rx), d.y / (ry * ry), d.z / (rz * rz))).normalized()
		nlist.append(tuple((n * (1 - up_lean) + Vector((0, 0, up_lean))).normalized()))
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	me.normals_split_custom_set_from_vertices(nlist)
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	objs = [obj]
	if cards:
		b = fk.Builder()
		for _ in range(cards):
			v = emitter_dir()
			if v.z < -0.5:
				continue
			p = c + Vector((v.x * rx, v.y * ry, v.z * rz)) * lump(v) * r.uniform(0.98, 1.16)
			hgt = (v.z + 1) / 2
			cell = fk.CELL_DARK if hgt < 0.35 else (fk.CELL_MID if hgt < 0.7 else r.choice((fk.CELL_LIGHT, fk.CELL_SPARSE, fk.CELL_MID)))
			fk.card(b, r, p, card_size * r.uniform(0.75, 1.3), cell, c, up_lean)
		objs.append(b.finish(name + "Cards"))
	return objs


def cloud(name, lobes, sphere_r, seed, colours, card_tint=None, cards_per=40, card_size=1.3, up_lean=0.3, subdiv=2):
	"""the video's foliage cloud, in lobes: spheres over the union of a few ellipsoids, each vertex shaded with its own lobe's smooth
	normal (so every clump reads as a soft ball, lit on one side), vertex colours dark low and inside, lighter up top; a coat of leaf cards"""
	r = random.Random(seed)
	bm = bmesh.new()
	col_layer = bm.loops.layers.float_color.new("Col")
	dark, mid, light = (Vector(hex_lin(h)) for h in colours)
	L = [(Vector(c), Vector(rr)) for c, rr in lobes]
	zs = [c.z - rr.z for c, rr in L] + [c.z + rr.z for c, rr in L]
	z_lo, z_hi = min(zs), max(zs)

	def inside_other(p, skip, k=0.9):
		for j, (c, rr) in enumerate(L):
			if j == skip:
				continue
			d = p - c
			if (d.x / rr.x) ** 2 + (d.y / rr.y) ** 2 + (d.z / rr.z) ** 2 < k * k:
				return True
		return False

	placed = []
	for li, (c, rr) in enumerate(L):
		area = 4 * math.pi * ((rr.x * rr.y + rr.y * rr.z + rr.x * rr.z) / 3)
		want = int(area / (sphere_r * sphere_r * 2.2)) + 4
		got = 0
		for _ in range(want * 12):
			if got >= want:
				break
			v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1) + 0.1)).normalized()
			p = c + Vector((v.x * rr.x, v.y * rr.y, v.z * rr.z)) * r.uniform(0.84, 1.0)
			if inside_other(p, li) or any((p - q).length < sphere_r * 0.6 for q, _ in placed):
				continue
			placed.append((p, li))
			got += 1
	for p, li in placed:
		bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=sphere_r * r.uniform(0.75, 1.15), matrix=Matrix.Translation(p))
	bm.verts.index_update()

	def lobe_of(p):
		best, bj = 1e9, 0
		for j, (c, rr) in enumerate(L):
			d = p - c
			e = abs(math.sqrt((d.x / rr.x) ** 2 + (d.y / rr.y) ** 2 + (d.z / rr.z) ** 2) - 1.0)
			if e < best:
				best, bj = e, j
		return bj

	vlobe = [lobe_of(v.co) for v in bm.verts]
	for f in bm.faces:
		f.smooth = True
		for lp in f.loops:
			c, rr = L[vlobe[lp.vert.index]]
			d = lp.vert.co - c
			local = max(0.0, min(1.0, (d.z / rr.z + 1) / 2))
			glob = max(0.0, min(1.0, (lp.vert.co.z - z_lo) / max(z_hi - z_lo, 0.1)))
			t = local * 0.55 + glob * 0.45
			col = dark.lerp(mid, min(1.0, t / 0.55)) if t < 0.55 else mid.lerp(light, (t - 0.55) / 0.45)
			lp[col_layer] = (*col, 1.0)
	nlist = []
	for v in bm.verts:
		c, rr = L[vlobe[v.index]]
		d = v.co - c
		n = Vector((d.x / (rr.x * rr.x), d.y / (rr.y * rr.y), d.z / (rr.z * rr.z))).normalized()
		nlist.append(tuple((n * (1 - up_lean) + Vector((0, 0, up_lean))).normalized()))
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	me.normals_split_custom_set_from_vertices(nlist)
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	obj["Vcol"] = 1
	objs = [obj]
	if card_tint:
		b = fk.Builder()
		for li, (c, rr) in enumerate(L):
			for _ in range(cards_per):
				v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1) + 0.2)).normalized()
				if v.z < -0.45:
					continue
				p = c + Vector((v.x * rr.x, v.y * rr.y, v.z * rr.z)) * r.uniform(0.98, 1.14)
				if inside_other(p, li, 0.95):
					continue
				cell = fk.CELL_DARK if v.z < -0.1 else (fk.CELL_MID if v.z < 0.45 else r.choice((fk.CELL_LIGHT, fk.CELL_MID, fk.CELL_SPARSE)))
				fk.card(b, r, p, card_size * r.uniform(0.75, 1.3), cell, c, up_lean)
		co = b.finish(name + "Leaves")
		co["Tint"] = card_tint
		objs.append(co)
	return objs


def sparse_bush(name, centre, radius, clumps, per, seed, height=None):
	"""our leaf-card bush (tools/blender/foliage_kit.py), placed and sized here; tinted by its material"""
	r = random.Random(seed)
	b = fk.Builder()
	c0 = Vector(centre)
	high = height or radius * 2.1
	for i in range(clumps):
		a = i * math.tau / clumps + r.uniform(-0.4, 0.4)
		c = c0 + Vector((math.cos(a) * radius * 0.6, math.sin(a) * radius * 0.6, radius * r.uniform(0.7, 1.0)))
		fk.clump(b, r, c, radius * r.uniform(0.8, 1.05), per, c0.z, c0.z + high)
	return b.finish(name)


def wall_leaves(name, pts, size, seed, normal, spread=0.5, count_per=6, lean=0.6):
	"""ivy and vines: leaf cards hugging a wall along a hand-placed path"""
	r = random.Random(seed)
	b = fk.Builder()
	n = Vector(normal).normalized()
	for i in range(len(pts) - 1):
		a, bb = Vector(pts[i]), Vector(pts[i + 1])
		steps = max(1, int((bb - a).length / (size * 0.45)))
		for s in range(steps):
			p = a.lerp(bb, (s + r.random()) / steps)
			for _ in range(count_per // 2 + r.randint(0, count_per // 2)):
				q = p + Vector((r.gauss(0, spread), r.gauss(0, spread), r.gauss(0, spread) * 0.6))
				q = q + n * (0.15 + abs(r.gauss(0, 0.25)))
				fk.card(b, r, q, size * r.uniform(0.7, 1.2), r.choice((fk.CELL_MID, fk.CELL_LIGHT, fk.CELL_SPARSE, fk.CELL_DARK)), q - n * 3.0, lean)
	return b.finish(name)


def flowers(name, spots, colour, size=0.22, seed=0):
	"""little low spheres for blossoms, coloured by vertex"""
	r = random.Random(seed)
	bm = bmesh.new()
	col_layer = bm.loops.layers.float_color.new("Col")
	base = Vector(hex_lin(colour))
	for p in spots:
		rr = size * r.uniform(0.75, 1.25)
		bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rr, matrix=Matrix.Translation(Vector(p)))
	for f in bm.faces:
		f.smooth = True
		for lp in f.loops:
			k = 0.85 + 0.3 * r.random()
			lp[col_layer] = (base.x * k, base.y * k, base.z * k, 1.0)
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	return obj


def scatter_on(r, centre, radii, count, below=-0.2):
	out = []
	c = Vector(centre)
	for _ in range(count):
		v = Vector((r.gauss(0, 1), r.gauss(0, 1), abs(r.gauss(0, 1)) * 0.9 + below)).normalized()
		out.append(c + Vector((v.x * radii[0], v.y * radii[1], v.z * radii[2])) * r.uniform(0.92, 1.06))
	return out


FOLIAGE_TINTS = {}  # object name -> (hex tint for the leaf atlas)


def build_foliage():
	made = []
	# the big tree behind the left of the house, and its lower mass by the lane: deep blue-green with teal shade
	tree_cols = ("0e2a24", "22523c", "5a8e52")
	made += cloud("TreeLeft", [((-10.5, 2.0, 2.0), (5.0, 4.2, 4.4)), ((-9.0, 1.0, 5.6), (3.6, 3.2, 3.0)), ((-14.2, 2.6, -0.6), (3.5, 3.2, 3.5)), ((-8.0, -2.2, -2.6), (4.0, 3.5, 3.5)), ((-12.2, 0.2, -4.6), (3.5, 3.1, 3.1))], 1.9, 11, tree_cols, card_tint="24543e", cards_per=60, card_size=1.5)
	made += cloud("TreeLow", [((-5.6, -14.4, -11.7), (3.4, 3.0, 3.0)), ((-8.0, -12.4, -10.6), (3.0, 2.8, 3.1)), ((-3.2, -16.2, -12.6), (2.4, 2.2, 2.0))], 1.6, 12, tree_cols, card_tint="24543e", cards_per=55, card_size=1.3)
	bush_cols = ("0a201d", "163e36", "33604a")
	made += cloud("BushRight", [((41.0, 4.5, 2.6), (3.4, 3.2, 3.0)), ((39.6, 7.6, 3.6), (3.0, 2.8, 3.2)), ((42.4, 1.6, 1.6), (2.6, 2.4, 2.2)), ((40.2, 10.4, 2.8), (3.2, 3.0, 3.0))], 1.4, 21, bush_cols, card_tint="1f4c40", cards_per=50, card_size=1.2)
	made += cloud("BushTower", [((35.6, 9.6, 2.4), (3.0, 2.6, 2.6)), ((37.8, 12.2, 3.2), (3.0, 2.8, 3.0))], 1.3, 22, bush_cols, card_tint="1f4c40", cards_per=50, card_size=1.1)
	# sparse leaf-card bushes: blue-flowered by the annex, small ones by the pots and the curb
	sb = sparse_bush("SparseAnnex", (-1.0, -6.6, LANE), 2.2, 4, 26, 31)
	FOLIAGE_TINTS[sb.name] = "3b6e4c"
	made.append(sb)
	sb2 = sparse_bush("SparsePots", (33.0, 0.8, 0.0), 1.4, 3, 18, 32)
	FOLIAGE_TINTS[sb2.name] = "5a9a4e"
	made.append(sb2)
	sb3 = sparse_bush("SparseTerrace", (6.1, -33.8, LANE + 3.0), 0.9, 3, 14, 33)
	FOLIAGE_TINTS[sb3.name] = "4f8a4a"
	made.append(sb3)
	# ivy down the front-left corner, on the upper wall and the annex
	ivy = wall_leaves("IvyLeft", [(-4.4, -0.2, 13.0), (-3.4, -0.2, 11.4), (-1.6, -0.2, 10.2), (-2.8, -0.2, 8.0), (-3.6, -0.2, 6.2), (-2.0, -0.3, 4.8), (-0.6, -0.3, 6.6)], 1.0, 41, (0, -1, 0), spread=0.75, count_per=9)
	FOLIAGE_TINTS[ivy.name] = "7cae5c"
	made.append(ivy)
	ivy2 = wall_leaves("IvyAnnex", [(-0.6, -4.2, 3.6), (-0.4, -4.2, 1.0), (0.2, -4.2, -2.0), (-0.2, -4.2, -5.0), (0.3, -4.2, -8.0)], 0.8, 42, (0, -1, 0), spread=0.45, count_per=5)
	FOLIAGE_TINTS[ivy2.name] = "7cae5c"
	made.append(ivy2)
	# the flowering vine hanging off the eave by the tower and up the tower's foot
	vine = wall_leaves("VineEave", [(22.5, -2.4, 12.0), (24.0, -2.5, 10.8), (25.6, -2.5, 11.2), (27.2, -2.4, 9.8), (28.8, -2.2, 10.2), (30.2, -2.0, 8.6), (29.8, -1.6, 6.8), (30.8, -1.2, 4.8)], 1.0, 43, (0, -1, 0), spread=0.7, count_per=9)
	FOLIAGE_TINTS[vine.name] = "4f8a50"
	made.append(vine)
	vine2 = wall_leaves("VineTower", [(31.6, 7.2, 0.5), (31.0, 7.1, 3.0), (32.4, 7.5, 5.5), (31.5, 7.3, 8.0), (30.6, 7.4, 10.5)], 1.0, 44, (0.12, -1, 0), spread=0.7, count_per=8)
	FOLIAGE_TINTS[vine2.name] = "4f8a50"
	made.append(vine2)
	r = random.Random(44)
	made.append(flowers("FlowersVine", [Vector((x, y, z)) + Vector((r.gauss(0, 0.4), -0.5, r.gauss(0, 0.4))) for x, y, z in [(25.5, -2, 12), (26.5, -2, 11.2), (27.8, -2, 11.6), (28.6, -2, 12.0), (29.6, -2, 10.6), (30.0, -2, 11.5), (26.0, -2, 12.4), (29.0, -2, 9.4)] for _ in range(3)], "9cc6f0", size=0.24, seed=45))
	made.append(flowers("FlowersAnnex", scatter_on(r, (-1.0, -6.6, LANE + 2.4), (2.6, 2.6, 2.2), 30), "7fb0ee", size=0.26, seed=46))
	made.append(flowers("FlowersVine2", [Vector((31.4 + r.gauss(0, 0.8), 6.6, 1.0 + r.random() * 9.0)) for _ in range(14)], "dbe8f6", size=0.24, seed=55))
	made.append(flowers("FlowersIvy", [Vector(p) + Vector((r.gauss(0, 0.5), -0.6, r.gauss(0, 0.6))) for p in [(-3.6, -0.2, 10.5), (-2.8, -0.2, 8.0), (-3.4, -0.2, 6.0)] for _ in range(4)], "e8a2c0", size=0.2, seed=47))
	made.append(flowers("FlowersTerrace", scatter_on(r, (6.1, -33.8, LANE + 4.1), (1.2, 1.2, 0.9), 16), "e04a40", size=0.26, seed=48))
	made.append(flowers("FlowersPots", [Vector((34.0 + r.gauss(0, 0.35), -1.4 + r.gauss(0, 0.35), 1.2 + r.random() * 0.5)) for _ in range(10)], "f2c94a", size=0.22, seed=49))
	# plants: the navy pot's big round leaves and the window box's pot
	made.append(leaf_plant("PlantNavy", (29.4, -9.3, 3.5), 7, 1.5, 51))
	made.append(leaf_plant("PlantBox", (2.0, -0.9, 5.45), 6, 0.6, 52))
	made.append(leaf_plant("PlantDormer", (10.6, 0.9, 15.8), 6, 0.5, 56))
	made.append(leaf_plant("PlantTub", (30.0, -2.2, 2.0), 5, 0.7, 53))
	made.append(leaf_plant("PlantPot", (32.0, -8.0, 0.8), 5, 0.6, 54))
	for o in made:
		if o.name in FOLIAGE_TINTS:
			o["Tint"] = FOLIAGE_TINTS[o.name]
		elif "Tint" not in o.keys():
			o["Vcol"] = 1
	return made


def leaf_plant(name, base, count, size, seed):
	"""a few big round leaves on stems (the navy pot's lotus-like plant)"""
	r = random.Random(seed)
	bm = bmesh.new()
	col_layer = bm.loops.layers.float_color.new("Col")
	b = Vector(base)
	for i in range(count):
		a = i * math.tau / count + r.uniform(-0.3, 0.3)
		out = Vector((math.cos(a), math.sin(a), 0))
		tip = b + out * size * r.uniform(0.6, 1.0) + Vector((0, 0, size * r.uniform(0.6, 1.3)))
		seg = 12
		ring = []
		rad = size * r.uniform(0.45, 0.62)
		tilt = Matrix.Rotation(r.uniform(0.25, 0.6), 3, Vector((-out.y, out.x, 0)))
		centre = bm.verts.new(tip)
		for k in range(seg):
			t = k * math.tau / seg
			p = tilt @ Vector((math.cos(t) * rad, math.sin(t) * rad, 0.06 * math.cos(2 * t) * rad))
			ring.append(bm.verts.new(tip + p))
		for k in range(seg):
			f = bm.faces.new((centre, ring[k], ring[(k + 1) % seg]))
		stem = bmesh.ops.create_cone(bm, cap_ends=False, segments=4, radius1=0.05 * size + 0.03, radius2=0.03, depth=(tip - b).length, matrix=Matrix.Translation((b + tip) / 2) @ (tip - b).to_track_quat("Z", "Y").to_matrix().to_4x4())
	for f in bm.faces:
		f.smooth = True
		for lp in f.loops:
			lp[col_layer] = (*hex_lin("4f9a52"), 1.0)
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	return obj


# ---------------------------------------------------------------------------------------------------------------- meshes, packing, bake
KIND_COLOURS = {
	"slate": "a39b98",
	"slate_lip": "6d6670",
	"slate_under": "4a4550",
	"slate_cap": "958d8e",
	"ashlar": "dd9c85",
	"ashlar_reveal": "c98672",
	"ashlar_in": "e5b096",
	"ashlar_round": "df9f88",
	"voussoir": "a8604e",
	"crown": "d9a88c",
	"cream_ring": "efd9bd",
	"cream": "eedabf",
	"curb": "eed8be",
	"step": "e8d2b6",
	"step_pink": "c98270",
	"plaster": "efdcc0",
	"plaster_reveal": "d9c2a6",
	"plaster_pink": "d59078",
	"brick": "cf8670",
	"planks": "7a5040",
	"wood": "5e3a2c",
	"wood_lid": "8a8a78",
	"shutter": "6b4636",
	"shutter_green": "3f7a45",
	"green": "3f7a45",
	"green_light": "8cc49a",
	"corbel": "b88a78",
	"window_box": "e8b47e",
	"glass": "5a6f8a",
	"door": "5a3226",
	"interior": "2c1d1d",
	"grass": "a9c96a",
	"grass_bed": "a9c96a",
	"paving": "e6d3ba",
	"tiles": "d98a76",
	"retaining": "e3c3a8",
	"mat": "f0a596",
}


def srgb_to_lin(c):
	c = c / 255.0
	return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def flat_material(name, hexc):
	m = bpy.data.materials.get("K_" + name)
	if m:
		return m
	m = bpy.data.materials.new("K_" + name)
	m.use_nodes = True
	b = m.node_tree.nodes["Principled BSDF"]
	rgb = [srgb_to_lin(int(hexc[i : i + 2], 16)) for i in (0, 2, 4)]
	b.inputs["Base Color"].default_value = (*rgb, 1)
	b.inputs["Roughness"].default_value = 0.92
	b.inputs["Specular IOR Level"].default_value = 0.12
	m.use_backface_culling = True
	return m


def make_objects(g):
	coll = bpy.context.scene.collection
	kinds = sorted({isl["Kind"] for isl in g.islands})
	out = []
	for name, o in g.objs.items():
		me = bpy.data.meshes.new(name)
		me.from_pydata(o["v"], [], o["f"])
		me.update()
		a = me.attributes.new("island", "INT", "FACE")
		a.data.foreach_set("value", o["isl"])
		uv = me.uv_layers.new(name="Paint")
		flat = [c for face in o["uv"] for p in face for c in p]
		uv.data.foreach_set("uv", flat)
		for k in kinds:
			me.materials.append(flat_material(k, KIND_COLOURS.get(k, "aaaaaa")))
		idx = [kinds.index(g.islands[i]["Kind"]) for i in o["isl"]]
		me.polygons.foreach_set("material_index", idx)
		obj = bpy.data.objects.new(name, me)
		coll.objects.link(obj)
		bm = bmesh.new()
		bm.from_mesh(me)
		bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
		bm.to_mesh(me)
		bm.free()
		me.shade_smooth()
		me.set_sharp_from_angle(angle=math.radians(32))
		out.append(obj)
	return out


def cam_vectors():
	pitch, yaw = math.radians(CAM["Pitch"]), math.radians(CAM["Yaw"])
	fh = Vector((-math.sin(yaw), math.cos(yaw), 0))
	fwd = fh * math.cos(pitch) - UP * math.sin(pitch)
	return fwd, Vector(CAM["Target"]) - fwd * CAM["Dist"]


def shelf_pack(items, scale, size):
	"""rows of rectangles; items = (key, w_studs, h_studs, k). Returns {key: (px, py, w, h)} or None"""
	placed = {}
	x, y, row = PAD, PAD, 0
	for key, w, h, k in sorted(items, key=lambda it: -(it[2] * it[3])):
		pw, ph = max(2, math.ceil(w * scale * k)), max(2, math.ceil(h * scale * k))
		if pw + 2 * PAD > size:
			return None
		if x + pw + PAD > size:
			x, y, row = PAD, y + row + PAD, 0
		if y + ph + PAD > size:
			return None
		placed[key] = (x, y, pw, ph)
		x += pw + PAD
		row = max(row, ph)
	return placed


def pack_and_bake(g, objs):
	"""UV islands -> sheets, final UVs, and bake.npz + layout.json for the painter"""
	fwd, eye = cam_vectors()
	layout = {"Sheets": {}, "Islands": {}, "Size": SHEET, "Consts": {"EAVE": EAVE, "WALL_TOP": WALL_TOP, "LANE": LANE, "T_WALL": T_WALL, "RING_TOP": RING_TOP}}
	arrays = {"isl": [], "uv": [], "pos": [], "nor": []}
	for obj in objs:
		me = obj.data
		me.calc_loop_triangles()
		ids = np.zeros(len(me.polygons), dtype=np.int64)
		me.attributes["island"].data.foreach_get("value", ids)
		puv = np.zeros(len(me.loops) * 2, dtype=np.float64)
		me.uv_layers["Paint"].data.foreach_get("uv", puv)
		puv = puv.reshape(-1, 2)
		cn = np.zeros(len(me.loops) * 3, dtype=np.float32)
		me.corner_normals.foreach_get("vector", cn)
		cn = cn.reshape(-1, 3)
		co = np.zeros(len(me.vertices) * 3, dtype=np.float64)
		me.vertices.foreach_get("co", co)
		co = co.reshape(-1, 3)
		loop_vert = np.zeros(len(me.loops), dtype=np.int64)
		me.loops.foreach_get("vertex_index", loop_vert)
		poly_n = np.zeros(len(me.polygons) * 3, dtype=np.float64)
		me.polygons.foreach_get("normal", poly_n)
		poly_n = poly_n.reshape(-1, 3)
		poly_a = np.zeros(len(me.polygons), dtype=np.float64)
		me.polygons.foreach_get("area", poly_a)
		poly_c = np.zeros(len(me.polygons) * 3, dtype=np.float64)
		me.polygons.foreach_get("center", poly_c)
		poly_c = poly_c.reshape(-1, 3)
		loop_poly = np.zeros(len(me.loops), dtype=np.int64)
		for p in me.polygons:
			loop_poly[p.loop_start : p.loop_start + p.loop_total] = p.index
		isl_of_loop = ids[loop_poly]
		# bounds and facing per island
		items = []
		bounds = {}
		for i in np.unique(ids):
			lm = isl_of_loop == i
			uv = puv[lm]
			u0, v0 = uv.min(0)
			u1, v1 = uv.max(0)
			pm = ids == i
			area = poly_a[pm].sum()
			n = (poly_n[pm] * poly_a[pm, None]).sum(0)
			n = n / (np.linalg.norm(n) + 1e-9)
			c = (poly_c[pm] * poly_a[pm, None]).sum(0) / (area + 1e-9)
			view = c - np.array(eye)
			view /= np.linalg.norm(view)
			facing = -float(n @ view)
			isl = g.islands[int(i)]
			k = isl["Params"].get("K", 1.0) if "K" in isl["Params"] else 1.0
			if facing < 0.05:
				k *= 0.3
			margin = 0.05
			bounds[int(i)] = (u0 - margin, v0 - margin, u1 + margin, v1 + margin, k)
			items.append((int(i), u1 - u0 + 2 * margin, v1 - v0 + 2 * margin, k))
		lo, hi = 1.0, 200.0
		for _ in range(30):
			mid = (lo + hi) / 2
			if shelf_pack(items, mid, SHEET):
				lo = mid
			else:
				hi = mid
		scale = lo * 0.995
		placed = shelf_pack(items, scale, SHEET)
		layout["Sheets"][obj.name] = {"Scale": scale}
		for i, (px, py, pw, ph) in placed.items():
			u0, v0, u1, v1, k = bounds[i]
			isl = g.islands[i]
			layout["Islands"][str(i)] = {"Sheet": obj.name, "Kind": isl["Kind"], "Params": {p: v for p, v in isl["Params"].items()}, "U0": u0, "V0": v0, "U1": u1, "V1": v1, "PX": px, "PY": py, "PW": pw, "PH": ph, "S": scale * k}
		# final UVs
		fin = np.zeros_like(puv)
		for i in placed:
			px, py, pw, ph = placed[i]
			u0, v0, u1, v1, k = bounds[i]
			s = scale * k
			lm = isl_of_loop == i
			fin[lm, 0] = (px + (puv[lm, 0] - u0) * s) / SHEET
			fin[lm, 1] = 1 - (py + (v1 - puv[lm, 1]) * s) / SHEET
		uvl = me.uv_layers.new(name="UVMap")
		uvl.data.foreach_set("uv", fin.ravel())
		me.uv_layers.active = uvl
		uvl.active_render = True
		# triangles for the painter
		tri_loops = np.zeros(len(me.loop_triangles) * 3, dtype=np.int64)
		me.loop_triangles.foreach_get("loops", tri_loops)
		tri_loops = tri_loops.reshape(-1, 3)
		arrays["isl"].append(isl_of_loop[tri_loops[:, 0]])
		arrays["uv"].append(puv[tri_loops].astype(np.float32))
		arrays["pos"].append(co[loop_vert[tri_loops]].astype(np.float32))
		arrays["nor"].append(cn[tri_loops])
		print("[cottage] sheet", obj.name, "islands", len(placed), "px/stud", round(scale, 2), flush=True)
	np.savez_compressed(os.path.join(OUT, "bake.npz"), **{k: np.concatenate(v) for k, v in arrays.items()})
	json.dump(layout, open(os.path.join(OUT, "layout.json"), "w"))


def build():
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	g = Geo()
	build_scene(g)
	wobble(g)
	objs = make_objects(g)
	tris = sum(len(o.data.polygons) for o in objs)
	print("[cottage] objects", [o.name for o in objs], "faces", tris, "islands", len(g.islands), flush=True)
	pack_and_bake(g, objs)
	made = build_foliage()
	tri = sum(len(o.data.polygons) for o in made)
	print("[cottage] foliage objects", len(made), "faces", tri, flush=True)
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "cottage.blend"))


# ---------------------------------------------------------------------------------------------------------------- render
def camera(sc):
	pitch, yaw = math.radians(CAM["Pitch"]), math.radians(CAM["Yaw"])
	fh = Vector((-math.sin(yaw), math.cos(yaw), 0))
	fwd = fh * math.cos(pitch) - UP * math.sin(pitch)
	pos = Vector(CAM["Target"]) - fwd * CAM["Dist"]
	cam_data = bpy.data.cameras.new("Cam")
	cam_data.sensor_fit = "VERTICAL"
	cam_data.angle_y = math.radians(CAM["FOV"])
	cam_data.clip_start = 5
	cam_data.clip_end = 2000
	cam = bpy.data.objects.new("Cam", cam_data)
	sc.collection.objects.link(cam)
	cam.location = pos
	cam.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
	sc.camera = cam
	return cam


SUN_DIR = (0.608, 0.467, -0.643)  # from the camera's upper left, a little behind it: shadows fall right and back
SKY_TOP, SKY_LOW = "8ccafe", "c4e8fc"  # the reference's sky, measured


def hex_lin(h):
	return [srgb_to_lin(int(h[i : i + 2], 16)) for i in (0, 2, 4)]


def lights(sc, sun_energy=2.1, sky_strength=0.6):
	sun = bpy.data.lights.new("Sun", "SUN")
	sun.energy = sun_energy
	sun.angle = math.radians(2.5)
	sun.color = (1.0, 0.94, 0.86)
	o = bpy.data.objects.new("Sun", sun)
	sc.collection.objects.link(o)
	o.rotation_euler = Vector(SUN_DIR).normalized().to_track_quat("-Z", "Y").to_euler()
	world = bpy.data.worlds.new("Sky")
	sc.world = world
	world.use_nodes = True
	nt = world.node_tree
	for n in list(nt.nodes):
		nt.nodes.remove(n)
	out = nt.nodes.new("ShaderNodeOutputWorld")
	# what the camera sees: the reference's sky, a screen-space gradient; what lights the scene: an even sky
	coord = nt.nodes.new("ShaderNodeTexCoord")
	sep = nt.nodes.new("ShaderNodeSeparateXYZ")
	nt.links.new(coord.outputs["Window"], sep.inputs[0])
	ramp = nt.nodes.new("ShaderNodeValToRGB")
	ramp.color_ramp.elements[0].position = 0.0
	ramp.color_ramp.elements[0].color = (*hex_lin(SKY_LOW), 1)
	ramp.color_ramp.elements[1].position = 1.0
	ramp.color_ramp.elements[1].color = (*hex_lin(SKY_TOP), 1)
	nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
	seen = nt.nodes.new("ShaderNodeBackground")
	nt.links.new(ramp.outputs["Color"], seen.inputs["Color"])
	seen.inputs["Strength"].default_value = 1.0
	fill = nt.nodes.new("ShaderNodeBackground")
	fill.inputs["Color"].default_value = (*hex_lin("f4ece6"), 1)
	fill.inputs["Strength"].default_value = sky_strength
	path = nt.nodes.new("ShaderNodeLightPath")
	mix = nt.nodes.new("ShaderNodeMixShader")
	nt.links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
	nt.links.new(fill.outputs["Background"], mix.inputs[1])
	nt.links.new(seen.outputs["Background"], mix.inputs[2])
	nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


def leaf_material(tint):
	m = bpy.data.materials.get("Leaf_" + tint)
	if m:
		return m
	m = bpy.data.materials.new("Leaf_" + tint)
	m.use_nodes = True
	nt = m.node_tree
	b = nt.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.85
	b.inputs["Specular IOR Level"].default_value = 0.05
	im = nt.nodes.new("ShaderNodeTexImage")
	im.image = bpy.data.images.load(os.path.join(ROOT, "art", "kit", "foliage", "leaves_white.png"))
	uv = nt.nodes.new("ShaderNodeUVMap")
	uv.uv_map = "UV"
	nt.links.new(uv.outputs["UV"], im.inputs["Vector"])
	mul = nt.nodes.new("ShaderNodeMix")
	mul.data_type = "RGBA"
	mul.blend_type = "MULTIPLY"
	mul.inputs["Factor"].default_value = 1.0
	nt.links.new(im.outputs["Color"], mul.inputs["A"])
	mul.inputs["B"].default_value = (*hex_lin(tint), 1)
	nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
	nt.links.new(im.outputs["Alpha"], b.inputs["Alpha"])
	m.use_backface_culling = True
	try:
		m.surface_render_method = "DITHERED"
	except AttributeError:
		pass
	return m


def vcol_material():
	m = bpy.data.materials.get("VertexColour")
	if m:
		return m
	m = bpy.data.materials.new("VertexColour")
	m.use_nodes = True
	nt = m.node_tree
	b = nt.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.9
	b.inputs["Specular IOR Level"].default_value = 0.08
	at = nt.nodes.new("ShaderNodeAttribute")
	at.attribute_name = "Col"
	nt.links.new(at.outputs["Color"], b.inputs["Base Color"])
	m.use_backface_culling = True
	return m


def sheet_material(name):
	path = os.path.join(OUT, "sheets", f"{name}.png")
	m = bpy.data.materials.new("Sheet_" + name)
	m.use_nodes = True
	nt = m.node_tree
	b = nt.nodes["Principled BSDF"]
	b.inputs["Roughness"].default_value = 0.9
	b.inputs["Specular IOR Level"].default_value = 0.1
	im = nt.nodes.new("ShaderNodeTexImage")
	im.image = bpy.data.images.load(path)
	im.interpolation = "Linear"
	uv = nt.nodes.new("ShaderNodeUVMap")
	uv.uv_map = "UVMap"
	nt.links.new(uv.outputs["UV"], im.inputs["Vector"])
	nt.links.new(im.outputs["Color"], b.inputs["Base Color"])
	m.use_backface_culling = True
	return m


def render():
	tag = ARGS[1] if len(ARGS) > 1 else "clay"
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cottage.blend"))
	sc = bpy.context.scene
	if "--clay" not in ARGS:
		for obj in list(sc.collection.objects):
			if obj.type == "MESH" and os.path.exists(os.path.join(OUT, "sheets", f"{obj.name}.png")):
				obj.data.materials.clear()
				obj.data.materials.append(sheet_material(obj.name))
	for obj in list(sc.collection.objects):
		if obj.type != "MESH":
			continue
		if "Tint" in obj.keys():
			obj.data.materials.clear()
			obj.data.materials.append(leaf_material(obj["Tint"]))
			obj.visible_shadow = False
		elif "Vcol" in obj.keys():
			obj.data.materials.clear()
			obj.data.materials.append(vcol_material())
	sc.render.engine = "BLENDER_EEVEE"
	sc.view_settings.view_transform = "Standard"
	sc.render.resolution_x, sc.render.resolution_y = RES
	sc.render.resolution_percentage = 50 if "--small" in ARGS else 100
	sc.render.film_transparent = False
	camera(sc)
	lights(sc)
	try:
		sc.eevee.taa_render_samples = 32
		sc.eevee.use_shadows = True
	except AttributeError:
		pass
	os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
	sc.render.filepath = os.path.join(OUT, "renders", f"{tag}.png")
	bpy.ops.render.render(write_still=True)
	print("[cottage] rendered", sc.render.filepath, flush=True)


def bake_ao():
	"""ambient occlusion per sheet from the whole scene (contact shadows Roblox can't draw), into sheets/ao/<sheet>.png"""
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cottage.blend"))
	sc = bpy.context.scene
	sc.render.engine = "CYCLES"
	try:
		prefs = bpy.context.preferences.addons["cycles"].preferences
		for kind in ("OPTIX", "CUDA"):
			try:
				prefs.compute_device_type = kind
				prefs.get_devices()
				for d in prefs.devices:
					d.use = True
				sc.cycles.device = "GPU"
				break
			except Exception:
				continue
	except Exception:
		pass
	sc.cycles.samples = int(ARGS[1]) if len(ARGS) > 1 else 96
	if sc.world is None:
		sc.world = bpy.data.worlds.new("W")
	sc.world.light_settings.distance = 3.2
	os.makedirs(os.path.join(OUT, "sheets", "ao"), exist_ok=True)
	for o in sc.collection.objects:
		if o.type == "MESH" and ("Tint" in o.keys() or "Vcol" in o.keys()):
			o.hide_render = True  # foliage casts its own shadows in Roblox; baked under a floating canopy it reads as a dark disc
	sheets = [o for o in sc.collection.objects if o.type == "MESH" and "UVMap" in o.data.uv_layers]
	for obj in sheets:
		img = bpy.data.images.new("AO_" + obj.name, SHEET, SHEET, alpha=False, float_buffer=False)
		mat = bpy.data.materials.new("Bake_" + obj.name)
		mat.use_nodes = True
		node = mat.node_tree.nodes.new("ShaderNodeTexImage")
		node.image = img
		mat.node_tree.nodes.active = node
		obj.data.materials.clear()
		obj.data.materials.append(mat)
		obj.data.uv_layers.active = obj.data.uv_layers["UVMap"]
		for o in sc.collection.objects:
			o.select_set(False)
		obj.select_set(True)
		bpy.context.view_layer.objects.active = obj
		bpy.ops.object.bake(type="AO", margin=6, use_clear=True)
		img.filepath_raw = os.path.join(OUT, "sheets", "ao", f"{obj.name}.png")
		img.file_format = "PNG"
		img.save()
		print("[cottage] baked AO", obj.name, flush=True)


def export():
	"""PinkCottage.glb (every object its own MeshPart, final UVs only, vertex colours kept) + export.json (bounds, triangles, kinds)"""
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cottage.blend"))
	info = {}
	for obj in bpy.data.objects:
		if obj.type != "MESH":
			continue
		me = obj.data
		if "Paint" in me.uv_layers:
			me.uv_layers.remove(me.uv_layers["Paint"])
		if "Col" in me.color_attributes:
			# Roblox's glb importer reads vertex colours as sRGB: store the sRGB-encoded values so they come out as painted
			col = me.color_attributes["Col"]
			vals = np.zeros(len(col.data) * 4, dtype=np.float32)
			col.data.foreach_get("color", vals)
			v = vals.reshape(-1, 4)
			rgb = np.clip(v[:, :3], 0, 1)
			v[:, :3] = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
			col.data.foreach_set("color", v.ravel())
			me.color_attributes.active_color = col
		me.calc_loop_triangles()
		c = [Vector(v) for v in obj.bound_box]
		kind = "sheet" if os.path.exists(os.path.join(OUT, "sheets", f"{obj.name}.png")) else ("leaves" if "Tint" in obj.keys() else "vcol")
		info[obj.name] = {
			"Bounds": [min(v.x for v in c), min(v.y for v in c), min(v.z for v in c), max(v.x for v in c), max(v.y for v in c), max(v.z for v in c)],
			"Tris": len(me.loop_triangles),
			"Kind": kind,
			"Tint": obj.get("Tint"),
		}
	for o in bpy.data.objects:
		o.select_set(o.type == "MESH")
	path = os.path.join(OUT, "PinkCottage.glb")
	bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True, export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True)
	json.dump(info, open(os.path.join(OUT, "export.json"), "w"), indent=1)
	big = {k: v["Tris"] for k, v in info.items() if v["Tris"] > 19000}
	print("[cottage] exported", len(info), "meshes, triangles", sum(v["Tris"] for v in info.values()), "over 19k:", big, flush=True)


if __name__ == "__main__":
	os.makedirs(OUT, exist_ok=True)
	{"build": build, "render": render, "bake_ao": bake_ao, "export": export}[ARGS[0]]()
