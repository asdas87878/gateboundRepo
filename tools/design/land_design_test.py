"""Design test of a Land's map (system Python): does its size, route and level order hold up against how many enemies and how much play the game needs?
Geometry is measured from art/lands/<land>/map.json. The player-behaviour numbers below are ASSUMPTIONS, to argue with: the design doc only fixes
16 studs/s walking (Roblox's default), clears of 30-90 s, parties of up to 4, and level 3-4 by minute 10.

  python tools/design/land_design_test.py art/lands/land1/map.json
"""
import json
import math
import sys

import numpy as np

WALK = 16.0  # studs/s
PATH_FACTOR = 1.3  # the block-out's measured path length against a straight line
PACK = 4  # enemies a camp
CLEAR_S = 45  # seconds to clear a camp, inside the doc's 30-90 s
RESPAWN_S = 90
CAMP_SPACING = 110  # studs between camp centres: at 16 studs/s that is about 7 s of walking
CAMP_RADIUS = 28  # studs a fight needs
PATH_CLEAR = 18  # studs each side of a road kept free of camps
SERVER = 16  # players in a server
PEAK_SHARE = 0.5  # share of a server in the busiest zone
LEVEL_MINUTES = [3, 4, 6, 9, 13, 18, 24, 30, 38]  # minutes for level 1->2 ... 9->10; a first draft, about 2.4 h; 3-4 by minute 10 is the doc's target
ROSTER = {  # rig each enemy could share
	"Slime": "slime", "Hornhare": "beast", "Field Boar": "beast", "Moss Golem": "golem", "Bandit Scout": "human", "Thornwolf": "beast", "Wisp": "wisp",
	"Mushroom Folk": "human", "Bandit Brute": "human", "Bandit Archer": "human", "Old Tusk": "beast", "Rockback": "golem", "Hollowhorn": "beast",
	"Captain Redfang": "human", "Rootmother": "unique: tree", "Mossback Warden": "golem",
}


def seg_len(pts):
	return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def seg_dist(X, Y, pts):
	best = np.full(X.shape, 1e9)
	for a, b in zip(pts, pts[1:]):
		ax, ay, bx, by = *a, *b
		dx, dy = bx - ax, by - ay
		t = np.clip(((X - ax) * dx + (Y - ay) * dy) / max(dx * dx + dy * dy, 1e-6), 0, 1)
		best = np.minimum(best, np.hypot(X - ax - t * dx, Y - ay - t * dy))
	return best


def crossing(p, q, r, s):
	def o(a, b, c):
		return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
	if o(p, q, r) * o(p, q, s) >= 0 or o(r, s, p) * o(r, s, q) >= 0:
		return None
	t = o(r, s, p) / (o(r, s, p) - o(r, s, q))
	return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))


m = json.load(open(sys.argv[1], encoding="utf-8"))
W, H = m["Size"]
step = 4
X, Y = np.meshgrid(np.arange(0, W, step, dtype=float), np.arange(0, H, step, dtype=float))
river = seg_dist(X, Y, m["River"])
roads = np.minimum.reduce([seg_dist(X, Y, p) for p in m["Paths"]])
rw = m["Blockout"]["RiverWidth"]
island = m["Blockout"]["Island"]
hub = m["Places"][0]["At"]
hubd = np.hypot(X - hub[0], Y - hub[1])
zones = m["Zones"]
inside = [((X - z["At"][0]) / z["Radius"][0]) ** 2 + ((Y - z["At"][1]) / z["Radius"][1]) ** 2 for z in zones]
owner = np.argmin(np.stack(inside), 0)
owner[np.min(np.stack(inside), 0) > 1] = -1

print("== SIZE ==")
print(f"map {W} x {H} studs: {W / WALK:.0f} s to walk across at {WALK:.0f} studs/s, {H / WALK:.0f} s top to bottom")
print(f"test river scene is about 400 x 488 studs ({400 / WALK:.0f} s across); the map is {W * H / (400 * 488):.1f}x its area")
print("\n== ZONES: how many camps fit, and how many a busy server needs ==")
print(f"(camp every {CAMP_SPACING} studs, not on roads or water, {PACK} enemies, {CLEAR_S} s to clear, {RESPAWN_S} s respawn, {int(SERVER * PEAK_SHARE)} players at peak)")
need = int(SERVER * PEAK_SHARE) * (CLEAR_S + RESPAWN_S) / CLEAR_S / 2  # a camp feeds one player for a clear + respawn; parties and overlap halve the demand
rs = np.random.RandomState(4)
totals = 0
caps = {}
for i, z in enumerate(zones):
	free = (owner == i) & (river > rw / 2 + CAMP_RADIUS) & (roads > PATH_CLEAR + CAMP_RADIUS * 0.5) & (hubd > island["Radius"] + island["Moat"] + CAMP_RADIUS)
	area = (owner == i).sum() * step * step
	ys, xs = np.where(free)
	order = rs.permutation(len(xs))
	placed = []
	for k in order:
		p = (xs[k] * step, ys[k] * step)
		if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= CAMP_SPACING ** 2 for q in placed):
			placed.append(p)
	caps[z["Name"]] = len(placed)
	totals += len(placed)
	crossing_s = 2 * max(z["Radius"]) / WALK
	flag = "OK" if len(placed) >= need else "TIGHT"
	print(f"{z['Name']:17s} Lv {z['Levels']:5s} area {area / 1000:4.0f}k  camps {len(placed):3d} ({len(placed) * PACK:3d} enemies)  across {crossing_s:3.0f} s  need about {need:.0f}: {flag}")
