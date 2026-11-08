-- Rebuilds the test river scene's terrain from one smooth height field (docs/style/terrain-method.md); run in Studio's edit mode.
-- Replaces Parts + noise warp + blur, which folded the voxels and left almost no beach. Clears ALL terrain first.
-- Shape comes from distance to the river's edge; materials come from the finished surface's height and slope.

local CONFIG = {
	WaterLevel = 8,
	BedHeight = 3,
	BeachTop = 10, -- height where the beach's first slope ends (above the water, so sand shows)
	BeachWidth = { 18, 6 }, -- studs, and how much it varies along the river
	ShelfHeight = 17, -- the walkable ground
	CliffAt = { 72, 5 }, -- distance from the river's edge
	CliffWidth = 12,
	CliffTop = { 1, 50, -1, 34 }, -- +z side height, -z side height
	HillRise = 22,
	LandEnd = 166, -- distance from the river where the land stops
	EndWall = { 165, 180, 44 }, -- x range and height of the wall closing the river's +x end
	GroundNoise = 1.3, -- slow relief on the land, studs
	RockSlope = 0.85, -- rise per stud above which the surface is rock
	SandTop = 12.5, -- height below which the river's banks are sand
	PathOffset = 54, -- distance from the river's edge on the +z shelf
	PathWander = 7,
	PathWidth = 5.5, -- half width
	WornWidth = 0, -- off: blades only grow on Grass, so a band of another material removes the jagged edge the blades make
}

local t = workspace.Terrain
local S = 4
local X0, X1, Z0, Z1, YH = -200, 200, -244, 244, 84
local C = CONFIG

local function ss(a, b, x)
	local k = math.clamp((x - a) / (b - a), 0, 1)
	return k * k * (3 - 2 * k)
end
local function zc(x)
	return 16 * math.sin(x / 58) + 7 * math.sin(x / 23 + 1.3)
end
local function hw(x)
	return 24 + 8 * math.sin(x / 41 + 0.6)
end

-- the surface height at a point, and what the path needs
local function surface(x, z)
	local side = z >= zc(x) and 1 or -1
	local d = math.abs(z - zc(x)) - hw(x)
	local nA = math.noise(x / 46, side * 3.1, 1.7)
	local nB = math.noise(x / 38, side * 5.3, 7.9)
	local beach = C.BeachWidth[1] + C.BeachWidth[2] * nA
	local cliffAt = C.CliffAt[1] + C.CliffAt[2] * nB
	local top = (side > 0 and C.CliffTop[2] or C.CliffTop[4]) + 3 * nA
	local h = C.BedHeight
	h += (C.BeachTop - C.BedHeight) * ss(0, beach, d)
	h += 4 * ss(beach, beach + 12, d)
	h += (C.ShelfHeight - C.BeachTop - 4) * ss(beach + 12, beach + 24, d)
	h += (top - C.ShelfHeight) * ss(cliffAt, cliffAt + C.CliffWidth, d)
	h += C.HillRise * ss(cliffAt + 40, cliffAt + 90, d)
	h += C.GroundNoise * math.noise(x / 30, z / 30, 3.3) * ss(beach, beach + 16, d)
	h = math.max(h, C.EndWall[3] * ss(C.EndWall[1], C.EndWall[2], x))
	local pathU = C.PathOffset + C.PathWander * math.sin(x / 31)
	local path = side > 0 and math.abs(d - pathU) or math.huge
	if path < C.PathWidth + 4 then -- level the ground under the path, fading out past its edge
		local k = ss(C.PathWidth + 4, C.PathWidth, path)
		h += (C.ShelfHeight - h) * k * 0.8
	end
	return h, d, path
end

