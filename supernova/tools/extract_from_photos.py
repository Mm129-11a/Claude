"""Saca las texturas de la supernova directamente de las imágenes de referencia.

Uso:
  python3 tools/extract_from_photos.py bola.jpg explosion.jpg destello.jpg

  bola.jpg       la bola de lava en Blockbench (2027x957)
  explosion.jpg  la captura de la explosión (2576x1171)
  destello.jpg   la captura del destello (2576x1171)

Necesita: numpy, pillow, opencv-python-headless

No se dibuja nada a mano: todo se recorta de las imágenes.
  estrella.png   la bola de lava, recortada en redondo y sin el fondo
  explosion.png  la explosión, separada del cielo
  destello.png   el destello de pantalla completa (blanco, bordes rosas y rayas de luz)

Lo que tapan el personaje y los botones se rellena con la misma imagen: en la explosión,
reflejando la parte que sí se ve (es redonda); en el destello, con el resplandor de alrededor.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SupernovaRP" / "textures" / "particle" / "supernova"

# --- medidas (en píxeles de cada imagen) ---
BALL = {"center": (938.64, 635.19), "radius": 194.2}
EXPLOSION = {"center": (1302.75, 451.97), "half": 560}       # borde rosa a ~474-500 px
FLASH = {"center": (1288, 452)}
# Zonas tapadas en las capturas (x0, y0, x1, y1)
UI = [(1140, 0, 1440, 82),        # iconos de arriba
      (185, 440, 590, 850),       # joystick
      (2040, 380, 2480, 1025),    # botones de la derecha
      (720, 1035, 1860, 1171),    # barra de objetos
      (2535, 90, 2576, 300)]      # barra de desplazamiento
PLAYER_EXPLOSION = [(1118, 470, 1482, 1171)]
PLAYER_FLASH = [(1195, 395, 1480, 1171)]


def load(path):
    return np.array(Image.open(path).convert("RGB")).astype(np.float32)


def rect_mask(shape, rects, grow=0):
    m = np.zeros(shape[:2], bool)
    for x0, y0, x1, y1 in rects:
        m[max(0, y0 - grow):y1 + grow, max(0, x0 - grow):x1 + grow] = True
    return m


def crop_square(arr, center, half, fill):
    cx, cy = center
    x0, y0 = int(round(cx - half)), int(round(cy - half))
    size = int(round(2 * half))
    out = np.full((size, size) + arr.shape[2:], fill, arr.dtype)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(arr.shape[1], x0 + size), min(arr.shape[0], y0 + size)
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = arr[sy0:sy1, sx0:sx1]
    return out


def fill_around_center(img, missing):
    """Rellena lo que falta copiando lo que hay justo al lado alrededor del centro: en cada
    distancia al centro, cada hueco se rellena con el reflejo de los ángulos vecinos que sí
    se ven. Así siguen los rayos de la explosión, sin anillos ni líneas rectas."""
    n = img.shape[0]
    c = (n / 2, n / 2)
    maxr = n / 2 * 1.42
    NA = 1440
    P = cv2.warpPolar(img, (n, NA), c, maxr, cv2.WARP_POLAR_LINEAR)
    M = cv2.warpPolar(missing.astype(np.uint8) * 255, (n, NA), c, maxr, cv2.WARP_POLAR_LINEAR) > 0
    for r in range(P.shape[1]):
        bad = M[:, r]
        if not bad.any() or bad.all():
            continue
        # rotar para que el ángulo 0 sea visible y los huecos no den la vuelta
        k0 = int(np.argmin(bad))
        col = np.roll(P[:, r], -k0, axis=0)
        b = np.roll(bad, -k0)
        i = 0
        while i < NA:
            if not b[i]:
                i += 1
                continue
            j = i
            while j < NA and b[j]:
                j += 1
            run = j - i                                  # hueco de i a j-1
            for t in range(run):
                left = (i - 1 - t) % NA                  # reflejo del lado de antes
                right = (j + (run - 1 - t)) % NA         # reflejo del lado de después
                if b[left]:
                    left = (i - 1) % NA
                if b[right]:
                    right = j % NA
                w = (t + 0.5) / run                      # se pasa poco a poco de un lado al otro
                col[i + t] = col[left] * (1 - w) + col[right] * w
            i = j
        P[:, r] = np.roll(col, k0, axis=0)
    back = cv2.warpPolar(P, (n, n), c, maxr, cv2.WARP_POLAR_LINEAR | cv2.WARP_INVERSE_MAP)
    out = img.copy()
    out[missing] = back[missing]
    # borde suave entre lo original y lo rellenado
    soft = cv2.GaussianBlur(missing.astype(np.float32), (0, 0), 2)
    w = np.clip(soft, 0, 1)[..., None]
    out = img * (1 - w) + out * w
    return out


def fill_lines(img, missing):
    """Rellena cada hueco con un degradado entre sus bordes, por filas y por columnas
    (y se hace la media), para que siga el degradado del resplandor de alrededor."""
    def along_rows(a, m):
        out = a.copy()
        has = np.zeros(m.shape, bool)
        xs = np.arange(a.shape[1])
        for y in range(a.shape[0]):
            ok = ~m[y]
            if ok.all() or not ok.any():
                continue
            idx = np.nonzero(ok)[0]
            for ch in range(a.shape[2]):
                out[y, :, ch] = np.where(ok, a[y, :, ch], np.interp(xs, idx, a[y, idx, ch]))
            has[y] = m[y]
        return out, has
    r_img, r_has = along_rows(img, missing)
    c_img, c_has = along_rows(img.transpose(1, 0, 2), missing.T)
    c_img, c_has = c_img.transpose(1, 0, 2), c_has.T
    both = r_has & c_has
    out = img.copy()
    out[both] = (r_img[both] + c_img[both]) / 2
    only_r = r_has & ~c_has
    only_c = c_has & ~r_has
    out[only_r] = r_img[only_r]
    out[only_c] = c_img[only_c]
    # suavizar lo rellenado y fundir su borde
    blurred = cv2.GaussianBlur(out, (0, 0), 10)
    w = np.clip(cv2.GaussianBlur(missing.astype(np.float32), (0, 0), 5), 0, 1)[..., None]
    return img * (1 - w) + blurred * w


def sky_behind(img, hole):
    """El cielo que hay detrás del efecto: el de alrededor, rellenado y suavizado."""
    small = cv2.resize(img, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    hm = cv2.resize(hole.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(np.clip(small, 0, 255).astype(np.uint8), hm, 25, cv2.INPAINT_TELEA).astype(np.float32)
    filled = cv2.GaussianBlur(filled, (0, 0), 8)
    return cv2.resize(filled, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)


def estrella(path, size=512):
    img = load(path)
    cx, cy = BALL["center"]
    R = BALL["radius"]
    half = R / 0.97
    sq = crop_square(img, (cx, cy), half, 0)
    n = sq.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.hypot(xx - n / 2 + .5, yy - n / 2 + .5)
    alpha = np.clip(R - d + 0.5, 0, 1)            # borde redondo y suave de 1 px
    rgba = np.dstack([sq, alpha * 255])
    rgba = cv2.resize(rgba, (size, size), interpolation=cv2.INTER_CUBIC)
    print(f"estrella: bola de radio {R:.0f} px, ocupa el {0.97 * 100:.0f}% de la textura")
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def explosion(path, size=512):
    img = load(path)
    cx, cy = EXPLOSION["center"]
    half = EXPLOSION["half"]
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    r = np.hypot(xx - cx, yy - cy)
    covered = rect_mask(img.shape, UI + PLAYER_EXPLOSION, grow=6)
    B = sky_behind(img, (r < half * 1.05) | covered)
    # separar la luz del cielo: alfa mínimo que deja el color dentro de 0..255
    a = np.clip(np.max((img - B) / np.maximum(255 - B, 1), axis=2), 0, 1)
    F = np.clip(B + (img - B) / np.maximum(a, 1e-3)[..., None], 0, 255)
    a *= np.clip((half - r) / (half * 0.05), 0, 1)
    a[a < 0.05] = 0
    rgba = np.dstack([F, a * 255])
    sq = crop_square(rgba, (cx, cy), half, 0)
    inside = np.ones(img.shape[:2], bool)
    inside[:3] = False                              # la primera fila de la captura no vale
    miss = crop_square(covered, (cx, cy), half, True) | ~crop_square(inside, (cx, cy), half, False)
    sq = fill_around_center(sq, miss)
    # lo que tapa el personaje (debajo del centro): la mitad de arriba de la explosión
    # reflejada, que sí se ve, con 40 px de mezcla en los bordes
    n = sq.shape[0]
    sc = n / (2 * half)
    x0, y0, x1, _ = PLAYER_EXPLOSION[0]
    px0 = (x0 - (cx - half)) * sc
    px1 = (x1 - (cx - half)) * sc
    py0 = (y0 - (cy - half)) * sc
    feather = 40 * sc
    xs = np.arange(n)
    wx = np.clip(np.minimum(xs - (px0 - feather), (px1 + feather) - xs) / feather, 0, 1)
    wy = np.clip((xs - (py0 - feather / 2)) / (feather / 2), 0, 1)
    w = (wy[:, None] * wx[None, :])[..., None]
    sq = sq * (1 - w) + sq[::-1] * w
    sq = cv2.resize(sq, (size, size), interpolation=cv2.INTER_AREA)
    return Image.fromarray(np.clip(sq, 0, 255).astype(np.uint8), "RGBA")


def destello(path, width=1024):
    """El destello ocupa toda la pantalla en la foto: se usa la foto entera hasta el suelo
    (centrada en el destello), quitando el personaje y los botones."""
    img = load(path)
    covered = rect_mask(img.shape, UI + PLAYER_FLASH, grow=10)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    covered |= (r > 150) & (g > 150) & (b < r - 45)          # suelo amarillo
    covered = cv2.dilate(covered.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    fixed = fill_lines(img, covered)
    cy = int(round(FLASH["center"][1]))
    sky = fixed[0:2 * cy]                          # del borde de arriba hasta el suelo
    h, w = sky.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    fx = np.minimum(xx, w - 1 - xx) / (w * 0.07)   # los bordes se funden
    fy = np.minimum(yy, h - 1 - yy) / (h * 0.10)
    alpha = np.clip(np.minimum(fx, fy), 0, 1)
    height = int(round(width * h / w))
    rgba = cv2.resize(np.dstack([sky, alpha * 255]), (width, height), interpolation=cv2.INTER_AREA)
    print(f"destello: {w}x{h} de la foto -> textura {width}x{height}")
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def main(ball, exp, flash):
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    estrella(ball).save(OUT / "estrella.png")
    explosion(exp).save(OUT / "explosion.png")
    destello(flash).save(OUT / "destello.png")
    print("ok:", OUT)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Uso: python3 tools/extract_from_photos.py bola.jpg explosion.jpg destello.jpg")
    main(*sys.argv[1:])
