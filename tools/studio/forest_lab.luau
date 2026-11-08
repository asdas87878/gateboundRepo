-- Forest test patches on a clean flat ground, to judge forest types (docs/style/forests.md). Workspace.ForestLab at x 20000; nothing in a Land uses it. Edit mode.

local ORIGIN = Vector3.new(20000, 20, 0)
local kit = game.ServerStorage.TreeKit
local old = workspace:FindFirstChild("ForestLab")
if old then
	old:Destroy()
end
local root = Instance.new("Folder")
root.Name = "ForestLab"
root.Parent = workspace
workspace.Terrain:FillBlock(CFrame.new(ORIGIN - Vector3.new(0, 4, 0)), Vector3.new(6000, 8, 2000), Enum.Material.Grass)
local rng = Random.new(21)
local count = 0

local function place(folder, name, x, z, scale)
	local piece = kit[name]:Clone()
	piece:ScaleTo(scale)
	local cf, size = piece:GetBoundingBox()
	local pivot = piece:GetPivot()
	local rise = ORIGIN.Y - 0.5 - (cf.Y - size.Y / 2)
	piece:PivotTo(CFrame.new(ORIGIN.X + x, pivot.Y + rise, ORIGIN.Z + z) * CFrame.Angles(0, rng:NextNumber(0, 6.28), 0))
	piece.Parent = folder
	count += 1
	if count % 30 == 0 then
		workspace:SetAttribute("ForestProgress", count)
		task.wait()
	end
end

