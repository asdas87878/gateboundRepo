-- Blockout of Verdant Vale v3, the star structure (art/lands/land1_v3, built by tools/art/land_v2.py), in edit mode. Terrain tiles and objects come from uploaded images.
-- Map (x, y) sits at world (x + Offset.X, height, y + Offset.Z). Rebuilds Workspace.ValeV3 and this terrain, replaces Workspace.ValeV2 (same ground); never Terrain:Clear.
-- Adds the home plot, spawn there, and a BlockoutTravel script: Gate Court prompts, "Go home" on every waystone, MaxSlopeAngle 52 so cliffs are real, and a test mount.
-- The DATA block is filled by a run of land_v2.py + upload: rerunning it means uploading again and updating the block.

local CONFIG = {
	Stage = "All", -- or "Terrain" / "Objects"
	Only = nil, -- a tile's index, to run one tile a call
	Offset = Vector3.new(4000, 0, -3000),
	Border = 400,
	Step = 4,
	Chunk = 64,
	-- BEGIN DATA
	Tiles = {
		{ "rbxassetid://133609381298480", 0, 0 },
		{ "rbxassetid://120983844191767", 1024, 0 },
		{ "rbxassetid://88227627024867", 0, 1024 },
		{ "rbxassetid://103227901203658", 1024, 1024 },
	},
	Objects = "rbxassetid://74119916846026",
	ObjectCount = 9736,
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
		"Material",
		"Rescue",
		"Secret",
		"Dungeon",
		"Lock",
		"Plot",
		"ArchOpen",
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
		{ T = "Mossgate towers", X = 1560, Y = 2240, Up = 44 },
		{ T = "Colossus chest ruins", X = 1040, Y = 3090, Up = 44 },
		{ T = "Colossus's crown", X = 640, Y = 2470, Up = 44 },
		{ T = "Old Quarry", X = 1400, Y = 1870, Up = 44 },
		{ T = "Golem Foundry", X = 640, Y = 1950, Up = 44 },
		{ T = "Row of Hands", X = 1450, Y = 3660, Up = 44 },
		{ T = "Lost scout's camp", X = 2180, Y = 1320, Up = 44 },
		{ T = "The Elder / Rootdeep Hollow", X = 1900, Y = 520, Up = 44 },
		{ T = "Wisp Mere", X = 1420, Y = 930, Up = 44 },
		{ T = "Mushroom ring", X = 2960, Y = 560, Up = 44 },
		{ T = "Woodcutters' wreck", X = 4000, Y = 800, Up = 44 },
		{ T = "Twin Fang shrine", X = 2980, Y = 1885, Up = 44 },
		{ T = "Canyon gate", X = 4400, Y = 2885, Up = 44 },
		{ T = "Rope bridge", X = 5050, Y = 2950, Up = 44 },
		{ T = "Redfang's Hold", X = 5040, Y = 2170, Up = 44 },
		{ T = "Crest watchtowers", X = 5040, Y = 2650, Up = 44 },
		{ T = "East mesa hold", X = 5620, Y = 2290, Up = 44 },
		{ T = "South mesa", X = 4400, Y = 3560, Up = 44 },
		{ T = "Dry mine", X = 5660, Y = 3700, Up = 44 },
		{ T = "Stair camp", X = 4780, Y = 1570, Up = 44 },
		{ T = "Fallen arch", X = 4420, Y = 900, Up = 44 },
		{ T = "Bell tower", X = 5660, Y = 760, Up = 44 },
		{ T = "THE GATE: Mossback Warden", X = 5050, Y = 700, Up = 44 },
		{ T = "Brightwater", X = 3130, Y = 2750, Up = 44 },
		{ T = "Ferry post", X = 2300, Y = 2860, Up = 44 },
		{ T = "Hillstair ruin", X = 1060, Y = 1560, Up = 44 },
		{ T = "Reed huts", X = 3240, Y = 2250, Up = 44 },
		{ T = "Hunter's stand", X = 3200, Y = 1500, Up = 44 },
		{ T = "Pilgrim shelter", X = 4640, Y = 350, Up = 44 },
		{ T = "Pilgrim ruin", X = 5530, Y = 1090, Up = 44 },
		{ T = "Farm: Slime Hollow", X = 560, Y = 4830, Up = 30, Kind = "Spot" },
		{ T = "Farm: Hare Bluff", X = 960, Y = 4880, Up = 30, Kind = "Spot" },
		{ T = "Material: Wakestone", X = 470, Y = 4640, Up = 30, Kind = "Material" },
		{ T = "Rescue: Blacksmith (opens the Forge)", X = 1000, Y = 4620, Up = 30, Kind = "Rescue" },
		{ T = "Boss: Mother Slime", X = 620, Y = 4540, Up = 30, Kind = "FieldBoss" },
		{ T = "Secret: Under-cliff cache (needs Climb)", X = 1160, Y = 4250, Up = 30, Kind = "Secret" },
		{ T = "Farm: Hare Warren", X = 2050, Y = 4230, Up = 30, Kind = "Spot" },
		{ T = "Farm: Boar Run", X = 2750, Y = 4600, Up = 30, Kind = "Spot" },
		{ T = "Farm: Scarecrow Field", X = 3700, Y = 4480, Up = 30, Kind = "Spot" },
		{ T = "Farm: Hillfolk Camp", X = 2520, Y = 3800, Up = 30, Kind = "Spot" },
		{ T = "Farm: Barrow Wights", X = 4220, Y = 4560, Up = 30, Kind = "Spot" },
		{ T = "Material: Sunwheat", X = 3480, Y = 4130, Up = 30, Kind = "Material" },
		{ T = "Rescue: Merchant (opens the Market)", X = 3170, Y = 4100, Up = 30, Kind = "Rescue" },
		{ T = "Rescue: Stablehand (opens the Stable: mounts)", X = 2620, Y = 4900, Up = 30, Kind = "Rescue" },
		{ T = "Boss: Old Tusk", X = 3350, Y = 4830, Up = 30, Kind = "FieldBoss" },
		{ T = "Secret: Tor-top cache (needs Climb)", X = 2200, Y = 3880, Up = 30, Kind = "Secret" },
		{ T = "Farm: Colossus Ribs", X = 1330, Y = 3060, Up = 30, Kind = "Spot" },
		{ T = "Farm: Thornwolf Run", X = 1700, Y = 3280, Up = 30, Kind = "Spot" },
		{ T = "Farm: Moss Golem Yard", X = 1000, Y = 2120, Up = 30, Kind = "Spot" },
		{ T = "Farm: Foundry Guards", X = 760, Y = 1800, Up = 30, Kind = "Spot" },
		{ T = "Farm: Quarry Crawlers", X = 1330, Y = 2030, Up = 30, Kind = "Spot" },
		{ T = "Material: Mossstone", X = 1470, Y = 1790, Up = 30, Kind = "Material" },
		{ T = "Rescue: Mason (opens Mossgate)", X = 1180, Y = 3660, Up = 30, Kind = "Rescue" },
		{ T = "Boss: Rockback", X = 760, Y = 3480, Up = 30, Kind = "FieldBoss" },
		{ T = "Secret: The Colossus's crown (needs Climb)", X = 640, Y = 2470, Up = 30, Kind = "Secret" },
		{ T = "LOCKED: Mossgate (rescue the Mason)", X = 1560, Y = 2240, Up = 30, Kind = "Lock" },
		{ T = "Farm: Wisp Mere", X = 1560, Y = 1060, Up = 30, Kind = "Spot" },
		{ T = "Farm: Thornwolf Den", X = 2280, Y = 1490, Up = 30, Kind = "Spot" },
		{ T = "Farm: Root Crawlers", X = 2340, Y = 650, Up = 30, Kind = "Spot" },
		{ T = "Farm: Fungus Ring", X = 3060, Y = 740, Up = 30, Kind = "Spot" },
		{ T = "Farm: Stag Glade", X = 3620, Y = 880, Up = 30, Kind = "Spot" },
		{ T = "Material: Elderbark", X = 2060, Y = 940, Up = 30, Kind = "Material" },
		{ T = "Rescue: Carpenter (opens the Workshop and Falls Stair)", X = 2180, Y = 1240, Up = 30, Kind = "Rescue" },
		{ T = "Rescue: Beast-keeper (opens the Pet Keeper)", X = 4020, Y = 700, Up = 30, Kind = "Rescue" },
		{ T = "Boss: Hollowhorn", X = 3500, Y = 620, Up = 30, Kind = "FieldBoss" },
		{ T = "Dungeon: Rootdeep Hollow", X = 1900, Y = 590, Up = 30, Kind = "Dungeon" },
		{ T = "Secret: Falls ledge (needs Glide)", X = 3150, Y = 1760, Up = 30, Kind = "Secret" },
		{ T = "LOCKED: Falls Stair (rescue the Carpenter)", X = 3320, Y = 1890, Up = 30, Kind = "Lock" },
		{ T = "Farm: Crest Riders", X = 4720, Y = 2500, Up = 30, Kind = "Spot" },
		{ T = "Farm: Hold Yard", X = 5040, Y = 2400, Up = 30, Kind = "Spot" },
		{ T = "Farm: Outlaw Flats", X = 4620, Y = 3230, Up = 30, Kind = "Spot" },
		{ T = "Farm: Cut Ambush", X = 5620, Y = 3200, Up = 30, Kind = "Spot" },
		{ T = "Farm: Mine Guards", X = 5430, Y = 3560, Up = 30, Kind = "Spot" },
		{ T = "Material: Bandit Iron", X = 5390, Y = 3820, Up = 30, Kind = "Material" },
		{ T = "Rescue: Engineer (opens Canyon Gate and East Gate)", X = 5600, Y = 2830, Up = 30, Kind = "Rescue" },
		{ T = "Boss: Captain Redfang (Stair Gate opens)", X = 5120, Y = 2095, Up = 30, Kind = "FieldBoss" },
		{ T = "Secret: South mesa cache (needs Climb)", X = 4400, Y = 3560, Up = 30, Kind = "Secret" },
		{ T = "LOCKED: Canyon Gate (rescue the Engineer)", X = 4400, Y = 2885, Up = 30, Kind = "Lock" },
		{ T = "LOCKED: East Gate (rescue the Engineer)", X = 5297, Y = 4283, Up = 30, Kind = "Lock" },
		{ T = "Farm: Stair Sentries", X = 4520, Y = 900, Up = 30, Kind = "Spot" },
		{ T = "Farm: Pilgrim Wraiths", X = 4900, Y = 380, Up = 30, Kind = "Spot" },
		{ T = "Farm: Bell Guard", X = 5480, Y = 700, Up = 30, Kind = "Spot" },
		{ T = "Material: Warden Ore", X = 5230, Y = 1120, Up = 30, Kind = "Material" },
		{ T = "Rescue: Waymaker (repairs the next arch)", X = 4700, Y = 330, Up = 30, Kind = "Rescue" },
		{ T = "Boss: Mossback Warden, the Guardian (Land 2 stone)", X = 5050, Y = 790, Up = 30, Kind = "FieldBoss" },
		{ T = "Secret: Bell top (needs Climb)", X = 5660, Y = 760, Up = 30, Kind = "Secret" },
		{ T = "LOCKED: Stair Gate (beat Captain Redfang)", X = 4905, Y = 1470, Up = 30, Kind = "Lock" },
		{ T = "Plot: Forge (Blacksmith)", X = 7210, Y = 2740, Up = 22, Kind = "Plot" },
		{ T = "Plot: Market (Merchant)", X = 7290, Y = 2830, Up = 22, Kind = "Plot" },
		{ T = "Plot: Stable (Stablehand)", X = 7400, Y = 2875, Up = 22, Kind = "Plot" },
		{ T = "Plot: Tavern", X = 7510, Y = 2830, Up = 22, Kind = "Plot" },
		{ T = "Plot: Walls (Mason)", X = 7590, Y = 2740, Up = 22, Kind = "Plot" },
		{ T = "Plot: Workshop (Carpenter)", X = 7185, Y = 2640, Up = 22, Kind = "Plot" },
		{ T = "Plot: Pet Keeper (Beast-keeper)", X = 7615, Y = 2640, Up = 22, Kind = "Plot" },
		{ T = "Plot: Trophy Hall", X = 7330, Y = 2730, Up = 22, Kind = "Plot" },
		{ T = "Plot: Armoury", X = 7470, Y = 2730, Up = 22, Kind = "Plot" },
		{ T = "Verdant Vale (open)", X = 7400.0, Y = 2576.0, Up = 44, Kind = "Plot" },
		{ T = "Land 2: locked", X = 7344.0, Y = 2520.0, Up = 44, Kind = "Plot" },
		{ T = "Land 3: locked", X = 7400.0, Y = 2464.0, Up = 44, Kind = "Plot" },
		{ T = "Land 4: locked", X = 7456.0, Y = 2520.0, Up = 44, Kind = "Plot" },
	},
	Arrival = { 750, 4654 },
	Home = {
		X = 7400,
		Y = 2700,
		Radius = 300,
		Level = 40,
		SpawnX = 7400,
		SpawnY = 2640,
		ArchX = 7400,
		ArchY = 2576,
		StableX = 7400,
		StableY = 2875,
	},
	-- END DATA
}
local C = CONFIG
local AssetService = game:GetService("AssetService")
local TRAVEL_SOURCE = [==[
-- Grey-box only: lets you walk the star. Home <-> Land by Gate Court and waystones. Replace with real services later.
local Players = game:GetService("Players")
local root = script.Parent
local spawnPart = root:WaitForChild("ValeV3Spawn")
local arrival = root:WaitForChild("LandArrival")
local last = {}

local function send(player, position)
	local character = player.Character
	if not character then
		return
	end
	pcall(function()
		player:RequestStreamAroundAsync(position, 15)
	end)
	character:PivotTo(CFrame.new(position + Vector3.new(0, 5, 0)))
end

local function connect(prompt)
	prompt.Triggered:Connect(function(player)
		local go = prompt:GetAttribute("Go")
		if go == "Home" then
			last[player] = prompt.Parent.Position + Vector3.new(6, 0, 6)
			send(player, spawnPart.Position)
		elseif go == "Land" then
			send(player, arrival.Position)
		elseif go == "Last" then
			send(player, last[player] or arrival.Position)
		elseif go == "Mount" then
			local humanoid = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
			if humanoid then
				humanoid.WalkSpeed = humanoid.WalkSpeed > 20 and 16 or 60
			end
		end
	end)
end

for _, d in root:GetDescendants() do
	if d:IsA("ProximityPrompt") then
		connect(d)
	end
end

local function onCharacter(character)
	local humanoid = character:WaitForChild("Humanoid")
	humanoid.MaxSlopeAngle = 52 -- matches the map's reachability check, so cliffs are real
end
local function onPlayer(player)
	player.CharacterAdded:Connect(onCharacter)
	if player.Character then
		onCharacter(player.Character)
	end
end
Players.PlayerAdded:Connect(onPlayer)
for _, player in Players:GetPlayers() do
	onPlayer(player)
end
Players.PlayerRemoving:Connect(function(player)
	last[player] = nil
end)
]==]

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
	Material = { Color3.fromRGB(235, 165, 40) },
	Rescue = { Color3.fromRGB(230, 80, 200) },
	Secret = { Color3.fromRGB(250, 225, 90) },
	Dungeon = { Color3.fromRGB(110, 70, 170) },
	Lock = { Color3.fromRGB(235, 50, 50), Ghost = true, Clear = 0.45 }, -- a marker for now: you can walk through it while testing
	Plot = { Color3.fromRGB(170, 160, 130) },
	ArchOpen = { Color3.fromRGB(120, 235, 255), Neon = true, Ghost = true },
}

