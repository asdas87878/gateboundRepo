-- Builds the river scene's rock walls as terraces from ServerStorage.RockKit; run in Studio's edit mode (docs/style/rock-kit.md).
-- Each row sits at the place the cliff actually reaches that height (found by raycast), and each row's top hides the base of the row above. The cliff top
-- caps the height, the path has a corridor no colliding rock enters, and a last pass plugs any terrain still seen from where a player stands.
-- Rebuilds Rocks_Wall_Near, _Far, _End only. It never touches Rocks_Shore, Rocks_Water or anything else, so hand-placed rocks belong in another folder.

local CONFIG = {
	Seed = 41,
	Step = 10, -- studs of height per row
	Overlap = 0.62, -- share of a rock's width before the next one in its row
	Rows = { "WallWide", "WallLong", "WallStep", "WallMid", "CliffWide", "WallHigh", "Block", "BlockChunk" },
	Foot = { "FootWide", "FootStub", "FootWedge", "SlabLong", "SlabBroken", "SlabStack", "BoulderWide" },
	Small = { "Stone", "BoulderSmall", "ChipTall", "BoulderRound", "SlabSmall" },
	Plug = { "Block", "BlockChunk", "BlockSmall", "WallMid" },
	PathClear = 6.5, -- half width of the corridor along the path
	MaxPlugs = 30,
}

local C = CONFIG
local t = workspace.Terrain
local kit = game:GetService("ServerStorage").RockKit
local r = Random.new(C.Seed)
local tOnly = RaycastParams.new()
tOnly.FilterType = Enum.RaycastFilterType.Include
tOnly.FilterDescendantsInstances = { t }
tOnly.IgnoreWater = true

local function zc(x) return 16 * math.sin(x / 58) + 7 * math.sin(x / 23 + 1.3) end
local function hw(x) return 24 + 8 * math.sin(x / 41 + 0.6) end
local function cliffAt(x, side) return 72 + 5 * math.noise(x / 38, side * 5.3, 7.9) end
local function pathU(x) return 54 + 7 * math.sin(x / 31) end
local function ground(x, z)
	local h = workspace:Raycast(Vector3.new(x, 150, z), Vector3.new(0, -200, 0), tOnly)
	return h and h.Position.Y or 0, h and h.Material or Enum.Material.Air
end

local function riverFrame(side, name)
	return {
		name = name,
		from = -198,
		to = 152,
		top = side > 0 and 53 or 37,
		pos = function(s, d) return s, zc(s) + side * (hw(s) + d) end,
		yaw = function(s) return math.deg(math.atan2(-(zc(s + 1) - zc(s - 1)) / 2, 1)) + (side > 0 and 180 or 0) end,
		d0 = function(s) return cliffAt(s, side) end,
		minD = function(s) return side > 0 and pathU(s) + C.PathClear or -math.huge end,
	}
end
local FRAMES = {
	riverFrame(1, "Rocks_Wall_Near"),
	riverFrame(-1, "Rocks_Wall_Far"),
	{
		name = "Rocks_Wall_End",
		from = -150,
		to = 150,
		top = 47,
		pos = function(s, d) return 158 + d, s end,
		yaw = function() return -90 end,
		d0 = function() return 2 end,
		minD = function() return -math.huge end,
	},
}

