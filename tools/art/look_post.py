"""Post for a look pass (docs/look-passes.md): haze from depth, bloom and a colour grade, in that order, on a pass's
beauty.png + depth.png. Each step stands for a Roblox Lighting effect so the numbers carry over: Haze ~ Atmosphere,
Bloom ~ BloomEffect, Grade ~ ColorCorrectionEffect (Brightness, Contrast, Saturation, TintColor).

  python tools/art/look_post.py <pass_dir> <spec.json>      -> <pass_dir>/final.png
"""

import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def hex_rgb(h):
	return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def to_lin(c):
	return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(c):
	c = np.clip(c, 0, None)
	return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055).astype(np.float32)


def lum(c):
	return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def view_dirs(meta, W, H):
	cam = meta["Camera"]
	FW, FH = cam["Frame"]
	f = cam["F"] * W / FW
	cy = cam.get("Cy", FH / 2) * H / FH
	fwd, right, up = (np.array(cam[k], np.float32) for k in ("Fwd", "Right", "Up"))
	xs = (np.arange(W, dtype=np.float32) + 0.5) - W / 2
	ys = cy - (np.arange(H, dtype=np.float32) + 0.5)
	d = fwd[None, None] * f + right[None, None] * xs[None, :, None] + up[None, None] * ys[:, None, None]
	return d / np.linalg.norm(d, axis=-1, keepdims=True)


def post(pass_dir, spec):
	meta = json.load(open(os.path.join(pass_dir, "placements.json"), encoding="utf-8"))["Meta"]
	beauty = np.asarray(Image.open(os.path.join(pass_dir, "beauty.png")), np.float32)
	beauty = beauty / (65535.0 if beauty.max() > 255 else 255.0)
	lin = to_lin(beauty[..., :3])
	H, W = lin.shape[:2]
	p = spec.get("Post", {})
	dpath = os.path.join(pass_dir, "depth.png")
	hz = p.get("Haze")
	if hz and os.path.exists(dpath):
		dep = np.asarray(Image.open(dpath), np.float32)
		dep = dep / (65535.0 if dep.max() > 255 else 255.0)
		if dep.ndim == 3:
			dep = dep[..., 0]
		if dep.shape != (H, W):
			dep = np.asarray(Image.fromarray(dep).resize((W, H), Image.NEAREST))
		sky = dep > 0.999
		dist = dep * meta["DepthRange"]
		dirs = view_dirs(meta, W, H)
		sd = np.array(meta["SkySunDir"], np.float32)
		cosang = np.clip(dirs @ sd, -1, 1)
		# Power 1 = plain exponential fog; Power 2 keeps the middle distance clear and still buries the mountains
		f = 1 - np.exp(-((hz["Density"] * np.maximum(0.0, dist - hz.get("Start", 0.0))) ** hz.get("Power", 1.0)))
		f = np.minimum(f, hz.get("Max", 1.0)) * (~sky)
		# haze colour: base, a glow toward the painted sun, and a lighter band low over the horizon
		glow = np.clip(cosang, 0, 1) ** hz.get("GlowPower", 8.0) * hz.get("Glow", 0.0)
		hc = to_lin(hex_rgb(hz["Colour"]))[None, None] * (1 - glow[..., None]) + to_lin(hex_rgb(hz.get("GlowColour", hz["Colour"])))[None, None] * glow[..., None]
		# far haze can be lighter than near (Roblox Atmosphere's Haze lightens toward the horizon)
		if "FarColour" in hz:
			t = np.clip((dist - hz["Start"]) / max(1.0, hz.get("FarAt", 1500.0) - hz["Start"]), 0, 1)[..., None]
			hc = hc * (1 - t) + to_lin(hex_rgb(hz["FarColour"]))[None, None] * t
		lin = lin * (1 - f[..., None]) + hc * f[..., None]
	bl = p.get("Bloom")
	if bl:
		L = lum(lin)
		bright = lin * (np.clip(L - bl["Threshold"], 0, None) / np.maximum(L, 1e-4))[..., None]
		acc = np.zeros_like(lin)
		for sigma, w in bl.get("Layers", [[6, 0.5], [24, 0.35], [70, 0.15]]):
			s = sigma * W / 1336
			acc += np.stack([gaussian_filter(bright[..., c], s) for c in range(3)], -1) * w
		lin = lin + acc * bl["Intensity"]
	g = p.get("Grade", {})
	s = to_srgb(lin)
	if "Tint" in g:
		s = s * hex_rgb(g["Tint"])[None, None]
	if "Brightness" in g or "Contrast" in g:
		s = (s - 0.5) * (1 + g.get("Contrast", 0.0)) + 0.5 + g.get("Brightness", 0.0)
	if "Saturation" in g:
		y = lum(s)[..., None]
		s = y + (s - y) * (1 + g["Saturation"])
	if "Lift" in g:  # not a Roblox effect: kept only to measure how much the shadows need lifting
		s = s + (1 - s) * g["Lift"]
	vg = p.get("Vignette")
	if vg:
		yy, xx = np.mgrid[0:H, 0:W]
		r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
		s = s * (1 - vg * np.clip(r - 0.6, 0, None) ** 2)[..., None]
	s = s + (np.random.RandomState(0).rand(*s.shape).astype(np.float32) - 0.5) / 255
	out = (np.clip(s, 0, 1) * 255 + 0.5).astype(np.uint8)
	Image.fromarray(out).save(os.path.join(pass_dir, "final.png"))


if __name__ == "__main__":
	post(sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8")))
