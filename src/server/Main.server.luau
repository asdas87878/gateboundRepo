--!strict
-- Loads every ModuleScript in Services/: Init on all of them first (setup, must not yield), then Start each in its
-- own thread.
local services = script.Parent:FindFirstChild("Services")
if not services then
	return
end

local loaded = {}
for _, module in services:GetChildren() do
	if module:IsA("ModuleScript") then
		table.insert(loaded, (require :: any)(module))
	end
end
for _, service in loaded do
	if service.Init then
		service.Init()
	end
end
for _, service in loaded do
	if service.Start then
		task.spawn(service.Start)
	end
end
