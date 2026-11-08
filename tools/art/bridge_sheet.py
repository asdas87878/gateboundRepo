"""The bridge beside the reference, for the user's review: art/kit/bridge/compare_reference.jpg from the views tools/blender/bridge_kit.py rendered. The reference stays study only.
  python tools/art/bridge_sheet.py art/kit/bridge
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "art/kit/bridge")
W = 800
H = 450
LABEL = 30
ref = Image.open("research/stylized_lesson/ref_01.png").convert("RGB")


def view(name):
	return Image.open(os.path.join(OUT, "views", name + ".png")).convert("RGB")


def fit(img):
	s = max(W / img.width, H / img.height)
	img = img.resize((int(img.width * s + 0.5), int(img.height * s + 0.5)), Image.LANCZOS)
	x, y = (img.width - W) // 2, (img.height - H) // 2
	return img.crop((x, y, x + W, y + H))


panels = [
	("Reference (study only)", ref),
	("From the riverbank (far read)", view("river")),
	("Up close, before", view("before_sharp_close")),
	("Up close, now", view("close")),
	("Leaning on the parapet", view("close_deck")),
	("The wall from nearby", view("wall_close")),
	("Walking across, player height", view("deck")),
	("Under the middle arch", view("under")),
	("Square on from the side", view("side_close")),
	("From the river", view("river_low")),
]
sheet = Image.new("RGB", (W * 2, (H + LABEL) * (len(panels) // 2)), (24, 24, 28))
draw = ImageDraw.Draw(sheet)
try:
	font = ImageFont.truetype("arialbd.ttf", 20)
except OSError:
	font = ImageFont.load_default()
for i, (label, img) in enumerate(panels):
	x, y = (i % 2) * W, (i // 2) * (H + LABEL)
	draw.text((x + 10, y + 4), label, fill=(240, 240, 235), font=font)
	sheet.paste(fit(img), (x, y + LABEL))
sheet.save(os.path.join(OUT, "compare_reference.jpg"), quality=92)
print("sheet", sheet.size)

# the same, from the Studio captures in art/kit/bridge/studio, when they exist
STUDIO = (
	("Reference (study only)", None),
	("Studio: lit side from the bank", "graded_hero"),
	("Studio: from the river, lit side", "graded_water"),
	("Studio: from the river, shaded side", "graded_shade"),
	("Studio: walking across", "graded_deck"),
	("Studio: near end, from the road", "graded_end_near"),
	("Studio: far end, from the road", "graded_end_far"),
	("Studio: far end, the notch beside the post", "slit_b"),
)
if os.path.exists(os.path.join(OUT, "studio", "graded_hero.jpeg")):
	sheet = Image.new("RGB", (W * 2, (H + LABEL) * (len(STUDIO) // 2)), (24, 24, 28))
	draw = ImageDraw.Draw(sheet)
	for i, (label, name) in enumerate(STUDIO):
		img = ref if name is None else Image.open(os.path.join(OUT, "studio", name + ".jpeg")).convert("RGB")
		x, y = (i % 2) * W, (i // 2) * (H + LABEL)
		draw.text((x + 10, y + 4), label, fill=(240, 240, 235), font=font)
		sheet.paste(fit(img), (x, y + LABEL))
	sheet.save(os.path.join(OUT, "compare_studio.jpg"), quality=92)
	print("studio sheet", sheet.size)
