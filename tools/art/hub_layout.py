"""The hub's rough composition (Proposed 2026-11-08). The floating saucer from docs/lands/hub.md at about twice its size: a 1,800-stud
deck, up from 940. On the deck sits a terraced town in the spirit of the user's reference: cobbled streets climbing to a crown,
stone retaining walls with stairs where streets cross them, sandy garden paths, flower terraces and a pond, lamp-lit plazas.
Rescued NPCs' houses line a lane on one side; player plots hang on bridges around the rim.

One source for the plan sheet and the Studio builder. Everything here is a first draft for the user to move by hand.
  python tools/art/hub_layout.py   -> art/hub/layout.json, art/hub/plan.png, art/hub/studio/build_hub.luau (tools/studio/build_hub.luau filled)

Roblox axes: x and z on the ground, y up. The arrival dock is at -z and the town climbs toward +z, so the afternoon sun
(ClockTime 15.6 comes from -x, -z) lights the faces the arrival view looks at. Angles: 0 = +z, 90 = +x.
"""

import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "hub")
LIFT = 2.0  # Roblox draws a terrain surface about 2 studs above the written height (docs/style/terrain-method.md)

# ---------------------------------------------------------------------------------------------------------------- the island
R_DECK = 900.0
DECK_WOB = [(3, 0.012, 0.7), (5, 0.006, 2.1)]
DECK_BOTTOM = -24.0
# the saucer under the deck, as stand-in cylinders (top y, bottom y, radius, colour): arcade band, flange, rock skirt, lower band, bowl
UNDERSIDE = [
	("ArcadeBand", -18, -100, 900, (226, 214, 190)),
	("Flange", -100, -140, 1000, (204, 192, 172)),
	("RockSkirt", -140, -215, 955, (84, 88, 110)),
	("LowerBand", -215, -295, 740, (112, 122, 152)),
	("Step", -295, -355, 620, (102, 112, 144)),
	("Bowl1", -355, -470, 500, (94, 104, 138)),
	("Bowl2", -470, -600, 340, (86, 96, 130)),
	("Bowl3", -600, -740, 170, (78, 88, 122)),
]

# ---------------------------------------------------------------------------------------------------------------- ground levels
# blobs: centre, radius, top height, out-of-round harmonics (k, amount, phase). Height anywhere is the highest blob holding it.
BLOBS = [
	{"Name": "UpperTown", "C": (0.0, 40.0), "R": 520.0, "Top": 16.0, "H": [(2, 0.07, 0.4), (3, 0.05, 1.9), (5, 0.025, 0.3)]},
	{"Name": "Crown", "C": (-40.0, 220.0), "R": 150.0, "Top": 36.0, "H": [(2, 0.06, 1.2), (3, 0.05, 0.2), (4, 0.02, 2.5)]},
	{"Name": "GardenLow", "C": (-670.0, 120.0), "R": 120.0, "Top": 5.0, "H": [(2, 0.08, 2.0), (3, 0.06, 0.5)]},
	{"Name": "GardenHigh", "C": (-655.0, 145.0), "R": 62.0, "Top": 10.0, "H": [(2, 0.08, 0.9), (3, 0.05, 2.4)]},
	{"Name": "GardenSouth", "C": (-630.0, -250.0), "R": 95.0, "Top": 5.0, "H": [(2, 0.09, 1.4), (3, 0.05, 0.1)]},
]
POND = {"C": (-560.0, -430.0), "R": 50.0, "Floor": -3.0, "Water": -0.7}
STREAMS = [
	{"Pts": [(-560, -430), (-620, -478), (-690, -540), (-740, -585)], "W": 10.0},
	{"Pts": [(-560, -430), (-525, -540), (-478, -650), (-440, -810)], "W": 9.0},
]

# ---------------------------------------------------------------------------------------------------------------- streets and paths
DOCK_ANGLES = [22.5 + 45 * k for k in range(8)]  # the plot docks; the arrival dock is at 180
RING_C, RING_R = (0.0, 40.0), 380.0


def at(a, r, c=(0.0, 0.0)):
	a = math.radians(a)
	return (c[0] + r * math.sin(a), c[1] + r * math.cos(a))


