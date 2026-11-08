"""Colour looks for the houses, tried over the finished sheets: shapes and paint stay exactly as they are, only colour moves, and the windows can be repainted. Rects come from each kit.json.
Writes art/kit/looks/<look>/<House>_<Sheet>.png. Blender then renders each look: tools/blender/house_looks.py, sheet: tools/art/house_looks_sheet.py.

  python tools/art/house_looks.py [look names; all by default]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HOUSES = {"Cottage": "cottage", "Townhouse": "townhouse", "Farmhouse": "farmhouse", "Bridgehouse": "bridgehouse", "Inn": "inn", "Mill": "mill", "Smithy": "smithy", "Clocktower": "clocktower", "Manor": "manor", "Terrace": "terrace", "Hut": "hut", "Tattered": "tattered"}
ROOF_OF = {"Townhouse": "slate", "Farmhouse": "thatch", "Smithy": "slate", "Clocktower": "slate", "Terrace": "slate", "Hut": "thatch"}
OVERRIDE = {"Tattered": dict(glass="dark", wood=(0, 0.62, 0.9, 1.05), sage=(0, 0.45, 0.85, 1.05), plaster=(4, 0.62, 0.92, 1.0), terracotta=(0, 0.72, 0.86, 1.05))}  # weathered: greyed and tired  # the rest are terracotta

# per material: hue turn in degrees, saturation gain, value gain, gamma on value (under 1 lifts the shadows)
KEEP = (0, 1, 1, 1)
LOOKS = {
	"current": dict(),
	"bright_windows": dict(glass="sky"),
	"warm_windows": dict(glass="glow"),
	"ghibli_summer": dict(glass="sky", wood=(-2, 1.16, 1.05, 0.95), sage=(14, 1.3, 1.06, 0.95), plaster=(2, 0.82, 1.05, 0.9), stone=(4, 1.2, 1.06, 0.92), terracotta=(2, 1.22, 1.08, 0.94), slate=(0, 1.3, 1.12, 0.92)),
	"ghibli_soft": dict(glass="sky", wood=(2, 0.92, 1.1, 0.82), sage=(34, 1.05, 1.1, 0.82), plaster=(-4, 0.75, 1.06, 0.82), stone=(-6, 1.1, 1.12, 0.8), terracotta=(6, 0.95, 1.12, 0.82), slate=(-6, 1.05, 1.22, 0.8)),
	# the user's pick: summer, with the soft look's wood, and a quieter reflection in the same sky colour
	"chosen": dict(glass="sky_soft", wood=(2, 0.92, 1.05, 0.85), sage=(14, 1.3, 1.06, 0.95), plaster=(2, 0.82, 1.05, 0.9), stone=(4, 1.2, 1.06, 0.92), terracotta=(2, 1.22, 1.08, 0.94), slate=(0, 1.3, 1.12, 0.92), thatch=(0, 0.92, 1.0, 1.0)),
	"storybook_bold": dict(glass="cartoon", wood=(-4, 1.3, 0.86, 1.1), sage=(42, 1.7, 0.98, 1.05), plaster=(0, 0.62, 1.1, 0.85), stone=(-4, 1.15, 0.98, 1.05), terracotta=(0, 1.42, 1.04, 1.08), slate=(0, 1.55, 1.05, 1.05)),
}


# variations on the chosen look: base = the modelled stone (hue, saturation, value, gamma), base_tint multiplies it, so moss stays green
_C = LOOKS["chosen"]
_DARK_COOL = dict(base=(0, 1.15, 0.66, 1.25))
_DARK_WARM = dict(base=(0, 0.9, 0.68, 1.2), base_tint=(1.02, 0.92, 0.8))
_OLD_WOOD = (0, 0.62, 0.9, 1.05)
LOOKS.update({
	"1_current": dict(_C),
	"2_dark_cool_stone": {**_C, **_DARK_COOL},
	"3_dark_warm_stone": {**_C, **_DARK_WARM},
	"4_walnut_wood": {**_C, **_DARK_COOL, "wood": (-4, 1.1, 0.78, 1.15)},
	"5_weathered_wood": {**_C, **_DARK_WARM, "wood": _OLD_WOOD},
	"6_old_town": {**_C, **_DARK_WARM, "wood": _OLD_WOOD, "sage": (0, 0.7, 0.9, 1.0), "plaster": (4, 0.62, 0.92, 1.0), "terracotta": (0, 0.72, 0.86, 1.05), "slate": (0, 0.8, 0.9, 1.05), "thatch": (0, 0.85, 0.95, 1.0)},
	"8_rich_brick": dict(_C),
	"9_muted_brick": dict(_C),
	"10_muted_brick_old_town": {**_C, "wood": _OLD_WOOD, "sage": (0, 0.7, 0.9, 1.0), "plaster": (4, 0.62, 0.92, 1.0), "terracotta": (0, 0.72, 0.86, 1.05), "slate": (0, 0.8, 0.9, 1.05), "thatch": (0, 0.85, 0.95, 1.0)},
	"7_golden_roofs": {**_C, **_DARK_COOL, "terracotta": (20, 0.8, 1.14, 0.9), "slate": (0, 1.0, 1.0, 1.0)},
})
# the approved dark warm stone, corrected so it reads the same under the place's lighting (a low sun and a blue sky) as it does in Blender.
# Measured by matched views, art/kit/houses/studio/. "studio" runs after the look, per material: (hue, sat, value, gamma) and a warm tint in linear light, full on the light paint, none on the darks, so the cold streaks stay cold
LOOKS["frame_test"] = None  # filled below: studio_match, unchanged, for a test build's sheets
LOOKS["studio_match"] = {
	**LOOKS["3_dark_warm_stone"],
	"studio": {
		"plaster": ((0, 1, 1.06, 0.9), (1.0, 0.9, 0.74)),
		"base": ((0, 1, 1.08, 0.94), (1.05, 1.0, 0.9)),
		"wood": ((0, 1, 1.1, 0.95), None),
		"sage": ((-14, 0.8, 1.08, 1.0), None),
		"glass": ((0, 0.72, 1.12, 1.0), None),
		"slate": ((0, 0.8, 1.0, 1.0), None),
		"terracotta": ((0, 1, 1.06, 1.0), None),
	},
}

LOOKS["frame_test"] = LOOKS["studio_match"]


def regrade(rgb, m):
	"""rgb uint8 array, m = (hue turn, sat gain, value gain, gamma)"""
	if m == KEEP:
		return rgb
	hsv = np.array(Image.fromarray(rgb).convert("HSV"), float)
	hsv[..., 0] = (hsv[..., 0] + m[0] / 360 * 255) % 255
	hsv[..., 1] = np.clip(hsv[..., 1] * m[1], 0, 255)
	v = hsv[..., 2] / 255
	hsv[..., 2] = np.clip(v ** m[3] * m[2], 0, 1) * 255
	return np.array(Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB"))


def warm(rgb, tint):
	"""tints in linear light, in proportion to how light the paint is"""
	lin = (rgb / 255.0) ** 2.2
	lum = lin @ np.array((0.2126, 0.7152, 0.0722))
	w = np.clip((lum - 0.12) / 0.4, 0, 1)[..., None]
	w = w * w * (3 - 2 * w)
	return (np.clip(lin * (1 + (np.array(tint) - 1) * w), 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def stroke_band(draw, w, h, x, y, length, half, tilt, colour):
	draw.polygon([(x, y), (x + length, y + length * tilt), (x + length, y + length * tilt + half * 2), (x, y + half * 2)], fill=colour)


def glass(style, w, h, rng):
	"""one window's glass, painted at twice size. Flat clean shapes: bright panes, no fried egg"""
	W, H = w * 2, h * 2
	yy = (np.arange(H) / H)[:, None, None]
	if style == "dark":
		# dirty glass with nothing behind it
		img = np.tile(np.array((66, 74, 92), float) * (1 - yy) + np.array((40, 42, 58), float) * yy, (1, W, 1))
	elif style == "sky_soft":
		# the same sky, with a reflection that is a soft, dim cloud shape: its own place and size on every window, and on some almost nothing
		img = np.tile(np.array((122, 186, 226), float) * (1 - yy) + np.array((70, 122, 186), float) * yy, (1, W, 1))
		mask = Image.new("L", (W, H), 0)
		d = ImageDraw.Draw(mask)
		left = rng.random() < 0.5
		cx = W * (rng.uniform(0.12, 0.42) if left else rng.uniform(0.58, 0.88))
		cy = H * rng.uniform(0.18, 0.46)
		for _ in range(int(rng.integers(3, 6))):
			rx, ry = W * rng.uniform(0.07, 0.2), H * rng.uniform(0.04, 0.1)
			x, y = cx + W * rng.uniform(-0.17, 0.17), cy + H * rng.uniform(-0.05, 0.05)
			d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255)
		m = gaussian_filter(np.array(mask, np.float32) / 255, max(W, H) * 0.022)[..., None]
		strength = rng.choice((0.1, 0.31, 0.41, 0.5), p=(0.2, 0.3, 0.3, 0.2))
		img = img * (1 - m * strength) + np.array((204, 228, 240)) * m * strength
		low = np.clip((yy - 0.8) / 0.2, 0, 1) ** 1.2
		img = img * (1 - low * 0.35) + np.array((236, 204, 164)) * low * 0.35
		top = np.clip((0.14 - yy) / 0.14, 0, 1)
		img = img * (1 - top * 0.45) + np.array((54, 66, 112)) * top * 0.45
	elif style == "sky":
		# a clear bright sky reflection: pale blue at the top falling to deeper blue, a warm hint low down
		img = np.array((122, 186, 226), float) * (1 - yy) + np.array((70, 122, 186), float) * yy
		img = np.tile(img, (1, W, 1))
		pil = Image.fromarray(img.astype(np.uint8))
		d = ImageDraw.Draw(pil)
		for fx, fw in ((0.08, 0.26), (0.46, 0.12)):
			d.polygon([(W * (fx + 0.22), 0), (W * (fx + 0.22 + fw), 0), (W * (fx + fw - 0.08), H), (W * (fx - 0.08), H)], fill=(198, 232, 244))
		img = np.array(pil, float)
		img = img * (1 - 0.0) + 0
		low = np.clip((yy - 0.78) / 0.22, 0, 1) ** 1.2
		img = img * (1 - low * 0.55) + np.array((240, 200, 150)) * low * 0.55
		top = np.clip((0.14 - yy) / 0.14, 0, 1)
		img = img * (1 - top * 0.45) + np.array((54, 66, 112)) * top * 0.45
	elif style == "glow":
		# warm light from inside, the classic cosy village window
		img = np.tile(np.array((252, 226, 150), float) * (1 - yy) + np.array((244, 176, 92), float) * yy, (1, W, 1))
		pil = Image.fromarray(img.astype(np.uint8))
		d = ImageDraw.Draw(pil)
		d.polygon([(W * 0.55, 0), (W * 0.85, 0), (W * 0.62, H), (W * 0.32, H)], fill=(255, 242, 190))
		img = np.array(pil, float)
		top = np.clip((0.2 - yy) / 0.2, 0, 1)
		img = img * (1 - top * 0.5) + np.array((150, 84, 84)) * top * 0.5
	else:
		# a cartoon pane: one flat teal blue, two crisp white glints
		img = np.tile(np.array((58, 138, 190), float) * (1 - yy) + np.array((30, 90, 150), float) * yy, (1, W, 1))
		pil = Image.fromarray(img.astype(np.uint8))
		d = ImageDraw.Draw(pil)
		d.polygon([(W * 0.2, 0), (W * 0.42, 0), (W * 0.14, H * 0.6), (W * -0.08, H * 0.6)], fill=(232, 246, 250))
		d.polygon([(W * 0.5, 0), (W * 0.56, 0), (W * 0.28, H * 0.6), (W * 0.22, H * 0.6)], fill=(232, 246, 250))
		img = np.array(pil, float)
		top = np.clip((0.12 - yy) / 0.12, 0, 1)
		img = img * (1 - top * 0.55) + np.array((26, 42, 84)) * top * 0.55
	img = gaussian_filter(img, (0.8, 0.8, 0))
	return np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS))


