"""Study reference footage (docs/style/botw-study.md): sample frames from clips, contact sheets, and the numbers of a
look: value and colour per horizontal band, sky colours, how colour fades with height in the frame (distance), the
palette, and how shadowed greens differ from sunlit ones.

  python tools/art/frame_study.py extract <clips dir> <frames dir> [--every 4]
  python tools/art/frame_study.py sheets <frames dir> <out dir>
  python tools/art/frame_study.py stats <frames dir> <out.json> [--pick <list.txt>]

Footage and frames stay in research/ (gitignored): study material only. Only numbers and our own writing go in the repo.
"""

import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def lab(rgb):
	c = rgb / 255.0
	c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
	x = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
	x = x / np.array([0.9505, 1.0, 1.089])
	f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
	return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_hex(L, a, b):
	fy = (L + 16) / 116
	fx, fz = fy + a / 500, fy - b / 200
	inv = lambda t: t**3 if t**3 > 0.008856 else (t - 16 / 116) / 7.787
	X = np.array([inv(fx), inv(fy), inv(fz)]) * np.array([0.9505, 1.0, 1.089])
	M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
	lin = np.linalg.solve(M, X)
	s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
	return "".join(f"{int(round(float(np.clip(v, 0, 1)) * 255)):02x}" for v in s)


