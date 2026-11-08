-- The cobble kit into the place (docs/style/cobble-kit.md). Edit mode. Run the filled copy that tools/art/upload_cobble_kit.py --luau
-- writes, not this template. Rerunning replaces ServerStorage.CobbleKit, MaterialService.HubPaving and Workspace.CobbleShelf, nothing else.
--
-- ServerStorage.CobbleKit: Edging (the blue-grey chiselled bed stones), EdgingMoss (the same, mossy), Border (one row of fitted stones for
-- paved areas). Every piece's pivot is the start of its run, on the ground: drag it, and it turns about that point. A straight runs
-- along its +X (8, 4 or 2 studs); a curve turns left (its Chain attribute: radius, degrees); turned 180 degrees it turns right.
-- Paved areas: any Part with Material Slate and MaterialVariant "HubPaving" (the flagstone tile, 16 studs a repeat).
-- To see it all: select Workspace.CobbleShelf.ShelfGround and press F (beside the other shelves, near x 30,000).
local DATA = game:GetService("HttpService"):JSONDecode([==[{"Files":{"CobbleKit.glb":124856872279365,"Cobble_ChiselSlate_Color.png":99402376533870,"Cobble_ChiselSlate_Moss.png":126792971795392,"Cobble_SettCool_Color.png":106917688319368,"Paving_Color.png":94498325986612},"Pieces":{"Chisel_Stone1":{"Style":"Chisel","Box":[-0.7333,-0.4876,-0.3461,0.7489,0.4826,0.4347],"Chain":null},"Chisel_Stone2":{"Style":"Chisel","Box":[-1.0284,-0.7591,-0.3531,1.0221,0.7855,0.6299],"Chain":null},"Chisel_Stone3":{"Style":"Chisel","Box":[-1.0818,-1.2148,-0.3427,1.1358,1.212,0.7122],"Chain":null},"Chisel_Stone4":{"Style":"Chisel","Box":[-1.5301,-0.8017,-0.3618,1.5092,0.7931,0.8164],"Chain":null},"Chisel_Stone5":{"Style":"Chisel","Box":[-0.603,-0.8443,-0.33,0.6029,0.8568,0.7966],"Chain":null},"Chisel_Straight8A":{"Style":"Chisel","Box":[-0.0221,-0.5674,-0.3688,7.8755,0.499,0.7287],"Chain":[8]},"Chisel_Straight8B":{"Style":"Chisel","Box":[-0.0117,-0.5674,-0.3473,7.7854,0.5392,0.6686],"Chain":[8]},"Chisel_Curve6":{"Style":"Chisel","Box":[0.0697,-0.5115,-0.3548,4.3585,1.8748,0.7646],"Chain":[6,45]},"Chisel_Curve12":{"Style":"Chisel","Box":[0.0146,-0.5399,-0.3535,6.103,1.8164,0.7478],"Chain":[12,30]},"Chisel_Curve24":{"Style":"Chisel","Box":[0.0177,-0.4075,-0.3418,6.1642,1.1537,0.8228],"Chain":[24,15]},"Chisel_Corner":{"Style":"Chisel","Box":[-0.0865,-0.5161,-0.3682,3.0206,2.5177,0.6736],"Chain":[2.5,90]},"Chisel_Cluster":{"Style":"Chisel","Box":[-2.2386,-2.067,-0.4661,2.4117,1.9091,0.8114],"Chain":null},"Sett_Single":{"Style":"Sett","Box":[-0.9653,-0.664,-0.0994,0.9666,0.6656,0.4377],"Chain":null},"Sett_Row8A":{"Style":"Sett","Box":[0.0313,-0.7154,-0.1198,7.9589,0.7352,0.5026],"Chain":[8]},"Sett_Row8B":{"Style":"Sett","Box":[-0.0013,-0.6292,-0.11,7.9781,0.6671,0.5029],"Chain":[8]},"Sett_Row4":{"Style":"Sett","Box":[0.0021,-0.7273,-0.1217,3.9717,0.7155,0.4449],"Chain":[4]},"Sett_Row2":{"Style":"Sett","Box":[0.1398,-0.671,-0.1014,1.8141,0.6309,0.4537],"Chain":[2]},"Sett_Curve8":{"Style":"Sett","Box":[-0.0266,-0.72,-0.1165,5.9719,2.7307,0.4739],"Chain":[8,45]},"Sett_Curve16":{"Style":"Sett","Box":[-0.033,-0.7555,-0.1164,6.3037,1.7555,0.478],"Chain":[16,22.5]},"Sett_Curve32":{"Style":"Sett","Box":[0.0464,-0.623,-0.1207,6.2115,1.2025,0.4523],"Chain":[32,11.25]},"Sett_Corner":{"Style":"Sett","Box":[-0.6672,-0.6444,-0.1016,0.6606,0.6633,0.4448],"Chain":[2.5,90]},"Sett_Cluster":{"Style":"Sett","Box":[-2.3463,-1.9416,-0.2046,2.4335,1.7615,0.476],"Chain":null}}}]==])
local SS = game:GetService("ServerStorage")
local TINT = Color3.fromRGB(222, 222, 216) -- as the rock pack: Studio's light adds to the paint
local SHELF = Vector3.new(30000, 0, 3020)

