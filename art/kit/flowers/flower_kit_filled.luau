-- The flower beds into the place (docs/style/flower-beds.md). Edit mode. Run the filled copy that tools/art/upload_flower_kit.py --luau
-- writes, not this template. Rerunning replaces ServerStorage.FlowerKit, Workspace.FlowerShelf and the beds in the cobble shelf's example.
--
-- ServerStorage.FlowerKit: White, Pink and Mixed, the same five pieces each (the same meshes, another card texture). A piece is a Model:
-- Mound (the solid painted leaves) and Cards (painted flowers and leaves on planes, transparent). Its pivot is on the ground:
-- BedRound centred (fills a ring of 8 Curve6), BedLong at the start of its 8-stud centre line along +X (between straight edging runs
-- 5 apart), BedEnd at the middle of a long bed's rounded end (the half disc on its +X side), Clump and ClumpWide centred.
local DATA = game:GetService("HttpService"):JSONDecode([==[{"Files":{"FlowerKit.glb":86270853990990,"FlowerMound_Color.png":115658859510946,"FlowerCards_White.png":89217226365652,"FlowerCards_Pink.png":112623389099605,"FlowerCards_Mixed.png":137595934890202},"Pieces":{"BedRound":{"BedRound_Mound":[-4.9851,-5.0837,-1.056,4.8328,4.7869,1.9046],"BedRound_Cards":[-5.2068,-5.2253,-0.2511,5.1204,5.0079,2.3274]},"BedLong":{"BedLong_Mound":[-1.0076,-2.3232,-0.8978,9.4062,2.2795,1.4434],"BedLong_Cards":[-1.241,-2.5809,-0.3349,9.6779,2.4678,1.8672]},"BedEnd":{"BedEnd_Mound":[-0.7943,-2.2535,-0.7565,2.6633,1.9828,1.0314],"BedEnd_Cards":[-0.9659,-2.5756,-0.217,2.8464,2.2223,1.5994]},"Clump":{"Clump_Mound":[-1.5572,-1.3221,-0.696,1.4969,1.6538,0.8548],"Clump_Cards":[-1.8622,-1.6516,-0.262,1.8755,1.9724,1.3181]},"ClumpWide":{"ClumpWide_Mound":[-2.0935,-2.0485,-0.7427,2.5778,2.0387,0.9909],"ClumpWide_Cards":[-2.2952,-2.286,-0.2773,2.8015,2.2656,1.4671]}}}]==])
local SS = game:GetService("ServerStorage")
local SHELF = Vector3.new(30000, 0, 3160)

local function id(file)
	return "rbxassetid://" .. DATA.Files[file]
end

local loaded = game:GetService("InsertService"):LoadAsset(DATA.Files["FlowerKit.glb"])
local meshes = {}
for _, d in loaded:GetDescendants() do
	if d:IsA("MeshPart") then
		meshes[d.Name] = d
	end
end
local old = SS:FindFirstChild("FlowerKit")
if old then
	old:Destroy()
end
local kit = Instance.new("Folder")
kit.Name = "FlowerKit"
local report = { missing = {}, sizeWrong = {} }

local function part(meshName, box, colourMap, cards)
	local src = meshes[meshName]
	if not src then
		table.insert(report.missing, meshName)
		return nil
	end
	local p = src:Clone()
	for _, c in p:GetChildren() do
		c:Destroy()
	end
	local want = Vector3.new(box[4] - box[1], box[6] - box[3], box[5] - box[2])
	if (p.Size - want).Magnitude > 0.1 then
		report.sizeWrong[meshName] = string.format("%.2f %.2f %.2f, wanted %.2f %.2f %.2f", p.Size.X, p.Size.Y, p.Size.Z, want.X, want.Y, want.Z)
	end
	-- Blender (x, y, z) is Roblox (x, z, -y); the glb importer turns each mesh 180 degrees about its centre, so turn it back
	p.CFrame = CFrame.new((box[1] + box[4]) / 2, (box[3] + box[6]) / 2, -(box[2] + box[5]) / 2) * CFrame.Angles(0, math.pi, 0)
	p.Anchored = true
	p.CanCollide = false
	p.CanTouch = false
	p.CastShadow = false -- soft and bright, as the foliage test chose
	p.Material = Enum.Material.SmoothPlastic
	p.Color = Color3.new(1, 1, 1)
	p.Name = cards and "Cards" or "Mound"
	local sa = Instance.new("SurfaceAppearance")
	sa.ColorMap = colourMap
	if cards then
		sa.AlphaMode = Enum.AlphaMode.Transparency
	end
	sa.Parent = p
	return p
end

local names = {}
for name in DATA.Pieces do
	table.insert(names, name)
