"""Corta la estrella (la bola de lava) en sus placas de roca para la animación pieza por pieza.

Uso:  python3 tools/make_pieces.py
Necesita: numpy, pillow, opencv-python-headless

Lee   SupernovaRP/textures/particle/supernova/estrella.png
Crea  SupernovaRP/textures/particle/supernova/piezas.png   cada pieza en 3D dando una vuelta (24 fotogramas)
      SupernovaRP/textures/particle/supernova/nucleo.png   el núcleo que brilla mientras se forma
      SupernovaBP/scripts/piezas.js                        dónde va cada pieza y su trozo de textura

Las piezas se cortan por las grietas de la propia bola: las placas oscuras son las piezas y
las grietas brillantes se reparten entre las placas vecinas, así que al juntarse todas forman
la bola exacta. Las piezas largas del borde se parten en trozos.

Cada pieza es un trozo de la cáscara de la bola con grosor: por fuera la roca de la bola, por
dentro lava al rojo vivo y los lados brillando. Se dibuja girando en 3D sobre un eje propio
(24 fotogramas = una vuelta); el fotograma 0 es la pieza en su sitio, tal cual en la bola.
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
ATLAS_W = 2048
PAD = 2
FRAMES = 24             # fotogramas de la vuelta en 3D de cada pieza (15° cada uno)
COLS, ROWS = 12, 2
SCALE_DIV = 3           # las piezas se guardan a un tercio de resolución (van en movimiento)
THICK = 0.11            # grosor de la cáscara (en radios de la bola)
LIGHT = np.array([-0.45, 0.55, 0.7])
LIGHT /= np.linalg.norm(LIGHT)
LAVA = np.array([[255, 214, 120], [240, 150, 55], [200, 85, 25]], float)   # interior: amarillo -> naranja


def shade(nrm):
    return 0.5 + 0.65 * np.clip(nrm @ LIGHT, 0, 1)


def piece_points(big, edge, rgb, lum, n, Rpx, rng):
    """Puntos 3D de la pieza (4 por píxel): la cara de fuera (la bola), la de dentro (lava) y los lados."""
    sub = np.array([[-0.25, -0.25], [0.25, -0.25], [-0.25, 0.25], [0.25, 0.25]])

    def sphere(ys, xs):
        X = np.repeat(xs + 0.5, 4) + np.tile(sub[:, 0], len(xs))
        Y = np.repeat(ys + 0.5, 4) + np.tile(sub[:, 1], len(ys))
        X = (X - n / 2) / Rpx
        Y = -(Y - n / 2) / Rpx
        r2 = X * X + Y * Y
        scale = np.where(r2 > 1, 1 / np.sqrt(np.maximum(r2, 1e-9)), 1.0)   # el borde, sobre la bola
        X, Y = X * scale, Y * scale
        Z = np.sqrt(np.clip(1 - X * X - Y * Y, 0, 1))
        return np.stack([X, Y, Z], -1)

    ys, xs = np.nonzero(big)
    front = sphere(ys, xs)
    col = np.repeat(rgb[ys, xs], 4, axis=0)
    emis = np.repeat(np.clip((lum[ys, xs] - 120) / 80, 0, 1), 4)
    P, N, C, E = [front], [front], [col], [emis]
    # cara de dentro: lava al rojo vivo
    field = cv2.GaussianBlur(rng.random((n, n)).astype(np.float32), (0, 0), 5)
    field = (field - field.min()) / (field.max() - field.min())
    noise = np.repeat(field[ys, xs], 4)
    back = np.array([0, 0, THICK])                         # el grosor va hacia atrás (en su sitio no se ve)
    inner = front - back
    t = np.clip((noise[:, None] - 0.3) / 0.4, 0, 1)
    lava = LAVA[0] * (1 - t) + LAVA[2] * t
    P.append(inner), N.append(-front), C.append(lava * 0.85), E.append(np.ones(len(front)))
    # lados: del borde de fuera al de dentro, brillando más hacia dentro
    ey, ex = np.nonzero(edge)
    if len(ey):
        base = sphere(ey, ex)
        steps = max(8, int(THICK * Rpx * 3))
        for t in np.linspace(0, 1, steps):
            P.append(base - back * t)
            out = base.copy()
            N.append(out)
            C.append(np.tile(LAVA[0] * (1 - t) + LAVA[1] * t, (len(base), 1)))
            E.append(np.ones(len(base)))
    return {"p": np.concatenate(P), "n": np.concatenate(N), "c": np.concatenate(C), "e": np.concatenate(E),
            "n0": np.concatenate(N)}


def rotation(axis, deg):
    a = math.radians(deg)
    k = axis
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def render_piece(pts, pivot, axis, deg, cell, Rpx):
    """Dibuja la pieza girada 'deg' grados (proyección desde delante, con profundidad)."""
    R = rotation(axis, deg)
    q = (pts["p"] - pivot) @ R.T
    nr = pts["n"] @ R.T
    sx = np.floor(q[:, 0] * Rpx + cell / 2).astype(int)
    sy = np.floor(-q[:, 1] * Rpx + cell / 2).astype(int)
    ok = (sx >= 0) & (sx < cell) & (sy >= 0) & (sy < cell)
    # luz: lo que no brilla por sí mismo cambia de luz al girar
    ratio = np.clip(shade(nr) / np.maximum(shade(pts["n0"]), 1e-3), 0.3, 1.8)
    e = pts["e"]
    col = pts["c"] * (e + (1 - e) * ratio)[:, None]
    # la cara de dentro y los lados solo se ven si miran hacia delante (o están de canto)
    z = q[:, 2]
    idx = np.nonzero(ok)[0]
    order = idx[np.argsort(z[idx])]                         # de atrás hacia delante
    lin = sy[order] * cell + sx[order]
    rgb = np.zeros((cell * cell, 3))
    cov = np.zeros(cell * cell)
    rgb[lin] = col[order]                                   # el último (el de delante) gana
    cov[lin] = 1
    rgb = rgb.reshape(cell, cell, 3)
    cov = cov.reshape(cell, cell)
    # cerrar agujeritos de 1 px
    k = np.ones((3, 3), np.float32)
    nb = cv2.filter2D(cov.astype(np.float32), -1, k, borderType=cv2.BORDER_CONSTANT)
    fill = (cov == 0) & (nb >= 6)
    if fill.any():
        s_rgb = cv2.filter2D((rgb * cov[..., None]).astype(np.float32), -1, k, borderType=cv2.BORDER_CONSTANT)
        rgb[fill] = s_rgb[fill] / np.maximum(nb[fill], 1)[:, None]
        cov[fill] = 1
    # bajar de resolución (suaviza los bordes)
    d = SCALE_DIV
    c2 = cell // d
    cv_ = cov.reshape(c2, d, c2, d).mean((1, 3))
    rg = (rgb * cov[..., None]).reshape(c2, d, c2, d, 3).sum((1, 3)) / np.maximum(cov.reshape(c2, d, c2, d).sum((1, 3)), 1)[..., None]
    return np.dstack([np.clip(rg, 0, 255), np.clip(cv_, 0, 1) * 255]).astype(np.uint8)


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

    # piezas en 3D: cada una es un trozo de cáscara de la bola, con grosor
    Rpx = n / 2 * 0.97                                   # radio de la bola en la textura
    rng = np.random.default_rng(7)
    lum_all = rgb.mean(2)
    pieces = []
    for l in labels:
        m = ws == l
        if not m.any():
            continue
        big = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        big &= disk
        edge = big & ~(cv2.erode(big.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        pts = piece_points(big, edge, rgb, lum_all, n, Rpx, rng)
        pivot = (pts["p"].min(0) + pts["p"].max(0)) / 2
        reach = np.linalg.norm(pts["p"] - pivot, axis=1).max() * Rpx
        cell = int(math.ceil(reach + 3)) * 2                       # a resolución completa
        cell += (-cell) % (2 * SCALE_DIV)                           # divisible entre 2 y SCALE_DIV
        axis = rng.normal(size=3)
        axis /= np.linalg.norm(axis)
        frames = [render_piece(pts, pivot, axis, k * 360 / FRAMES, cell, Rpx) for k in range(FRAMES)]
        pieces.append({"frames": frames, "cell": cell // SCALE_DIV, "full": cell,
                       "x": pivot[0] * Rpx, "y": -pivot[1] * Rpx,
                       "dist": math.hypot(pivot[0], pivot[1]) * Rpx})

    # orden de llegada: del centro hacia afuera, con algo de azar
    for p in pieces:
        p["key"] = p["dist"] + rng.uniform(-60, 60)
    pieces.sort(key=lambda p: p["key"])

    # empaquetar: cada pieza ocupa un bloque de COLS x ROWS fotogramas
    x = y = row_h = 0
    for p in sorted(pieces, key=lambda p: -p["cell"]):
        bw, bh = COLS * p["cell"], ROWS * p["cell"]
        if x + bw > ATLAS_W:
            x, y = 0, y + row_h + PAD
            row_h = 0
        p["u"], p["v"] = x, y
        x += bw + PAD
        row_h = max(row_h, bh)
    atlas_h = y + row_h
    atlas = np.zeros((atlas_h, ATLAS_W, 4), np.uint8)
    for p in pieces:
        c = p["cell"]
        for k, f in enumerate(p["frames"]):
            u, v = p["u"] + (k % COLS) * c, p["v"] + (k // COLS) * c
            atlas[v:v + c, u:u + c] = f
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

    data = [{"u": int(p["u"]), "v": int(p["v"]), "c": int(p["cell"]), "s": int(p["full"]),
             "x": round(float(p["x"]), 2), "y": round(float(p["y"]), 2)} for p in pieces]
    JS.write_text(
        "// Generado por tools/make_pieces.py: las piezas de la estrella, en orden de llegada.\n"
        "// x, y: centro de giro de la pieza respecto al centro de la bola, en píxeles de estrella.png\n"
        "//       (y hacia abajo); s: tamaño de su cuadro en esos píxeles\n"
        "// u, v: esquina de su bloque en piezas.png; c: tamaño de cada fotograma en piezas.png\n"
        "// Cada pieza tiene FRAMES fotogramas (una vuelta en 3D), en COLS columnas.\n"
        f"export const STAR_TEXTURE = {n};\n"
        f"export const STAR_HALF = {STAR_R};   // mitad del ancho de la estrella, en bloques\n"
        f"export const ATLAS = {{ width: {ATLAS_W}, height: {atlas_h} }};\n"
        f"export const FRAMES = {FRAMES};\n"
        f"export const COLS = {COLS};\n"
        f"export const PIEZAS = {json.dumps(data, separators=(',', ':'))};\n")
    print(f"{len(pieces)} piezas, textura {ATLAS_W}x{atlas_h}")
    return pieces, ws


if __name__ == "__main__":
    main()
