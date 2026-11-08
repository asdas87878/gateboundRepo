-- Trees and understory from the leaf-card method (tools/blender/foliage_species.py, docs/style/forests.md) into ServerStorage.TreeKit: painted bark, a tinted leaf atlas per species, two soft lights on trees. Edit mode.

local LEAVES = { broad = "rbxassetid://114706624371586", small = "rbxassetid://126219577166496", needle = "rbxassetid://78301385694343" }
local KIT = {
	-- name, model id, bark id (nil for understory), leaf shape, leaf tint, limbs' bark id
	{ "Apple23", 87543043395626, 109369508255273, "broad", Color3.fromRGB(96, 178, 62), nil },
	{ "Apple7", 85766210309415, 107234221146658, "broad", Color3.fromRGB(96, 178, 62), nil },
	{ "Birch23", 89555260912102, 103812111277631, "small", Color3.fromRGB(128, 196, 84), nil },
	{ "Birch7", 104083516732091, 99441505692583, "small", Color3.fromRGB(128, 196, 84), nil },
	{ "Canopy23", 85751204192673, nil, "broad", Color3.fromRGB(46, 142, 84), nil },
	{ "Canopy7", 93609809931227, nil, "broad", Color3.fromRGB(46, 142, 84), nil },
	{ "Colossal23", 90187461631675, 90607658542641, "broad", Color3.fromRGB(54, 152, 88), 139345181243386 },
	{ "Colossal41", 96371832636520, 107264728730091, "broad", Color3.fromRGB(54, 152, 88), 139198736950977 },
	{ "Colossal7", 126260218585571, 137289736171097, "broad", Color3.fromRGB(54, 152, 88), 121424631318110 },
	{ "Elm23", 92706609546759, 97159483499166, "broad", Color3.fromRGB(44, 140, 84), nil },
	{ "Elm7", 122032546404454, 137461828677159, "broad", Color3.fromRGB(44, 140, 84), nil },
	{ "Fern", 99782822982764, nil, "needle", Color3.fromRGB(48, 140, 84), nil },
	{ "Giant23", 70844977831965, 99686460189780, "broad", Color3.fromRGB(50, 148, 86), nil },
	{ "Giant7", 110390815965535, 124362731928794, "broad", Color3.fromRGB(50, 148, 86), nil },
	{ "Oak23", 78979245816827, 125259950231956, "broad", Color3.fromRGB(60, 165, 80), nil },
	{ "Oak7", 112902963340989, 118228629776659, "broad", Color3.fromRGB(60, 165, 80), nil },
	{ "Pine23", 132891370729319, 90217395051755, "needle", Color3.fromRGB(44, 120, 92), nil },
	{ "Pine7", 113474010414971, 87876842958840, "needle", Color3.fromRGB(44, 120, 92), nil },
	{ "Sapling7", 105827297569130, 87004150296154, "small", Color3.fromRGB(88, 176, 70), nil },
	{ "ShrubBig", 125035663303661, nil, "broad", Color3.fromRGB(56, 150, 76), nil },
	{ "ShrubLow", 125565004252223, nil, "small", Color3.fromRGB(96, 180, 76), nil },
}

local function light(parent, name, position, colour, brightness, range)
	local anchor = Instance.new("Part")
	anchor.Name = name
	anchor.Anchored = true
	anchor.CanCollide, anchor.CanQuery, anchor.CanTouch = false, false, false
	anchor.Transparency = 1
	anchor.Size = Vector3.one
	anchor.Position = position
	local p = Instance.new("PointLight")
	p.Color = colour
	p.Brightness = brightness
	p.Range = range
	p.Shadows = false
	p.Parent = anchor
	anchor.Parent = parent
end

local old = game.ServerStorage:FindFirstChild("TreeKit")
if old then
	old:Destroy()
end
local kit = Instance.new("Folder")
kit.Name = "TreeKit"
for _, entry in KIT do
	local name, modelId, barkId, shape, tint, limbBark = entry[1], entry[2], entry[3], entry[4], entry[5], entry[6]
	local loaded = game:GetService("InsertService"):LoadAsset(modelId)
	local tree = Instance.new("Model")
	tree.Name = name
	local crown
	for _, d in loaded:GetDescendants() do
		if d:IsA("MeshPart") then
			local part = d:Clone()
			for _, c in part:GetChildren() do
				c:Destroy()
			end
			part.Anchored = true
			local sa = Instance.new("SurfaceAppearance")
			if string.find(d.Name, "Crown") then
				part.Name = "Crown"
				part.CanCollide, part.CanQuery, part.CanTouch = false, false, false
				sa.ColorMap = LEAVES[shape]
				sa.Color = tint
				sa.AlphaMode = Enum.AlphaMode.Transparency
				crown = part
			elseif string.find(d.Name, "Limbs") then
				part.Name = "Limbs"
				part.CanCollide = false
				sa.ColorMap = "rbxassetid://" .. limbBark
			else
				part.Name = "Trunk"
				sa.ColorMap = "rbxassetid://" .. barkId
			end
			sa.Parent = part
			part.Parent = tree
		end
	end
	loaded:Destroy()
	if barkId and not limbBark then
		-- the crown's two lights, by the numbers in docs/style/foliage-method.md
		local r = math.min(crown.Size.X, crown.Size.Z)
		light(tree, "LightInner", crown.Position - Vector3.new(0, crown.Size.Y * 0.05, 0), Color3.fromRGB(150, 175, 255), 0.5, r * 0.7)
		light(tree, "LightTop", crown.Position + Vector3.new(0, crown.Size.Y * 0.6, 0), Color3.fromRGB(205, 255, 175), 0.6, r * 0.7)
	elseif not string.find(name, "Canopy") and not limbBark then
		crown.CastShadow = false
	end
	tree.PrimaryPart = crown
	tree.Parent = kit
	task.wait()
end
kit.Parent = game.ServerStorage
return #kit:GetChildren()