def arc(c, r, a0, a1, step=6.0):
	n = max(2, int(abs(a1 - a0) / step) + 1)
	return [at(a0 + (a1 - a0) * i / (n - 1), r, c) for i in range(n)]


ROADS = [
	{"Name": "MarketStreet", "Pts": [(0, -960), (0, -880), (0, -700), (0, -600), (0, -480), (0, -330), (0, -165), (0, -80)], "W": 26.0, "Mat": "Cobblestone"},
	{"Name": "CrownSteps", "Pts": [(0, -80), (0, 5), (-14, 55), (-30, 100), (-38, 160), (-40, 220)], "W": 22.0, "Mat": "Cobblestone"},
	{"Name": "RingRoad", "Pts": arc(RING_C, RING_R, 0, 360, 4.0), "W": 16.0, "Mat": "Cobblestone"},
	{"Name": "ResidentLane", "Pts": arc((0, 0), 700, 46, 142, 3.0), "W": 12.0, "Mat": "Cobblestone"},
	{"Name": "RimPromenade", "Pts": arc((0, 0), 832, 0, 360, 2.0), "W": 14.0, "Mat": "Sand"},
	{"Name": "GardenLoop", "Pts": arc((-670, 120), 150, 0, 360, 6.0), "W": 8.0, "Mat": "Sand"},
	{"Name": "GardenLink", "Pts": [at(270, RING_R, RING_C), (-470, 50), (-520, 85)], "W": 9.0, "Mat": "Sand"},
	{"Name": "PondPath", "Pts": arc(POND["C"], 74, 0, 360, 8.0), "W": 7.0, "Mat": "Sand"},
	{"Name": "PondLink", "Pts": [(-630, -250), (-600, -330), (-575, -362)], "W": 7.0, "Mat": "Sand"},
	{"Name": "LookoutPath", "Pts": [at(10, RING_R, RING_C), (110, 560), (130, 690), (140, 740)], "W": 9.0, "Mat": "Sand"},
]
for k, a in enumerate(DOCK_ANGLES):
	bend = 5.0 if k % 2 else -5.0
	ROADS.append({"Name": f"Spoke{k + 1}", "Pts": [at(a, RING_R, RING_C), at(a + bend, 600), at(a + bend * 0.4, 760), at(a, 890)], "W": 12.0, "Mat": "Sand"})

PLAZAS = [
	{"Name": "WaystonePlaza", "C": (0, -600), "R": 62.0, "Mat": "Cobblestone"},
	{"Name": "TownSquare", "C": (0, -80), "R": 88.0, "Mat": "Cobblestone"},
	{"Name": "GateCourt", "C": (-40, 220), "R": 95.0, "Mat": "Pavement"},
	{"Name": "TreeLookout", "C": (140, 760), "R": 32.0, "Mat": "Sand"},
	{"Name": "ArrivalDockHead", "C": (0, -880), "R": 34.0, "Mat": "Cobblestone"},
] + [{"Name": f"DockHead{k + 1}", "C": at(a, 884), "R": 22.0, "Mat": "Cobblestone"} for k, a in enumerate(DOCK_ANGLES)]


# ---------------------------------------------------------------------------------------------------------------- the height field
def blob_radius(b, x, z):
	dx, dz = x - b["C"][0], z - b["C"][1]
	th = math.atan2(dz, dx)
	return b["R"] * (1 + sum(a * math.cos(k * th + ph) for k, a, ph in b["H"])), math.hypot(dx, dz)


def deck_radius(x, z):
	th = math.atan2(z, x)
	return R_DECK * (1 + sum(a * math.cos(k * th + ph) for k, a, ph in DECK_WOB))


def height(x, z):
	"""the walking surface (None off the island)"""
	if math.hypot(x, z) > deck_radius(x, z):
		return None
	h = 0.0
	for b in BLOBS:
		r, d = blob_radius(b, x, z)
		if d <= r:
			h = max(h, b["Top"])
	return h


