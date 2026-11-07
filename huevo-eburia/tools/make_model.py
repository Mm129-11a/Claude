"""Genera el modelo del Huevo Eburia para Blockbench.

Uso:  python3 tools/make_model.py
Crea:
  huevo_eburia.bbmodel     proyecto de Blockbench (Bedrock, con la textura incluida)
  huevo_eburia.png         textura 64x64
  huevo_eburia.geo.json    geometría de Bedrock lista para un addon
"""
import base64
import io
import json
import math
import random
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TEX = 64

# Colores
CREAM = [(222, 210, 190), (214, 200, 178), (230, 220, 202), (205, 190, 166)]
TAN = (196, 170, 136)
SPOT = (88, 178, 222)
SPOT_D = (60, 146, 196)
SPOT_L = (130, 206, 236)
ROOT_C = [(122, 46, 34), (140, 58, 40), (104, 38, 30), (158, 72, 48)]

# Piezas: nombre, tamaño (w,h,d), posición mínima (x,y,z), rotación (x,y,z), uv, tipo
# Coordenadas de Blockbench (Bedrock): el bloque va de -8 a 8 en X/Z y de 0 a 16 en Y.
PIECES = [
    ("huevo_grande", (9, 9, 9), (-7, 5, -5), (0, 15, 8), (0, 0), "egg"),
    ("huevo_chico", (7, 7, 7), (0, 3, -1), (0, -20, -6), (0, 18), "egg"),
    ("raiz_1", (2, 7, 2), (-7, 0, -4), (-15, 0, 30), (36, 0), "root"),
    ("raiz_2", (2, 7, 2), (-3, 0, -6), (-30, 0, -10), (36, 0), "root"),
    ("raiz_3", (2, 6, 2), (-2, 0, 3), (30, 0, 15), (36, 0), "root"),
    ("raiz_4", (2, 5, 2), (6, 0, 4), (20, 0, -30), (36, 0), "root"),
]


def box_faces(u, v, w, h, d):
    """Rectángulos UV (x0,y0,x1,y1) de cada cara con Box UV de Blockbench."""
    return {
        # arriba y abajo van invertidos, igual que los calcula Blockbench
        "up": (u + d + w, v + d, u + d, v),
        "down": (u + d + 2 * w, v, u + d + w, v + d),
        "east": (u, v + d, u + d, v + d + h),
        "north": (u + d, v + d, u + d + w, v + d + h),
        "west": (u + d + w, v + d, u + 2 * d + w, v + d + h),
        "south": (u + 2 * d + w, v + d, u + 2 * d + 2 * w, v + d + h),
    }


