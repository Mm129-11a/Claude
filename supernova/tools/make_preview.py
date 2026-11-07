"""Simula la supernova para verla sin abrir el juego (video e imagen con los momentos clave).

Uso:  python3 tools/make_preview.py
Crea preview.mp4 (1288x586, apaisado como las capturas) y preview.png.
Usa las mismas texturas, piezas, tamaños, giros y tiempos que las partículas y el script.
"""
import json
import math
import random
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"
W, H = 1288, 586                  # misma proporción que las capturas (2576x1171)
FPS = 20
FOCAL = (H / 2) / math.tan(math.radians(30))   # campo de visión vertical de 60°
DIST, EYE, HEIGHT = 32, 1.62, 9
CX = W // 2
CY = int(H / 2 - FOCAL * (HEIGHT - EYE) / DIST)

# Momentos (ticks) del script
T_DARK, T_P0, T_P1, T_STAR, T_SHAKE, T_EXP, T_FLASH, T_TIME, T_END = 10, 14, 74, 96, 136, 160, 180, 195, 270
FLIGHT = (T_STAR - T_P1) / 20

est = Image.open(TEX / "estrella.png").convert("RGBA")
nuc = Image.open(TEX / "nucleo.png").convert("RGBA")
exp = Image.open(TEX / "explosion.png").convert("RGBA")
fla = Image.open(TEX / "destello.png").convert("RGBA")
atlas = Image.open(TEX / "piezas.png").convert("RGBA")
js = (ROOT / "SupernovaBP" / "scripts" / "piezas.js").read_text()
PIEZAS = json.loads(re.search(r"PIEZAS = (\[.*\]);", js).group(1))
STAR_HALF = float(re.search(r"STAR_HALF = ([0-9.]+)", js).group(1))
STAR_TEX = int(re.search(r"STAR_TEXTURE = (\d+)", js).group(1))
PX = 2 * STAR_HALF / STAR_TEX

clamp = lambda v, a, b: max(a, min(b, v))
ease = lambda a, t, p=3: 1 - (1 - clamp(a / t, 0, 1)) ** p

# Mismo reparto al azar que el script (dirección hacia afuera, distancia, profundidad y giro)
rng = random.Random(11)
FLY = []
for i, p in enumerate(PIEZAS):
    tick = T_P0 + round(i / max(1, len(PIEZAS) - 1) * (T_P1 - T_P0))
    ax, ay = p["x"], -p["y"]
    if math.hypot(ax, ay) < 1:
        a = rng.uniform(0, 2 * math.pi)
        ax, ay = math.cos(a), math.sin(a)
    ang = math.atan2(ay, ax) + (rng.random() - 0.5) * 0.9
    dist = 14 + rng.random() * 10
    FLY.append({"tick": tick, "ox": math.cos(ang) * dist, "oy": math.sin(ang) * dist,
                "oz": -6 + rng.random() * 14, "rot": rng.choice([-1, 1]) * (120 + rng.random() * 200),
                "life": (T_STAR - tick) / 20 + 0.3,
                "img": atlas.crop((p["u"], p["v"], p["u"] + p["w"], p["v"] + p["h"]))})

srng = random.Random(4)
STARS = [(srng.uniform(0, W), srng.uniform(0, 430), srng.uniform(0.8, 2.6)) for _ in range(320)]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def background(tick):
    night = T_DARK <= tick < T_TIME
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    horizon = 470
    if night:
        top, bottom = ((24, 10, 20), (70, 28, 48)) if tick < T_EXP else ((60, 40, 66), (110, 80, 112))
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


def put(img, tex, half_w, half_h, alpha, depth, x=0.0, y=0.0, angle=0.0, tint=None, shake=(0, 0)):
    """Partícula de half_w x half_h bloques (mitad de ancho y alto) a 'depth' bloques, desplazada
    (x, y) bloques en el plano que mira a la cámara."""
    rw, rh = half_w * FOCAL / depth, half_h * FOCAL / depth
    if rw < 1 or rh < 1 or alpha <= 0:
        return
    t = tex.resize((max(2, round(2 * rw)), max(2, round(2 * rh))), Image.BILINEAR)
    if tint:
        r, g, b, a = t.split()
        r, g, b = (ch.point(lambda v, k=k: int(v * k)) for ch, k in zip((r, g, b), tint))
        t = Image.merge("RGBA", (r, g, b, a))
    if angle:
        t = t.rotate(-angle, resample=Image.BILINEAR, expand=True)
    if alpha < 1:
        t.putalpha(t.getchannel("A").point(lambda v: int(v * alpha)))
    sx = CX + x * FOCAL / depth + shake[0]
    sy = CY - y * FOCAL / depth + shake[1]
    layer = Image.new("RGBA", img.size)
    layer.paste(t, (round(sx - t.width / 2), round(sy - t.height / 2)), t)
    img.alpha_composite(layer)