local function pick(list)
	return list[rng:NextInteger(1, #list)]
end

local function patch(name, cx, spacing, half, keep, chooser, under)
	local folder = Instance.new("Folder")
	folder.Name = name
	folder.Parent = root
	for gx = -half, half, spacing do
		for gz = -half, half, spacing do
			if rng:NextNumber() < keep then
				local x, z = cx + gx + rng:NextNumber(-0.4, 0.4) * spacing, gz + rng:NextNumber(-0.4, 0.4) * spacing
				local tree, scale = chooser()
				place(folder, tree, x, z, scale)
				under(folder, x, z)
			end
		end
	end
	return folder
end

local function near(folder, name, x, z, reach, scale)
	local a = rng:NextNumber(0, 6.28)
	local d = rng:NextNumber(reach * 0.4, reach)
	place(folder, name, x + math.cos(a) * d, z + math.sin(a) * d, scale)
end

-- Deep wood: tight canopy, a few giants, a dense lower layer with an edge belt
patch("DeepWood", -540, 36, 150, 0.82, function()
	local r = rng:NextNumber()
	if r < 0.28 then
		return pick({ "Elm7", "Elm23" }), rng:NextNumber(0.95, 1.3)
	end
	return pick({ "Oak7", "Oak23" }), rng:NextNumber(0.85, 1.2)
end, function(f, x, z)
	-- a full lower layer: shrubs, plenty of ferns, young trees
	if rng:NextNumber() < 0.85 then
		near(f, "ShrubBig", x, z, 20, rng:NextNumber(0.9, 1.6))
	end
	for _ = 1, 3 do
		near(f, "Fern", x, z, 19, rng:NextNumber(1.1, 1.9))
	end
	if rng:NextNumber() < 0.45 then
		near(f, "Sapling7", x, z, 20, rng:NextNumber(0.9, 1.4))
	end
end)
local function canopy(folder, x, z, y, scale)
	local piece = kit[pick({ "Canopy7", "Canopy23" })]:Clone()
	piece:ScaleTo(scale)
	piece:PivotTo(CFrame.new(ORIGIN.X + x, ORIGIN.Y + y, ORIGIN.Z + z) * CFrame.Angles(0, rng:NextNumber(0, 6.28), 0))
	piece.Parent = folder
	count += 1
end
-- A few giants through the deep wood, with canopy layers closing the ceiling above it
do
	local deep = root.DeepWood
	for _, spot in { { -600, -70 }, { -470, 60 }, { -560, 100 } } do
		place(deep, pick({ "Giant7", "Giant23" }), spot[1], spot[2], rng:NextNumber(0.75, 0.95))
	end
	for gx = -660, -420, 70 do
		for gz = -130, 130, 70 do
			if rng:NextNumber() < 0.7 then
				canopy(deep, gx + rng:NextNumber(-18, 18), gz + rng:NextNumber(-18, 18), rng:NextNumber(66, 92), rng:NextNumber(0.8, 1.1))
			end
		end
	end
end
-- Colossal wood: massive layered trees, many of them, with a mid layer and a floor beneath
do
	local folder = Instance.new("Folder")
	folder.Name = "ColossalWood"
	folder.Parent = root
	local spots = {}
	for gx = -2620, -1500, 215 do
		for gz = -640, 640, 215 do
			if rng:NextNumber() < 0.78 then
				local x, z = gx + rng:NextNumber(-55, 55), gz + rng:NextNumber(-55, 55)
				table.insert(spots, { x, z })
				place(folder, pick({ "Colossal7", "Colossal23", "Colossal41" }), x, z, rng:NextNumber(0.9, 1.3))
			end
		end
	end
	-- a mid layer of ordinary big trees between them, and a floor of shrubs and ferns
	for _ = 1, 110 do
		local x, z = rng:NextNumber(-2680, -1440), rng:NextNumber(-680, 680)
		local clear = true
		for _, s in spots do
			if (s[1] - x) ^ 2 + (s[2] - z) ^ 2 < 60 ^ 2 then
				clear = false
			end
		end
		if clear then
			place(folder, pick({ "Elm7", "Elm23", "Oak7", "Oak23", "Giant7" }), x, z, rng:NextNumber(0.7, 1.15))
		end
	end
	for _, s in spots do
		for _ = 1, 8 do
			near(folder, "Fern", s[1], s[2], 95, rng:NextNumber(1.3, 2.4))
		end
		for _ = 1, 4 do
			near(folder, "ShrubBig", s[1], s[2], 100, rng:NextNumber(1.0, 2.0))
		end
		near(folder, "Sapling7", s[1], s[2], 100, rng:NextNumber(1.0, 1.8))
	end
	-- light. Some crowns cast no shadow, so real sun patches reach the floor; warm bounce light on the trunks keeps bark from going lavender in the shade (the video's coloured lights in shadows);
	-- pools of green-gold light on the floor, with soft shafts along the sun's direction
	local function lightAt(position, colour, brightness, range)
		local anchor = Instance.new("Part")
		anchor.Name = "Light"
		anchor.Anchored = true
		anchor.CanCollide, anchor.CanQuery, anchor.CanTouch = false, false, false
		anchor.Transparency = 1
		anchor.Size = Vector3.one
		anchor.Position = position
		local p = Instance.new("PointLight")
		p.Color, p.Brightness, p.Range, p.Shadows = colour, brightness, range, false
		p.Parent = anchor
		anchor.Parent = folder
		return anchor
	end
	for _, m in folder:GetChildren() do
		if string.find(m.Name, "Colossal") then
			-- most crowns let the sun through: a third cast shadow, enough for dappled shade rather than a dark ceiling
			if rng:NextNumber() < 0.68 then
				m.Crown.CastShadow = false
			end
		end
	end
	local sun = game:GetService("Lighting"):GetSunDirection()
	for _ = 1, 26 do
		local x, z = rng:NextNumber(-2650, -1460), rng:NextNumber(-660, 660)
		local spot = Vector3.new(ORIGIN.X + x, ORIGIN.Y + 1, ORIGIN.Z + z)
		local anchor = lightAt(spot + Vector3.new(0, 20, 0), Color3.fromRGB(222, 255, 150), 1.0, 45)
		local a0, a1 = Instance.new("Attachment"), Instance.new("Attachment")
		a0.WorldPosition = spot
		a1.WorldPosition = spot + sun * 300
		a0.Parent, a1.Parent = anchor, anchor
		a0.WorldPosition, a1.WorldPosition = spot, spot + sun * 300
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
	end
end
-- Giant grove: the huge trees alone, layered, with a high canopy and a forest floor
do
	local folder = Instance.new("Folder")
	folder.Name = "GiantGrove"
	folder.Parent = root
	for _, spot in { { -1040, -80 }, { -900, -110 }, { -1080, 70 }, { -930, 50 }, { -1010, 170 } } do
		place(folder, pick({ "Giant7", "Giant23" }), spot[1], spot[2], rng:NextNumber(0.95, 1.2))
		for _ = 1, 7 do
			near(folder, "Fern", spot[1], spot[2], 42, rng:NextNumber(1.2, 2.2))
		end
		for _ = 1, 3 do
			near(folder, "ShrubBig", spot[1], spot[2], 46, rng:NextNumber(1.0, 1.8))
		end
		near(folder, "Sapling7", spot[1], spot[2], 50, rng:NextNumber(1.0, 1.6))
	end
	for gx = -1130, -870, 80 do
		for gz = -170, 200, 80 do
			if rng:NextNumber() < 0.65 then
				canopy(folder, gx + rng:NextNumber(-22, 22), gz + rng:NextNumber(-22, 22), rng:NextNumber(112, 145), rng:NextNumber(1.1, 1.5))
			end
		end
	end
end
-- Birch glade: open, loose clusters, pale trunks, sky between crowns
patch("BirchGlade", -180, 40, 150, 0.6, function()
	return pick({ "Birch7", "Birch23" }), rng:NextNumber(0.8, 1.25)
end, function(f, x, z)
	if rng:NextNumber() < 0.6 then
		near(f, "ShrubLow", x, z, 16, rng:NextNumber(0.8, 1.3))
	end
	if rng:NextNumber() < 0.25 then
		near(f, "Sapling7", x, z, 16, rng:NextNumber(0.7, 1.0))
	end
end)
-- Pine stand: tall trunks in rhythm, open floor
patch("PineStand", 180, 38, 150, 0.8, function()
	return pick({ "Pine7", "Pine23" }), rng:NextNumber(0.8, 1.2)
end, function(f, x, z)
	if rng:NextNumber() < 0.4 then
		near(f, "Fern", x, z, 14, rng:NextNumber(1.0, 1.6))
	end
end)
-- Orchard: planted rows, a few missing or off-line
do
	local folder = Instance.new("Folder")
	folder.Name = "Orchard"
	folder.Parent = root
	for gx = -140, 140, 40 do
		for gz = -140, 140, 40 do
			if rng:NextNumber() < 0.9 then
				place(folder, pick({ "Apple7", "Apple23" }), 540 + gx + rng:NextNumber(-2.5, 2.5), gz + rng:NextNumber(-2.5, 2.5), rng:NextNumber(0.9, 1.15))
			end
		end
	end
end
workspace:SetAttribute("ForestProgress", nil)
return count
