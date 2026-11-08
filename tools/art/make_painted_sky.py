"""Paints a crisp daytime sky (copied from the FPS project's tool): zenith to pale horizon, painted cumulus built
from shaded puffs, wispy cirrus strokes.

  python tools/art/make_painted_sky.py [--seed N] [--preset ClearDay|SaltCove]   -> art/style/sky/<preset>/
      equirect.png (8192 x 4096, for Blender worlds), Sky{Ft,Bk,Lf,Rt,Up,Dn}.png (1024, Roblox's orientation)

Why the old sky looked soft: its clouds were painted at half resolution and its 2048-wide equirect gave each
1024 cube face only 512 source pixels (2x upsampling). Here everything is painted at 8192 wide (22.8 px per degree),
so each 90-degree face samples 2048 source pixels down to 1024.

Cumulus: each cloud is a dome filled with puffs (big in the body, small round the rim) whose sphere caps make one
height field, smoothed so lumps merge; the light off its slope is snapped to four painted tones with anti-aliased
band edges. The base is cut flat and darkened, as real fair-weather cumulus are. Cirrus: bundles of broad tapered
brush arcs. Faces are cut at 2048 and Lanczos-reduced to Roblox's 1024 cap (sharper than cutting at 1024).
"""

import argparse
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art", "style", "sky", "ClearDay")
W, H = 8192, 4096
PPD = W / 360.0  # pixels per degree
CLOUD_SMOOTH = 0.09  # share of a cloud's height: merges lumps; low values leave blotches inside the cloud
CLOUD_SOFT = 0.14  # half width of the blend between cloud tones
CLOUD_FEATHER = 14.0  # pixels of soft cloud edge at 8192 wide

SKY = {
    "Zenith": (34, 92, 206),
    "Mid": (70, 138, 226),
    "Horizon": (182, 214, 240),
    "Haze": (226, 232, 236),
    "Sun": (35.0, 52.0),  # azimuth (from north through east), elevation: the key light's direction
    "Tones": [(150, 168, 206), (192, 206, 232), (230, 238, 248), (255, 255, 255)],  # cumulus shadow -> lit
    "Base": (128, 146, 190),  # the flat, darker cloud bases
}


# Roblox's face orientation, checked in Studio; from the FPS project's tools/art/make_sky.py
def cube_faces(eq, size=1024):
    """Roblox Sky faces from the equirect, in Roblox's own orientation (checked in Studio 2026-10-19: SkyboxFt looks
    north (-Z), Bk south, SkyboxLf EAST (+X) and SkyboxRt west, SkyboxUp a quarter turn counter-clockwise; Dn
    unchecked: it's under the ground everywhere you can stand)"""
    h, w = eq.shape[:2]
    a = (np.arange(size) + 0.5) / size * 2 - 1
    X, Y = np.meshgrid(a, -a)  # image right, image up
    faces = {
        "Ft": (X, Y, -np.ones_like(X)),  # looking -Z: right = +X
        "Bk": (-X, Y, np.ones_like(X)),  # looking +Z: right = -X
        "Rt": (np.ones_like(X), Y, X),  # looking +X: right = +Z
        "Lf": (-np.ones_like(X), Y, -X),  # looking -X: right = -Z
        "Up": (X, np.ones_like(X), Y),  # looking up: image up = -Z... set below
        "Dn": (X, -np.ones_like(X), -Y),
    }
    out = {}
    for name, (dx, dy, dz) in faces.items():
        n = np.sqrt(dx * dx + dy * dy + dz * dz)
        dx, dy, dz = dx / n, dy / n, dz / n
        az = np.arctan2(dx, -dz)
        el = np.arcsin(np.clip(dy, -1, 1))
        u = (az + np.pi) / (2 * np.pi) * (w - 1)
        v = (np.pi / 2 - el) / np.pi * (h - 1)
        face = np.stack([ndimage.map_coordinates(eq[..., c], [v, u], order=1, mode="wrap") for c in range(3)], -1)
        out[name] = face
    out["Lf"], out["Rt"] = out["Rt"], out["Lf"]  # Roblox's Lf is the east face
    out["Up"] = np.rot90(out["Up"], 1)  # a quarter turn counter-clockwise (read off a labelled test sky in Studio)
    out["Dn"] = out["Dn"][::-1, ::-1]
    return out


