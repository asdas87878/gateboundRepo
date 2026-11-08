-- Grey-box of Land 1, Verdant Vale, for judging scale: terrain from the baked height image (tools/blender/export_land_terrain.py) plus plain labelled blocks. Run in edit mode.
-- Map (x, y) sits at world (x + Offset.X, height, y + Offset.Z), clear of the river scene. Rebuilds Workspace.ValeGreybox and this terrain region only, never Terrain:Clear.
-- Camps and trees are rough stand-ins scattered by the rules in tools/design/land_design_test.py, to show density, not final placement.

local CONFIG = {
	Image = "rbxassetid://132623038596075",
	Offset = Vector3.new(1500, 0, -600),
	Border = 200,
	Step = 4,
	YMin = -16,
	YMax = 256,
	Chunk = 64,
	CampSpacing = 110,
	CampRadius = 28,
	PackSize = 4,
	Seed = 7,
}
local C = CONFIG

local ZONES = {
	{ Name = "Sunny Meadows", Levels = "1-3", At = { 700, 940 }, Radius = { 400, 240 }, Trees = 0.05, Tint = Color3.fromRGB(120, 140, 105) },
	{ Name = "Mossrock Hills", Levels = "3-5", At = { 1110, 680 }, Radius = { 260, 290 }, Trees = 0.08, Tint = Color3.fromRGB(110, 125, 105) },
	{ Name = "Whisperwood", Levels = "5-8", At = { 640, 260 }, Radius = { 400, 230 }, Trees = 0.75, Tint = Color3.fromRGB(65, 85, 72) },
	{ Name = "Bandit Ridge", Levels = "7-9", At = { 230, 560 }, Radius = { 210, 310 }, Trees = 0.12, Tint = Color3.fromRGB(135, 125, 100) },
	{ Name = "Gatehill", Levels = "10", At = { 1150, 230 }, Radius = { 190, 160 }, Trees = 0.04, Tint = Color3.fromRGB(125, 125, 115) },
	{ Name = "Wayfarer's Rest", Levels = "1", At = { 230, 1060 }, Radius = { 150, 110 }, Trees = 0.06, Tint = Color3.fromRGB(120, 135, 105) },
}
local PLACES = {
	{ "Brightwater (hub)", 700, 620 }, { "Wake: gate-stone circle", 230, 1060 }, { "THE GATE: Mossback Warden", 1150, 230 }, { "Rootdeep Hollow (dungeon)", 520, 110 },
	{ "Boss: Old Tusk", 820, 1010, true }, { "Boss: Rockback", 1190, 760, true }, { "Boss: Hollowhorn", 760, 200, true }, { "Boss: Captain Redfang", 190, 470, true },
	{ "Twin Fang shrine", 330, 360 }, { "Old gate towers", 1020, 560 }, { "Bandit camp", 270, 620 },
}
local WAYSTONES = { { 700, 640 }, { 640, 940 }, { 1100, 700 }, { 640, 300 }, { 240, 580 }, { 1120, 330 } }
-- x, y, direction the road runs (degrees from map +x), length. The hub's three, then the two river crossings the land doc doesn't plan yet.
local BRIDGES = { { 700, 722, 90, 54 }, { 694, 508, 90, 54 }, { 806, 631, 0, 54 }, { 486, 344, -16, 62 }, { 981, 873, 144, 62 } }

local MATS = {
	[0] = Enum.Material.Grass,
	[1] = Enum.Material.LeafyGrass,
	[2] = Enum.Material.Sandstone,
	[3] = Enum.Material.Limestone,
	[4] = Enum.Material.Rock,
	[5] = Enum.Material.Sand,
	[6] = Enum.Material.Mud,
	[7] = Enum.Material.Sand, -- the river's bed
	[8] = Enum.Material.Cobblestone,
}

local terrain = workspace.Terrain
terrain:SetMaterialColor(Enum.Material.LeafyGrass, Color3.fromRGB(44, 92, 66))
terrain:SetMaterialColor(Enum.Material.Sandstone, Color3.fromRGB(176, 150, 98))
terrain:SetMaterialColor(Enum.Material.Limestone, Color3.fromRGB(190, 186, 166))
terrain:SetMaterialColor(Enum.Material.Cobblestone, Color3.fromRGB(150, 148, 142))

local image = game:GetService("AssetService"):CreateEditableImageAsync(Content.fromUri(C.Image))
local W, H = image.Size.X, image.Size.Y
local px = image:ReadPixelsBuffer(Vector2.zero, image.Size)
local function column(i, j)
	local o = (j * W + i) * 4
	return (buffer.readu8(px, o) * 256 + buffer.readu8(px, o + 1)) / 100 - 40, buffer.readu8(px, o + 2)
