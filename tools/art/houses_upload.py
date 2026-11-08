"""Uploads the houses' model and painted sheets once each, remembering the ids in art/kit/houses/assets.json, so a rerun only sends what changed. Uploads are permanent assets on the owner's account.
  python tools/art/houses_upload.py [look] [House,House: only these sheets, to test before sending them all]
Replaced ids are kept under "previous", so tools/art/houses_luau.py can swap them in place.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TOOL = r"C:\Users\blast\New folder\tools\roblox\upload_asset.py"
LOOK = sys.argv[1] if len(sys.argv) > 1 else "studio_match"
HOUSES = ("Cottage", "Townhouse", "Farmhouse", "Bridgehouse", "Inn", "Mill", "Smithy", "Clocktower", "Manor", "Terrace", "Hut", "Tattered")
if len(sys.argv) > 2:
	HOUSES = tuple(sys.argv[2].split(","))
STORE = os.path.join(ROOT, "art", "kit", "houses", "assets.json")
done = json.load(open(STORE)) if os.path.exists(STORE) else {}


def send(key, path, image):
	h = hashlib.sha1(open(path, "rb").read()).hexdigest()
	if done.get(key, {}).get("sha") == h:
		return
	cmd = [sys.executable, TOOL, path, "--name", key[:50], "--description", "Gatebound houses"] + (["--image"] if image else [])
	r = subprocess.run(cmd, capture_output=True, text=True)
	m = re.search(r"rbxassetid://(\d+) \(moderation: (\w+)\)", r.stdout)
	if not m:
		print("FAILED", key, (r.stdout + r.stderr)[-300:])
		sys.exit(1)
	old = done.get(key, {})
	done[key] = {"id": m.group(1), "sha": h, "moderation": m.group(2), "previous": old.get("previous", []) + ([old["id"]] if "id" in old else [])}
	json.dump(done, open(STORE, "w"), indent=1)
	print(key, m.group(1), m.group(2), flush=True)


send("Houses", os.path.join(ROOT, "art", "kit", "houses", "Houses.glb"), False)
for house in HOUSES:
	for sheet in ("Frame", "Joinery", "Walls", "Roof", "Stone"):
		send(f"{house}_{sheet}", os.path.join(ROOT, "art", "kit", "looks", LOOK, f"{house}_{sheet}.png"), True)
print("all uploaded", len(done))
