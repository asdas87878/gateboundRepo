--!strict
-- Loads every ModuleScript in Controllers/: Init on all of them first (setup, must not yield), then Start each in its
-- own thread.
local controllers = script.Parent:FindFirstChild("Controllers")
if not controllers then
	return
end

local loaded = {}
for _, module in controllers:GetChildren() do
	if module:IsA("ModuleScript") then
		table.insert(loaded, (require :: any)(module))
	end
end
for _, controller in loaded do
	if controller.Init then
		controller.Init()
	end
end
for _, controller in loaded do
	if controller.Start then
		task.spawn(controller.Start)
	end
end