def col(c):
    return np.array(c, np.float32) / 255.0


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def gradient():
    el = (0.5 - (np.arange(H) + 0.5) / H) * 180.0  # degrees, +90 at the top row
    t = np.clip(el / 90.0, 0, 1) ** 0.55
    sky = np.where(t[:, None] < 0.35, 0, 1)  # (computed per row below)
    rows = np.zeros((H, 3), np.float32)
    for i, (e, tt) in enumerate(zip(el, t)):
        if e < 0:
            rows[i] = col(SKY["Horizon"]) * 0.92  # below the horizon: never seen over the map, keep it calm
        elif tt < 0.35:
            rows[i] = col(SKY["Horizon"]) + (col(SKY["Mid"]) - col(SKY["Horizon"])) * smoothstep(0, 0.35, tt)
        else:
            rows[i] = col(SKY["Mid"]) + (col(SKY["Zenith"]) - col(SKY["Mid"])) * smoothstep(0.35, 1.0, tt)
    del sky
    img = np.repeat(rows[:, None, :], W, axis=1)
    # a pale haze hugging the horizon, a little warmer under the sun
    haze = np.exp(-np.clip(el, 0, None) / 4.0)[:, None] * 0.55
    az = (np.arange(W) + 0.5) / W * 360.0 - 180.0
    sun_az = SKY["Sun"][0]
    near = np.exp(-(((az - sun_az + 180) % 360 - 180) / 60.0) ** 2)[None, :]
    hz = col(SKY["Haze"]) * (1 - 0.3 * near[..., None]) + col((248, 236, 214)) * 0.3 * near[..., None]
    img = img * (1 - haze[..., None]) + hz * haze[..., None]
    return img


def px(az, el):
    """equirect pixel (x, y) of an azimuth/elevation in degrees"""
    return (az + 180.0) / 360.0 * W, (90.0 - el) / 180.0 * H


def cumulus(img, rng, az, el, width, height):
    """one painted cumulus, width/height in degrees, its flat base at elevation el. The puffs build one height field
    (the union of their sphere caps), smoothed a little so neighbouring lumps merge like real cauliflower tops; the
    light comes off that field's slope, snapped to the painted tones."""
    from scipy import ndimage

    squash = 1.0 / max(math.cos(math.radians(el + height / 2)), 0.3)  # equirect stretch: drawn wider up high
    x0, y0 = px(az - width * squash * 0.62, el + height * 1.15)
    x1, y1 = px(az + width * squash * 0.62, el - 0.4)
    x0, x1, y0, y1 = int(x0), int(x1) + 1, max(int(y0), 0), min(int(y1) + 1, H)
    xs, ys = np.arange(x0, x1), np.arange(y0, y1)
    X, Y = np.meshgrid(xs, ys)
    du = ((X + 0.5) / W * 360.0 - 180.0 - az) / squash  # degrees across (stretch undone)
    dv = (90.0 - (Y + 0.5) / H * 180.0) - el  # degrees up from the base
    field = np.zeros(X.shape, np.float32)
    # a dome profile, filled with puffs: big ones in the body, a crowd of small ones on the rim (the cauliflower edge)
    count = int(18 + width * 2.2)
    for k in range(count):
        u = rng.uniform(-0.5, 0.5)
        top = height * max(0.0, 1 - (2 * u) ** 2) ** 0.6 * rng.uniform(0.75, 1.0)
        rim = k > count * 0.45
        r = (rng.uniform(0.08, 0.16) if rim else rng.uniform(0.18, 0.32)) * height
        v = top - r * 0.9 if rim else rng.uniform(0.25, 0.7) * top
        cu = u * width
        d2 = (du - cu) ** 2 + (dv - v) ** 2
        cap = np.sqrt(np.clip(r * r - d2, 0, None)) + (v * 0.35)
        field = np.maximum(field, np.where(d2 < r * r, cap, 0))
    field = np.where(dv > 0.12, field, 0)  # a flat base
    mask = field > 0
    if not mask.any():
        return
    smooth = ndimage.gaussian_filter(field, height * PPD * CLOUD_SMOOTH)
    gy, gx = np.gradient(smooth)
    gx, gy = gx * PPD, -gy * PPD  # per degree, y up
    nz = 1.0 / np.sqrt(1 + gx * gx + gy * gy)
    nx, ny = -gx * nz, -gy * nz
    L = np.array([0.5, 0.62, 0.6])
    L /= np.linalg.norm(L)
    light = nx * L[0] + ny * L[1] + nz * L[2]
    light = light * 0.85 + 0.3 * np.clip(dv / height, 0, 1) - 0.1
    tones = [col(t) for t in SKY["Tones"]]
    out = np.broadcast_to(tones[0], X.shape + (3,)).copy()
    for c, t in zip((0.18, 0.45, 0.7), tones[1:]):
        k = smoothstep(c - CLOUD_SOFT, c + CLOUD_SOFT, light)[..., None]
        out = out * (1 - k) + t * k
    base = smoothstep(height * 0.16, 0.0, dv)[..., None] * 0.6  # darker flat underside
    out = out * (1 - base) + col(SKY["Base"]) * base
    # an anti-aliased edge from the union's outline
    edge = ndimage.distance_transform_edt(mask) - ndimage.distance_transform_edt(~mask)
    alpha = ndimage.gaussian_filter(np.clip(edge / CLOUD_FEATHER + 0.5, 0, 1), CLOUD_FEATHER * 0.3)[..., None]
    xi = np.mod(xs, W)
    region = img[y0:y1][:, xi]
    img[y0:y1, xi] = region * (1 - alpha) + out * alpha


