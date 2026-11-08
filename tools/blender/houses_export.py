"""Every house into one model for Roblox: art/kit/houses/Houses.glb, one mesh per sheet, named <House>_<Sheet>. Textures are uploaded apart (tools/art/houses_upload.py).
  blender --background --python tools/blender/houses_export.py
"""
import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HOUSES = ("Cottage", "Townhouse", "Farmhouse", "Bridgehouse", "Inn", "Mill", "Smithy", "Clocktower", "Manor", "Terrace", "Hut", "Tattered")
OUT = os.path.join(ROOT, "art", "kit", "houses")
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for house in HOUSES:
	for sheet in ("Frame", "Joinery", "Walls", "Roof", "Stone"):
		name = f"{house}_{sheet}"
		bpy.ops.wm.obj_import(filepath=os.path.join(ROOT, "art", "kit", house.lower(), name + ".obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
		o = bpy.context.selected_objects[0]
		o.name = o.data.name = name
		o.data.materials.clear()
		o.data.materials.append(bpy.data.materials.new(name))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Houses.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
print("exported", len(HOUSES) * 5, "meshes", os.path.getsize(os.path.join(OUT, "Houses.glb")))
