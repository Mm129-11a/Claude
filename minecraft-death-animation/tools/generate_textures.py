"""Genera las texturas de la animación de muerte (pixel art original).

Uso:  python3 tools/generate_textures.py
Crea en DeathAnimation_RP/textures/ui/death_anim/:
  emblem.png     tira vertical de 48 fotogramas de 80x80 (criatura que flota y se desintegra)
  lightning.png  tira vertical de 8 fotogramas de 160x90 (rayos blancos a pantalla completa)
  white.png      cuadrado blanco para el destello de color
Y una vista previa preview.gif en la carpeta del addon.
"""
import colorsys
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "DeathAnimation_RP" / "textures" / "ui" / "death_anim"
OUT.mkdir(parents=True, exist_ok=True)

EMBLEM_FPS = 10
EMBLEM_FRAMES = 48          # 4,8 s
EMBLEM_SIZE = 80            # 80 x 48 = 3840 px de alto (cabe en 4096)
LIGHTNING_FPS = 12
LIGHTNING_FRAMES = 8
LW, LH = 160, 90

# Paleta carnosa
OUTLINE = (64, 10, 14)
DARK = (138, 28, 34)
MID = (200, 68, 62)
BASE = (234, 108, 92)
LIGHT = (250, 158, 136)
SHINE = (255, 206, 186)
PURPLE = (170, 80, 200)
PINK = (240, 100, 170)
BEARD = (190, 64, 56)
BEARD_L = (236, 128, 108)
CLAW = (96, 20, 24)


