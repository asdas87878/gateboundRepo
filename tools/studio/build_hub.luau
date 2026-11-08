-- The hub's rough composition into the place (docs/lands/hub.md). Edit mode. Generated data: run the filled copy that
-- tools/art/hub_layout.py writes to art/hub/studio/build_hub.luau, not this template.
-- Every layer has its own folder in Workspace.Hub and is rebuilt only when it's on in RUN, so hand-placed work in other folders is
-- safe. Turn a layer off once you've edited it by hand. Terrain rewrites the whole deck and the plots: hand sculpting there is lost.
local RUN = {
	Setup = true, -- removes the Baseplate, moves the SpawnLocation to the waystone plaza
	Materials = true, -- the approved terrain tiles (MaterialVariants) and terrain colours
	Lighting = true, -- the approved lighting, the Stylized Skybox, gentle post effects
	Terrain = true, -- the deck, terraces, streets, plazas, pond and the plots' tops
	Island = true, -- stand-ins for the saucer under the deck, waterfalls, the land far below
	Walls = true, -- retaining walls round the terraces, the rim parapet
	Stairs = true, -- ramps where streets cross a wall (swap for stair assets)
	Lots = true, -- ghost boxes for buildings, labelled with the kit house or the asset still needed
	Docks = true, -- the arrival dock and the eight plot docks with their bridges
	Plots = true, -- stand-ins under the player plots
	Guides = true, -- lamp posts and benches marking the rhythm along the streets and plazas
	Labels = true, -- zone names floating over the map
}

local DATA = game:GetService("HttpService"):JSONDecode([==[__DATA__]==])
local Terrain = workspace.Terrain
local LIFT = DATA.Lift

local hub = workspace:FindFirstChild("Hub")
if not hub then
	hub = Instance.new("Folder")
	hub.Name = "Hub"
	hub.Parent = workspace
end

local function layer(name)
	local old = hub:FindFirstChild(name)
	if old then
		old:Destroy()
	end
	local f = Instance.new("Folder")
	f.Name = name
	return f
end

local function part(props, parent)
	local p = Instance.new(props.ClassName or "Part")
	p.Anchored = true
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Material = Enum.Material.SmoothPlastic
	for k, v in props do
		if k ~= "ClassName" then
			p[k] = v
		end
	end
	p.Parent = parent
	return p
end

local function label(parent, text, pos, colour, maxDistance)
	local anchor = part({ Name = "Label", Size = Vector3.one, Transparency = 1, CanCollide = false, CanQuery = false, CanTouch = false, CastShadow = false, Position = pos }, parent)
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(260, 34)
	gui.AlwaysOnTop = true
	gui.MaxDistance = maxDistance or 900
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Font = Enum.Font.GothamBold
	t.TextSize = 16
	t.TextColor3 = colour or Color3.new(1, 1, 1)
	t.TextStrokeTransparency = 0.25
	t.Text = text
	t.Parent = gui
	gui.Parent = anchor
	return anchor
end

local function at(a, r, c)
	a = math.rad(a)
	return (c and c[1] or 0) + r * math.sin(a), (c and c[2] or 0) + r * math.cos(a)
end

-- the height field, the same as hub_layout.py's
local function blobRadius(b, x, z)
	local dx, dz = x - b.C[1], z - b.C[2]
	local th = math.atan2(dz, dx)
	local s = 1
	for _, h in b.H do
		s += h[2] * math.cos(h[1] * th + h[3])
	end
	return b.R * s, math.sqrt(dx * dx + dz * dz)
end
local function deckRadius(x, z)
	local th = math.atan2(z, x)
	local s = 1
	for _, h in DATA.Deck.Wob do
		s += h[2] * math.cos(h[1] * th + h[3])
	end
	return DATA.Deck.R * s
end
local function heightAt(x, z)
	if math.sqrt(x * x + z * z) > deckRadius(x, z) then
		return nil
	end
	local h = 0
	for _, b in DATA.Blobs do
		local r, d = blobRadius(b, x, z)
		if d <= r and b.Top > h then
			h = b.Top
		end
	end
	return h
end
local function segDist(px, pz, ax, az, bx, bz)
	local vx, vz = bx - ax, bz - az
	local L2 = vx * vx + vz * vz
	local t = 0
	if L2 > 1e-9 then
		t = math.clamp(((px - ax) * vx + (pz - az) * vz) / L2, 0, 1)
	end
	local dx, dz = px - ax - vx * t, pz - az - vz * t
	return math.sqrt(dx * dx + dz * dz)