def paint_texture():
    rng = random.Random(11)
    img = Image.new("RGBA", (TEX, TEX), (0, 0, 0, 0))
    px = img.load()
    done = set()
    for name, (w, h, d), _, _, (u, v), kind in PIECES:
        if (u, v) in done:
            continue
        done.add((u, v))
        for face, (ax, ay, bx, by) in box_faces(u, v, w, h, d).items():
            x0, x1 = sorted((ax, bx))
            y0, y1 = sorted((ay, by))
            fw, fh = x1 - x0, y1 - y0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    pal = CREAM if kind == "egg" else ROOT_C
                    px[x, y] = rng.choice(pal) + (255,)
            if kind == "egg":
                # vetas color tostado, como la textura de la imagen
                for _ in range(max(1, fw * fh // 30)):
                    sx, sy = rng.randrange(x0, x1), rng.randrange(y0, y1)
                    for k in range(rng.randint(2, 4)):
                        if x0 <= sx + k < x1:
                            px[sx + k, sy] = TAN + (255,)
                # manchas azules de 2x2 separadas entre sí
                spots = []
                tries = 0
                want = max(2, fw * fh // 22)
                while len(spots) < want and tries < 200:
                    tries += 1
                    sx = rng.randrange(x0, x1 - 1)
                    sy = rng.randrange(y0, y1 - 1)
                    if any(abs(sx - a) < 3 and abs(sy - b) < 3 for a, b in spots):
                        continue
                    spots.append((sx, sy))
                    px[sx, sy] = SPOT_L + (255,)
                    px[sx + 1, sy] = SPOT + (255,)
                    px[sx, sy + 1] = SPOT + (255,)
                    px[sx + 1, sy + 1] = SPOT_D + (255,)
            else:
                # punta un poco más oscura en las raíces
                for x in range(x0, x1):
                    px[x, y1 - 1] = ROOT_C[2] + (255,)
    return img


def bbmodel(tex_png):
    elements, outliner = [], []
    for name, (w, h, d), (x, y, z), rot, (u, v), _ in PIECES:
        eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia." + name))
        center = [x + w / 2, y + h / 2, z + d / 2]
        faces = {f: {"uv": list(r), "texture": 0}
                 for f, r in box_faces(u, v, w, h, d).items()}
        elements.append({
            "name": name, "box_uv": True, "rescale": False, "locked": False,
            "render_order": "default", "allow_mirror_modeling": True,
            "from": [x, y, z], "to": [x + w, y + h, z + d],
            "autouv": 0, "color": 0, "origin": center, "rotation": list(rot),
            "uv_offset": [u, v], "faces": faces, "type": "cube", "uuid": eid,
        })
        outliner.append(eid)
    group = {
        "name": "huevo_eburia", "origin": [0, 0, 0], "color": 0, "uuid":
        str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia.group")), "export": True,
        "mirror_uv": False, "isOpen": True, "locked": False, "visibility": True,
        "autouv": 0, "children": outliner,
    }
    return {
        "meta": {"format_version": "4.10", "model_format": "bedrock_block", "box_uv": True},
        "name": "huevo_eburia",
        "model_identifier": "huevo_eburia",
        "visible_box": [1, 1, 0],
        "variable_placeholders": "",
        "variable_placeholder_buttons": [],
        "timeline_setups": [],
        "unhandled_root_fields": {},
        "resolution": {"width": TEX, "height": TEX},
        "elements": elements,
        "outliner": [group],
        "textures": [{
            "path": "", "name": "huevo_eburia.png", "folder": "block",
            "namespace": "", "id": "0", "group": "", "width": TEX, "height": TEX,
            "uv_width": TEX, "uv_height": TEX, "particle": False, "use_as_default": False,
            "layers_enabled": False, "sync_to_project": "", "render_mode": "default",
            "render_sides": "auto", "frame_time": 1, "frame_order_type": "loop",
            "frame_order": "", "frame_interpolate": False, "visible": True,
            "internal": True, "saved": True,
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia.texture")),
            "relative_path": "huevo_eburia.png",
            "source": "data:image/png;base64," + base64.b64encode(tex_png).decode(),
        }],
    }


def geo_json():
    """Geometría Bedrock (Blockbench la exporta así: X invertida y origen = esquina)."""
    cubes = []
    for name, (w, h, d), (x, y, z), rot, (u, v), _ in PIECES:
        cubes.append({
            "origin": [-(x + w), y, z], "size": [w, h, d],
            "pivot": [-(x + w / 2), y + h / 2, z + d / 2],
            "rotation": [-rot[0], -rot[1], rot[2]], "uv": [u, v],
        })
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.huevo_eburia",
                            "texture_width": TEX, "texture_height": TEX,
                            "visible_bounds_width": 2, "visible_bounds_height": 2,
                            "visible_bounds_offset": [0, 0.5, 0]},
            "bones": [{"name": "huevo_eburia", "pivot": [0, 0, 0], "cubes": cubes}],
        }],
    }


if __name__ == "__main__":
    tex = paint_texture()
    buf = io.BytesIO()
    tex.save(buf, "PNG")
    tex.save(ROOT / "huevo_eburia.png")
    (ROOT / "huevo_eburia.bbmodel").write_text(json.dumps(bbmodel(buf.getvalue()), indent=1))
    (ROOT / "huevo_eburia.geo.json").write_text(json.dumps(geo_json(), indent=2) + "\n")
    print("ok")
