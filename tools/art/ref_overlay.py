"""Lines a render up against its reference: a 50/50 blend, and the reference's edges drawn in red over the render.

  python tools/art/ref_overlay.py <render.png> <reference.png> <out.jpg> [--side]

--side also puts the two side by side (the render resized to the reference's height).
"""

import sys

import numpy as np
from PIL import Image, ImageFilter


def main():
	render_path, ref_path, out_path = sys.argv[1:4]
	ref = Image.open(ref_path).convert("RGB")
	ren = Image.open(render_path).convert("RGB").resize(ref.size, Image.LANCZOS)
	blend = Image.blend(ref, ren, 0.5)
	edges = np.asarray(ref.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
	edges = np.clip((edges - 28) / 40, 0, 1)[..., None]
	lined = np.asarray(ren, dtype=np.float32) * (1 - edges) + np.array((255, 30, 30), dtype=np.float32) * edges
	tiles = [blend, Image.fromarray(lined.astype(np.uint8))]
	if "--side" in sys.argv:
		tiles = [ref, ren] + tiles
	w, h = ref.size
	sheet = Image.new("RGB", (w * len(tiles), h), "white")
	for i, t in enumerate(tiles):
		sheet.paste(t, (i * w, 0))
	sheet.thumbnail((2400, 2400))
	sheet.save(out_path, quality=90)


if __name__ == "__main__":
	main()
