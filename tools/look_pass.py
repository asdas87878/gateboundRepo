"""Run one look pass (docs/look-passes.md): build + render the copy in Blender, post it, compare with the reference,
log the score.

  python tools/look_pass.py <spec.json> <pass name> [--post] [--quick] [--note "what changed"]

--post   reuse the pass folder's beauty/depth and redo only the post + comparison (haze/bloom/grade tuning)
Output in art/look/<ref>/passes/<name>/: beauty.png, depth.png, final.png, sheet.jpg, stats.json, placements.json, spec.json
"""

import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
import look_compare  # noqa: E402
import look_post  # noqa: E402


def main():
	a = sys.argv[1:]
	spec_path, name = os.path.abspath(a[0]), a[1]
	note = a[a.index("--note") + 1] if "--note" in a else ""
	ref_dir = os.path.dirname(spec_path)
	out = os.path.join(ref_dir, "passes", name)
	os.makedirs(out, exist_ok=True)
	spec = json.load(open(spec_path, encoding="utf-8"))
	shutil.copy(spec_path, os.path.join(out, "spec.json"))
	t0 = time.time()
	if "--post" not in a:
		cmd = [BLENDER, "--background", "--python", os.path.join(ROOT, "tools", "blender", "look_match.py"), "--", spec_path, out]
		if "--quick" in a:
			cmd.append("--quick")
		if "--save" in a:
			cmd.append("--save")
		res = subprocess.run(cmd, capture_output=True, text=True)
		lines = [ln for ln in res.stdout.splitlines() if ln.startswith("[look") or "Error" in ln or "Traceback" in ln]
		print("\n".join(lines))
		if res.returncode != 0 or not os.path.exists(os.path.join(out, "beauty.png")):
			print(res.stdout[-4000:], res.stderr[-4000:])
			sys.exit(1)
	look_post.post(out, spec)
	ref = os.path.join(ref_dir, "frame.png")
	areas = os.path.join(ref_dir, "areas.json")
	R, F, rows, score, layout, d, mask, aspec, scale = look_compare.compare(os.path.join(out, "final.png"), ref, areas)
	look_compare.sheet(R, F, rows, score, layout, d, mask, aspec, scale, os.path.join(out, "sheet.jpg"), name)
	json.dump({"score": score, "layout": layout, "areas": rows}, open(os.path.join(out, "stats.json"), "w"), indent=1)
	for r in rows:
		print(f"  {r['area']:14s} L ref {r['ref']['L']:5.1f} ours {r['ours']['L']:5.1f}   dE(ab) {r['dab']:5.1f}   "
			  f"ref a,b ({r['ref']['a']:5.1f},{r['ref']['b']:5.1f}) ours ({r['ours']['a']:5.1f},{r['ours']['b']:5.1f})")
	print(f"{name}: score {score:.2f}  layout {layout:.2f}  ({time.time() - t0:.0f} s)")
	with open(os.path.join(ref_dir, "passes", "log.md"), "a", encoding="utf-8") as f:
		f.write(f"| {name} | {score:.2f} | {layout:.2f} | {note} |\n")


if __name__ == "__main__":
	main()