def rainbow(h, s=0.9, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def tentacle(d, root, tip, bend, width, rng_phase):
    """Tentáculo curvo que se va afinando y termina en una garra."""
    pts = []
    for i in range(13):
        t = i / 12
        # curva cuadrática con un punto de control desplazado
        cx = (root[0] + tip[0]) / 2 + bend[0]
        cy = (root[1] + tip[1]) / 2 + bend[1]
        x = (1 - t) ** 2 * root[0] + 2 * (1 - t) * t * cx + t * t * tip[0]
        y = (1 - t) ** 2 * root[1] + 2 * (1 - t) * t * cy + t * t * tip[1]
        x += math.sin(t * 6 + rng_phase) * 1.2 * t
        pts.append((x, y))
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        w = max(2, round(width * (1 - i / 14)))
        d.line([a, b], fill=MID, width=w + 2)
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        w = max(1, round(width * (1 - i / 14)) - 1)
        d.line([a, b], fill=BASE if i % 3 else LIGHT, width=w)
    tx, ty = pts[-1]
    d.ellipse([tx - 3, ty - 2, tx + 3, ty + 3], fill=CLAW)
    d.point([(tx - 1, ty - 1)], fill=MID)
    # garras
    d.line([(tx - 3, ty + 2), (tx - 5, ty + 5)], fill=CLAW, width=1)
    d.line([(tx + 3, ty + 2), (tx + 5, ty + 5)], fill=CLAW, width=1)


def creature(f, mode="normal"):
    """Dibuja la criatura (80x80) para el fotograma f."""
    img = Image.new("RGBA", (EMBLEM_SIZE, EMBLEM_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = 40
    wig = math.sin(f * 0.7)

    # --- tentáculos (detrás), gruesos y abiertos hacia los lados ---
    tentacle(d, (24, 48), (6, 64 + wig), (-6, 9), 9, f * 0.7)
    tentacle(d, (33, 56), (22, 74 - wig), (-3, 6), 8, f * 0.7 + 1)
    tentacle(d, (47, 56), (58, 74 + wig), (3, 6), 8, f * 0.7 + 2)
    tentacle(d, (56, 48), (74, 64 - wig), (6, 9), 9, f * 0.7 + 3)

    # --- placas laterales redondeadas (hombros) ---
    for side in (-1, 1):
        xa, xb = (7, 17) if side < 0 else (63, 73)
        d.rounded_rectangle([xa, 15, xb, 46], radius=3, fill=MID)
        for y in range(17, 45, 3):
            d.line([(xa + 1, y), (xb - 1, y)], fill=LIGHT)
            d.line([(xa + 1, y + 1), (xb - 1, y + 1)], fill=DARK)
        edge = xb if side > 0 else xa
        for y in range(19, 44, 5):
            d.line([(edge, y), (edge, y + 1)], fill=PURPLE)
            d.point([(edge - side, y + 2)], fill=PINK)

    # --- barba / mandíbula ancha por bloques ---
    beard = [(19, 40), (61, 40), (58, 52), (49, 63), (40, 72), (31, 63), (22, 52)]
    d.polygon(beard, fill=BEARD)
    for x in range(21, 60, 3):
        bottom = 70 - abs(x - cx) * 1.0
        d.line([(x, 41), (x, bottom)], fill=BEARD_L)
        d.line([(x + 1, 43), (x + 1, bottom - 2)], fill=DARK)
    for y, half in ((48, 16), (56, 11), (63, 6)):
        d.line([(cx - half, y), (cx + half, y)], fill=DARK)
    d.polygon([(34, 41), (46, 41), (44, 46), (36, 46)], fill=OUTLINE)

    # --- cabeza: cúpula ancha con costillas ---
    head = [(14, 18), (21, 9), (31, 4), (49, 4), (59, 9), (66, 18), (66, 33), (60, 42), (20, 42), (14, 33)]
    d.polygon(head, fill=BASE)
    for i, x in enumerate(range(18, 64, 4)):
        top = 6 + abs(x - cx) * 0.18
        col = LIGHT if i % 2 else MID
        d.line([(x, top), (x - (x - cx) * 0.08, 27)], fill=col, width=2)
    d.polygon([(21, 9), (31, 4), (34, 9), (24, 14)], fill=SHINE)
    d.polygon([(59, 9), (49, 4), (46, 9), (56, 14)], fill=MID)
    d.line([(14, 33), (20, 42)], fill=DARK, width=2)
    d.line([(66, 33), (60, 42)], fill=DARK, width=2)

    # --- franja roja con los ojos brillantes ---
    glow = 0.75 + 0.25 * math.sin(f * 0.9)
    eye = (255, int(40 * glow), int(30 * glow))
    core = (255, int(210 * glow), int(150 * glow))
    d.rounded_rectangle([19, 29, 61, 39], radius=3, fill=DARK)
    for side, ex in ((-1, 30), (1, 50)):
        # forma de cuña: alta por fuera, baja hacia el centro (mirada enojada)
        outer, inner = ex - side * 7, ex + side * 6
        d.polygon([(outer, 30), (inner, 34), (inner, 37), (outer, 37)], fill=OUTLINE)
        d.polygon([(outer + side, 31), (inner - side, 34), (inner - side, 36), (outer + side, 36)], fill=eye)
        d.line([(ex - 2, 35), (ex + 2, 35)], fill=core)
    d.line([(36, 32), (44, 32)], fill=OUTLINE, width=2)

    # --- esfera arcoíris grande en el centro ---
    ox, oy, r = cx, 17, 9
    d.ellipse([ox - r - 1, oy - r - 1, ox + r + 1, oy + r + 1], fill=OUTLINE)
    px = img.load()
    for y in range(oy - r, oy + r + 1):
        for x in range(ox - r, ox + r + 1):
            dx, dy = x - ox, y - oy
            dist = math.hypot(dx, dy)
            if dist <= r:
                ang = math.atan2(dy, dx) / (2 * math.pi)
                v = 1.0 if dist < r - 2 else 0.8
                px[x, y] = rainbow(ang + f * 0.05, 0.85, v) + (255,)
    d.ellipse([ox - 5, oy - 6, ox - 2, oy - 3], fill=(255, 255, 255))
    d.point([(ox + 4, oy + 4)], fill=(255, 255, 255))
    for i in range(8):
        a = i / 8 * 2 * math.pi + f * 0.25
        sx = ox + math.cos(a) * (r + 4)
        sy = oy + math.sin(a) * (r + 3)
        d.point([(sx, sy)], fill=PINK if i % 2 else PURPLE)

    # --- contorno oscuro y textura de bajo detalle ---
    out = img.copy()
    op = out.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            if px[x, y][3]:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3]:
                    op[x, y] = OUTLINE + (255,)
                    break
    noise = random.Random(42)
    for y in range(h):
        for x in range(w):
            r_, g_, b_, a_ = op[x, y]
            n = noise.uniform(0.82, 1.14)
            if a_:
                op[x, y] = (min(255, int(r_ * n)), min(255, int(g_ * n)), min(255, int(b_ * n)), a_)

    if mode == "outline":
        for y in range(h):
            for x in range(w):
                if op[x, y][3]:
                    lum = sum(op[x, y][:3]) / 3
                    op[x, y] = (10, 0, 0, 255) if lum < 110 else (0, 0, 0, 0)
    elif mode == "white":
        for y in range(h):
            for x in range(w):
                if op[x, y][3]:
                    op[x, y] = (255, 255, 255, 255)
    return out


def place(canvas, art, scale=1.0, dx=0, dy=0):
    size = int(EMBLEM_SIZE * scale)
    big = art.resize((size, size), Image.NEAREST)
    x = (EMBLEM_SIZE - size) // 2 + dx
    y = (EMBLEM_SIZE - size) // 2 + dy
    canvas.paste(big, (x, y), big)


def glitch(img, strength, rng):
    """Desplaza franjas horizontales, separa canales y blanquea/borra píxeles."""
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    while y < h:
        band = rng.randint(1, 5)
        shift = int(rng.uniform(-1, 1) * strength * 18)
        out.paste(img.crop((0, y, w, y + band)), (shift, y))
        y += band
    px = out.load()
    for yy in range(h):
        for xx in range(w):
            r, g, b, a = px[xx, yy]
            if not a:
                continue
            roll = rng.random()
            if roll < strength * 0.55:
                px[xx, yy] = (0, 0, 0, 0)
            elif roll < strength * 0.9:
                px[xx, yy] = (255, 255, 255, 255)
            else:
                px[xx, yy] = (min(255, r + 60), g // 2, b // 2, a)
    return out


def emblem_frames():
    rng = random.Random(7)
    frames = []
    for f in range(EMBLEM_FRAMES):
        c = Image.new("RGBA", (EMBLEM_SIZE, EMBLEM_SIZE), (0, 0, 0, 0))
        if f == 0:
            place(c, creature(f, "outline"), 1.0)
        elif f == 1:
            place(c, creature(f, "white"), 0.98)
        elif f in (2, 3):
            place(c, creature(f), 0.97 if f == 2 else 0.95)
        elif f < 36:
            bob = round(math.sin(f * 0.45) * 1.5)
            jitter = rng.choice([-1, 1]) if f % 8 == 0 else 0
            place(c, creature(f), 0.95, jitter, bob)
        elif f < 42:
            strength = (f - 35) / 6
            tmp = Image.new("RGBA", (EMBLEM_SIZE, EMBLEM_SIZE), (0, 0, 0, 0))
            place(tmp, creature(f), 0.95)
            c = glitch(tmp, strength, rng)
        elif f < 47:
            # restos blancos que se dispersan
            d = ImageDraw.Draw(c)
            n = 12 - 2 * (f - 42)
            for _ in range(n):
                x = rng.randint(6, 70)
                y = 34 + rng.randint(-12, 12) - (f - 42)
                d.line([(x, y), (x + rng.randint(2, 10), y)], fill=(255, 255, 255, 255))
        frames.append(c)
    return frames


def bolt(d, start, end, width, rng, broken=0.0):
    pts = [start]
    segs = 9
    for i in range(1, segs):
        t = i / segs
        x = start[0] + (end[0] - start[0]) * t + rng.uniform(-7, 7)
        y = start[1] + (end[1] - start[1]) * t + rng.uniform(-7, 7)
        pts.append((x, y))
    pts.append(end)
    for a, b in zip(pts, pts[1:]):
        if rng.random() < broken:
            continue
        d.line([a, b], fill=(255, 255, 255, 255), width=width)


def lightning_frames():
    cx, cy = LW / 2, LH / 2
    angles = [0.3, 1.2, 2.4, 3.5, 4.4, 5.5]
    frames = []
    for f in range(LIGHTNING_FRAMES):
        rng = random.Random(100 + f)
        c = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        if f < LIGHTNING_FRAMES - 1:
            width = [5, 4, 3, 3, 2, 1, 1][f]
            broken = [0, 0, 0.1, 0.25, 0.45, 0.65, 0.8][f]
            for a in angles:
                a += rng.uniform(-0.15, 0.15)
                inner = 16 + f * 3
                start = (cx + math.cos(a) * inner, cy + math.sin(a) * inner * 0.7)
                end = (cx + math.cos(a) * 120, cy + math.sin(a) * 80)
                bolt(d, start, end, width, rng, broken)
        frames.append(c)
    return frames


def strip(frames):
    w, h = frames[0].size
    s = Image.new("RGBA", (w, h * len(frames)), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        s.paste(fr, (0, i * h))
    return s


def preview(emblem, lightning):
    """GIF a 30 fps que combina las capas con sus propias velocidades."""
    W, H = 320, 180
    out = []
    total = EMBLEM_FRAMES / EMBLEM_FPS + 0.5
    steps = int(total * 30)
    for i in range(steps):
        t = i / 30
        bg = Image.new("RGBA", (W, H), (70, 110, 60, 255))
        if t < 0.3:
            a = int(230 * (1 - t / 0.3) ** 2)
            bg.alpha_composite(Image.new("RGBA", (W, H), (220, 0, 0, a)))
        lf = int(t * LIGHTNING_FPS)
        if lf < LIGHTNING_FRAMES:
            bg.alpha_composite(lightning[lf].resize((W, H), Image.NEAREST))
        ef = int(t * EMBLEM_FPS)
        if ef < EMBLEM_FRAMES:
            e = emblem[ef].resize((120, 120), Image.NEAREST)
            bg.alpha_composite(e, ((W - 120) // 2, 8))
        out.append(bg.convert("RGB"))
    out[0].save(ROOT / "preview.gif", save_all=True, append_images=out[1:],
                duration=33, loop=0)


if __name__ == "__main__":
    em = emblem_frames()
    li = lightning_frames()
    strip(em).save(OUT / "emblem.png")
    strip(li).save(OUT / "lightning.png")
    Image.new("RGBA", (16, 16), (255, 255, 255, 255)).save(OUT / "white.png")
    preview(em, li)
    print("ok:", OUT)
