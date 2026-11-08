"""2D noise for terrain and skies (numpy only, so it runs in Blender's Python too): value noise on any coordinates,
fractal sums with each octave turned, and ridged noise for mountain crests."""

import math

import numpy as np

_TABLES = {}


def table(seed, n=1024):
	if (seed, n) not in _TABLES:
		rs = np.random.RandomState(seed)
		p = rs.permutation(n)
		_TABLES[(seed, n)] = (np.concatenate([p, p]), rs.uniform(-1, 1, n).astype(np.float32))
	return _TABLES[(seed, n)]


def vnoise(x, y, tab):
	"""value noise (lattice hashed through a permutation table), quintic smoothing, -1..1"""
	perm, vals = tab
	m = len(vals) - 1  # table size is a power of two: & m wraps negatives too
	x0, y0 = np.floor(x), np.floor(y)
	fx, fy = (x - x0).astype(np.float32), (y - y0).astype(np.float32)
	xi, yi = x0.astype(np.int32) & m, y0.astype(np.int32) & m
	xj, yj = (xi + 1) & m, (yi + 1) & m

	def g(ix, iy):
		return vals[perm[perm[ix] + iy]]

	sx = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
	sy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
	a = g(xi, yi) * (1 - sx) + g(xj, yi) * sx
	b = g(xi, yj) * (1 - sx) + g(xj, yj) * sx
	return a * (1 - sy) + b * sy


def fbm(x, y, seed, octaves=5, gain=0.5, fade=None):
	"""fractal value noise, each octave turned so the lattice doesn't show; fade(o) scales octave o per pixel (to drop
	fine octaves where they would only alias)"""
	out = np.zeros(np.shape(x), np.float32)
	norm = 0.0
	amp, freq = 1.0, 1.0
	for o in range(octaves):
		a = 0.9 + o * 1.7
		ca, sa = math.cos(a), math.sin(a)
		u, v = (x * ca - y * sa) * freq + o * 31.7, (x * sa + y * ca) * freq - o * 17.3
		w = amp if fade is None else amp * fade(o)
		out += vnoise(u, v, table(seed + o)) * w
		norm += amp
		amp *= gain
		freq *= 2.0
	return out / norm


def ridged(x, y, seed, octaves=5, gain=0.5, sharp=2.0, warp=0.0):
	"""ridged fractal noise, 0..1: sharp crests where the noise crosses zero, each octave weighted by the one before so
	detail gathers on the ridges (mountain ranges, not egg crates). warp bends the coordinates for less regular ridges."""
	if warp:
		wx = fbm(x + 5.2, y + 1.3, seed + 200, 3) * warp
		wy = fbm(x - 7.1, y + 3.7, seed + 300, 3) * warp
		x, y = x + wx, y + wy
	out = np.zeros(np.shape(x), np.float32)
	weight = np.ones(np.shape(x), np.float32)
	norm = 0.0
	amp, freq = 1.0, 1.0
	for o in range(octaves):
		a = 0.4 + o * 1.3
		ca, sa = math.cos(a), math.sin(a)
		u, v = (x * ca - y * sa) * freq + o * 11.3, (x * sa + y * ca) * freq - o * 23.9
		r = (1 - np.abs(vnoise(u, v, table(seed + o)))) ** sharp
		r *= weight
		weight = np.clip(r * 1.5, 0, 1)
		out += r * amp
		norm += amp
		amp *= gain
		freq *= 2.0
	return out / norm