def cirrus(img, rng, count):
    """wispy high cloud as broad brush strokes: bundles of long tapered arcs, drawn anti-aliased with PIL at twice
    the size of the band they sit in, softened a touch across their width"""
    from PIL import ImageDraw, ImageFilter

    top, bottom = px(0, 66)[1], px(0, 18)[1]
    band_h = int(bottom - top)
    S = 2
    layer = Image.new("L", (W * S, band_h * S), 0)
    draw = ImageDraw.Draw(layer)
    for _ in range(count):
        az = rng.uniform(-180, 180)
        el = rng.uniform(24, 60)
        ang = math.radians(rng.uniform(-20, 20) + 12)
        squash = 1.0 / max(math.cos(math.radians(el)), 0.3)
        length = rng.uniform(14, 40)
        for b in range(int(rng.integers(4, 10))):
            off = rng.normal(0, 1.2)
            l = length * rng.uniform(0.45, 1.0)
            bend = rng.uniform(-0.025, 0.025)
            width = rng.uniform(2.0, 7.0) * S
            shade = int(rng.uniform(90, 200))
            pts = []
            for s in range(24):
                t = s / 23
                u = (t - 0.5) * l
                v = off + bend * u * u
                a_ = az + (u * math.cos(ang) - v * math.sin(ang)) * squash
                e_ = el + u * math.sin(ang) + v * math.cos(ang)
                x, y = px(a_, e_)
                pts.append((x * S, (y - top) * S, math.sin(math.pi * t) ** 0.8))
            for (xa, ya, ta), (xb, yb, tb) in zip(pts, pts[1:]):
                w = max(1, int(width * (ta + tb) / 2))
                draw.line([(xa % (W * S), ya), (xa % (W * S) + (xb - xa), yb)], fill=int(shade * (ta + tb) / 2), width=w)
    layer = layer.filter(ImageFilter.GaussianBlur(S * 1.2)).resize((W, band_h), Image.LANCZOS)
    a = np.asarray(layer, np.float32)[..., None] / 255.0 * 0.75
    y0 = int(top)
    img[y0 : y0 + band_h] = img[y0 : y0 + band_h] * (1 - a) + col((250, 252, 255)) * a


PRESETS = {
    # the Stylized Environment Lesson's sky: bright cyan over a pale horizon (measured from its frames, top about 36, 195, 240),
    # white cumulus with cyan shadows; Roblox draws its own sun, so no disc here
    "Lesson": {"Cirrus": 8, "Banks": (18, 36, (2, 9), (18, 40), (9, 18)), "Towers": 7, "SunDisc": False,
               "Zenith": (26, 150, 228), "Mid": (52, 190, 236), "Horizon": (170, 232, 240), "Haze": (222, 244, 244),
               "Sun": (35.0, 52.0), "Tones": [(186, 226, 240), (214, 238, 247), (240, 249, 252), (255, 255, 255)],
               "Base": (168, 216, 234)},
    # the first look test: banks of big cumulus, cirrus
    "ClearDay": {"Cirrus": 18, "Banks": (16, 34, (2, 9), (18, 40), (9, 18)), "Towers": 9, "SunDisc": False},
    # Salt Cove (the user's concept paintings): a clear deep blue over a pale horizon, a bright sun disc with a soft
    # glow, a few small flat clouds low down, no cirrus
    "SaltCove": {"Cirrus": 0, "Banks": (30, 60, (2, 7), (12, 24), (4, 8)), "Towers": 0, "SunDisc": True,
                 "Zenith": (52, 108, 206), "Mid": (92, 150, 222), "Horizon": (196, 214, 236), "Haze": (226, 230, 238),
                 "Sun": (40.0, 38.0), "Tones": [(170, 186, 214), (206, 216, 236), (234, 240, 250), (255, 255, 255)],
                 "Base": (150, 168, 204)},
    # the Fyrestone study (Borderlands 2's Arid Badlands): a pale hazy sky, cream at the horizon, a few warm clouds
    "Badlands": {"Cirrus": 10, "Banks": (40, 80, (2, 8), (14, 26), (4, 8)), "Towers": 0, "SunDisc": True,
                 "Zenith": (104, 150, 200), "Mid": (160, 190, 214), "Horizon": (236, 222, 196), "Haze": (242, 228, 204),
                 "Sun": (215.0, 40.0), "Tones": [(196, 176, 158), (220, 206, 190), (240, 232, 220), (255, 250, 242)],
                 "Base": (176, 160, 150)},
}


