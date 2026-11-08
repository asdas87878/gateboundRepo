-- The cottage (docs/style/art-style.md) into the place: masters in ServerStorage.CottageKit, one test cottage in Workspace.Land1.Cottages on a grey-box house spot. Edit mode.
-- Each MeshPart is centred on its box, so its place is worked back from the OBJ bounds. Rerun after a new upload (ids below) or after build_land_small.luau.

local CONFIG = {
	Model = 87600941665104,
	Maps = {
		Frame = { Color = "rbxassetid://76865545123261" },
		Joinery = { Color = "rbxassetid://87519638304379" },
		Walls = { Color = "rbxassetid://110420407978391", Normal = "rbxassetid://82287525295595" },
		Roof = { Color = "rbxassetid://115717292589635" },
	},
	-- from the OBJs: { lowest x, y, z, highest x, y, z }, about the cottage's ground origin
	Bounds = {
		Frame = { -12.176, -0.59, -8.111, 12.91, 20.083, 8.358 },
		Joinery = { -11.89, 0.041, -6.837, 13.406, 22.901, 7.749 },
		Walls = { -11.35, -1.123, -6.85, 13.92, 21.925, 7.487 },
		Roof = { -11.985, 7.606, -7.783, 12.66, 19.665, 8.116 },
	},
	Spot = Vector3.new(-4847, 0, 1220), -- the grey-box house this one stands on
	Yaw = -95, -- degrees: for the test the door looks about 25 degrees off the sun (ClockTime 15.6), so its face is lit and its frame still throws shadows; the door faces local +z
	Sink = 0.2,
}
local C = CONFIG

local function kit()
	local old = game.ServerStorage:FindFirstChild("CottageKit")
	if old then
		old:Destroy()
	end
	local model = game:GetService("InsertService"):LoadAsset(C.Model)
	local folder = Instance.new("Folder")
	folder.Name = "CottageKit"
	for _, d in model:GetDescendants() do
		if d:IsA("MeshPart") then
			local key
			for name in C.Maps do
				if d.Name:find(name) then
					key = name
				end
			end
			assert(key, "unknown part " .. d.Name)
			local part = d:Clone()
			part.Name = key
			part.Anchored = true
			for _, c in part:GetChildren() do
				c:Destroy()
			end
			part.TextureID = ""
			local sa = Instance.new("SurfaceAppearance")
			sa.ColorMap = C.Maps[key].Color
			sa.NormalMap = C.Maps[key].Normal or ""
			sa.Parent = part
			-- only the walls' box blocks the player for now; a proper collider set comes with the real placement
			part.CanCollide = key == "Walls"
			part.CanTouch = false
			part.CastShadow = true
			part.Parent = folder
		end
	end
	folder.Parent = game.ServerStorage
	model:Destroy()
	return folder
end

local masters = kit()
local land = workspace.Land1
local old = land:FindFirstChild("Cottages")
if old then
	old:Destroy()
end
local holder = Instance.new("Folder")
holder.Name = "Cottages"
holder.Parent = land

-- ground: the mean of the footprint's corners, so the footing's sunk stud meets a slope
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
params.FilterDescendantsInstances = { workspace.Terrain }
local base = CFrame.new(C.Spot) * CFrame.Angles(0, math.rad(C.Yaw), 0)
local sum, n = 0, 0
for _, o in { { -10, -6 }, { 10, -6 }, { -10, 6 }, { 10, 6 }, { 0, 0 } } do
	local p = base:PointToWorldSpace(Vector3.new(o[1], 0, o[2]))
	local hit = workspace:Raycast(Vector3.new(p.X, 900, p.Z), Vector3.new(0, -1000, 0), params)
	if hit then
		sum += hit.Position.Y
		n += 1
	end
end
assert(n > 0, "no ground under the spot")
local ground = sum / n - C.Sink
local origin = base + Vector3.new(0, ground, 0)

local model = Instance.new("Model")
model.Name = "Cottage"
local report = { Ground = ground }
for _, m in masters:GetChildren() do
	local b = C.Bounds[m.Name]
	local part = m:Clone()
	-- the importer turns these meshes half way round their own centres (seen in Studio: the back wall faced where the door should), so each part is turned back
	part.CFrame = origin * CFrame.new((b[1] + b[4]) / 2, (b[2] + b[5]) / 2, (b[3] + b[6]) / 2) * CFrame.Angles(0, math.pi, 0)
	part.Parent = model
	report[m.Name] = string.format("size %.1f %.1f %.1f, expected %.1f %.1f %.1f", part.Size.X, part.Size.Y, part.Size.Z, b[4] - b[1], b[5] - b[2], b[6] - b[3])
end
model.Parent = holder

-- hide the grey boxes on this spot; build_land_small.luau brings them back
for _, b in land.Blocks:GetChildren() do
	if (b.Name == "Planned" or b.Name == "PlannedRoof") and (Vector3.new(b.Position.X, 0, b.Position.Z) - C.Spot).Magnitude < 5 then
		b.Transparency = 1
		b.CanCollide = false
	end
end
game:GetService("ChangeHistoryService"):SetWaypoint("Place test cottage")
return game:GetService("HttpService"):JSONEncode(report)
