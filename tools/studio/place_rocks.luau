-- Places rocks from ServerStorage.RockKit against the river scene's cliffs, by the lesson's rules (docs/style/rock-kit.md); run in Studio's edit mode.
-- Large wide rocks fill the face, no piece repeats next to itself, each is turned and rescaled, an upper tier sits set back, flat stubby foot rocks
-- run slightly off parallel where the wall meets the ground, and small stones break up that line. Replaces Workspace.Rocks each time, so
-- hand-placed rocks belong in another folder. Change Seed for a new arrangement.

local CONFIG = {
	Seed = 5,
	Sides = { 1 }, -- 1 the path's side of the river, -1 the far side
	From = -135,
	To = 70,
	FaceYaw = 180, -- degrees added so a piece's low front lumps face the river
	UpperBase = 11, -- how far the upper tier's base sits above the walkable ground; its front hides behind the lower wall
	Lower = { "WallWide", "WallLong", "WallStep", "WallMid", "CliffWide", "WallHigh", "Block", "CliffTall" },
	Upper = { "WallWide", "WallMid", "CliffWide", "Block", "WallStep", "BlockChunk" },
	Foot = { "FootWide", "FootStub", "FootWedge", "SlabLong", "SlabBroken", "SlabStack", "BoulderWide", "BlockChunk" },
	Small = { "Stone", "BoulderSmall", "Chip", "ChipTall", "ChipFlat", "BoulderRound", "SlabSmall" },
}

local C = CONFIG
local kit = game:GetService("ServerStorage").RockKit
local r = Random.new(C.Seed)
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
	return 72 + 5 * math.noise(x / 38, side * 5.3, 7.9) -- matches build_terrain.luau's CliffAt
end
local function ground(x, z)
	local hit = workspace:Raycast(Vector3.new(x, 150, z), Vector3.new(0, -200, 0), params)
	return hit and hit.Position.Y or 0
end

-- DELETES Workspace.Rocks: anything moved by hand in there is lost. Back up first, or move hand-placed rocks to another folder.
local folder = workspace:FindFirstChild("Rocks")
if folder then
	folder:Destroy()
end
folder = Instance.new("Folder")
folder.Name = "Rocks"

local last = {}
local function pick(list, key)
	local name
	repeat
		name = list[r:NextInteger(1, #list)]
	until name ~= last[key]
	last[key] = name
	return name
end

local count = 0
-- baseY: an explicit height for the rock's base; otherwise it sits on the lowest ground under its footprint, so nothing hangs in the air
local function place(name, x, z, side, scale, sink, yawJitter, baseY)
	local src = kit[name]
	local c = src:Clone()
	c.Size *= scale
	local slope = (zc(x + 1) - zc(x - 1)) / 2
	local yaw = math.deg(math.atan2(-slope, 1)) + (side > 0 and 0 or 180) + C.FaceYaw + yawJitter
	local turned = CFrame.new(x, 0, z) * CFrame.Angles(0, math.rad(yaw), 0)
	local base = baseY
	if not base then
		base = ground(x, z)
		for _, u in ipairs({ { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 }, { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }) do
			local q = turned:PointToWorldSpace(Vector3.new(u[1] * c.Size.X * 0.45, 0, u[2] * c.Size.Z * 0.45))
			base = math.min(base, ground(q.X, q.Z))
		end
	end
	c.CFrame = turned + Vector3.new(0, base + c.Size.Y / 2 - sink, 0)
	c.Parent = folder
	count += 1
	return c
end

for _, side in ipairs(C.Sides) do
	local function zAt(x, d)
		return zc(x) + side * (hw(x) + d)
	end
	-- the lower wall: big pieces overlapping along the cliff's foot
	local x = C.From
	while x < C.To do
		local name = pick(C.Lower, "lower")
		local s = r:NextNumber(0.95, 1.3)
		local w = kit[name].Size.X * s
		x += w * 0.34
		place(name, x, zAt(x, cliffAt(x, side) + 3 + r:NextNumber(-1.5, 2)), side, s, 1.5, r:NextNumber(-14, 14))
		x += w * 0.34
	end
	-- the upper tier, set back, so the face reaches the cliff's top
	x = C.From + 8
	while x < C.To do
		local name = pick(C.Upper, "upper")
		local s = r:NextNumber(1.0, 1.4)
		local w = kit[name].Size.X * s
		x += w * 0.34
		place(name, x, zAt(x, cliffAt(x, side) + 8 + r:NextNumber(-1, 2)), side, s, 0, r:NextNumber(-18, 18), ground(x, zAt(x, cliffAt(x, side) - 4)) + C.UpperBase + r:NextNumber(-2, 2))
		x += w * 0.36
	end
	-- foot rocks: flatter, off parallel, gaps between them
	x = C.From
	while x < C.To do
		local name = pick(C.Foot, "foot")
		local s = r:NextNumber(0.9, 1.35)
		local w = kit[name].Size.X * s
		x += w * 0.5
		place(name, x, zAt(x, cliffAt(x, side) - 4 + r:NextNumber(-2, 1.5)), side, s, 0.6, r:NextNumber(-28, 28))
		x += w * 0.5 + r:NextNumber(-1, 6)
	end
	-- small stones in front, in loose groups
	x = C.From
	while x < C.To do
		x += r:NextNumber(5, 20)
		for _ = 1, r:NextInteger(1, 3) do
			local px = x + r:NextNumber(-3, 3)
			place(pick(C.Small, "small"), px, zAt(px, cliffAt(px, side) - 8 + r:NextNumber(-3, 2)), side, r:NextNumber(0.8, 1.5), 0.3, r:NextNumber(-180, 180))
		end
	end
end
folder.Parent = workspace
return "rocks " .. count