print(f"total {totals} camps, {totals * PACK} enemies placed; only those near players need to be awake")

print("\n== ROUTES: story order, real walking ==")
places = {p["Name"]: p["At"] for p in m["Places"]}
nodes, edges = {}, {}
def key(p):
	return (round(p[0]), round(p[1]))
for path in m["Paths"]:
	for a, b in zip(path, path[1:]):
		ka, kb = key(a), key(b)
		d = math.dist(a, b)
		edges.setdefault(ka, {})[kb] = d
		edges.setdefault(kb, {})[ka] = d
# the hub joins its road ends
hub_ends = [k for k in edges if math.dist(k, hub) < 90]
for a in hub_ends:
	for b in hub_ends:
		if a != b:
			edges[a][b] = math.dist(a, b)
def route(a, b):
	ka = min(edges, key=lambda k: math.dist(k, a))
	kb = min(edges, key=lambda k: math.dist(k, b))
	dist = {ka: math.dist(a, ka)}
	todo = set(edges)
	while todo:
		u = min((t for t in todo if t in dist), key=lambda t: dist[t], default=None)
		if u is None or u == kb:
			break
		todo.remove(u)
		for v, w in edges[u].items():
			if dist[u] + w < dist.get(v, 1e12):
				dist[v] = dist[u] + w
	return dist.get(kb, float("inf")) + math.dist(b, kb)
start = places["Wake: gate-stone circle"]
gate = places["THE GATE: Mossback Warden"]
stops = [("Wake", start), ("Hub", hub), ("Mossrock ruins", places["Old gate towers + arcade"]), ("Rootdeep", places["Rootdeep Hollow (dungeon)"]), ("Bandit camp", places["Bandit camp"]), ("Gate", gate)]
tot = 0
for (na, a), (nb, b) in zip(stops, stops[1:]):
	d = route(a, b)
	tot += d
	print(f"{na:15s} -> {nb:15s} {d:5.0f} studs {d / WALK:4.0f} s")
print(f"whole story route {tot:.0f} studs, {tot / WALK / 60:.1f} min of pure walking")
print("\nA new player's first steps, walking from the start to each zone's edge:")
for i, z in enumerate(zones):
	if z["Name"] == "Wayfarer's Rest":
		continue
	mask = owner == i
	ys, xs = np.where(mask & (roads < 8))
	if len(xs):
		best = min(route(start, (xs[k] * step, ys[k] * step)) for k in range(0, len(xs), max(1, len(xs) // 40)))
		print(f"  {z['Name']:17s} Lv {z['Levels']:5s} {best:5.0f} studs {best / WALK:4.0f} s")
	else:
		print(f"  {z['Name']:17s} Lv {z['Levels']:5s} no road")

print("\n== RIVER: where roads cross it (each needs a bridge) ==")
n = 0
for path in m["Paths"]:
	for a, b in zip(path, path[1:]):
		for r, s in zip(m["River"], m["River"][1:]):
			c = crossing(a, b, r, s)
			if c:
				n += 1
				print(f"  at {c[0]:.0f}, {c[1]:.0f}" + ("  (hub island)" if math.dist(c, hub) < 130 else ""))
print(f"  {n} crossings. The land doc only plans the hub's 3 bridges.")

print("\n== LEVELS ==")
bands = [(z["Name"], *map(int, (z["Levels"] + "-" + z["Levels"]).split("-")[:2])) for z in zones]
cover = {lv: [] for lv in range(1, 11)}
for name, a, b in bands:
	for lv in range(a, b + 1):
		cover[lv].append(name)
cover_dungeon = range(6, 10)
for lv, names in cover.items():
	extra = " + Rootdeep" if lv in cover_dungeon else ""
	print(f"  Lv {lv:2d}: {', '.join(names) or 'NOTHING'}{extra}")
print("\n== PLAY TIME AND KILLS (assumed level curve) ==")
kills_per_min = PACK / ((CLEAR_S + CAMP_SPACING / WALK) / 60)
clock = 0
for lv, mins in enumerate(LEVEL_MINUTES, 1):
	clock += mins
	print(f"  Lv {lv:2d} -> {lv + 1:2d}: {mins:3d} min, {mins * kills_per_min:4.0f} kills, total {clock:3d} min")
print(f"  about {kills_per_min:.1f} kills a minute; {clock / 60:.1f} h to level 10; level at minute 10: {sum(1 for c in np.cumsum(LEVEL_MINUTES) if c <= 10) + 1}")

print("\n== ENEMIES TO BUILD ==")
rigs = {}
for name, rig in ROSTER.items():
	rigs.setdefault(rig, []).append(name)
print(f"  {len(ROSTER)} enemy types in Land 1. On {len(rigs)} shared rigs:")
for rig, names in rigs.items():
	print(f"    {rig}: {', '.join(names)}")