def render(tick):
    img = background(tick).convert("RGBA")
    sh = 2 if T_SHAKE <= tick < T_EXP else 12 * (1 - (tick - T_EXP) / 50) if T_EXP <= tick < T_EXP + 50 else 0
    shake = (int(srng.uniform(-sh, sh)), int(srng.uniform(-sh, sh))) if sh else (0, 0)
    # núcleo
    a = (tick - T_DARK) / FPS
    life = (T_STAR - T_DARK) / 20 + 0.3
    if 0 <= a <= life:
        s = STAR_HALF * 1.2 * (0.45 + 0.55 * clamp(a / (life - 0.3), 0, 1)) * (1 + 0.08 * math.sin(math.radians(a * 720)))
        put(img, nuc, s, s, clamp(a / 0.4, 0, 1) * (1 - clamp((a - life + 0.3) / 0.3, 0, 1)), DIST + 0.6, shake=shake)
    # piezas (las más lejanas primero)
    live = []
    for p, f in zip(PIEZAS, FLY):
        a = (tick - f["tick"]) / FPS
        if 0 <= a <= f["life"]:
            k = (1 - clamp(a / FLIGHT, 0, 1)) ** 3
            live.append((DIST + f["oz"] * k, p, f, a, k))
    for depth, p, f, a, k in sorted(live, key=lambda e: -e[0]):
        alpha = clamp(a / 0.12, 0, 1) * (1 - clamp((a - f["life"] + 0.15) / 0.15, 0, 1))
        tint = (0.5 + 0.5 * (1 - k), 0.45 + 0.55 * (1 - k), 0.4 + 0.6 * (1 - k))
        put(img, f["img"], p["w"] / 2 * PX, p["h"] / 2 * PX, alpha, max(2, depth),
            p["x"] * PX + f["ox"] * k, -p["y"] * PX + f["oy"] * k, f["rot"] * k, tint, shake)
    # estrella completa
    a = (tick - T_STAR) / FPS
    if 0 <= a <= 3.35:
        s = STAR_HALF * (1 + clamp((a - 2.2) / 1.0, 0, 1) * 0.3 + math.sin(math.radians(a * 300)) * 0.02)
        put(img, est, s, s, clamp(a / 0.12, 0, 1) * (1 - clamp((a - 3.2) / 0.12, 0, 1)), DIST, angle=5 * a, shake=shake)
    # explosión
    a = (tick - T_EXP) / FPS
    if 0 <= a <= 3.2:
        s = 17.1 * (0.3 + 0.7 * ease(a, 0.6)) + a * 0.4
        put(img, exp, s, s, 1 - clamp((a - 2.0) / 1.2, 0, 1), DIST - 1, angle=4 * a, shake=shake)
    # destello
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 4.0:
        s = 24.0 * (0.3 + 0.7 * ease(a, 0.35, 2))
        put(img, fla, s * 2.85, s, clamp(a / 0.15, 0, 1) * (1 - clamp((a - 1.6) / 2.4, 0, 1)), DIST + 3, shake=shake)
    out = img.convert("RGB")
    fade = None
    t = tick / FPS
    if t < 2.0:
        v = clamp(t / 0.5, 0, 1) if t < 0.5 else 1 if t < 0.8 else 1 - clamp((t - 0.8) / 1.2, 0, 1)
        fade = ((0, 0, 0), v)
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 0.75:
        v = clamp(a / 0.1, 0, 1) if a < 0.1 else 1 if a < 0.15 else 1 - clamp((a - 0.15) / 0.6, 0, 1)
        fade = ((255, 236, 248), v)
    if fade:
        out = Image.blend(out, Image.new("RGB", (W, H), fade[0]), fade[1])
    return out


KEYS = [(36, "1. Llegan las primeras piezas"), (62, "2. Se va formando"), (90, "3. Encajan las ultimas"),
        (112, "4. La estrella completa"), (166, "5. La explosion"), (186, "6. El destello")]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for t in range(T_END + 30):
            render(t).save(f"{tmp}/f{t:04d}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(ROOT / "preview.mp4")],
                       check=True)
    cw, ch = W // 2, H // 2
    sheet = Image.new("RGB", (3 * cw + 40, 2 * (ch + 30) + 10), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    for i, (t, label) in enumerate(KEYS):
        x = 10 + (i % 3) * (cw + 10)
        y = 30 + (i // 3) * (ch + 30)
        sheet.paste(render(t).resize((cw, ch)), (x, y))
        d.text((x, y - 20), label, fill=(20, 20, 20))
    sheet.save(ROOT / "preview.png")
    print("preview.mp4 y preview.png ok")


if __name__ == "__main__":
    main()
