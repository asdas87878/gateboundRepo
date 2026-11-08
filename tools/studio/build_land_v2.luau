-- Grey-box of Verdant Vale v2 (art/lands/land1_v2, built by tools/art/land_v2.py), in edit mode. Reads terrain tiles and the object list from uploaded images.
-- Map (x, y) sits at world (x + Offset.X, height, y + Offset.Z), clear of the river scene and the first grey-box. Rebuilds Workspace.ValeV2 and this terrain only; never Terrain:Clear.
-- Yields between chunks. Stage "All" does both; to run a piece at a time use "Terrain" (set Only to a tile's index if a call times out) or "Objects".
-- Image ids, labels and counts come from a run of tools/art/land_v2.py: rerunning it means uploading the images again and updating them here.

local CONFIG = {
	Stage = "All", -- or "Terrain" / "Objects"
	Only = nil, -- a tile's index, to run one tile a call
	Offset = Vector3.new(4000, 0, -3000),
	Border = 400,
	Step = 4,
	Chunk = 64,
	Tiles = {
		-- { image id, first column, first row }, filled in after upload
		{ "rbxassetid://127401839460930", 0, 0 },
		{ "rbxassetid://112293754609631", 1024, 0 },
		{ "rbxassetid://107748577855347", 0, 1024 },
		{ "rbxassetid://128527233711592", 1024, 1024 },
	},
	Objects = "rbxassetid://104850393057217",
	ObjectCount = 10532,
	Kinds = {
		"Stone",
		"Roof",
		"Wood",
		"Enemy",
		"Boss",
		"Ink",
		"Rock",
		"TreeMeadow",
		"TreeHill",
		"TreeDark",
		"TreeDry",
		"Glow",
		"FightCircle",
		"Bridge",
		"Waystone",
		"Crop",
		"Giant",
	},
	Labels = {
		{ T = "Wayfarer's Crag  Lv 1", X = 750, Y = 4700, Up = 90, Big = true },
		{ T = "Sunny Meadows  Lv 1-3", X = 3050, Y = 4400, Up = 90, Big = true },
		{ T = "Mossrock Hills  Lv 3-5", X = 1050, Y = 2750, Up = 90, Big = true },
		{ T = "Whisperwood  Lv 5-7", X = 2700, Y = 1000, Up = 90, Big = true },
		{ T = "Bandit Ridge  Lv 7-9", X = 5000, Y = 3000, Up = 90, Big = true },
		{ T = "Gatehill  Lv 9-10", X = 5050, Y = 800, Up = 90, Big = true },
		{ T = "Gate-stone circle (wake)", X = 750, Y = 4700, Up = 44 },
		{ T = "Cliff lookout", X = 1020, Y = 4430, Up = 44 },
		{ T = "Millford", X = 1900, Y = 4620, Up = 44 },
		{ T = "Crossroads Inn", X = 3010, Y = 3960, Up = 44 },
		{ T = "Windmill Hill", X = 2450, Y = 4780, Up = 44 },
		{ T = "Shepherd's Tor", X = 2200, Y = 3880, Up = 44 },
		{ T = "The Ploughlands", X = 3700, Y = 4280, Up = 44 },
		{ T = "Lake Landing", X = 3560, Y = 3240, Up = 44 },
		{ T = "Barrow Field", X = 4200, Y = 4720, Up = 44 },
		{ T = "Boss: Old Tusk", X = 3350, Y = 4830, Up = 44 },
		{ T = "Mossgate towers", X = 1560, Y = 2240, Up = 44 },
		{ T = "Colossus chest ruins", X = 1040, Y = 3090, Up = 44 },
		{ T = "Colossus's crown", X = 640, Y = 2470, Up = 44 },
		{ T = "Boss: Rockback", X = 760, Y = 3480, Up = 44 },
		{ T = "Old Quarry", X = 1400, Y = 1870, Up = 44 },
		{ T = "Golem Foundry", X = 640, Y = 1950, Up = 44 },
		{ T = "Row of Hands", X = 1450, Y = 3660, Up = 44 },
		{ T = "Lost scout's camp", X = 2180, Y = 1320, Up = 44 },
		{ T = "The Elder / Rootdeep Hollow", X = 1900, Y = 520, Up = 44 },
		{ T = "Wisp Mere", X = 1420, Y = 930, Up = 44 },
		{ T = "Mushroom ring", X = 2960, Y = 560, Up = 44 },
		{ T = "Boss: Hollowhorn", X = 3500, Y = 620, Up = 44 },
		{ T = "Woodcutters' wreck", X = 4000, Y = 800, Up = 44 },
		{ T = "Twin Fang shrine", X = 2980, Y = 1885, Up = 44 },
		{ T = "Canyon gate", X = 4400, Y = 2885, Up = 44 },
		{ T = "Rope bridge", X = 5050, Y = 2950, Up = 44 },
		{ T = "Redfang's Hold", X = 5040, Y = 2170, Up = 44 },
		{ T = "Crest watchtowers", X = 5040, Y = 2650, Up = 44 },
		{ T = "East mesa hold", X = 5620, Y = 2290, Up = 44 },
		{ T = "South mesa", X = 4400, Y = 3560, Up = 44 },
		{ T = "Dry mine", X = 5660, Y = 3700, Up = 44 },
		{ T = "Boss: Captain Redfang", X = 5120, Y = 4120, Up = 44 },
		{ T = "Stair camp", X = 4830, Y = 1420, Up = 44 },
		{ T = "Fallen arch", X = 4420, Y = 900, Up = 44 },
		{ T = "Bell tower", X = 5660, Y = 760, Up = 44 },
		{ T = "THE GATE: Mossback Warden", X = 5050, Y = 700, Up = 44 },
		{ T = "Brightwater", X = 3130, Y = 2750, Up = 44 },
		{ T = "East gate (locked until story step 6)", X = 3700, Y = 2720, Up = 44 },
		{ T = "Ferry post", X = 2300, Y = 2860, Up = 44 },
		{ T = "Hillstair ruin", X = 1060, Y = 1560, Up = 44 },
		{ T = "Reed huts", X = 3240, Y = 2250, Up = 44 },
		{ T = "Hunter's stand", X = 3200, Y = 1500, Up = 44 },
		{ T = "Pilgrim shelter", X = 4640, Y = 350, Up = 44 },
		{ T = "Pilgrim ruin", X = 5530, Y = 1090, Up = 44 },
	},
}
local C = CONFIG
local AssetService = game:GetService("AssetService")

local function load(id)
	local image = AssetService:CreateEditableImageAsync(Content.fromUri(id))
	return image.Size.X, image.Size.Y, image:ReadPixelsBuffer(Vector2.zero, image.Size)
end

local function buildTerrain()
	local terrain = workspace.Terrain
	terrain:SetMaterialColor(Enum.Material.LeafyGrass, Color3.fromRGB(44, 92, 66))
	terrain:SetMaterialColor(Enum.Material.Sandstone, Color3.fromRGB(176, 150, 98))
	terrain:SetMaterialColor(Enum.Material.Limestone, Color3.fromRGB(190, 186, 166))
	terrain:SetMaterialColor(Enum.Material.Cobblestone, Color3.fromRGB(150, 148, 142))
	local MATS = {
		[0] = Enum.Material.Grass,
		[1] = Enum.Material.LeafyGrass,
		[2] = Enum.Material.Sandstone,
		[3] = Enum.Material.Limestone,
		[4] = Enum.Material.Rock,
		[5] = Enum.Material.Sand,
		[6] = Enum.Material.Mud,
		[7] = Enum.Material.Sand, -- the water's bed
		[8] = Enum.Material.Cobblestone,
	}
	local BED = 6
	local air, water = Enum.Material.Air, Enum.Material.Water
	local written = 0
	for index, tile in C.Tiles do
		if C.Only == nil or C.Only == index then
			local w, h, px = load(tile[1])
			for cj = 0, h - 1, C.Chunk do
				for ci = 0, w - 1, C.Chunk do
					local nx, nz = math.min(C.Chunk, w - ci), math.min(C.Chunk, h - cj)
					-- each column's height and material, and the chunk's range: mountains stay hollow below their shell
					local hs, ms = table.create(nx * nz), table.create(nx * nz)
					local lo, hi = math.huge, -math.huge
					for j = 0, nz - 1 do
						for i = 0, nx - 1 do
							local o = ((cj + j) * w + ci + i) * 4
							local height = (buffer.readu8(px, o) * 256 + buffer.readu8(px, o + 1)) / 50 - 40
							local m = buffer.readu8(px, o + 2)
							local n = j * nx + i + 1
							hs[n], ms[n] = height, m
							lo = math.min(lo, height)
							hi = math.max(hi, m == 7 and height + BED or height)
						end
					end
					local bottom = C.Step * (math.floor(lo / C.Step) - 5)
					local ny = (C.Step * (math.ceil(hi / C.Step) + 1) - bottom) // C.Step
					local mats, occ = table.create(nx), table.create(nx)
					for i = 1, nx do
						local mi, oi = table.create(ny), table.create(ny)
						for k = 1, ny do
							local b = bottom + (k - 1) * C.Step
							local mk, ok = table.create(nz), table.create(nz)
							for j = 1, nz do
								local n = (j - 1) * nx + i
								local height, m = hs[n], ms[n]
								local fill = math.clamp((height - b) / C.Step, 0, 1)
								if fill > 0 then
									mk[j], ok[j] = MATS[m] or MATS[0], fill
								elseif m == 7 and b < height + BED - 1 then
									mk[j], ok[j] = water, 1
								else
									mk[j], ok[j] = air, 0
								end
							end
							mi[k], oi[k] = mk, ok
						end
						mats[i], occ[i] = mi, oi
					end
					local low = Vector3.new(
						C.Offset.X + (tile[2] + ci) * C.Step - C.Border,
						bottom,
						C.Offset.Z + (tile[3] + cj) * C.Step - C.Border
					)
					terrain:WriteVoxels(Region3.new(low, low + Vector3.new(nx, ny, nz) * C.Step), C.Step, mats, occ)
					written += nx * ny * nz
					task.wait()
				end
			end
		end
	end
	return string.format("terrain written, %.1f million voxels", written / 1e6)
end

local LOOK = {
	Stone = { Color3.fromRGB(190, 188, 180) },
	Roof = { Color3.fromRGB(120, 124, 136) },
	Wood = { Color3.fromRGB(130, 112, 92) },
	Enemy = { Color3.fromRGB(190, 60, 55) },
	Boss = { Color3.fromRGB(120, 30, 30) },
	Ink = { Color3.fromRGB(35, 32, 42) },
	Rock = { Color3.fromRGB(118, 116, 112) },
	TreeMeadow = { Color3.fromRGB(96, 140, 84) },
	TreeHill = { Color3.fromRGB(88, 124, 92) },
	TreeDark = { Color3.fromRGB(46, 78, 62) },
	TreeDry = { Color3.fromRGB(120, 118, 84) },
	Glow = { Color3.fromRGB(160, 235, 255), Neon = true, Ghost = true },
	FightCircle = { Color3.fromRGB(190, 60, 55), Ghost = true, Clear = 0.75 },
	Bridge = { Color3.fromRGB(130, 112, 92) },
	Waystone = { Color3.fromRGB(95, 180, 200) },
	Crop = { Color3.fromRGB(190, 170, 90), Ghost = true },
	Giant = { Color3.fromRGB(70, 58, 48) },
}

local function buildObjects()
	local w, _, px = load(C.Objects)
	local old = workspace:FindFirstChild("ValeV2")
	if old then
		old:Destroy()
	end
	local root = Instance.new("Folder")
	root.Name = "ValeV2"
	root.Parent = workspace
	-- landmarks always loaded, so they can be seen across the map
	local landmarks = Instance.new("Model")
	landmarks.Name = "Landmarks"
	landmarks.ModelStreamingMode = Enum.ModelStreamingMode.Persistent
	landmarks.Parent = root
	local function read16(o)
		return (buffer.readu8(px, o) * 256 + buffer.readu8(px, o + 1)) / 2 - 1024
	end
	local function size(o)
		return (buffer.readu8(px, o) / 16) ^ 2
	end
	local chunk = Instance.new("Folder")
	chunk.Name = "Blocks"
	for i = 0, C.ObjectCount - 1 do
		local o = i * 16
		local kind = C.Kinds[buffer.readu8(px, o + 2) + 1]
		local look = LOOK[kind]
		local persist = buffer.readu8(px, o + 10) == 1
		local p = Instance.new("Part")
		p.Name = kind
		p.Anchored = true
		p.Size = Vector3.new(size(o + 12), size(o + 13), size(o + 14))
		if kind == "Glow" and p.Size.Y > 250 then
			p.Size = Vector3.new(p.Size.X, 2000, p.Size.Z) -- the Gate's beam: taller than the image's 254-stud size limit
		elseif kind == "Bridge" and p.Size.Z > 250 then
			p.Size = Vector3.new(p.Size.X, p.Size.Y, 700) -- the rope bridge: longer than that limit
		end
		p.Color = look[1]
		p.Material = look.Neon and Enum.Material.Neon or Enum.Material.SmoothPlastic
		p.TopSurface, p.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
		if look.Ghost then
			p.CanCollide, p.CanQuery, p.CanTouch = false, false, false
		end
		p.Transparency = look.Clear or 0
		p.CFrame = CFrame.new(read16(o) + C.Offset.X, read16(o + 8), read16(o + 4) + C.Offset.Z)
			* CFrame.Angles(0, buffer.readu8(px, o + 6) / 255 * math.pi, 0)
		p.Parent = persist and landmarks or chunk
		if i % 400 == 399 then
			chunk.Parent = root
			chunk = Instance.new("Folder")
			chunk.Name = "Blocks"
			task.wait()
		end
	end
	chunk.Parent = root

	local labels = Instance.new("Folder")
	labels.Name = "Labels"
	labels.Parent = root
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { workspace.Terrain }
	local function groundAt(x, y)
		local hit =
			workspace:Raycast(Vector3.new(x + C.Offset.X, 1200, y + C.Offset.Z), Vector3.new(0, -1400, 0), params)
		return hit and hit.Position.Y or 0
	end
	for _, l in C.Labels do
		local a = Instance.new("Part")
		a.Name = "Label"
		a.Anchored = true
		a.CanCollide, a.CanQuery, a.CanTouch = false, false, false
		a.Transparency = 1
		a.Size = Vector3.one
		a.Position = Vector3.new(l.X + C.Offset.X, groundAt(l.X, l.Y) + l.Up, l.Y + C.Offset.Z)
		local g = Instance.new("BillboardGui")
		g.Size = UDim2.fromOffset(420, 34)
		g.AlwaysOnTop = true
		g.MaxDistance = l.Big and 3000 or 700
		g.Parent = a
		local t = Instance.new("TextLabel")
		t.Size = UDim2.fromScale(1, 1)
		t.BackgroundTransparency = 1
		t.Text = l.T
		t.TextColor3 = l.Big and Color3.new(1, 1, 1) or Color3.fromRGB(255, 235, 170)
		t.TextStrokeTransparency = 0.2
		t.Font = Enum.Font.GothamBold
		t.TextSize = l.Big and 26 or 20
		t.Parent = g
		a.Parent = labels
	end

	-- spawn at the Wake circle; the older spawns are switched off, not removed
	local spawn = Instance.new("SpawnLocation")
	spawn.Name = "ValeV2Spawn"
	spawn.Anchored = true
	spawn.Size = Vector3.new(8, 1, 8)
	spawn.Position = Vector3.new(750 + C.Offset.X, groundAt(750, 4700) + 0.3, 4700 + C.Offset.Z)
	spawn.Neutral = true
	spawn.Duration = 0
	spawn.Parent = root
	for _, d in workspace:GetDescendants() do
		if d:IsA("SpawnLocation") and d ~= spawn then
			d.Enabled = false
		end
	end
	return string.format("objects %d, landmarks %d, width %d", C.ObjectCount, #landmarks:GetChildren(), w)
end

local report = {}
if C.Stage ~= "Objects" then
	table.insert(report, buildTerrain())
end
if C.Stage ~= "Terrain" then
	table.insert(report, buildObjects())
end
print("[ValeV2] " .. table.concat(report, ", "))
return table.concat(report, ", ")