end

local report = {}

-- ---------------------------------------------------------------------------------------------------------- setup
if RUN.Setup then
	local bp = workspace:FindFirstChild("Baseplate")
	if bp then
		bp:Destroy()
	end
	local spawn = workspace:FindFirstChildOfClass("SpawnLocation") or Instance.new("SpawnLocation")
	spawn.Anchored = true
	spawn.Size = Vector3.new(12, 1, 12)
	spawn.Position = Vector3.new(DATA.Spawn[1], DATA.Spawn[2] + 0.5, DATA.Spawn[3])
	spawn.Transparency = 0.6
	spawn.Parent = workspace
	report.Setup = "spawn at the waystone plaza"
end

-- ---------------------------------------------------------------------------------------------------------- materials
if RUN.Materials then
	local MS = game:GetService("MaterialService")
	-- the approved low-key tiles (docs/style/terrain-method.md); the sand and cobble tints are this hub's
	local tiles = {
		{ "HubGrass", Enum.Material.Grass, "rbxassetid://120413043594048", 40 },
		{ "HubRock", Enum.Material.Rock, "rbxassetid://97571239280875", 40 },
		{ "HubMud", Enum.Material.Mud, "rbxassetid://99828434307675", 20 },
		{ "HubSand", Enum.Material.Sand, "rbxassetid://108417294349064", 36 },
	}
	for _, t in tiles do
		local old = MS:FindFirstChild(t[1])
		if old then
			old:Destroy()
		end
		local v = Instance.new("MaterialVariant")
		v.Name = t[1]
		v.BaseMaterial = t[2]
		v.ColorMap = t[3]
		v.StudsPerTile = t[4]
		v.MaterialPattern = Enum.MaterialPattern.Organic
		v.Parent = MS
		MS:SetBaseMaterialOverride(t[2], t[1])
	end
	Terrain:SetMaterialColor(Enum.Material.Grass, Color3.fromRGB(62, 150, 72))
	Terrain:SetMaterialColor(Enum.Material.Rock, Color3.fromRGB(122, 128, 126))
	Terrain:SetMaterialColor(Enum.Material.Mud, Color3.fromRGB(174, 150, 129))
	Terrain:SetMaterialColor(Enum.Material.Sand, Color3.fromRGB(240, 226, 190))
	Terrain:SetMaterialColor(Enum.Material.Cobblestone, Color3.fromRGB(214, 204, 188))
	Terrain:SetMaterialColor(Enum.Material.Pavement, Color3.fromRGB(226, 220, 208))
	Terrain.Decoration = true
	report.Materials = "4 tiles, terrain colours, grass blades on"
end

-- ---------------------------------------------------------------------------------------------------------- lighting
if RUN.Lighting then
	local L = game:GetService("Lighting")
	-- the values every asset's Studio grade was measured under (docs/style/art-style.md), plus the stylized extras of
	-- docs/style/roblox-lighting.md section 9
	L.Brightness = 3
	L.ClockTime = 15.6
	L.Ambient = Color3.fromRGB(69, 69, 69)
	L.OutdoorAmbient = Color3.fromRGB(110, 118, 145)
	L.ColorShift_Top = Color3.fromRGB(255, 236, 206)
	L.EnvironmentDiffuseScale = 0.35
	L.EnvironmentSpecularScale = 0.1
	L.GlobalShadows = true
	pcall(function()
		L.ShadowSoftness = 0.15
	end)
	pcall(function()
		L.LightingStyle = Enum.LightingStyle.Realistic
		L.PrioritizeLightingQuality = true
	end)
	local function fx(class, name)
		local e = L:FindFirstChildOfClass(class)
		if not e then
			e = Instance.new(class)
			e.Parent = L
		end
		e.Name = name
		return e
	end
	local atm = fx("Atmosphere", "Atmosphere")
	atm.Density, atm.Offset, atm.Haze, atm.Glare = 0.22, 0.18, 0.9, 0
	atm.Color = Color3.fromRGB(196, 218, 240)
	atm.Decay = Color3.fromRGB(150, 164, 196)
	local bloom = fx("BloomEffect", "Bloom")
	bloom.Intensity, bloom.Size, bloom.Threshold = 0.3, 24, 2.5
	local cc = fx("ColorCorrectionEffect", "Grade")
	cc.Saturation, cc.Contrast, cc.Brightness = 0.08, 0.05, 0
	cc.TintColor = Color3.fromRGB(255, 250, 244)
	for _, class in { "SunRaysEffect", "DepthOfFieldEffect" } do
		local e = L:FindFirstChildOfClass(class)
		if e then
			e.Enabled = false
		end
	end
	local ok, model = pcall(function()
		return game:GetService("InsertService"):LoadAsset(8755940451)
	end)
	local sky = ok and model:FindFirstChildWhichIsA("Sky", true)
	if sky then
		for _, s in L:GetChildren() do
			if s:IsA("Sky") then
				s:Destroy()
			end
		end
		sky.Name = "StylizedSky"
		sky.Parent = L
	end
	if ok then
		model:Destroy()
	end
	report.Lighting = sky and "set, Stylized Skybox in" or "set; the skybox didn't load, so the place's own Sky stays"
