-- The pink cottage study (private look test) into the place. Edit mode. Run the filled copy written by
-- tools/art/pink_cottage_luau.py (it fills __DATA__ with ids, bounds and settings): research/pink_cottage/place_filled.luau
-- Workspace.PinkCottage: every mesh its own anchored MeshPart, no collision, floating at DATA.Offset; rerunning replaces it.
-- Lighting is set for the study's look (sun aimed from Blender's sun direction); the previous values are kept as attributes on
-- Lighting ("PinkCottagePrev_*") so they can be put back.

local DATA = game:GetService("HttpService"):JSONDecode([==[__DATA__]==])
local OFFSET = Vector3.new(DATA.Offset[1], DATA.Offset[2], DATA.Offset[3])

local old = workspace:FindFirstChild("PinkCottage")
if old then
	old:Destroy()
end

local loaded = game:GetService("InsertService"):LoadAsset(DATA.Model)
local meshes = {}
for _, d in loaded:GetDescendants() do
	if d:IsA("MeshPart") then
		meshes[d.Name] = d
	end
end

local folder = Instance.new("Folder")
folder.Name = "PinkCottage"
local report = {}
local count = 0
for name, m in DATA.Meshes do
	local src = meshes[name]
	if not src then
		table.insert(report, "missing " .. name)
		continue
	end
	local p = src:Clone()
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanTouch = false
	p.CanQuery = false
	p.TextureID = ""
	for _, c in p:GetChildren() do
		c:Destroy()
	end
	pcall(function()
		p.RenderFidelity = Enum.RenderFidelity.Precise -- the camera stands ~280 studs off: no lower detail level
	end)
	local b = m.Bounds
	-- Blender's x, z, -y are Roblox's x, y, z; the importer turns each mesh half way round its own centre, so it's turned back
	p.CFrame = CFrame.new(OFFSET + Vector3.new((b[1] + b[4]) / 2, (b[3] + b[6]) / 2, -(b[2] + b[5]) / 2)) * CFrame.Angles(0, math.pi, 0)
	local want = Vector3.new(b[4] - b[1], b[6] - b[3], b[5] - b[2])
	if (p.Size - want).Magnitude > 0.5 then
		table.insert(report, name .. " size " .. tostring(p.Size) .. " wanted " .. tostring(want))
	end
	p.Material = Enum.Material.SmoothPlastic
	p.Color = Color3.new(1, 1, 1)
	if m.Kind == "sheet" then
		local sa = Instance.new("SurfaceAppearance")
		sa.ColorMap = "rbxassetid://" .. DATA.Sheets[name]
		-- the Studio grade, measured against the reference under this lighting: Roblox lights up-facing slates more than walls
		local g = DATA.Grade[name]
		if g then
			sa.Color = Color3.new(g[1], g[2], g[3])
		end
		sa.Parent = p
		p.CastShadow = true
	elseif m.Kind == "leaves" then
		local sa = Instance.new("SurfaceAppearance")
		sa.ColorMap = "rbxassetid://" .. DATA.Leaves
		sa.AlphaMode = Enum.AlphaMode.Transparency
		sa.Color = Color3.fromHex(m.Tint)
		sa.Parent = p
		p.CastShadow = false
	else
		p.CastShadow = true -- vertex coloured: the cloud foliage, flowers and plants
		-- SmoothPlastic is glossy under Realistic lighting: a bright roughness map makes it matte (the mesh has no UVs, so one value)
		local sa = Instance.new("SurfaceAppearance")
		sa.RoughnessMap = "rbxassetid://" .. DATA.Sheets.Garden
		sa.Parent = p
		local shade = DATA.FoliageShade[name]
		if shade then
			p.Color = Color3.fromRGB(shade[1], shade[2], shade[3]) -- multiplies the vertex colours: deeper greens, as the reference's
		end
	end
	p.Parent = folder
	count += 1
end
loaded:Destroy()
folder.Parent = workspace

