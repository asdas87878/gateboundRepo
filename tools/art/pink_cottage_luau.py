"""Fills tools/studio/place_pink_cottage.luau with the study's ids, bounds and light, and writes the view-camera snippet.

  python tools/art/pink_cottage_luau.py      -> research/pink_cottage/place_filled.luau, research/pink_cottage/camera.luau
"""

import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "research", "pink_cottage")
OFFSET = (4000.0, 300.0, 0.0)  # off the baseplate, so the view's background is sky as in the reference
CAM = {"Pitch": 20.0, "Yaw": 27.5, "FOV": 16.0, "Dist": 283.16, "Target": (10.184, 10.338, 12.274)}
SUN_BLENDER = (0.608, 0.467, -0.643)  # the direction light travels in tools/blender/pink_cottage.py
# measured in Studio against the reference (research/pink_cottage/studio): Roblox's sky light comes from above only, so most
# ambient goes in Ambient; its filmic tone curve caps white near 223, hence the exposure
LIGHT = {
	"Brightness": 2.8,
	"Exposure": 0.45,
	"OutdoorAmbient": (80, 78, 82),
	"Ambient": (146, 138, 134),
	"ColorShiftTop": (255, 240, 220),
	"EnvDiffuse": 0.15,
	"EnvSpecular": 0.1,
	"ShadowSoftness": 0.2,
	"AtmosphereDensity": 0.0,
	"Saturation": -0.05,
	"Contrast": 0.03,
	"Tint": (255, 250, 244),
}
# SurfaceAppearance.Color per sheet (multiplies the painted map), measured the same way: the slates read 20% too light in Studio
GRADE = {
	"RoofA": (0.76, 0.77, 0.81), "RoofB": (0.76, 0.77, 0.81), "RoofC": (0.76, 0.77, 0.81),
	"Tower": (1.07, 1.1, 1.18), "Walls": (0.97, 1.0, 1.0), "Walls2": (0.97, 1.0, 1.0),  # the tower's lit stone read dark and warm
	"Garden": (0.82, 0.87, 0.86), "Path": (0.95, 0.95, 0.95),
}
FOLIAGE_SHADE = {"BushRight": (175, 168, 175), "BushTower": (175, 168, 175), "TreeLeft": (170, 166, 172), "TreeLow": (170, 166, 172)}
LEAVES = 135970127157400  # the leaf atlas from the foliage test (docs/style/foliage-method.md)


def rbx(v):
	return (v[0], v[2], -v[1])


def main():
	exp = json.load(open(os.path.join(OUT, "export.json")))
	ids = json.load(open(os.path.join(OUT, "roblox.json")))["Files"]
	toward_sun = tuple(-c for c in SUN_BLENDER)
	light = dict(LIGHT, Sun=rbx(toward_sun))
	data = {
		"Offset": OFFSET,
		"Model": ids["PinkCottage.glb"]["Id"],
		"Leaves": LEAVES,
		"Sheets": {os.path.splitext(os.path.basename(k))[0]: v["Id"] for k, v in ids.items() if k.endswith(".png")},
		"Meshes": {k: {"Bounds": v["Bounds"], "Kind": v["Kind"], "Tint": v["Tint"]} for k, v in exp.items()},
		"Light": light,
		"Grade": GRADE,
		"FoliageShade": FOLIAGE_SHADE,
	}
	p_, w_ = math.radians(CAM["Pitch"]), math.radians(CAM["Yaw"])
	fwd_ = (-math.sin(w_) * math.cos(p_), math.cos(w_) * math.cos(p_), -math.sin(p_))
	t_ = CAM["Target"]
	eye_ = tuple(t_[i] - fwd_[i] * CAM["Dist"] for i in range(3))
	data["Camera"] = {"Eye": [rbx(eye_)[i] + OFFSET[i] for i in range(3)], "Target": [rbx(t_)[i] + OFFSET[i] for i in range(3)]}
	src = open(os.path.join(ROOT, "tools", "studio", "place_pink_cottage.luau"), encoding="utf-8").read()
	open(os.path.join(OUT, "place_filled.luau"), "w", encoding="utf-8").write(src.replace("__DATA__", json.dumps(data)))
	# the reference's view: the same camera as the Blender renders
	p, w = math.radians(CAM["Pitch"]), math.radians(CAM["Yaw"])
	fwd = (-math.sin(w) * math.cos(p), math.cos(w) * math.cos(p), -math.sin(p))
	t = CAM["Target"]
	eye = tuple(t[i] - fwd[i] * CAM["Dist"] for i in range(3))
	e, a = rbx(eye), rbx(t)
	e = tuple(e[i] + OFFSET[i] for i in range(3))
	a = tuple(a[i] + OFFSET[i] for i in range(3))
	cam = (
		"-- the reference's view of the pink cottage study (command bar, edit mode); set CameraType back to Fixed to fly again\n"
		"local cam = workspace.CurrentCamera\n"
		"cam.CameraType = Enum.CameraType.Scriptable\n"
		f"cam.FieldOfView = {CAM['FOV']}\n"
		f"cam.CFrame = CFrame.lookAt(Vector3.new({e[0]:.3f}, {e[1]:.3f}, {e[2]:.3f}), Vector3.new({a[0]:.3f}, {a[1]:.3f}, {a[2]:.3f}))\n"
		f"cam.Focus = CFrame.new({a[0]:.3f}, {a[1]:.3f}, {a[2]:.3f})\n"
	)
	open(os.path.join(OUT, "camera.luau"), "w", encoding="utf-8").write(cam)
	print("eye", [round(x, 2) for x in e], "target", [round(x, 2) for x in a], "sheets", len(data["Sheets"]), "meshes", len(data["Meshes"]))


if __name__ == "__main__":
	main()