end

-- ---------------------------------------------------------------------------------------------------------- terrain
local function writeRegion(x0, z0, x1, z1, y0, y1, column)
	-- column(x, z) -> list of {lo, hi, material} solid spans in written heights, or nil
	local region = Region3.new(Vector3.new(x0, y0, z0), Vector3.new(x1, y1, z1)):ExpandToGrid(4)
	local size = region.Size / 4
	local nx, ny, nz = size.X, size.Y, size.Z
	local mn = region.CFrame.Position - region.Size / 2
	local mats, occ = table.create(nx), table.create(nx)
	for i = 1, nx do
		local mi, oi = table.create(ny), table.create(ny)
		for j = 1, ny do
			mi[j] = table.create(nz, Enum.Material.Air)
			oi[j] = table.create(nz, 0)
		end
		mats[i], occ[i] = mi, oi
	end
	local filled = 0
	for i = 1, nx do
		local cx = mn.X + 4 * i - 2
		for k = 1, nz do
			local cz = mn.Z + 4 * k - 2
			local spans = column(cx, cz, i, k)
			if spans then
				filled += 1
				for j = 1, ny do
					local lo = mn.Y + 4 * (j - 1)
					for _, s in spans do
						local o = math.clamp((s[2] - lo) / 4, 0, 1)
						if lo + 4 <= s[1] then
							o = 0
						end
						if o > 0 and o >= occ[i][j][k] then
							occ[i][j][k] = o
							mats[i][j][k] = (s[4] and lo + 4 <= s[2] - 4) and s[4] or s[3]
						end
					end
				end
			end
		end
	end
	Terrain:WriteVoxels(region, 4, mats, occ)
	return filled
end