-- lighting: keep what was there, then set the study's
local L = game:GetService("Lighting")
for _, prop in { "Brightness", "ClockTime", "GeographicLatitude", "OutdoorAmbient", "Ambient", "EnvironmentDiffuseScale", "EnvironmentSpecularScale", "ShadowSoftness", "ColorShift_Top", "ExposureCompensation" } do
	if L:GetAttribute("PinkCottagePrev_" .. prop) == nil then
		L:SetAttribute("PinkCottagePrev_" .. prop, L[prop])
	end
end
local S = DATA.Light
pcall(function()
	L.LightingStyle = Enum.LightingStyle.Realistic
end)
L.Brightness = S.Brightness
L.ExposureCompensation = S.Exposure
L.OutdoorAmbient = Color3.fromRGB(S.OutdoorAmbient[1], S.OutdoorAmbient[2], S.OutdoorAmbient[3])
L.Ambient = Color3.fromRGB(S.Ambient[1], S.Ambient[2], S.Ambient[3])
L.ColorShift_Top = Color3.fromRGB(S.ColorShiftTop[1], S.ColorShiftTop[2], S.ColorShiftTop[3])
L.EnvironmentDiffuseScale = S.EnvDiffuse
L.EnvironmentSpecularScale = S.EnvSpecular
L.ShadowSoftness = S.ShadowSoftness
L.GlobalShadows = true
-- the sun along Blender's direction (docs/style/roblox-lighting.md, section 3): Roblox (x, y, z) = Blender (x, z, -y)
local d = Vector3.new(S.Sun[1], S.Sun[2], S.Sun[3]).Unit
L.GeographicLatitude = 23.5 + math.deg(math.asin(d.Z))
L.ClockTime = (math.deg(math.atan2(d.X, -d.Y)) / 15) % 24
local got = L:GetSunDirection()

local dof = L:FindFirstChildOfClass("DepthOfFieldEffect")
if dof then
	dof.Enabled = false -- a far camera would be blurred
end
local atm = L:FindFirstChildOfClass("Atmosphere")
if atm then
	atm.Density = S.AtmosphereDensity
	atm.Haze = 0
	atm.Glare = 0
end
-- an unlit sky backdrop behind the reference's view, as its painted sky
local eye = Vector3.new(DATA.Camera.Eye[1], DATA.Camera.Eye[2], DATA.Camera.Eye[3])
local target = Vector3.new(DATA.Camera.Target[1], DATA.Camera.Target[2], DATA.Camera.Target[3])
local dir = (target - eye).Unit
local back = Instance.new("Part")
back.Name = "Backdrop"
back.Anchored = true
back.CanCollide = false
back.CanQuery = false
back.CanTouch = false
back.CastShadow = false
back.Transparency = 1
back.Size = Vector3.new(1100, 760, 1)
back.CFrame = CFrame.lookAt(target + dir * 900, eye)
local gui = Instance.new("SurfaceGui")
gui.Face = Enum.NormalId.Front
gui.LightInfluence = 0
gui.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
gui.CanvasSize = Vector2.new(400, 280)
gui.Brightness = 1.4 -- past 1, so the tone curve doesn't grey the sky
local frame = Instance.new("Frame")
frame.Size = UDim2.fromScale(1, 1)
frame.BorderSizePixel = 0
frame.BackgroundColor3 = Color3.new(1, 1, 1)
local grad = Instance.new("UIGradient")
grad.Rotation = 90
grad.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(84, 168, 255)),
	ColorSequenceKeypoint.new(0.55, Color3.fromRGB(110, 192, 255)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(164, 222, 255)),
})
grad.Parent = frame
frame.Parent = gui
gui.Parent = back
back.Parent = folder

local cc = L:FindFirstChild("PinkCottageGrade") or Instance.new("ColorCorrectionEffect")
cc.Name = "PinkCottageGrade"
cc.Saturation = S.Saturation
cc.Contrast = S.Contrast
cc.TintColor = Color3.fromRGB(S.Tint[1], S.Tint[2], S.Tint[3])
cc.Parent = L

return string.format("placed %d meshes; sun asked (%.3f, %.3f, %.3f) got (%.3f, %.3f, %.3f), ClockTime %.2f, latitude %.1f; %s", count, d.X, d.Y, d.Z, got.X, got.Y, got.Z, L.ClockTime, L.GeographicLatitude, #report > 0 and table.concat(report, "; ") or "sizes match")