def seg_dist(p, a, b):
	ax, az = a
	bx, bz = b
	vx, vz = bx - ax, bz - az
	L2 = vx * vx + vz * vz
	t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - az) * vz) / L2))
	return math.hypot(p[0] - ax - vx * t, p[1] - az - vz * t)


def resample(pts, step):
	out = [pts[0]]
	for a, b in zip(pts[:-1], pts[1:]):
		L = math.hypot(b[0] - a[0], b[1] - a[1])
		n = max(1, int(L / step))
		for i in range(1, n + 1):
			out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
	return out


# ---------------------------------------------------------------------------------------------------------------- stairs and walls
def find_stairs():
	"""where a street or path crosses a change of level: a flight of stairs on the lower side, rising into the upper"""
	stairs = []
	for road in ROADS:
		pts = resample(road["Pts"], 1.0)
		for p, q in zip(pts[:-1], pts[1:]):
			hp, hq = height(*p), height(*q)
			if hp is None or hq is None or abs(hp - hq) < 1:
				continue
			lo, hi = (p, q) if hp < hq else (q, p)
			d = (hi[0] - lo[0], hi[1] - lo[1])
			L = math.hypot(*d)
			stairs.append({"Road": road["Name"], "At": [round(hi[0], 2), round(hi[1], 2)], "Dir": [d[0] / L, d[1] / L], "Low": min(hp, hq), "High": max(hp, hq), "W": road["W"] + 2})
	# a street may cross the same edge once only; drop near-duplicates
	out = []
	for s in stairs:
		if all(math.hypot(s["At"][0] - o["At"][0], s["At"][1] - o["At"][1]) > 6 for o in out):
			out.append(s)
	return out


def find_walls(stairs):
	"""retaining walls round every raised level where the ground outside is lower, broken where stairs come through; a low parapet
	round the deck's rim, broken at the docks and where the streams pour off"""
	walls = []
	for b in BLOBS:
		n = int(2 * math.pi * b["R"] / 10.0)
		ring = []
		for i in range(n + 1):
			th = 2 * math.pi * i / n
			r = b["R"] * (1 + sum(a * math.cos(k * th + ph) for k, a, ph in b["H"]))
			ring.append((b["C"][0] + r * math.cos(th), b["C"][1] + r * math.sin(th), th))
		for (x0, z0, t0), (x1, z1, t1) in zip(ring[:-1], ring[1:]):
			mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
			nx, nz = math.cos((t0 + t1) / 2), math.sin((t0 + t1) / 2)
			outside = height(mx + nx * 3, mz + nz * 3)
			inside = height(mx - nx * 3, mz - nz * 3)
			if outside is None or inside is None or inside - outside < 1:
				continue
			if any(math.hypot(mx - s["At"][0], mz - s["At"][1]) < s["W"] / 2 + 4 for s in stairs):
				continue
			L = math.hypot(x1 - x0, z1 - z0)
			walls.append({"Kind": "Retaining", "Level": b["Name"], "C": [round(mx + nx * 1.2, 2), round(mz + nz * 1.2, 2)], "L": round(L + 0.6, 2), "Top": inside + 2.5, "Bottom": outside - 1.0, "Yaw": math.atan2(x1 - x0, z1 - z0)})
	gaps = [(at(a, 900), 26.0) for a in DOCK_ANGLES] + [(at(180, 900), 40.0)] + [(s["Pts"][-1], s["W"] + 6) for s in STREAMS]
	n = int(2 * math.pi * R_DECK / 12.0)
	for i in range(n):
		t0, t1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
		p0 = (deck_radius(math.cos(t0), math.sin(t0)) * math.cos(t0), deck_radius(math.cos(t0), math.sin(t0)) * math.sin(t0))
		p1 = (deck_radius(math.cos(t1), math.sin(t1)) * math.cos(t1), deck_radius(math.cos(t1), math.sin(t1)) * math.sin(t1))
		m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
		if any(math.hypot(m[0] - g[0][0], m[1] - g[0][1]) < g[1] for g in gaps):
			continue
		walls.append({"Kind": "Parapet", "Level": "Rim", "C": [round(m[0] * 0.997, 2), round(m[1] * 0.997, 2)], "L": round(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) + 0.6, 2), "Top": 3.2, "Bottom": -3.0, "Yaw": math.atan2(p1[0] - p0[0], p1[1] - p0[1])})
	return walls


