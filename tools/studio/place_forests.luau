-- Land 1's forests (docs/style/forests.md): the kit in ServerStorage.TreeKit placed on the real terrain, a forest type per area. Edit mode. Touches only trees: rebuilds Workspace.Land1.Forests and moves the old Land1.Trees to ServerStorage.Land1TreesOld.
-- Rerun after build_land_small.luau, which brings the old trees back. Trees keep off roads, water and rock (read from the terrain), and off the bridge, cottages, props and fences.

local OX = -6000
local AREAS = {
	HighWood = {
		{ 227, 147 },
		{ 1147, 120 },
		{ 1240, 320 },
		{ 1200, 533 },
		{ 1027, 707 },
		{ 720, 800 },
		{ 427, 827 },
		{ 227, 720 },
	},
	Thornwood = { { 1200, 1493 }, { 1627, 1347 }, { 1920, 1333 }, { 1933, 1893 }, { 1333, 1920 }, { 1160, 1733 } },
	Pines = {
		{ 1413, 120 },
		{ 1893, 120 },
		{ 1933, 667 },
		{ 1760, 867 },
		{ 1720, 827 },
		{ 1867, 480 },
		{ 1493, 507 },
		{ 1413, 627 },
	},
	Glade = { { 827, 1787 }, { 1147, 1747 }, { 1227, 1920 }, { 800, 1947 } },
	Grove = { { 80, 1093 }, { 333, 1107 }, { 333, 1360 }, { 80, 1360 } },
}
local ORCHARD = { X = 1660, Z = 1440, Across = 6, Down = 6, Spacing = 44 }
local FRAMES = {
	{ 253, 1447, 1.30 },
	{ 387, 1547, 1.00 },
	{ 693, 1347, 1.15 },
	{ 800, 1173, 0.80 },
	{ 933, 1067, 1.20 },
	{ 1207, 1013, 1.10 },
	{ 1313, 1147, 1.25 },
	{ 1347, 933, 1.20 },
	{ 1013, 1447, 0.90 },
	{ 653, 1547, 1.00 },
	{ 160, 1520, 1.10 },
}
local kit = game.ServerStorage.TreeKit
local land = workspace.Land1
for _, name in { "Forests", "TreeTest" } do
	local old = land:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end
local oldTrees = land:FindFirstChild("Trees")
if oldTrees then
	local store = game.ServerStorage:FindFirstChild("Land1TreesOld")
	if store then
		store:Destroy()
	end
	oldTrees.Name = "Land1TreesOld"
	oldTrees.Parent = game.ServerStorage
end
local root = Instance.new("Folder")
root.Name = "Forests"
root.Parent = land
local rng = Random.new(31)
local count, skipped = 0, 0

local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
params.FilterDescendantsInstances = { workspace.Terrain }
params.IgnoreWater = false
local function ground(x, z)
	local hit = workspace:Raycast(Vector3.new(x + OX, 1200, z), Vector3.new(0, -1400, 0), params)
	if hit then
		return hit.Position.Y, hit.Material
	end
	return nil
end
local BAD = {
	[Enum.Material.Water] = true,
	[Enum.Material.Mud] = true,
	[Enum.Material.Rock] = true,
	[Enum.Material.Sand] = true,
	[Enum.Material.Sandstone] = true,
}

-- what's already placed: keep trees off it
local keepOff = {}
local function addKeepOff(inst, extra)
	local cf, size
	if inst:IsA("Model") then
		cf, size = inst:GetBoundingBox()
	elseif inst:IsA("BasePart") then
		cf, size = inst.CFrame, inst.Size
	end
	if cf then
		table.insert(keepOff, { cf.X - OX, cf.Z, math.max(size.X, size.Z) / 2 + extra })
	end
end
for _, name in { "Cottages", "Props", "Fences" } do
	local f = land:FindFirstChild(name)
	if f then
		for _, c in f:GetChildren() do
			addKeepOff(c, 4)
		end
	end
