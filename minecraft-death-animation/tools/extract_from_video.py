"""Saca la animación de muerte directamente del video de referencia (pantalla verde).

Uso:  python3 tools/extract_from_video.py ruta/al/video.mp4

No redibuja nada: toma los fotogramas del video, quita el fondo verde y la marca de
agua de TikTok, y los guarda como texturas del paquete de recursos:

  textures/ui/death_anim/intro.png        rayos y destellos (franja completa, fotogramas 5-23)
  textures/ui/death_anim/creature_0..6.png la criatura a resolución original (fotogramas 5-269, 7 texturas)
  sounds/death_anim/death.ogg             el audio del efecto

La animación original va a ~15 fps (el video repite cada fotograma), así que se toma
uno de cada dos fotogramas del video de 30 fps.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RP = ROOT / "DeathAnimation_RP"
TEX = RP / "textures" / "ui" / "death_anim"
SND = RP / "sounds" / "death_anim"

# Franja del video (576x1024) donde está el efecto
STRIP_Y0, STRIP_Y1 = 352, 672
SW, SH = 576, STRIP_Y1 - STRIP_Y0
# Fotogramas del efecto en el video (30 fps) y paso para quedar a 15 fps
FIRST, LAST, STEP = 5, 269, 2
INTRO_LAST = 24                      # después de este fotograma ya no hay rayos
# Recuadro de la criatura dentro de la franja (incluye el glitch final)
CX0, CY0, CX1, CY1 = 150, 58, 434, 268
FRAMES_PER_TEXTURE = 19              # 19 x 210 px = 3990 px de alto (< 4096)
# Marca de agua de TikTok (dentro de la franja)
WM = (5, 112, 151, 208)
AUDIO_START, AUDIO_END = 0.2, 9.05


def key_green(rgb):
    """RGB uint8 (H,W,3) -> RGBA con el verde transparente y sin halo verde."""
    f = rgb.astype(np.int32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    k = g - np.maximum(r, b)                       # cuánto "verde puro" tiene
    alpha = np.clip((90 - k) * 255 // 60, 0, 255)  # k>=90 transparente, k<=30 opaco
    g2 = np.minimum(g, np.maximum(r, b) + 10)      # quita el reflejo verde en los bordes
    out = np.stack([r, np.where(alpha < 255, g2, g), b, alpha], axis=-1)
    return out.clip(0, 255).astype(np.uint8)


def box_sum(a, r):
    """Suma de cada ventana (2r+1)x(2r+1) alrededor de cada píxel."""
    p = np.pad(a, ((r + 1, r), (r + 1, r)))
    c = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]


def main(video):
    tmp = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(video),
                        "-vf", f"crop={SW}:{SH}:0:{STRIP_Y0}", str(tmp / "f%04d.png")],
                       check=True)

        def frame(i):  # i = índice 0-based del video
            return np.array(Image.open(tmp / f"f{i + 1:04d}.png").convert("RGB"))

        # Máscara de la marca de agua: lo que no es verde en un fotograma sin efecto
        ref = key_green(frame(1))
        mask = np.zeros((SH, SW), bool)
        x0, y0, x1, y1 = WM
        mask[y0:y1, x0:x1] = ref[y0:y1, x0:x1, 3] > 0
        # ensanchar 4 px para no dejar bordes
        for _ in range(4):
            m = mask.copy()
            m[1:] |= mask[:-1]; m[:-1] |= mask[1:]
            m[:, 1:] |= mask[:, :-1]; m[:, :-1] |= mask[:, 1:]
            mask = m

        def clean(i):
            rgba = key_green(frame(i))
            # tapa la marca de agua con el fondo de esa misma fila (verde, rojo o negro)
            # Dentro del recuadro solo se conservan los rayos (blanco puro fuera de las letras).
            # El fondo es el color más común del fotograma (transparente, rojo o negro).
            colors, counts = np.unique(rgba[::4, ::4].reshape(-1, 4), axis=0, return_counts=True)
            bg = colors[counts.argmax()]
            x0, y0, x1, y1 = WM
            region = rgba[y0:y1, x0:x1]
            letters = mask[y0:y1, x0:x1]
            bolt = (region[..., :3].min(axis=2) > 200) & ~letters
            # donde las letras tapaban un rayo, se rellena con blanco si alrededor hay rayo
            known = (~letters).astype(float)
            near_bolt = box_sum(bolt.astype(float), 6) / np.maximum(box_sum(known, 6), 1)
            # o si en la misma columna hay rayo justo encima y justo debajo (sombra de las letras)
            def between(white, reach):
                h, w = white.shape
                up, down = np.zeros_like(white), np.zeros_like(white)
                left, right = np.zeros_like(white), np.zeros_like(white)
                for d in range(1, reach + 1):
                    up[d:] |= white[:h - d]
                    down[:h - d] |= white[d:]
                    left[:, d:] |= white[:, :w - d]
                    right[:, :w - d] |= white[:, d:]
                return (up & down) | (left & right)

            fill_white = (letters & (near_bolt > 0.5)) | (~bolt & between(bolt, 8))
            # segunda pasada: cierra huecos de 1-2 px que quedan entre lo ya rellenado
            fill_white |= between(bolt | fill_white, 3)
            fill_white &= ~bolt
            region[~bolt] = bg
            region[fill_white] = (255, 255, 255, 255)
            return rgba

        indices = list(range(FIRST, LAST + 1, STEP))
        TEX.mkdir(parents=True, exist_ok=True)
        for old in TEX.glob("*.png"):
            old.unlink()

        # Capa 1: franja completa sin la zona de la criatura (se dibuja en la capa 2)
        intro = []
        for i in [n for n in indices if n <= INTRO_LAST]:
            rgba = clean(i)
            rgba[CY0:CY1, CX0:CX1] = 0
            intro.append(rgba)
        intro.append(np.zeros_like(intro[0]))      # último fotograma vacío
        Image.fromarray(np.concatenate(intro)).save(TEX / "intro.png", optimize=True)

        # Capa 2: la criatura a resolución original, repartida en varias texturas
        crops = [clean(i)[CY0:CY1, CX0:CX1] for i in indices]
        chunks = [crops[k:k + FRAMES_PER_TEXTURE]
                  for k in range(0, len(crops), FRAMES_PER_TEXTURE)]
        for n, chunk in enumerate(chunks):
            Image.fromarray(np.concatenate(chunk)).save(TEX / f"creature_{n}.png", optimize=True)

        # Sonido del efecto
        SND.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(AUDIO_START),
                        "-to", str(AUDIO_END), "-i", str(video), "-vn", "-ac", "1",
                        "-c:a", "libvorbis", "-q:a", "5", str(SND / "death.ogg")], check=True)

        print(f"intro: {len(intro)} fotogramas | criatura: {len(crops)} fotogramas en "
              f"{len(chunks)} texturas ({[len(c) for c in chunks]})")
        return intro, chunks
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 tools/extract_from_video.py video.mp4")
    main(Path(sys.argv[1]))
