"""Genera el Huevo Eburia para Blockbench, copiado de la foto de referencia.

Uso:  python3 tools/make_model.py

La textura está leída de la foto píxel por píxel: cada cara se enderezó, se le quitó el
degradado de luz de la cueva y se le puso encima una cuadrícula de 8x8 (cubo grande) y
5x5 (cubo chico) para ver dónde cae cada mancha azul y cada zona tostada.
Las dos caras visibles del cubo grande tienen exactamente el mismo dibujo, así que todas
sus caras usan esa textura; lo mismo con el cubo chico.

Crea:
  huevo_eburia.bbmodel     proyecto de Blockbench (Bedrock, con la textura incluida)
  huevo_eburia.png         textura 16x16 (1 píxel = 1 unidad, como en Minecraft)
  huevo_eburia.geo.json    geometría de Bedrock lista para un addon
"""
import base64
import io
import json
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TEX = 16

# Colores (los de la foto, con la luz de la cueva corregida)
PALETTE = {
    "L": (232, 224, 210),   # crema claro
    "C": (222, 208, 188),   # crema
    "T": (204, 178, 146),   # tostado
    "D": (186, 156, 122),   # tostado oscuro
    "B": (80, 180, 225),    # mancha azul
    "R": (122, 50, 32),     # raíz
    "r": (100, 38, 26),     # raíz oscura
}

# Cubo grande, 8x8 (fila 0 = arriba de la cara)
BIG = [
    "TTCCCCLL",
    "TCCCCCBL",
    "CCBCCTCL",
    "TTTTDDTC",
    "CCCCCCLL",
    "CCCLCBLL",
    "CBCCLLLL",
    "CTCCLLLL",
]
# Cubo chico, 5x5
SMALL = [
    "CCCDT",
    "CBCTT",
    "CTTTT",
    "LLCCC",
    "LLCBC",
]
ROOTS = ["Rr", "rR"]

# Zonas de la textura (x0, y0, x1, y1)
UV_BIG = [0, 0, 8, 8]
UV_SMALL = [8, 0, 13, 5]
UV_ROOT = [13, 0, 15, 2]

# Piezas: nombre, desde, hasta, UV de arriba/abajo, UV de los lados
PIECES = [
    ("huevo_grande", (-7, 3, -6), (1, 11, 2), UV_BIG, UV_BIG),
    ("huevo_chico", (-1, 2, 1), (4, 7, 6), UV_SMALL, UV_SMALL),
    ("raiz_1", (-7, 0, 0), (-6, 3, 1), UV_ROOT, UV_ROOT),
    ("raiz_1_pie", (-8, 0, 0), (-7, 1, 1), UV_ROOT, UV_ROOT),
    ("raiz_2", (-5, 0, 1), (-4, 3, 2), UV_ROOT, UV_ROOT),
    ("raiz_2_pie", (-5, 0, 2), (-4, 1, 3), UV_ROOT, UV_ROOT),
    ("raiz_3", (-1, 0, 5), (0, 2, 6), UV_ROOT, UV_ROOT),
    ("raiz_3_pie", (-2, 0, 5), (-1, 1, 6), UV_ROOT, UV_ROOT),
    ("raiz_4", (3, 0, 5), (4, 2, 6), UV_ROOT, UV_ROOT),
    ("raiz_4_pie", (3, 0, 6), (4, 1, 7), UV_ROOT, UV_ROOT),
    ("raiz_5", (-7, 0, -6), (-6, 3, -5), UV_ROOT, UV_ROOT),
    ("raiz_5_pie", (-8, 0, -6), (-7, 1, -5), UV_ROOT, UV_ROOT),
]


def build_texture():
    img = Image.new("RGBA", (TEX, TEX), (0, 0, 0, 0))
    px = img.load()
    for rows, (x0, y0, _, _) in ((BIG, UV_BIG), (SMALL, UV_SMALL), (ROOTS, UV_ROOT)):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                px[x0 + i, y0 + j] = PALETTE[ch] + (255,)
    return img


def faces_uv(top, side):
    return {"north": side, "south": side, "east": side, "west": side, "up": top, "down": top}


def bbmodel(tex_png):
    elements, ids = [], []
    for name, a, b, top, side in PIECES:
        eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia." + name))
        elements.append({
            "name": name, "box_uv": False, "rescale": False, "locked": False,
            "render_order": "default", "allow_mirror_modeling": True,
            "from": list(a), "to": list(b), "autouv": 0, "color": 0,
            "origin": [(a[i] + b[i]) / 2 for i in range(3)], "rotation": [0, 0, 0],
            "faces": {f: {"uv": list(uv), "texture": 0} for f, uv in faces_uv(top, side).items()},
            "type": "cube", "uuid": eid,
        })
        ids.append(eid)
    return {
        "meta": {"format_version": "4.10", "model_format": "bedrock_block", "box_uv": False},
        "name": "huevo_eburia", "model_identifier": "huevo_eburia",
        "visible_box": [1, 1, 0], "variable_placeholders": "", "variable_placeholder_buttons": [],
        "timeline_setups": [], "unhandled_root_fields": {},
        "resolution": {"width": TEX, "height": TEX},
        "elements": elements,
        "outliner": [{
            "name": "huevo_eburia", "origin": [0, 0, 0], "color": 0,
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia.group")), "export": True,
            "mirror_uv": False, "isOpen": True, "locked": False, "visibility": True,
            "autouv": 0, "children": ids,
        }],
        "textures": [{
            "path": "", "name": "huevo_eburia.png", "folder": "block", "namespace": "",
            "id": "0", "group": "", "width": TEX, "height": TEX, "uv_width": TEX, "uv_height": TEX,
            "particle": False, "use_as_default": False, "layers_enabled": False,
            "sync_to_project": "", "render_mode": "default", "render_sides": "auto",
            "frame_time": 1, "frame_order_type": "loop", "frame_order": "",
            "frame_interpolate": False, "visible": True, "internal": True, "saved": True,
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia.texture")),
            "relative_path": "huevo_eburia.png",
            "source": "data:image/png;base64," + base64.b64encode(tex_png).decode(),
        }],
    }


def geo_json():
    cubes = []
    for name, a, b, top, side in PIECES:
        size = [b[i] - a[i] for i in range(3)]
        uv = {f: {"uv": [r[0], r[1]], "uv_size": [r[2] - r[0], r[3] - r[1]]}
              for f, r in faces_uv(top, side).items()}
        cubes.append({"origin": [-b[0], a[1], a[2]], "size": size, "uv": uv})
    return {
        "format_version": "1.16.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.huevo_eburia",
                            "texture_width": TEX, "texture_height": TEX,
                            "visible_bounds_width": 2, "visible_bounds_height": 2,
                            "visible_bounds_offset": [0, 0.5, 0]},
            "bones": [{"name": "huevo_eburia", "pivot": [0, 0, 0], "cubes": cubes}],
        }],
    }


if __name__ == "__main__":
    tex = build_texture()
    buf = io.BytesIO(); tex.save(buf, "PNG")
    tex.save(ROOT / "huevo_eburia.png")
    (ROOT / "huevo_eburia.bbmodel").write_text(json.dumps(bbmodel(buf.getvalue()), indent=1))
    (ROOT / "huevo_eburia.geo.json").write_text(json.dumps(geo_json(), indent=2) + "\n")
    print("ok")
