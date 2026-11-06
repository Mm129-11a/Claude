"""Genera las texturas de la animación de muerte (pixel art original).

Uso:  python3 tools/generate_textures.py
Crea en DeathAnimation_RP/textures/ui/death_anim/:
  emblem.png     tira vertical de 60 fotogramas de 64x64 (calavera que late y se desintegra)
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

FPS = 12
EMBLEM_FRAMES = 60
EMBLEM_SIZE = 64
LIGHTNING_FRAMES = 8
LW, LH = 160, 90

# --- Calavera: mitad izquierda (12 columnas); se refleja para tener 24x24 ---
LEFT = [
    "......KKKKKK",
    "....KKLLLLLL",
    "...KLLLLRRRR",
    "..KLLRRRRRKG",
    "..KLRRRRRKGG",
    ".KLRRRRRRKGG",
    ".KLRRRRRRRKG",
    ".KRRRRRRRRRK",
    ".KRRKKKKRRRR",
    ".KRKEEEEKRRR",
    ".KRKEEEEEKRR",
    ".KRKEEEEEKRR",
    ".KrRKEEEKRRR",
    ".KrRRKKKRRRK",
    "..KrRRRRRRKE",
    "..KrrRRRRRKK",
    "...KrrRRRRRR",
    "....KKrrrrrr",
    "....KWKWKWKW",
    "....KwKwKwKw",
    ".....KKKKKKK",
    ".WWw........",
    "..wWWw......",
    "....wWWw....",
]
ART = [row + row[::-1] for row in LEFT]
PALETTE = {
    "K": (58, 8, 10),
    "R": (200, 40, 45),
    "r": (140, 24, 30),
    "L": (240, 122, 106),
    "E": (18, 4, 4),
    "W": (243, 217, 200),
    "w": (201, 168, 150),
}


def skull(frame, mode="normal"):
    """Devuelve la calavera 24x24 RGBA para un fotograma."""
    img = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(ART):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            if mode == "outline":
                if ch == "K":
                    px[x, y] = (10, 0, 0, 255)
                continue
            if mode == "white":
                px[x, y] = (255, 255, 255, 255)
                continue
            if ch == "G":
                h = (frame * 0.06 + (x + y) * 0.08) % 1.0
                r, g, b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
                px[x, y] = (int(r * 255), int(g * 255), int(b * 255), 255)
            else:
                px[x, y] = PALETTE[ch] + (255,)
    return img


def place(canvas, art, scale, dx=0, dy=0):
    size = int(24 * scale)
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
        band = rng.randint(1, 4)
        shift = int(rng.uniform(-1, 1) * strength * 14)
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
            place(c, skull(f, "outline"), 2.4)
        elif f == 1:
            place(c, skull(f, "white"), 2.3)
        elif f in (2, 3):
            place(c, skull(f), 2.3 if f == 2 else 2.15)
        elif f < 42:
            bob = round(math.sin(f * 0.5) * 1.5)
            # pequeño temblor cada cierto tiempo, como en el video
            jitter = rng.choice([-1, 1]) if f % 9 == 0 else 0
            place(c, skull(f), 2, jitter, bob)
        elif f < 50:
            strength = (f - 41) / 8
            tmp = Image.new("RGBA", (EMBLEM_SIZE, EMBLEM_SIZE), (0, 0, 0, 0))
            place(tmp, skull(f), 2)
            c = glitch(tmp, strength, rng)
        elif f < 58:
            # restos blancos que se dispersan
            d = ImageDraw.Draw(c)
            n = 10 - (f - 50)
            for _ in range(n):
                x = rng.randint(4, 58)
                y = 26 + rng.randint(-10, 10) - (f - 50)
                d.line([(x, y), (x + rng.randint(2, 9), y)], fill=(255, 255, 255, 255))
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
    W, H = 320, 180
    out = []
    for f in range(EMBLEM_FRAMES + 6):
        bg = Image.new("RGBA", (W, H), (70, 110, 60, 255))
        t = f / FPS
        if t < 0.25:
            a = int(230 * (1 - t / 0.25))
            bg.alpha_composite(Image.new("RGBA", (W, H), (220, 0, 0, a)))
        if f < LIGHTNING_FRAMES:
            bg.alpha_composite(lightning[f].resize((W, H), Image.NEAREST))
        if f < EMBLEM_FRAMES:
            e = emblem[f].resize((96, 96), Image.NEAREST)
            bg.alpha_composite(e, ((W - 96) // 2, 14))
        out.append(bg.convert("RGB"))
    out[0].save(ROOT / "preview.gif", save_all=True, append_images=out[1:],
                duration=int(1000 / FPS), loop=0)


if __name__ == "__main__":
    em = emblem_frames()
    li = lightning_frames()
    strip(em).save(OUT / "emblem.png")
    strip(li).save(OUT / "lightning.png")
    Image.new("RGBA", (16, 16), (255, 255, 255, 255)).save(OUT / "white.png")
    preview(em, li)
    print("ok:", OUT)