def mask_rects(shape, rects):
	m = np.zeros(shape[:2], bool)
	for x, y, w, h in rects:
		m[y : y + h, x : x + w] = True
	return m


def run_look(name, look, house, folder, rects, rng):
	out = os.path.join(ROOT, "art", "kit", "looks", name)
	os.makedirs(out, exist_ok=True)
	src = os.path.join(ROOT, "art", "kit", os.environ.get("LOOK_SRC_" + house.upper(), folder))  # a test build of one house can be graded from its own folder
	own = name == "chosen" or name[0].isdigit()  # the tattered house keeps its own tired colours through the variations
	get = lambda k: {**look, **OVERRIDE.get(house, {})}.get(k, KEEP) if own else look.get(k, KEEP)
	sheet = lambda s: np.array(Image.open(os.path.join(src, f"{house}_{s}.png")).convert("RGB"))

	def finish(img, key):
		s = look.get("studio", {}).get(key)
		if not s:
			return img
		img = regrade(img, s[0])
		return warm(img, s[1]) if s[1] else img

	roof_key = ROOF_OF.get(house, "terracotta")
	# frame
	a = sheet("Frame")
	keep = mask_rects(a.shape, rects["frame_other"])
	g = finish(regrade(a, get("wood")), "wood")
	roof_m = get(roof_key)
	a2 = np.where(keep[..., None], finish(regrade(a, roof_m), roof_key), g)
	Image.fromarray(a2).save(os.path.join(out, f"{house}_Frame.png"))
	# joinery: wood, sage, glass
	a = sheet("Joinery")
	wood, sage = finish(regrade(a, get("wood")), "wood"), finish(regrade(a, get("sage")), "sage")
	sage_m = mask_rects(a.shape, rects["sage"])
	keep = mask_rects(a.shape, rects["joinery_other"])
	b = np.where(sage_m[..., None], sage, wood)
	b = np.where(keep[..., None], a, b)
	style = OVERRIDE.get(house, {}).get("glass", look.get("glass")) if own else look.get("glass")
	if style:
		for x, y, w, h in rects["glass"]:
			b[y : y + h, x : x + w] = finish(glass(style, w, h, rng), "glass")
	Image.fromarray(b).save(os.path.join(out, f"{house}_Joinery.png"))
	# walls: plaster and stone
	a = sheet("Walls")
	st = mask_rects(a.shape, rects["stone"])
	plaster = regrade(a, get("plaster"))
	if look.get("plaster_tint"):
		plaster = np.clip(plaster * np.array(look["plaster_tint"]), 0, 255).astype(np.uint8)
	plaster = finish(plaster, "plaster")
	Image.fromarray(np.where(st[..., None], regrade(a, get("stone")), plaster)).save(os.path.join(out, f"{house}_Walls.png"))
	# the modelled stone
	if os.path.exists(os.path.join(src, f"{house}_Stone.png")):
		st_img = regrade(sheet("Stone"), get("base"))
		if look.get("base_tint"):
			st_img = np.clip(st_img * np.array(look["base_tint"]), 0, 255).astype(np.uint8)
		Image.fromarray(finish(st_img, "base")).save(os.path.join(out, f"{house}_Stone.png"))
	# roof
	Image.fromarray(finish(regrade(sheet("Roof"), roof_m), roof_key)).save(os.path.join(out, f"{house}_Roof.png"))


ONLY = sys.argv[1:] or list(LOOKS)


def main():
	rng = np.random.default_rng(5)
	only_houses = os.environ.get("LOOK_HOUSES")
	for house, folder in HOUSES.items():
		if only_houses and house not in only_houses.split(","):
			continue
		rects = json.load(open(os.path.join(ROOT, "art", "kit", os.environ.get("LOOK_SRC_" + house.upper(), folder), "kit.json")))["Rects"]
		for name, look in LOOKS.items():
			if name in ONLY:
				run_look(name, look, house, folder, rects, rng)
	json.dump(ONLY, open(os.path.join(ROOT, "art", "kit", "looks", "looks.json"), "w"))
	print("looks:", ONLY)


main()
