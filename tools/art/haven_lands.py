"""Writes the Themes and Lands in art/haven/layout.json: 30 Lands in six themes of five.
Each Land is placed by how it looks from the plaza (bearing, elevation, apparent size), so the sky is composed.
Prints any overlaps and Lands dipping into the cloud. Run with system Python, then rerun haven_blockout.py."""
import json
import math

p = "C:/Users/blast/RpgGame/art/haven/layout.json"
S = json.load(open(p, encoding="utf-8"))

# name, bearing offset, distance factor, elevation (deg), apparent radius (deg), top colour, bits
THEMES = [
    ("Greenreach", (0.5, 0.41, 0.34), "grass", -12, 3200, [
        ("Verdant Vale", 0, 1.00, -1.8, 14.0, (0.42, 0.68, 0.36), [["hills", 9, "hill"], ["giant", 1], ["trees", 16, "tree"], ["falls", 1]]),
        ("Sandbar Meadow", 8, 1.25, 20, 5.5, (0.50, 0.68, 0.38), [["patch", 7, "sand"], ["hills", 3, "hill"], ["trees", 5, "tree"]]),
        ("Mirrorbrook", -13, 1.45, 11, 4.6, (0.36, 0.66, 0.42), [["patch", 5, "water"], ["hills", 4, "hill"], ["trees", 6, "tree"], ["falls", 2]]),
        ("Thornwood", -2, 1.75, 33, 3.4, (0.30, 0.54, 0.32), [["trees", 34, "tree"]]),
        ("Oldroot", 12, 2.00, -4.6, 2.9, (0.40, 0.60, 0.30), [["stump", 1], ["trees", 8, "tree"]]),
    ]),
    ("High Meadows", (0.68, 0.56, 0.38), "top grass", 12, 4400, [
        ("Brightwheat Downs", 0, 1.00, 9, 7.5, (0.76, 0.66, 0.34), [["hills", 6, "gold"], ["mill", 1]]),
        ("Poppyrise", 3, 1.20, 23, 4.4, (0.62, 0.72, 0.38), [["patch", 12, "red"], ["hills", 4, "hill"]]),
        ("Stepfields", -1, 1.35, 34, 3.4, (0.58, 0.74, 0.40), [["terraces", 4]]),
        ("Ringstone Tops", 10, 1.55, 5, 3.0, (0.66, 0.72, 0.46), [["stones", 9], ["hills", 2, "hill"]]),
        ("Highwind", 6, 1.80, 45, 2.6, (0.70, 0.76, 0.50), [["hills", 7, "hill"], ["trees", 3, "tree"]]),
    ]),
    ("Hollowmere", (0.22, 0.34, 0.36), "marsh", -36, 5600, [
        ("Hollowmere", 0, 1.00, 2, 6.5, (0.32, 0.50, 0.48), [["patch", 4, "water"], ["trees", 12, "willow"]]),
        ("Reedwater", -8, 1.20, -2.4, 3.4, (0.36, 0.56, 0.46), [["patch", 7, "water"], ["pines", 18, "reed"]]),
        ("Lanternbog", 2, 1.30, 14, 3.8, (0.26, 0.42, 0.40), [["trees", 9, "willow"], ["glows", 12, "lamp"]]),
        ("Drownroot", -2, 1.55, 25, 2.8, (0.28, 0.40, 0.34), [["roots", 7], ["patch", 3, "water"]]),
        ("Blackmire", 3, 1.75, 35, 2.2, (0.20, 0.28, 0.30), [["patch", 6, "mud"], ["trees", 6, "willow"]]),
    ]),
    ("Fae Hollow", (0.46, 0.32, 0.6), "fae", 36, 7000, [
        ("Fae Hollow", 0, 1.00, 11, 5.5, (0.56, 0.42, 0.68), [["caps", 11, "cap"]]),
        ("Glowcap Dell", 3, 1.15, 23, 3.8, (0.44, 0.40, 0.72), [["caps", 9, "capblue"], ["glows", 8, "lamp"]]),
        ("Moonpetal", -4, 1.30, 1, 3.0, (0.66, 0.52, 0.78), [["patch", 10, "petal"], ["caps", 3, "capgold"]]),
        ("Thistlecourt", 8, 1.50, 3, 2.2, (0.60, 0.36, 0.60), [["stones", 7], ["spires", 4, "stone"], ["caps", 3, "cap"]]),
        ("Everdusk", -1, 1.75, 36, 2.6, (0.36, 0.30, 0.58), [["caps", 12, "capgold"]]),
    ]),
    ("Sunscar", (0.74, 0.4, 0.24), "desert", -60, 8600, [
        ("Sunscar Expanse", 0, 1.00, 6, 5.0, (0.80, 0.58, 0.36), [["mesas", 7, "mesa"]]),
        ("Dunesea", -7, 1.15, -1.5, 3.0, (0.88, 0.72, 0.46), [["dunes", 12, "dune"]]),
        ("Redspire", 4, 1.30, 18, 3.2, (0.72, 0.40, 0.28), [["spires", 12, "mesa"]]),
        ("Glassflats", -2, 1.50, 29, 2.4, (0.82, 0.78, 0.62), [["patch", 9, "glass"], ["mesas", 2, "mesa"]]),
        ("Emberwaste", 10, 1.70, 3, 1.9, (0.42, 0.26, 0.24), [["mesas", 4, "ember"], ["glows", 9, "lava"]]),
    ]),
    ("Rimefell", (0.72, 0.82, 0.92), "snow", 60, 10500, [
        ("Rimefell", 0, 1.00, 15, 4.6, (0.82, 0.88, 0.94), [["peaks", 6, "snow"]]),
        ("Frostpine", 4, 1.12, 3, 2.8, (0.78, 0.86, 0.90), [["pines", 26, "pine"]]),
        ("Icefall", -3, 1.25, 27, 3.0, (0.76, 0.88, 0.96), [["peaks", 3, "ice"], ["falls", 3]]),
        ("Whitepeak", 3, 1.40, 39, 2.2, (0.92, 0.95, 0.98), [["peaks", 4, "snow"]]),
        # the very last Land sits dead ahead at the top of the sky: you can see where it all ends from your first minute
        ("The Crown", None, 16000 / 10500, 37, 3.4, (0.96, 0.97, 1.0), [["crown", 1]]),
    ]),
]

