"""Corta la estrella (la bola de lava) en sus placas de roca para la animación pieza por pieza.

Uso:  python3 tools/make_pieces.py
Necesita: numpy, pillow, opencv-python-headless

Lee   SupernovaRP/textures/particle/supernova/estrella.png
Crea  SupernovaRP/textures/particle/supernova/piezas.png   todas las piezas en una textura
      SupernovaRP/textures/particle/supernova/nucleo.png   el núcleo que brilla mientras se forma
      SupernovaBP/scripts/piezas.js                        dónde va cada pieza y su trozo de textura

Las piezas se cortan por las grietas de la propia bola: las placas oscuras son las piezas y
las grietas brillantes se reparten entre las placas vecinas, así que al juntarse todas forman
la bola exacta. Las piezas largas del borde se parten en trozos.
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from make_particles import STAR_R

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"
JS = ROOT / "SupernovaBP" / "scripts" / "piezas.js"

MIN_AREA = 120          # placas más pequeñas se reparten entre las vecinas
MAX_SPAN = 38           # grados: las piezas del borde más largas se parten
ATLAS_W = 1024
PAD = 2


def main():
    img = np.array(Image.open(TEX / "estrella.png").convert("RGBA"))
    n = img.shape[0]
    rgb = img[..., :3].astype(np.float32)
    disk = img[..., 3] > 8
    c = (n - 1) / 2
    yy, xx = np.mgrid[0:n, 0:n]
    ang = np.degrees(np.arctan2(yy - c, xx - c)) % 360
    rad = np.hypot(xx - c, yy - c)

    # grietas: líneas finas más claras que lo de alrededor, o muy amarillas
    lum = rgb.mean(2)
    tophat = cv2.morphologyEx(lum, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    crack = ((rgb[..., 1] > 120) | (tophat > 18)) & disk
    crack = cv2.dilate(crack.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    plates = ((~crack) & disk).astype(np.uint8)
    count, lab, stats, _ = cv2.connectedComponentsWithStats(plates, connectivity=4)

    markers = np.zeros((n, n), np.int32)
    next_id = 1
    for i in range(1, count):
        if stats[i, 4] < MIN_AREA:
            continue
        m = lab == i
        a = ang[m]
        # tramo de ángulos que ocupa (teniendo en cuenta la vuelta de 360°)
        s = np.sort(a)
        gaps = np.diff(np.r_[s, s[0] + 360])
        span = 360 - gaps.max()
        if span > MAX_SPAN and rad[m].mean() > n * 0.3:
            start = s[(np.argmax(gaps) + 1) % len(s)]
            rel = (a - start) % 360
            parts = math.ceil(span / MAX_SPAN)
            idx = np.minimum((rel / span * parts).astype(int), parts - 1)
            ys, xs = np.nonzero(m)
            for p in range(parts):
                sel = idx == p
                if sel.sum() >= MIN_AREA // 2:
                    markers[ys[sel], xs[sel]] = next_id
                    next_id += 1
        else:
            markers[m] = next_id
            next_id += 1
    # repartir grietas y placas pequeñas: cada pieza crece a la misma velocidad hasta tocar a
    # sus vecinas, así cada grieta queda partida por la mitad entre las dos placas
    ws = markers.copy()
    kernel = np.ones((3, 3), np.uint8)
    while True:
        todo = disk & (ws == 0)
        if not todo.any():
            break
        grown = cv2.dilate(ws.astype(np.float32), kernel).astype(np.int32)
        new = todo & (grown > 0)
        if not new.any():
            break
        ws[new] = grown[new]
    ws[~disk] = 0
    labels = [l for l in np.unique(ws) if l > 0]

    # piezas: recorte de cada una (1 px más grande para que no queden rendijas al juntarse)
    pieces = []
    for l in labels:
        m = ws == l
        if not m.any():
            continue
        big = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        ys, xs = np.nonzero(big)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        crop = img[y0:y1, x0:x1].copy()
        crop[..., 3] = np.where(big[y0:y1, x0:x1], crop[..., 3], 0)
        cy_, cx_ = (y0 + y1) / 2, (x0 + x1) / 2
        pieces.append({"crop": crop, "x": cx_ - n / 2, "y": cy_ - n / 2, "w": x1 - x0, "h": y1 - y0,
                       "dist": math.hypot(cx_ - n / 2, cy_ - n / 2)})

    # orden de llegada: del centro hacia afuera, con algo de azar
    rng = np.random.default_rng(7)
    for p in pieces:
        p["key"] = p["dist"] + rng.uniform(-60, 60)
    pieces.sort(key=lambda p: p["key"])

    # empaquetar en una textura (por filas)
    x = y = row_h = 0
    for p in sorted(pieces, key=lambda p: -p["h"]):
        if x + p["w"] + PAD > ATLAS_W:
            x, y = 0, y + row_h + PAD
            row_h = 0
        p["u"], p["v"] = x, y
        x += p["w"] + PAD
        row_h = max(row_h, p["h"])
    atlas_h = y + row_h
    atlas = np.zeros((atlas_h, ATLAS_W, 4), np.uint8)
    for p in pieces:
        atlas[p["v"]:p["v"] + p["h"], p["u"]:p["u"] + p["w"]] = p["crop"]
    Image.fromarray(atlas, "RGBA").save(TEX / "piezas.png")

    # núcleo: brillo redondo con los colores de las grietas de la bola
    hot = rgb[crack & (lum > np.percentile(lum[crack], 60))]
    core_cols = [np.percentile(hot, q, axis=0) for q in (95, 60, 20)]
    m = 256
    gy, gx = np.mgrid[0:m, 0:m]
    rr = np.hypot(gx - (m - 1) / 2, gy - (m - 1) / 2) / (m / 2)
    col = np.zeros((m, m, 3))
    for (r0, c0), (r1, c1) in zip([(0, core_cols[0]), (0.45, core_cols[1]), (1.0, core_cols[2])],
                                  [(0.45, core_cols[1]), (1.0, core_cols[2]), (1.01, core_cols[2])]):
        sel = (rr >= r0) & (rr < r1)
        t = ((rr - r0) / (r1 - r0))[sel][:, None]
        col[sel] = c0 * (1 - t) + c1 * t
    core_a = np.clip(1 - rr, 0, 1) ** 1.6
    Image.fromarray(np.dstack([col, core_a * 255]).clip(0, 255).astype(np.uint8), "RGBA").save(TEX / "nucleo.png")

    data = [{"u": int(p["u"]), "v": int(p["v"]), "w": int(p["w"]), "h": int(p["h"]),
             "x": round(float(p["x"]), 2), "y": round(float(p["y"]), 2)} for p in pieces]
    JS.write_text(
        "// Generado por tools/make_pieces.py: las piezas de la estrella, en orden de llegada.\n"
        "// x, y: centro de la pieza respecto al centro de la bola, en píxeles de estrella.png (y hacia abajo)\n"
        "// u, v, w, h: su trozo en piezas.png\n"
        f"export const STAR_TEXTURE = {n};\n"
        f"export const STAR_HALF = {STAR_R};   // mitad del ancho de la estrella, en bloques\n"
        f"export const ATLAS = {{ width: {ATLAS_W}, height: {atlas_h} }};\n"
        f"export const PIEZAS = {json.dumps(data, separators=(',', ':'))};\n")
    print(f"{len(pieces)} piezas, textura {ATLAS_W}x{atlas_h}")
    return pieces, ws


if __name__ == "__main__":
    main()
