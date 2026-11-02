"""Per-area numbers for one or more passes against the reference (L, a, b), compact.

  python tools/art/pass_table.py <pass dir> [<pass dir> ...]
"""

import json
import os
import sys


def main():
	dirs = sys.argv[1:]
	stats = [json.load(open(os.path.join(d, "stats.json"))) for d in dirs]
	names = [os.path.basename(os.path.normpath(d)) for d in dirs]
	print(f"{'area':14s} {'ref L/a/b':>18s} " + " ".join(f"{n:>22s}" for n in names))
	for i, r in enumerate(stats[0]["areas"]):
		a = r["ref"]
		row = f"{r['area']:14s} {a['L']:5.1f} {a['a']:5.1f} {a['b']:5.1f}  "
		for s in stats:
			o = s["areas"][i]["ours"]
			err = abs(s["areas"][i]["dL"]) + s["areas"][i]["dab"]
			row += f"  {o['L']:5.1f} {o['a']:5.1f} {o['b']:5.1f} ({err:4.1f})"
		print(row)
	print(f"{'score':14s} {'':18s} " + " ".join(f"{s['score']:>22.2f}" for s in stats))


if __name__ == "__main__":
	main()