lands = []
themes = []
number = 0
for t, (theme, rock, kind, bearing, base, group) in enumerate(THEMES):
    first = number + 1
    for j, (name, offset, factor, elevation, apparent, colour, bits) in enumerate(group):
        number += 1
        distance = round(base * factor)
        b = 0 if offset is None else bearing + offset
        land = {
            "Number": number,
            "Name": name,
            "Theme": theme,
            "Bearing": b,
            "Distance": distance,
            "Radius": round(distance * math.tan(math.radians(apparent))),
            "Top": round(distance * math.tan(math.radians(elevation))),
            "Colour": colour,
            "Rock": rock,
            "Bits": bits,
        }
        if number == 1:
            land["Open"] = True
        lands.append(land)
    themes.append({"Name": theme, "Kind": kind, "Bearing": bearing, "Rock": rock, "Lands": [first, number]})

S.pop("Lands", None)
S.pop("Themes", None)
S["Themes"] = themes
S["Lands"] = lands
json.dump(S, open(p, "w", encoding="utf-8"), indent=1)


# what overlaps from the plaza, and which islands dip into the cloud
def spot(L):
    return L["Bearing"], math.degrees(math.atan2(L["Top"] - 0.3 * L["Radius"], L["Distance"])), math.degrees(math.atan2(L["Radius"], L["Distance"]))


for i, a in enumerate(lands):
    ax, ay, ar = spot(a)
    if a["Top"] - a["Radius"] * 0.95 < S["Clouds"]:
        print("in cloud:", a["Name"], a["Top"], a["Radius"])
    for b in lands[i + 1:]:
        bx, by, br = spot(b)
        if math.hypot(ax - bx, ay - by) < 0.8 * (ar + br):
            print("overlap:", a["Name"], "/", b["Name"], round(math.hypot(ax - bx, ay - by), 1), round(ar + br, 1))
print(len(lands), "lands; furthest", max(l["Distance"] for l in lands))
