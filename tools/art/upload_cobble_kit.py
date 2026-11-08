"""Upload the chosen cobble kit set (docs/style/cobble-kit.md) and note the ids in art/kit/cobbles/roblox.json.

  python tools/art/upload_cobble_kit.py [--luau <out.luau>]

What goes up: CobbleKit.glb (the Chisel edging and the border stones, from `cobble_kit.py -- export Chisel,Sett`), the blue-grey
colour maps (ChiselSlate, its moss version, SettCool) and the paving tile. Only files that changed since last time are uploaded (a hash
per file), each with three tries. --luau writes tools/studio/cobble_kit.luau with the ids filled in, to run in Studio.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "art", "kit", "cobbles")
UPLOADER = r"C:\Users\blast\New folder\tools\roblox\upload_asset.py"
STATE = os.path.join(OUT, "roblox.json")
FILES = ["CobbleKit.glb", "Cobble_ChiselSlate_Color.png", "Cobble_ChiselSlate_Moss.png", "Cobble_SettCool_Color.png", "Paving_Color.png"]
# how each run chains: length along its +X, or a left turn (radius, degrees)
CHAIN = {
	"Straight8A": [8], "Straight8B": [8], "Row8A": [8], "Row8B": [8], "Row4": [4], "Row2": [2],
	"Curve6": [6, 45], "Curve12": [12, 30], "Curve24": [24, 15], "Corner": [2.5, 90], "Curve8": [8, 45], "Curve16": [16, 22.5], "Curve32": [32, 11.25],
}


def digest(path):
	return hashlib.sha1(open(path, "rb").read()).hexdigest()[:16]


def upload(path):
	name = os.path.splitext(os.path.basename(path))[0]
	args = [sys.executable, UPLOADER, path, "--name", name, "--description", "Gatebound cobble kit"]
	if path.endswith(".png"):
		args.append("--image")
	for attempt in range(3):
		res = subprocess.run(args, capture_output=True, text=True)
		found = re.findall(r"rbxassetid://(\d+)", res.stdout)
		if found:
			print(name, found[-1], flush=True)
			return int(found[-1])
		print("retry", name, attempt, res.stderr[-300:], flush=True)
	return None


def main():
	state = json.load(open(STATE)) if os.path.exists(STATE) else {"Files": {}}
	todo = [f for f in FILES if state["Files"].get(f, {}).get("Hash") != digest(os.path.join(OUT, f))]
	print(len(FILES), "files,", len(todo), "to upload", flush=True)
	with ThreadPoolExecutor(4) as pool:
		for f, asset in zip(todo, pool.map(lambda f: upload(os.path.join(OUT, f)), todo)):
			if asset:
				state["Files"][f] = {"Id": asset, "Hash": digest(os.path.join(OUT, f))}
			else:
				print("FAILED", f, flush=True)
			json.dump(state, open(STATE, "w"), indent=1)
	kit = json.load(open(os.path.join(OUT, "kit.json")))
	state["Pieces"] = {n: {"Style": m["Style"], "Box": m["Box"], "Chain": CHAIN.get(n.split("_", 1)[1])} for n, m in kit.items() if "Box" in m}
	json.dump(state, open(STATE, "w"), indent=1)
	missing = [f for f in FILES if f not in state["Files"]]
	print("missing", missing, flush=True)
	if "--luau" in sys.argv and not missing:
		out = sys.argv[sys.argv.index("--luau") + 1]
		body = open(os.path.join(ROOT, "tools", "studio", "cobble_kit.luau"), encoding="utf-8").read()
		data = {"Files": {k: v["Id"] for k, v in state["Files"].items()}, "Pieces": state["Pieces"]}
		open(out, "w", encoding="utf-8").write(body.replace("__DATA__", json.dumps(data, separators=(",", ":"))))
		print("wrote", out, flush=True)


if __name__ == "__main__":
	main()