if RUN.Terrain then
	local t0 = os.clock()
	local MAT = { Cobblestone = Enum.Material.Cobblestone, Sand = Enum.Material.Sand, Pavement = Enum.Material.Pavement }
	local R = DATA.Deck.R * 1.02
	local columns = 0
	for x0 = -1024, 1023, 256 do
		for z0 = -1024, 1023, 256 do
			if math.max(math.abs(x0 + 128) - 128, 0) ^ 2 + math.max(math.abs(z0 + 128) - 128, 0) ^ 2 > R * R then
				continue
			end
			-- surface materials for this chunk, painted shape by shape (plazas first, then streets in order; first wins)
			local grid = {}
			local wet = {}
			local function paint(cx, cz, rad, test, value, into)
				local i0, i1 = math.max(1, math.floor((cx - rad - x0) / 4) + 1), math.min(64, math.floor((cx + rad - x0) / 4) + 1)
				local k0, k1 = math.max(1, math.floor((cz - rad - z0) / 4) + 1), math.min(64, math.floor((cz + rad - z0) / 4) + 1)
				for i = i0, i1 do
					local px = x0 + 4 * i - 2
					for k = k0, k1 do
						local key = i * 100 + k
						if into[key] == nil and test(px, z0 + 4 * k - 2) then
							into[key] = value
						end
					end
				end
			end
			local P = DATA.Pond
			paint(P.C[1], P.C[2], P.R, function(px, pz)
				return (px - P.C[1]) ^ 2 + (pz - P.C[2]) ^ 2 <= P.R * P.R
			end, P.Floor, wet)
			for _, s in DATA.Streams do
				for n = 1, #s.Pts - 1 do
					local a, b = s.Pts[n], s.Pts[n + 1]
					paint((a[1] + b[1]) / 2, (a[2] + b[2]) / 2, math.abs(a[1] - b[1]) / 2 + math.abs(a[2] - b[2]) / 2 + s.W, function(px, pz)
						return segDist(px, pz, a[1], a[2], b[1], b[2]) <= s.W / 2
					end, -2.2, wet)
				end
			end
			for _, p in DATA.Plazas do
				paint(p.C[1], p.C[2], p.R, function(px, pz)
					return (px - p.C[1]) ^ 2 + (pz - p.C[2]) ^ 2 <= p.R * p.R
				end, MAT[p.Mat], grid)
			end
			for _, r in DATA.Roads do
				for n = 1, #r.Pts - 1 do
					local a, b = r.Pts[n], r.Pts[n + 1]
					if math.max(a[1], b[1]) + r.W < x0 or math.min(a[1], b[1]) - r.W > x0 + 256 or math.max(a[2], b[2]) + r.W < z0 or math.min(a[2], b[2]) - r.W > z0 + 256 then
						continue
					end
					paint((a[1] + b[1]) / 2, (a[2] + b[2]) / 2, math.abs(a[1] - b[1]) / 2 + math.abs(a[2] - b[2]) / 2 + r.W, function(px, pz)
						return segDist(px, pz, a[1], a[2], b[1], b[2]) <= r.W / 2
					end, MAT[r.Mat], grid)
				end
			end
			columns += writeRegion(x0, z0, x0 + 256, z0 + 256, -28, 44, function(cx, cz, i, k)
				local h = heightAt(cx, cz)
				if not h then
					return nil
				end
				local key = i * 100 + k
				local floor = wet[key]
				if floor and h == 0 then
					return { { DATA.Deck.Bottom, floor - LIFT, Enum.Material.Mud, Enum.Material.Rock }, { floor - LIFT, DATA.Pond.Water - LIFT, Enum.Material.Water } }
				end
				return { { DATA.Deck.Bottom, h - LIFT, grid[key] or Enum.Material.Grass, Enum.Material.Rock } }
			end)
			task.wait()
		end
	end
	-- the plots' tops: plain grass islands for the players' bases
	for _, p in DATA.Plots do
		local c, rad = p.C, p.R
		columns += writeRegion(c[1] - rad - 12, c[2] - rad - 12, c[1] + rad + 12, c[2] + rad + 12, -100, -60, function(cx, cz)
			local dx, dz = cx - c[1], cz - c[2]
			local th = math.atan2(dz, dx)
			local s = 1
			for _, h in p.Wob do
				s += h[2] * math.cos(h[1] * th + h[3])
			end
			if dx * dx + dz * dz > (rad * s) ^ 2 then
				return nil
			end
			return { { p.Bottom, p.Top - LIFT, Enum.Material.Grass, Enum.Material.Rock } }
		end)
		task.wait()
	end
	report.Terrain = string.format("%d columns in %.1f s", columns, os.clock() - t0)
end