# ---------------------------------------------------------------------------------------------------------------- lots
# kit sizes (x, y, z) measured in Studio; a house's door faces its model's +z
KIT = {
	"Inn": (30, 31, 21), "Hut": (21, 21, 14), "Smithy": (20, 23, 18), "Cottage": (26, 24, 16), "Farmhouse": (29, 25, 18),
	"Tattered": (25, 27, 16), "Terrace": (42, 38, 16), "Bridgehouse": (23, 35, 21), "Mill": (23, 30, 22), "Clocktower": (38, 42, 16),
	"Manor": (48, 33, 21), "Townhouse": (17, 33, 15),
}
LOTS = []


def lot(name, asset, kind, x, z, face_to=None, yaw=None, size=None):
	sz = size or KIT[asset]
	if yaw is None:
		dx, dz = face_to[0] - x, face_to[1] - z
		yaw = math.atan2(dx, dz)
	LOTS.append({"Name": name, "Asset": asset if asset in KIT else "", "Needs": "" if asset in KIT else asset, "Kind": kind, "X": round(x, 2), "Z": round(z, 2), "Yaw": round(yaw, 4), "Size": list(sz)})


def around(c, a, rim, name, asset, kind, size=None):
	sz = size or KIT[asset]
	x, z = at(a, rim + sz[2] / 2, c)
	lot(name, asset, kind, x, z, face_to=c, size=sz)


# the waystone plaza: where you arrive home
W = (0.0, -600.0)
lot("Waystone and its flower ring", "Waystone + round planter", "Special", W[0], W[1], yaw=0.0, size=(34, 22, 34))
around(W, 100, 72, "Dock master", "Hut", "Civic")
around(W, -100, 70, "Notice board", "Notice board", "Special", size=(10, 9, 3))
# market street on the upper town, shops on both sides with gaps left for flowers and alleys
for z, name, asset in ((-393, "Pet keeper", "Cottage"), (-298, "Tailor (cosmetics)", "Townhouse"), (-254, "General store", "Townhouse"), (-206, "Alchemist", "Townhouse")):
	sz = KIT[asset]
	lot(name, asset, "Shop", 13 + 5 + sz[2] / 2, z, face_to=(0, z), size=sz)
for z, name, asset in ((-392, "Storehouse (haul home)", "Mill"), (-292, "Bakery", "Cottage"), (-226, "Bank", "Terrace")):
	sz = KIT[asset]
	lot(name, asset, "Shop", -(13 + 5 + sz[2] / 2), z, face_to=(0, z), size=sz)
# the town square
S = (0.0, -80.0)
around(S, -55, 94, "Inn (tavern)", "Inn", "Civic")
around(S, 55, 94, "Town hall", "Clocktower", "Civic")
around(S, 122, 94, "Forge", "Smithy", "Civic")
around(S, -122, 94, "Guild hall", "Manor", "Civic")
around(S, -150, 62, "Quest board", "Quest board", "Special", size=(12, 10, 3))
for a in (40, 80, 140, -40, -80):
	around(S, a, 46, "Market stall", "Market stall", "Shop", size=(10, 11, 10))
# the crown: the gate court with an arch per theme, the Climb, the trophy hall, a lookout toward the giant tree
G = (-40.0, 220.0)
for i, a in enumerate((-75, -45, -15, 15, 45, 75)):
	around(G, a, 96, f"Theme arch {i + 1}", "Theme arch", "Special", size=(18, 28, 6))
