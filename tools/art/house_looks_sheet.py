"""The colour looks side by side, one row per look: art/kit/looks/looks_sheet.jpg"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
L = os.path.join(ROOT, "art", "kit", "looks")
font = ImageFont.truetype("arial.ttf", 26)
looks = json.load(open(os.path.join(L, "looks.json")))
H = 720
sheet = Image.new("RGB", (1200 + 760 + 10, (H + 10) * len(looks) - 10), (24, 24, 30))
for i, look in enumerate(looks):
	y = i * (H + 10)
	sheet.paste(Image.open(os.path.join(L, look, "pair.png")).convert("RGB"), (0, y))
	sheet.paste(Image.open(os.path.join(L, look, "close.png")).convert("RGB"), (1210, y))
	d = ImageDraw.Draw(sheet)
	label = f"{i + 1}. " + look.replace("_", " ")
	box = d.textbbox((14, y + 10), label, font=font)
	d.rectangle((box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4), fill=(32, 30, 40))
	d.text((14, y + 10), label, font=font, fill=(240, 234, 220))
sheet.save(os.path.join(L, "looks_sheet.jpg"), quality=90)
print(sheet.size)
