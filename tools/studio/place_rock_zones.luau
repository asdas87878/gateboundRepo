-- Step 2 of the rocks: fills the river scene's other areas from ServerStorage.RockKit; run in Studio's edit mode (docs/style/rock-kit.md).
-- Each zone rebuilds only its own folder, Workspace.Rocks_<Zone>. It never touches Workspace.Rocks or anything else, so hand-placed rocks there are safe.
-- List only the zones you want in Run. Moving rocks inside a Rocks_<Zone> folder by hand: take that zone off Run first.

local CONFIG = {
	Run = { "Shore", "Water" }, -- NearMore, Far, End are done: naming them again rebuilds them
	Seed = 11,
	WaterLevel = 8,
	Lower = { "WallWide", "WallLong", "WallStep", "WallMid", "CliffWide", "WallHigh", "Block", "CliffTall" },
	Upper = { "WallWide", "WallMid", "CliffWide", "Block", "WallStep", "BlockChunk" },
	Foot = { "FootWide", "FootStub", "FootWedge", "SlabLong", "SlabBroken", "SlabStack", "BoulderWide", "BlockChunk" },
	Small = { "Stone", "BoulderSmall", "Chip", "ChipTall", "ChipFlat", "BoulderRound", "SlabSmall" },
	Tiny = { "Chip", "ChipFlat", "ChipTall", "Stone" },
	TinyBig = { "Stone", "BoulderSmall", "BoulderRound", "ChipTall" },
	-- deliberate spots on the banks' bends: x, side, studs up the bank from the waterline, stones in the group
	ShoreSpots = {
		{ -168, 1, 1.5, 3 }, { -112, 1, 0.5, 3 }, { -74, 1, 2, 1 }, { -8, 1, 0.5, 3 }, { 46, 1, 1, 3 }, { 108, 1, 0.5, 5 },
		{ -148, -1, 1, 3 }, { -92, -1, 0.5, 5 }, { -36, -1, 2, 1 }, { 22, -1, 0.5, 3 }, { 78, -1, 1.5, 3 }, { 136, -1, 0.5, 3 },
	},
	Stepping = { -26, 1, 5 }, -- x, side, stones
	WaterSpots = { { -128, -1, 5 }, { 62, 1, 6 }, { 118, -1, 4 } }, -- x, side, studs out from the waterline
	Near = { UpperBase = 11, Ranges = { { -198, -135 }, { 70, 162 } } },
	FarSide = { UpperBase = 9, Ranges = { { -198, 162 } } },
	TreeClear = 9, -- no shore rock this close to a tree
	PlainZones = { Shore = true, Water = true }, -- wet rocks grow no moss: these get the plain sheet
	-- moss sheet -> plain sheet, per atlas
	PlainMap = {
		["rbxassetid://137931462822661"] = "rbxassetid://128940563516709",
		["rbxassetid://88463318686619"] = "rbxassetid://111834703646301",
		["rbxassetid://101459269225189"] = "rbxassetid://101267229971765",
		["rbxassetid://78314945448041"] = "rbxassetid://130648739309181",
		["rbxassetid://123578232466712"] = "rbxassetid://84250033846591",
	},
}

local C = CONFIG
local kit = game:GetService("ServerStorage").RockKit
local t = workspace.Terrain
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
params.FilterDescendantsInstances = { t }
params.IgnoreWater = true

local function zc(x)
	return 16 * math.sin(x / 58) + 7 * math.sin(x / 23 + 1.3)
end
local function hw(x)
	return 24 + 8 * math.sin(x / 41 + 0.6)
end
local function cliffAt(x, side)
	return 72 + 5 * math.noise(x / 38, side * 5.3, 7.9)
end
local function ground(x, z)
	local hit = workspace:Raycast(Vector3.new(x, 150, z), Vector3.new(0, -200, 0), params)
	return hit and hit.Position.Y or 0
end

local trees = {}
local foliage = workspace:FindFirstChild("Foliage")
if foliage then
	for _, m in ipairs(foliage:GetChildren()) do
		if m:IsA("Model") and m:FindFirstChild("Trunk") then
			table.insert(trees, m.Trunk.Position)
		end
	end