around(G, -132, 100, "The Climb (tower)", "Climb tower", "Special", size=(30, 80, 30))
around(G, 132, 100, "Trophy hall", "Bridgehouse", "Civic")
# the residents' lane: houses for rescued NPCs, both sides, gaps where the spokes cross
names = ["Cottage", "Hut", "Tattered", "Farmhouse", "Cottage", "Bridgehouse", "Hut", "Tattered", "Cottage", "Farmhouse", "Terrace"]
k = 0
for side, rr, angles in (("in", 700 - 6 - 5, (52, 80, 93, 126, 138)), ("out", 700 + 6 + 5, (56, 79, 91, 102, 124, 136))):
	for a in angles:
		asset = names[k % len(names)]
		k += 1
		sz = KIT[asset]
		rc = rr - sz[2] / 2 if side == "in" else rr + sz[2] / 2
		x, z = at(a, rc)
		fx, fz = at(a, 700)
		lot(f"Resident house {k}", asset, "House", x, z, face_to=(fx, fz), size=sz)
# the gardens and the pond
lot("Greenhouse", "Greenhouse", "Special", -655, 150, yaw=math.radians(30), size=(26, 16, 18))
lot("Gardener", "Hut", "House", -742, 60, face_to=(-670, 120))
lot("Pond", "Pond (terrain)", "Guide", POND["C"][0], POND["C"][1], yaw=0.0, size=(100, 1, 100))
for i, (x, z, w, d, yaw) in enumerate(((-690, 40, 34, 14, 20), (-600, 190, 30, 12, -40), (-700, 200, 26, 12, 60), (-640, -230, 40, 14, -10), (-600, -300, 26, 10, 35))):
	lot(f"Flower bed {i + 1}", "Flower bed", "Guide", x, z, yaw=math.radians(yaw), size=(w, 1.5, d))
lot("Orchard", "Orchard trees (hand-placed)", "Guide", -470, 580, yaw=0.0, size=(220, 1, 160))
lot("Lookout benches", "Benches + telescope", "Guide", 140, 760, face_to=(400, 1400), size=(20, 4, 8))


# ---------------------------------------------------------------------------------------------------------------- docks and plots
def docks_and_plots():
	docks, plots = [], []
	for k, a in enumerate(DOCK_ANGLES):
		docks.append({"Name": f"Dock{k + 1}", "A": a, "R0": 878.0, "R1": 948.0, "W": 34.0, "Bridge": True})
		plots.append({"Name": f"Plot{k + 1}", "C": [round(v, 2) for v in at(a, 1330)], "R": 150.0, "Top": -70.0, "Bottom": -92.0, "Wob": [(3, 0.03, k * 0.9), (5, 0.015, k * 1.7)]})
	docks.append({"Name": "ArrivalDock", "A": 180.0, "R0": 870.0, "R1": 975.0, "W": 64.0, "Bridge": False})
	return docks, plots


GUIDES = []
for z in range(-860, -180, 46):
	if abs(z + 600) < 70 or abs(z + 340) < 14:
		continue
	for x in (-15.5, 15.5):
		GUIDES.append({"Name": "Lamp", "X": x, "Z": z, "Size": [1.2, 11, 1.2]})
for c, r, n in ((W, 66, 6), (S, 92, 8), (G, 99, 6)):
	for i in range(n):
		x, z = at(i * 360 / n + 180 / n, r, c)
		GUIDES.append({"Name": "Lamp", "X": round(x, 2), "Z": round(z, 2), "Size": [1.2, 11, 1.2]})
for c, r, angles in ((W, 48, (60, 120, 240, 300)), (S, 74, (20, -20, 160, -160))):
	for a in angles:
		x, z = at(a, r, c)
		GUIDES.append({"Name": "Bench", "X": round(x, 2), "Z": round(z, 2), "Size": [6, 2.5, 2.5], "Face": list(c)})

LABELS = [
	("Arrival dock (sky-ship)", (0, -930)), ("Waystone plaza (home)", (0, -600)), ("Market street", (60, -360)), ("Town square", (0, -80)),
	("The Crown: gate court", (-40, 220)), ("Residents' lane (rescued NPCs)", (560, 260)), ("Flower gardens", (-660, 60)), ("Pond", (-560, -430)),
	("Orchard", (-470, 580)), ("Tree lookout", (140, 760)), ("Rim promenade", (590, -590)),
]


