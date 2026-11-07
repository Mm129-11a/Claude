"""Genera el Huevo Eburia para Blockbench a partir de lo medido en la foto de referencia.

Uso:  python3 tools/make_model.py

Usa lo que sacó tools/extract_from_photo.py de la foto:
  fuente/textura_grande.png   textura 16x16 del cubo grande (la misma en todas sus caras)
  fuente/textura_chica.png    textura 11x11 del cubo chico
  fuente/camara_foto.json     cámara de la foto y posición/tamaño del cubo chico

Crea:
  huevo_eburia.bbmodel     proyecto de Blockbench (Bedrock, con la textura incluida)
  huevo_eburia.png         textura 32x32
  huevo_eburia.geo.json    geometría de Bedrock lista para un addon
"""
import base64
import io
import json
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "fuente"
TEX = 32

# Colores de las ramitas (los de la foto, con la luz corregida)
TWIG = [(122, 50, 26), (134, 58, 30), (108, 44, 22), (146, 64, 34)]

UV_BIG = [0, 0, 16, 16]
UV_SMALL = [16, 0, 27, 11]
UV_TWIG = [27, 0, 29, 2]

# Medidas en el sistema de la foto: cubo grande [0,16]^3, la base de los cubos en y=0.
cam = json.loads((SRC / "camara_foto.json").read_text())
SX, SY, SZ, SS = cam["small"]          # cubo chico: esquina mínima y lado (11)

# Ramitas del rabito: como en la foto, salen de la parte de abajo del extremo chico y quedan
# sobre el suelo, hacia afuera y hacia atrás (cajas desde-hasta, sistema de la foto)
X_END = SX + SS                         # cara del extremo chico
TWIGS = [
    ("rabito", (X_END - 1, 1, 2), (X_END + 4, 4, 5)),
    ("ramita_1", (X_END + 3, 1, -1), (X_END + 5, 3, 2)),
    ("ramita_1_punta", (X_END + 4, 0, -4), (X_END + 6, 2, -1)),
    ("ramita_2", (X_END + 4, 2, 2), (X_END + 8, 4, 4)),
    ("ramita_2_punta", (X_END + 7, 3, 1), (X_END + 9, 6, 3)),
    ("ramita_3", (X_END + 2, 0, 5), (X_END + 4, 2, 8)),
    ("ramita_3_punta", (X_END + 3, 0, 8), (X_END + 6, 1, 9)),
]

# Del sistema de la foto al de Blockbench: centrado en X/Z y apoyado en el suelo (y=0)
_xs = [p[0] for _, a, b in TWIGS for p in (a, b)] + [0, X_END]
OFFSET = (-round((min(_xs) + max(_xs)) / 2), 0, -8)

PIECES = [("huevo_grande", (0, 0, 0), (16, 16, 16), UV_BIG),
          ("huevo_chico", (SX, SY, SZ), (SX + SS, SY + SS, SZ + SS), UV_SMALL)]
PIECES += [(n, a, b, UV_TWIG) for n, a, b in TWIGS]


def to_bb(p):
    return [p[i] + OFFSET[i] for i in range(3)]


def build_texture():
    img = Image.new("RGBA", (TEX, TEX), (0, 0, 0, 0))
    img.paste(Image.open(SRC / "textura_grande.png").convert("RGBA"), tuple(UV_BIG[:2]))
    img.paste(Image.open(SRC / "textura_chica.png").convert("RGBA"), tuple(UV_SMALL[:2]))
    px = img.load()
    x0, y0 = UV_TWIG[:2]
    for k, c in enumerate(TWIG):
        px[x0 + k % 2, y0 + k // 2] = c + (255,)
    return img


FACES = ("north", "south", "east", "west", "up", "down")


def bbmodel(tex_png):
    elements, ids = [], []
    for name, a, b, uv in PIECES:
        eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "eburia." + name))
        fa, fb = to_bb(a), to_bb(b)
        elements.append({
            "name": name, "box_uv": False, "rescale": False, "locked": False,
            "render_order": "default", "allow_mirror_modeling": True,
            "from": fa, "to": fb, "autouv": 0, "color": 0,
            "origin": [(fa[i] + fb[i]) / 2 for i in range(3)], "rotation": [0, 0, 0],
            "faces": {f: {"uv": list(uv), "texture": 0} for f in FACES},
            "type": "cube", "uuid": eid,
        })
        ids.append(eid)
    return {
        "meta": {"format_version": "4.10", "model_format": "bedrock", "box_uv": False},
        "name": "huevo_eburia", "model_identifier": "huevo_eburia",
        "visible_box": [2, 2, 0.5], "variable_placeholders": "", "variable_placeholder_buttons": [],
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
            "path": "", "name": "huevo_eburia.png", "folder": "entity", "namespace": "",
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
    for name, a, b, uv in PIECES:
        fa, fb = to_bb(a), to_bb(b)
        size = [fb[i] - fa[i] for i in range(3)]
        faces = {f: {"uv": [uv[0], uv[1]], "uv_size": [uv[2] - uv[0], uv[3] - uv[1]]} for f in FACES}
        cubes.append({"origin": [-fb[0], fa[1], fa[2]], "size": size, "uv": faces})
    return {
        "format_version": "1.16.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.huevo_eburia",
                            "texture_width": TEX, "texture_height": TEX,
                            "visible_bounds_width": 3, "visible_bounds_height": 2.5,
                            "visible_bounds_offset": [0, 1, 0]},
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
