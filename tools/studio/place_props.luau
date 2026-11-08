-- Props kit into the place (docs/style/art-style.md): masters in ServerStorage.PropsKit, a test row in front of a fence line in Workspace.Land1.Props. Edit mode.
-- The row is for judging the set beside the fence, with loose gaps and turns; it isn't the final scatter.

local CONFIG = {
	Model = 128094429859101,
	ColorMap = "rbxassetid://121270248937308",
	-- from the OBJs: lowest and highest y, then x and z extents, about the prop's ground origin. Each MeshPart is centred on its box, so the origin has to be worked back from these.
	Bounds = {
		BarrelA = { -0.3, 3.83, -1.47, 1.49, -1.46, 1.47 },
		BarrelOpen = { -0.26, 3.38, -1.61, 1.64, -1.61, 1.63 },
		BarrelPile = { -0.3, 3.83, -4.87, 2.62, -2.78, 6.06 },
		CrateA = { -0.27, 3.06, -1.79, 1.79, -1.84, 1.8 },
		CrateSmall = { -0.2, 2.22, -1.34, 1.35, -1.29, 1.37 },
		CrateBroken = { -0.42, 3.42, -4.06, 2.68, -1.89, 3.63 },
		CrateStack = { -0.27, 5.64, -3.31, 4.28, -2.06, 4.71 },
		Cart = { -0.1, 6.02, -4.85, 9.77, -3.86, 3.92 },
		CartBroken = { -0.35, 5.03, -5.44, 9.9, -4.09, 6.13 },
		SignPost = { -0.91, 7.54, -3.39, 4.1, -0.55, 1.32 },
		SignLean = { -1.0, 6.79, -3.41, 1.59, -0.49, 1.13 },
	},
	-- the test row: name, world x, world z, yaw in degrees
	Row = {
		{ "SignPost", -5664, 1176, 8 },
		{ "BarrelA", -5655, 1174, 20 },
		{ "BarrelOpen", -5649, 1178, -40 },
		{ "BarrelPile", -5638, 1176, 15 },
		{ "CrateA", -5626, 1173, 25 },
		{ "CrateSmall", -5620, 1178, -15 },
		{ "CrateStack", -5610, 1175, 10 },
		{ "CrateBroken", -5597, 1177, -20 },
		{ "Cart", -5578, 1177, 12 },
		{ "CartBroken", -5552, 1176, -10 },
		{ "SignLean", -5536, 1174, 5 },
	},
}
local C = CONFIG

local function kit()
	local old = game.ServerStorage:FindFirstChild("PropsKit")
	if old then
		old:Destroy()
	end
	local model = game:GetService("InsertService"):LoadAsset(C.Model)
	local folder = Instance.new("Folder")
	folder.Name = "PropsKit"
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
	return "PropsKit only: this place has no Workspace.Land1 for the test row"
end
local old = land:FindFirstChild("Props")
if old then
	old:Destroy()
end
local props = Instance.new("Folder")
props.Name = "Props"
props.Parent = land
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
params.FilterDescendantsInstances = { workspace.Terrain }
local placed, heights = 0, {}
for _, row in C.Row do
	local name, x, z, yaw = row[1], row[2], row[3], row[4]
	local hit = workspace:Raycast(Vector3.new(x, 900, z), Vector3.new(0, -1000, 0), params)
	local ground = hit and hit.Position.Y or 0
	local master = masters:FindFirstChild(name)
	if master then
		local b = C.Bounds[name]
		local centre = Vector3.new((b[3] + b[4]) / 2, (b[1] + b[2]) / 2, (b[5] + b[6]) / 2)
		local part = master:Clone()
		part.CFrame = CFrame.new(x, ground, z) * CFrame.Angles(0, math.rad(yaw), 0) * CFrame.new(centre)
		part.Parent = props
		placed += 1
		heights[name] = string.format("%.1f h %.1f", ground, part.Size.Y)
	end
end
local out = { placed = placed, masters = #masters:GetChildren(), heights = heights }
return game:GetService("HttpService"):JSONEncode(out)
