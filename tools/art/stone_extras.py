"""Shared by tools/art/house_stone.py and bridgehouse_stone.py: a chimney laid from the stone bridge's parts, and moss painted on stones."""
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d


def _unit(v):
	v = np.array(v, float)
	return v / (np.linalg.norm(v) + 1e-9)


def chimney(b, C, card, block, piece, sections):
	"""sections: (centre x, centre z, half x, half z, y0, y1) from the bottom up. Every section's top carries a band of stone, the last a heavy cap"""
	for i, (cx, cz, hx, hz, y0, y1) in enumerate(sections):
		clip = [(np.array((0, y0, 0.0)), np.array((0, 1.0, 0)))]
		for o, U, N, u0, u1 in (
			((0, 0, cz + hz), (1, 0, 0), (0, 0, 1), cx - hx, cx + hx),
			((0, 0, cz - hz), (-1, 0, 0), (0, 0, -1), -(cx + hx), -(cx - hx)),
			((cx + hx, 0, 0), (0, 0, -1), (1, 0, 0), -(cz + hz), -(cz - hz)),
			((cx - hx, 0, 0), (0, 0, 1), (-1, 0, 0), cz - hz, cz + hz),
		):
			o, U, N = np.array(o, float), np.array(U, float), np.array(N, float)
			b.courses(lambda _m: piece, o, U, N, u0, u1, y1, y0 - 0.5, lambda _u: 0.0, lambda w, y, u, k: card(w, y), lambda *_a: clip, b=0.14, depth=0.11)
			q = [o + U * u0 + np.array((0, y0, 0)) - N * 0.03, o + U * u1 + np.array((0, y0, 0)) - N * 0.03, o + U * u1 + np.array((0, y1, 0)) - N * 0.03, o + U * u0 + np.array((0, y1, 0)) - N * 0.03]
			b.plain_quad(piece, q, N, C["mortar"])
		last = i == len(sections) - 1
		if last:
			block(cx, y1 + 0.36, cz, hx + 0.34, 0.36, hz + 0.34, C["block"])
		else:
			block(cx, y1 + 0.08, cz, hx + 0.16, 0.24, hz + 0.16, C["block"])


def paint_moss(img, x, y, w, h, cover, rng, ss=2):
	"""moss painted on a stone's place on the sheet, rising from its lower edge to a torn top: cover is how much of it. Muted, with a dark contact line above the moss so it sits on the stone"""
	H, W = h * ss, w * ss
	part = img[y * ss : (y + h) * ss, x * ss : (x + w) * ss]
	wander = gaussian_filter1d(rng.normal(0, 1, W), max(W * 0.05, 2))
	wander = wander / (np.abs(wander).max() + 1e-6)
	fine = gaussian_filter1d(rng.normal(0, 1, W), max(W * 0.012, 1))
	fine = fine / (np.abs(fine).max() + 1e-6)
	top = (1 - cover + wander * 0.16 + fine * 0.05)[None, :] * H
	yy = np.arange(H, dtype=np.float32)[:, None]
	m = gaussian_filter(((yy > top) * 1.0).astype(np.float32), 0.8)
	lip = gaussian_filter(((yy > top - H * 0.05) * 1.0).astype(np.float32), 1.2) * (1 - m)
	spots = gaussian_filter(rng.random((H, W)).astype(np.float32), max(H * 0.05, 1.5))
	spots = np.clip((spots - spots.mean()) / (spots.std() + 1e-6), -1, 1)[..., None]
	moss_colour = MOSS_DARK + (MOSS_LIGHT - MOSS_DARK) * (spots * 0.5 + 0.5) ** 1.4
	# lit towards its top edge, darker at the foot
	moss_colour = moss_colour * (1.06 - 0.22 * np.clip((yy - top) / (H * 0.6), 0, 1))[..., None]
	part[:] = part * (1 - lip[..., None] * 0.28) + part * 0.72 * lip[..., None] * 0.28
	part[:] = part * (1 - m[..., None]) + moss_colour * m[..., None]


MOSS_DARK = np.array((72, 108, 78), float)
MOSS_LIGHT = np.array((122, 158, 92), float)


# ---- multi-coloured dark brick, placed to frame the house
PALETTES = {
	"Rich": dict(slate=(0.62, 0.64, 0.72), slate_dark=(0.46, 0.47, 0.56), frame=(0.4, 0.35, 0.44), umber=(0.68, 0.54, 0.44), rust=(0.76, 0.46, 0.34), blue=(0.46, 0.58, 0.76), olive=(0.6, 0.62, 0.4), cap=(0.58, 0.52, 0.52)),
	"Muted": dict(slate=(0.58, 0.58, 0.62), slate_dark=(0.44, 0.43, 0.48), frame=(0.38, 0.34, 0.38), umber=(0.6, 0.52, 0.46), rust=(0.64, 0.48, 0.4), blue=(0.5, 0.56, 0.64), olive=(0.56, 0.56, 0.44), cap=(0.54, 0.5, 0.48)),
}


def tint(sheet, x, y, w, h, colour, ss=2):
	sheet.img[y * ss : (y + h) * ss, x * ss : (x + w) * ss] *= np.array(colour, np.float32)


def tint_card(sheet, card, colour, ss=2):
	tint(sheet, card.x, card.y, card.W, card.H, colour, ss)


class Multi:
	"""which brick goes where. The frame is dark: corners, door sides, the foot. Each wall has two accent colours, gathered in clusters, with calm stretches of slate between"""

	def __init__(self, sheet, Card, widths, course, b, tx, palette, rng, ss=2):
		self.rng, self.widths, self.p = rng, widths, palette
		self.cards = {}
		for name in ("slate", "slate_dark", "frame", "umber", "rust", "blue", "olive"):
			for w in widths:
				c = Card(sheet, f"multi_{name}_{w}", w, course, b, tx, "mid/base", rng)
				tint_card(sheet, c, palette[name], ss)
				self.cards[(name, w)] = c
		self.new_wall()

	def new_wall(self):
		r = self.rng
		self.ph = r.uniform(0, 6.3, 2)
		self.accents = list(r.choice(("umber", "rust", "blue", "olive"), 2, replace=False))

	def pick(self, w, y, u=None, near_end=None, foot_y=1.2):
		ws = min(self.widths, key=lambda v: abs(v - w))
		r = self.rng
		if near_end is not None and near_end < 1.5 + r.uniform(-0.3, 0.5):
			return self.cards[("frame", ws)]
		if y < foot_y and r.random() < 0.7:
			return self.cards[("slate_dark" if r.random() < 0.7 else "frame", ws)]
		if u is None:
			name = "slate" if r.random() < 0.6 else "slate_dark" if r.random() < 0.6 else self.accents[0]
			return self.cards[(name, ws)]
		f = np.sin(u * 0.62 + self.ph[0]) + 0.55 * np.sin(u * 1.45 + self.ph[1])
		if f > 0.8 and r.random() < 0.72:
			return self.cards[(self.accents[0], ws)]
		if f < -0.8 and r.random() < 0.72:
			return self.cards[(self.accents[1], ws)]
		return self.cards[("slate_dark" if r.random() < 0.3 else "slate", ws)]
