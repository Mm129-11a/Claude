"""Crea preview.gif juntando las capas igual que el juego (con un nombre y causa de ejemplo)."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import extract_from_video as ex

ROOT = Path(__file__).resolve().parent.parent
tex = ROOT / "DeathAnimation_RP" / "textures" / "ui" / "death_anim"
intro = np.array(Image.open(tex / "intro.png"))
ni = intro.shape[0] // ex.SH
ch = ex.CY1 - ex.CY0
n_frames = len(range(ex.FIRST, ex.LAST + 1, ex.STEP))
crs = [np.array(Image.open(tex / f"creature_{k}.png")) for k in range(-(-n_frames // ex.FRAMES_PER_TEXTURE))]

frames = []
for n in range(n_frames):
    c = Image.new("RGBA", (ex.SW, ex.SH), (112, 146, 190, 255))       # cielo de fondo
    ImageDraw.Draw(c).rectangle([0, 250, ex.SW, ex.SH], fill=(96, 140, 60, 255))
    li = min(n, ni - 1)
    c.alpha_composite(Image.fromarray(intro[li * ex.SH:(li + 1) * ex.SH]))
    k, j = divmod(n, ex.FRAMES_PER_TEXTURE)
    c.alpha_composite(Image.fromarray(crs[k][j * ch:(j + 1) * ch]), (ex.CX0, ex.CY0))
    t = n / 15
    if 0.35 < t < 8.6:
        d = ImageDraw.Draw(c)
        y = ex.CY1 - 14
        for txt, col, dy in (("Steve", (255, 85, 85), 0), ("intentó nadar en lava", (255, 255, 255), 16)):
            w = d.textlength(txt)
            d.text(((ex.SW - w) / 2 + 1, y + dy + 1), txt, fill=(40, 40, 40))
            d.text(((ex.SW - w) / 2, y + dy), txt, fill=col)
    frames.append(c.convert("RGB"))
frames[0].save(ROOT / "preview.gif", save_all=True, append_images=frames[1:], duration=67, loop=0)
print("preview.gif ok")
