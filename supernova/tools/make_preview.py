"""Simula la supernova para verla sin abrir el juego (video e imagen con los momentos clave).

Uso:  python3 tools/make_preview.py
Crea preview.mp4 (1288x586, apaisado como las capturas) y preview.png.
Usa las mismas texturas, tamaños, mezclas (normal o aditiva) y tiempos que las partículas y el
script; el modelo 3D de la estrella se dibuja con three.js (tools/preview3d, necesita node).
"""
import json
import math
import random
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

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
STAR_R, EXP_R, FLASH_H, STAR_LIFE = 5.15, 19.3, 24.0, 3.35


def load(name):
    return Image.open(TEX / f"{name}.png").convert("RGBA")


halo, brasa, nuc = load("halo"), load("brasa"), load("nucleo")
body_atlas, rays, bolts, ring, core = (load("exp_cuerpo"), load("exp_rayos"), load("exp_morados"),
                                      load("exp_anillo"), load("exp_nucleo"))
fla = load("destello")
STAR_LAYER = {}          # tick -> imagen RGBA del modelo 3D de la estrella (la llena render_star_model)
T_SPAWN, BURST = 14, 46  # cuándo aparece la entidad de la estrella y cuánto dura la rota (ticks)

clamp = lambda v, a, b: max(a, min(b, v))
ease = lambda a, t, p=3: 1 - (1 - clamp(a / t, 0, 1)) ** p