local report = {}
local folders = {}
for _, f in ipairs(FRAMES) do
	local old = workspace:FindFirstChild(f.name)
	if old then old:Destroy() end
	local folder = Instance.new("Folder")
	folder.Name = f.name
	folder.Parent = workspace
	folders[f.name] = folder
	local last = {}
	local function pick(list, key)
		local n
		repeat n = list[r:NextInteger(1, #list)] until n ~= last[key]
		last[key] = n
		return n
	end
	local function place(name, s, d, baseY, height, yawJit)
		local src = kit[name]
		local scale = height and math.clamp(height / src.Size.Y, 0.6, 1.7) or 1
		local c = src:Clone()
		c.Size *= scale
		local x, z = f.pos(s, d)
		c.CFrame = CFrame.new(x, baseY + c.Size.Y / 2, z) * CFrame.Angles(0, math.rad(f.yaw(s) + yawJit), 0)
		c.CanCollide = c.Size.Y > 2
		c.Parent = folder
		return c
	end
	local function clampD(s, d, depth)
		return math.max(d, f.minD(s) + depth * 0.55)
	end
	local function surfaceD(s, y)
		local d0 = f.d0(s)
		for d = d0 - 6, d0 + 36 do
			local x, z = f.pos(s, d)
			if ground(x, z) >= y then return d end
		end
		return nil
	end
	-- terraces, staggered like brickwork
	for k = 0, 6 do
		local s = f.from + k * 7
		local placedInRow = 0
		while s < f.to do
			local d0 = f.d0(s)
			local bx, bz = f.pos(s, d0 - 2)
			local floor = ground(bx, bz)
			local y = floor + k * C.Step
			local name = pick(C.Rows, "row" .. k)
			local h = C.Step + r:NextNumber(k == 0 and 4 or 3, k == 0 and 9 or 7)
			local base = k == 0 and y - 1.5 or y - 2
			local room = f.top + 3 - base
			if room < 4 then
				s += 8
			else
				h = math.min(h, room)
				local scale = math.clamp(h / kit[name].Size.Y, 0.6, 1.7)
				local depth = kit[name].Size.Z * scale
				local d = k == 0 and d0 + 3 or surfaceD(s, y)
				if d then
					d = clampD(s, d, depth)
					place(name, s, d, base, h, r:NextNumber(-14, 14))
					placedInRow += 1
				end
				s += kit[name].Size.X * scale * C.Overlap
			end
		end
		if placedInRow == 0 then break end
		task.wait()
	end
	-- foot rocks off parallel, with gaps
	local s = f.from
	while s < f.to do
		local name = pick(C.Foot, "foot")
		local scale = r:NextNumber(0.9, 1.3)
		local depth = kit[name].Size.Z * scale
		local d = clampD(s, f.d0(s) - 4 + r:NextNumber(-2, 1), depth)
		local x, z = f.pos(s, d)
		place(name, s, d, ground(x, z) - 0.6, kit[name].Size.Y * scale, r:NextNumber(-28, 28))
		s += kit[name].Size.X * scale + r:NextNumber(0, 7)
	end
	-- small stones in loose groups
	s = f.from
	while s < f.to do
		s += r:NextNumber(8, 24)
		for _ = 1, r:NextInteger(1, 3) do
			local ps = s + r:NextNumber(-3, 3)
			local d = clampD(ps, f.d0(ps) - 9 + r:NextNumber(-3, 2), 2)
			local x, z = f.pos(ps, d)
			local name = pick(C.Small, "small")
			place(name, ps, d, ground(x, z) - 0.3, kit[name].Size.Y * r:NextNumber(0.6, 1.1), r:NextNumber(-180, 180))
		end
	end
	task.wait()
end

-- what a player can still see of the terrain's rock, from the walkway, across the river, and along it at the end wall
local list = { t }
for _, n in pairs(folders) do table.insert(list, n) end
table.insert(list, workspace.Rocks_Shore)
local all = RaycastParams.new()
all.FilterType = Enum.RaycastFilterType.Include
all.FilterDescendantsInstances = list
all.IgnoreWater = true
local function visible()
	local out = {}
	for fi = 1, 3 do
		local f = FRAMES[fi]
		for s = f.from, f.to, 5 do
			local d0 = f.d0(s)
			local eyes
			if fi == 3 then
				eyes = { Vector3.new(112, 16, zc(112) + s * 0.2) }
			else
				local side = fi == 1 and 1 or -1
				local ex, ez = f.pos(s - 6, d0 - 26)
				eyes = { Vector3.new(ex, ground(ex, ez) + 5, ez), Vector3.new(s + 10, 13, zc(s) - side * (hw(s) + 14)) }
			end
			for d = d0 - 2, d0 + 26, 2 do
				local x, z = f.pos(s, d)
				local y, mat = ground(x, z)
				if mat == Enum.Material.Rock then
					local p = Vector3.new(x, y + 0.3, z)
					for _, e in ipairs(eyes) do
						local hit = workspace:Raycast(e, (p - e) * 1.02, all)
						if hit and hit.Instance == t then
							table.insert(out, { f = f, s = s, d = d, y = y })
							break
						end
					end
				end
			end
		end
		task.wait()
	end
	return out
end
local before = #visible()
local plugs = 0
for _ = 1, 3 do
	local v = visible()
	if #v == 0 or plugs >= C.MaxPlugs then break end
	for i = #v, 2, -1 do
		local j = r:NextInteger(1, i)
		v[i], v[j] = v[j], v[i]
	end
	local used = {}
	for _, g in ipairs(v) do
		if plugs >= C.MaxPlugs then break end
		local clash = false
		for _, u in ipairs(used) do
			if u.f == g.f and math.abs(u.s - g.s) < 12 and math.abs(u.y - g.y) < 8 then clash = true; break end
		end
		if not clash then
			local name = C.Plug[r:NextInteger(1, #C.Plug)]
			local base = g.y - 3
			local h = math.min(r:NextNumber(9, 13), g.f.top + 3 - base)
			if h > 4 then
				local scale = math.clamp(h / kit[name].Size.Y, 0.6, 1.6)
				local c = kit[name]:Clone()
				c.Size *= scale
				local x, z = g.f.pos(g.s, g.d)
				c.CFrame = CFrame.new(x, base + c.Size.Y / 2, z) * CFrame.Angles(0, math.rad(g.f.yaw(g.s) + r:NextNumber(-18, 18)), 0)
				c.Parent = folders[g.f.name]
				table.insert(used, g)
				plugs += 1
			end
		end
	end
	task.wait()
end
local after = #visible()

-- results
local rocks = RaycastParams.new()
rocks.FilterType = Enum.RaycastFilterType.Include
local rl = {}
for _, n in pairs(folders) do table.insert(rl, n) end
rocks.FilterDescendantsInstances = rl
local blocked, tested = 0, 0
for x = -190, 150, 3 do
	for _, off in ipairs({ -3, 0, 3 }) do
		local z = zc(x) + hw(x) + pathU(x) + off
		tested += 1
		local h = workspace:Raycast(Vector3.new(x, ground(x, z) + 30, z), Vector3.new(0, -29, 0), rocks)
		if h and h.Instance.CanCollide then blocked += 1 end
	end
end
for _, n in pairs(folders) do table.insert(report, n.Name .. " " .. #n:GetChildren()) end
table.insert(report, string.format("plugs %d, visible terrain points %d -> %d, rock over path %d of %d", plugs, before, after, blocked, tested))
return table.concat(report, "\n")