end
if land:FindFirstChild("StoneBridge") then
	addKeepOff(land.StoneBridge, 16)
end
for _, b in land.Blocks:GetChildren() do
	if
		b.Name == "Planned"
		or b.Name == "Waystone"
		or b.Name == "Boss"
		or b.Name == "Rescue"
		or b.Name == "Secret"
		or b.Name == "Material"
	then
		addKeepOff(b, 8)
	end
end

local placed = {}
local function clearSpot(x, z, reach, spread, flat)
	local y, material = ground(x, z)
	if not y or BAD[material] then
		return nil
	end
	for i = 1, 8 do
		local a = i / 8 * math.pi * 2
		for _, r in { reach * 0.5, reach } do
			local gy, gm = ground(x + math.cos(a) * r, z + math.sin(a) * r)
			if not gy or BAD[gm] or math.abs(gy - y) > flat then
				return nil
			end
		end
	end
	for _, k in keepOff do
		if (k[1] - x) ^ 2 + (k[2] - z) ^ 2 < (k[3] + reach * 0.6) ^ 2 then
			return nil
		end
	end
	for _, p in placed do
		if (p[1] - x) ^ 2 + (p[2] - z) ^ 2 < (p[3] + spread) ^ 2 then
			return nil
		end
	end
	return y
end

local function put(folder, name, x, z, y, scale)
	local piece = kit[name]:Clone()
	piece:ScaleTo(scale)
	local cf, size = piece:GetBoundingBox()
	local pivot = piece:GetPivot()
	local rise = y - 0.5 - (cf.Y - size.Y / 2)
	piece:PivotTo(CFrame.new(x + OX, pivot.Y + rise, z) * CFrame.Angles(0, rng:NextNumber(0, 6.28), 0))
	piece.Parent = folder
	count += 1
	if count % 25 == 0 then
		workspace:SetAttribute("Land1ForestProgress", count)
		task.wait()
	end
	return piece
end

local function tree(folder, name, x, z, scale, reach, spread, flat)
	local y = clearSpot(x, z, reach, spread, flat)
	if not y then
		skipped += 1
		return nil
	end
	table.insert(placed, { x, z, spread })
	return put(folder, name, x, z, y, scale)
end

local function small(folder, name, x, z, scale)
	local y, material = ground(x, z)
	if y and not BAD[material] then
		put(folder, name, x, z, y, scale)
	end
end