def build():
	stairs = find_stairs()
	walls = find_walls(stairs)
	docks, plots = docks_and_plots()
	for l in LOTS:
		l["Y"] = height(l["X"], l["Z"])
	for g in GUIDES:
		g["Y"] = height(g["X"], g["Z"])
	labels = [{"Text": t, "X": p[0], "Z": p[1], "Y": (height(*p) or 0.0) + 40} for t, p in LABELS]
	labels += [{"Text": p["Name"].replace("Plot", "Player plot "), "X": p["C"][0], "Z": p["C"][1], "Y": p["Top"] + 40} for p in plots]
	data = {
		"Lift": LIFT, "Deck": {"R": R_DECK, "Wob": DECK_WOB, "Bottom": DECK_BOTTOM}, "Underside": [list(u) for u in UNDERSIDE],
		"Blobs": [dict(b, C=list(b["C"]), H=[list(h) for h in b["H"]]) for b in BLOBS],
		"Pond": dict(POND, C=list(POND["C"])), "Streams": [{"Pts": [list(p) for p in resample(s["Pts"], 6.0)], "W": s["W"]} for s in STREAMS],
		"Roads": [{"Name": r["Name"], "Pts": [[round(x, 2), round(z, 2)] for x, z in resample(r["Pts"], 8.0)], "W": r["W"], "Mat": r["Mat"]} for r in ROADS],
		"Plazas": [dict(p, C=[round(v, 2) for v in p["C"]]) for p in PLAZAS],
		"Stairs": stairs, "Walls": walls, "Lots": LOTS, "Docks": docks, "Plots": plots, "Guides": GUIDES, "Labels": labels,
		"Spawn": [W[0], 0.0, W[1] - 40],
	}
	os.makedirs(os.path.join(OUT, "studio"), exist_ok=True)
	json.dump(data, open(os.path.join(OUT, "layout.json"), "w"), indent=1)
	tpl = open(os.path.join(ROOT, "tools", "studio", "build_hub.luau"), encoding="utf-8").read()
	assert "__DATA__" in tpl
	body = tpl.replace("__DATA__", json.dumps(data, separators=(",", ":")))
	open(os.path.join(OUT, "studio", "build_hub.luau"), "w", encoding="utf-8").write(body)
	plan(data)
	bad = [l["Name"] for l in LOTS if l["Kind"] != "Guide" and not lot_flat(l)]
	print(f"[hub] stairs {len(stairs)}, walls {len(walls)}, lots {len(LOTS)}, guides {len(GUIDES)}, script {len(body) // 1024} KB; lots on a change of level: {bad}")


