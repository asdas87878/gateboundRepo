"""Study: a crooked timber-framed cottage with pink tiled roofs, after a stylized render the user shared (private; the reference and every
output stay in research/crooked_cottage, gitignored, never in the game). Studs, z up; the door wall faces -y, the right side +x.

Built from the reference's own view. A camera fitted to it back-projects measured pixels onto chosen planes (px_y, px_x), so each part
lands where the reference has it; the depth of each plane is the one free choice. The curved, hand-built look comes from the parts
themselves: every roof face is a bell-cast surface between a drooping eave and a swooping ridge, tiles are chunky slabs laid row by row
on it with small turns, barge boards run past the apex and curl up, timbers bow and lean.

tools/blender/pink_cottage.py is the library (Geo, islands, packing, bake, render helpers), pointed at this study's folder.

  blender --background --python tools/blender/crooked_cottage.py -- build
  blender --background --python tools/blender/crooked_cottage.py -- render <tag> [--clay] [--small]
  blender --background --python tools/blender/crooked_cottage.py -- bake_ao 64
  blender --background --python tools/blender/crooked_cottage.py -- export
"""

import json
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pink_cottage as pc  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "research", "crooked_cottage")
ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["build"]
UP = Vector((0, 0, 1))
X, Y = Vector((1, 0, 0)), Vector((0, 1, 0))

# ---------------------------------------------------------------------------------------------------------------- the reference's camera
# fitted to the reference (1200 x 675): f 1430 px, horizon at y 490 (looking up 6.1 degrees), the door wall at 50 degrees to the view;
# the eye 5 studs up, placed so the right block's front-right corner at the ground lands on pixel (781, 606). The door is 7.3 tall.
W_REF, H_REF = 1200, 675
F_PX = 1430.0
PITCH = math.atan((490.0 - H_REF / 2) / F_PX)
_V = Vector((-math.cos(math.radians(50.0)), math.sin(math.radians(50.0)), 0.0))
FWD = Vector((_V.x * math.cos(PITCH), _V.y * math.cos(PITCH), math.sin(PITCH)))
RIGHTV = Vector((_V.y, -_V.x, 0.0))
UPV = RIGHTV.cross(FWD)
EYE = Vector((34.40308, -53.20614, 5.0))
DIST = 63.6
FOCUS = 62.0  # the lens blur's focus distance (other houses built on this module set their own)
pc.OUT = OUT
pc.RES = (W_REF, H_REF)
pc.CAM = {"Pitch": -math.degrees(PITCH), "Yaw": 40.0, "FOV": math.degrees(2 * math.atan(H_REF / 2 / F_PX)), "Dist": DIST, "Target": tuple(EYE + FWD * DIST)}


def ray(px, py):
	return (FWD + RIGHTV * ((px - W_REF / 2) / F_PX) - UPV * ((py - H_REF / 2) / F_PX)).normalized()


def px_plane(px, py, n, d0):
	r = ray(px, py)
	n = Vector(n)
	return EYE + r * ((d0 - n.dot(EYE)) / n.dot(r))


def px_y(px, py, y):
	"""the point on the plane y = const that the reference shows at pixel (px, py)"""
	return px_plane(px, py, Y, y)


def px_x(px, py, x):
	return px_plane(px, py, X, x)


def proj(P):
	d = Vector(P) - EYE
	z = d.dot(FWD)
	return (W_REF / 2 + F_PX * d.dot(RIGHTV) / z, H_REF / 2 - F_PX * d.dot(UPV) / z)


def lerp(a, b, t):
	return a + (b - a) * t


# ---------------------------------------------------------------------------------------------------------------- curves
def bezier(p0, p1, p2, steps=10):
	p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
	return [p0 * ((1 - s) ** 2) + p1 * (2 * (1 - s) * s) + p2 * (s * s) for s in (i / steps for i in range(steps + 1))]


def arc_pts(c, r, a0, a1, steps, au, av):
	"""points on a circle of radius r about c in the plane (au, av), from angle a0 to a1 (degrees)"""
	c, au, av = Vector(c), Vector(au), Vector(av)
	out = []
	for i in range(steps + 1):
		a = math.radians(a0 + (a1 - a0) * i / steps)
		out.append(c + au * (r * math.cos(a)) + av * (r * math.sin(a)))
	return out


def polyline_at(pts, run, s):
	s = min(max(s, 0.0), run[-1])
	i = max(0, min(len(pts) - 2, int(np.searchsorted(run, s)) - 1))
	seg = run[i + 1] - run[i]
	t = (s - run[i]) / seg if seg > 1e-9 else 0.0
	return pts[i].lerp(pts[i + 1], t)


def resample(pts, n):
	pts = [Vector(p) for p in pts]
	run = [0.0]
	for i in range(1, len(pts)):
		run.append(run[-1] + (pts[i] - pts[i - 1]).length)
	return [polyline_at(pts, run, run[-1] * k / (n - 1)) for k in range(n)]


def smooth_curve(pts, n=24):
	"""a Catmull-Rom curve through the points, resampled evenly"""
	P = [Vector(p) for p in pts]
	if len(P) == 2:
		return resample(P, n)
	P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
	out = []
	for i in range(1, len(P) - 2):
		p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
		for k in range(8):
			t = k / 8
			out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
	out.append(P[-2])
	return resample(out, n)


