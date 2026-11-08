"""Upload the rock pack to Roblox and note the ids in art/kit/rock_pack/roblox.json, which tools/studio/rock_pack.luau reads.

  python tools/art/upload_rock_pack.py

Only uploads what changed since last time (a hash per file is kept beside each id). Uploads can fail silently, so each file gets three tries.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "rock_pack")
UPLOADER = r"C:\Users\blast\New folder\tools\roblox\upload_asset.py"
STATE = os.path.join(OUT, "roblox.json")


def digest(path):
	return hashlib.sha1(open(path, "rb").read()).hexdigest()[:16]


def upload(path):
	name = os.path.splitext(os.path.basename(path))[0]
	args = [sys.executable, UPLOADER, path, "--name", name, "--description", "Gatebound rock pack"]
	if path.endswith(".png"):
		args.append("--image")
	for attempt in range(3):
		res = subprocess.run(args, capture_output=True, text=True)
		found = re.findall(r"rbxassetid://(\d+)", res.stdout)
		if found:
			print(name, found[-1], flush=True)
			return int(found[-1])
		print("retry", name, attempt, res.stderr[-200:], flush=True)
	return None


def main():
	state = json.load(open(STATE)) if os.path.exists(STATE) else {"Files": {}}
	files = [f for f in sorted(os.listdir(OUT)) if (f.startswith("Pack_") and f.endswith(".png")) or (f.startswith("RockPack") and f.endswith(".glb"))]
	todo = [f for f in files if state["Files"].get(f, {}).get("Hash") != digest(os.path.join(OUT, f))]
	print(len(files), "files,", len(todo), "to upload", flush=True)
	with ThreadPoolExecutor(4) as pool:
		for f, asset in zip(todo, pool.map(lambda f: upload(os.path.join(OUT, f)), todo)):
			if asset:
				state["Files"][f] = {"Id": asset, "Hash": digest(os.path.join(OUT, f))}
			else:
				print("FAILED", f, flush=True)
			json.dump(state, open(STATE, "w"), indent=1)
	kit = json.load(open(os.path.join(OUT, "kit.json")))
	state["Pieces"] = kit
	json.dump(state, open(STATE, "w"), indent=1)
	print("missing", [f for f in files if f not in state["Files"]], flush=True)


if __name__ == "__main__":
	main()