-- ---------------------------------------------------------------------------------------------------------- the island
if RUN.Island then
	local f = layer("Island")
	for _, u in DATA.Underside do
		local h = u[2] - u[3]
		part({ Name = u[1], Shape = Enum.PartType.Cylinder, Size = Vector3.new(h, u[4] * 2, u[4] * 2), CFrame = CFrame.new(0, (u[2] + u[3]) / 2, 0) * CFrame.Angles(0, 0, math.pi / 2), Color = Color3.fromRGB(u[5][1], u[5][2], u[5][3]), CanCollide = false, CastShadow = true }, f)
	end
	for n, s in DATA.Streams do
		local e = s.Pts[#s.Pts]
		local a = math.deg(math.atan2(e[1], e[2]))
		local x, z = at(a, deckRadius(e[1], e[2]) + 3)
		part({ Name = "Waterfall" .. n, Size = Vector3.new(s.W + 4, 680, 1.5), CFrame = CFrame.new(x, -340, z) * CFrame.Angles(0, math.rad(a), 0), Color = Color3.fromRGB(206, 232, 250), Transparency = 0.35, CanCollide = false, CastShadow = false }, f)
	end
	local below = Instance.new("Folder")
	below.Name = "LandBelow"
	below.Parent = f
	for i = -2, 2 do
		for k = -2, 2 do
			part({ Name = "Ground", Size = Vector3.new(2048, 4, 2048), Position = Vector3.new(i * 2048, -3200, k * 2048), Color = Color3.fromRGB(120, 164, 96), CanCollide = false, CastShadow = false }, below)
		end
	end
	f.Parent = hub
	report.Island = #f:GetDescendants() .. " parts"
end

-- ---------------------------------------------------------------------------------------------------------- walls and stairs
if RUN.Walls then
	local f = layer("Walls")
	local stone, rim = Color3.fromRGB(206, 198, 184), Color3.fromRGB(222, 214, 198)
	for _, w in DATA.Walls do
		local h = w.Top - w.Bottom
		part({ Name = w.Kind, Size = Vector3.new(w.Kind == "Parapet" and 2 or 2.6, h, w.L), CFrame = CFrame.new(w.C[1], (w.Top + w.Bottom) / 2, w.C[2]) * CFrame.Angles(0, w.Yaw, 0), Color = w.Kind == "Parapet" and rim or stone, Material = Enum.Material.Slate }, f)
	end
	f.Parent = hub
	report.Walls = #DATA.Walls
end

if RUN.Stairs then
	local f = layer("Stairs")
	for _, s in DATA.Stairs do
		local rise = s.High - s.Low
		local run = rise * 1.7
		local dir = Vector3.new(s.Dir[1], 0, s.Dir[2])
		local top = Vector3.new(s.At[1], 0, s.At[2])
		local mid = top - dir * (run / 2) + Vector3.new(0, s.Low + rise / 2, 0)
		local w = part({ ClassName = "WedgePart", Name = "Stairs_" .. s.Road, Size = Vector3.new(s.W, rise, run), CFrame = CFrame.lookAt(mid, mid - dir), Color = Color3.fromRGB(232, 214, 160), Material = Enum.Material.Slate }, f)
		w:SetAttribute("Swap", "stair asset, " .. rise .. " studs up")
	end
	f.Parent = hub
	report.Stairs = #DATA.Stairs
end

-- ---------------------------------------------------------------------------------------------------------- lots
if RUN.Lots then
	local f = layer("Lots")
	local colours = { Civic = Color3.fromRGB(70, 110, 200), Shop = Color3.fromRGB(230, 140, 60), House = Color3.fromRGB(80, 160, 90), Special = Color3.fromRGB(160, 90, 200), Guide = Color3.fromRGB(245, 245, 245) }
	for _, l in DATA.Lots do
		local m = Instance.new("Model")
		m.Name = l.Name
		local y = l.Y or 0
		local guide = l.Kind == "Guide"
		local base = CFrame.new(l.X, y, l.Z) * CFrame.Angles(0, l.Yaw, 0)
		local box = part({ Name = "Ghost", Size = Vector3.new(l.Size[1], l.Size[2], l.Size[3]), CFrame = base * CFrame.new(0, l.Size[2] / 2, 0), Color = colours[l.Kind], Transparency = guide and 0.55 or 0.7, CanCollide = false, CastShadow = false }, m)
		if not guide then
			-- the front, where the door goes (a kit house's door faces its model's +z)
			part({ Name = "Front", Size = Vector3.new(l.Size[1] * 0.4, 1, 0.6), CFrame = base * CFrame.new(0, 0.5, l.Size[3] / 2 + 0.3), Color = Color3.fromRGB(255, 230, 90), Material = Enum.Material.Neon, CanCollide = false, CastShadow = false }, m)
		end
		m:SetAttribute("Kind", l.Kind)
		m:SetAttribute("Asset", l.Asset ~= "" and ("ServerStorage.HouseKit." .. l.Asset) or "")
		m:SetAttribute("Needs", l.Needs)
		m.PrimaryPart = box
		m.WorldPivot = base
		local text = l.Name .. (l.Asset ~= "" and ("  [" .. l.Asset .. "]") or ("  (needs: " .. l.Needs .. ")"))
		label(m, text, base.Position + Vector3.new(0, l.Size[2] + 6, 0), guide and Color3.fromRGB(230, 240, 255) or nil, 450)
		m.Parent = f
	end
	f.Parent = hub
	report.Lots = #DATA.Lots
end

-- ---------------------------------------------------------------------------------------------------------- docks, bridges and plots
if RUN.Docks then
	local f = layer("Docks")
	local stone, wood = Color3.fromRGB(214, 204, 188), Color3.fromRGB(150, 110, 76)
	for _, d in DATA.Docks do
		local m = Instance.new("Model")
		m.Name = d.Name
		local a = math.rad(d.A)
		local dir = Vector3.new(math.sin(a), 0, math.cos(a))
		local mid = dir * ((d.R0 + d.R1) / 2)
		local cf = CFrame.lookAt(mid, mid + dir)
		part({ Name = "Platform", Size = Vector3.new(d.W, 6, d.R1 - d.R0), CFrame = cf * CFrame.new(0, -3, 0), Color = stone, Material = Enum.Material.Slate }, m)
		for _, side in { -1, 1 } do
			part({ Name = "GatePost", Size = Vector3.new(4, 18, 4), CFrame = cf * CFrame.new(side * (d.W / 2 - 3), 9, -(d.R1 - d.R0) / 2 + 2.5), Color = stone, Material = Enum.Material.Slate }, m)
			part({ Name = "Rail", Size = Vector3.new(1.6, 3, d.R1 - d.R0 - 6), CFrame = cf * CFrame.new(side * (d.W / 2 - 0.8), 1.5, 3), Color = stone, Material = Enum.Material.Slate }, m)
		end
		if d.Bridge then
			local p0 = dir * d.R1
			local p1 = dir * (1330 - 150 + 12) + Vector3.new(0, -70, 0)
			local L = (p1 - p0).Magnitude
			local bcf = CFrame.lookAt((p0 + p1) / 2, p1)
			part({ Name = "Planks", Size = Vector3.new(12, 1, L), CFrame = bcf * CFrame.new(0, -0.5, 0), Color = wood, Material = Enum.Material.WoodPlanks }, m)
			for _, side in { -1, 1 } do
				part({ Name = "Rope", Size = Vector3.new(0.4, 0.4, L), CFrame = bcf * CFrame.new(side * 6, 3.6, 0), Color = Color3.fromRGB(196, 170, 120), CanCollide = false }, m)
			end
		end
		m.Parent = f
	end
	f.Parent = hub
	report.Docks = #DATA.Docks
end

if RUN.Plots then
	local f = layer("Plots")
	for _, p in DATA.Plots do
		local m = Instance.new("Model")
		m.Name = p.Name
		local rock = Color3.fromRGB(88, 92, 116)
		for n, step in { { p.R * 0.97, p.Bottom + 2, p.Bottom - 28 }, { p.R * 0.72, p.Bottom - 28, p.Bottom - 70 }, { p.R * 0.4, p.Bottom - 70, p.Bottom - 115 } } do
			local h = step[2] - step[3]
			part({ Name = "Under" .. n, Shape = Enum.PartType.Cylinder, Size = Vector3.new(h, step[1] * 2, step[1] * 2), CFrame = CFrame.new(p.C[1], (step[2] + step[3]) / 2, p.C[2]) * CFrame.Angles(0, 0, math.pi / 2), Color = rock, CanCollide = false }, m)
		end
		m.Parent = f
	end
	f.Parent = hub
	report.Plots = #DATA.Plots
end

-- ---------------------------------------------------------------------------------------------------------- guides and labels
if RUN.Guides then
	local f = layer("Guides")
	for _, g in DATA.Guides do
		local y = g.Y or 0
		if g.Name == "Lamp" then
			local m = Instance.new("Model")
			m.Name = "Lamp"
			part({ Name = "Post", Size = Vector3.new(g.Size[1], g.Size[2], g.Size[3]), Position = Vector3.new(g.X, y + g.Size[2] / 2, g.Z), Color = Color3.fromRGB(96, 70, 52) }, m)
			part({ Name = "Light", Size = Vector3.new(1.6, 1.6, 1.6), Position = Vector3.new(g.X, y + g.Size[2] + 0.8, g.Z), Color = Color3.fromRGB(255, 200, 120), Material = Enum.Material.Neon, CanCollide = false }, m)
			m.Parent = f
		else
			local pos = Vector3.new(g.X, y + g.Size[2] / 2, g.Z)
			local face = Vector3.new(g.Face[1], pos.Y, g.Face[2])
			part({ Name = "Bench", Size = Vector3.new(g.Size[1], g.Size[2], g.Size[3]), CFrame = CFrame.lookAt(pos, face), Color = Color3.fromRGB(150, 110, 76) }, f)
		end
	end
	f.Parent = hub
	report.Guides = #DATA.Guides
end

if RUN.Labels then
	local f = layer("Labels")
	for _, t in DATA.Labels do
		label(f, t.Text, Vector3.new(t.X, t.Y, t.Z), Color3.fromRGB(255, 244, 200), 4000)
	end
	f.Parent = hub
	report.Labels = #DATA.Labels
end

game:GetService("ChangeHistoryService"):SetWaypoint("Hub blockout")
return game:GetService("HttpService"):JSONEncode(report)
