-- A shelf for the kits that have none (TreeKit, FenceKit, PropsKit, BridgeKit), beside the rock, house and sword shelves at
-- x 30,000. Edit mode. Copies only: the masters stay in ServerStorage. Rerunning replaces Workspace.KitShelf and nothing else.
-- To go there: select Workspace.KitShelf.ShelfGround in the Explorer and press F.
local SS = game:GetService("ServerStorage")
local AT = Vector3.new(30000, 0, 1120) -- the row starts past the sword shelf
local GAP = 14

local old = workspace:FindFirstChild("KitShelf")
if old then
	old:Destroy()
end
local shelf = Instance.new("Folder")
shelf.Name = "KitShelf"

local function label(parent, text, pos)
	local p = Instance.new("Part")
	p.Name = text
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.Transparency = true, false, false, false, 1
	p.Size = Vector3.one
	p.Position = pos
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(220, 30)
	gui.AlwaysOnTop = true
	gui.MaxDistance = 600
	local t = Instance.new("TextLabel")
	t.Size = UDim2.fromScale(1, 1)
	t.BackgroundTransparency = 1
	t.Font = Enum.Font.GothamBold
	t.TextSize = 15
	t.TextColor3 = Color3.new(1, 1, 1)
	t.TextStrokeTransparency = 0.3
	t.Text = text
	t.Parent = gui
	gui.Parent = p
	p.Parent = parent
end

local function sizeOf(inst)
	if inst:IsA("Model") then
		local _, s = inst:GetBoundingBox()
		return s
	end
	return inst.Size
end

local z = AT.Z
local maxX = 0
for _, kitName in { "PropsKit", "FenceKit", "BridgeKit", "TreeKit" } do
	local kit = SS:FindFirstChild(kitName)
	if not kit then
		continue
	end
	local row = Instance.new("Folder")
	row.Name = kitName
	row.Parent = shelf
	local items = kit:GetChildren()
	if kitName == "BridgeKit" then
		items = { kit:FindFirstChild("StoneBridge") }
	end
	table.sort(items, function(a, b)
		return a.Name < b.Name
	end)
	local x, depth = AT.X - 200, 0
	for _, item in items do
		local s = sizeOf(item)
		if x + s.X > AT.X + 420 then
			z += depth + GAP
			x, depth = AT.X - 200, 0
		end
		local copy = item:Clone()
		local pos = Vector3.new(x + s.X / 2, AT.Y, z + s.Z / 2)
		if copy:IsA("Model") then
			local cf, bs = copy:GetBoundingBox()
			copy:PivotTo(copy:GetPivot() + (pos + Vector3.new(0, bs.Y / 2, 0) - cf.Position))
		else
			copy.CFrame = CFrame.new(pos + Vector3.new(0, s.Y / 2, 0)) * (copy.CFrame - copy.CFrame.Position)
		end
		copy.Parent = row
		label(row, item.Name, pos + Vector3.new(0, s.Y + 4, 0))
		x += s.X + GAP
		depth = math.max(depth, s.Z)
		maxX = math.max(maxX, x)
	end
	label(row, kitName, Vector3.new(AT.X - 230, AT.Y + 8, z + depth / 2))
	z += depth + GAP * 2
end
local ground = Instance.new("Part")
ground.Name = "ShelfGround"
ground.Anchored = true
ground.Size = Vector3.new(700, 2, z - AT.Z + 40)
ground.Position = Vector3.new(AT.X + 110, AT.Y - 1, (AT.Z + z) / 2)
ground.Color = Color3.fromRGB(150, 170, 120)
ground.Material = Enum.Material.SmoothPlastic
ground.Parent = shelf
shelf.Parent = workspace
return string.format("KitShelf: %d items, z %d to %d", #shelf:GetDescendants(), AT.Z, z)
