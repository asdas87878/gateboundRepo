"""Upload the flower kit (tools/blender/flower_kit.py, docs/style/flower-beds.md) and note the ids in art/kit/flowers/roblox.json.

  python tools/art/upload_flower_kit.py [--luau <out.luau>]

Only changed files go up (a hash per file), three tries each. --luau fills tools/studio/flower_kit.luau with the ids, to run in Studio.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upload_cobble_kit as up  # noqa: E402  (digest, upload)

ROOT = up.ROOT
OUT = os.path.join(ROOT, "art", "kit", "flowers")
STATE = os.path.join(OUT, "roblox.json")
FILES = ["FlowerKit.glb", "FlowerMound_Color.png", "FlowerCards_White.png", "FlowerCards_Pink.png", "FlowerCards_Mixed.png"]


def main():
	state = json.load(open(STATE)) if os.path.exists(STATE) else {"Files": {}}
	todo = [f for f in FILES if state["Files"].get(f, {}).get("Hash") != up.digest(os.path.join(OUT, f))]
	print(len(FILES), "files,", len(todo), "to upload", flush=True)
	for f in todo:
		asset = up.upload(os.path.join(OUT, f))
		if asset:
			state["Files"][f] = {"Id": asset, "Hash": up.digest(os.path.join(OUT, f))}
		else:
			print("FAILED", f, flush=True)
		json.dump(state, open(STATE, "w"), indent=1)
	kit = json.load(open(os.path.join(OUT, "kit.json")))
	state["Pieces"] = {n: {p: v["Box"] for p, v in m["Parts"].items()} for n, m in kit.items()}
	json.dump(state, open(STATE, "w"), indent=1)
	missing = [f for f in FILES if f not in state["Files"]]
	print("missing", missing, flush=True)
	if "--luau" in sys.argv and not missing:
		out = sys.argv[sys.argv.index("--luau") + 1]
		body = open(os.path.join(ROOT, "tools", "studio", "flower_kit.luau"), encoding="utf-8").read()
		data = {"Files": {k: v["Id"] for k, v in state["Files"].items()}, "Pieces": state["Pieces"]}
		open(out, "w", encoding="utf-8").write(body.replace("__DATA__", json.dumps(data, separators=(",", ":"))))
		print("wrote", out, flush=True)


if __name__ == "__main__":
	main()