def lot_flat(l):
	"""a lot sits on one level: its corners and middle share a height"""
	c, s = math.cos(l["Yaw"]), math.sin(l["Yaw"])
	hs = set()
	for u, v in ((0, 0), (-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
		dx, dz = u * l["Size"][0], v * l["Size"][2]
		hs.add(height(l["X"] + dx * c + dz * s, l["Z"] - dx * s + dz * c))
	return len(hs) == 1


# ---------------------------------------------------------------------------------------------------------------- the plan sheet
def plan(data):
	S, half = 0.5, 1520  # px per stud, half extent
	N = int(2 * half * S)
	im = Image.new("RGB", (N, N + 70), (196, 214, 234))
	d = ImageDraw.Draw(im)

	def P(x, z):  # +z up the sheet (toward the crown and the giant tree), +x to the right
		return ((x + half) * S, (half - z) * S + 70)

	try:
		font, big = ImageFont.truetype("arial.ttf", 13), ImageFont.truetype("arialbd.ttf", 18)
	except OSError:
		font = big = ImageFont.load_default()
	ring = [P(deck_radius(math.cos(t), math.sin(t)) * math.cos(t) * 1.11, deck_radius(math.cos(t), math.sin(t)) * math.sin(t) * 1.11) for t in [i * math.pi / 90 for i in range(181)]]
	d.polygon(ring, fill=(206, 196, 178))
	ring = [P(deck_radius(math.cos(t), math.sin(t)) * math.cos(t), deck_radius(math.cos(t), math.sin(t)) * math.sin(t)) for t in [i * math.pi / 90 for i in range(181)]]
	d.polygon(ring, fill=(122, 176, 90))
	for b in sorted(BLOBS, key=lambda b: b["Top"]):
		pts = []
		for i in range(181):
			th = 2 * math.pi * i / 180
			r = b["R"] * (1 + sum(a * math.cos(k * th + ph) for k, a, ph in b["H"]))
			pts.append(P(b["C"][0] + r * math.cos(th), b["C"][1] + r * math.sin(th)))
		v = int(min(60, b["Top"] * 1.6))
		d.polygon(pts, fill=(122 + v, 176 + v // 2, 90 + v // 3), outline=(90, 84, 76))
	for p in data["Plots"]:
		c, r = p["C"], p["R"]
		d.ellipse([P(c[0] - r, c[1] + r), P(c[0] + r, c[1] - r)], fill=(132, 182, 98), outline=(90, 84, 76))
	cols = {"Cobblestone": (214, 202, 182), "Sand": (236, 222, 180), "Pavement": (226, 220, 210)}
	for r in data["Roads"]:
		d.line([P(x, z) for x, z in r["Pts"]], fill=cols[r["Mat"]], width=max(2, int(r["W"] * S)))
	for p in data["Plazas"]:
		c, r = p["C"], p["R"]
		d.ellipse([P(c[0] - r, c[1] + r), P(c[0] + r, c[1] - r)], fill=cols[p["Mat"]])
	c, r = POND["C"], POND["R"]
	d.ellipse([P(c[0] - r, c[1] + r), P(c[0] + r, c[1] - r)], fill=(96, 160, 206))
	for s in data["Streams"]:
		d.line([P(x, z) for x, z in s["Pts"]], fill=(96, 160, 206), width=int(s["W"] * S) + 1)
	for w in data["Walls"]:
		dx, dz = math.sin(w["Yaw"]) * w["L"] / 2, math.cos(w["Yaw"]) * w["L"] / 2
		d.line([P(w["C"][0] - dx, w["C"][1] - dz), P(w["C"][0] + dx, w["C"][1] + dz)], fill=(112, 104, 96) if w["Kind"] == "Retaining" else (160, 150, 136), width=2)
	for s in data["Stairs"]:
		d.ellipse([P(s["At"][0] - 7, s["At"][1] + 7), P(s["At"][0] + 7, s["At"][1] - 7)], fill=(240, 180, 60))
	for k in data["Docks"]:
		a0, a1 = at(k["A"], k["R0"]), at(k["A"], k["R1"])
		d.line([P(*a0), P(*a1)], fill=(214, 202, 182), width=int(k["W"] * S))
		if k["Bridge"]:
			d.line([P(*a1), P(*at(k["A"], 1330 - 150))], fill=(150, 112, 76), width=4)
	kc = {"Civic": (70, 110, 200), "Shop": (220, 130, 60), "House": (80, 150, 90), "Special": (150, 90, 190), "Guide": (240, 240, 240)}
	for l in data["Lots"]:
		c, s = math.cos(l["Yaw"]), math.sin(l["Yaw"])
		pts = []
		for u, v in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
			dx, dz = u * l["Size"][0], v * l["Size"][2]
			pts.append(P(l["X"] + dx * c + dz * s, l["Z"] - dx * s + dz * c))
		if l["Kind"] == "Guide":
			d.polygon(pts, outline=(255, 255, 255))
		else:
			d.polygon(pts, fill=kc[l["Kind"]], outline=(40, 40, 40))
	for t in data["Labels"]:
		x, y = P(t["X"], t["Z"])
		d.text((x, y - 14), t["Text"], fill=(30, 30, 40), font=font, anchor="mm")
	d.text((14, 12), "Hub plan draft (2026-11-08): 1,800-stud deck, terraced town, 8 player plots. Top = toward the Crown and the giant tree; arrival at the bottom.", fill=(30, 30, 40), font=big)
	d.text((14, 40), "Blue civic, orange shops, green houses, purple needs a new asset, white outlines = guides. Yellow dots = stairs. 1 px = 2 studs.", fill=(30, 30, 40), font=font)
	im.save(os.path.join(OUT, "plan.png"))


if __name__ == "__main__":
	build()