end
local function at(x, y)
	local i = math.clamp(math.round((x + C.Border) / C.Step), 0, W - 1)
	local j = math.clamp(math.round((y + C.Border) / C.Step), 0, H - 1)
	return column(i, j)
end

-- terrain, one chunk at a time
local ny = (C.YMax - C.YMin) // C.Step
for cj = 0, H - 1, C.Chunk do
	for ci = 0, W - 1, C.Chunk do
		local nx, nz = math.min(C.Chunk, W - ci), math.min(C.Chunk, H - cj)
		local mats, occ = table.create(nx), table.create(nx)
		for i = 1, nx do
			local mi, oi = table.create(ny), table.create(ny)
			for k = 1, ny do
				local bottom = C.YMin + (k - 1) * C.Step
				local mk, ok = table.create(nz), table.create(nz)
				for j = 1, nz do
					local h, m = column(ci + i - 1, cj + j - 1)
					local fill = math.clamp((h - bottom) / C.Step, 0, 1)
					if fill > 0 then
						mk[j], ok[j] = MATS[m] or Enum.Material.Grass, fill
					elseif bottom < -1 and (m == 7 or h < -0.5) then
						mk[j], ok[j] = Enum.Material.Water, 1
					else
						mk[j], ok[j] = Enum.Material.Air, 0
					end
				end
				mi[k], oi[k] = mk, ok
			end
			mats[i], occ[i] = mi, oi
		end
		local low = Vector3.new(C.Offset.X + (ci - C.Border / C.Step) * C.Step, C.YMin, C.Offset.Z + (cj - C.Border / C.Step) * C.Step)
		local region = Region3.new(low, low + Vector3.new(nx, ny, nz) * C.Step)
		terrain:WriteVoxels(region, C.Step, mats, occ)
		task.wait()
	end
end

-- blocks
local old = workspace:FindFirstChild("ValeGreybox")
if old then
	old:Destroy()
end
local root = Instance.new("Folder")
root.Name = "ValeGreybox"
root.Parent = workspace
local function group(name)
	local f = Instance.new("Folder")
	f.Name = name
	f.Parent = root
	return f
end

local STONE, ROOF, WOOD = Color3.fromRGB(190, 188, 180), Color3.fromRGB(120, 124, 136), Color3.fromRGB(130, 112, 92)
local ENEMY = Color3.fromRGB(190, 60, 55)

-- a block standing on the ground at map (x, y), size = width, height, depth
local function box(parent, name, x, y, size, colour, yaw, lift)
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.Size = size
	p.Color = colour
	p.Material = Enum.Material.SmoothPlastic
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	local ground = at(x, y)
	p.CFrame = CFrame.new(x + C.Offset.X, ground + (lift or 0) + size.Y / 2, y + C.Offset.Z) * CFrame.Angles(0, yaw or 0, 0)
	p.Parent = parent
	return p
end

local function label(parent, text, x, y, up, colour, distance)
	local a = Instance.new("Part")
	a.Name = "Label"
	a.Anchored = true
	a.CanCollide = false
	a.CanQuery = false
	a.CanTouch = false
	a.Transparency = 1
	a.Size = Vector3.one
	local ground = at(x, y)
	a.Position = Vector3.new(x + C.Offset.X, ground + up, y + C.Offset.Z)
	local g = Instance.new("BillboardGui")
	g.Size = UDim2.fromOffset(340, 34)
	g.AlwaysOnTop = true
	g.MaxDistance = distance
	g.Parent = a
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Text = text
	t.TextColor3 = colour
	t.TextStrokeTransparency = 0.2
	t.Font = Enum.Font.GothamBold
	t.TextSize = 22
	t.Parent = g
	a.Parent = parent
end

-- Brightwater
local town = group("Brightwater")
do
	local x, y = 700, 620
	local r = Random.new(4)
	box(town, "Keep", x + 25, y - 30, Vector3.new(28, 60, 28), STONE)
	box(town, "KeepRoof", x + 25, y - 30, Vector3.new(30, 6, 30), ROOF, 0, 60)
	box(town, "KeepSpire", x + 25, y - 30, Vector3.new(8, 26, 8), ROOF, 0, 66)
	for k = 0, 3 do
		local a = k * math.pi / 2 + 0.4
		box(town, "KeepTower", x + 25 + math.cos(a) * 22, y - 30 + math.sin(a) * 22, Vector3.new(9, 36, 9), STONE)
	end
	for _ = 1, 26 do
		local a, d = r:NextNumber(0, math.pi * 2), r:NextNumber(28, 72)
		local hx, hy = x + math.cos(a) * d, y + math.sin(a) * d
		local onRoad = (math.abs(hy - y - (hx - x) * 0.11) < 12 and hx > x) or (math.abs(hx - x) < 12 and math.abs(hy - y) > 8)
		if (hx - x - 25) ^ 2 + (hy - y + 30) ^ 2 >= 30 ^ 2 and not onRoad then
			local hh = r:NextNumber(8, 13)
			box(town, "House", hx, hy, Vector3.new(r:NextNumber(9, 14), hh, r:NextNumber(8, 12)), STONE, a)
			box(town, "HouseRoof", hx, hy, Vector3.new(r:NextNumber(10, 15), 4, r:NextNumber(9, 13)), ROOF, a, hh)
		end
	end
	box(town, "Fountain", x, y + 10, Vector3.new(10, 3, 10), STONE)
	for k = 0, 23 do
		local a = k * math.pi * 2 / 24
		-- gaps where the three roads come in
		local deg = math.deg(a)
		if not (math.abs(deg - 90) < 8 or math.abs(deg - 270) < 8 or deg < 8 or deg > 352) then
			box(town, "Wall", x + math.cos(a) * 84, y + math.sin(a) * 84, Vector3.new(23, 9, 3), STONE, -a - math.pi / 2)
		end
	end