def cell(img, frame, cols, size):
    return img.crop(((frame % cols) * size, (frame // cols) * size, (frame % cols + 1) * size, (frame // cols + 1) * size))


rng = random.Random(11)

# brasas y chispas: posiciones al azar fijas para que el video sea estable
EMBERS = []
for k in range(int(45 * (STAR_LIFE - 0.2))):
    v = np.random.default_rng(k).normal(size=3)
    v /= np.linalg.norm(v)
    EMBERS.append((k / 45, v, rng.uniform(1, 3), rng.uniform(1.2, 2.6), rng.random()))
SPARKS = []
for k in range(240):
    v = np.random.default_rng(1000 + k).normal(size=3)
    v /= np.linalg.norm(v)
    c = rng.random()
    col = (255, 255, 255) if c < 0.25 else (255, 140, 190) if c < 0.5 else (190, 150, 255) if c < 0.75 else (224, 255, 255)
    SPARKS.append((v, rng.uniform(18, 42), rng.uniform(1.0, 2.6), rng.random(), col))

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
        top, bottom = ((14, 6, 14), (52, 20, 36)) if tick < T_EXP else ((50, 32, 58), (100, 70, 104))
    else:
        k = clamp((tick - T_TIME) / 40, 0, 1) if tick >= T_TIME else 1
        top, bottom = lerp((250, 225, 240), (90, 140, 230), k), lerp((255, 240, 248), (170, 205, 245), k)
    for y in range(horizon):
        d.line([(0, y), (W, y)], fill=lerp(top, bottom, y / horizon))
    if night:
        for x, y, s in STARS:
            c = int(170 + 50 * math.sin(tick * 0.2 + x))
            d.ellipse([x - s / 2, y - s / 2, x + s / 2, y + s / 2], fill=(c, c - 25, c - 10))
    ground = (205, 190, 70) if not night else (80, 70, 30) if tick < T_EXP else (150, 130, 80)
    d.rectangle([0, horizon, W, H], fill=ground)
    return np.array(img).astype(np.float32)


class Frame:
    def __init__(self, tick):
        self.img = background(tick)
        sh = 2 if T_SHAKE <= tick < T_EXP else 12 * (1 - (tick - T_EXP) / 50) if T_EXP <= tick < T_EXP + 50 else 0
        self.shake = (int(srng.uniform(-sh, sh)), int(srng.uniform(-sh, sh))) if sh else (0, 0)

    def put(self, tex, half_w, half_h, alpha, depth, x=0.0, y=0.0, angle=0.0, tint=(1, 1, 1), add=False):
        """Partícula de half_w x half_h bloques a 'depth' bloques, desplazada (x, y) bloques."""
        rw, rh = half_w * FOCAL / depth, half_h * FOCAL / depth
        if rw < 0.6 or rh < 0.6 or alpha <= 0.003:
            return
        t = tex.resize((max(2, round(2 * rw)), max(2, round(2 * rh))), Image.BILINEAR)
        if angle:
            t = t.rotate(-angle, resample=Image.BILINEAR, expand=True)
        a = np.array(t).astype(np.float32) / 255
        rgb = a[..., :3] * np.array(tint, np.float32)
        al = a[..., 3] * alpha
        sx = CX + x * FOCAL / depth + self.shake[0] - t.width / 2
        sy = CY - y * FOCAL / depth + self.shake[1] - t.height / 2
        x0, y0 = int(round(sx)), int(round(sy))
        X0, Y0 = max(0, x0), max(0, y0)
        X1, Y1 = min(W, x0 + t.width), min(H, y0 + t.height)
        if X0 >= X1 or Y0 >= Y1:
            return
        rgb = rgb[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * 255
        al = al[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None]
        dst = self.img[Y0:Y1, X0:X1]
        if add:
            self.img[Y0:Y1, X0:X1] = np.minimum(255, dst + rgb * al)
        else:
            self.img[Y0:Y1, X0:X1] = dst * (1 - al) + rgb * al


def render(tick):
    f = Frame(tick)
    # ---- formación: núcleo y piezas
    a = (tick - T_DARK) / FPS
    life = (T_STAR - T_DARK) / 20 + 0.3
    if 0 <= a <= life:
        s = STAR_R * 1.2 * (0.45 + 0.55 * clamp(a / (life - 0.3), 0, 1)) * (1 + 0.08 * math.sin(math.radians(a * 720)))
        f.put(nuc, s, s, clamp(a / 0.4, 0, 1) * (1 - clamp((a - life + 0.3) / 0.3, 0, 1)), DIST + 0.6, add=True)
    # ---- la estrella completa: resplandor detrás
    a = (tick - T_STAR) / FPS
    if 0 <= a <= STAR_LIFE:
        swell = 1 + clamp((a - 2.2) / 1.0, 0, 1) * 0.3
        end = 1 - clamp((a - 3.2) / 0.12, 0, 1)
        s = STAR_R * 1.9 * swell * (1 + math.sin(math.radians(a * 250)) * 0.05)
        f.put(halo, s, s, (0.5 + 0.15 * math.sin(math.radians(a * 400))) * clamp(a / 0.4, 0, 1) * end, DIST + 0.4, add=True)
    # ---- el modelo 3D de la estrella (formándose, girando o rota)
    if tick in STAR_LAYER:
        layer = np.array(STAR_LAYER[tick]).astype(np.float32) / 255
        if f.shake != (0, 0):
            layer = np.roll(layer, f.shake, axis=(1, 0))
        al = layer[..., 3:4]
        f.img = f.img * (1 - al) + layer[..., :3] * 255 * al
    # ---- brasas
    a = (tick - T_STAR) / FPS
    if 0 <= a <= STAR_LIFE:
        swell = 1 + clamp((a - 2.2) / 1.0, 0, 1) * 0.3
        end = 1 - clamp((a - 3.2) / 0.12, 0, 1)
        for t0, v, sp, lf, rnd in EMBERS:
            e = a - t0
            if 0 <= e <= lf and t0 <= STAR_LIFE - 0.2:
                dist = STAR_R * 0.9 * swell + sp * (1 - math.exp(-0.6 * e)) / 0.6
                px, py, pz = v[0] * dist, v[1] * dist + 0.4 * e * e, v[2] * dist
                if pz < 0 and math.hypot(px, py) < STAR_R * 0.95 * swell:
                    continue                                     # detrás de la estrella
                tt = e / lf
                sz = (0.12 + 0.12 * rnd) * (1 - tt)
                f.put(brasa, sz, sz, 1 - tt, DIST - pz, px, py, tint=(1, 0.95 - 0.45 * tt, 0.7 - 0.55 * tt), add=True)
    # ---- explosión por capas
    a = (tick - T_EXP) / FPS
    if 0 <= a <= 3.2:
        s = EXP_R * (0.25 + 0.75 * ease(a, 0.55)) + a * 0.5
        f.put(cell(body_atlas, int(a * 6) % 4, 2, 512), s, s, 1 - clamp((a - 2.0) / 1.2, 0, 1), DIST - 1, angle=3 * a + 40)
        s = EXP_R * 0.95 * (0.3 + 0.7 * ease(a, 0.5))
        f.put(rays, s, s, 0.9 * (1 - clamp((a - 1.5) / 1.3, 0, 1)), DIST - 1, angle=12 * a + 70, add=True)
        for delay in (0, 0.3):
            r_ = a - delay
            if 0 <= r_ <= 1.6:
                s = EXP_R * (0.5 + 1.4 * ease(r_, 1.6, 2))
                f.put(ring, s, s, 1 - r_ / 1.6, DIST - 1, add=True)
        if a <= 0.9:
            s = 3 + EXP_R * 0.6 * ease(a, 0.25, 2)
            f.put(core, s, s, 0.7 * (1 - clamp((a - 0.1) / 0.8, 0, 1)), DIST - 1, add=True)
        s = EXP_R * 0.8 * (0.3 + 0.7 * ease(a, 0.5))
        f.put(cell(bolts, (int(a * 18) + 5) % 16, 4, 512), s, s, 1 - clamp((a - 1.8) / 0.8, 0, 1), DIST - 1.8,
              angle=-6 * a + 200)
        for v, sp, lf, rnd, col in SPARKS:
            if a <= lf:
                dist = 3 + sp * (1 - math.exp(-1.1 * a)) / 1.1
                pz = v[2] * dist
                if DIST - 1 - pz < 3:
                    continue
                tt = a / lf
                sz = (0.25 + 0.3 * rnd) * (1 - tt)
                f.put(brasa, sz, sz, 1 - tt * tt, DIST - pz, v[0] * dist, v[1] * dist,
                      tint=tuple(c / 255 for c in col), add=True)
    # ---- destello
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 4.0:
        s = FLASH_H * (0.3 + 0.7 * ease(a, 0.35, 2))
        f.put(fla, s * 2.85, s, clamp(a / 0.15, 0, 1) * (1 - clamp((a - 1.6) / 2.4, 0, 1)), DIST + 3)
    out = f.img
    t = tick / FPS
    fade = None
    if t < 2.0:
        v = clamp(t / 0.5, 0, 1) if t < 0.5 else 1 if t < 0.8 else 1 - clamp((t - 0.8) / 1.2, 0, 1)
        fade = ((0, 0, 0), v)
    a = (tick - T_FLASH) / FPS
    if 0 <= a <= 0.75:
        v = clamp(a / 0.1, 0, 1) if a < 0.1 else 1 if a < 0.15 else 1 - clamp((a - 0.15) / 0.6, 0, 1)
        fade = ((255, 236, 248), v)
    if fade:
        out = out * (1 - fade[1]) + np.array(fade[0], np.float32) * fade[1]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


KEYS = [(40, "1. Las piezas 3D llegan volando"), (70, "2. Encajan en la esfera"), (120, "3. La estrella 3D girando"),
        (163, "4. Explota: las piezas salen disparadas"), (172, "5. La explosion y la onda"), (186, "6. El destello")]


def render_star_model(tmp):
    """Dibuja el modelo 3D de la estrella en cada tick con three.js (tools/preview3d)."""
    import json as _json
    tool = ROOT / "tools" / "preview3d"
    if not (tool / "node_modules" / "three").exists():
        subprocess.run(["npm", "install", "--silent"], cwd=tool, check=True)
    cam = {"pos": [0, -(HEIGHT - EYE), DIST], "look": [0, -(HEIGHT - EYE), 0], "fov": 60}
    F = ["animation.supernova.formacion", "animation.supernova.giro", "animation.supernova.hinchar"]
    jobs = []
    for t in range(T_SPAWN, T_EXP + BURST):
        anims, at = (F, (t - T_SPAWN) / FPS) if t < T_EXP else (["animation.supernova.estalla"], (t - T_EXP) / FPS)
        jobs.append({"anims": anims, "t": at, "cam": cam, "out": f"{tmp}/star{t:04d}.png"})
    cfg = {"geo": str(ROOT / "SupernovaRP/models/entity/supernova_estrella.geo.json"),
           "anim": str(ROOT / "SupernovaRP/animations/supernova_estrella.animation.json"),
           "tex": str(ROOT / "SupernovaRP/textures/entity/supernova/estrella.png"),
           "width": W, "height": H, "jobs": jobs}
    Path(f"{tmp}/jobs.json").write_text(_json.dumps(cfg))
    subprocess.run(["node", str(tool / "shot.js"), f"{tmp}/jobs.json"], check=True)
    for j in jobs:
        t = int(Path(j["out"]).stem[4:])
        STAR_LAYER[t] = Image.open(j["out"]).convert("RGBA").copy()


def main():
    with tempfile.TemporaryDirectory() as stars:
        render_star_model(stars)
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