local function buildObjects()
	local w, _, px = load(C.Objects)
	for _, name in { "ValeV2", "ValeV3" } do
		local old = workspace:FindFirstChild(name)
		if old then
			old:Destroy()
		end
	end
	local root = Instance.new("Folder")
	root.Name = "ValeV3"
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
		if kind == "Waystone" then
			local prompt = Instance.new("ProximityPrompt")
			prompt.ActionText = "Go home"
			prompt.ObjectText = "Waystone"
			prompt.MaxActivationDistance = 14
			prompt:SetAttribute("Go", "Home")
			prompt.Parent = p
		end
		p.Parent = persist and landmarks or chunk
		if i % 400 == 399 then
			chunk.Parent = root
			chunk = Instance.new("Folder")
			chunk.Name = "Blocks"
			task.wait()
		end
	end
	chunk.Parent = root

	-- the home plot's ground: a flat bowl, shut in by rocks. Fill calls, so it needs no tile.
	local H = C.Home
	local hc = Vector3.new(H.X + C.Offset.X, H.Level, H.Y + C.Offset.Z)
	local terrain = workspace.Terrain
	terrain:FillCylinder(CFrame.new(hc - Vector3.new(0, 20, 0)), 40, H.Radius + 60, Enum.Material.Grass)
	for i = 1, 36 do
		local a = i / 36 * math.pi * 2
		terrain:FillBall(
			hc + Vector3.new(math.cos(a), 0, math.sin(a)) * (H.Radius + 34 + (i % 3) * 8),
			58 + (i * 7 % 22),
			Enum.Material.Rock
		)
	end
	task.wait()

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
	local LABEL_COLOUR = {
		Spot = Color3.fromRGB(255, 120, 110),
		Material = Color3.fromRGB(255, 190, 90),
		Rescue = Color3.fromRGB(255, 130, 230),
		FieldBoss = Color3.fromRGB(255, 90, 90),
		Secret = Color3.fromRGB(255, 240, 130),
		Dungeon = Color3.fromRGB(200, 165, 255),
		Lock = Color3.fromRGB(255, 70, 70),
		Plot = Color3.fromRGB(210, 240, 255),
	}
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
		t.TextColor3 = l.Big and Color3.new(1, 1, 1) or LABEL_COLOUR[l.Kind] or Color3.fromRGB(255, 235, 170)
		t.TextStrokeTransparency = 0.2
		t.Font = Enum.Font.GothamBold
		t.TextSize = l.Big and 26 or 20
		t.Parent = g
		a.Parent = labels
	end

	-- you spawn at home; Gate Court is how you leave
	local function marker(name, x, y, up)
		local m = Instance.new("Part")
		m.Name = name
		m.Anchored = true
		m.CanCollide, m.CanQuery, m.CanTouch = false, false, false
		m.Transparency = 1
		m.Size = Vector3.new(8, 8, 8)
		m.Position = Vector3.new(x + C.Offset.X, groundAt(x, y) + up, y + C.Offset.Z)
		m.Parent = root
		return m
	end
	local spawn = Instance.new("SpawnLocation")
	spawn.Name = "ValeV3Spawn"
	spawn.Anchored = true
	spawn.Size = Vector3.new(8, 1, 8)
	spawn.Position = Vector3.new(H.SpawnX + C.Offset.X, groundAt(H.SpawnX, H.SpawnY) + 0.3, H.SpawnY + C.Offset.Z)
	spawn.Neutral = true
	spawn.Duration = 0
	spawn.Parent = root
	marker("LandArrival", C.Arrival[1], C.Arrival[2], 5)
	local function prompt(parent, action, object, go, distance)
		local pr = Instance.new("ProximityPrompt")
		pr.ActionText = action
		pr.ObjectText = object
		pr.MaxActivationDistance = distance
		pr.UIOffset = Vector2.new(0, go == "Last" and 70 or 0)
		pr.KeyboardKeyCode = go == "Last" and Enum.KeyCode.F or Enum.KeyCode.E
		pr:SetAttribute("Go", go)
		pr.Parent = parent
	end
	local arch = marker("VerdantValeArch", H.ArchX, H.ArchY, 8)
	prompt(arch, "Enter", "Verdant Vale", "Land", 18)
	prompt(arch, "Back to last waystone", "Verdant Vale", "Last", 18)
	local stable = marker("TestMount", H.StableX, H.StableY, 4)
	prompt(stable, "Toggle test mount (60 studs/s)", "Stable plot", "Mount", 30)
	local travel = Instance.new("Script")
	travel.Name = "BlockoutTravel"
	travel.Source = TRAVEL_SOURCE
	travel.Parent = root

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
print("[ValeV3] " .. table.concat(report, ", "))
return table.concat(report, ", ")
