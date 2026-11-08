-- Fence kit into the place (docs/style/art-style.md): masters in ServerStorage.FenceKit, sections along Land 1's fence lines in Workspace.Land1.Fences. Edit mode. Replaces the grey-box Fence blocks.
-- The lesson's placement rules: gaps, variation, leans. Rerun after build_land_small.luau, which brings the grey-box blocks back.

local CONFIG = {
	Model = 89979500277296,
	ColorMap = "rbxassetid://71253854507051",
	OffsetX = -6000,
	Lines = {
		{ { 333, 1167 }, { 520, 1153 }, { 533, 1287 }, { 353, 1300 }, { 333, 1167 } },
		{ { 567, 1127 }, { 733, 1113 }, { 747, 1240 }, { 580, 1253 } },
		{ { 460, 1347 }, { 667, 1253 } },
		{ { 747, 1233 }, { 893, 1147 } },
		{ { 1200, 1520 }, { 1387, 1580 } },
		{ { 1093, 1200 }, { 1067, 1347 } },
	},
	-- walked along each line in turn: a section, or Gap (studs of nothing)
	Pattern = { "FenceA", "FenceLean", "Gap", "FenceA", "FenceBroken", "Gap", "FenceLean", "FencePost", "Gap", "FenceA", "FenceA", "Gap", "FenceLean", "Gap" },
	Length = { FenceA = 10.4, FenceLean = 10.6, FenceBroken = 10.2, FencePost = 4 },
	GapLength = 16,
	Sink = 0.0, -- the kit's feet already reach 1 stud below its ground line
}
local C = CONFIG

local function kit()
	local old = game.ServerStorage:FindFirstChild("FenceKit")
	if old then
		old:Destroy()
	end
	local model = game:GetService("InsertService"):LoadAsset(C.Model)
	local folder = Instance.new("Folder")
	folder.Name = "FenceKit"
	for _, d in model:GetDescendants() do
		if d:IsA("MeshPart") then
			local part = d:Clone()
			part.Name = d.Name
			part.Anchored = true
			for _, c in part:GetChildren() do
				c:Destroy()
			end
			local sa = Instance.new("SurfaceAppearance")
			sa.ColorMap = C.ColorMap
			sa.Parent = part
			part.Parent = folder
		end
	end
	folder.Parent = game.ServerStorage
	model:Destroy()
	return folder
end

local masters = kit()
local land = workspace:FindFirstChild("Land1")
if not land then
	return "FenceKit only: this place has no Workspace.Land1 to fence"
end
for _, name in { "Fences", "FenceColourTest" } do
	local old = land:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end
for _, b in land.Blocks:GetChildren() do
	if b.Name == "Fence" then
		b:Destroy()
	end
end
local fences = Instance.new("Folder")
fences.Name = "Fences"
fences.Parent = land
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
params.FilterDescendantsInstances = { workspace.Terrain }
local function ground(x, z)
	local hit = workspace:Raycast(Vector3.new(x, 900, z), Vector3.new(0, -1000, 0), params)
	return hit and hit.Position.Y or 0, hit and hit.Material
end
local rng = Random.new(5)
local step = 0
local placed = 0
local sizes = {}
for _, m in masters:GetChildren() do
	sizes[m.Name] = m.Size
end
for _, line in C.Lines do
	for i = 1, #line - 1 do
		local a = Vector2.new(line[i][1] + C.OffsetX, line[i][2])
		local b = Vector2.new(line[i + 1][1] + C.OffsetX, line[i + 1][2])
		local dir = (b - a).Unit
		local length = (b - a).Magnitude
		local at = rng:NextNumber(0, 5)
		while at < length do
			step += 1
			local name = C.Pattern[(step - 1) % #C.Pattern + 1]
			if name == "Gap" then
				at += C.GapLength * rng:NextNumber(0.7, 1.4)
			else
				local L = C.Length[name]
				if at + L > length then
					break
				end
				local mid = a + dir * (at + L / 2)
				local off = rng:NextNumber(-1.2, 1.2)
				local cx, cz = mid.X - dir.Y * off, mid.Y + dir.X * off
				local h0 = ground(cx - dir.X * L / 2, cz - dir.Y * L / 2)
				local h1 = ground(cx + dir.X * L / 2, cz + dir.Y * L / 2)
				local h, mat = ground(cx, cz)
				if mat ~= Enum.Material.Water and mat ~= Enum.Material.Mud then
					local part = masters[name]:Clone()
					local yaw = -math.atan2(dir.Y, dir.X) + rng:NextNumber(-0.09, 0.09)
					if rng:NextNumber() < 0.5 then
						yaw += math.pi -- either face to the road
					end
					local tilt = rng:NextNumber(-0.04, 0.04)
					local base = math.min(h, (h0 + h1) / 2) - C.Sink
					part.CFrame = CFrame.new(cx, base - 1 + part.Size.Y / 2, cz) * CFrame.Angles(0, yaw, 0) * CFrame.Angles(tilt, 0, 0)
					part.Parent = fences
					placed += 1
				end
				at += L + rng:NextNumber(0.2, 2.5)
			end
		end
	end
end
local out = { placed = placed, masters = #masters:GetChildren() }
for n, s in sizes do
	out[n] = string.format("%.1f %.1f %.1f", s.X, s.Y, s.Z)
end
return game:GetService("HttpService"):JSONEncode(out)