def sun_disc(img):
    """the sun: a hard bright disc (2.2 degrees) with a soft wide glow"""
    az, el = SKY["Sun"]
    ys = (90.0 - (np.arange(H) + 0.5) / H * 180.0)[:, None]
    xs = ((np.arange(W) + 0.5) / W * 360.0 - 180.0)[None, :]
    a1, e1 = np.radians(xs), np.radians(ys)
    a0, e0 = np.radians(az), np.radians(el)
    cosd = np.sin(e1) * np.sin(e0) + np.cos(e1) * np.cos(e0) * np.cos(a1 - a0)
    d = np.degrees(np.arccos(np.clip(cosd, -1, 1)))
    glow = np.exp(-(d / 9.0) ** 2) * 0.35 + np.exp(-(d / 2.8) ** 2) * 0.4
    disc = smoothstep(2.3, 2.0, d)
    img[:] = img + (1 - img) * glow[..., None] * np.array([1.0, 0.98, 0.92])
    img[:] = img * (1 - disc[..., None]) + np.array([1.0, 1.0, 0.97]) * disc[..., None]


def main(seed, preset="ClearDay"):
    global OUT
    cfg = PRESETS[preset]
    for k in ("Zenith", "Mid", "Horizon", "Haze", "Sun", "Tones", "Base"):
        if k in cfg:
            SKY[k] = cfg[k]
    OUT = os.path.join(ROOT, "art", "style", "sky", preset)
    rng = np.random.default_rng(seed)
    img = gradient()
    if cfg["SunDisc"]:
        sun_disc(img)
    if cfg["Cirrus"]:
        cirrus(img, rng, cfg["Cirrus"])
    # banks of cumulus round the horizon, big ones low; a few smaller ones higher up
    clouds = []
    gap0, gap1, el, width, height = cfg["Banks"]
    az = -180.0
    while az < 180:
        az += rng.uniform(gap0, gap1)
        clouds.append((az, rng.uniform(*el), rng.uniform(*width), rng.uniform(*height)))
    for _ in range(cfg["Towers"]):  # towers standing higher up, where a camera tilted up over walls still sees them
        clouds.append((rng.uniform(-180, 180), rng.uniform(14, 30), rng.uniform(10, 20), rng.uniform(5, 10)))
    clouds.sort(key=lambda c: -c[1])  # high (far) first, low (near) over them
    for c in clouds:
        cumulus(img, rng, *c)
    os.makedirs(OUT, exist_ok=True)
    # a +-1/255 dither so the gradient never bands
    eq = np.clip(img + (rng.random(img.shape[:2])[..., None] - 0.5) / 255.0, 0, 1)
    Image.fromarray((eq * 255).astype(np.uint8)).save(os.path.join(OUT, "equirect.png"))
    for name, face in cube_faces(eq, 2048).items():  # cut at 2048, then Lanczos down to Roblox's 1024 cap
        img_face = Image.fromarray((np.clip(face, 0, 1) * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS)
        img_face.save(os.path.join(OUT, f"Sky{name}.png"))
    print(f"[painted sky] {os.path.relpath(OUT, ROOT)}: equirect {W}x{H}, faces 1024 (from 2048)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--preset", default="Lesson", choices=sorted(PRESETS))
    a = p.parse_args()
    main(a.seed, a.preset)
