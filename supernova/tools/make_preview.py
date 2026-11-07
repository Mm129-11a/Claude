"""Simula la supernova para ver cómo queda sin abrir el juego (video y tira de imágenes).

Uso:  python3 tools/make_preview.py
Crea preview.mp4 (960x540, horizontal) y preview.png (momentos clave) en la carpeta del addon.
Usa los mismos tiempos, tamaños y transparencias que las partículas y el script.
"""
import math
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"
W, H = 960, 540
FPS = 20
FOCAL = 685          # campo de visión de ~70° como el juego
DIST = 32            # distancia de la estrella
CX, CY = W // 2, 190  # donde se ve la estrella en pantalla

est = Image.open(TEX / "estrella.png").convert("RGBA")
exp = Image.open(TEX / "explosion.png").convert("RGBA")
fla = Image.open(TEX / "destello.png").convert("RGBA")
frame = lambda strip, i: strip.crop((0, i * 256, 256, (i + 1) * 256))
clamp = lambda v, a, b: max(a, min(b, v))

# Momentos (ticks) del script
T_DARK, T_EXP, T_FLASH, T_TIME, T_END = 10, 130, 150, 165, 240


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


rng = random.Random(4)
STARS = [(rng.uniform(0, W), rng.uniform(0, 360), rng.uniform(0.6, 2.2)) for _ in range(260)]


def background(tick):
    night = tick >= T_DARK and tick < T_TIME
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    horizon = 400
    if night:
        fog = (42, 13, 31) if tick < T_EXP else (107, 58, 110) if tick < T_FLASH else (255, 238, 248)
        top, bottom = (14, 6, 16), lerp((60, 22, 40), fog, 0.5)
        if tick >= T_FLASH:
            top, bottom = (250, 225, 240), (255, 240, 248)
    else:
        top, bottom = (90, 140, 230), (170, 205, 245)
        if tick >= T_TIME:
            top, bottom = lerp((250, 225, 240), top, clamp((tick - T_TIME) / 40, 0, 1)), \
                lerp((255, 240, 248), bottom, clamp((tick - T_TIME) / 40, 0, 1))
    for y in range(horizon):
        d.line([(0, y), (W, y)], fill=lerp(top, bottom, y / horizon))
    if night and tick < T_FLASH:
        for x, y, s in STARS:
            c = int(160 + 60 * math.sin(tick * 0.2 + x))
            d.ellipse([x - s / 2, y - s / 2, x + s / 2, y + s / 2], fill=(c, c - 20, c))
    ground = (200, 190, 90) if not night else (90, 80, 40) if tick < T_EXP else (150, 120, 100) \
        if tick < T_FLASH else (250, 240, 150)
    d.rectangle([0, horizon, W, H], fill=ground)
    for x in range(0, W, 24):
        d.line([(x, horizon), (CX + (x - CX) * 3, H)], fill=tuple(max(0, c - 18) for c in ground))
    return img


def paste(img, tex, radius_blocks, alpha, dx=0, dy=0, depth=DIST):
    r = int(radius_blocks * FOCAL / depth)
    if r < 2 or alpha <= 0:
        return
    t = tex.resize((2 * r, 2 * r), Image.BILINEAR)
    if alpha < 1:
        a = t.getchannel("A").point(lambda v: int(v * alpha))
        t.putalpha(a)
    img.paste(t, (CX - r + dx, CY - r + dy), t)


def render(tick):
    img = background(tick).convert("RGBA")
    shake = 0
    if 110 <= tick < 130:
        shake = 2
    elif 130 <= tick < 180:
        shake = 10 * (1 - (tick - 130) / 50)
    dx, dy = (int(rng.uniform(-shake, shake)), int(rng.uniform(-shake, shake))) if shake else (0, 0)
    # estrella (vive 6.6 s desde T_DARK)
    a = (tick - T_DARK) / FPS
    if 0 <= a <= 6.6:
        s = 3.2 * ((1 - (1 - clamp(a / 2.0, 0, 1)) ** 3) + clamp((a - 5.0) / 1.0, 0, 1) * 0.3
                   + math.sin(math.radians(a * 300)) * 0.03)
        paste(img, frame(est, int(a * 6) % 6), s, 1 - clamp((a - 6.1) / 0.5, 0, 1), dx, dy)
    # explosión
    a = (tick - T_EXP) / FPS
    if 0 <= a <= 3.2:
        s = 4.0 + 6.0 * (1 - (1 - clamp(a / 1.0, 0, 1)) ** 3) + a * 0.6
        paste(img, frame(exp, int(a * 12) % 6), s, 1 - clamp((a - 2.0) / 1.2, 0, 1), dx, dy, DIST - 1)
    # destello
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 4.5:
        s = 10 + 24 * (1 - (1 - clamp(a / 1.2, 0, 1)) ** 2)
        paste(img, fla, s, clamp(a / 0.2, 0, 1) * (1 - clamp((a - 1.8) / 2.5, 0, 1)), dx, dy, DIST + 3)
    # fundidos de cámara
    out = img.convert("RGB")
    fade = None
    if tick < 40:
        t = tick / FPS
        v = clamp(t / 0.5, 0, 1) if t < 0.5 else 1 if t < 0.8 else 1 - clamp((t - 0.8) / 1.2, 0, 1)
        fade = ((0, 0, 0), v)
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 0.75:
        v = clamp(a / 0.1, 0, 1) if a < 0.1 else 1 if a < 0.15 else 1 - clamp((a - 0.15) / 0.6, 0, 1)
        fade = ((255, 236, 248), v)
    if fade:
        out = Image.blend(out, Image.new("RGB", (W, H), fade[0]), fade[1])
    return out


def main():
    total = T_END + 30
    with tempfile.TemporaryDirectory() as tmp:
        for t in range(total):
            render(t).save(f"{tmp}/f{t:04d}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(ROOT / "preview.mp4")],
                       check=True)
    keys = [(60, "1. Nace la estrella y todo se oscurece"), (140, "2. Explota"),
            (172, "3. El destello")]
    strip = Image.new("RGB", (W // 2 * 3 + 40, H // 2 + 40), (245, 245, 245))
    d = ImageDraw.Draw(strip)
    for i, (t, label) in enumerate(keys):
        strip.paste(render(t).resize((W // 2, H // 2)), (10 + i * (W // 2 + 10), 30))
        d.text((10 + i * (W // 2 + 10), 10), label, fill=(20, 20, 20))
    strip.save(ROOT / "preview.png")
    print("preview.mp4 y preview.png ok")


if __name__ == "__main__":
    main()