local function id(file)
	return "rbxassetid://" .. DATA.Files[file]
end

-- the paving material
local MS = game:GetService("MaterialService")
local oldVariant = MS:FindFirstChild("HubPaving")
if oldVariant then
	oldVariant:Destroy()
end
local paving = Instance.new("MaterialVariant")
paving.Name = "HubPaving"
paving.BaseMaterial = Enum.Material.Slate
paving.ColorMap = id("Paving_Color.png")
paving.StudsPerTile = 16
paving.MaterialPattern = Enum.MaterialPattern.Regular
paving.Parent = MS

-- the masters
local loaded = game:GetService("InsertService"):LoadAsset(DATA.Files["CobbleKit.glb"])
local meshes = {}
for _, d in loaded:GetDescendants() do
	if d:IsA("MeshPart") then
		meshes[d.Name] = d
	end
end
local old = SS:FindFirstChild("CobbleKit")
if old then
	old:Destroy()
end
local kit = Instance.new("Folder")
kit.Name = "CobbleKit"
local report = { missing = {}, sizeWrong = {} }

local function master(name, colourMap, collide)
	local src = meshes[name]
	if not src then
		table.insert(report.missing, name)
		return nil
	end
	local part = src:Clone()
	for _, c in part:GetChildren() do
		c:Destroy()
	end
	local info = DATA.Pieces[name]
	local b = info.Box -- Blender: x y z min, then max (z up)
	local want = Vector3.new(b[4] - b[1], b[6] - b[3], b[5] - b[2])
	if (part.Size - want).Magnitude > 0.1 then
		report.sizeWrong[name] = string.format("%.2f %.2f %.2f, wanted %.2f %.2f %.2f", part.Size.X, part.Size.Y, part.Size.Z, want.X, want.Y, want.Z)
	end
	-- Blender (x, y, z) is Roblox (x, z, -y); the glb importer turns each mesh 180 degrees about its centre, so turn it back
	part.CFrame = CFrame.new((b[1] + b[4]) / 2, (b[3] + b[6]) / 2, -(b[2] + b[5]) / 2) * CFrame.Angles(0, math.pi, 0)
	part.PivotOffset = part.CFrame:Inverse() -- the pivot at the run's start, on the ground, square to the world
	part.Anchored = true
	part.Material = Enum.Material.SmoothPlastic
	part.Color = Color3.new(1, 1, 1)
	part.CanCollide = collide
	part.CanTouch = false
	part.CastShadow = true
	if collide then
		part.CollisionFidelity = Enum.CollisionFidelity.Box
	end
	local sa = Instance.new("SurfaceAppearance")
	sa.ColorMap = colourMap
	sa.Color = TINT
	sa.Parent = part
	if info.Chain then
		part:SetAttribute("Chain", #info.Chain == 1 and string.format("straight, %g studs along +X", info.Chain[1]) or string.format("turns left %g degrees on radius %g (turn it 180 to go right)", info.Chain[2], info.Chain[1]))
	end
	part:PivotTo(CFrame.new())
	return part
end

local sets = {
	{ "Edging", "Chisel", id("Cobble_ChiselSlate_Color.png"), false },
	{ "EdgingMoss", "Chisel", id("Cobble_ChiselSlate_Moss.png"), false },
	{ "Border", "Sett", id("Cobble_SettCool_Color.png"), true },
}
local names = {}
for name in DATA.Pieces do
	table.insert(names, name)
end
table.sort(names)
for _, s in sets do
	local f = Instance.new("Folder")
	f.Name = s[1]
	for _, name in names do
		if DATA.Pieces[name].Style == s[2] then
			local p = master(name, s[3], s[4])
			if p then
				p.Name = string.gsub(name, "^Chisel_", ""):gsub("^Sett_", "")
				p.Parent = f
			end
		end
	end
	f.Parent = kit
end
loaded:Destroy()
kit.Parent = SS

-- the shelf: every piece in a row per set, and a worked example of each use
local oldShelf = workspace:FindFirstChild("CobbleShelf")
if oldShelf then
	oldShelf:Destroy()
end
local shelf = Instance.new("Folder")
shelf.Name = "CobbleShelf"
local function label(parent, text, pos)
	local p = Instance.new("Part")
	p.Name = text
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Transparency = true, false, false, false, 1
	p.Size = Vector3.one
	p.Position = pos
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(240, 30)
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
local function put(parent, setName, piece, cf)
	local m = kit[setName]:FindFirstChild(piece)
	if not m then
		return nil
	end
	local c = m:Clone()
	c:PivotTo(cf)
	c.Parent = parent
	return c
end
local z = SHELF.Z
for _, s in sets do
	local row = Instance.new("Folder")
	row.Name = s[1]
	row.Parent = shelf
	local x = SHELF.X - 150
	for _, part in kit[s[1]]:GetChildren() do
		local c = part:Clone()
		c:PivotTo(CFrame.new(x, SHELF.Y, z))
		c.Parent = row
		label(row, part.Name, Vector3.new(x + part.Size.X / 2, SHELF.Y + 4, z))
		x += math.max(part.Size.X, 3) + 6
	end
	label(row, s[1], Vector3.new(SHELF.X - 165, SHELF.Y + 6, z))
	z += 14
end

-- a paved square, 24 x 16: a Part with the paving material, its border laid outside it, a square stone at each corner
local demo = Instance.new("Folder")
demo.Name = "Example"
demo.Parent = shelf
local x0, x1, z0, z1 = SHELF.X - 140, SHELF.X - 116, z + 10, z + 26
local pave = Instance.new("Part")
pave.Name = "PavedArea"
pave.Anchored = true
pave.Size = Vector3.new(x1 - x0, 1, z1 - z0)
pave.Position = Vector3.new((x0 + x1) / 2, SHELF.Y - 0.45, (z0 + z1) / 2)
pave.Material = Enum.Material.Slate
pave.MaterialVariant = "HubPaving"
pave.Color = Color3.fromRGB(255, 255, 255)
pave.Parent = demo
local b = 0.68
local rows = { "Row8A", "Row8B" }
for i = 0, 2 do
	put(demo, "Border", rows[i % 2 + 1], CFrame.new(x0 + 8 * i, 0, z1 + b))
	put(demo, "Border", rows[(i + 1) % 2 + 1], CFrame.new(x1 - 8 * i, 0, z0 - b) * CFrame.Angles(0, math.pi, 0))
end
for i = 0, 1 do
	put(demo, "Border", rows[i % 2 + 1], CFrame.new(x1 + b, 0, z1 - 8 * i) * CFrame.Angles(0, math.pi / 2, 0))
	put(demo, "Border", rows[(i + 1) % 2 + 1], CFrame.new(x0 - b, 0, z0 + 8 * i) * CFrame.Angles(0, -math.pi / 2, 0))
end
for _, c in { { x0 - b, z0 - b }, { x1 + b, z0 - b }, { x1 + b, z1 + b }, { x0 - b, z1 + b } } do
	put(demo, "Border", "Corner", CFrame.new(c[1], 0, c[2]))
end
label(demo, "Paved Part (Slate + HubPaving) with its border", Vector3.new((x0 + x1) / 2, 6, z0 - 3))
-- a round bed: eight Curve6 pieces, each starting where the last ended
local cf = CFrame.new(x1 + 22, 0, z1)
for _ = 1, 8 do
	put(demo, "Edging", "Curve6", cf)
	cf = cf * CFrame.new(6 * math.sin(math.rad(45)), 0, -(6 - 6 * math.cos(math.rad(45)))) * CFrame.Angles(0, math.rad(45), 0)
end
label(demo, "Round bed: 8 x Curve6", Vector3.new(x1 + 22, 6, z1 - 6))
-- a long bed: straights and pairs of corners
cf = CFrame.new(x1 + 40, 0, z1 - 2)
for _, n in { "Straight8A", "Straight8B", "Corner", "Corner", "Straight8B", "Straight8A", "Corner", "Corner" } do
	put(demo, "EdgingMoss", n, cf)
	if n == "Corner" then
		cf = cf * CFrame.new(2.5, 0, -2.5) * CFrame.Angles(0, math.rad(90), 0)
	else
		cf = cf * CFrame.new(8, 0, 0)
	end
end
label(demo, "Long bed: straights + corner pairs (mossy)", Vector3.new(x1 + 48, 6, z1 - 4.5))

local ground = Instance.new("Part")
ground.Name = "ShelfGround"
ground.Anchored = true
ground.Size = Vector3.new(420, 2, z1 - SHELF.Z + 30)
ground.Position = Vector3.new(SHELF.X + 40, SHELF.Y - 1, (SHELF.Z + z1) / 2)
ground.Color = Color3.fromRGB(96, 160, 86)
ground.Material = Enum.Material.SmoothPlastic
ground.Parent = shelf
shelf.Parent = workspace
game:GetService("ChangeHistoryService"):SetWaypoint("Add cobble kit")
report.pieces = #kit:GetDescendants()
return game:GetService("HttpService"):JSONEncode(report)
