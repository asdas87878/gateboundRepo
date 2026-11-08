-- The stone sword into the place (docs/style/stone-sword.md). Edit mode. tools/art/upload_sword.py --luau <out> fills in __DATA__: run that output, not this file.
-- ServerStorage.SwordKit.StoneSword: a Model with its pivot on the ground at the blade's middle; drag copies out, then tilt them.
-- Workspace.SwordPack: a Folder with one upright and one leaning copy on a plain pad, beside the rock and house shelves. Rerunning replaces both, nothing else.
-- Meshes have no collision; invisible, locked Collider parts stand in for them.

local DATA = game:GetService("HttpService"):JSONDecode([==[__DATA__]==])
local Storage = game:GetService("ServerStorage")

local function clearOld(parent, name)
	local old = parent:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end
clearOld(Storage, "SwordKit")
clearOld(workspace, "SwordPack")

local loaded = game:GetService("InsertService"):LoadAsset(DATA.Files["StoneSword.glb"])
local meshes = {}
for _, d in loaded:GetDescendants() do
	if d:IsA("MeshPart") then
		meshes[d.Name] = d
	end
end

local model = Instance.new("Model")
model.Name = "StoneSword"
local report = {}
for name, b in DATA.Bounds do
	local mesh = meshes[name]
	assert(mesh, "no mesh called " .. name)
	local p = mesh:Clone()
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanTouch = false
	p.CanQuery = false
	p.TextureID = ""
	for _, c in p:GetChildren() do
		c:Destroy()
	end
	-- Blender's x, z, -y are Roblox's x, y, z; the importer turns each mesh half way round its own centre, so it's turned back
	p.CFrame = CFrame.new((b[1] + b[4]) / 2, (b[3] + b[6]) / 2, -(b[2] + b[5]) / 2) * CFrame.Angles(0, math.pi, 0)
	local want = Vector3.new(b[4] - b[1], b[6] - b[3], b[5] - b[2])
	if (p.Size - want).Magnitude > 0.3 then
		table.insert(report, name .. " size " .. tostring(p.Size) .. " wanted " .. tostring(want))
	end
	if name == "Outline" then
		p.Material = Enum.Material.Neon
		p.Color = Color3.fromRGB(24, 34, 36)
		p.CastShadow = false
	else
		p.Material = Enum.Material.SmoothPlastic
		p.CastShadow = true
		local sa = Instance.new("SurfaceAppearance")
		sa.ColorMap = "rbxassetid://" .. DATA.Files["Sword_" .. name .. ".png"]
		sa.Parent = p
	end
	p.Parent = model
end
loaded:Destroy()

-- plain boxes to walk into
local W, LB = DATA.Layout.W, DATA.Layout.LB
for _, c in
	{
		{ 0, LB / 2, 0, W * 0.92, LB, W * 0.3 },
		{ 0, LB + 0.2 * W, 0, 2.2 * W, 0.6 * W, 0.56 * W },
		{ 0, LB + 1.35 * W, 0, 0.5 * W, 1.9 * W, 0.5 * W },
		{ 0, LB + 2.6 * W, 0, 0.62 * W, 0.8 * W, 0.34 * W },
	}
do
	local box = Instance.new("Part")
	box.Name = "Collider"
	box.Anchored = true
	box.Transparency = 1
	box.CanTouch = false
	box.CastShadow = false
	box.Locked = true
	box.Size = Vector3.new(c[4], c[5], c[6])
	box.Position = Vector3.new(c[1], c[2], c[3])
	box.Parent = model
end
model.WorldPivot = CFrame.new()

local kit = Instance.new("Folder")
kit.Name = "SwordKit"
model.Parent = kit
kit.Parent = Storage

-- the shelf
local pack = Instance.new("Folder")
pack.Name = "SwordPack"
local ground = Instance.new("Part")
ground.Name = "ShelfGround"
ground.Anchored = true
ground.Size = Vector3.new(420, 2, 240)
ground.Position = Vector3.new(30000, -1, 950)
ground.Material = Enum.Material.SmoothPlastic
ground.Color = Color3.fromRGB(121, 170, 96)
ground.Parent = pack
local upright = model:Clone()
upright.Name = "Upright"
upright:PivotTo(CFrame.new(29930, 0, 950))
upright.Parent = pack
local leaning = model:Clone()
leaning.Name = "Leaning"
leaning:PivotTo(
	CFrame.new(30060, -1, 950) * CFrame.Angles(0, math.rad(35), 0) * CFrame.Angles(math.rad(-3), 0, math.rad(-7))
)
leaning.Parent = pack
pack.Parent = workspace

return "placed; " .. (#report > 0 and table.concat(report, "; ") or "sizes match")
