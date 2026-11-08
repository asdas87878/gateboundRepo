-- Turns a hand-made blockout (a folder of block Parts and wedges) into terrain; run in Studio's edit mode. docs/style/terrain-method.md.
-- Only changes terrain inside the blockout's own bounds. Rerunning rewrites that area, so hand sculpting and painting there is lost.
-- Afterwards the blocks are kept in ServerStorage.Blockouts.<Folder>. To change the shape: drag the folder back into Workspace, edit it, rerun.
-- Your blocks become one height surface, so overhangs and caves don't convert: make those with rocks or by hand.

local CONFIG = {
	Folder = "land1manual",
	Soft = 4, -- how soft edges and steps are, studs (a wall's line stays put, its foot and top round off about 7 studs each way)
	Wander = 5, -- how far straight edges bend, studs; 0 keeps them straight
	Relief = 1.2, -- slow rise and fall on flat ground, studs; 0 keeps it flat
	RockSlope = 0.85, -- rise per stud above which the surface is rock
	FootDirt = 0.3, -- rise per stud above which the foot of a slope is dirt (Mud); 0 turns the band off
	Margin = 40, -- empty room kept round the blockout, studs
}

local C = CONFIG
local S, G = 4, 2 -- voxel size, height grid size (2 height samples per voxel each way, so walls get soft edges)
local SURFACE_LIFT = 2 -- Roblox draws a surface this much above what the occupancy says (measured: 8.01 over a 6.05 block top), so it's taken off
local t = workspace.Terrain
local ServerStorage = game:GetService("ServerStorage")
local store = ServerStorage:FindFirstChild("Blockouts")
local folder = workspace:FindFirstChild(C.Folder) or (store and store:FindFirstChild(C.Folder))
assert(folder, "no blockout folder called " .. C.Folder)

local function ss(a, b, x)
	local k = math.clamp((x - a) / (b - a), 0, 1)
	return k * k * (3 - 2 * k)
end

-- each block or wedge as flat limits in its own space, so turned and tilted ones work: { nx, ny, nz, c } means nx*x + ny*y + nz*z <= c
local shapes, skipped = {}, {}
local minX, minY, minZ, maxX, maxY, maxZ = math.huge, math.huge, math.huge, -math.huge, -math.huge, -math.huge
for _, p in folder:GetDescendants() do
	local isWedge = p:IsA("WedgePart")
	if isWedge or (p:IsA("Part") and p.Shape == Enum.PartType.Block) then
		local hx, hy, hz = p.Size.X / 2, p.Size.Y / 2, p.Size.Z / 2
		local limits = {
			{ 1, 0, 0, hx },
			{ -1, 0, 0, hx },
			{ 0, -1, 0, hy },
			{ 0, 0, 1, hz },
			{ 0, 0, -1, hz },
			if isWedge then { 0, 1, -hy / hz, 0 } else { 0, 1, 0, hy },
		}
		local a, b = math.huge, -math.huge
		local c, d = math.huge, -math.huge
		for _, sx in { -1, 1 } do
			for _, sy in { -1, 1 } do
				for _, sz in { -1, 1 } do
					local v = p.CFrame * Vector3.new(hx * sx, hy * sy, hz * sz)
					a, b = math.min(a, v.X), math.max(b, v.X)
					c, d = math.min(c, v.Z), math.max(d, v.Z)
					minY, maxY = math.min(minY, v.Y), math.max(maxY, v.Y)
				end
			end
		end
		minX, maxX, minZ, maxZ = math.min(minX, a), math.max(maxX, b), math.min(minZ, c), math.max(maxZ, d)
		table.insert(shapes, { Part = p, Limits = limits, X0 = a, X1 = b, Z0 = c, Z1 = d })
	elseif p:IsA("BasePart") then
		table.insert(skipped, p.Name .. " (" .. p.ClassName .. ")")
	end
end
assert(#shapes > 0, "no blocks or wedges in " .. C.Folder)

local X0 = math.floor((minX - C.Margin) / S) * S
local Z0 = math.floor((minZ - C.Margin) / S) * S
local Y0 = math.floor(minY / S) * S
local NX = math.ceil((maxX + C.Margin - X0) / S)
local NZ = math.ceil((maxZ + C.Margin - Z0) / S)
local NY = math.ceil((maxY + C.Relief + S - Y0) / S)
local CX, CZ = NX * S // G, NZ * S // G
local floorY = Y0 -- "no land": the surface sits exactly on the bottom of the lowest voxels, so they stay empty

local function index(i, j)
	return (math.clamp(i, 1, CX) - 1) * CZ + math.clamp(j, 1, CZ)
end

-- 1. the top of the highest block over each grid point
local raw = table.create(CX * CZ, floorY)
for _, shape in shapes do
	local cf = shape.Part.CFrame
	local d = cf:VectorToObjectSpace(Vector3.yAxis)
	local i0 = math.max(1, math.floor((shape.X0 - X0) / G))
	local i1 = math.min(CX, math.ceil((shape.X1 - X0) / G) + 1)
	local j0 = math.max(1, math.floor((shape.Z0 - Z0) / G))
	local j1 = math.min(CZ, math.ceil((shape.Z1 - Z0) / G) + 1)
	for i = i0, i1 do
		local x = X0 + (i - 0.5) * G
		for j = j0, j1 do
			local o = cf:PointToObjectSpace(Vector3.new(x, 0, Z0 + (j - 0.5) * G))
			local low, high = -math.huge, math.huge
			for _, l in shape.Limits do
				local rate = l[1] * d.X + l[2] * d.Y + l[3] * d.Z
				local room = l[4] - (l[1] * o.X + l[2] * o.Y + l[3] * o.Z)
				if math.abs(rate) < 1e-6 then
					if room < 0 then
						high = -math.huge
						break
					end
				elseif rate > 0 then
					high = math.min(high, room / rate)
				else
					low = math.max(low, room / rate)
				end
			end
			if low <= high then
				local k = (i - 1) * CZ + j
				raw[k] = math.max(raw[k], high)
			end
		end
	end
	task.wait()
end

-- 2. straight edges bend: every point reads the blocks from a nearby spot. One height per column, so this can't fold the surface
local H = table.create(CX * CZ, floorY)
for i = 1, CX do
	local x = X0 + (i - 0.5) * G
	for j = 1, CZ do
		local z = Z0 + (j - 0.5) * G
		local wx = C.Wander * (2 * math.noise(x / 90, z / 90, 11.3) + 0.7 * math.noise(x / 31, z / 31, 5.7))
		local wz = C.Wander * (2 * math.noise(x / 90, z / 90, 23.9) + 0.7 * math.noise(x / 31, z / 31, 17.1))
		H[(i - 1) * CZ + j] = raw[index(math.round(i + wx / G), math.round(j + wz / G))]
	end
	if i % 64 == 0 then
		task.wait()
	end
end

-- 3. three box blurs, which round walls into cliffs with soft feet and tops
local r = math.max(1, math.round(C.Soft / G))
local width = 2 * r + 1
local function blur(alongI)
	local out = table.create(CX * CZ, floorY)
	local lines, length = if alongI then CZ else CX, if alongI then CX else CZ
	for a = 1, lines do
		local sum = 0
		for b = -r, r do
			sum += if alongI then H[index(b, a)] else H[index(a, b)]
		end
		for b = 1, length do
			sum += (if alongI then H[index(b + r, a)] else H[index(a, b + r)]) - (if alongI
				then H[index(b - r - 1, a)]
				else H[index(a, b - r - 1)])
			out[if alongI then index(b, a) else index(a, b)] = sum / width
		end
		if a % 64 == 0 then
			task.wait()
		end
	end
	H = out
end
for _ = 1, 3 do
	blur(true)
	blur(false)
end

-- 4. nothing dead flat
if C.Relief > 0 then
	for i = 1, CX do
		local x = X0 + (i - 0.5) * G
		for j = 1, CZ do
			local k = (i - 1) * CZ + j
			H[k] += C.Relief * 2 * math.noise(x / 38, (Z0 + (j - 0.5) * G) / 38, 3.3) * ss(0, 4, H[k] - floorY)
		end
		if i % 64 == 0 then
			task.wait()
		end
	end
end

-- 5. voxels, a slab at a time. Occupancy is how much of the voxel is under the surface, which keeps turned walls from sawtoothing.
-- Paint comes from the finished surface: steep is rock, the hollow at a slope's foot dirt, the rest grass; deep voxels are rock, seen only where a wall cuts them
local Air, Grass, Rock, Mud = Enum.Material.Air, Enum.Material.Grass, Enum.Material.Rock, Enum.Material.Mud
local counts = { Grass = 0, Rock = 0, Mud = 0 }
for first = 1, NX, 24 do
	local last = math.min(first + 23, NX)
	local M, O = table.create(last - first + 1), table.create(last - first + 1)
	for ix = first, last do
		local row = ix - first + 1
		M[row], O[row] = table.create(NY), table.create(NY)
		for iy = 1, NY do
			M[row][iy], O[row][iy] = table.create(NZ, Air), table.create(NZ, 0)
		end
		local i1, i2 = 2 * ix - 1, 2 * ix
		local x = X0 + (ix - 0.5) * S
		for iz = 1, NZ do
			local j1, j2 = 2 * iz - 1, 2 * iz
			local a, b, c, d =
				H[index(i1, j1)] - SURFACE_LIFT,
				H[index(i1, j2)] - SURFACE_LIFT,
				H[index(i2, j1)] - SURFACE_LIFT,
				H[index(i2, j2)] - SURFACE_LIFT
			local mean = (a + b + c + d) / 4
			local gx = (H[index(i2 + 1, j1)] + H[index(i2 + 1, j2)] - H[index(i1 - 1, j1)] - H[index(i1 - 1, j2)])
				/ (2 * 3 * G)
			local gz = (H[index(i1, j2 + 1)] + H[index(i2, j2 + 1)] - H[index(i1, j1 - 1)] - H[index(i2, j1 - 1)])
				/ (2 * 3 * G)
			local z = Z0 + (iz - 0.5) * S
			local slope = math.sqrt(gx * gx + gz * gz)
			local paint = Grass
			if slope > C.RockSlope + 0.3 * math.noise(x / 18, z / 18, 9.1) then
				paint = Rock
			elseif C.FootDirt > 0 then
				-- measured 9 studs either way, so the band reaches out from the wall rather than being one voxel wide
				local left, right, near, far =
					H[index(i1 - 4, j1)], H[index(i2 + 4, j1)], H[index(i1, j1 - 4)], H[index(i1, j2 + 4)]
				local wide = math.sqrt((right - left) ^ 2 + (far - near) ^ 2) / (9 * G)
				if
					wide > C.FootDirt + 0.2 * math.noise(x / 24, z / 24, 31.7)
					and left + right + near + far > 4 * (mean + SURFACE_LIFT)
				then
					paint = Mud -- the surface curves upward here, so this is a foot, not a top edge
				end
			end
			for iy = 1, NY do
				local bottom = Y0 + (iy - 1) * S
				local o = (
					math.clamp((a - bottom) / S, 0, 1)
					+ math.clamp((b - bottom) / S, 0, 1)
					+ math.clamp((c - bottom) / S, 0, 1)
					+ math.clamp((d - bottom) / S, 0, 1)
				) / 4
				if o >= 0.08 then
					local material = if bottom + S > mean - 6 then paint else Rock
					M[row][iy][iz], O[row][iy][iz] = material, if o > 0.97 then 1 else o
					counts[material.Name] += 1
				end
			end
		end
	end
	local from = Vector3.new(X0 + (first - 1) * S, Y0, Z0)
	local to = Vector3.new(X0 + last * S, Y0 + NY * S, Z0 + NZ * S)
	t:WriteVoxels(Region3.new(from, to), S, M, O)
	task.wait()
end

-- the blocks stay safe but out of the way
local wasIn = folder.Parent == workspace
if wasIn then
	if not store then
		store = Instance.new("Folder")
		store.Name = "Blockouts"
		store.Parent = ServerStorage
	end
	folder.Parent = store
end

return string.format(
	"%d blocks -> terrain x %d..%d, y %d..%d, z %d..%d (%dx%dx%d voxels), solid voxels grass %d mud %d rock %d; %s%s",
	#shapes,
	X0,
	X0 + NX * S,
	Y0,
	Y0 + NY * S,
	Z0,
	Z0 + NZ * S,
	NX,
	NY,
	NZ,
	counts.Grass,
	counts.Mud,
	counts.Rock,
	if wasIn then "blocks moved to ServerStorage.Blockouts" else "blocks read from ServerStorage.Blockouts",
	if #skipped > 0 then "; skipped (only blocks and wedges convert): " .. table.concat(skipped, ", ") else ""
)