end
task.wait()

-- the Gate and its arena
local gate = group("Gate")
do
	local x, y = 1150, 230
	box(gate, "GateTowerL", x - 18, y, Vector3.new(10, 30, 10), STONE)
	box(gate, "GateTowerR", x + 18, y, Vector3.new(12, 38, 12), STONE)
	box(gate, "GateArch", x, y, Vector3.new(26, 6, 6), STONE, 0, 24)
	for k = 0, 6 do
		local a = k * math.pi * 2 / 7
		box(gate, "ArenaTower", x + math.cos(a) * 55, y + 25 + math.sin(a) * 45, Vector3.new(8, Random.new(k):NextNumber(10, 22), 8), STONE)
	end
end

-- bandit camp, ruins, cave, start stones, shrine, waystones
local sites = group("Sites")
for k = 0, 7 do
	local a = k * math.pi / 4
	box(sites, "Tent", 270 + math.cos(a) * 26, 620 + math.sin(a) * 26, Vector3.new(9, 6, 7), WOOD, -a)
end
for k = 0, 2 do
	box(sites, "Watchtower", 250 + k * 40, 545, Vector3.new(7, 22, 7), WOOD)
end
for k = 0, 4 do
	box(sites, "Ruin", 990 + k * 14, 560 + (k % 2) * 10, Vector3.new(10, 8 + 4 * (k % 3), 4), STONE)
end
box(sites, "CaveCliff", 520, 98, Vector3.new(70, 30, 18), Color3.fromRGB(110, 108, 102), 0, -2)
box(sites, "CaveMouth", 520, 109, Vector3.new(14, 12, 4), Color3.fromRGB(35, 32, 42))
for k = 0, 7 do
	local a = k * math.pi / 4
	box(sites, "StandingStone", 230 + math.cos(a) * 14, 1060 + math.sin(a) * 14, Vector3.new(2.5, 7, 2), STONE, -a)
end
box(sites, "Shrine", 330, 360, Vector3.new(8, 9, 8), STONE)
for _, w in WAYSTONES do
	box(sites, "Waystone", w[1], w[2], Vector3.new(2, 6, 2), Color3.fromRGB(95, 180, 200))
end
-- a player's height, to judge everything else by
box(sites, "PlayerSize", 245, 1040, Vector3.new(2, 5.2, 1), Color3.fromRGB(240, 200, 60))
task.wait()

-- bridges, simple slabs at the roads' height
local bridges = group("Bridges")
for _, b in BRIDGES do
	local rad = math.rad(b[3])
	local ex, ey = math.cos(rad) * b[4] / 2, math.sin(rad) * b[4] / 2
	local top = math.max((at(b[1] + ex, b[2] + ey)), (at(b[1] - ex, b[2] - ey)), 1)
	local p = Instance.new("Part")
	p.Name = "Bridge"
	p.Anchored = true
	p.Size = Vector3.new(b[4], 1.5, 14)
	p.Color = WOOD
	p.Material = Enum.Material.SmoothPlastic
	p.CFrame = CFrame.new(b[1] + C.Offset.X, top - 0.75, b[2] + C.Offset.Z) * CFrame.Angles(0, -rad, 0)
	p.Parent = bridges
end

-- labels
local labels = group("Labels")
for _, z in ZONES do
	label(labels, z.Name .. "  Lv " .. z.Levels, z.At[1], z.At[2], 60, Color3.new(1, 1, 1), 1500)
end
for _, p in PLACES do
	label(labels, p[1], p[2], p[3], p[4] and 20 or 34, p[4] and Color3.fromRGB(255, 150, 130) or Color3.fromRGB(255, 235, 170), 500)
	if p[4] then
		box(sites, "Boss", p[2], p[3], Vector3.new(10, 14, 10), Color3.fromRGB(120, 30, 30))
	end
end