end
local function nearTree(x, z)
	for _, p in ipairs(trees) do
		if (Vector3.new(p.X, 0, p.Z) - Vector3.new(x, 0, z)).Magnitude < C.TreeClear then
			return true
		end
	end
	return false
end

local report = {}
local function zone(name, build)
	local keep = workspace:FindFirstChild("Rocks_" .. name)
	if keep then
		keep:Destroy()
	end
	local folder = Instance.new("Folder")
	folder.Name = "Rocks_" .. name
	local r = Random.new(C.Seed + #name * 7)
	local last, count = {}, 0
	local function pick(list, key)
		local n
		repeat
			n = list[r:NextInteger(1, #list)]
		until n ~= last[key]
		last[key] = n
		return n
	end
	-- yaw in degrees: 0 faces +z. baseY optional, otherwise the lowest ground under the footprint
	local function place(piece, x, z, yaw, scale, sink, baseY)
		local c = kit[piece]:Clone()
		c.Size *= scale
		local turned = CFrame.new(x, 0, z) * CFrame.Angles(0, math.rad(yaw), 0)
		local base = baseY
		if not base then
			base = ground(x, z)
			for _, u in ipairs({ { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 }, { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }) do
				local q = turned:PointToWorldSpace(Vector3.new(u[1] * c.Size.X * 0.45, 0, u[2] * c.Size.Z * 0.45))
				base = math.min(base, ground(q.X, q.Z))
			end
		end
		if C.PlainZones[name] then
			local sa = c.SurfaceAppearance
			sa.ColorMap = C.PlainMap[sa.ColorMap] or sa.ColorMap
		end
		c.CanCollide = c.Size.Y > 2 -- tiny stones never trip a player
		c.CFrame = turned + Vector3.new(0, base + c.Size.Y / 2 - sink, 0)
		c.Parent = folder
		count += 1
	end
	build(r, pick, place)
	folder.Parent = workspace
	table.insert(report, name .. " " .. count)
	task.wait()
end

-- the same recipe as the path-side wall: lower wall, set-back upper tier, foot rocks off parallel, small stones
local function wall(side, cfg, r, pick, place)
	local function zAt(x, d)
		return zc(x) + side * (hw(x) + d)
	end
	local function face(x)
		return math.deg(math.atan2(-(zc(x + 1) - zc(x - 1)) / 2, 1)) + (side > 0 and 180 or 0)
	end
	for _, range in ipairs(cfg.Ranges) do
		local a, b = range[1], range[2]
		local x = a
		while x < b do
			local n = pick(C.Lower, "lower")
			local s = r:NextNumber(0.95, 1.3)
			local w = kit[n].Size.X * s
			x += w * 0.34
			place(n, x, zAt(x, cliffAt(x, side) + 3 + r:NextNumber(-1.5, 2)), face(x) + r:NextNumber(-14, 14), s, 1.5)
			x += w * 0.34
		end
		x = a + 8
		while x < b do
			local n = pick(C.Upper, "upper")
			local s = r:NextNumber(1.0, 1.4)
			local w = kit[n].Size.X * s
			x += w * 0.34
			local baseY = ground(x, zAt(x, cliffAt(x, side) - 4)) + cfg.UpperBase + r:NextNumber(-2, 2)
			place(n, x, zAt(x, cliffAt(x, side) + 8 + r:NextNumber(-1, 2)), face(x) + r:NextNumber(-18, 18), s, 0, baseY)
			x += w * 0.36
		end
		x = a
		while x < b do
			local n = pick(C.Foot, "foot")
			local s = r:NextNumber(0.9, 1.35)
			local w = kit[n].Size.X * s
			x += w * 0.5
			place(n, x, zAt(x, cliffAt(x, side) - 4 + r:NextNumber(-2, 1.5)), face(x) + r:NextNumber(-28, 28), s, 0.6)
			x += w * 0.5 + r:NextNumber(-1, 6)
		end
		x = a
		while x < b do
			x += r:NextNumber(5, 20)
			for _ = 1, r:NextInteger(1, 3) do
				local px = x + r:NextNumber(-3, 3)
				place(pick(C.Small, "small"), px, zAt(px, cliffAt(px, side) - 8 + r:NextNumber(-3, 2)), r:NextNumber(-180, 180), r:NextNumber(0.8, 1.5), 0.3)
			end
		end
	end
end

local ZONES = {}
function ZONES.NearMore(r, pick, place)
	wall(1, C.Near, r, pick, place)
end
function ZONES.Far(r, pick, place)
	wall(-1, C.FarSide, r, pick, place)
end
function ZONES.End(r, pick, place)
	-- across the river's closed end, facing back along it
	local z = -150
	while z < 150 do
		local n = pick(C.Lower, "lower")
		local s = r:NextNumber(1.05, 1.4)
		local w = kit[n].Size.X * s
		z += w * 0.34
		place(n, 166 + r:NextNumber(-2, 2), z, -90 + r:NextNumber(-14, 14), s, 1.5)
		z += w * 0.34
	end
	z = -145
	while z < 150 do
		local n = pick(C.Upper, "upper")
		local s = r:NextNumber(1.1, 1.5)
		local w = kit[n].Size.X * s
		z += w * 0.34
		place(n, 174 + r:NextNumber(-1, 2), z, -90 + r:NextNumber(-18, 18), s, 0, 14 + r:NextNumber(-2, 3))
		z += w * 0.36
	end
	z = -150
	while z < 150 do
		local n = pick(C.Foot, "foot")
		local s = r:NextNumber(0.95, 1.4)
		local w = kit[n].Size.X * s
		z += w * 0.5
		place(n, 157 + r:NextNumber(-2.5, 2), z, -90 + r:NextNumber(-28, 28), s, 0.6)
		z += w * 0.5 + r:NextNumber(0, 6)
	end
end
-- the waterline on a bank at x, found by walking out from the river's middle
local function waterline(x, side)
	local d = hw(x) * 0.5
	while d < hw(x) + 40 and ground(x, zc(x) + side * d) < C.WaterLevel do
		d += 0.5
	end
	return d
end
-- a tight group, biggest first: odd numbers, the small ones huddled against the big one on its land side or in the water
local function group(r, pick, place, x, z, side, count)
	for i = 1, count do
		local big = i == 1
		local a = r:NextNumber(0, math.pi * 2)
		local reach = big and 0 or r:NextNumber(1.8, 3.6)
		local px, pz = x + math.cos(a) * reach, z + math.sin(a) * reach
		local piece = big and pick(C.TinyBig, "tb") or pick(C.Tiny, "t")
		place(piece, px, pz, r:NextNumber(-180, 180), big and r:NextNumber(0.75, 1.05) or r:NextNumber(0.45, 0.8), 0.25)
	end
end
function ZONES.Shore(r, pick, place)
	for _, spot in ipairs(C.ShoreSpots) do
		local x, side = spot[1], spot[2]
		local z = zc(x) + side * (waterline(x, side) + spot[3])
		if not nearTree(x, z) then
			group(r, pick, place, x, z, side, spot[4])
		end
	end
end
function ZONES.Water(r, pick, place)
	-- stepping stones: one short run from a bank, tops just above the water
	local x0 = C.Stepping[1]
	local side = C.Stepping[2]
	local d = waterline(x0, side)
	for i = 0, C.Stepping[3] - 1 do
		local u = d - 1 - i * 5.2
		local px = x0 + i * 1.6 + r:NextNumber(-0.5, 0.5)
		local name = i % 2 == 0 and "BoulderRound" or "Stone"
		local scale = r:NextNumber(0.62, 0.8)
		local h = kit[name].Size.Y * scale
		place(name, px, zc(px) + side * u, r:NextNumber(-180, 180), scale, 0, C.WaterLevel + 0.5 - h)
	end
	-- a very few lone stones, each beside something
	for _, spot in ipairs(C.WaterSpots) do
		local x, sd = spot[1], spot[2]
		local z = zc(x) + sd * (waterline(x, sd) - spot[3])
		local scale = r:NextNumber(0.6, 0.85)
		local name = pick({ "Stone", "BoulderSmall" }, "w")
		place(name, x, z, r:NextNumber(-180, 180), scale, 0, C.WaterLevel + 0.45 - kit[name].Size.Y * scale)
	end
end

for _, name in ipairs(C.Run) do
	zone(name, ZONES[name])
end
return table.concat(report, ", ")
