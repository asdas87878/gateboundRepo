"""Uploads the stone sword's sheets and model, only what changed, and notes the ids in art/kit/sword/roblox.json:

  python tools/art/upload_sword.py
  python tools/art/upload_sword.py --luau <out.luau>     also writes the placement script with the ids filled in (tools/studio/place_sword.luau)

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
OUT = os.path.join(ROOT, "art", "kit", "sword")
UPLOADER = r"C:\Users\blast\New folder\tools\roblox\upload_asset.py"
STATE = os.path.join(OUT, "roblox.json")


def digest(path):
	return hashlib.sha1(open(path, "rb").read()).hexdigest()[:16]


def upload(path):
	name = os.path.splitext(os.path.basename(path))[0]
	args = [sys.executable, UPLOADER, path, "--name", name, "--description", "Gatebound stone sword"]
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
	files = [f for f in sorted(os.listdir(OUT)) if (f.startswith("Sword_") and f.endswith(".png")) or f == "StoneSword.glb"]
	todo = [f for f in files if state["Files"].get(f, {}).get("Hash") != digest(os.path.join(OUT, f))]
	print(len(files), "files,", len(todo), "to upload", flush=True)
	with ThreadPoolExecutor(4) as pool:
		for f, asset in zip(todo, pool.map(lambda f: upload(os.path.join(OUT, f)), todo)):
			if asset:
				state["Files"][f] = {"Id": asset, "Hash": digest(os.path.join(OUT, f))}
			else:
				print("FAILED", f, flush=True)
			json.dump(state, open(STATE, "w"), indent=1)
	state["Bounds"] = json.load(open(os.path.join(OUT, "bounds.json")))
	state["Layout"] = json.load(open(os.path.join(OUT, "layout.json")))["Params"]
	json.dump(state, open(STATE, "w"), indent=1)
	missing = [f for f in files if f not in state["Files"]]
	if missing:
		print("missing", missing, flush=True)
	if "--luau" in sys.argv:
		out = sys.argv[sys.argv.index("--luau") + 1]
		body = open(os.path.join(ROOT, "tools", "studio", "place_sword.luau"), encoding="utf-8").read()
		data = {"Files": {k: v["Id"] for k, v in state["Files"].items()}, "Bounds": state["Bounds"], "Layout": state["Layout"]}
		open(out, "w", encoding="utf-8").write(body.replace("__DATA__", json.dumps(data)))
		print("wrote", out, flush=True)


if __name__ == "__main__":
	main()