# ---------------------------------------------------------------------------------------------------------------- timbers
def sweep(g, obj, sheet, kind, pts, w, t, up, caps=True, K=1.0, **params):
	"""a w x t timber swept along pts. `up` (one vector, or a list with one per point) is the direction of the thickness t; w runs
	across. Four long faces (u = run along the timber, v = across it) and two end caps (kind + '_end')."""
	pts = [Vector(p) for p in pts]
	n = len(pts)
	if isinstance(up, list):
		ups = [Vector(u) for u in up]
	else:
		ups = [Vector(up)] * n
	run = [0.0]
	for i in range(1, n):
		run.append(run[-1] + (pts[i] - pts[i - 1]).length)
	rings = []
	for i in range(n):
		T = (pts[min(n - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
		U = ups[i] - T * ups[i].dot(T)
		U = U.normalized() if U.length > 1e-6 else T.orthogonal().normalized()
		S = T.cross(U).normalized()
		c = pts[i]
		rings.append((c, T, U, S, [c + S * (w / 2) + U * (t / 2), c - S * (w / 2) + U * (t / 2), c - S * (w / 2) - U * (t / 2), c + S * (w / 2) - U * (t / 2)]))
	names = ("top", "side_b", "bottom", "side_a")
	spans = (w, t, w, t)
	for k in range(4):
		isl = g.island(sheet, kind, None, Face=names[k], Width=spans[k], Length=run[-1], K=K, **params)
		for i in range(n - 1):
			A, B = rings[i][4][k], rings[i][4][(k + 1) % 4]
			C, D = rings[i + 1][4][(k + 1) % 4], rings[i + 1][4][k]
			quad = [A, D, C, B]
			uv = [(run[i], 0.0), (run[i + 1], 0.0), (run[i + 1], spans[k]), (run[i], spans[k])]
			centre = (A + B + C + D) / 4
			mid = (rings[i][0] + rings[i + 1][0]) / 2
			if (D - A).cross(B - A).dot(centre - mid) < 0:
				quad, uv = quad[::-1], uv[::-1]
			g.face(obj, quad, isl, uv)
	if caps:
		for i, sign in ((0, -1.0), (n - 1, 1.0)):
			c, T, U, S, ring = rings[i]
			isl = g.island(sheet, kind + "_end", None, Face="end", K=K, W=w, T=t, **params)
			q = list(ring)
			if (q[1] - q[0]).cross(q[3] - q[0]).dot(T * sign) < 0:
				q = q[::-1]
			g.face(obj, q, isl, [((p - c).dot(S) + w / 2, (p - c).dot(U) + t / 2) for p in q])
	return run[-1]


def timber(g, a, b, w, t, up, bow=0.0, bow_dir=None, segs=4, obj="Timber", sheet="Timber", kind="timber", **params):
	"""a straight timber from a to b, or bowed sideways by `bow` studs (hand-cut, slightly bent)"""
	a, b = Vector(a), Vector(b)
	if abs(bow) < 1e-6:
		pts = [a, b]
	else:
		bd = Vector(bow_dir).normalized()
		pts = [a.lerp(b, s / segs) + bd * (bow * math.sin(math.pi * s / segs)) for s in range(segs + 1)]
	return sweep(g, obj, sheet, kind, pts, w, t, up, **params)


def obox(g, obj, sheet, kind, centre, ax, ay, size, **params):
	pc.obox(g, obj, sheet, kind, centre, ax, ay, size, **params)


# ---------------------------------------------------------------------------------------------------------------- roof faces and tiles
class Surface:
	"""a roof face between an eave polyline and a ridge polyline (matched point for point, a = 0..1 along them). In plan it runs
	straight from eave to ridge; its height follows prof(b) = c*b + (1-c)*b**k, a bell-cast: shallow at the eave, steep near the ridge."""

	def __init__(self, eave, ridge, c=0.55, k=2.0, n=40, name="", kick=None):
		self.E = resample(eave, n)
		self.R = resample(ridge, n)
		self.c, self.k, self.n, self.name = c, k, n, name
		self.kick = kick  # (amount at a = 0, amount at a = 1, reach along a, reach up b, lift share): the eave's corners kick out
		self.t0 = (self.E[0] - self.E[1]).normalized()
		self.t1 = (self.E[-1] - self.E[-2]).normalized()
		m = 0.5 + (max(kick[0], kick[1]) if kick else 0.0)
		xs = [p.x for p in self.E + self.R]
		ys = [p.y for p in self.E + self.R]
		self.bbox = (min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m)

	def prof(self, b):
		return self.c * b + (1 - self.c) * b**self.k

	def at(self, a, b):
		f = min(max(a, 0.0), 1.0) * (self.n - 1)
		i = min(int(f), self.n - 2)
		t = f - i
		E = self.E[i].lerp(self.E[i + 1], t)
		R = self.R[i].lerp(self.R[i + 1], t)
		p = E.lerp(R, b)
		p.z = E.z + (R.z - E.z) * self.prof(min(max(b, 0.0), 1.0)) + (R.z - E.z) * self.c * min(b, 0.0)
		if self.kick:
			k0, k1, ra, rb, lift = self.kick
			wb = max(0.0, 1.0 - max(b, 0.0) / rb) ** 2
			if k0 > 0 and a < ra:
				w = (1 - max(a, 0.0) / ra) ** 2 * wb
				p = p + self.t0 * (k0 * w) + UP * (k0 * lift * w)
			if k1 > 0 and a > 1 - ra:
				w = (1 - (1 - min(a, 1.0)) / ra) ** 2 * wb
				p = p + self.t1 * (k1 * w) + UP * (k1 * lift * w)
		return p

	def frame(self, a, b):
		h = 1e-3
		a0, a1 = max(a - h, 0.0), min(a + h, 1.0)
		b0, b1 = max(b - h, 0.0), min(b + h, 1.0)
		da = (self.at(a1, b) - self.at(a0, b)) / (a1 - a0)
		db = (self.at(a, b1) - self.at(a, b0)) / (b1 - b0)
		N = da.cross(db).normalized()
		if N.z < 0:
			N = -N
		return da, db, N

	def ab_of(self, x, y):
		"""(a, b) whose plan position is (x, y), by Newton; None when outside the face"""
		if not (self.bbox[0] <= x <= self.bbox[1] and self.bbox[2] <= y <= self.bbox[3]):
			return None
		a, b = 0.5, 0.5
		for _ in range(25):
			p = self.at(a, b)
			da, db, _n = self.frame(a, b)
			det = da.x * db.y - da.y * db.x
			if abs(det) < 1e-9:
				return None
			rx, ry = x - p.x, y - p.y
			sa = (rx * db.y - ry * db.x) / det
			sb = (da.x * ry - da.y * rx) / det
			a, b = min(max(a + sa, -0.3), 1.3), min(max(b + sb, -0.3), 1.3)
			if abs(sa) + abs(sb) < 1e-6:
				break
		if -1e-3 <= a <= 1 + 1e-3 and -1e-3 <= b <= 1 + 1e-3:
			return a, b
		return None

	def height(self, x, y):
		ab = self.ab_of(x, y)
		return None if ab is None else self.at(*ab).z


SKIPS = {}
ROOFS = {}  # every roof face by name: tiles found under another face are not laid
GROUP = {}  # faces of one roof don't clip each other


def under_other(P, own, margin=0.05):
	for name, s in ROOFS.items():
		if GROUP.get(name, name) == GROUP.get(own, own):
			continue
		h = s.height(P.x, P.y)
		if h is not None and h - 4.0 < P.z < h - margin:
			SKIPS[own + "<" + name] = SKIPS.get(own + "<" + name, 0) + 1
			return True
	return False


def register(group, *surfs):
	for s in surfs:
		ROOFS[s.name] = s
		GROUP[s.name] = group


def lay_tiles(g, surf, obj, tile_w=1.85, row=2.05, tile_len=2.95, thick=0.34, rest=0.16, seed=0, turn=2.2, shift=0.08, skip=None, lip=True, inside=False):
	"""chunky tiles with rounded lower corners, laid in rows from the eave up a Surface. Each tile lies on the one below (its foot
	lifted by `rest`), turned a few degrees and nudged along its row: the reference's hand-laid look. Every tile is its own island
	(top: u across, v up the slope, studs) with a lip island for its edge. inside: every row ends flush with the face's edges, with a
	narrower tile where the bond leaves a gap (a real verge), so no tile overhangs a verge with nothing under it."""
	r = random.Random(seed)
	na = 24
	A = [i / (na - 1) for i in range(na)]
	bs = np.linspace(0, 1, 60)
	tabs = []
	for a in A:
		pts = [surf.at(a, b) for b in bs]
		s = [0.0]
		for i in range(1, len(pts)):
			s.append(s[-1] + (pts[i] - pts[i - 1]).length)
		tabs.append(np.array(s))

	def b_at(a, s):
		f = min(max(a, 0.0), 1.0) * (na - 1)
		i = min(int(f), na - 2)
		t = f - i
		return float(np.interp(s, tabs[i], bs)) * (1 - t) + float(np.interp(s, tabs[i + 1], bs)) * t

	def len_at(a):
		f = min(max(a, 0.0), 1.0) * (na - 1)
		i = min(int(f), na - 2)
		t = f - i
		return tabs[i][-1] * (1 - t) + tabs[i + 1][-1] * t

	rows = int(max(t[-1] for t in tabs) / row) + 1
	count = 0
	for k in range(rows):
		s0 = k * row
		samples = []
		for i in range(81):
			a = i / 80
			samples.append((a, surf.at(a, b_at(a, s0))) if s0 < len_at(a) - 0.3 else None)
		run = [0.0]
		for i in range(1, len(samples)):
			ok = samples[i] is not None and samples[i - 1] is not None
			run.append(run[-1] + ((samples[i][1] - samples[i - 1][1]).length if ok else 0.0))
		total = run[-1]
		if total < 0.3:
			continue
		ntile = max(1, round(total / tile_w))
		wk = total / ntile
		off = (0.5 if k % 2 else 0.0) * wk + r.uniform(-0.1, 0.1) * wk
		for ci in range(-1, ntile + 1):
			sc = off + (ci + 0.5) * wk + r.uniform(-shift, shift)
			wfix = None
			if inside:
				half = wk * 0.515
				lo_, hi_ = max(sc - half, 0.0), min(sc + half, total)
				if hi_ - lo_ < 0.3 * wk:
					continue
				if hi_ - lo_ < 2 * half - 1e-6:
					sc, wfix = (lo_ + hi_) / 2, hi_ - lo_
			elif sc < 0.15 * wk or sc > total - 0.15 * wk:
				continue
			j = int(np.searchsorted(run, sc))
			j = min(max(j, 1), len(run) - 1)
			if samples[j] is None or samples[j - 1] is None:
				continue
			t = (sc - run[j - 1]) / max(run[j] - run[j - 1], 1e-9)
			ac = samples[j - 1][0] + (samples[j][0] - samples[j - 1][0]) * min(max(t, 0.0), 1.0)
			bc = b_at(ac, s0)
			if bc > 0.985:
				continue
			da, db, N = surf.frame(ac, bc)
			Ta, Tb = da.length, db.length
			centre = surf.at(ac, bc)
			if skip and skip(centre):
				SKIPS[surf.name + ":box"] = SKIPS.get(surf.name + ":box", 0) + 1
				continue
			if under_other(surf.at(ac, min(bc + 0.4 * tile_len / Tb, 1.0)) + N * 0.25, surf.name):
				SKIPS[surf.name + ":under"] = SKIPS.get(surf.name + ":under", 0) + 1
				continue
			w = wk * r.uniform(1.0, 1.06)
			if wfix is not None:
				w = wfix
			L = tile_len * r.uniform(0.96, 1.06)
			ang = math.radians(r.uniform(-turn, turn))
			lift = thick + r.uniform(-0.02, 0.03)
			rc = min(0.2 * w, 0.34)
			outline = [(-w / 2, L)]
			for q in range(5):
				th = math.pi + (math.pi / 2) * q / 4
				outline.append((-w / 2 + rc + rc * math.cos(th), rc + rc * math.sin(th)))
			for q in range(5):
				th = 1.5 * math.pi + (math.pi / 2) * q / 4
				outline.append((w / 2 - rc + rc * math.cos(th), rc + rc * math.sin(th)))
			outline.append((w / 2, L))
			ca, sa = math.cos(ang), math.sin(ang)

			def place(s, tt, extra):
				rs, rt = s * ca - tt * sa, s * sa + tt * ca
				a2 = ac + rs / Ta
				b2 = bc + rt / Tb
				aa, bb = min(max(a2, 0.0), 1.0), min(max(b2, -0.3), 1.0)
				p = surf.at(aa, bb)
				if a2 != aa:
					p = p + surf.frame(aa, max(bb, 0.0))[0] * (a2 - aa)
				_x, _y, Nn = surf.frame(aa, min(max(bb, 0.0), 1.0))
				return p + Nn * extra

			top = [place(s, tt, lift + rest * (1 - tt / L)) for s, tt in outline]
			isl = g.island(obj, "tile", None, Face="top", Roof=surf.name, Row=k, Col=ci, W=w, L=L, Seed=r.randrange(10**6))
			uv_of = [(s + w / 2, tt) for s, tt in outline]
			for tri in tessellate_polygon([[(s, tt, 0.0) for s, tt in outline]]):
				a_, b_, c_ = tri
				P3 = [top[a_], top[b_], top[c_]]
				uvs = [uv_of[a_], uv_of[b_], uv_of[c_]]
				if (P3[1] - P3[0]).cross(P3[2] - P3[0]).dot(N) < 0:
					P3, uvs = [P3[0], P3[2], P3[1]], [uvs[0], uvs[2], uvs[1]]
				g.face(obj, P3, isl, uvs)
			if lip:
				li = g.island(obj, "tile_lip", None, Face="lip", Roof=surf.name, Row=k, Col=ci, Thick=thick)
				inner = place(0.0, 0.5 * L, lift)
				runl = 0.0
				for i in range(len(outline) - 1):
					p0, p1 = top[i], top[i + 1]
					q0, q1 = p0 - N * thick, p1 - N * thick
					L01 = (p1 - p0).length
					quad = [p0, p1, q1, q0]
					uv = [(runl, thick), (runl + L01, thick), (runl + L01, 0.0), (runl, 0.0)]
					if (p1 - p0).cross(q0 - p0).dot(inner - (p0 + p1) / 2) > 0:
						quad, uv = quad[::-1], uv[::-1]
					g.face(obj, quad, li, uv)
					runl += L01
			count += 1
	return count


def roof_skin(g, surf, obj, na=16, nb=10, soffit=True, drop=0.04):
	"""the face under the tiles (dark, closes the gaps between them) and below it the soffit, seen from the ground under the eaves"""
	grid = [[surf.at(i / na, j / nb) for j in range(nb + 1)] for i in range(na + 1)]
	isl = g.island(obj, "roof_under", None, Face="skin", Roof=surf.name)
	low = g.island(obj, "soffit", None, Face="soffit", Roof=surf.name) if soffit else None
	for i in range(na):
		for j in range(nb):
			q = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
			_a, _b, N = surf.frame((i + 0.5) / na, (j + 0.5) / nb)
			uv = [(q[0] - grid[0][0]).length * 0 + i * 1.3, j * 1.3], [(i + 1) * 1.3, j * 1.3], [(i + 1) * 1.3, (j + 1) * 1.3], [i * 1.3, (j + 1) * 1.3]
			uv = [tuple(u) for u in uv]
			upq = [p + N * drop for p in q]
			if (upq[1] - upq[0]).cross(upq[3] - upq[0]).dot(N) < 0:
				g.face(obj, upq[::-1], isl, uv[::-1])
			else:
				g.face(obj, upq, isl, uv)
			if low is not None:
				dn = [p - N * 0.22 for p in q]
				if (dn[1] - dn[0]).cross(dn[3] - dn[0]).dot(-N) < 0:
					g.face(obj, dn[::-1], low, uv[::-1])
				else:
					g.face(obj, dn, low, uv)


# ---------------------------------------------------------------------------------------------------------------- chunky timbers
PROUD = 0.45  # timbers stand this far out of the plaster panels
FRAME_PROUD = 0.2  # window and door surrounds stand less far out than the frame around them


def beam(g, pts, w, t, up, chamfer=None, taper=(1.0, 1.0), obj="Timber", kind="timber", caps=True, widths=None, **params):
	"""a chunky hand-cut timber: a w x t section with chamfered corners swept along pts. The chamfers catch the light as the
	reference's rounded edges do (the painter lightens them). taper scales the section from the first point to the last;
	`up` is the direction of the thickness t (one vector or one per point)."""
	pts = [Vector(p) for p in pts]
	n = len(pts)
	ups = [Vector(u) for u in up] if isinstance(up, list) else [Vector(up)] * n
	c0 = chamfer if chamfer is not None else min(w, t) * 0.2
	run = [0.0]
	for i in range(1, n):
		run.append(run[-1] + (pts[i] - pts[i - 1]).length)
	L = max(run[-1], 1e-6)
	rings = []
	for i in range(n):
		T = (pts[min(n - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
		U = ups[i] - T * ups[i].dot(T)
		U = U.normalized() if U.length > 1e-6 else T.orthogonal().normalized()
		S = T.cross(U).normalized()
		k = taper[0] + (taper[1] - taper[0]) * run[i] / L
		kw = k * (widths[i] if widths else 1.0)
		hw, ht, c = w * kw / 2, t * k / 2, c0 * k
		prof = [(hw - c, ht), (-hw + c, ht), (-hw, ht - c), (-hw, -ht + c), (-hw + c, -ht), (hw - c, -ht), (hw, -ht + c), (hw, ht - c)]
		rings.append((pts[i], T, [pts[i] + S * a + U * b for a, b in prof]))
	names = ("top", "chamfer", "side_b", "chamfer", "bottom", "chamfer", "side_a", "chamfer")
	for k in range(8):
		span = (rings[0][2][(k + 1) % 8] - rings[0][2][k]).length
		isl = g.island(obj, kind, None, Face=names[k], Width=span, Length=L, **params)
		for i in range(n - 1):
			A, B = rings[i][2][k], rings[i][2][(k + 1) % 8]
			C, D = rings[i + 1][2][(k + 1) % 8], rings[i + 1][2][k]
			quad = [A, D, C, B]
			uv = [(run[i], 0.0), (run[i + 1], 0.0), (run[i + 1], span), (run[i], span)]
			if (D - A).cross(B - A).dot((A + B + C + D) / 4 - (rings[i][0] + rings[i + 1][0]) / 2) < 0:
				quad, uv = quad[::-1], uv[::-1]
			g.face(obj, quad, isl, uv)
	if caps:
		for i, sign in ((0, -1.0), (n - 1, 1.0)):
			c, T, ring = rings[i]
			isl = g.island(obj, kind + "_end", None, Face="end", W=w, T=t, **params)
			q = list(ring)
			if (q[1] - q[0]).cross(q[2] - q[0]).dot(T * sign) < 0:
				q = q[::-1]
			sx = (ring[0] - ring[1]).normalized()
			uy = T.cross(sx).normalized()
			g.face(obj, q, isl, [((p - c).dot(sx) + w / 2, (p - c).dot(uy) + t / 2) for p in q])
	return L


# walls: (origin, along); the outward normal is along x up
W_CW = (Vector((0.0, -4.06, 0.0)), X)  # the cross-wing's front (both floors and its gable wall)
W_SIDE = (Vector((-7.55, 0.0, 0.0)), Y)  # the cross-wing's right wall, seen from its front corner back to the door wall
W_RB = (Vector((0.0, 0.0, 0.0)), X)  # the door wall and the round window's wall above it
W_RIGHT = (Vector((0.0, 0.0, 0.0)), Y)  # the right block's right wall
W_AX = (Vector((0.0, -1.0, 0.0)), X)  # the annex
YC, XC0, XC1 = -4.06, -14.48, -7.55  # the cross-wing: front, left wall (its corner post at pixel 478), right wall
CW_BACK = 12.0


def wnorm(W):
	return W[1].cross(UP).normalized()


def uvp(W, px, py):
	"""the (u, v) on wall W that the reference shows at pixel (px, py)"""
	org, au = W
	if abs(au.x) > 0.5:
		p = px_y(px, py, org.y)
		return (p.x * au.x, p.z)
	p = px_x(px, py, org.x)
	return (p.y * au.y, p.z)


def wpt(W, u, v, out=0.0):
	org, au = W
	return Vector(org) + Vector(au) * u + UP * v + wnorm(W) * out


def wbeam(g, W, uvs, w, t=0.7, out=None, **kw):
	"""a timber lying on wall W through (u, v) points, standing PROUD out of the plaster (out overrides)"""
	o = (PROUD if out is None else out) - t / 2
	return beam(g, [wpt(W, u, v, o) for u, v in uvs], w, t, wnorm(W), **kw)


def warc(c, r, a0, a1, steps=10):
	"""(u, v) points on an arc about c (degrees)"""
	return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def quarter(p0, p1, bulge=0.55, steps=10):
	"""a curved brace from p0 to p1 in a wall's (u, v): it leaves p0 along v (up a post) and arrives at p1 along u (under a beam)"""
	(u0, v0), (u1, v1) = p0, p1
	corner = (u0, v1)
	out = []
	for i in range(steps + 1):
		s = i / steps
		a = ((1 - s) ** 2, 2 * (1 - s) * s, s * s)
		out.append((a[0] * u0 + a[1] * corner[0] + a[2] * u1, a[0] * v0 + a[1] * corner[1] + a[2] * v1))
	return out


# ---------------------------------------------------------------------------------------------------------------- walls, windows, doors
def wall(g, kind, W, outline, holes=(), reveal="reveal", **params):
	org, au = W
	return pc.wall(g, "Walls", "Walls", kind, org, au, outline, holes=holes, thick=0.45, reveal_kind=reveal, edges=False, back=False, **params)


def opening_loop(u0, u1, v0, v1, arch=0.0, steps=14, pointed=0.0):
	"""counter-clockwise (u, v) loop of an opening, arched on top when arch > 0 (pointed > 0 lifts the crown into a soft point)"""
	if arch <= 0:
		return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
	cu, cv, r, a = pc.arch_geom(u0, u1, v1 - arch, arch)
	pts = []
	for i in range(steps + 1):
		ang = math.radians(90 - a + 2 * a * i / steps)
		lift = pointed * (1 - abs(i / steps - 0.5) * 2) ** 2
		pts.append((cu + r * math.cos(ang), cv + r * math.sin(ang) + lift))
	return [(u0, v0), (u1, v0)] + pts


def turn_uv(pts, c, deg):
	a = math.radians(deg)
	ca, sa = math.cos(a), math.sin(a)
	return [(c[0] + (u - c[0]) * ca - (v - c[1]) * sa, c[1] + (u - c[0]) * sa + (v - c[1]) * ca) for u, v in pts]


def window(g, W, u0, u1, v0, v1, arch=0.0, pointed=0.0, frame=0.46, ft=0.55, recess=0.3, bars=(), sill=(0.35, 0.55, 0.34), tilt=0.0, bar_w=0.15, **params):
	"""a window in wall W: the opening (its reveal), glass set back by `recess`, a chunky surround `frame` wide standing FRAME_PROUD
	out of the plaster, glazing bars as segments in the window's own 0..1 box (u across, v up to the crown), and a sill (overhang
	past the frame, depth out of the wall, thickness). tilt turns it a few degrees in the wall: hand-set, as the reference's."""
	n = wnorm(W)
	cu, cvv = (u0 + u1) / 2, (v0 + v1) / 2
	loop = turn_uv(opening_loop(u0, u1, v0, v1, arch, pointed=pointed), (cu, cvv), tilt)
	P = [wpt(W, u, v) for u, v in loop]
	ctr = sum(P, Vector()) / len(P)
	org, au = W
	gl = g.island("Joinery", "glass", pc.frame_of(wpt(W, u0, v0), au, UP), Face="glass", Wd=u1 - u0, Ht=v1 - v0, **params)
	g.tri_fill("Joinery", [[p - n * recess for p in P]], n, gl)
	rv = g.island("Joinery", "reveal", None, Face="reveal", **params)
	runl = 0.0
	for i in range(len(P)):
		a, b = P[i], P[(i + 1) % len(P)]
		Lr = (b - a).length
		q = [a, b, b - n * recess, a - n * recess]
		uv = [(runl, 0), (runl + Lr, 0), (runl + Lr, recess), (runl, recess)]
		if (q[1] - q[0]).cross(q[3] - q[0]).dot(ctr - (a + b) / 2) < 0:
			q, uv = q[::-1], uv[::-1]
		g.face("Joinery", q, rv, uv)
		runl += Lr
	o = FRAME_PROUD - ft / 2
	ring = [wpt(W, u, v, o) for u, v in loop]
	if arch > 0:
		beam(g, [ring[0] - UP * (frame / 2), ring[-1]], frame, ft, n, obj="Joinery", kind="frame", Part="jamb", **params)
		beam(g, [ring[1] - UP * (frame / 2), ring[2]], frame, ft, n, obj="Joinery", kind="frame", Part="jamb", **params)
		beam(g, ring[2:], frame, ft, n, obj="Joinery", kind="frame", caps=False, Part="arch", **params)
		beam(g, [ring[0] - au * (frame / 2), ring[1] + au * (frame / 2)], frame, ft, n, obj="Joinery", kind="frame", Part="rail", **params)
	else:
		for i in range(4):
			a, b = ring[i], ring[(i + 1) % 4]
			d = (b - a).normalized()
			beam(g, [a - d * (frame / 2), b + d * (frame / 2)], frame, ft, n, obj="Joinery", kind="frame", Part="side", **params)
	# bars: segments in the window's 0..1 box, set just in front of the glass
	if arch > 0:
		_cu, _cv, r, _a = pc.arch_geom(u0, u1, v1 - arch, arch)
	for (a0, b0), (a1, b1) in bars:
		pa = (u0 + (u1 - u0) * a0, v0 + (v1 - v0) * b0)
		pb = (u0 + (u1 - u0) * a1, v0 + (v1 - v0) * b1)
		pa, pb = turn_uv([pa, pb], (cu, cvv), tilt)
		beam(g, [wpt(W, pa[0], pa[1], -recess + 0.08), wpt(W, pb[0], pb[1], -recess + 0.08)], bar_w, 0.12, n, obj="Joinery", kind="frame_bar", **params)
	if sill:
		over, depth, thick = sill
		sw = (u1 - u0) + 2 * frame + 2 * over
		c = wpt(W, cu, v0 - frame / 2 - thick / 2 + 0.05, depth / 2 - 0.1)
		mark = g.mark()
		obox(g, "Joinery", "Joinery", "sill", c, au, n, (sw, depth, thick), **params)
		if tilt:
			g.warp_since(mark, lambda p: wpt(W, *turn_uv([((p - org).dot(au), p.z)], (cu, cvv), tilt)[0], (p - org).dot(n)))


def arched_door(g, W, u0, u1, top, base, fw=0.7, ft=0.62, light=True, step=True, name="door", leaf_back=0.24):
	"""a round-topped door: a chunky round arch and jambs standing just out of the wall, a planked leaf set well back in it with
	ledges, a small arched light; a timber step in front"""
	n = wnorm(W)
	org, au = W
	rise = (u1 - u0) / 2
	spring = top - rise
	cx = (u0 + u1) / 2
	o = 0.3 - ft / 2
	for u in (u0 + fw / 2, u1 - fw / 2):
		beam(g, [wpt(W, u, base - 0.1, o), wpt(W, u, spring, o)], fw, ft, n, obj="Joinery", kind="frame", Part="door_jamb", Door=name, taper=(1.06, 1.0))
	arch = warc((cx, spring), rise - fw / 2, 180, 0, 16)
	beam(g, [wpt(W, u, v, o) for u, v in arch], fw, ft, n, obj="Joinery", kind="frame", caps=False, widths=[1.0 + 0.4 * math.sin(math.pi * i / (len(arch) - 1)) for i in range(len(arch))], Part="door_arch", Door=name)
	inner = rise - fw + 0.04
	loop = [(u0 + fw - 0.04, base), (u1 - fw + 0.04, base)] + warc((cx, spring), inner, 0, 180, 16)[1:]
	leaf = g.island("Joinery", "door", pc.frame_of(wpt(W, u0 + fw, base, -leaf_back), au, UP), Face="leaf", Wd=u1 - u0 - 2 * fw, Top=spring + inner - base, Door=name)
	g.tri_fill("Joinery", [[wpt(W, u, v, -leaf_back) for u, v in loop]], n, leaf)
	# the deep reveal round the leaf, so the leaf sits in a shadowed recess
	rv = g.island("Joinery", "reveal", None, Face="reveal", Door=name)
	P = [wpt(W, u, v, 0.0) for u, v in loop]
	ctr = sum(P, Vector()) / len(P)
	run = 0.0
	for i in range(len(P)):
		a, b = P[i], P[(i + 1) % len(P)]
		if i == 0:
			continue
		q = [a, b, b - n * leaf_back, a - n * leaf_back]
		Lr = (b - a).length
		uv = [(run, 0), (run + Lr, 0), (run + Lr, leaf_back), (run, leaf_back)]
		if (q[1] - q[0]).cross(q[3] - q[0]).dot(ctr - (a + b) / 2) < 0:
			q, uv = q[::-1], uv[::-1]
		g.face("Joinery", q, rv, uv)
		run += Lr
	if light:
		lw = inner * 0.34
		lb = spring - 0.55
		lt = [(cx - lw, lb), (cx + lw, lb)] + warc((cx, lb + 0.6), lw, 0, 180, 10)[1:]
		gl = g.island("Joinery", "glass", pc.frame_of(wpt(W, cx - lw, lb, -leaf_back + 0.02), au, UP), Face="glass", Door=name)
		g.tri_fill("Joinery", [[wpt(W, u, v, -leaf_back + 0.02) for u, v in lt]], n, gl)
		ring = [wpt(W, u, v, -leaf_back + 0.1) for u, v in lt[1:]] + [wpt(W, lt[0][0], lt[0][1], -leaf_back + 0.1), wpt(W, lt[1][0], lt[1][1], -leaf_back + 0.1)]
		beam(g, ring, 0.24, 0.2, n, obj="Joinery", kind="frame", caps=False, Part="door_light", Door=name)
		beam(g, [wpt(W, u0 + fw, lb - 0.28, -leaf_back + 0.1), wpt(W, u1 - fw, lb - 0.28, -leaf_back + 0.1)], 0.34, 0.2, n, obj="Joinery", kind="frame", Part="door_rail", Door=name)
	beam(g, [wpt(W, u0 + fw, base + 1.7, -leaf_back + 0.1), wpt(W, u1 - fw, base + 1.7, -leaf_back + 0.1)], 0.42, 0.2, n, obj="Joinery", kind="frame", Part="door_ledge", Door=name)
	if step:
		obox(g, "Joinery", "Joinery", "planks", wpt(W, cx, base - 0.25, 0.75), au, n, (u1 - u0 + 0.4, 1.5, 0.46), Part="step")


def round_window(g, W, c, r, frame=0.5, ft=0.6, recess=0.32):
	n = wnorm(W)
	org, au = W
	ring = [wpt(W, c[0] + (r + frame * 0.35) * math.cos(2 * math.pi * i / 28), c[1] + (r + frame * 0.35) * math.sin(2 * math.pi * i / 28) * (1.0 + 0.04 * math.cos(2 * math.pi * i / 28 * 2)), FRAME_PROUD - ft / 2) for i in range(29)]
	beam(g, ring, frame, ft, n, obj="Joinery", kind="frame", caps=False, Part="round")
	disc = [wpt(W, c[0] + r * math.cos(2 * math.pi * i / 28), c[1] + r * math.sin(2 * math.pi * i / 28), -recess) for i in range(28)]
	gl = g.island("Joinery", "glass", pc.frame_of(wpt(W, c[0] - r, c[1] - r, -recess), au, UP), Face="glass", Round=1, Ht=2 * r)
	g.tri_fill("Joinery", [disc], n, gl)
	for (a, b) in (((c[0] - r, c[1]), (c[0] + r, c[1])), ((c[0], c[1] - r), (c[0], c[1] + r))):
		beam(g, [wpt(W, a[0], a[1], -recess + 0.08), wpt(W, b[0], b[1], -recess + 0.08)], 0.17, 0.13, n, obj="Joinery", kind="frame_bar")
	rv = g.island("Joinery", "reveal", None, Face="reveal")
	P = [wpt(W, c[0] + r * math.cos(2 * math.pi * i / 28), c[1] + r * math.sin(2 * math.pi * i / 28)) for i in range(28)]
	ctr = wpt(W, c[0], c[1])
	for i in range(28):
		p0, p1 = P[i], P[(i + 1) % 28]
		q = [p0, p1, p1 - n * recess, p0 - n * recess]
		uv = [(i * 0.3, 0), ((i + 1) * 0.3, 0), ((i + 1) * 0.3, recess), (i * 0.3, recess)]
		if (q[1] - q[0]).cross(q[3] - q[0]).dot(ctr - (p0 + p1) / 2) < 0:
			q, uv = q[::-1], uv[::-1]
		g.face("Joinery", q, rv, uv)


# ---------------------------------------------------------------------------------------------------------------- stone plinths
def stone_course(g, a, b, z0, z1, depth, seed, rows=2, length=(1.5, 2.5), normal=None, gap=0.08, gaps=()):
	"""rows of chunky stones along a wall line from a to b (plan points), z0 to z1, standing `depth` out (along normal)"""
	r = random.Random(seed)
	a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
	d = b - a
	L = d.length
	d.normalize()
	n = Vector(normal) if normal is not None else d.cross(UP)
	h = (z1 - z0) / rows
	for row in range(rows):
		s = -r.uniform(0.3, 0.9) if row % 2 else 0.0
		zc = z0 + h * (row + 0.5)
		while s < L - 0.05:
			ln = r.uniform(*length)
			if L - (s + ln) < 0.8:
				ln = L - s
			s0, s1 = max(s, 0.0), min(s + ln, L)
			s += ln
			if s1 - s0 < 0.25 or any(not (s1 < g0 or s0 > g1) for g0, g1 in gaps):
				continue
			mid = a + d * ((s0 + s1) / 2) + n * (depth / 2 - 0.2 + r.uniform(-0.05, 0.06))
			obox(g, "Stone", "Stone", "stone", mid + UP * (zc + r.uniform(-0.03, 0.03)), d, n, (s1 - s0 - gap, depth + r.uniform(-0.06, 0.06), h - gap + r.uniform(-0.05, 0.02)), Seed=r.randrange(10**6))


# ---------------------------------------------------------------------------------------------------------------- roof extras
def roof_edges(g, surf, obj, sides=("eave", "lo", "hi"), drop=0.04, under=0.22, n=24):
	"""the thickness of a roof face along its open edges: a strip from the top skin down to the soffit (a thick edge, not a sheet)"""
	isl = g.island(obj, "soffit", None, Face="edge", Roof=surf.name)
	lines = []
	if "eave" in sides:
		lines.append([(i / n, 0.0) for i in range(n + 1)])
	if "lo" in sides:
		lines.append([(0.0, j / n) for j in range(n + 1)])
	if "hi" in sides:
		lines.append([(1.0, j / n) for j in range(n + 1)])
	for line in lines:
		run = 0.0
		for (a0, b0), (a1, b1) in zip(line[:-1], line[1:]):
			p0, p1 = surf.at(a0, b0), surf.at(a1, b1)
			n0, n1 = surf.frame(a0, b0)[2], surf.frame(a1, b1)[2]
			q = [p0 + n0 * drop, p1 + n1 * drop, p1 - n1 * under, p0 - n0 * under]
			Lr = (p1 - p0).length
			uv = [(run, 0.26), (run + Lr, 0.26), (run + Lr, 0.0), (run, 0.0)]
			mid = (p0 + p1) / 2
			centre = surf.at(0.5, 0.5)
			outward = (mid - centre)
			outward.z = 0
			if (q[1] - q[0]).cross(q[3] - q[0]).dot(outward) < 0:
				q, uv = q[::-1], uv[::-1]
			g.face(obj, q, isl, uv)
			run += Lr


def barge(g, s, a_edge, out, name, w=0.95, t=0.45, inset=0.3, drop=0.34, ext=0.85, b_lo=0.0, taper=(1.05, 0.95)):
	"""a barge board tucked under a roof face's verge, just inside the tile ends with its top under them; it runs on past the
	apex by `ext` and is cut square there (the reference's crossed barge ends)"""
	out = Vector(out).normalized()
	pts = []
	for b in np.linspace(b_lo, 1.0, 16):
		p = s.at(a_edge, b)
		N = s.frame(a_edge, b)[2]
		pts.append(p - out * inset - N * drop)
	d = (pts[-1] - pts[-2]).normalized()
	pts.append(pts[-1] + d * ext)
	beam(g, pts, w, t, out, kind="barge", Part="barge", Roof=name, taper=taper)


def ridge_beak(g, ridge, side, name, beak=1.3, rise=0.45, w=0.95, t=0.6):
	"""the ridge board, on edge along the ridge, running on past the gable as a square-cut beak that tips up a little"""
	pts = [Vector(p) + UP * 0.12 for p in ridge]
	d = (pts[-1] - pts[-2]).normalized()
	d.z = 0
	d.normalize()
	pts += [pts[-1] + d * (beak * 0.5) + UP * (rise * 0.3), pts[-1] + d * beak + UP * rise]
	beam(g, pts, w, t, side, kind="barge", Part="ridge", Roof=name)


def king_block(g, apex, out, w=0.8, h=1.6, d=0.7):
	"""the short post under the barges' crossing at a gable's apex"""
	out = Vector(out).normalized()
	beam(g, [apex - UP * h - out * 0.1, apex - UP * 0.15 - out * 0.1], w, d, out, kind="barge", Part="king")


# ---------------------------------------------------------------------------------------------------------------- the plan and its roofs
RB_UP_BACK = 6.8
RB_GROUND_BACK = 11.1
Z_PLINTH = 1.8
Z_SILL = 2.4
Z_FLOOR1 = 9.2
Z_PLATE = 13.6
TW, TT = 1.0, 0.7  # a post's face width and depth: chunky, as the reference's
RIDGE_Y = 5.5
AX_FRONT = -1.0
AX_RIDGE_Y = 5.0
BOARD = 0.55
CROSS = 0.95


def define_roofs():
	"""every roof face first, so each tile can be tested against all the others. Overhangs are the reference's: the front eave 2
	studs out (its shadow band), the cross-wing's gable leaning 2 studs forward at its apex (the dark underside left of its face),
	the right gable flaring out at its feet, the annex's eave kicking out at its left corner"""
	R = {}
	# ---- the right block: a long front face (the dormer's), a short steep back one, a ridge sagging from the valley and sweeping up
	ye = -2.0
	eave = [px_y(640, 309, ye), px_y(700, 293, ye), px_y(760, 287, ye)]
	eave = [Vector((-7.6, ye, eave[0].z - 0.15))] + eave + [Vector((1.96, ye, 13.6))]
	ridge = [px_y(642, 180, RIDGE_Y), px_y(700, 160, RIDGE_Y), px_y(750, 143, RIDGE_Y), px_y(800, 118, RIDGE_Y), px_y(838, 97, RIDGE_Y)]
	ridge = [p - UP * BOARD for p in ridge]
	apex = px_y(852, 89, RIDGE_Y)
	ridge = [Vector((-12.6, RIDGE_Y, ridge[0].z - 0.35))] + ridge + [Vector((apex.x, RIDGE_Y, apex.z - CROSS))]
	R["rb_ridge"] = smooth_curve(ridge, 40)
	R["RB_F"] = Surface(smooth_curve(eave, 40), R["rb_ridge"], c=0.42, k=2.4, name="RB_F", kick=(0.0, 0.9, 0.18, 0.3, 0.25))
	foot = px_y(895, 325, 8.4)
	back_eave = [Vector((p.x + (foot.x - apex.x) * smoothstep(0.6, 1.0, i / 39), 8.4 + 0.6 * smoothstep(0.0, 0.5, i / 39), foot.z + 0.3 * (1 - i / 39))) for i, p in enumerate(R["rb_ridge"])]
	R["RB_B"] = Surface(back_eave, R["rb_ridge"], c=0.55, k=1.9, name="RB_B")
	register("RB", R["RB_F"], R["RB_B"])
	# ---- the cross-wing: its gable leans forward (the roof's front edge 0.6 out at the feet, 2.2 at the apex); the ridge droops back
	yf_feet, yf_apex = YC - 1.3, YC - 2.2  # the roof stands out on outriggers at its feet and leans further out at the apex
	apex = px_y(500, 135, yf_apex)
	footL, footR = px_y(468, 323, yf_feet), px_y(578, 318, yf_feet)
	rp = [px_x(550, 160, -12.0), px_x(600, 193, -12.0), px_x(624, 206, -12.0)]
	ridge = [Vector((apex.x, yf_apex, apex.z - CROSS))] + [Vector((p.x, p.y, p.z - BOARD)) for p in rp] + [Vector((-12.3, CW_BACK + 0.9, rp[-1].z - BOARD - 0.7))]
	R["cw_ridge"] = smooth_curve(ridge, 30)
	R["cw_apex"] = Vector((apex.x, yf_apex, apex.z - CROSS))
	eL = smooth_curve([Vector((footL.x, yf_feet, footL.z - 0.1)), Vector((XC0 - 0.75, YC + 1.2, footL.z - 0.3)), Vector((XC0 - 0.9, CW_BACK + 0.9, footL.z - 0.4))], 30)
	eR = smooth_curve([Vector((footR.x, yf_feet, footR.z - 0.1)), Vector((XC1 + 0.95, YC + 1.4, footR.z - 0.2)), Vector((XC1 + 0.95, CW_BACK + 0.9, footR.z - 0.25))], 30)
	R["CW_L"] = Surface(eL, R["cw_ridge"], c=0.9, k=1.3, n=30, name="CW_L")
	R["CW_R"] = Surface(eR, R["cw_ridge"], c=0.9, k=1.3, n=30, name="CW_R")
	register("CW", R["CW_L"], R["CW_R"])
	# ---- the annex: a sagging ridge with a curled left end; its eave flares out at the left corner
	ye = AX_FRONT - 1.8
	eave = [px_y(273, 487, ye), px_y(340, 489, ye), px_y(407, 489, ye)]
	eave = [Vector((p.x, ye, p.z)) for p in eave] + [Vector((XC0 + 0.3, ye, eave[-1].z + 0.05))]
	curl, dip, rr = px_y(340, 353, AX_RIDGE_Y), px_y(400, 368, AX_RIDGE_Y), px_y(465, 352, AX_RIDGE_Y)
	ridge = [Vector((curl.x, AX_RIDGE_Y, curl.z - CROSS)), Vector((curl.x + 2.2, AX_RIDGE_Y, curl.z - 0.9 - BOARD)), dip - UP * BOARD, rr - UP * BOARD, Vector((XC0 + 0.3, AX_RIDGE_Y, rr.z + 0.25 - BOARD))]
	R["ax_ridge"] = smooth_curve(ridge, 30)
	R["ax_eave"] = smooth_curve(eave, 30)
	R["AX_F"] = Surface(R["ax_eave"], R["ax_ridge"], c=0.32, k=2.6, n=30, name="AX_F", kick=(1.1, 0.0, 0.22, 0.35, 0.3))
	R["AX_B"] = Surface([Vector((p.x, AX_RIDGE_Y + 6.6, p.z - 0.2)) for p in R["ax_eave"]], R["ax_ridge"], c=0.4, k=2.2, n=30, name="AX_B")
	register("AX", R["AX_F"], R["AX_B"])
	# ---- the right block's dormer: a pointed little gable hood, tiled, with thick edges
	yd = 0.6
	d = {"y": yd, "L": px_y(674, 242, yd), "R": px_y(748, 242, yd), "sill": px_y(707, 274, yd), "apex": px_y(705, 166, yd - 0.9), "tipL": px_y(662, 228, yd - 1.0), "tipR": px_y(757, 219, yd - 1.0), "depth": 4.4}
	d["zt"] = (d["tipL"].z + d["tipR"].z) / 2 - 0.5
	ridge = [Vector((d["apex"].x, yd - 0.9, d["apex"].z - 0.4)), Vector((d["apex"].x + 0.1, yd + d["depth"] + 0.8, d["apex"].z - 0.8))]
	eL = [Vector((d["tipL"].x, yd - 1.0, d["tipL"].z)), Vector((d["L"].x - 0.5, yd + d["depth"] + 0.8, d["zt"] - 0.4))]
	eR = [Vector((d["tipR"].x, yd - 1.0, d["tipR"].z)), Vector((d["R"].x + 0.5, yd + d["depth"] + 0.8, d["zt"] - 0.4))]
	R["DM_L"] = Surface(eL, ridge, c=0.55, k=1.8, n=8, name="DM_L")
	R["DM_R"] = Surface(eR, ridge, c=0.55, k=1.8, n=8, name="DM_R")
	R["dormer"] = d
	register("DM", R["DM_L"], R["DM_R"])
	# ---- the annex's dormer: a short tiled hood sloping forward off the annex roof
	yd = 0.3
	a = {"y": yd, "L": px_y(343, 440, yd), "R": px_y(377, 440, yd), "sill": px_y(360, 463, yd), "top": px_y(360, 415, yd), "depth": 3.6}
	a["zt"] = a["top"].z + 0.15
	front = [Vector((a["L"].x - 0.8, yd - 1.1, a["zt"] + 0.2)), Vector((a["R"].x + 0.9, yd - 1.1, a["zt"] + 0.15))]
	back = [Vector((a["L"].x - 0.8, yd + a["depth"], a["zt"] + 1.5)), Vector((a["R"].x + 0.9, yd + a["depth"], a["zt"] + 1.45))]
	R["AXD"] = Surface(front, back, c=0.85, k=1.5, n=6, name="AXD")
	R["ax_dormer"] = a
	register("AXD", R["AXD"])
	# ---- the pent roof over the door: from the door wall out to a lip whose left corner meets the cross-wing's side wall
	lipL, lipR = px_y(612, 405, -2.6), px_y(790, 412, -2.6)
	eave = [Vector((XC1 + 0.05, -2.6, lipL.z - 0.3)), Vector(((XC1 + lipR.x) / 2, -2.6, (lipL.z + lipR.z) / 2 - 0.38)), Vector((lipR.x, -2.6, lipR.z - 0.3))]
	wallp = [Vector((p.x, -0.15, Z_FLOOR1 + 0.2)) for p in eave]
	R["CANOPY"] = Surface(smooth_curve(eave, 12), wallp, c=0.62, k=1.6, n=12, name="CANOPY")
	register("CANOPY", R["CANOPY"])
	return R


def smoothstep(a, b, x):
	t = min(max((x - a) / (b - a), 0.0), 1.0)
	return t * t * (3 - 2 * t)


def in_box(P, box):
	x0, x1, y0, y1 = box
	return x0 < P.x < x1 and y0 < P.y < y1


def roof_top(surfs, x, y, default):
	hs = [h for h in (s.height(x, y) for s in surfs) if h is not None]
	return min(hs) if hs else default


# ---------------------------------------------------------------------------------------------------------------- the cross-wing
def build_cross_wing(g, R):
	"""the middle part that stands out: its front 4 studs ahead of the door wall, its right wall seen from the front corner back to
	the door wall (the two small windows and the quarter arch the reference shows there), a carved jetty beam across the front, the
	boarded panel on the upper floor, a forward-leaning gable on outriggers"""
	W, S = W_CW, W_SIDE
	z_s0, z_s1 = 7.45, 8.7  # the carved jetty beam
	zu1 = 13.0  # top of the upper floor
	# plinth and base: stones behind a sill beam on short leaning struts
	stone_course(g, (XC0 - 0.3, YC - 0.3), (XC1 + 0.3, YC - 0.3), 0.0, Z_PLINTH - 0.2, 0.7, 3, normal=-Y)
	stone_course(g, (XC1 + 0.3, YC - 0.3), (XC1 + 0.3, 0.2), 0.0, Z_PLINTH, 0.7, 5, normal=X)
	stone_course(g, (XC0 - 0.3, CW_BACK), (XC0 - 0.3, YC - 0.3), 0.0, Z_PLINTH - 0.2, 0.7, 4, normal=-X)
	sill_l, sill_r = uvp(W, 468, 552), uvp(W, 596, 552)
	wbeam(g, W, [(sill_l[0], 2.05), (sill_r[0], 2.0)], 0.75, 0.8, out=0.75, Part="sill")
	for k, px in enumerate((483, 507, 540, 573)):
		u, _v = uvp(W, px, 570)
		lean = (-0.35, 0.25, -0.2, 0.3)[k]
		wbeam(g, W, [(u - lean, 0.0), (u + lean, 1.65)], 0.42, 0.4, out=0.95, Part="strut")
	# ground floor wall with the arched flower window (a soft point to its crown, as the reference's)
	wl, wr = uvp(W, 513, 484)[0], uvp(W, 566, 484)[0]
	wb, wt = uvp(W, 540, 509)[1], uvp(W, 540, 456)[1]
	fw_loop = opening_loop(wl, wr, wb, wt, 1.35)
	wall(g, "plaster", W, [(XC0, Z_PLINTH), (XC1, Z_PLINTH), (XC1, z_s1 - 0.3), (XC0, z_s1 - 0.3)], holes=[fw_loop], Block="CW", Floor=0)
	window(g, W, wl, wr, wb, wt, arch=1.35, frame=0.58, bars=[((0.36, 0.0), (0.36, 0.72)), ((0.64, 0.0), (0.64, 0.72)), ((0.0, 0.5), (1.0, 0.5)), ((0.5, 0.72), (0.5, 1.0)), ((0.5, 0.72), (0.14, 0.86)), ((0.5, 0.72), (0.86, 0.86))], sill=None, Block="CW", Win="flower")
	obox(g, "Joinery", "Joinery", "box", wpt(W, (wl + wr) / 2, wb - 0.8, 0.62), X, -Y, (wr - wl + 1.1, 1.2, 1.25), Part="flower_box")
	# posts and their curved knee braces into the jetty beam: they round the window panel's top corners (the reference's arch shape)
	pl, pr = uvp(W, 487, 500)[0], uvp(W, 583, 500)[0]
	wbeam(g, W, [(pl + 0.05, Z_SILL - 0.3), (pl - 0.12, 5.0), (pl - 0.05, z_s0)], TW, 0.75, Part="post")
	wbeam(g, W, [(pr - 0.05, Z_SILL - 0.3), (pr + 0.1, 5.0), (pr, z_s0)], TW, 0.75, Part="post")
	wbeam(g, W, quarter((pl - 0.45, 4.9), (pl - 2.1, z_s0 - 0.25)), 0.66, 0.55, out=0.5, Part="brace")
	wbeam(g, W, quarter((pr - 0.45, 4.6), (pr - 2.0, z_s0 - 0.25)), 0.62, 0.5, out=0.4, Part="brace")
	s_beam(g, px_y(437, 425, YC - 0.95).x, px_y(607, 425, YC - 0.95).x, YC - 0.95, z_s0, z_s1)
	# upper floor: the boarded panel between two thick posts, a curved knee brace up to the left outrigger
	wall(g, "plaster", W, [(XC0, z_s1), (XC1, z_s1), (XC1, zu1), (XC0, zu1)], Block="CW", Floor=1)
	pa, pb = uvp(W, 512, 372)[0], uvp(W, 562, 372)[0]
	pz0, pz1 = uvp(W, 536, 403)[1], uvp(W, 536, 338)[1]
	boards(g, W, pa, pb, pz0, pz1)
	ul, ur = uvp(W, 491, 370)[0], uvp(W, 574, 370)[0]
	wbeam(g, W, [(ul, z_s1), (ul + 0.1, 11.0), (ul - 0.05, zu1)], TW, 0.75, Part="post")
	wbeam(g, W, [(ur, z_s1), (ur - 0.08, 11.0), (ur + 0.05, zu1)], TW, 0.75, Part="post")
	wbeam(g, W, quarter((ul - 0.55, z_s1 + 0.6), (ul - 2.1, zu1 - 0.35), bulge=0.7), 0.6, 0.5, out=0.4, Part="brace")
	# the gable's base: a thick beam with outriggers at both corners carrying the leaning gable
	wbeam(g, W, [(XC0 - 0.5, zu1 + 0.45), (XC1 + 0.4, zu1 + 0.4)], 1.0, 0.85, out=0.6, Part="plate")
	for u0_, foot in ((XC0 + 0.35, R["CW_L"].at(0.0, 0.0)), (XC1 - 0.35, R["CW_R"].at(0.0, 0.0))):
		beam(g, [wpt(W, u0_, zu1 + 0.35, 0.2), Vector((foot.x, foot.y + 0.2, zu1 + 0.25))], 0.95, 0.9, UP, Part="outrigger", taper=(1.0, 0.9))
	# the gable wall, under the leaning roof
	CL, CR = R["CW_L"], R["CW_R"]
	gl = []
	for u in np.linspace(XC0 + 0.2, XC1 - 0.2, 30):
		gl.append((u, roof_top((CL, CR), u, YC + 0.05, zu1 + 0.9) - 0.3))
	gable = [(XC0 + 0.2, zu1 + 0.9), (XC1 - 0.2, zu1 + 0.9)] + [p for p in gl[::-1] if p[1] > zu1 + 0.95]
	fwl, fwr = uvp(W, 514, 286)[0], uvp(W, 552, 286)[0]
	fb, ft = uvp(W, 533, 302)[1], uvp(W, 533, 255)[1]
	fan = opening_loop(fwl, fwr, fb, ft, arch=(fwr - fwl) / 2)
	wall(g, "plaster", W, gable, holes=[fan], Block="CW", Floor=2)
	window(g, W, fwl, fwr, fb, ft, arch=(fwr - fwl) / 2, frame=0.5, bars=[((0.5, 0.0), (0.5, 1.0)), ((0.5, 0.05), (0.06, 0.62)), ((0.5, 0.05), (0.94, 0.62))], sill=None, Block="CW", Win="fan")
	ledge = [(fwl - 1.2, fb - 0.42), ((fwl + fwr) / 2, fb - 0.55), (fwr + 1.2, fb - 0.42)]
	wbeam(g, W, ledge, 0.8, 1.0, out=0.8, Part="ledge")
	# its right wall, from the front corner back to the door wall: two small windows, the quarter arch, bricks (painter)
	lw0, lw1 = uvp(S, 613, 475)[0], uvp(S, 638, 475)[0]
	lz0, lz1 = uvp(S, 625, 493)[1], uvp(S, 625, 456)[1]
	hw0, hw1 = uvp(S, 613, 366)[0], uvp(S, 638, 366)[0]
	hz0, hz1 = uvp(S, 625, 382)[1], uvp(S, 625, 349)[1]
	wall(g, "plaster_shade", S, [(YC, Z_PLINTH), (0.0, Z_PLINTH), (0.0, z_s0 + 0.6), (YC, z_s0 + 0.6)], holes=[opening_loop(lw0, lw1, lz0, lz1)], Block="CW", Side="right")
	top_side = [(y, roof_top((CL, CR), XC1 + 0.05, y, zu1) - 0.25) for y in np.linspace(YC, 0.0, 12)]
	wall(g, "plaster_shade", S, [(YC, z_s0 + 0.6), (0.0, z_s0 + 0.6)] + top_side[::-1], holes=[opening_loop(hw0, hw1, hz0, hz1)], Block="CW", Side="right_up")
	window(g, S, lw0, lw1, lz0, lz1, frame=0.4, bars=[((0.5, 0.0), (0.5, 1.0))], sill=(0.2, 0.45, 0.3), Block="CW", Win="side_low")
	window(g, S, hw0, hw1, hz0, hz1, frame=0.4, bars=(), sill=(0.2, 0.45, 0.3), tilt=-2.0, Block="CW", Win="side_up")
	ya, yb = uvp(S, 595, 552), uvp(S, 652, 503)
	ru, rv = -0.35 - (YC + 0.25), yb[1] - ya[1]
	wbeam(g, S, [(-0.35 - ru * math.cos(math.radians(t)), ya[1] + rv * math.sin(math.radians(t))) for t in np.linspace(0, 90, 10)], 0.62, 0.5, out=0.4, Part="arch")
	wbeam(g, S, [(-0.35, Z_SILL - 0.3), (-0.3, zu1)], 0.9, 0.75, Part="post")
	wbeam(g, S, [(YC + 0.1, z_s0 + 0.05), (-0.2, z_s0 + 0.15)], 0.8, 0.7, Part="beam")
	wbeam(g, S, [(YC + 0.1, Z_SILL - 0.2), (-0.2, Z_SILL - 0.15)], 0.62, 0.65, Part="sill")
	# the left wall (seen only from the side)
	wall(g, "plaster_shade", (Vector((XC0, 0, 0)), -Y), [(-CW_BACK, Z_PLINTH), (-YC, Z_PLINTH), (-YC, zu1), (-CW_BACK, zu1)], Block="CW", Side="left")
	# roof
	n_l = lay_tiles(g, CL, "RoofLB", seed=51)
	n_r = lay_tiles(g, CR, "RoofLB", seed=52)
	for s in (CL, CR):
		roof_skin(g, s, "RoofLB")
		roof_edges(g, s, "RoofLB", sides=("eave", "lo"))
	barge(g, CL, 0.0, -Y, "CW", w=1.4, t=0.58, inset=0.25, drop=0.45, ext=0.2)
	barge(g, CR, 0.0, -Y, "CW", w=1.3, t=0.58, inset=0.25, drop=0.42, ext=0.2)
	ridge_beak(g, list(reversed(R["cw_ridge"])), -X, "CW", beak=1.8, rise=0.35, w=1.05, t=0.7)
	king_block(g, R["cw_apex"] + Y * 0.3, -Y)
	print("[crooked] cross-wing tiles", n_l, n_r, flush=True)


def s_beam(g, xa, xb, y, z0, z1):
	"""the carved jetty beam: its front face swells into a big scroll left of centre and thins toward the right (the reference's)"""
	steps = 36

	def depth(t):
		# a slim beam that drops into one carved scroll left of centre, with small swellings at both ends
		return 0.66 + 0.62 * math.exp(-(((t - 0.3) / 0.075) ** 2)) + 0.22 * math.exp(-(((t - 0.05) / 0.04) ** 2)) + 0.2 * math.exp(-(((t - 0.95) / 0.04) ** 2))

	def bulge(t):
		return 0.22 * math.exp(-(((t - 0.3) / 0.09) ** 2)) + 0.06 * math.sin(t * math.pi * 4)

	fr = g.island("Timber", "timber", None, Face="front", Part="s_beam", Width=1.6, Length=xb - xa)
	tp = g.island("Timber", "timber", None, Face="top", Part="s_beam", Width=1.1, Length=xb - xa)
	bt = g.island("Timber", "timber", None, Face="bottom", Part="s_beam", Width=1.1, Length=xb - xa)
	zt = z1
	prev = None
	for i in range(steps + 1):
		t = i / steps
		x = xa + (xb - xa) * t
		dpt = depth(t)
		b = bulge(t)
		front = (Vector((x, y - b, zt)), Vector((x, y - b - 0.15, zt - dpt)))
		back = (Vector((x, y + 1.0, zt)), Vector((x, y + 1.0, zt - 0.8)))
		if prev:
			pf, pb, xp_, dp = prev
			for quad, uv, want, isl in (
				([pf[0], front[0], front[1], pf[1]], [(xp_ - xa, 1.6), (x - xa, 1.6), (x - xa, 1.6 - dpt), (xp_ - xa, 1.6 - dp)], -Y, fr),
				([pf[0], pb[0], back[0], front[0]], [(xp_ - xa, 0), (xp_ - xa, 1.1), (x - xa, 1.1), (x - xa, 0)], UP, tp),
				([pf[1], front[1], back[1], pb[1]], [(xp_ - xa, 0), (x - xa, 0), (x - xa, 1.1), (xp_ - xa, 1.1)], -UP, bt),
			):
				if (quad[1] - quad[0]).cross(quad[3] - quad[0]).dot(want) < 0:
					quad, uv = quad[::-1], uv[::-1]
				g.face("Timber", quad, isl, uv)
		prev = (front, back, x, dpt)
	for x, sgn, t in ((xa, -1, 0.0), (xb, 1, 1.0)):
		dpt, b = depth(t), bulge(t)
		q = [Vector((x, y - b, zt)), Vector((x, y + 1.0, zt)), Vector((x, y + 1.0, zt - 0.8)), Vector((x, y - b - 0.15, zt - dpt))]
		if (q[1] - q[0]).cross(q[3] - q[0]).dot(X * sgn) < 0:
			q = q[::-1]
		e = g.island("Timber", "timber_end", None, Face="end", Part="s_beam", W=1.2, T=1.6)
		g.face("Timber", q, e, [(p.y - y + 0.4, p.z - zt + 1.6) for p in q])


def boards(g, W, ua, ub, za, zb):
	"""the boarded panel: upright planks in a chunky frame, a little proud of the plaster"""
	n = 5
	w = (ub - ua) / n
	for i in range(n):
		c = wpt(W, ua + w * (i + 0.5), (za + zb) / 2 + 0.04 * ((i * 7) % 3 - 1), 0.12 + 0.04 * (i % 2))
		obox(g, "Joinery", "Joinery", "planks", c, X, -Y, (w - 0.08, 0.28, zb - za), Part="boards", Upright=1)
	for zz in (za - 0.12, zb + 0.12):
		wbeam(g, W, [(ua - 0.35, zz), (ub + 0.35, zz)], 0.5, 0.42, out=0.42, obj="Joinery", kind="frame", Part="board_frame")
	for uu in (ua - 0.18, ub + 0.18):
		wbeam(g, W, [(uu, za - 0.3), (uu, zb + 0.3)], 0.48, 0.42, out=0.42, obj="Joinery", kind="frame", Part="board_frame")


# ---------------------------------------------------------------------------------------------------------------- the right block
def build_right_block(g, R):
	W, RW = W_RB, W_RIGHT
	nF = -Y
	rnd = random.Random(11)
	# plinth
	door_u0, door_u1 = uvp(W, 680, 600)[0], uvp(W, 762, 437)[0]
	door_top = uvp(W, 721, 430)[1]
	stone_course(g, (XC1 + 0.3, -0.3), (0.3, -0.3), 0.0, Z_PLINTH, 0.7, 1, normal=-Y, gaps=[(door_u0 - XC1 - 0.4, door_u1 - XC1 + 0.1)])
	stone_course(g, (0.3, -0.3), (0.3, RB_GROUND_BACK + 0.3), 0.0, Z_PLINTH, 0.7, 2, normal=X)
	# the door wall: plaster round the door's notch; the inner corner post, the corner post, the first-floor beam
	rise = (door_u1 - door_u0) / 2
	spring = door_top - rise
	cx = (door_u0 + door_u1) / 2
	notch = [(door_u0, Z_PLINTH), (door_u0, spring)] + warc((cx, spring), rise, 180, 0, 16)[1:-1] + [(door_u1, spring), (door_u1, Z_PLINTH)]
	wall(g, "plaster", W, [(XC1, Z_PLINTH)] + notch + [(0.0, Z_PLINTH), (0.0, Z_FLOOR1 - 0.4), (XC1, Z_FLOOR1 - 0.4)], Block="RB", Floor=0)
	arched_door(g, W, door_u0, door_u1, door_top, 0.25, name="front")
	wbeam(g, W, [(XC1 + 0.4, Z_SILL - 0.3), (XC1 + 0.45, Z_FLOOR1 - 0.4)], 0.9, 0.75, Part="post")
	wbeam(g, W, [(-0.05, Z_SILL - 0.4), (0.0, Z_FLOOR1 - 0.4)], 1.1, 0.85, Part="post", taper=(1.06, 0.98))
	wbeam(g, W, [(XC1, Z_PLINTH + 0.28), (door_u0 + 0.1, Z_PLINTH + 0.26)], 0.62, 0.7, Part="sill")
	wbeam(g, W, [(door_u1 - 0.1, Z_PLINTH + 0.26), (0.6, Z_PLINTH + 0.24)], 0.62, 0.7, Part="sill")
	wbeam(g, W, [(XC1 - 0.2, Z_FLOOR1 - 0.4), (cx, Z_FLOOR1 - 0.5), (1.0, Z_FLOOR1 - 0.35)], 0.95, 0.85, out=0.55, Part="beam")
	# the right wall, ground floor: the tall window, the round-topped one, posts, the top beams
	tall = (uvp(RW, 810, 480)[0], uvp(RW, 846, 480)[0], uvp(RW, 828, 515)[1], uvp(RW, 828, 445)[1])
	arw = (uvp(RW, 868, 480)[0], uvp(RW, 896, 480)[0], uvp(RW, 882, 507)[1], uvp(RW, 882, 450)[1])
	wall(g, "plaster", RW, [(0, Z_PLINTH), (RB_GROUND_BACK, Z_PLINTH), (RB_GROUND_BACK, Z_FLOOR1 - 0.4), (0, Z_FLOOR1 - 0.4)], holes=[opening_loop(*tall), opening_loop(*arw, arch=1.0)], Block="RB", Floor=0, Side="right")
	window(g, RW, *tall, frame=0.5, bars=(), sill=(0.25, 0.6, 0.36), Block="RB", Win="tall")
	window(g, RW, *arw, arch=1.0, frame=0.44, bars=[((0.0, 0.3), (1.0, 0.3)), ((0.0, 0.55), (1.0, 0.55)), ((0.0, 0.78), (1.0, 0.78))], sill=(0.2, 0.5, 0.32), Block="RB", Win="arch_right")
	wall(g, "plaster_shade", (Vector((0, RB_GROUND_BACK, 0)), -X), [(0, Z_PLINTH), (-XC1, Z_PLINTH), (-XC1, Z_FLOOR1), (0, Z_FLOOR1)], Block="RB", Side="back")
	for y_, lean in ((uvp(RW, 856, 480)[0], 0.12), (RB_GROUND_BACK, -0.1)):
		wbeam(g, RW, [(y_, Z_SILL - 0.3), (y_ + lean, 5.5), (y_, Z_FLOOR1 - 0.4)], TW, 0.75, Part="post")
	wbeam(g, RW, [(-0.6, Z_FLOOR1 - 0.4), (RB_GROUND_BACK + 0.5, Z_FLOOR1 - 0.5)], 0.95, 0.85, out=0.55, Part="beam")
	wbeam(g, RW, [(0.4, uvp(RW, 850, 422)[1]), (RB_GROUND_BACK, uvp(RW, 900, 428)[1])], 0.55, 0.5, Part="rail")
	wbeam(g, RW, [(0.0, Z_PLINTH + 0.3), (RB_GROUND_BACK + 0.4, Z_PLINTH + 0.33)], 0.62, 0.7, Part="sill")
	# the upper floor's front: the round window cradled by two arched braces, posts, the wall plate
	z0, z1 = Z_FLOOR1, Z_PLATE
	rc = uvp(W, 720, 333)
	rr = 1.28
	ring = [(rc[0] + rr * math.cos(2 * math.pi * i / 28), rc[1] + rr * math.sin(2 * math.pi * i / 28)) for i in range(28)]
	wall(g, "plaster", W, [(XC1, z0), (0, z0), (0, z1), (XC1, z1)], holes=[ring], Block="RB", Floor=1)
	round_window(g, W, rc, rr)
	ula, ura = uvp(W, 666, 350)[0], uvp(W, 772, 350)[0]
	wbeam(g, W, [(ula, z0), (ula - 0.1, 11.3), (ula + 0.05, z1)], 0.9, 0.7, Part="post")
	wbeam(g, W, [(ura, z0), (ura + 0.1, 11.3), (ura - 0.05, z1)], 0.9, 0.7, Part="post")
	wbeam(g, W, [(0.0, z0), (0.08, 11.3), (0.0, z1)], 1.05, 0.8, Part="post")
	# two little semicircular arches on the floor beam under the round window (the reference's arcade), plaster inside them
	for pa, pb, pt in (((673, 386), (712, 386), (692, 351)), ((733, 386), (771, 386), (752, 349))):
		ua, ub = uvp(W, *pa)[0], uvp(W, *pb)[0]
		tv = uvp(W, *pt)[1]
		cu, ru, rv = (ua + ub) / 2, (ub - ua) / 2, tv - z0
		wbeam(g, W, [(cu - ru * math.cos(math.radians(t)), z0 - 0.05 + rv * math.sin(math.radians(t))) for t in np.linspace(0, 180, 16)], 0.56, 0.5, out=0.4, Part="arch")
	wbeam(g, W, [(XC1 - 0.3, z1 + 0.2), (1.0, z1 + 0.3)], 0.85, 0.8, out=0.55, Part="plate")
	# the upper floor's right wall: posts that bow, beams that tilt down toward the back (the reference's)
	wall(g, "plaster", RW, [(0, z0), (RB_UP_BACK, z0), (RB_UP_BACK, z1), (0, z1)], Block="RB", Floor=1, Side="right")
	wbeam(g, RW, [(RB_UP_BACK, z0), (RB_UP_BACK + 0.25, 11.4), (RB_UP_BACK, z1 + 0.4)], TW, 0.75, Part="post")
	wbeam(g, RW, [(0.2, uvp(RW, 803, 336)[1]), (RB_UP_BACK, uvp(RW, 847, 346)[1])], 0.6, 0.5, Part="rail")
	wbeam(g, RW, [(-0.6, z1 + 0.3), (RB_UP_BACK + 0.5, z1 - 0.15)], 0.85, 0.8, out=0.55, Part="plate")
	# the roof, the boarded gable over the right wall and its double window
	front, back = R["RB_F"], R["RB_B"]
	top = [(-x_, roof_top((front, back), x_, RB_UP_BACK, z1) - 0.3) for x_ in np.linspace(XC1, 0.0, 21)]
	wall(g, "plaster_shade", (Vector((0, RB_UP_BACK, 0)), -X), [(0, z0), (-XC1, z0)] + top, Block="RB", Side="back_up")
	go = [(y_, roof_top((front, back), 0.0, y_, z1) - 0.25) for y_ in np.linspace(0.0, RB_UP_BACK, 31)]
	gw = (uvp(RW, 806, 255)[0], uvp(RW, 834, 255)[0], uvp(RW, 820, 287)[1], uvp(RW, 820, 222)[1])
	gmid = (gw[0] + gw[1]) / 2
	lancets = [opening_loop(gw[0], gmid - 0.12, gw[2], gw[3], arch=(gmid - 0.12 - gw[0]) / 2), opening_loop(gmid + 0.12, gw[1], gw[2], gw[3], arch=(gw[1] - gmid - 0.12) / 2)]
	wall(g, "gable_boards", RW, [(0.0, z1 + 0.6), (RB_UP_BACK, z1 + 0.6)] + go[::-1], holes=lancets, Block="RB", Floor=2, Side="gable")
	for a0, a1 in ((gw[0], gmid - 0.12), (gmid + 0.12, gw[1])):
		window(g, RW, a0, a1, gw[2], gw[3], arch=(a1 - a0) / 2, frame=0.32, ft=0.45, bars=(), sill=None, Block="RB", Win="lancet")
	wbeam(g, RW, [(gw[0] - 0.7, gw[2] - 0.35), (gw[1] + 0.7, gw[2] - 0.38)], 0.5, 0.5, out=0.5, Part="ledge")
	d = R["dormer"]
	dbox = (d["L"].x - 0.2, d["R"].x + 0.2, d["y"] - 0.3, d["y"] + 1.6)
	nf = lay_tiles(g, front, "RoofRB", seed=21, skip=lambda P: in_box(P, dbox))
	nb = lay_tiles(g, back, "RoofRB", seed=22)
	for s in (front, back):
		roof_skin(g, s, "RoofRB")
		roof_edges(g, s, "RoofRB", sides=("eave", "hi"))
	barge(g, front, 1.0, X, "RB", w=1.2, t=0.55, inset=0.3, drop=0.4, ext=0.2)
	barge(g, back, 1.0, X, "RB", w=1.2, t=0.55, inset=0.3, drop=0.4, ext=0.2)
	ridge_beak(g, R["rb_ridge"][1:], -Y, "RB", beak=1.4, rise=0.45)
	king_block(g, R["rb_ridge"][-1] + X * 0.25, X, h=1.4)
	rb_dormer(g, R)
	canopy(g, R)
	balcony(g)
	print("[crooked] right block tiles", nf, nb, flush=True)


def cheek(g, roof, x_, sign, y0, depth, zs, zt, kind="plaster_shade", **params):
	"""a dormer's side wall from its front back to where the roof below rises to meet its top"""
	pts = []
	y_end = y0 + depth
	for j in range(41):
		y_ = y0 + depth * j / 40
		h = roof.height(x_, y_)
		h = zs if h is None else h - 0.1
		if h >= zt - 0.05:
			y_end = y_
			pts.append((y_, zt - 0.05))
			break
		pts.append((y_, h))
	loop = [(y0, zs), (y0, zt), (y_end, zt)] + pts[::-1][1:-1]
	if sign > 0:
		wall(g, kind, (Vector((x_, 0, 0)), Y), loop, **params)
	else:
		wall(g, kind, (Vector((x_, 0, 0)), -Y), [(-u, v) for u, v in loop], **params)


def rb_dormer(g, R):
	"""the dormer: a plaster front whose big arched window and chunky frame fill it, its tiled hood with thick edges and flared tips,
	slim barges tucked under the tile ends, a little square beak at the apex"""
	d = R["dormer"]
	roof = R["RB_F"]
	yd = d["y"]
	Wd = (Vector((0.0, yd, 0.0)), X)
	x0, x1 = d["L"].x, d["R"].x
	zs, zt = d["sill"].z - 0.25, d["zt"]
	wv = (uvp(Wd, 689, 246)[0], uvp(Wd, 726, 246)[0], uvp(Wd, 707, 268)[1], uvp(Wd, 707, 216)[1])
	outline = [(x0, zs), (x1, zs), (x1, zt), ((x0 + x1) / 2, d["apex"].z - 1.0), (x0, zt)]
	wall(g, "plaster", Wd, outline, holes=[opening_loop(*wv, arch=0.95)], Block="Dormer")
	window(g, Wd, *wv, arch=0.95, frame=0.55, ft=0.6, bars=[((0.0, 0.2), (1.0, 0.2)), ((0.0, 0.4), (1.0, 0.4)), ((0.0, 0.6), (1.0, 0.6)), ((0.0, 0.78), (1.0, 0.78))], sill=(0.3, 0.6, 0.38), tilt=1.5, Block="Dormer", Win="dormer")
	cheek(g, roof, x0, -1, yd, d["depth"], zs, zt, Block="Dormer")
	cheek(g, roof, x1, 1, yd, d["depth"], zs, zt, Block="Dormer")
	for x_ in (x0, x1):
		wbeam(g, Wd, [(x_, zs - 0.3), (x_, zt)], 0.55, 0.5, Part="post")
	for s, sd in ((R["DM_L"], 31), (R["DM_R"], 32)):
		lay_tiles(g, s, "RoofRB", tile_w=1.3, row=1.05, tile_len=1.55, thick=0.26, rest=0.14, seed=sd)
		roof_skin(g, s, "RoofRB", na=6, nb=6)
		roof_edges(g, s, "RoofRB", sides=("eave", "lo"))
		barge(g, s, 0.0, -Y, "DM", w=0.5, t=0.32, inset=0.18, drop=0.26, ext=0.45)


def canopy(g, R):
	s = R["CANOPY"]
	lay_tiles(g, s, "RoofRB", tile_w=1.75, row=1.2, tile_len=1.8, thick=0.3, seed=41)
	roof_skin(g, s, "RoofRB", na=8, nb=3)
	roof_edges(g, s, "RoofRB", sides=("eave", "hi"))


def balcony(g):
	"""the shelf over the ground floor's bay beside the right gable, and the low deck along the right wall"""
	z = Z_FLOOR1 - 0.15
	x1 = 2.5
	y1 = px_x(940, 398, x1).y
	y0 = RB_UP_BACK - 1.6
	for xc, dy0, dy1, dz in ((0.45, 0.0, -0.4, 0.0), (1.3, 0.3, 0.2, 0.05), (2.15, -0.2, 0.45, 0.0)):
		obox(g, "Joinery", "Joinery", "planks", (xc, (y0 + dy0 + y1 + dy1) / 2, z + dz), Y, X, (y1 + dy1 - y0 - dy0, 0.82, 0.3), Part="shelf")
	for yy in (y0 + 0.8, y1 - 1.0):
		beam(g, [(0.0, yy, z - 0.42), (x1 + 0.35, yy, z - 0.45)], 0.45, 0.5, Y, Part="joist")
	dl, dr = px_x(813, 557, 3.0), px_x(920, 567, 3.0)
	dl = Vector((dl.x, max(dl.y, 0.4), dl.z))
	for i in range(4):
		xc = 0.7 + i * 0.78
		obox(g, "Joinery", "Joinery", "planks", (xc, (dl.y + dr.y) / 2 + 0.15 * (i % 2), (dl.z + dr.z) / 2 - 0.2 + 0.03 * i), Y, X, (dr.y - dl.y + 0.3 * (i % 2), 0.74, 0.3), Part="deck")
	for yy in (dl.y + 0.6, dr.y - 0.6):
		beam(g, [(0.3, yy, 0.0), (3.2, yy, 0.0)], 0.5, 1.2, Y, Part="deck_joist")


# ---------------------------------------------------------------------------------------------------------------- annex
def build_annex(g, R):
	"""the low annex on the left: a wall with a small round-topped door, a sagging roof with a curled left end and a small tiled hood
	over its dormer, an open bay against the cross-wing (barrel, crates)"""
	W = W_AX
	yf = W[0].y
	xL = uvp(W, 300, 520)[0]
	xR = uvp(W, 398, 520)[0]
	ze = 5.0
	stone_course(g, (xL - 0.3, yf - 0.3), (xR + 0.3, yf - 0.3), 0.0, 1.2, 0.6, 7, rows=1, normal=-Y)
	dl, dr = uvp(W, 332, 540)[0], uvp(W, 375, 540)[0]
	dtop = uvp(W, 355, 500)[1]
	rise = (dr - dl) / 2
	spring = dtop - rise
	cxd = (dl + dr) / 2
	notch = [(dl, 1.2), (dl, spring)] + warc((cxd, spring), rise, 180, 0, 12)[1:-1] + [(dr, spring), (dr, 1.2)]
	wall(g, "plaster", W, [(xL, 1.2)] + notch + [(xR, 1.2), (xR, ze), (xL, ze)], Block="AX")
	arched_door(g, W, dl, dr, dtop, 0.6, fw=0.5, ft=0.52, light=True, step=False, name="annex", leaf_back=0.3)
	for xx, lean in ((xL + 0.4, 0.12), (xR - 0.35, -0.1)):
		wbeam(g, W, [(xx, 1.2), (xx + lean, 3.2), (xx, ze + 0.2)], 0.8, 0.65, Part="post")
	wbeam(g, W, [(xL - 0.3, ze + 0.15), (xR + 0.5, ze + 0.1)], 0.75, 0.7, out=0.55, Part="plate")
	bay_y = yf + 3.2
	wall(g, "brick", (Vector((0, bay_y, 0)), X), [(xR, 0.0), (XC0, 0.0), (XC0, 9.0), (xR, 9.0)], Block="AX", Side="bay")
	wall(g, "plaster_shade", (Vector((xR, 0, 0)), Y), [(yf, 0.0), (bay_y, 0.0), (bay_y, ze), (yf, ze)], Block="AX", Side="bay_side")
	beam(g, [(XC0 - 0.6, yf - 0.6, 0.0), (XC0 - 0.55, yf - 0.6, ze + 0.7)], 0.75, 0.7, -Y, Part="post")
	front, back = R["AX_F"], R["AX_B"]
	go = []
	for y_ in np.linspace(yf, AX_RIDGE_Y + 5.6, 24):
		hs = [h for h in (front.height(xL + 0.7, y_), back.height(xL + 0.7, y_)) if h is not None]
		if hs:
			go.append((y_, min(hs) - 0.3))
	if go:
		wall(g, "plaster_shade", (Vector((xL, 0, 0)), -Y), [(-yf, 1.2), (-(AX_RIDGE_Y + 5.6), 1.2)] + [(-y_, z_) for y_, z_ in go[::-1]], Block="AX", Side="gable")
	a = R["ax_dormer"]
	abox = (a["L"].x - 0.3, a["R"].x + 0.3, a["y"] - 0.3, a["y"] + 1.4)
	n_f = lay_tiles(g, front, "RoofAX", seed=61, skip=lambda P: in_box(P, abox))
	n_b = lay_tiles(g, back, "RoofAX", seed=62)
	for s in (front, back):
		roof_skin(g, s, "RoofAX")
		roof_edges(g, s, "RoofAX", sides=("eave", "lo"))
	barge(g, front, 0.0, -X, "AX", w=0.85, t=0.42, inset=0.3)
	barge(g, back, 0.0, -X, "AX", w=0.85, t=0.42, inset=0.3)
	ridge_beak(g, list(reversed(R["ax_ridge"])), -Y, "AX", beak=0.9, rise=0.55)
	# its dormer under a tiled hood
	yd = a["y"]
	Wd = (Vector((0.0, yd, 0.0)), X)
	x0, x1 = a["L"].x, a["R"].x
	zs, zt = a["sill"].z - 0.25, a["zt"]
	wall(g, "plaster", Wd, [(x0, zs), (x1, zs), (x1, zt), (x0, zt)], holes=[opening_loop(x0 + 0.45, x1 - 0.45, zs + 0.45, zt - 0.3, arch=0.6)], Block="AXD")
	window(g, Wd, x0 + 0.45, x1 - 0.45, zs + 0.45, zt - 0.3, arch=0.6, frame=0.36, bars=[((0.0, 0.3), (1.0, 0.3)), ((0.0, 0.55), (1.0, 0.55)), ((0.0, 0.78), (1.0, 0.78))], sill=(0.15, 0.45, 0.3), Block="AXD", Win="ax_dormer")
	cheek(g, front, x0, -1, yd, a["depth"], zs, zt + 0.5, Block="AXD")
	cheek(g, front, x1, 1, yd, a["depth"], zs, zt + 0.5, Block="AXD")
	lay_tiles(g, R["AXD"], "RoofAX", tile_w=1.35, row=1.05, tile_len=1.5, thick=0.28, rest=0.14, seed=63)
	roof_skin(g, R["AXD"], "RoofAX", na=4, nb=4)
	roof_edges(g, R["AXD"], "RoofAX", sides=("eave", "lo", "hi"))
	print("[crooked] annex tiles", n_f, n_b, flush=True)


# ---------------------------------------------------------------------------------------------------------------- chimney
def fit_box(lpx, rpx, py, yc, k=0.95):
	"""a box centred on the plane y = yc whose silhouette spans pixels lpx..rpx at row py (its front-left and back-right edges)"""
	hw = 1.5
	for _ in range(30):
		hd = hw * k
		a = px_y(lpx, py, yc - hd)
		b = px_y(rpx, py, yc + hd)
		hw = (b.x - a.x) / 2
	return (a.x + b.x) / 2, hw, (a.z + b.z) / 2


def chimney(g):
	"""tall and tapering, cream render with bricks showing, a thin dark cap slab with a smaller one on it"""
	yc = 6.0
	cxt, hwt, zt_ = fit_box(603, 651, 80, yc)
	cxb, hwb, zb_ = fit_box(600, 657, 200, yc)
	ccx, chw, czc = fit_box(595, 662, 50, yc, 0.92)
	cap_top = px_y(630, 31, yc - chw).z
	cap_bot = px_y(630, 60, yc - chw).z
	z_b = 15.0

	def ring(z):
		t = (z - zb_) / (zt_ - zb_)
		cxx = lerp(cxb, cxt, t)
		hw = lerp(hwb, hwt, t)
		hd = hw * 0.95
		return [Vector((cxx - hw, yc - hd, z)), Vector((cxx + hw, yc - hd, z)), Vector((cxx + hw, yc + hd, z)), Vector((cxx - hw, yc + hd, z))]

	zs = [z_b, cap_bot - 1.3, cap_bot]
	for k in range(2):
		lo, hi = ring(zs[k]), ring(zs[k + 1])
		kind = "chimney" if k == 0 else "brick"
		for i, (fname, au) in enumerate((("-y", X), ("+x", Y), ("+y", -X), ("-x", -Y))):
			isl = g.island("Stone", kind, pc.frame_of(lo[i], au, UP), Face=fname, Part="chimney")
			g.face("Stone", [lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i]], isl)
	slab = (cap_top - cap_bot) * 0.55
	obox(g, "Stone", "Stone", "chimney_cap", (ccx, yc, cap_bot + slab / 2), X, Y, (2 * chw, 2 * chw * 0.92, slab), Part="cap")
	obox(g, "Stone", "Stone", "chimney_cap", (ccx - 0.05, yc, cap_bot + slab + (cap_top - cap_bot - slab) / 2), X, Y, (2 * chw * 0.72, 2 * chw * 0.68, cap_top - cap_bot - slab), Part="cap_top")
	print("[crooked] chimney widths", round(2 * hwb, 2), round(2 * hwt, 2), "cap", round(2 * chw, 2), flush=True)


def build_house(g, R):
	build_cross_wing(g, R)
	build_right_block(g, R)
	build_annex(g, R)
	chimney(g)


# ---------------------------------------------------------------------------------------------------------------- the garden around it
def gp(px, py, z=0.0):
	"""the point on the ground (height z) that the reference shows at pixel (px, py)"""
	return px_plane(px, py, UP, z)


def ground_h(x, y):
	"""the lawn's height: flat by the house, rolling a little farther out, falling away toward us"""
	far = max(0.0, min(1.0, (abs(y - 4.0) - 8.0) / 25.0)) * max(0.0, min(1.0, (abs(x + 12.0) - 22.0) / 25.0 + 0.6))
	return -0.1 + far * (0.6 * math.sin(x * 0.06 + 1.3) * math.cos(y * 0.05) - 0.25) - 0.9 * max(0.0, min(1.0, (-y - 25.0) / 30.0))


def ground(g):
	"""a gently rolling lawn around the house: one painted island (u, v = world x, y)"""
	x0, x1, y0, y1, cell = -90.0, 70.0, -60.0, 60.0, 4.0
	nx, ny = int((x1 - x0) / cell), int((y1 - y0) / cell)
	isl = g.island("Ground", "grass", pc.frame_of((0, 0, 0), X, Y), Face="+z")
	for i in range(nx):
		for j in range(ny):
			xa, xb = x0 + i * cell, x0 + (i + 1) * cell
			ya, yb = y0 + j * cell, y0 + (j + 1) * cell
			q = [Vector((xa, ya, ground_h(xa, ya))), Vector((xb, ya, ground_h(xb, ya))), Vector((xb, yb, ground_h(xb, yb))), Vector((xa, yb, ground_h(xa, yb)))]
			g.face("Ground", q, isl, [(p.x, p.y) for p in q])


def on_ground(P):
	P = Vector(P)
	return Vector((P.x, P.y, ground_h(P.x, P.y)))


def flagstone(g, c, r, seed, yaw=0.0, thick=0.28, obj="Ground"):
	"""a flat stepping stone: an irregular rounded slab set into the grass"""
	rr = random.Random(seed)
	c = on_ground(c)
	n = 10
	pts = []
	for k in range(n):
		a = 2 * math.pi * k / n + math.radians(yaw)
		rad = r * rr.uniform(0.82, 1.08) * (1.0 if k % 2 else 0.95)
		pts.append(Vector((c.x + rad * math.cos(a) * 1.25, c.y + rad * math.sin(a) * 0.9, c.z + 0.1 + rr.uniform(-0.03, 0.03))))
	top = g.island(obj, "flagstone", pc.frame_of(pts[0], X, Y), Face="+z", Seed=seed)
	g.tri_fill(obj, [pts], UP, top)
	side = g.island(obj, "flagstone", None, Face="side", Seed=seed)
	run = 0.0
	for k in range(n):
		a, b = pts[k], pts[(k + 1) % n]
		q = [a, b, b - UP * thick, a - UP * thick]
		L = (b - a).length
		uv = [(run, thick), (run + L, thick), (run + L, 0), (run, 0)]
		if (q[1] - q[0]).cross(q[3] - q[0]).dot((a + b) / 2 - c) < 0:
			q, uv = q[::-1], uv[::-1]
		g.face(obj, q, side, uv)
		run += L


def rock(g, c, size, seed, obj="Props"):
	"""a chunky rock: a squashed, chipped icosphere hull"""
	import bmesh
	from mathutils import Matrix

	rr = random.Random(seed)
	c = on_ground(c)
	bm = bmesh.new()
	bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0, matrix=Matrix.Identity(4))
	isl = g.island(obj, "rock", None, Face="rock", Seed=seed)
	for f in bm.faces:
		pts = []
		for v in f.verts:
			k = 0.86 + 0.24 * ((hash((round(v.co.x, 3), round(v.co.y, 3), seed)) % 1000) / 1000.0)
			pts.append(c + Vector((v.co.x * size[0], v.co.y * size[1], max(v.co.z, -0.35) * size[2])) * k)
		nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
		if nrm.dot(sum(pts, Vector()) / len(pts) - c) < 0:
			pts = pts[::-1]
		g.face(obj, pts, isl, [((p - c).x + (p - c).y * 0.6, (p - c).z) for p in pts])
	bm.free()


def fence(g, a, b, height, seed, obj="Props"):
	"""a run of weathered boards with two rails behind them, a few short or missing"""
	rr = random.Random(seed)
	a, b = on_ground(a), on_ground(b)
	d = b - a
	L = d.length
	d.normalize()
	n = d.cross(UP).normalized()
	s = 0.0
	while s < L - 0.3:
		bw = 0.9 * rr.uniform(0.85, 1.1)
		if rr.random() > 0.07:
			hgt = height * rr.uniform(0.84, 1.08) * (0.65 if rr.random() < 0.08 else 1.0)
			c = a + d * (s + bw / 2) + n * rr.uniform(-0.05, 0.05)
			obox(g, obj, obj, "fence", c + UP * (hgt / 2 - 0.3), d, n, (bw - 0.1, 0.22, hgt), Part="board", Seed=rr.randrange(10**6))
		s += bw
	for z in (height * 0.3, height * 0.75):
		timber(g, a + n * 0.3 + UP * z, b + n * 0.3 + UP * z, 0.35, 0.3, n, obj=obj, sheet=obj, kind="fence", Part="rail")


def lathe(g, obj, kind, cx, cy, z0, prof, segs=16, **params):
	pc.lathe(g, obj, obj, kind, cx, cy, z0, prof, segs=segs, **params)


def barrel(g, c, R, H, seed, obj="Props", lying=None):
	"""a barrel standing on c, or lying on its side along the horizontal direction `lying`"""
	mark = g.mark()
	pc.barrel(g, obj, 0.0, 0.0, 0.0, R, H, seed=seed)
	c = Vector(c)
	if lying is None:
		g.warp_since(mark, lambda p: p + c)
		return
	dv = Vector(lying).normalized()
	side = dv.cross(UP).normalized()
	g.warp_since(mark, lambda p: c + dv * (p.z - H / 2) + side * p.x + UP * (p.y + R))


def crate(g, c, size, yaw, seed, obj="Props"):
	"""a plank crate: a box with thicker boards round each side and a diagonal brace"""
	R = Vector((math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0))
	S = UP.cross(R).normalized()
	sx, sy, sz = size
	c = Vector(c)
	obox(g, obj, obj, "crate", c + UP * (sz / 2), R, S, (sx, sy, sz), Seed=seed)
	for sgn in (-1, 1):
		f = c + S * (sgn * (sy / 2 + 0.06))
		for zz in (0.18, sz - 0.18):
			timber(g, f - R * (sx / 2) + UP * zz, f + R * (sx / 2) + UP * zz, 0.34, 0.14, S * sgn, obj=obj, sheet=obj, kind="crate_trim")
		for xx in (-sx / 2 + 0.18, sx / 2 - 0.18):
			timber(g, f + R * xx + UP * 0.1, f + R * xx + UP * (sz - 0.1), 0.34, 0.14, S * sgn, obj=obj, sheet=obj, kind="crate_trim")
		timber(g, f - R * (sx / 2 - 0.3) + UP * 0.35, f + R * (sx / 2 - 0.3) + UP * (sz - 0.35), 0.32, 0.12, S * sgn, obj=obj, sheet=obj, kind="crate_trim")


def pumpkin(g, c, r, seed, kind="pumpkin", obj="Props", ribs=10, h=0.78):
	"""a ribbed squash"""
	c = Vector(c)
	segs, rings = ribs * 4, 10
	isl = g.island(obj, kind, None, Face="skin", Seed=seed, Ribs=ribs)
	pts = []
	for j in range(rings + 1):
		phi = math.pi * j / rings
		row = []
		for i in range(segs):
			a = 2 * math.pi * i / segs
			rib = 1 - 0.09 * (1 - math.cos(ribs * a)) / 2
			rad = r * math.sin(phi) * rib
			row.append(Vector((c.x + rad * math.cos(a), c.y + rad * math.sin(a), c.z + r * h * (1 - math.cos(phi)))))
		pts.append(row)
	ctr = Vector((c.x, c.y, c.z + r * h))
	for j in range(rings):
		for i in range(segs):
			q = [pts[j][i], pts[j][(i + 1) % segs], pts[j + 1][(i + 1) % segs], pts[j + 1][i]]
			uv = [(i / segs * 6, j / rings * 2), ((i + 1) / segs * 6, j / rings * 2), ((i + 1) / segs * 6, (j + 1) / rings * 2), (i / segs * 6, (j + 1) / rings * 2)]
			if (q[1] - q[0]).cross(q[3] - q[0]).dot(sum(q, Vector()) / 4 - ctr) < 0:
				q, uv = q[::-1], uv[::-1]
			if (q[0] - q[1]).length < 1e-6 or (q[2] - q[3]).length < 1e-6:
				tri = [p for k, p in enumerate(q) if k == 0 or (p - q[k - 1]).length > 1e-6]
				tuv = [uv[k] for k, p in enumerate(q) if k == 0 or (p - q[k - 1]).length > 1e-6]
				if len(tri) >= 3:
					g.face(obj, tri[:3], isl, tuv[:3])
				continue
			g.face(obj, q, isl, uv)
	top = c.z + 2 * r * h
	sweep(g, obj, obj, "stem", [Vector((c.x, c.y, top - 0.1)), Vector((c.x + 0.08, c.y, top + 0.3)), Vector((c.x + 0.2, c.y + 0.05, top + 0.42))], 0.16, 0.16, X)


def sky_backdrop(g):
	"""a big card far behind the house facing the camera: the painter draws the reference's sky on it (blue, soft clouds)"""
	c = EYE + FWD * 420.0
	right, up = RIGHTV, UPV
	hw, hh = 420.0 * math.tan(math.atan(W_REF / 2 / F_PX)) * 1.15, 420.0 * math.tan(math.atan(H_REF / 2 / F_PX)) * 1.25
	q = [c - right * hw - up * hh, c + right * hw - up * hh, c + right * hw + up * hh, c - right * hw + up * hh]
	isl = g.island("Sky", "sky", pc.frame_of(q[0], right, up), Face="sky", W=2 * hw, H=2 * hh)
	g.face("Sky", q if (q[1] - q[0]).cross(q[3] - q[0]).dot(-FWD) > 0 else q[::-1], isl, [(0, 0), (2 * hw, 0), (2 * hw, 2 * hh), (0, 2 * hh)])


def build_env(g):
	rnd = random.Random(77)
	ground(g)
	sky_backdrop(g)
	# stepping stones on the reference's path from the door toward us, and a few by the annex
	for i, (px, py, r) in enumerate([(660, 613, 1.35), (612, 624, 1.3), (566, 634, 1.4), (704, 606, 1.1), (520, 646, 1.45), (268, 580, 1.3), (330, 578, 1.2), (262, 631, 1.5), (341, 604, 0.8), (418, 592, 1.0), (470, 662, 1.5)]):
		flagstone(g, gp(px, py), r, 900 + i, yaw=rnd.uniform(0, 40))
	rock(g, Vector((-4.85, -28.2, -0.3)), (1.5, 1.3, 2.3), 31)
	rock(g, gp(375, 612), (0.7, 0.6, 0.55), 32)
	rock(g, gp(1080, 642), (0.6, 0.5, 0.4), 33)
	fence(g, gp(108, 606), gp(300, 548), 3.4, 41)
	fence(g, gp(985, 600), gp(1092, 590), 3.6, 42)
	fence(g, gp(1095, 590), gp(1200, 584), 3.0, 43)
	post = on_ground(gp(82, 650))
	timber(g, post, post + UP * 5.2, 0.85, 0.85, -Y, obj="Props", sheet="Props", kind="fence", Part="post", bow=0.15, bow_dir=X)
	bc = px_y(432, 560, 0.6)
	crate(g, Vector((bc.x, 0.6, 0.0)), (2.4, 2.0, 1.9), 8, 51)
	bb = px_y(444, 540, 0.9)
	barrel(g, Vector((bb.x, 0.9, 1.9)), 1.15, 2.6, 52)
	crate(g, on_ground(gp(957, 600)), (3.0, 2.4, 2.3), -24, 53)
	barrel(g, on_ground(gp(1028, 606)), 1.25, 3.0, 54, lying=(0.85, -0.5, 0))
	barrel(g, on_ground(gp(1152, 598)), 1.3, 2.0, 55)
	barrel(g, on_ground(gp(30, 620)), 1.5, 1.3, 56)
	pk = px_y(650, 604, -1.3)
	pumpkin(g, Vector((pk.x, -1.3, 0.0)), 1.0, 61)
	pumpkin(g, Vector((1.3, 8.1, Z_FLOOR1 + 0.15)), 0.75, 62, kind="melon", ribs=8, h=0.82)
	lathe(g, "Props", "bucket", 1.6, 9.9, Z_FLOOR1 + 0.15, [(0.0, 0.0), (0.72, 0.0), (0.8, 0.12), (0.86, 1.9), (0.92, 2.0), (0.84, 2.0)], segs=14)
	timber(g, (1.6, -1.6, 0.0), (1.2, -0.4, 1.6), 0.7, 0.7, X, obj="Props", sheet="Props", kind="log", Part="log")
	st = on_ground(gp(1080, 640))
	lathe(g, "Props", "log", st.x, st.y, st.z - 0.1, [(0.0, 0.0), (0.8, 0.0), (0.72, 0.6), (0.0, 0.62)], segs=10)



# ---------------------------------------------------------------------------------------------------------------- foliage (the video's method)
def grass_tufts(name, spots, seed, height=(0.8, 1.6), blades=(14, 22), colours=("7c9438", "b8c25a", "e2e08e"), lean=0.6):
	"""clumps of tapering blades bending outward, vertex-coloured dark at the root to pale yellow-green at the tip, normals straight
	up so they shade like the lawn (the grass method in docs/style/grass.md)"""
	import bmesh

	r = random.Random(seed)
	bm = bmesh.new()
	col = bm.loops.layers.float_color.new("Col")
	dark, mid, light = (Vector(pc.hex_lin(h)) for h in colours)
	for sp in spots:
		c = on_ground(sp[:3]) if len(sp) == 3 else on_ground(sp[:3])
		k = sp[3] if len(sp) > 3 else 1.0
		for _ in range(r.randint(*blades)):
			a = r.uniform(0, 2 * math.pi)
			out = Vector((math.cos(a), math.sin(a), 0))
			base = c + out * r.uniform(0.0, 0.45 * k)
			hgt = r.uniform(*height) * k
			w = r.uniform(0.06, 0.11) * k
			bend = out * (lean * hgt * r.uniform(0.3, 1.0))
			side = UP.cross(out).normalized()
			segs = 4
			for back in (False, True):
				ring = []
				for j in range(segs + 1):
					t = j / segs
					ctr = base + UP * (hgt * t) + bend * (t * t)
					ww = max(w * (1 - t) ** 0.9, 0.004)
					ring.append((bm.verts.new(ctr - side * ww), bm.verts.new(ctr + side * ww), t))
				for j in range(segs):
					(a0, b0, t0), (a1, b1, t1) = ring[j], ring[j + 1]
					fv = (a1, b1, b0, a0) if back else (a0, b0, b1, a1)
					f = bm.faces.new(fv)
					for lp in f.loops:
						tt = t0 if lp.vert in (a0, b0) else t1
						cc = dark.lerp(mid, min(1.0, tt / 0.5)) if tt < 0.5 else mid.lerp(light, (tt - 0.5) / 0.5)
						lp[col] = (*cc, 1.0)
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	me.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(me.vertices))
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	obj.visible_shadow = False
	return obj


def trunk(name, base, top, r0, r1, seed, colours=("5a3c30", "8a6248")):
	"""a plain tapered trunk, vertex-coloured dark low to warmer up"""
	import bmesh

	bm = bmesh.new()
	col = bm.loops.layers.float_color.new("Col")
	a, b = Vector(base), Vector(top)
	segs, rings = 10, 6
	dark, light = Vector(pc.hex_lin(colours[0])), Vector(pc.hex_lin(colours[1]))
	verts = []
	for j in range(rings + 1):
		t = j / rings
		c = a.lerp(b, t) + Vector((0.4 * math.sin(t * 3 + seed), 0.3 * math.cos(t * 2.5 + seed), 0)) * t
		rr = r0 + (r1 - r0) * t
		verts.append([bm.verts.new(c + Vector((rr * math.cos(2 * math.pi * i / segs), rr * math.sin(2 * math.pi * i / segs), 0))) for i in range(segs)])
	for j in range(rings):
		for i in range(segs):
			f = bm.faces.new((verts[j][i], verts[j][(i + 1) % segs], verts[j + 1][(i + 1) % segs], verts[j + 1][i]))
			f.smooth = True
			for lp in f.loops:
				t = (lp.vert.co.z - a.z) / max(b.z - a.z, 1e-6)
				cc = dark.lerp(light, min(1.0, max(0.0, t)))
				lp[col] = (*cc, 1.0)
	me = bpy.data.meshes.new(name)
	bm.to_mesh(me)
	bm.free()
	obj = bpy.data.objects.new(name, me)
	bpy.context.scene.collection.objects.link(obj)
	return obj


def build_foliage():
	made = []
	rnd = random.Random(5)
	moss = ("9aa832", "cad84e", "f2f290")
	# moss on the roofs where the reference has it: a tall clump down the valley by the chimney, a fluffy one on the right ridge
	v = px_y(630, 228, 1.2)
	made += pc.blob("MossValley", (v.x, v.y, v.z + 0.3), (0.75, 0.75, 1.7), 30, 0.4, 81, moss, up_lean=0.45, cards=70, card_size=0.55)
	rdg = px_y(766, 136, RIDGE_Y)
	made += pc.blob("MossRidge", (rdg.x, rdg.y, rdg.z + 0.15), (1.2, 0.8, 0.6), 26, 0.36, 82, moss, up_lean=0.5, cards=60, card_size=0.5)
	ax = px_y(318, 452, 0.2)
	made += pc.blob("MossAnnex", (ax.x, ax.y, ax.z + 0.15), (1.0, 0.8, 0.35), 12, 0.38, 83, moss, up_lean=0.6)
	# the flower box's leafy spill
	bx = px_y(530, 515, YC - 0.8)
	made += pc.blob("BoxPlants", (bx.x, YC - 0.85, bx.z + 0.2), (1.9, 0.75, 0.75), 30, 0.4, 84, ("7aa034", "b8d24e", "e8f08a"), up_lean=0.5, cards=70, card_size=0.6)
	# trees: one dark and deep behind the annex on the left, light sunny ones behind the right of the house
	left = ("1d3b2c", "3f6e44", "86a95a")
	left = ("4a6e4c", "7a9c62", "bccc8a")
	made += pc.cloud("TreeLeft", [((-118.0, 52.0, 12.0), (6.0, 5.0, 6.5)), ((-112.0, 50.0, 16.0), (4.5, 4.0, 4.5))], 2.0, 91, ("6a8a54", "98b26c", "d2d89a"), card_tint="98b26c", cards_per=40, card_size=1.8)
	made += pc.cloud("TreeLeft2", [((-100.0, 60.0, 11.0), (5.0, 4.5, 6.0)), ((-96.0, 58.0, 15.0), (3.6, 3.4, 4.0))], 1.8, 96, ("8c8a4c", "c0b064", "e8d896"), card_tint="c0b064", cards_per=36, card_size=1.7)
	made += pc.cloud("TreeLeft3", [((-140.0, 48.0, 10.0), (6.0, 5.0, 7.0))], 2.0, 97, ("2c4838", "4e7050", "8aa678"), card_tint="4e7050", cards_per=40, card_size=1.9)
	made.append(trunk("TrunkLeft", (-116.0, 52.0, -0.5), (-116.5, 52.0, 8.0), 0.9, 0.6, 1))
	right = ("4f7a3e", "8db45a", "cfe08c")
	made += pc.cloud("TreeRight", [((-1.0, 38.0, 13.0), (4.6, 4.2, 5.2)), ((3.0, 42.0, 9.5), (4.2, 3.8, 4.4)), ((-3.0, 36.0, 17.5), (3.4, 3.0, 3.2))], 1.6, 92, ("88aa70", "b8d290", "eaf0c4"), card_tint="b8d290", cards_per=60, card_size=1.5)
	made.append(trunk("TrunkRight", (4.0, 31.0, -0.2), (3.5, 30.0, 10.0), 1.0, 0.7, 2))
	made += pc.cloud("TreeFarRight", [((60.0, 70.0, 14.0), (11.0, 9.0, 9.0)), ((75.0, 80.0, 12.0), (10.0, 8.0, 8.0))], 3.0, 93, ("6c8a5c", "9cb47a", "d0dca2"), card_tint="9ab47a", cards_per=40, card_size=2.6)
	made += pc.cloud("TreeFarLeft", [((-75.0, 55.0, 13.0), (12.0, 9.0, 9.0)), ((-95.0, 60.0, 10.0), (10.0, 8.0, 8.0))], 3.0, 94, ("2e4c3a", "5a7e54", "93ad78"), card_tint="557a50", cards_per=40, card_size=2.6)
	# a dark hedge behind the deck
	made += pc.cloud("HedgeRight", [((9.0, 15.0, 1.2), (4.0, 2.4, 2.0)), ((14.0, 16.0, 1.4), (3.6, 2.4, 2.2))], 1.2, 95, ("1c2e3c", "2e4c50", "4f7258"), card_tint="2e4a4a", cards_per=40, card_size=1.1)
	# grass: tufts along the house's foot and the fence, lusher in the sunny foreground
	spots = []
	for x0, x1, y0, y1, n, k in ((-33.5, -19.0, -3.0, -2.0, 8, 0.65), (-16.0, -8.0, -5.6, -4.7, 5, 0.55), (-7.2, 3.0, -2.6, -1.6, 5, 0.55), (0.8, 3.5, 0.0, 9.0, 6, 0.7), (-12.0, 8.0, -16.0, -6.0, 22, 0.95), (-40.0, -12.0, -14.0, -5.0, 20, 0.9), (-60.0, -35.0, -6.0, 6.0, 14, 1.0)):
		for _ in range(n):
			spots.append((rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0.0, k * rnd.uniform(0.8, 1.2)))
	made.append(grass_tufts("GrassTufts", spots, 7))
	# flowers: purple on the big rock and behind the deck, blue in the lawn, a few white stalks
	made.append(pc.flowers("FlowersRock", [Vector((-4.85 + rnd.gauss(0, 0.5), -28.2 + rnd.gauss(0, 0.4), 1.75 + rnd.random() * 0.35)) for _ in range(22)], "9a7ad0", size=0.2, seed=71))
	made.append(pc.flowers("FlowersHedge", [Vector((8.5 + rnd.gauss(0, 1.4), 13.0 + rnd.gauss(0, 0.6), 1.6 + rnd.random() * 1.2)) for _ in range(30)], "6a5ac8", size=0.3, seed=72))
	bl = on_ground(gp(510, 615))
	made.append(pc.flowers("FlowersBlue", [Vector((bl.x + rnd.gauss(0, 0.8), bl.y + rnd.gauss(0, 0.6), 0.9 + rnd.random() * 0.6)) for _ in range(16)], "8aa6e8", size=0.22, seed=73))
	for o in made:
		if o.name.endswith("Cards"):
			o["Tint"] = "c8d850" if not o.name.startswith("Box") else "b0cc4c"
		if o.name in pc.FOLIAGE_TINTS:
			o["Tint"] = pc.FOLIAGE_TINTS[o.name]
		elif "Tint" not in o.keys():
			o["Vcol"] = 1
	return made


# ---------------------------------------------------------------------------------------------------------------- build, render, export
def build():
	for o in list(bpy.data.objects):
		bpy.data.objects.remove(o)
	g = pc.Geo()
	R = define_roofs()
	build_house(g, R)
	build_env(g)
	# a smooth, low waviness over everything built: nothing ruler-true, seams stay closed (vertices at one place move together)
	pc.WOBBLE = (0.16, 7.5)
	pc.WOBBLE_OBJS = ("Walls", "Timber", "Joinery", "Stone", "RoofRB", "RoofLB", "RoofAX")
	pc.wobble(g)
	objs = pc.make_objects(g)
	print("[crooked] tile skips", SKIPS, flush=True)
	print("[crooked] objects", [(o.name, len(o.data.polygons)) for o in objs], "faces", sum(len(o.data.polygons) for o in objs), "islands", len(g.islands), flush=True)
	pc.pack_and_bake(g, objs)
	made = build_foliage()
	print("[crooked] foliage objects", len(made), "faces", sum(len(o.data.polygons) for o in made), flush=True)
	path = os.path.join(OUT, "layout.json")
	lay = json.load(open(path))
	lay["Consts"] = {"Z_PLINTH": Z_PLINTH, "Z_FLOOR1": Z_FLOOR1, "Z_PLATE": Z_PLATE, "Bricks": brick_patches(), "Moss": moss_spots()}
	json.dump(lay, open(path, "w"))
	bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "cottage.blend"))


def brick_patches():
	"""where the render has fallen off the plaster and bricks show, read off the reference: (centre, half width, half height, wall
	normal). The painter grows each into a ragged patch of running-bond bricks"""
	out = []
	for px, py, plane, val, hw, hh, n in (
		(612, 328, "x", XC1, 1.4, 1.1, (1, 0, 0)),  # the cross-wing's right wall, upper floor, left of its small window
		(652, 372, "x", XC1, 1.0, 1.3, (1, 0, 0)),  # and right of it
		(612, 445, "x", XC1, 1.2, 1.0, (1, 0, 0)),  # over its lower small window
		(752, 375, "y", 0.0, 1.4, 0.6, (0, -1, 0)),  # under the round window's right brace
		(758, 440, "y", 0.0, 1.6, 1.4, (0, -1, 0)),  # over the door's arch, right
		(826, 440, "x", 0.0, 1.6, 0.9, (1, 0, 0)),  # right wall, top
		(812, 536, "x", 0.0, 1.0, 0.9, (1, 0, 0)),  # right wall, foot by the corner
		(880, 528, "x", 0.0, 1.6, 0.9, (1, 0, 0)),  # right wall, foot by the back post
		(830, 318, "x", 0.0, 1.3, 0.8, (1, 0, 0)),  # right wall, upper floor
		(490, 245, "y", YC, 1.0, 1.4, (0, -1, 0)),  # the cross-wing's gable, left of the fan window
		(552, 455, "y", YC, 0.9, 1.3, (0, -1, 0)),  # the cross-wing, right of the flower window
		(300, 545, "y", AX_FRONT, 1.1, 1.4, (0, -1, 0)),  # annex wall, left
		(690, 196, "y", 0.6, 0.8, 0.5, (0, -1, 0)),  # dormer gable
	):
		c = px_y(px, py, val) if plane == "y" else px_x(px, py, val)
		out.append([list(c), hw, hh, list(n)])
	return out


def moss_spots():
	"""moss and lichen on the roofs (world centre, radius): in the valley by the chimney and at the right gable's ridge"""
	return [[list(px_y(632, 228, 1.5)), 2.2], [list(px_y(765, 135, RIDGE_Y)), 1.6], [list(px_y(300, 455, 0.5)), 2.0], [list(px_y(690, 270, -0.8)), 1.4]]


SKY_TOP, SKY_LOW = "6e98d8", "c0cbe6"  # the reference's sky, top and toward the horizon
SUN_DIR = (0.2, 0.68, -0.7)
SUN_ENERGY = 2.6
SUN_COLOUR = (1.0, 0.9, 0.76)  # the reference's warm afternoon light
EXPOSURE = 0.45
FILL = 0.3
FILL_COLOUR = "dfe4f2"  # the sky's fill, a little blue; the ground plane adds the warm green bounce


def render():
	tag = ARGS[1] if len(ARGS) > 1 else "clay"
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cottage.blend"))
	sc = bpy.context.scene
	if "--clay" not in ARGS:
		for obj in list(sc.collection.objects):
			if obj.type == "MESH" and os.path.exists(os.path.join(OUT, "sheets", f"{obj.name}.png")):
				obj.data.materials.clear()
				obj.data.materials.append(pc.sheet_material(obj.name))
	sky = bpy.data.objects.get("Sky")
	if sky and os.path.exists(os.path.join(OUT, "sheets", "Sky.png")):
		m = bpy.data.materials.new("SkyUnlit")
		m.use_nodes = True
		nt = m.node_tree
		for n in list(nt.nodes):
			nt.nodes.remove(n)
		o_ = nt.nodes.new("ShaderNodeOutputMaterial")
		em = nt.nodes.new("ShaderNodeEmission")
		im = nt.nodes.new("ShaderNodeTexImage")
		im.image = bpy.data.images.load(os.path.join(OUT, "sheets", "Sky.png"))
		uvn = nt.nodes.new("ShaderNodeUVMap")
		uvn.uv_map = "UVMap"
		nt.links.new(uvn.outputs["UV"], im.inputs["Vector"])
		nt.links.new(im.outputs["Color"], em.inputs["Color"])
		em.inputs["Strength"].default_value = 1.0 / (2 ** EXPOSURE)
		nt.links.new(em.outputs["Emission"], o_.inputs["Surface"])
		sky.data.materials.clear()
		sky.data.materials.append(m)
		sky.visible_shadow = False
	for obj in list(sc.collection.objects):
		if obj.type != "MESH":
			continue
		if "Tint" in obj.keys():
			obj.data.materials.clear()
			obj.data.materials.append(pc.leaf_material(obj["Tint"]))
			obj.visible_shadow = False
		elif "Vcol" in obj.keys():
			obj.data.materials.clear()
			obj.data.materials.append(pc.vcol_material())
	sc.render.engine = "BLENDER_EEVEE"
	sc.view_settings.view_transform = "Standard"
	sc.render.resolution_x, sc.render.resolution_y = W_REF, H_REF
	sc.render.resolution_percentage = 50 if "--small" in ARGS else 100
	cam = pc.camera(sc)
	for a in ARGS:
		if a.startswith("--cam="):
			# a check view: --cam=ex,ey,ez,tx,ty,tz,fov
			v = [float(t) for t in a[6:].split(",")]
			eye, tgt = Vector(v[0:3]), Vector(v[3:6])
			cam.location = eye
			cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
			cam.data.angle_y = math.radians(v[6])
	for a in ARGS:
		if a.startswith("--only="):
			keep = set(a[7:].split(","))
			for obj in list(sc.collection.objects):
				if obj.type == "MESH" and obj.name not in keep:
					obj.hide_render = True
	pc.SUN_DIR, pc.SKY_TOP, pc.SKY_LOW = SUN_DIR, SKY_TOP, SKY_LOW
	fill = FILL
	for a in ARGS:
		if a.startswith("--fill="):
			fill = float(a[7:])
	pc.lights(sc, sun_energy=SUN_ENERGY, sky_strength=fill)
	for n in sc.world.node_tree.nodes:
		if n.type == "BACKGROUND" and abs(n.inputs["Strength"].default_value - fill) < 1e-6 and not n.inputs["Color"].is_linked:
			n.inputs["Color"].default_value = (*pc.hex_lin(FILL_COLOUR), 1)
	if "--plane" in ARGS:
		ground_plane(sc)
	for attr, val in (("taa_render_samples", 48), ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8), ("use_gtao", True), ("gtao_distance", 1.2)):
		try:
			setattr(sc.eevee, attr, val)
		except (AttributeError, TypeError):
			pass
	sc.view_settings.exposure = EXPOSURE
	sun = bpy.data.objects.get("Sun")
	if sun:
		sun.data.energy = SUN_ENERGY
		sun.data.color = SUN_COLOUR
		sun.data.angle = math.radians(1.2)
		try:
			sun.data.use_shadow = True
		except AttributeError:
			pass
	if "--flat" not in ARGS:
		cam.data.dof.use_dof = True
		cam.data.dof.focus_distance = FOCUS
		cam.data.dof.aperture_fstop = 0.08  # studs are metres to Blender: a real-lens number hardly blurs at this scale
		post(sc)
	os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
	sc.render.filepath = os.path.join(OUT, "renders", f"{tag}.png")
	bpy.ops.render.render(write_still=True)
	print("[crooked] rendered", sc.render.filepath, flush=True)


