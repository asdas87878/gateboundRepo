"""Uploads the pink cottage study's sheets and model (only what changed) and notes the ids in research/pink_cottage/roblox.json.
Private study: these uploads are for testing the look in Studio, not game assets.

  python tools/art/upload_pink_cottage.py

The Roblox key comes from ROBLOX_OPEN_CLOUD_KEY, read by the uploader.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "research", "pink_cottage")
UPLOADER = r"C:\Users\blast\New folder\tools\roblox\upload_asset.py"
STATE = os.path.join(OUT, "roblox.json")


def digest(path):
	return hashlib.sha1(open(path, "rb").read()).hexdigest()[:16]


def upload(path):
	name = "PinkCottage_" + os.path.splitext(os.path.basename(path))[0]
	args = [sys.executable, UPLOADER, path, "--name", name, "--description", "Private look study"]
	if path.endswith(".png"):
		args.append("--image")
	for attempt in range(3):
		res = subprocess.run(args, capture_output=True, text=True)
		found = re.findall(r"rbxassetid://(\d+)", res.stdout)
		if found:
			print(name, found[-1], flush=True)
			return int(found[-1])
		print("retry", name, attempt, (res.stdout + res.stderr)[-300:], flush=True)
	return None


def main():
	state = json.load(open(STATE)) if os.path.exists(STATE) else {"Files": {}}
	files = [os.path.join("sheets", f) for f in sorted(os.listdir(os.path.join(OUT, "sheets"))) if f.endswith(".png") and f != "ao_check.png"] + ["PinkCottage.glb"]
	todo = [f for f in files if state["Files"].get(f, {}).get("Hash") != digest(os.path.join(OUT, f))]
	print(len(files), "files,", len(todo), "to upload", flush=True)
	with ThreadPoolExecutor(4) as pool:
		for f, asset in zip(todo, pool.map(lambda f: upload(os.path.join(OUT, f)), todo)):
			if asset:
				state["Files"][f] = {"Id": asset, "Hash": digest(os.path.join(OUT, f))}
			else:
				print("FAILED", f, flush=True)
			json.dump(state, open(STATE, "w"), indent=1)
	missing = [f for f in files if f not in state["Files"]]
	print("missing", missing if missing else "none", flush=True)


if __name__ == "__main__":
	main()
