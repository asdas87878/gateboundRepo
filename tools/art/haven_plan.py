"""Draw the Haven's composition from above and from the side: art/haven/composition/plan.png.

Plain circles at real sizes, with walking times, read from art/haven/layout.json. The Lands are far too far
away to fit at scale, so they sit on an outer band at their true bearings, with their real distance written on.
Run with system Python: python tools/art/haven_plan.py
"""

import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
S = json.load(open(os.path.join(ROOT, "art", "haven", "layout.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "art", "haven", "composition", "plan.png")

W, H = 1800, 1500
BG = (236, 240, 244)
INK = (40, 44, 54)
SOFT = (118, 124, 136)
GRASS = (150, 196, 128)
YOURS = (120, 196, 96)
STONE = (206, 202, 192)
TOWER = (158, 152, 142)
WOOD = (150, 108, 76)
WATER = (116, 184, 224)
HOUSE = (196, 96, 72)
GLOW = (64, 196, 214)


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def seconds(studs):
    return studs / S["WalkSpeed"]


def bearing_xy(bearing, distance):
    a = math.radians(bearing)
    return math.sin(a) * distance, math.cos(a) * distance


image = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(image)

# ---- plan: 1 stud = SCALE pixels, north up
SCALE = 1.02
CX, CY = 640, 760


def P(x, y):
    return CX + x * SCALE, CY - y * SCALE


def circle(x, y, r, fill=None, outline=None, width=2):
    px, py = P(x, y)
    r *= SCALE
    d.ellipse((px - r, py - r, px + r, py + r), fill=fill, outline=outline, width=width)


def label(x, y, text, size=19, fill=INK, bold=False, anchor="mm"):
    d.text((x, y), text, font=font(size, bold), fill=fill, anchor=anchor)


d.text((36, 26), "The Haven: composition from above", font=font(34, True), fill=INK)
for k, line in enumerate(("Circles at real size.", f"Walking: {S['WalkSpeed']} studs a second.", f"A player is {S['Player']} studs tall.")):
    d.text((36, 72 + k * 24), line, font=font(18), fill=SOFT)

M = S["Main"]
Pl = S["Plots"]
A = S["Arches"]

# the themes, off scale, on an outer band at their true bearings, each with its five Lands
BAND = 590
for t, theme in enumerate(S["Themes"]):
    x, y = bearing_xy(theme["Bearing"], BAND)
    x0, y0 = bearing_xy(theme["Bearing"], A["Radius"])
    ax0, ay0 = P(x0, y0)
    ax1, ay1 = P(x, y)
    group = S["Lands"][theme["Lands"][0] - 1 : theme["Lands"][1]]
    is_open = group[0].get("Open")
    d.line((ax0, ay0, ax1, ay1), fill=(160, 214, 224) if is_open else (196, 200, 208), width=4 if is_open else 2)
    circle(x, y, 92, fill=tuple(int(c * 255) for c in group[0]["Colour"]), outline=INK)
    px, py = P(x, y)
    tone = (40, 44, 54) if sum(group[0]["Colour"]) > 2.2 else (255, 255, 255)
    label(px, py - 44, theme["Name"], 17, tone, True)
    label(px, py - 24, f"{theme['Kind']}, Lands {theme['Lands'][0]}-{theme['Lands'][1]}", 13, tone)
    near, far = min(l["Distance"] for l in group), max(l["Distance"] for l in group)
    label(px, py - 8, f"{near} to {far} away", 13, tone)
    for j, land in enumerate(group):
        dx = px + (j - 2) * 30
        dy = py + 24
        fill = tuple(int(c * 255) for c in land["Colour"])
        d.ellipse((dx - 13, dy - 13, dx + 13, dy + 13), fill=fill, outline=INK)
        label(dx, dy, str(land["Number"]), 12, (40, 44, 54) if sum(land["Colour"]) > 1.5 else (255, 255, 255), True)

# bridges under the plots
for b in Pl["Bearings"]:
    x0, y0 = bearing_xy(b, M["Radius"])
    x1, y1 = bearing_xy(b, Pl["Ring"] - Pl["Radius"])
    ax, ay = P(x0, y0)
    bx, by = P(x1, y1)
    d.line((ax, ay, bx, by), fill=WOOD, width=max(3, int(S["BridgeWidth"] * SCALE)))

# main island
circle(0, 0, M["Radius"], fill=GRASS, outline=INK)

# promenade band along the north rim
steps = 40
outer = [P(*bearing_xy(-74 + 148 * k / steps, 176)) for k in range(steps + 1)]
inner = [P(*bearing_xy(74 - 148 * k / steps, 120)) for k in range(steps + 1)]
d.polygon(outer + inner, fill=STONE)

# stream
x0, y0 = bearing_xy(S["Stream"]["Bearing"], S["Stream"]["From"])
x1, y1 = bearing_xy(S["Stream"]["Bearing"], M["Radius"])
ax, ay = P(x0, y0)
bx, by = P(x1, y1)
d.line((ax, ay, bx, by), fill=WATER, width=int(S["Stream"]["Width"] * SCALE))

# plaza and tower
circle(0, 0, M["Plaza"]["Radius"], fill=STONE, outline=INK)
circle(0, 0, S["Tower"]["Tiers"][0][0], fill=TOWER, outline=INK)
label(CX, CY - 6, "The Climb", 16, (255, 255, 255), True)
label(CX, CY + 13, "tower", 14, (255, 255, 255))

# arches, each on the line to its Land
for i, b in enumerate(A["Bearings"]):
    x, y = bearing_xy(b, A["Radius"])
    half = A["Width"] / 2 + A["Post"]
    tx, ty = math.cos(math.radians(b)) * half, -math.sin(math.radians(b)) * half
    ax, ay = P(x - tx, y - ty)
    bx, by = P(x + tx, y + ty)
    open_land = S["Lands"][[l["Bearing"] for l in S["Lands"]].index(b)].get("Open")
    d.line((ax, ay, bx, by), fill=GLOW if open_land else INK, width=7)

# market stalls
for b in S["Market"]["Bearings"]:
    x, y = bearing_xy(b, S["Market"]["Radius"])
    circle(x, y, S["Market"]["Stall"], fill=(214, 176, 112), outline=INK)
x, y = bearing_xy(180, S["Market"]["Radius"])
label(P(x, y)[0], P(x, y)[1] - 40, "market", 15)

# plots, with the building spots of each (the same spots on every plot)
for i, b in enumerate(Pl["Bearings"]):
    x, y = bearing_xy(b, Pl["Ring"])
    yours = b == Pl["Yours"]
    circle(x, y, Pl["Radius"], fill=YOURS if yours else GRASS, outline=INK, width=4 if yours else 2)
    hx, hy = bearing_xy(b, Pl["Ring"] + 20)
    circle(hx, hy, Pl["CentreRadius"], outline=(70, 110, 60), width=2)
    for k in range(Pl["Slots"]):
        a = math.radians(b + 180 + 66 + k * (228 / (Pl["Slots"] - 1)))
        sx, sy = x + math.sin(a) * Pl["SlotRing"], y + math.cos(a) * Pl["SlotRing"]
        circle(sx, sy, Pl["SlotRadius"], outline=(70, 110, 60), width=2)
    h = Pl["Heights"][i]
    px, py = P(*bearing_xy(b, Pl["Ring"] + Pl["Radius"] + 20))
    if yours:
        label(px, py, f"YOUR PLOT, height {h:+d}", 17, INK, True)
    elif abs(math.sin(math.radians(b))) > 0.8:
        px, py = P(*bearing_xy(b, Pl["Ring"] + Pl["Radius"] + 4))
        label(px, py, f"height {h:+d}", 14, SOFT, anchor="rm" if px < CX else "lm")
    else:
        label(px, py, f"height {h:+d}", 14, SOFT)

# size bar
bx, by = P(-560, -560)
d.line((bx, by, bx + 100 * SCALE, by), fill=INK, width=4)
label(bx + 50 * SCALE, by - 14, f"100 studs = {seconds(100):.1f} s walk", 15)

# ---- right column: what the numbers are, then the side view
RX = 1290
d.text((RX, 120), "Sizes", font=font(24, True), fill=INK)
bridge = Pl["Ring"] - Pl["Radius"] - M["Radius"]
home_to_arch = (Pl["Ring"] - Pl["Radius"]) + Pl["Radius"] + A["Radius"]
rows = [
    ("Main island", f"{M['Radius'] * 2} across"),
    ("Plaza", f"{M['Plaza']['Radius'] * 2} across, {M['Plaza']['Height']} up"),
    ("Tower", f"{sum(t[2] for t in S['Tower']['Tiers']) + S['Tower']['Cap']} tall, {S['Tower']['Tiers'][0][0] * 2} wide"),
    ("Arches", f"{A['Width']} wide, {A['Height']} tall"),
    ("Your plot", f"{Pl['Radius'] * 2} across"),
    ("Building spots", f"1 at {Pl['CentreRadius'] * 2}, {Pl['Slots']} at {Pl['SlotRadius'] * 2}"),
    ("Starter building", f"{S['Building'][0]} by {S['Building'][1]} by {S['Building'][2]}"),
    ("Bridge", f"{bridge} long, {S['BridgeWidth']} wide"),
    ("Lands", f"{len(S['Lands'])}, in {len(S['Themes'])} themes of 5"),
    ("Sky", f"{min(l['Distance'] for l in S['Lands'])} to {max(l['Distance'] for l in S['Lands'])} away"),
]
y = 158
for name, value in rows:
    d.text((RX, y), name, font=font(18), fill=SOFT)
    d.text((RX + 170, y), value, font=font(18), fill=INK)
    y += 28

y += 22
d.text((RX, y), "Walks", font=font(24, True), fill=INK)
y += 38
walks = [
    ("Your plot to the plaza", Pl["Ring"] - M["Plaza"]["Radius"]),
    ("Across a bridge", bridge),
    ("Your plot to an arch", home_to_arch),
    ("Plaza to an arch", A["Radius"] - M["Plaza"]["Radius"]),
    ("Across your plot", Pl["Radius"] * 2),
    ("Plot to next plot, by plaza", 2 * (Pl["Ring"] - M["Radius"])),
]
for name, studs in walks:
    d.text((RX, y), name, font=font(18), fill=SOFT)
    d.text((RX + 270, y), f"{seconds(studs):.0f} s", font=font(18, True), fill=INK)
    y += 28

y += 22
d.text((RX, y), "Why it's laid out this way", font=font(24, True), fill=INK)
y += 38
for line in (
    "One arch per theme, on the line from",
    "the tower to that theme's first Land,",
    "so it frames that Land from the plaza.",
    "The theme's other Lands stack around",
    "it, above and below, further away.",
    "Land 30 hangs dead ahead, top of the sky.",
    "Plots sit south, Lands north, so every",
    "plot looks across the bridge at the",
    "tower with the Lands behind it.",
    "Neighbours sit either side: you see",
    "what other players have built.",
):
    d.text((RX, y), line, font=font(17), fill=INK)
    y += 24

# ---- the sky as seen from the plaza: where each Land hangs, numbered in the order you reach them
SX, SY, SW, SH = RX - 30, 1110, 530, 370
LEFT, RIGHT, LOW, HIGH = -80, 80, -14, 52
d.text((RX, 1040), "The sky from the plaza", font=font(24, True), fill=INK)
d.text((RX, 1072), "Each circle's size is how big it looks. 1 to 30 is the order.", font=font(15), fill=SOFT)
d.rectangle((SX, SY, SX + SW, SY + SH), fill=(176, 208, 236))


def sky(bearing, elevation):
    return SX + (bearing - LEFT) / (RIGHT - LEFT) * SW, SY + (HIGH - elevation) / (HIGH - LOW) * SH


hx0, hy0 = sky(LEFT, 0)
hx1, hy1 = sky(RIGHT, 0)
d.rectangle((hx0, hy0, hx1, SY + SH), fill=(226, 234, 242))
for land in S["Lands"]:
    e = math.degrees(math.atan2(land["Top"], land["Distance"]))
    r = math.degrees(math.atan2(land["Radius"], land["Distance"]))
    x, y = sky(land["Bearing"], e)
    rx = r / (RIGHT - LEFT) * SW
    ry = max(4, rx * 0.34)
    d.polygon(((x - rx * 0.86, y), (x + rx * 0.86, y), (x, y + rx * 1.0)), fill=(132, 134, 158))
    d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=tuple(int(c * 255) for c in land["Colour"]), outline=INK)
    label(x, y - ry - 8, str(land["Number"]), 12, INK, True)
for bearing in (-60, -36, -12, 12, 36, 60):
    x, y = sky(bearing, LOW)
    d.line((x, y, x, y - 8), fill=INK, width=2)
label(SX + 8, SY + SH - 10, "ticks: the six arches", 12, SOFT, anchor="lm")

image.save(OUT)
print("wrote", OUT)

# ---- the six views on one sheet, labelled, for reviewing (give ChatGPT the single images)
VIEWS = (
    ("A_your_plot", "A. Your plot: your buildings, the bridge, the tower, the Lands behind"),
    ("B_bridge", "B. The bridge home: it leads your eye up the tower"),
    ("C_arch_to_land", "C. From the plaza: Land 1's arch frames Land 1"),
    ("D_promenade", "D. The promenade: the row of arches curving away"),
    ("E_neighbours", "E. Your neighbour: more built than you, so you want more"),
    ("F_establishing", "F. The whole place, for a poster or the game icon"),
    ("G_sky", "G. The sky of Lands, between two arches"),
)
FOLDER = os.path.dirname(OUT)
VW, VH = 800, 450
sheet = Image.new("RGB", (VW * 2, VH * ((len(VIEWS) + 1) // 2)), BG)
sd = ImageDraw.Draw(sheet)
for i, (name, caption) in enumerate(VIEWS):
    view = Image.open(os.path.join(FOLDER, name + ".png")).convert("RGB").resize((VW, VH), Image.LANCZOS)
    x, y = (i % 2) * VW, (i // 2) * VH
    sheet.paste(view, (x, y))
    sd.text((x + 14, y + 10), caption, font=font(21, True), fill=(255, 255, 255), stroke_width=2, stroke_fill=(30, 34, 44))
sheet.save(os.path.join(FOLDER, "views_sheet.jpg"), quality=90)