def post(sc):
	"""the reference's soft bloom and warm grade, in the compositor (Blender 5 node groups, or the older scene tree)"""
	try:
		tree = bpy.data.node_groups.new("CrookedPost", "CompositorNodeTree")
		sc.compositing_node_group = tree
		rl = tree.nodes.new("CompositorNodeRLayers")
		out = tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
		go = tree.nodes.new("NodeGroupOutput")
		target = go.inputs[0]
	except Exception:
		sc.use_nodes = True
		tree = sc.node_tree
		for n in list(tree.nodes):
			tree.nodes.remove(n)
		rl = tree.nodes.new("CompositorNodeRLayers")
		target = tree.nodes.new("CompositorNodeComposite").inputs["Image"]
	glare = tree.nodes.new("CompositorNodeGlare")
	for attr, val in (("glare_type", "BLOOM"), ("threshold", 0.75), ("size", 7), ("mix", -0.55), ("quality", "HIGH")):
		try:
			setattr(glare, attr, val)
		except Exception:
			pass
	for key, val in (("Threshold", 0.75), ("Strength", 0.45), ("Size", 0.6)):
		if key in glare.inputs:
			glare.inputs[key].default_value = val
	tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
	bal = tree.nodes.new("CompositorNodeColorBalance")
	try:
		bal.correction_method = "LIFT_GAMMA_GAIN"
		bal.gain = (1.04, 1.0, 0.93)
		bal.lift = (1.02, 1.01, 1.03)
	except Exception:
		pass
	tree.links.new(glare.outputs["Image"], bal.inputs["Image"])
	tree.links.new(bal.outputs["Image"], target)
	sc.render.use_compositing = True
	print("[crooked] post", getattr(sc, "compositing_node_group", None), [n.bl_idname for n in tree.nodes], flush=True)


