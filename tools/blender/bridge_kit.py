"""The stone bridge in Blender (run headless): imports the OBJs from tools/art/bridge_kit.py, exports Bridge.glb, and renders views in the real land (terrain.png, water at level 8), back faces hidden as in Roblox.
  blender --background --python tools/blender/bridge_kit.py -- art/kit/bridge [--views river,deck,...] [--res 1280x720]
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(args[0])
VIEWS = args[args.index("--views") + 1].split(",") if "--views" in args else None
RX, RY = (int(v) for v in args[args.index("--res") + 1].split("x")) if "--res" in args else (1280, 720)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAND = os.path.join(ROOT, "art/lands/verdant_vale")
KIT = json.load(open(os.path.join(OUT, "kit.json")))
A = np.array(KIT["From"])
B = np.array(KIT["To"])
L = np.linalg.norm(B - A)
U = (B - A) / L
N = np.array((-U[1], U[0]))


def land(s, z, y):
	"""local bridge coords to Blender: land (x, y) goes to (x, -y), height to z"""
	p = A + U * s + N * z
	return Vector((p[0], -p[1], y))


bpy.ops.wm.read_factory_settings(use_empty=True)


def sheet_material(name, image):
	m = bpy.data.materials.new(name)
	m.use_nodes = True
	m.use_backface_culling = True
	nodes = m.node_tree
	principled = nodes.nodes["Principled BSDF"]
	principled.inputs["Roughness"].default_value = 1
	principled.inputs["Specular IOR Level"].default_value = 0  # no sheen: light is in the paint
	node = nodes.nodes.new("ShaderNodeTexImage")
	node.image = bpy.data.images.load(os.path.join(OUT, image))
	nodes.links.new(node.outputs["Color"], principled.inputs["Base Color"])
	return m


mat = sheet_material("Bridge", "Bridge_Color.png")
mat_top = sheet_material("BridgeTop", "Bridge_Top_Color.png")
objs = []
for name, info in KIT["Pieces"].items():
	bpy.ops.wm.obj_import(filepath=os.path.join(OUT, name + ".obj"), forward_axis="NEGATIVE_Z", up_axis="Y")
	o = bpy.context.selected_objects[0]
	o.name = name
	o.data.name = name
	o.data.materials.clear()
	o.data.materials.append(mat_top if name.startswith("BridgeTop") else mat)
	objs.append(o)
bpy.ops.object.select_all(action="DESELECT")
for o in objs:
	o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Bridge.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
yaw = math.atan2(-U[1], U[0])
for o in objs:
	c = KIT["Pieces"][o.name]["Centre"]
	# the importer's y-up turn is on the object, keep it under the yaw
	o.matrix_world = Matrix.Translation(land(c[0], c[2], c[1])) @ Matrix.Rotation(yaw, 4, "Z") @ o.matrix_world.to_3x3().to_4x4()

# the land, from the same height map as the Studio build
crop = np.load(os.path.join(OUT, "land_crop.npz"))
Z, M = crop["Z"], crop["M"]
x0, y0, step = int(crop["x0"]), int(crop["y0"]), int(crop["step"])
h, w = Z.shape
verts = [(x0 + k * step, -(y0 + j * step), float(Z[j, k])) for j in range(h) for k in range(w)]
faces = [(j * w + k, j * w + k + 1, (j + 1) * w + k + 1, (j + 1) * w + k) for j in range(h - 1) for k in range(w - 1)]
me = bpy.data.meshes.new("Land")
me.from_pydata(verts, [], faces)
me.update()
# Blender flips nothing on from_pydata: make every land face look up
for p in me.polygons:
	if p.normal.z < 0:
		p.flip()
me.update()
COL = {0: (86, 168, 84), 1: (240, 222, 150), 2: (176, 150, 128), 3: (138, 142, 138), 4: (160, 190, 100), 5: (196, 176, 96), 7: (232, 216, 150)}


def lin(c):
	return tuple(((v / 255) ** 2.2) for v in c) + (1,)


ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
for p in me.polygons:
	for li, vi in zip(p.loop_indices, p.vertices):
		j, k = vi // w, vi % w
		ca.data[li].color = lin(COL.get(int(M[j, k]), (86, 168, 84)))
for p in me.polygons:
	p.use_smooth = True
lo = bpy.data.objects.new("Land", me)
bpy.context.collection.objects.link(lo)
lm = bpy.data.materials.new("Land")
lm.use_nodes = True
ln = lm.node_tree.nodes.new("ShaderNodeVertexColor")
ln.layer_name = "Col"
lm.node_tree.links.new(ln.outputs["Color"], lm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
lm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1
me.materials.append(lm)
# water at level 8
bpy.ops.mesh.primitive_plane_add(size=1, location=(x0 + w * step / 2, -(y0 + h * step / 2), 8.0))
wo = bpy.context.object
wo.scale = (w * step, h * step, 1)
wm = bpy.data.materials.new("Water")
wm.use_nodes = True
wb = wm.node_tree.nodes["Principled BSDF"]
wb.inputs["Base Color"].default_value = lin((126, 208, 192))
wb.inputs["Roughness"].default_value = 0.35
wo.data.materials.append(wm)
sun = bpy.data.lights.new("Sun", "SUN")
sun.energy = 2.4
sun.color = (1, 0.96, 0.88)
sun.angle = math.radians(3)
so = bpy.data.objects.new("Sun", sun)
bpy.context.collection.objects.link(so)
so.rotation_euler = (math.radians(42), 0, math.radians(-40))
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.68, 0.95, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.85
bpy.context.scene.world = world
cam = bpy.data.cameras.new("C")
cam.sensor_fit = "VERTICAL"
cam.angle_y = math.radians(70)
co = bpy.data.objects.new("C", cam)
bpy.context.collection.objects.link(co)
bpy.context.scene.camera = co
s = bpy.context.scene
s.render.engine = "BLENDER_EEVEE"
s.render.resolution_x, s.render.resolution_y = RX, RY
s.view_settings.view_transform = "Standard"
s.render.image_settings.file_format = "PNG"


def ground(x, y):
	return float(Z[int(round((y - y0) / step)), int(round((x - x0) / step))])


def aim(eye, target):
	co.location = eye
	co.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()


def bank(s_, z_, up):
	"""a local point, up studs above whatever is there (land or water)"""
	p = A + U * s_ + N * z_
	return land(s_, z_, max(ground(p[0], p[1]), 8.0) + up)


D = 19 + 4
ALL = {
	# the spec's own views
	"hero": (Vector((767, -1467, ground(767, 1467) + 7)), Vector((1013, -1107, 22))),
	"deck_road": (Vector((933, -1164, ground(933, 1164) + 7)), Vector((1147, -1120, 22))),
	# from the river like the reference's framing: on the water, a little above it, downstream
	"river": (bank(46, 96, 5.5), land(70, 0, 15)),
	"river_up": (bank(92, -92, 5.5), land(70, 0, 15)),
	"river_low": (bank(22, 62, 2.2), land(58, 0, 15)),
	# walking across: over the shoulder height
	"deck": (land(28, 0, 21.2 + 6.2), land(95, 0, 22.5)),
	"deck_back": (land(118, -1.5, 21.2 + 6.2), land(40, 0.8, 21.5)),
	"close": (land(62, 2.0, 22.4 + 4.4), land(70, 7.8, 23.2)),
	# what a player meets: the end of the bridge from the road
	"end_near": (land(-26, 2.0, ground(*(A - U * 26 + N * 2)) + 6.6), land(5, 0, 19.5)),
	"end_far": (land(L + 28, -1.0, ground(*(B + U * 28 - N * 1)) + 6.6), land(L - 5, 0, 19.5)),
	# from above, so an inside-out face would show as a hole
	"above": (land(100, 54, 60), land(70, 0, 15)),
	"under": (bank(68, 26, 1.8), land(70, -8, 19)),
	# what you see leaning on the parapet and looking at the wall from a boat's distance
	"close_deck": (land(66, -2.5, 23 + 3.6), land(72, 4.5, 23.4)),
	"wall_close": (land(76, 24, 15), land(70, 8, 17)),
	# square on, long lens, land out of the way: how the rows line up
	"side": (land(L / 2, 250, 16), land(L / 2, 0, 15)),
	"side_back": (land(L / 2, -250, 16), land(L / 2, 0, 15)),
	"side_close": (land(45, 70, 16), land(45, 0, 15)),
}
if "--noland" in args:  # the bridge alone: for checking faces
	lo.hide_render = True
	wo.hide_render = True
for name in VIEWS or ALL:
	eye, target = ALL[name]
	aim(eye, target)
	square = name.startswith("side")
	lo.hide_render = square or "--noland" in args
	for o in objs:
		if o.name == "BridgeLoose":
			o.hide_render = square  # they sit on the land, which is hidden in these views
	cam.angle_y = math.radians(40 if name == "side_close" else 26 if square else 70)
	s.render.filepath = os.path.join(OUT, "views", name + ".png")
	bpy.ops.render.render(write_still=True)
	print("VIEW", name)