def extract(clips, frames, every):
	os.makedirs(frames, exist_ok=True)
	n = 0
	for path in sorted(glob.glob(os.path.join(clips, "*.mp4"))):
		cap = cv2.VideoCapture(path)
		fps = cap.get(cv2.CAP_PROP_FPS) or 30
		total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
		name = os.path.splitext(os.path.basename(path))[0]
		if glob.glob(os.path.join(frames, name + "_*.jpg")):  # already extracted
			cap.release()
			continue
		for f in range(int(fps * 2), total, int(fps * every)):
			cap.set(cv2.CAP_PROP_POS_FRAMES, f)
			ok, img = cap.read()
			if not ok:
				continue
			if img.mean() < 25:  # black/loading frames
				continue
			cv2.imwrite(os.path.join(frames, f"{name}_{int(f / fps):04d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
			n += 1
		cap.release()
	print("frames:", n)


def sheets(frames, out):
	os.makedirs(out, exist_ok=True)
	files = sorted(glob.glob(os.path.join(frames, "*.jpg")))
	font = ImageFont.truetype("arial.ttf", 14)
	per, cols, tw, th = 30, 6, 320, 180
	for s in range(0, len(files), per):
		chunk = files[s : s + per]
		sheet = Image.new("RGB", (cols * tw, ((len(chunk) + cols - 1) // cols) * th), (0, 0, 0))
		d = ImageDraw.Draw(sheet)
		for k, f in enumerate(chunk):
			im = Image.open(f).convert("RGB").resize((tw, th))
			x, y = (k % cols) * tw, (k // cols) * th
			sheet.paste(im, (x, y))
			d.rectangle((x, y, x + 120, y + 17), fill=(0, 0, 0))
			d.text((x + 3, y + 1), os.path.basename(f)[:-4], font=font, fill=(255, 255, 0))
		sheet.save(os.path.join(out, f"sheet_{s // per:02d}.jpg"), quality=85)
	print("sheets:", (len(files) + per - 1) // per)


def stats(frames, out, pick=None):
	files = sorted(glob.glob(os.path.join(frames, "*.jpg")))
	if pick:
		keep = {ln.strip() for ln in open(pick, encoding="utf-8") if ln.strip() and not ln.startswith("#")}
		files = [f for f in files if os.path.basename(f)[:-4] in keep]
	bands = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
	band_acc = [[] for _ in bands]
	sky, green_lit, green_shade, allpix = [], [], [], []
	for f in files:
		im = np.asarray(Image.open(f).convert("RGB").resize((320, 180)), np.float64)
		L = lab(im)
		h = L.shape[0]
		for k, (a, b) in enumerate(bands):
			p = L[int(a * h) : int(b * h)].reshape(-1, 3)
			band_acc[k].append([p[:, 0].mean(), p[:, 0].std(), np.hypot(p[:, 1], p[:, 2]).mean(), p[:, 1].mean(), p[:, 2].mean()])
		top = L[: int(0.3 * h)].reshape(-1, 3)
		s = top[(top[:, 0] > 55) & (top[:, 2] < 2)]  # bright and blue-ish: sky
		if len(s) > 200:
			sky.append(np.percentile(s, [10, 50, 90], axis=0))
		px = L.reshape(-1, 3)
		g = px[(px[:, 1] < -6) & (px[:, 2] > 8)]  # greens (grass, leaves)
		if len(g) > 300:
			med = np.median(g[:, 0])
			green_lit.append(g[g[:, 0] > med + 8].mean(0) if (g[:, 0] > med + 8).sum() > 30 else g.mean(0))
			green_shade.append(g[g[:, 0] < med - 8].mean(0) if (g[:, 0] < med - 8).sum() > 30 else g.mean(0))
		allpix.append(px[np.random.RandomState(0).choice(len(px), 600, replace=False)])
	res = {"frames": len(files), "bands": []}
	for (a, b), acc in zip(bands, band_acc):
		m = np.mean(acc, 0)
		res["bands"].append({"rows": f"{int(a * 100)}-{int(b * 100)}%", "L": round(m[0], 1), "spread": round(m[1], 1), "chroma": round(m[2], 1),
							 "a": round(m[3], 1), "b": round(m[4], 1)})
	if sky:
		sk = np.mean(sky, 0)
		res["sky"] = {q: {"Lab": [round(v, 1) for v in sk[i]], "hex": lab_to_hex(*sk[i])} for i, q in enumerate(("p10", "p50", "p90"))}
	if green_lit:
		gl, gs = np.mean(green_lit, 0), np.mean(green_shade, 0)
		res["greens"] = {"lit": {"Lab": [round(v, 1) for v in gl], "hex": lab_to_hex(*gl)},
						 "shade": {"Lab": [round(v, 1) for v in gs], "hex": lab_to_hex(*gs)},
						 "shade_shift_ab": [round(gs[1] - gl[1], 1), round(gs[2] - gl[2], 1)]}
	P = np.concatenate(allpix)
	# palette: k-means in Lab
	crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
	_, labels, centres = cv2.kmeans(P.astype(np.float32), 14, None, crit, 4, cv2.KMEANS_PP_CENTERS)
	counts = np.bincount(labels.ravel(), minlength=14) / len(labels)
	order = np.argsort(centres[:, 0])
	res["palette"] = [{"hex": lab_to_hex(*centres[i]), "Lab": [round(float(v), 1) for v in centres[i]], "share": round(float(counts[i]), 3)} for i in order]
	json.dump(res, open(out, "w"), indent=1)
	# swatch strip
	sw = Image.new("RGB", (14 * 80, 110), (255, 255, 255))
	d = ImageDraw.Draw(sw)
	font = ImageFont.truetype("arial.ttf", 13)
	for k, p in enumerate(res["palette"]):
		d.rectangle((k * 80, 0, k * 80 + 79, 80), fill="#" + p["hex"])
		d.text((k * 80 + 4, 84), p["hex"], font=font, fill=(0, 0, 0))
		d.text((k * 80 + 4, 96), f"{p['share'] * 100:.0f}%", font=font, fill=(0, 0, 0))
	sw.save(out.replace(".json", "_palette.png"))
	print(json.dumps({k: v for k, v in res.items() if k != "palette"}, indent=1))


if __name__ == "__main__":
	a = sys.argv[1:]
	if a[0] == "extract":
		extract(a[1], a[2], float(a[a.index("--every") + 1]) if "--every" in a else 4.0)
	elif a[0] == "sheets":
		sheets(a[1], a[2])
	elif a[0] == "stats":
		stats(a[1], a[2], a[a.index("--pick") + 1] if "--pick" in a else None)