-- which zone a map point falls in, the same way the design test decides
local function zoneAt(x, y)
	local best, bestD = nil, 1
	for _, z in ZONES do
		local d = ((x - z.At[1]) / z.Radius[1]) ^ 2 + ((y - z.At[2]) / z.Radius[2]) ^ 2
		if d <= bestD then
			best, bestD = z, d
		end
	end
	return best
end
-- no road, water, town or cliff within radius
local function clear(x, y, radius)
	for _, r in { 0, radius * 0.5, radius } do
		for k = 0, 7 do
			local a = k * math.pi / 4
			local _, m = at(x + math.cos(a) * r, y + math.sin(a) * r)
			if m >= 4 then
				return false
			end
		end
	end
	return true
end

-- camps: darts in each zone, four enemies round a faint fight circle
local rng = Random.new(C.Seed)
local counts = {}
local camps = group("Camps")
local placed = {}
for _ = 1, 9000 do
	local x, y = rng:NextNumber(0, 1400), rng:NextNumber(0, 1200)
	local z = zoneAt(x, y)
	if z and clear(x, y, C.CampRadius) then
		local ok = true
		for _, q in placed do
			if (q[1] - x) ^ 2 + (q[2] - y) ^ 2 < C.CampSpacing ^ 2 then
				ok = false
				break
			end
		end
		for _, p in PLACES do
			if (p[2] - x) ^ 2 + (p[3] - y) ^ 2 < 50 ^ 2 then
				ok = false
				break
			end
		end
		if ok then
			table.insert(placed, { x, y })
			counts[z.Name] = (counts[z.Name] or 0) + 1
			local f = Instance.new("Folder")
			f.Name = "Camp " .. z.Name
			local disc = box(f, "FightCircle", x, y, Vector3.new(0.3, C.CampRadius * 2, C.CampRadius * 2), ENEMY)
			disc.Shape = Enum.PartType.Cylinder
			disc.CFrame = CFrame.new(disc.Position.X, at(x, y) + 0.3, disc.Position.Z) * CFrame.Angles(0, 0, math.pi / 2)
			disc.CanCollide = false
			disc.CanQuery = false
			disc.Transparency = 0.75
			for k = 1, C.PackSize do
				local a = k * math.pi * 2 / C.PackSize + rng:NextNumber(-0.5, 0.5)
				local d = rng:NextNumber(6, 14)
				box(f, "Enemy", x + math.cos(a) * d, y + math.sin(a) * d, Vector3.new(3, 5, 3), ENEMY)
			end
			f.Parent = camps
		end
	end
end
task.wait()

-- trees, plain blocks at the zones' densities
local trees = group("Trees")
local treeCount = 0
local chunk = Instance.new("Folder")
chunk.Name = "Chunk"
for _ = 1, 1400 * 1200 // 400 do
	local x, y = rng:NextNumber(0, 1400), rng:NextNumber(0, 1200)
	local z = zoneAt(x, y)
	if z and rng:NextNumber() < z.Trees and clear(x, y, 7) then
		local s = rng:NextNumber(0.7, 1.25)
		box(chunk, "Tree", x, y, Vector3.new(7 * s, 30 * s, 7 * s), z.Tint, rng:NextNumber(0, 6.28), -0.5)
		treeCount += 1
		if treeCount % 150 == 0 then
			chunk.Parent = trees
			chunk = Instance.new("Folder")
			chunk.Name = "Chunk"
			task.wait()
		end
	end
end
chunk.Parent = trees

-- spawn at the Wake circle; the river scene's spawn is switched off, not removed (turn it back on, and ValeSpawn off, to test the river scene)
local spawnGround = at(230, 1060)
local spawn = Instance.new("SpawnLocation")
spawn.Name = "ValeSpawn"
spawn.Anchored = true
spawn.Size = Vector3.new(8, 1, 8)
spawn.Position = Vector3.new(230 + C.Offset.X, spawnGround + 0.2, 1060 + C.Offset.Z)
spawn.Neutral = true
spawn.Duration = 0
spawn.Color = STONE
spawn.Parent = root
local riverSpawn = workspace:FindFirstChild("SpawnLocation")
if riverSpawn then
	riverSpawn.Enabled = false
end

local report = { string.format("image %dx%d", W, H) }
for _, z in ZONES do
	table.insert(report, string.format("%s camps %d", z.Name, counts[z.Name] or 0))
end
table.insert(report, string.format("total camps %d, trees %d", #placed, treeCount))
local spawns = {}
for _, d in workspace:GetDescendants() do
	if d:IsA("SpawnLocation") then
		table.insert(spawns, d:GetFullName() .. (d.Enabled and " on" or " off"))
	end
end
table.insert(report, "spawns: " .. (#spawns > 0 and table.concat(spawns, ", ") or "none"))
return table.concat(report, "\n")