end
table.sort(names)
for _, variant in { "White", "Pink", "Mixed" } do
	local f = Instance.new("Folder")
	f.Name = variant
	for _, name in names do
		local boxes = DATA.Pieces[name]
		local m = Instance.new("Model")
		m.Name = name
		local mound = part(name .. "_Mound", boxes[name .. "_Mound"], id("FlowerMound_Color.png"), false)
		local cards = part(name .. "_Cards", boxes[name .. "_Cards"], id("FlowerCards_" .. variant .. ".png"), true)
		if mound and cards then
			mound.Parent = m
			cards.Parent = m
			-- a model with a PrimaryPart pivots on that part's pivot (WorldPivot is ignored), so the mound carries the piece's origin
			mound.PivotOffset = mound.CFrame:Inverse()
			m.PrimaryPart = mound
			m.Parent = f
		end
	end
	f.Parent = kit
end
loaded:Destroy()
kit.Parent = SS

-- a shelf row per colourway, beside the cobble shelf
local oldShelf = workspace:FindFirstChild("FlowerShelf")
if oldShelf then
	oldShelf:Destroy()
end
local shelf = Instance.new("Folder")
shelf.Name = "FlowerShelf"
local function label(parent, text, pos)
	local p = Instance.new("Part")
	p.Name = text
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Transparency = true, false, false, false, 1
	p.Size = Vector3.one
	p.Position = pos
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(200, 28)
	gui.AlwaysOnTop = true
	gui.MaxDistance = 300
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Font = Enum.Font.GothamBold
	t.TextSize = 14
	t.TextColor3 = Color3.new(1, 1, 1)
	t.TextStrokeTransparency = 0.3
	t.Text = text
	t.Parent = gui
	gui.Parent = p
	p.Parent = parent
end
local z = SHELF.Z
for _, variant in { "White", "Pink", "Mixed" } do
	local row = Instance.new("Folder")
	row.Name = variant
	row.Parent = shelf
	local x = SHELF.X - 140
	for _, m in kit[variant]:GetChildren() do
		local _, size = m:GetBoundingBox()
		local c = m:Clone()
		local offset = m.Name == "BedLong" and 0 or (m.Name == "BedEnd" and 0 or size.X / 2)
		c:PivotTo(CFrame.new(x + offset, SHELF.Y, z))
		c.Parent = row
		label(row, m.Name, Vector3.new(x + size.X / 2, SHELF.Y + 5, z))
		x += size.X + 8
	end
	label(row, variant, Vector3.new(SHELF.X - 155, SHELF.Y + 6, z))
	z += 16
end
local ground = Instance.new("Part")
ground.Name = "ShelfGround"
ground.Anchored = true
ground.Size = Vector3.new(420, 2, z - SHELF.Z + 20)
ground.Position = Vector3.new(SHELF.X + 40, SHELF.Y - 1, (SHELF.Z + z) / 2 - 8)
ground.Color = Color3.fromRGB(96, 160, 86)
ground.Material = Enum.Material.SmoothPlastic
ground.Parent = shelf
shelf.Parent = workspace

-- fill the cobble shelf's example beds, so the pieces are seen in their edging
local example = workspace:FindFirstChild("CobbleShelf") and workspace.CobbleShelf:FindFirstChild("Example")
if example then
	local paved = example:FindFirstChild("PavedArea")
	local old2 = example:FindFirstChild("Beds")
	if old2 then
		old2:Destroy()
	end
	local beds = Instance.new("Folder")
	beds.Name = "Beds"
	beds.Parent = example
	if paved then
		local x1 = paved.Position.X + paved.Size.X / 2
		local z1 = paved.Position.Z + paved.Size.Z / 2
		local function put(variant, name, cf)
			local c = kit[variant][name]:Clone()
			c:PivotTo(cf)
			c.Parent = beds
		end
		put("Mixed", "BedRound", CFrame.new(x1 + 22, 0, z1 - 6))
		local zc = z1 - 2 - 2.5
		put("White", "BedLong", CFrame.new(x1 + 40, 0, zc))
		put("White", "BedLong", CFrame.new(x1 + 48, 0, zc))
		put("White", "BedEnd", CFrame.new(x1 + 56, 0, zc))
		put("White", "BedEnd", CFrame.new(x1 + 40, 0, zc) * CFrame.Angles(0, math.pi, 0))
		put("Pink", "Clump", CFrame.new(x1 + 33, 0, z1 + 3))
		put("Mixed", "ClumpWide", CFrame.new(x1 + 4, 0, z1 + 5))
	end
end
game:GetService("ChangeHistoryService"):SetWaypoint("Add flower kit")
report.pieces = #kit:GetDescendants()
return game:GetService("HttpService"):JSONEncode(report)
