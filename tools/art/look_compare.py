"""Compare a render with the reference frame (docs/look-passes.md).

  python tools/art/look_compare.py <render.png> [--ref art/look/ashen_ref/frame.png] [--areas art/look/ashen_ref/areas.json]
                                   [--out <sheet.jpg>] [--json <stats.json>]

Both images are taken as the same camera, so a box covers the same thing in both. Per area: CIELAB lightness (mean,
p10, p90), chroma, and the colour difference (dE = distance in a,b plus |dL|). The global score is the mean over areas
of |dL| + dE(ab) (0 = identical colours), plus a blurred whole-frame difference outside the HUD mask (layout + colour).
The sheet: reference over render, an onion skin (50/50) and a per-area table.
"""

import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def lab(rgb):
	c = rgb / 255.0
	c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
	x = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
	x = x / np.array([0.9505, 1.0, 1.089])
	f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
	return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def area_stats(im_lab, box, scale):
	x0, y0, x1, y1 = (int(round(v * s)) for v, s in zip(box, (scale[0], scale[1], scale[0], scale[1])))
	p = im_lab[y0:y1, x0:x1].reshape(-1, 3)
	L, a, b = p[:, 0], p[:, 1], p[:, 2]
	return {"L": float(L.mean()), "p10": float(np.percentile(L, 10)), "p90": float(np.percentile(L, 90)),
			"a": float(a.mean()), "b": float(b.mean()), "C": float(np.hypot(a, b).mean())}


def compare(render, ref, areas_file):
	spec = json.load(open(areas_file, encoding="utf-8"))
	fw, fh = spec["Frame"]
	R = Image.open(render).convert("RGB")
	F = Image.open(ref).convert("RGB")
	if R.size != F.size:
		R = R.resize(F.size, Image.LANCZOS)
	scale = (F.size[0] / fw, F.size[1] / fh)
	rl, fl = lab(np.asarray(R, np.float64)), lab(np.asarray(F, np.float64))
	rows = []
	for name, box in spec["Areas"].items():
		s_ref, s_ren = area_stats(fl, box, scale), area_stats(rl, box, scale)
		dab = float(np.hypot(s_ref["a"] - s_ren["a"], s_ref["b"] - s_ren["b"]))
		rows.append({"area": name, "ref": s_ref, "ours": s_ren, "dL": s_ren["L"] - s_ref["L"], "dab": dab})
	# layout + colour: blur both (detail doesn't count), compare outside the HUD mask
	mask = np.ones((F.size[1], F.size[0]), bool)
	for x0, y0, x1, y1 in spec.get("Mask", []):
		mask[int(y0 * scale[1]):int(y1 * scale[1]), int(x0 * scale[0]):int(x1 * scale[0])] = False
	blur = lambda im: lab(np.asarray(im.filter(ImageFilter.GaussianBlur(6 * scale[0])), np.float64))
	d = np.linalg.norm(blur(R) - blur(F), axis=-1)
	layout = float(d[mask].mean())
	score = float(np.mean([abs(r["dL"]) + r["dab"] for r in rows]))
	return R, F, rows, score, layout, d, mask, spec, scale


def sheet(R, F, rows, score, layout, d, mask, spec, scale, out, title=""):
	W, H = F.size
	table_h = 26 * (len(rows) + 3)
	S = Image.new("RGB", (W * 2, H * 2 + table_h), (24, 24, 28))
	S.paste(F, (0, 0))
	S.paste(R, (W, 0))
	S.paste(Image.blend(F, R, 0.5), (0, H))
	heat = np.clip(d / 30.0, 0, 1)
	heat_img = np.zeros((H, W, 3), np.uint8)
	heat_img[..., 0] = (heat * 255).astype(np.uint8)
	heat_img[..., 1] = ((1 - heat) * 120).astype(np.uint8)
	heat_img[~mask] = (40, 40, 40)
	S.paste(Image.fromarray(heat_img), (W, H))
	dr = ImageDraw.Draw(S)
	font = ImageFont.truetype("arialbd.ttf", 20)
	small = ImageFont.truetype("consola.ttf", 17)
	for (x, y), t in (((0, 0), "Reference"), ((W, 0), f"Ours {title}"), ((0, H), "Onion skin 50/50"),
					  ((W, H), f"Blurred difference (red = far off): layout {layout:.1f}")):
		bx = dr.textbbox((x + 12, y + 8), t, font=font)
		dr.rectangle((bx[0] - 6, bx[1] - 4, bx[2] + 6, bx[3] + 4), fill=(20, 20, 24))
		dr.text((x + 12, y + 8), t, font=font, fill="white")
	for name, box in spec["Areas"].items():
		x0, y0, x1, y1 = box[0] * scale[0], box[1] * scale[1], box[2] * scale[0], box[3] * scale[1]
		for ox in (0, W):
			dr.rectangle((x0 + ox, y0, x1 + ox, y1), outline=(255, 255, 255), width=1)
			dr.text((x0 + ox + 2, y0 + 1), name, font=ImageFont.truetype("arial.ttf", 11), fill="white")
	y = H * 2 + 8
	dr.text((12, y), f"{'area':14s} {'L ref/ours':>12s} {'p10-p90 ref':>12s} {'ours':>9s} {'chroma ref/ours':>16s} {'dE(ab)':>7s}   "
			f"score {score:.1f} (mean |dL|+dE over areas, 0 = same)   layout {layout:.1f}", font=small, fill="white")
	for k, r in enumerate(rows):
		a, b = r["ref"], r["ours"]
		dl = r["dL"]
		col = (120, 220, 120) if abs(dl) + r["dab"] < 6 else (240, 200, 90) if abs(dl) + r["dab"] < 14 else (240, 110, 100)
		dr.text((12, y + 26 * (k + 1)), f"{r['area']:14s} {a['L']:5.0f} / {b['L']:<5.0f} {a['p10']:5.0f}-{a['p90']:<5.0f} "
				f"{b['p10']:4.0f}-{b['p90']:<4.0f} {a['C']:7.0f} / {b['C']:<7.0f} {r['dab']:7.1f}   "
				f"{'lighter' if dl > 0 else 'darker'} by {abs(dl):.0f}", font=small, fill=col)
	S.save(out, quality=90)


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	render = a[0]
	ref = opt("--ref", "art/look/ashen_ref/frame.png")
	areas = opt("--areas", "art/look/ashen_ref/areas.json")
	R, F, rows, score, layout, d, mask, spec, scale = compare(render, ref, areas)
	for r in rows:
		print(f"{r['area']:14s} L {r['ref']['L']:5.1f} / {r['ours']['L']:5.1f}  C {r['ref']['C']:5.1f} / {r['ours']['C']:5.1f}"
			  f"  a,b ref ({r['ref']['a']:5.1f},{r['ref']['b']:5.1f}) ours ({r['ours']['a']:5.1f},{r['ours']['b']:5.1f})  dE {r['dab']:4.1f}")
	print(f"score {score:.2f}  layout {layout:.2f}")
	if "--out" in a:
		sheet(R, F, rows, score, layout, d, mask, spec, scale, opt("--out", None), opt("--title", ""))
	if "--json" in a:
		json.dump({"score": score, "layout": layout, "areas": rows}, open(opt("--json", None), "w"), indent=1)


if __name__ == "__main__":
	main()