local function pick(list)
	return list[rng:NextInteger(1, #list)]
end

local function inside(x, z, poly)
	local c = false
	for i = 1, #poly do
		local a, b = poly[i], poly[i % #poly + 1]
		if (a[2] > z) ~= (b[2] > z) and x < (b[1] - a[1]) * (z - a[2]) / (b[2] - a[2]) + a[1] then
			c = not c
		end
	end
	return c
end

local function bounds(poly)
	local x0, x1, z0, z1 = math.huge, -math.huge, math.huge, -math.huge
	for _, p in poly do
		x0, x1, z0, z1 = math.min(x0, p[1]), math.max(x1, p[1]), math.min(z0, p[2]), math.max(z1, p[2])
	end
	return x0, x1, z0, z1
end

-- a jittered grid across an area; the callback places what goes there
local function scatter(poly, spacing, keep, callback)
	local x0, x1, z0, z1 = bounds(poly)
	for gx = x0, x1, spacing do
		for gz = z0, z1, spacing do
			local x, z = gx + rng:NextNumber(-0.42, 0.42) * spacing, gz + rng:NextNumber(-0.42, 0.42) * spacing
			if rng:NextNumber() < keep and inside(x, z, poly) then
				callback(x, z)
			end
		end
	end
end

local function floor(folder, x, z, reach, ferns, shrubs, saplings)
	local function near()
		local a, d = rng:NextNumber(0, 6.28), rng:NextNumber(reach * 0.35, reach)
		return x + math.cos(a) * d, z + math.sin(a) * d
	end
	for _ = 1, ferns do
		local fx, fz = near()
		small(folder, "Fern", fx, fz, rng:NextNumber(1.2, 2.2))
	end
	for _ = 1, shrubs do
		local fx, fz = near()
		small(folder, "ShrubBig", fx, fz, rng:NextNumber(1.0, 1.8))
	end
	for _ = 1, saplings do
		local fx, fz = near()
		small(folder, "Sapling7", fx, fz, rng:NextNumber(1.0, 1.6))
	end
end

local function folderOf(name)
	local f = Instance.new("Folder")
	f.Name = name
	f.Parent = root
	return f
end

-- soft light where the wood is deep: most crowns let the sun through, and shafts along the sun's direction
local sun = game:GetService("Lighting"):GetSunDirection()
local function shafts(folder, poly, count_)
	local x0, x1, z0, z1 = bounds(poly)
	local made = 0
	for _ = 1, count_ * 8 do
		if made >= count_ then
			break
		end
		local x, z = rng:NextNumber(x0, x1), rng:NextNumber(z0, z1)
		local y = ground(x, z)
		if y and inside(x, z, poly) then
			made += 1
			local anchor = Instance.new("Part")
			anchor.Name = "Light"
			anchor.Anchored = true
			anchor.CanCollide, anchor.CanQuery, anchor.CanTouch = false, false, false
			anchor.Transparency = 1
			anchor.Size = Vector3.one
			anchor.Position = Vector3.new(x + OX, y + 20, z)
			local p = Instance.new("PointLight")
			p.Color, p.Brightness, p.Range, p.Shadows = Color3.fromRGB(222, 255, 150), 1.0, 45, false
			p.Parent = anchor
			local a0, a1 = Instance.new("Attachment"), Instance.new("Attachment")
			a0.Parent, a1.Parent = anchor, anchor
			a0.WorldPosition, a1.WorldPosition =
				Vector3.new(x + OX, y + 1, z), Vector3.new(x + OX, y + 1, z) + sun * 300
			local beam = Instance.new("Beam")
			beam.Attachment0, beam.Attachment1 = a0, a1
			beam.FaceCamera = true
			beam.Width0, beam.Width1 = rng:NextNumber(26, 44), rng:NextNumber(55, 90)
			beam.Texture = "rbxassetid://72272588546454"
			beam.TextureMode = Enum.TextureMode.Stretch
			beam.Color = ColorSequence.new(Color3.fromRGB(255, 244, 190))
			beam.LightEmission = 0.8
			beam.LightInfluence = 0
			beam.Transparency = NumberSequence.new({
				NumberSequenceKeypoint.new(0, 1),
				NumberSequenceKeypoint.new(0.18, 0.78),
				NumberSequenceKeypoint.new(0.65, 0.84),
				NumberSequenceKeypoint.new(1, 1),
			})
			beam.Parent = anchor
			anchor.Parent = folder
		end
	end
end

local function colossal(folder, x, z, scale)
	local t = tree(folder, pick({ "Colossal7", "Colossal23", "Colossal41" }), x, z, scale, 58, 150, 16)
	if t then
		if rng:NextNumber() < 0.68 then
			t.Crown.CastShadow = false
		end
		floor(folder, x, z, 100, 7, 3, 1)
	end
	return t
end

-- High Wood: the colossal wood on its plateau, seen from the whole valley
do
	local f = folderOf("HighWood")
	scatter(AREAS.HighWood, 205, 0.95, function(x, z)
		colossal(f, x, z, rng:NextNumber(0.9, 1.25))
	end)
	scatter(AREAS.HighWood, 62, 0.5, function(x, z)
		local t = tree(f, pick({ "Elm7", "Elm23", "Oak7", "Oak23" }), x, z, rng:NextNumber(0.7, 1.15), 11, 30, 9)
		if t then
			floor(f, x, z, 22, 2, 1, 0)
		end
	end)
	shafts(f, AREAS.HighWood, 10)
end
-- Thornwood: the deep wood, closest to the road, with a few colossals leading
do
	local f = folderOf("Thornwood")
	scatter(AREAS.Thornwood, 290, 0.8, function(x, z)
		if not (x > 1620 and z > 1400) then
			colossal(f, x, z, rng:NextNumber(0.75, 1.05))
		end
	end)
	scatter(AREAS.Thornwood, 46, 0.72, function(x, z)
		if not (x > 1620 and z > 1400) then
			local name = rng:NextNumber() < 0.3 and pick({ "Elm7", "Elm23" }) or pick({ "Oak7", "Oak23" })
			local t = tree(f, name, x, z, rng:NextNumber(0.8, 1.2), 11, 26, 8)
			if t then
				floor(f, x, z, 20, 2, 1, rng:NextNumber() < 0.35 and 1 or 0)
			end
		end
	end)
	shafts(f, AREAS.Thornwood, 8)
end
-- Pines on the falls plateau
do
	local f = folderOf("Pines")
	scatter(AREAS.Pines, 46, 0.82, function(x, z)
		local t = tree(f, pick({ "Pine7", "Pine23" }), x, z, rng:NextNumber(0.85, 1.3), 8, 26, 8)
		if t and rng:NextNumber() < 0.4 then
			floor(f, x, z, 14, 2, 0, 0)
		end
	end)
end
-- Birch glade on the south shoulder
do
	local f = folderOf("Glade")
	scatter(AREAS.Glade, 52, 0.62, function(x, z)
		local t = tree(f, pick({ "Birch7", "Birch23" }), x, z, rng:NextNumber(0.85, 1.3), 8, 24, 8)
		if t and rng:NextNumber() < 0.6 then
			small(f, "ShrubLow", x + rng:NextNumber(-14, 14), z + rng:NextNumber(-14, 14), rng:NextNumber(0.9, 1.4))
		end
	end)
end
-- A mixed grove behind the farm
do
	local f = folderOf("Grove")
	scatter(AREAS.Grove, 56, 0.6, function(x, z)
		local t = tree(f, pick({ "Oak7", "Oak23", "Birch7" }), x, z, rng:NextNumber(0.8, 1.15), 9, 26, 8)
		if t and rng:NextNumber() < 0.5 then
			small(f, "ShrubBig", x + rng:NextNumber(-16, 16), z + rng:NextNumber(-16, 16), rng:NextNumber(0.8, 1.3))
		end
	end)
end
-- The orchard on the Thornwood rise: planted rows, a few missing
do
	local f = folderOf("Orchard")
	for i = 0, ORCHARD.Across - 1 do
		for j = 0, ORCHARD.Down - 1 do
			if rng:NextNumber() < 0.9 then
				tree(
					f,
					pick({ "Apple7", "Apple23" }),
					ORCHARD.X + i * ORCHARD.Spacing + rng:NextNumber(-2.5, 2.5),
					ORCHARD.Z + j * ORCHARD.Spacing + rng:NextNumber(-2.5, 2.5),
					rng:NextNumber(0.9, 1.15),
					7,
					22,
					9
				)
			end
		end
	end
end
-- The hand-placed framing trees keep their spots for the key views
do
	local f = folderOf("Frames")
	for _, s in FRAMES do
		tree(f, pick({ "Oak7", "Oak23" }), s[1], s[2], s[3] * 0.85, 7, 12, 10)
	end
end
workspace:SetAttribute("Land1ForestProgress", nil)
local report = {}
for _, f in root:GetChildren() do
	local big = 0
	for _, c in f:GetChildren() do
		if string.find(c.Name, "Colossal") then
			big += 1
		end
	end
	table.insert(report, f.Name .. " " .. #f:GetChildren() .. " (" .. big .. " colossal)")
end
return string.format("%d placed, %d spots skipped. %s", count, skipped, table.concat(report, ", "))