local region = Region3.new(Vector3.new(X0, 0, Z0), Vector3.new(X1, YH, Z1)):ExpandToGrid(S)
local NX = math.round(region.Size.X / S)
local NY = math.round(region.Size.Y / S)
local NZ = math.round(region.Size.Z / S)
local ox, oy, oz = region.CFrame.X - region.Size.X / 2, region.CFrame.Y - region.Size.Y / 2, region.CFrame.Z - region.Size.Z / 2

local Air, Water = Enum.Material.Air, Enum.Material.Water
local Grass, Sand, Rock, Mud = Enum.Material.Grass, Enum.Material.Sand, Enum.Material.Rock, Enum.Material.Mud
local M, O = table.create(NX), table.create(NX)
for ix = 1, NX do
	M[ix], O[ix] = table.create(NY), table.create(NY)
	for iy = 1, NY do
		M[ix][iy], O[ix][iy] = table.create(NZ), table.create(NZ)
	end
	local x = ox + (ix - 0.5) * S
	for iz = 1, NZ do
		local z = oz + (iz - 0.5) * S
		local h, d, path = surface(x, z)
		local gx = (surface(x + 2, z) - surface(x - 2, z)) / 4
		local gz = (surface(x, z + 2) - surface(x, z - 2)) / 4
		local slope = math.sqrt(gx * gx + gz * gz)
		local mat = Grass
		if slope > C.RockSlope then
			mat = Rock
		elseif path < C.PathWidth + 1.5 * math.noise(x / 13, z / 13) then
			mat = Mud
		elseif C.WornWidth > 0 and path < C.PathWidth + C.WornWidth + 2 * math.noise(x / 11, z / 11, 6.1) then
			mat = Enum.Material.Ground
		elseif h < C.SandTop + 1.5 * math.noise(x / 17, z / 17, 4.2) and d < 50 then
			mat = Sand
		end
		local land = d <= C.LandEnd
		for iy = 1, NY do
			local bottom = oy + (iy - 1) * S
			local o = land and math.clamp((h - bottom) / S, 0, 1) or 0
			if o > 0 then
				M[ix][iy][iz], O[ix][iy][iz] = mat, o
			elseif land and bottom + S <= C.WaterLevel then
				M[ix][iy][iz], O[ix][iy][iz] = Water, 1
			else
				M[ix][iy][iz], O[ix][iy][iz] = Air, 0
			end
		end
	end
	if ix % 10 == 0 then
		task.wait()
	end
end
t:Clear()
t:WriteVoxels(region, S, M, O)
task.wait(1)

-- re-seat the trees and bushes on grass near where they stood
local foliage = workspace:FindFirstChild("Foliage")
local report = {}
if foliage then
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { t }
	params.IgnoreWater = true
	local function findGrass(x, z)
		for r = 0, 60, 2 do
			for _, dz in ipairs({ r, -r }) do
				local hit = workspace:Raycast(Vector3.new(x, 150, z + dz), Vector3.new(0, -200, 0), params)
				if hit and hit.Material == Grass and hit.Normal.Y > 0.9 then
					return hit.Position
				end
			end
		end
		return nil
	end
	for _, m in ipairs(foliage:GetChildren()) do
		if m:IsA("Model") and m.Name == "Tree" then
			local trunk = m.Trunk
			local footOffset = trunk.Size.Y / 2 - trunk.Size.Y / 32
			local foot = trunk.Position - Vector3.new(0, footOffset, 0)
			local p = findGrass(foot.X, foot.Z)
			if p then
				m:PivotTo(m:GetPivot() + (p - foot))
				table.insert(report, string.format("tree -> %.0f, %.1f, %.0f", p.X, p.Y, p.Z))
			end
		elseif m.Name == "Bush" then
			local p = findGrass(m.Position.X, m.Position.Z)
			if p then
				m.Position = p + Vector3.new(0, m.Size.Y / 2 - 0.8, 0)
			end
		end
	end
end

return string.format("cells %d, voxels %dx%dx%d\n%s", t:CountCells(), NX, NY, NZ, table.concat(report, "\n"))
