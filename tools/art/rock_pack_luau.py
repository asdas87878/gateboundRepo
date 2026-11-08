"""Fill tools/studio/rock_pack.luau with the ids from art/kit/rock_pack/roblox.json. Prints the path of the filled copy, to run in Studio.

  python tools/art/rock_pack_luau.py <out.luau>
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
state = json.load(open(os.path.join(ROOT, "art", "kit", "rock_pack", "roblox.json")))
data = {"Files": {k: {"Id": v["Id"]} for k, v in state["Files"].items()}, "Pieces": state["Pieces"]}
source = open(os.path.join(ROOT, "tools", "studio", "rock_pack.luau"), encoding="utf-8").read()
assert "__DATA__" in source
open(sys.argv[1], "w", encoding="utf-8").write(source.replace("__DATA__", json.dumps(data, separators=(",", ":"))))
print(sys.argv[1])
