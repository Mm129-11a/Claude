"""Genera las texturas de las partículas de la supernova.

Uso:  python3 tools/make_textures.py
Necesita: numpy, pillow, scipy

Crea en SupernovaRP/textures/particle/supernova/:
  estrella.png   6 fotogramas de 256x256 (superficie de fuego que hierve y llamas alrededor)
  explosion.png  6 fotogramas de 256x256 (núcleo blanco, rayos morados, borde rosa)
  destello.png   256x256 (resplandor blanco con borde rosa)
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter, map_coordinates

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"
OUT.mkdir(parents=True, exist_ok=True)
N = 256
FRAMES = 6

yy, xx = np.mgrid[0:N, 0:N]
X = (xx + 0.5) / N * 2 - 1
Y = (yy + 0.5) / N * 2 - 1
R = np.hypot(X, Y)
TH = np.arctan2(Y, X)


def fractal(rng, scales=(32, 16, 8, 4, 2), weights=(1, .6, .4, .25, .15), shape=(N, N), wrap=False):
    f = np.zeros(shape)
    for s, w in zip(scales, weights):
        f += w * gaussian_filter(rng.standard_normal(shape), s, mode="wrap" if wrap else "reflect")
    f -= f.min()
    return f / f.max()


def ramp(v, stops):
    v = np.clip(v, 0, 1)
    out = np.zeros(v.shape + (3,))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (v >= a) & (v <= b)
        t = ((v - a) / (b - a))[m][:, None]
        out[m] = np.array(ca) * (1 - t) + np.array(cb) * t
    return out


def to_img(rgb, a):
    arr = np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def strip(frames):
    s = Image.new("RGBA", (N, N * len(frames)))
    for i, f in enumerate(frames):
        s.paste(f, (0, i * N))
    return s


# ------------------------------------------------------------------ estrella
def estrella():
    rng = np.random.default_rng(3)
    A, B = fractal(rng), fractal(rng)
    WA, WB = fractal(rng, (24, 12)), fractal(rng, (24, 12))
    # llamas: ruido en coordenadas polares, alargado hacia afuera
    PA = fractal(rng, (3, 1.5), (1, .5), shape=(64, 512), wrap=True)
    PB = fractal(rng, (3, 1.5), (1, .5), shape=(64, 512), wrap=True)
    PA = gaussian_filter(PA, (6, 0.8), mode="wrap")
    PB = gaussian_filter(PB, (6, 0.8), mode="wrap")
    disk = 0.70
    frames = []
    for k in range(FRAMES):
        a = 2 * math.pi * k / FRAMES
        ca, sa = math.cos(a), math.sin(a)
        warp = (ca * WA + sa * WB - 0.5) * 40
        F = ca * A + sa * B
        F = (F - F.min()) / (F.max() - F.min())
        F = map_coordinates(F, [yy + warp, xx - warp], order=1, mode="reflect")
        # superficie: más clara en el centro, vetas naranjas
        rr = np.clip(R / disk, 0, 1)
        v = 0.55 * F + 0.45 * (1 - rr ** 2) + 0.14
        v = v ** 1.15
        surf = ramp(v, [(0, (150, 30, 5)), (0.3, (225, 80, 12)), (0.5, (250, 140, 30)),
                        (0.7, (255, 200, 80)), (0.88, (255, 236, 160)), (1, (255, 250, 225))])
        # borde del disco más rojizo y brillante
        limb = np.clip((rr - 0.82) / 0.18, 0, 1)
        surf = surf * (1 - 0.35 * limb[..., None]) + np.array([255, 120, 30]) * 0.35 * limb[..., None]
        # llamas alrededor
        P = ca * PA + sa * PB
        P = (P - P.min()) / (P.max() - P.min())
        pr = np.clip((R - disk) / (1 - disk), 0, 1)
        flame = map_coordinates(P, [pr * 63, (TH + math.pi) / (2 * math.pi) * 511], order=1, mode="wrap")
        corona_a = np.clip(flame * 1.6 - pr * 1.25, 0, 1) * (R > disk - 0.02)
        glow = np.exp(-((R - disk) / 0.07) ** 2) * 0.9
        corona_a = np.clip(np.maximum(corona_a, glow * (R >= disk)), 0, 1) * (R < 0.995)
        corona = ramp(1 - pr, [(0, (200, 40, 5)), (0.5, (245, 110, 25)), (1, (255, 190, 80))])
        inside = R < disk
        edge = np.clip((disk - R) / 0.015, 0, 1)        # borde suave del disco
        rgb = np.where(inside[..., None], surf, corona)
        alpha = np.where(inside, np.maximum(edge, corona_a), corona_a)
        rgb = rgb * (alpha[..., None] > 0) + (alpha[..., None] == 0) * np.array([255, 120, 30])
        frames.append(to_img(rgb, alpha))
    strip(frames).save(OUT / "estrella.png")
    return frames


# ------------------------------------------------------------------ explosión
def bolt_layer(seed):
    rng = random.Random(seed)
    S = N * 2
    img = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(img)
    c = S / 2

    def branch(x, y, ang, length, width, depth):
        steps = max(3, int(length / 10))
        for _ in range(steps):
            ang += rng.uniform(-0.6, 0.6)
            nx = x + math.cos(ang) * length / steps
            ny = y + math.sin(ang) * length / steps
            d.line([(x, y), (nx, ny)], fill=255, width=max(1, int(width)))
            if depth < 2 and rng.random() < 0.22:
                branch(nx, ny, ang + rng.choice([-1, 1]) * rng.uniform(0.4, 0.9),
                       length * rng.uniform(0.3, 0.5), width * 0.6, depth + 1)
            x, y = nx, ny
            width *= 0.93

    for i in range(18):
        a = rng.uniform(0, 2 * math.pi)
        # más rayos hacia arriba, como en la foto
        if rng.random() < 0.4:
            a = -math.pi / 2 + rng.uniform(-0.9, 0.9)
        r0 = rng.uniform(0.02, 0.12) * S / 2
        branch(c + math.cos(a) * r0, c + math.sin(a) * r0, a, rng.uniform(0.35, 0.7) * S / 2, 8, 0)
    return np.array(img.resize((N, N), Image.LANCZOS)).astype(float) / 255


def explosion():
    rng = np.random.default_rng(9)
    rays_base = fractal(rng, (2, 1), (1, .5), shape=(32, 360), wrap=True)
    rays_base = gaussian_filter(rays_base, (8, 1), mode="wrap")
    blobs = fractal(rng, (10, 5), (1, .5))
    frames = []
    for k in range(FRAMES):
        rays = map_coordinates(rays_base, [np.clip(R, 0, 1) * 31, ((TH + math.pi) / (2 * math.pi) * 359 + k * 7) % 360],
                               order=1, mode="wrap")
        # base: blanco brillante hasta 0.55, lavanda, luego rosa en el borde
        base = ramp(R, [(0, (255, 255, 255)), (0.45, (252, 248, 255)), (0.68, (240, 225, 250)),
                        (0.82, (255, 170, 215)), (0.93, (255, 95, 160)), (1.0, (240, 60, 130))])
        alpha = np.clip((1.0 - R) / 0.12, 0, 1) ** 1.2
        # manchas celestes y lavanda
        tint = np.clip((blobs - 0.55) * 3, 0, 1) * np.clip(1 - np.abs(R - 0.4) / 0.35, 0, 1)
        base = base * (1 - 0.55 * tint[..., None]) + np.array([150, 205, 245]) * 0.55 * tint[..., None]
        # rayos radiales lavanda
        rmask = np.clip((rays - 0.55) * 3, 0, 1) * np.clip(1 - np.abs(R - 0.45) / 0.35, 0, 1)
        base = base * (1 - 0.45 * rmask[..., None]) + np.array([185, 150, 245]) * 0.45 * rmask[..., None]
        # relámpagos morados con brillo
        b = bolt_layer(100 + k)
        glow = gaussian_filter(b, 4)
        glow = np.clip(glow / max(glow.max(), 1e-6) * 1.6, 0, 1)
        fade = np.clip(1 - (R - 0.6) / 0.3, 0, 1)
        purple = np.array([135, 80, 230])
        base = base * (1 - (0.9 * glow * fade)[..., None]) + purple * (0.9 * glow * fade)[..., None]
        core = np.clip(b * 1.5, 0, 1) * fade
        base = base * (1 - (0.75 * core)[..., None]) + np.array([200, 175, 255]) * (0.75 * core)[..., None]
        # núcleo blanco puro
        hot = np.clip(1 - R / 0.18, 0, 1) ** 1.5
        base = base * (1 - hot[..., None]) + 255 * hot[..., None]
        frames.append(to_img(base, alpha))
    strip(frames).save(OUT / "explosion.png")
    return frames


# ------------------------------------------------------------------ destello
def destello():
    rgb = ramp(R, [(0, (255, 255, 255)), (0.5, (255, 252, 254)), (0.7, (255, 220, 240)),
                   (0.84, (255, 120, 195)), (1.0, (235, 70, 170))])
    alpha = np.clip((1 - R) / 0.25, 0, 1) ** 0.8
    # rayas de luz horizontales
    streak = np.exp(-((Y - 0.18) / 0.012) ** 2) * np.clip(1 - np.abs(X) / 1.0, 0, 1) * 0.8
    streak += np.exp(-((Y + 0.32) / 0.008) ** 2) * np.clip(1 - np.abs(X + 0.2) / 0.9, 0, 1) * 0.5
    alpha = np.clip(alpha + streak * (R < 1), 0, 1)
    rgb = rgb * (1 - streak[..., None] * 0.5) + 255 * streak[..., None] * 0.5
    img = to_img(rgb, alpha)
    img.save(OUT / "destello.png")
    return img


if __name__ == "__main__":
    estrella()
    explosion()
    destello()
    print("ok:", OUT)
