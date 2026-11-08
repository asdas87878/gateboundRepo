-- The rock pack into the place (docs/style/rock-pack.md). Edit mode. Masters in ServerStorage.RockPack (Moss and Clean, one folder per group), and a shelf to copy from
-- at Workspace.RockPack (a Folder, so a click picks one rock), far from everything else: select its ShelfGround in the Explorer and press F to go there. Rerunning replaces both, nothing else.
-- DATA_JSON is filled in from art/kit/rock_pack/roblox.json by tools/art/rock_pack_luau.py.

local DATA_JSON = [==[__DATA__]==]

local SHELF_AT = Vector3.new(30000, 0, 0)
local TINT = Color3.fromRGB(222, 222, 216) -- as the earlier rocks: Studio's light is added on top of the paint
local GAP = 7
local ROW_GAP = 16
local AISLE_GAP = 40
-- the order and names on the shelf
local SHELVES = {
	{ "Clusters", { "Clusters" } },
	{ "Blocks", { "Cubes" } },
	{ "Modular", { "Modular" } },
	{ "Cliffs", { "Cliffs" } },
	{ "Loose", { "Boulders", "Slabs", "Spires", "Chips" } },
	{ "FromBefore", { "Classic", "Natural" } },
}

local HttpService = game:GetService("HttpService")
local data = HttpService:JSONDecode(DATA_JSON)
local ss = game:GetService("ServerStorage")

local meshes = {}
local loads = {}
for file, info in data.Files do
	if string.find(file, "^RockPack.*%.glb$") then
		local loaded = game:GetService("InsertService"):LoadAsset(info.Id)
		table.insert(loads, loaded)
		for _, d in loaded:GetDescendants() do
			if d:IsA("MeshPart") then
				meshes[d.Name] = d
			end
		end
	end
end

local function master(name, variant)
	local info = data.Pieces[name]
	local source = meshes[name]
	assert(source, "not in the upload: " .. name)
	local part = source:Clone()
	for _, c in part:GetChildren() do
		c:Destroy()
	end
	part.Anchored = true
	part.Material = Enum.Material.SmoothPlastic
	part.Color = Color3.new(1, 1, 1)
	part.PivotOffset = CFrame.new(0, -part.Size.Y / 2, 0) -- the pivot at its foot, so it sits and turns on the ground
	if part.Size.Y < 2 then
		part.CanCollide = false
	end
	local sa = Instance.new("SurfaceAppearance")
	sa.ColorMap = "rbxassetid://" .. data.Files["Pack_" .. info.Sheet .. "_" .. variant .. ".png"].Id
	sa.Color = TINT
	sa.Parent = part
	return part
end

local old = ss:FindFirstChild("RockPack")
if old then
	old:Destroy()
end
local oldShelf = workspace:FindFirstChild("RockPack")
if oldShelf then
	oldShelf:Destroy()
end

local masters = Instance.new("Folder")
masters.Name = "RockPack"
local shelf = Instance.new("Folder")
shelf.Name = "RockPack"

local function label(parent, text, position, size, reach)
	local anchor = Instance.new("Part")
	anchor.Name = text
	anchor.Anchored = true
	anchor.CanCollide, anchor.CanQuery, anchor.CanTouch = false, false, false
	anchor.Transparency = 1
	anchor.Size = Vector3.one
	anchor.Position = position
	local board = Instance.new("BillboardGui")
	board.Size = UDim2.fromOffset(size * 12, size * 2)
	board.AlwaysOnTop = true
	board.MaxDistance = reach
	local words = Instance.new("TextLabel")
	words.Size = UDim2.fromScale(1, 1)
	words.BackgroundTransparency = 1
	words.Text = text
	words.TextColor3 = Color3.new(1, 1, 1)
	words.TextStrokeTransparency = 0.3
	words.TextSize = size
	words.Font = Enum.Font.GothamBold
	words.Parent = board
	board.Parent = anchor
	anchor.Parent = parent
end

local labels = Instance.new("Folder")
labels.Name = "Labels"
labels.Parent = shelf

local total = 0
local z = SHELF_AT.Z
for _, variant in { "Moss", "Clean" } do
	local variantMasters = Instance.new("Folder")
	variantMasters.Name = variant
	variantMasters.Parent = masters
	local variantShelf = Instance.new("Folder")
	variantShelf.Name = variant
	variantShelf.Parent = shelf
	for _, entry in SHELVES do
		local title, groups = entry[1], entry[2]
		local names = {}
		for name, info in data.Pieces do
			if table.find(groups, info.Group) then
				table.insert(names, name)
			end
		end
		if #names > 0 then
			table.sort(names, function(a, b)
				local sa, sb = data.Pieces[a].Size, data.Pieces[b].Size
				return sa[1] * sa[2] * sa[3] < sb[1] * sb[2] * sb[3]
			end)
			local folder = Instance.new("Folder")
			folder.Name = title
			folder.Parent = variantMasters
			local rowFolder = Instance.new("Folder")
			rowFolder.Name = title
			local width = 0
			local depth = 0
			local parts = {}
			for _, name in names do
				local part = master(name, variant)
				part.Parent = folder
				local copy = part:Clone()
				width += copy.Size.X + GAP
				depth = math.max(depth, copy.Size.Z)
				table.insert(parts, copy)
			end
			local x = SHELF_AT.X - width / 2
			for _, copy in parts do
				copy.CFrame = CFrame.new(x + copy.Size.X / 2, SHELF_AT.Y + copy.Size.Y / 2, z + depth / 2)
				copy.Parent = rowFolder
				label(
					labels,
					copy.Name,
					Vector3.new(x + copy.Size.X / 2, SHELF_AT.Y + copy.Size.Y + 2, z + depth / 2),
					16,
					140
				)
				x += copy.Size.X + GAP
				total += 1
			end
			rowFolder.Parent = variantShelf
			label(
				labels,
				variant .. ": " .. title,
				Vector3.new(SHELF_AT.X - width / 2 - 8, SHELF_AT.Y + 6, z + depth / 2),
				26,
				900
			)
			z += depth + ROW_GAP
			task.wait()
		end
	end
	z += AISLE_GAP
end
for _, loaded in loads do
	loaded:Destroy()
end

local ground = Instance.new("Part")
ground.Name = "ShelfGround"
ground.Anchored = true
ground.Locked = true
ground.Material = Enum.Material.SmoothPlastic
ground.Color = Color3.fromRGB(60, 150, 80)
ground.Size = Vector3.new(420, 2, z - SHELF_AT.Z + 80)
ground.Position = SHELF_AT + Vector3.new(0, -1, (z - SHELF_AT.Z) / 2)
ground.Parent = shelf

masters.Parent = ss
shelf.Parent = workspace
return "placed " .. total .. " rocks on the shelf, far side z " .. z
