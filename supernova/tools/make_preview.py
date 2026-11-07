"""Simula la supernova para verla sin abrir el juego (video y comparación con las referencias).

Uso:  python3 tools/make_preview.py [bola.jpg explosion.jpg destello.jpg]
Crea preview.mp4 (1288x586, apaisado como las capturas) y preview.png. Si se le pasan las
imágenes de referencia, preview.png las pone encima de cada fase para compararlas.
Usa las mismas texturas, tamaños, giros y tiempos que las partículas y el script.
"""
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"
W, H = 1288, 586                  # misma proporción que las capturas (2576x1171)
FPS = 20
FOCAL = (H / 2) / math.tan(math.radians(30))   # campo de visión vertical de 60°
DIST = 32
EYE = 1.62
HEIGHT = 9
CX = W // 2
CY = int(H / 2 - FOCAL * (HEIGHT - EYE) / DIST)

est = Image.open(TEX / "estrella.png").convert("RGBA")
exp = Image.open(TEX / "explosion.png").convert("RGBA")
fla = Image.open(TEX / "destello.png").convert("RGBA")
clamp = lambda v, a, b: max(a, min(b, v))
ease = lambda a, t, p=3: 1 - (1 - clamp(a / t, 0, 1)) ** p

# Momentos (ticks) del script
T_DARK, T_EXP, T_FLASH, T_TIME, T_END = 10, 130, 150, 165, 240

rng = random.Random(4)
STARS = [(rng.uniform(0, W), rng.uniform(0, 430), rng.uniform(0.8, 2.6)) for _ in range(320)]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def background(tick):
    night = T_DARK <= tick < T_TIME
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    horizon = 470
    if night:
        top, bottom = (24, 10, 20), (70, 28, 48)
        if tick >= T_EXP:
            top, bottom = (60, 40, 66), (110, 80, 112)
    else:
        k = clamp((tick - T_TIME) / 40, 0, 1) if tick >= T_TIME else 1
        top, bottom = lerp((250, 225, 240), (90, 140, 230), k), lerp((255, 240, 248), (170, 205, 245), k)
    for y in range(horizon):
        d.line([(0, y), (W, y)], fill=lerp(top, bottom, y / horizon))
    if night:
        for x, y, s in STARS:
            c = int(170 + 50 * math.sin(tick * 0.2 + x))
            d.ellipse([x - s / 2, y - s / 2, x + s / 2, y + s / 2], fill=(c, c - 25, c - 10))
    ground = (205, 190, 70) if not night else (95, 85, 35) if tick < T_EXP else (150, 130, 80)
    d.rectangle([0, horizon, W, H], fill=ground)
    return img


def paste(img, tex, half_w, half_h, alpha, depth, angle=0.0, shake=(0, 0)):
    """Pone una partícula de half_w x half_h bloques (mitad de ancho y alto) a 'depth' bloques."""
    rw, rh = int(half_w * FOCAL / depth), int(half_h * FOCAL / depth)
    if rw < 2 or rh < 2 or alpha <= 0:
        return
    t = tex.resize((2 * rw, 2 * rh), Image.BILINEAR)
    if angle:
        t = t.rotate(-angle, resample=Image.BILINEAR, expand=False)
    if alpha < 1:
        t.putalpha(t.getchannel("A").point(lambda v: int(v * alpha)))
    layer = Image.new("RGBA", img.size)
    layer.paste(t, (CX - rw + shake[0], CY - rh + shake[1]), t)
    img.alpha_composite(layer)


def render(tick):
    img = background(tick).convert("RGBA")
    sh = 0
    if 110 <= tick < 130:
        sh = 2
    elif 130 <= tick < 180:
        sh = 12 * (1 - (tick - 130) / 50)
    shake = (int(rng.uniform(-sh, sh)), int(rng.uniform(-sh, sh))) if sh else (0, 0)
    a = (tick - T_DARK) / FPS                    # estrella
    if 0 <= a <= 6.6:
        s = 5.15 * (ease(a, 2.0) + clamp((a - 5.0) / 1.0, 0, 1) * 0.3 + math.sin(math.radians(a * 300)) * 0.02)
        paste(img, est, s, s, 1 - clamp((a - 6.1) / 0.5, 0, 1), DIST, 5 * a, shake)
    a = (tick - T_EXP) / FPS                     # explosión
    if 0 <= a <= 3.2:
        s = 17.1 * (0.3 + 0.7 * ease(a, 0.6)) + a * 0.4
        paste(img, exp, s, s, 1 - clamp((a - 2.0) / 1.2, 0, 1), DIST - 1, 4 * a, shake)
    a = (tick - T_FLASH) / FPS                   # destello
    if 0 <= a <= 4.0:
        s = 24.0 * (0.3 + 0.7 * ease(a, 0.35, 2))
        paste(img, fla, s * 2.85, s, clamp(a / 0.15, 0, 1) * (1 - clamp((a - 1.6) / 2.4, 0, 1)), DIST + 3,
              0, shake)
    out = img.convert("RGB")
    fade = None
    t = tick / FPS
    if t < 2.0:                                  # fundido a negro al empezar
        v = clamp(t / 0.5, 0, 1) if t < 0.5 else 1 if t < 0.8 else 1 - clamp((t - 0.8) / 1.2, 0, 1)
        fade = ((0, 0, 0), v)
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 0.75:                           # parpadeo del destello
        v = clamp(a / 0.1, 0, 1) if a < 0.1 else 1 if a < 0.15 else 1 - clamp((a - 0.15) / 0.6, 0, 1)
        fade = ((255, 236, 248), v)
    if fade:
        out = Image.blend(out, Image.new("RGB", (W, H), fade[0]), fade[1])
    return out


KEYS = [(80, "1. La estrella (bola de lava) y todo oscuro"), (142, "2. La explosion"), (160, "3. El destello")]


def main(refs):
    with tempfile.TemporaryDirectory() as tmp:
        for t in range(T_END + 30):
            render(t).save(f"{tmp}/f{t:04d}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(ROOT / "preview.mp4")],
                       check=True)
    cw, ch = W // 2, H // 2
    rows = 2 if refs else 1
    sheet = Image.new("RGB", (3 * cw + 40, rows * (ch + 30) + 10), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    for i, (t, label) in enumerate(KEYS):
        x = 10 + i * (cw + 10)
        if refs:
            ref = Image.open(refs[i]).convert("RGB")
            ref.thumbnail((cw, ch))
            box = Image.new("RGB", (cw, ch), (20, 16, 30))
            box.paste(ref, ((cw - ref.width) // 2, (ch - ref.height) // 2))
            sheet.paste(box, (x, 30))
            d.text((x, 10), "Referencia: " + label[3:], fill=(20, 20, 20))
        y = 30 + (ch + 30 if refs else 0)
        sheet.paste(render(t).resize((cw, ch)), (x, y))
        d.text((x, y - 20), "Addon: " + label, fill=(20, 20, 20))
    sheet.save(ROOT / "preview.png")
    print("preview.mp4 y preview.png ok")


if __name__ == "__main__":
    main(sys.argv[1:4] if len(sys.argv) == 4 else None)