def ground_plane(sc):
	"""a grass plane under the house for the render (bounce light and the view's ground); the painted ground comes later"""
	me = bpy.data.meshes.new("GroundPlane")
	me.from_pydata([(-200, -200, -0.05), (200, -200, -0.05), (200, 200, -0.05), (-200, 200, -0.05)], [], [(0, 1, 2, 3)])
	obj = bpy.data.objects.new("GroundPlane", me)
	sc.collection.objects.link(obj)
	m = bpy.data.materials.new("Grass")
	m.use_nodes = True
	b = m.node_tree.nodes["Principled BSDF"]
	b.inputs["Base Color"].default_value = (*pc.hex_lin("b9c86a"), 1)
	b.inputs["Roughness"].default_value = 0.95
	me.materials.append(m)


def export():
	bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "cottage.blend"))
	info = {}
	for obj in bpy.data.objects:
		if obj.type != "MESH":
			continue
		me = obj.data
		if "Paint" in me.uv_layers:
			me.uv_layers.remove(me.uv_layers["Paint"])
		me.calc_loop_triangles()
		c = [Vector(v) for v in obj.bound_box]
		info[obj.name] = {"Bounds": [min(v.x for v in c), min(v.y for v in c), min(v.z for v in c), max(v.x for v in c), max(v.y for v in c), max(v.z for v in c)], "Tris": len(me.loop_triangles)}
	for o in bpy.data.objects:
		o.select_set(o.type == "MESH")
	bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "CrookedCottage.glb"), export_format="GLB", use_selection=True, export_materials="NONE", export_normals=True, export_apply=False, export_texcoords=True)
	json.dump(info, open(os.path.join(OUT, "export.json"), "w"), indent=1)
	print("[crooked] exported", len(info), "meshes, triangles", sum(v["Tris"] for v in info.values()), flush=True)


if __name__ == "__main__":
	os.makedirs(OUT, exist_ok=True)
	{"build": build, "render": render, "bake_ao": pc.bake_ao, "export": export}[ARGS[0]]()
