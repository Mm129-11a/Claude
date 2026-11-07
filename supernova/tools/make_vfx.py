"""Genera las texturas animadas de la supernova (estrella en 3D y explosión por capas).

Uso:  python3 tools/make_vfx.py
Necesita: numpy, pillow, scipy

Los colores salen de las imágenes de referencia:
  - bola de lava (Blockbench): roca (68,45,35) - (122,81,55) - (151,103,68), grietas (239,197,119)
  - explosión (captura 2): centro lavanda (251,225,254), cuerpo blanco, rayos morados (185,156,214),
    vetas celestes (224,253,253), borde rosa (251,115,161) y rosa claro (253,172,240)

Crea en SupernovaRP/textures/particle/supernova/:
  nucleo.png          el brillo del centro mientras se forma la estrella
(la superficie de la estrella -placas, grietas y colores- también sale de aquí: la usa
 tools/make_star_model.py para el modelo 3D; render_star/make_star dibujan una vista plana)
  halo.png            resplandor de calor alrededor de la estrella
  brasa.png           chispa / brasa
  exp_cuerpo.png      4 fotogramas de 512x512 (2x2): el cuerpo de la explosión, con el borde ondulando
  exp_rayos.png       rayos de luz celestes y lavanda que salen del centro
  exp_morados.png     16 fotogramas de 512x512 (4x4): relámpagos morados que chisporrotean
  exp_anillo.png      el anillo rosa de la onda expansiva
  exp_nucleo.png      el núcleo blanco de la explosión
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"

# --- colores medidos en las referencias ---
ROCK = [(0.0, (52, 34, 27)), (0.35, (68, 45, 35)), (0.6, (122, 81, 55)), (0.85, (151, 103, 68)),
        (1.0, (176, 128, 88))]
CRACK_CORE = np.array([255, 238, 170.0])
CRACK = np.array([239, 197, 119.0])
CRACK_GLOW = np.array([226, 140, 52.0])
WHITE = (254, 254, 254)
LAVENDER = (251, 225, 254)
PURPLE = (185, 156, 214)
PURPLE_DEEP = (150, 105, 225)
CYAN = (224, 253, 253)
PINK = (251, 115, 161)
PINK_LIGHT = (253, 172, 240)
PINK_OUT = (163, 90, 119)


def ramp(v, stops):
    v = np.clip(v, 0, 1)
    out = np.zeros(v.shape + (3,))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (v >= a) & (v <= b)
        t = ((v - a) / (b - a))[m][:, None]
        out[m] = np.array(ca) * (1 - t) + np.array(cb) * t
    return out


def to_img(rgb, a):
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8), "RGBA")


# ------------------------------------------------------------------ ruido 3D
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(P, seed=0):
    """Ruido de valor 3D suave (P: ...x3)."""
    i = np.floor(P).astype(np.int64)
    f = P - i
    u = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((u[..., 0] if dx else 1 - u[..., 0]) * (u[..., 1] if dy else 1 - u[..., 1])
                     * (u[..., 2] if dz else 1 - u[..., 2]))
                out = out + w * _hash(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def fbm(P, octaves=4, seed=0):
    s, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + a * vnoise(P * (2 ** o), seed + o * 17)
        tot += a
        a *= 0.5
    return s / tot


# ------------------------------------------------------------------ estrella en 3D
rng = np.random.default_rng(5)
NSITES = 120
# puntos al azar (placas de tamaños distintos), separados un mínimo para que no haya placas diminutas
_pts = []
while len(_pts) < NSITES:
    v = rng.normal(size=3)
    v /= np.linalg.norm(v)
    if all(np.dot(v, q) < 0.978 for q in _pts):
        _pts.append(v)
SITES = np.array(_pts)
CELL_TONE = rng.uniform(0.82, 1.18, NSITES)
HOT = np.zeros(NSITES)
HOT[rng.choice(NSITES, 7, replace=False)] = rng.uniform(0.45, 0.8, 7)    # placas fundidas
AXIS = np.array([0.22, 1.0, 0.12])
AXIS /= np.linalg.norm(AXIS)
LIGHT = np.array([-0.45, 0.55, 0.7])
LIGHT /= np.linalg.norm(LIGHT)


def rot_axis(v, ang):
    """Gira los vectores v alrededor de AXIS (Rodrigues)."""
    c, s = math.cos(ang), math.sin(ang)
    kx = AXIS
    return v * c + np.cross(kx, v) * s + np.outer(v @ kx, kx) * (1 - c)


def render_star(size, frame, frames=64):
    t = 2 * math.pi * frame / frames
    R = size / 2 * 0.97
    yy, xx = np.mgrid[0:size, 0:size]
    x = (xx + 0.5 - size / 2) / R
    y = -(yy + 0.5 - size / 2) / R
    rr = x * x + y * y
    inside = rr < 1
    alpha = np.clip((1 - np.sqrt(rr)) * R + 0.5, 0, 1)
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    n = np.stack([x[inside], y[inside], z[inside]], -1)
    p = rot_axis(n, -t)                                   # punto de la superficie en la bola
    # deformar un poco el espacio para que las grietas sean onduladas, no rectas
    warp = np.stack([fbm(p * 4 + 10, 3, 61), fbm(p * 4 + 20, 3, 67), fbm(p * 4 + 30, 3, 71)], -1) - 0.5
    pw = p + warp * 0.16
    pw /= np.linalg.norm(pw, axis=1, keepdims=True)
    dots = pw @ SITES.T
    idx = np.argsort(-dots, axis=1)[:, :2]
    d1 = np.sqrt(np.maximum(0, 2 - 2 * np.take_along_axis(dots, idx[:, :1], 1)[:, 0]))
    d2 = np.sqrt(np.maximum(0, 2 - 2 * np.take_along_axis(dots, idx[:, 1:], 1)[:, 0]))
    cell = idx[:, 0]
    e = (d2 - d1) / 2                                     # distancia a la grieta
    wobble = fbm(p * 7, 2, 3)
    width = 0.006 + 0.02 * wobble ** 2                    # grietas de grosor variable
    core = np.clip(1 - e / width, 0, 1) ** 0.7
    glow = np.exp(-e / (0.022 + 0.03 * wobble))
    # roca: textura "peluda" + tono por placa
    tex = fbm(p * 6, 4, 11) * 0.5 + fbm(p * 30, 3, 29) * 0.5
    tone = np.clip((tex - 0.22) / 0.5, 0, 1) * CELL_TONE[cell]
    rock = ramp(np.clip(tone, 0, 1), ROCK)
    shade = 0.5 + 0.65 * np.clip(n @ LIGHT, 0, 1)
    rock *= shade[:, None]
    # lava que late: ruido que se mueve en bucle con el tiempo
    flow = fbm(p * 3.2 + np.array([math.cos(t) * 1.3, math.sin(t) * 1.3, 0.0]), 3, 41)
    pulse = 0.7 + 0.6 * flow
    hot = HOT[cell] * (0.6 + 0.4 * fbm(p * 5 + np.array([0, math.cos(t), math.sin(t)]), 2, 53))
    g = glow * (1 - core)
    emis = core[:, None] * (CRACK_CORE * 0.6 + CRACK * 0.4) + g[:, None] * (CRACK * 0.5 + CRACK_GLOW * 0.5)
    emis = emis * pulse[:, None] + hot[:, None] * CRACK_GLOW * (0.5 + 0.5 * glow[:, None])
    mix = np.clip(core + g * 0.75 + hot * 0.9, 0, 1)[:, None]
    col = rock * (1 - mix) + emis * np.clip(mix * 1.2, 0, 1)
    # borde caliente (como si brillara por dentro)
    rim = (1 - n[:, 2]) ** 4
    col += rim[:, None] * np.array([220, 110, 40]) * 0.35
    img = np.zeros((size, size, 3))
    img[inside] = col
    return to_img(img, alpha * inside)


def make_star():
    frames = 64
    atlas = Image.new("RGBA", (2048, 2048))
    for f in range(frames):
        atlas.paste(render_star(256, f, frames), ((f % 8) * 256, (f // 8) * 256))
    atlas.save(OUT / "estrella_giro.png")
    render_star(512, 0, frames).save(OUT / "estrella.png")


def radial(size, stops, falloff):
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx + 0.5 - size / 2, yy + 0.5 - size / 2) / (size / 2)
    return r, ramp(r, stops), falloff(r)


def make_glows():
    r, col, a = radial(256, [(0, (255, 200, 110)), (0.4, (245, 140, 50)), (1, (200, 70, 20))],
                       lambda r: np.clip(1 - r, 0, 1) ** 2.2)
    to_img(col, a).save(OUT / "halo.png")
    r, col, a = radial(64, [(0, (255, 255, 240)), (0.35, (255, 220, 140)), (1, (255, 140, 60))],
                       lambda r: np.clip(1 - r, 0, 1) ** 1.8)
    to_img(col, a).save(OUT / "brasa.png")
    r, col, a = radial(256, [(0, WHITE), (0.5, LAVENDER), (1, PINK_LIGHT)],
                       lambda r: np.clip(1 - r, 0, 1) ** 1.5)
    to_img(col, a).save(OUT / "exp_nucleo.png")
    # núcleo que brilla mientras se forma la estrella (colores de las grietas)
    r, col, a = radial(256, [(0, tuple(CRACK_CORE)), (0.45, tuple(CRACK)), (1, tuple(CRACK_GLOW))],
                       lambda r: np.clip(1 - r, 0, 1) ** 1.6)
    to_img(col, a).save(OUT / "nucleo.png")


# ------------------------------------------------------------------ explosión
def make_body():
    """Cuerpo de la explosión: blanco con el centro lavanda, manchas celestes y rosas y el borde
    rosa ondulado (como en la captura 2). 4 fotogramas para que el borde se mueva."""
    S = 512
    yy, xx = np.mgrid[0:S, 0:S]
    X = (xx + 0.5 - S / 2) / (S / 2)
    Y = (yy + 0.5 - S / 2) / (S / 2)
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    atlas = Image.new("RGBA", (1024, 1024))
    for f in range(4):
        t = 2 * math.pi * f / 4
        P = np.stack([np.cos(th) * 1.6 + math.cos(t) * 0.5, np.sin(th) * 1.6 + math.sin(t) * 0.5,
                      np.full_like(th, 0.3)], -1)
        edge = 0.80 + 0.07 * (fbm(P, 3, 7) - 0.5) * 2          # borde ondulado
        q = r / edge
        col = ramp(q, [(0, LAVENDER), (0.3, (252, 238, 255)), (0.45, WHITE), (0.84, WHITE),
                       (0.93, PINK_LIGHT), (1.0, PINK), (1.12, PINK_OUT)])
        blot = fbm(np.stack([X * 3 + math.cos(t), Y * 3 + math.sin(t), np.full_like(X, 2.0)], -1), 3, 19)
        cy_ = np.clip((blot - 0.55) * 4, 0, 1) * np.clip(1 - np.abs(q - 0.55) / 0.3, 0, 1)
        col = col * (1 - 0.6 * cy_[..., None]) + np.array(CYAN) * 0.6 * cy_[..., None]
        pk = np.clip((0.45 - blot) * 4, 0, 1) * np.clip(1 - np.abs(q - 0.75) / 0.15, 0, 1)
        col = col * (1 - 0.5 * pk[..., None]) + np.array(PINK_LIGHT) * 0.5 * pk[..., None]
        a = np.clip((1.16 - q) / 0.16, 0, 1)
        atlas.paste(to_img(col, a), ((f % 2) * 512, (f // 2) * 512))
    atlas.save(OUT / "exp_cuerpo.png")


def make_rays():
    """Rayos de luz (celestes y lavanda) que salen del centro."""
    S = 512
    yy, xx = np.mgrid[0:S, 0:S]
    X = (xx + 0.5 - S / 2) / (S / 2)
    Y = (yy + 0.5 - S / 2) / (S / 2)
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    rs = np.random.default_rng(3)
    a = np.zeros((S, S))
    hue = np.zeros((S, S))
    for _ in range(46):
        ang = rs.uniform(-math.pi, math.pi)
        width = rs.uniform(0.012, 0.05)
        length = rs.uniform(0.55, 1.0)
        d = np.abs(np.angle(np.exp(1j * (th - ang))))
        ray = np.exp(-(d / width) ** 2) * np.clip(1 - r / length, 0, 1) ** 0.8 * np.clip(r / 0.08, 0, 1)
        a = np.maximum(a, ray * rs.uniform(0.5, 1.0))
        hue = np.where(ray > 0.05, rs.random(), hue)
    col = np.where(hue[..., None] < 0.55, np.array(CYAN), np.array(LAVENDER)).astype(float)
    to_img(col, a).save(OUT / "exp_rayos.png")


def bolt_frame(seed, S=512):
    rs = random.Random(seed)
    big = S * 2
    layer = Image.new("L", (big, big))
    d = ImageDraw.Draw(layer)
    c = big / 2

    def branch(x, y, ang, length, width, depth):
        steps = max(4, int(length / 14))
        for _ in range(steps):
            ang += rs.uniform(-0.55, 0.55)
            nx, ny = x + math.cos(ang) * length / steps, y + math.sin(ang) * length / steps
            d.line([(x, y), (nx, ny)], fill=255, width=max(1, int(width)))
            if depth < 2 and rs.random() < 0.28:
                branch(nx, ny, ang + rs.choice([-1, 1]) * rs.uniform(0.4, 1.0),
                       length * rs.uniform(0.25, 0.5), width * 0.6, depth + 1)
            x, y = nx, ny
            width *= 0.9

    for _ in range(16):
        a = rs.uniform(0, 2 * math.pi)
        if rs.random() < 0.45:                       # más hacia arriba, como en la captura
            a = -math.pi / 2 + rs.uniform(-1.2, 1.2)
        r0 = rs.uniform(0.02, 0.1) * big / 2
        branch(c + math.cos(a) * r0, c + math.sin(a) * r0, a, rs.uniform(0.3, 0.62) * big / 2, 7, 0)
    line = np.array(layer.resize((S, S), Image.LANCZOS)).astype(float) / 255
    glow = gaussian_filter(line, 5)
    glow = np.clip(glow / max(glow.max(), 1e-6) * 1.8, 0, 1)
    a = np.clip(line * 1.2 + glow * 0.75, 0, 1)
    col = (np.array(PURPLE_DEEP) * (1 - line[..., None]) + np.array((230, 215, 255)) * line[..., None]) * 0.6 \
        + np.array(PURPLE) * 0.4
    return to_img(col, a)


def make_bolts():
    atlas = Image.new("RGBA", (2048, 2048))
    for f in range(16):
        atlas.paste(bolt_frame(200 + f), ((f % 4) * 512, (f // 4) * 512))
    atlas.save(OUT / "exp_morados.png")


def make_ring():
    S = 512
    yy, xx = np.mgrid[0:S, 0:S]
    r = np.hypot(xx + 0.5 - S / 2, yy + 0.5 - S / 2) / (S / 2)
    ring = np.exp(-((r - 0.86) / 0.05) ** 2)
    inner = np.exp(-((r - 0.83) / 0.012) ** 2) * 0.8
    a = np.clip(ring + inner, 0, 1) * (r < 1)
    col = np.array(PINK, float) * (1 - inner[..., None]) + np.array(WHITE) * inner[..., None]
    to_img(col, a).save(OUT / "exp_anillo.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_glows()
    make_body()
    make_rays()
    make_bolts()
    make_ring()
    print("ok:", OUT)
