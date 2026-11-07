"""Genera el modelo del Embestidor (el mob del cubo con el caparazón) para Blockbench y Bedrock.

Uso:  python3 tools/make_mob.py

Crea:
  embestidor.bbmodel                                       proyecto de Blockbench (con textura y animaciones)
  EmbestidorRP/models/entity/embestidor.geo.json           geometría de Bedrock
  EmbestidorRP/textures/entity/embestidor.png              textura
  EmbestidorRP/animations/embestidor.animation.json        animaciones (quieto, andar, embestir)

Todo se diseña en el espacio de Blockbench (16 = 1 bloque, la cara de delante mira a -z) y se
convierte a Bedrock como lo hace Blockbench: x cambiada de signo y giros [-x, -y, z].
"""
import base64
import io
import json
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RP = ROOT / "EmbestidorRP"
TEX_W = TEX_H = 128

# ---------------------------------------------------------------- colores (medidos en la imagen)
BLACK = (14, 14, 14)
BLACK_EDGE = (22, 22, 22)
GREY = (42, 42, 42)
GREY_EDGE = (54, 50, 48)
GREY_DARK = (33, 32, 31)
RING = (170, 163, 155)
RING_LIGHT = (184, 178, 170)
RING_DARK = (142, 136, 130)
RING_SIDE = (128, 123, 117)
PUPIL = (30, 30, 30)
TEAL = (14, 50, 43)
TEAL_LIGHT = (22, 66, 56)
TEAL_DARK = (9, 34, 30)
TEAL_SIDE = (11, 40, 35)
CHANNEL = (6, 6, 6)
PANEL = (20, 20, 20)
PANEL_LIGHT = (28, 28, 28)
RED = (139, 27, 27)
RED_LIGHT = (179, 29, 29)


# ---------------------------------------------------------------- texturas de cada cara
def fill(w, h, c):
    a = np.zeros((h, w, 4), np.uint8)
    a[..., :3] = c
    a[..., 3] = 255
    return a


def rect(a, x0, y0, x1, y1, c):
    a[y0:y1, x0:x1, :3] = c


def body_side(w, h):
    a = fill(w, h, BLACK)
    a[0, :, :3] = BLACK_EDGE
    a[:, 0, :3] = BLACK_EDGE
    return a


def body_top(w, h):
    a = fill(w, h, GREY)
    a[0, :, :3] = GREY_EDGE
    a[:, 0, :3] = GREY_EDGE
    a[-1, :, :3] = GREY_DARK
    a[:, -1, :3] = GREY_DARK
    return a


def body_front(w, h):
    a = fill(w, h, GREY_DARK)
    rect(a, 0, 0, w, 1, GREY_EDGE)
    rect(a, 0, 0, 1, h, GREY_EDGE)
    rect(a, 1, 1, w - 1, h - 1, GREY)
    rect(a, 2, 2, w - 2, h - 2, (36, 34, 33))
    # el hueco del ojo (detrás del aro) y la pupila
    c = w // 2
    rect(a, c - 3, c - 3, c + 3, c + 3, BLACK)
    rect(a, c - 1, c - 1, c + 2, c + 2, PUPIL)
    rect(a, c, c, c + 1, c + 1, (40, 40, 40))
    return a


def ring_face(w, h, light=True):
    a = fill(w, h, RING)
    if light:
        a[0, :, :3] = RING_LIGHT
        a[:, 0, :3] = RING_LIGHT
        a[-1, :, :3] = RING_DARK
        a[:, -1, :3] = RING_DARK
    return a


def shell_top(w, h, open_side="left", slot=None):
    """Cara de fuera del caparazón: borde verde, canal negro en U y panel gris dentro.
    El canal queda abierto por 'open_side' (por donde sigue en la otra parte de la banda)."""
    a = fill(w, h, TEAL)
    rect(a, 0, 0, w, 1, TEAL_LIGHT)
    rect(a, 0, h - 1, w, h, TEAL_DARK)
    rim = 3
    x0 = 0 if open_side == "left" else rim
    x1 = w if open_side == "right" else w - rim
    rect(a, x0, rim, x1, h - rim, CHANNEL)
    p0 = x0 if open_side == "left" else x0 + 2
    p1 = x1 if open_side == "right" else x1 - 2
    rect(a, p0, rim + 2, p1, h - rim - 2, PANEL)
    rect(a, p0, rim + 2, p1, rim + 3, PANEL_LIGHT)
    # escalón de dentro del panel
    q0 = p0 + (0 if open_side == "left" else 2)
    q1 = p1 - (0 if open_side == "right" else 2)
    if q1 - q0 > 2 and h - 2 * rim - 8 > 2:
        rect(a, q0, rim + 4, q1, h - rim - 4, (17, 17, 17))
        rect(a, q0, rim + 4, q1, rim + 5, PANEL_LIGHT)
    if slot:
        u, v = slot
        rect(a, u, v, u + 2, v + 3, RED_LIGHT)
        rect(a, u + 1, v, u + 2, v + 3, RED)
    return a


def shell_side(w, h):
    a = fill(w, h, TEAL_SIDE)
    rect(a, 0, 0, w, 1, TEAL)
    rect(a, 0, h - 1, w, h, TEAL_DARK)
    return a


def shell_under(w, h):
    a = fill(w, h, RED)
    rect(a, 0, 0, w, 1, RED_LIGHT)
    return a


# ---------------------------------------------------------------- piezas (espacio de Blockbench)
# (nombre, hueso, desde, hasta, pivote, giro, caras: {cara: función(w, h)})
FACE_DIMS = {"north": (0, 1), "south": (0, 1), "east": (2, 1), "west": (2, 1), "up": (0, 2), "down": (0, 2)}


# Medidas sacadas de la imagen (cámara calculada con las esquinas del cubo y el aro)
BODY = (12, 12, 15)          # ancho (x), alto (y), fondo (z)
RING_SIZE, RING_Y = 8, 6.5   # lado del aro y altura de su centro
# Caparazón: una banda gruesa doblada (medida en la imagen)
SHELL_CENTER = (-2.0, 15.5, 2.0)      # centro de la placa
SHELL_ROT = (-5.0, -17.5, 7.0)        # giro del caparazón (orden ZYX como Blockbench)
PLATE = (16.0, 4.0, 13.0)             # placa: largo (x), grosor (y), ancho (z)
ARM_LEN, BEND = 14.5, 68.5            # el brazo sigue por el lado -x y se dobla hacia abajo


def parts():
    P = []
    side, top = body_side, body_top
    bx, by, bz = BODY
    P.append(("cuerpo", "cuerpo", (-bx / 2, 0, -bz / 2), (bx / 2, by, bz / 2), (0, 0, 0), (0, 0, 0),
              {"north": body_front, "south": side, "east": side, "west": side, "up": top, "down": side}))
    # el aro del ojo: un marco que sobresale 1 de la cara de delante
    ring = {"north": ring_face, "east": lambda w, h: fill(w, h, RING_SIDE), "west": lambda w, h: fill(w, h, RING_SIDE),
            "up": lambda w, h: fill(w, h, RING_LIGHT), "down": lambda w, h: fill(w, h, RING_SIDE),
            "south": lambda w, h: fill(w, h, RING_SIDE)}
    h = RING_SIZE / 2
    z0, z1 = -bz / 2 - 1, -bz / 2
    y0, y1 = RING_Y - h, RING_Y + h
    P.append(("aro_arriba", "cuerpo", (-h, y1 - 2, z0), (h, y1, z1), (0, 0, 0), (0, 0, 0), ring))
    P.append(("aro_abajo", "cuerpo", (-h, y0, z0), (h, y0 + 2, z1), (0, 0, 0), (0, 0, 0), ring))
    P.append(("aro_izq", "cuerpo", (-h, y0 + 2, z0), (-h + 2, y1 - 2, z1), (0, 0, 0), (0, 0, 0), ring))
    P.append(("aro_der", "cuerpo", (h - 2, y0 + 2, z0), (h, y1 - 2, z1), (0, 0, 0), (0, 0, 0), ring))
    cx, cy, cz = SHELL_CENTER
    sx, sy, sz = PLATE
    side_faces = {"north": shell_side, "south": shell_side, "east": shell_side, "west": shell_side,
                  "down": shell_under}
    plate = dict(side_faces, up=lambda w, h: shell_top(w, h, "left", slot=(w // 2, h - 6)))
    P.append(("caparazon_placa", "caparazon", (cx - sx / 2, cy - sy / 2, cz - sz / 2),
              (cx + sx / 2, cy + sy / 2, cz + sz / 2), (0, 0, 0), (0, 0, 0), plate))
    arm = dict(side_faces, up=lambda w, h: shell_top(w, h, "right"))
    P.append(("caparazon_brazo", "caparazon", (cx - sx / 2 - ARM_LEN, cy - sy / 2, cz - sz / 2),
              (cx - sx / 2, cy + sy / 2, cz + sz / 2), (cx - sx / 2, cy + sy / 2, cz), (0, 0, BEND), arm))
    return P


def build():
    P = parts()
    tiles = []
    for name, bone, a, b, pv, rot, faces in P:
        size = [b[i] - a[i] for i in range(3)]
        for f, fn in faces.items():
            i, j = FACE_DIMS[f]
            w, h = max(1, round(size[i])), max(1, round(size[j]))
            tiles.append((name, f, fn(w, h)))
    # empaquetar
    x = y = row = 0
    place = {}
    atlas = np.zeros((TEX_H, TEX_W, 4), np.uint8)
    for name, f, img in sorted(tiles, key=lambda t: -t[2].shape[0]):
        h, w = img.shape[:2]
        if x + w > TEX_W:
            x, y, row = 0, y + row, 0
        atlas[y:y + h, x:x + w] = img
        place[(name, f)] = (x, y, w, h)
        x += w
        row = max(row, h)
    assert y + row <= TEX_H, "la textura no cabe"
    return P, place, Image.fromarray(atlas, "RGBA")


# ---------------------------------------------------------------- animaciones
ANIMS = {
    "animation.embestidor.quieto": {"loop": True, "animation_length": 2.0, "bones": {
        "cuerpo": {"position": [0, "math.sin(query.anim_time * 180) * 0.3", 0]},
        "caparazon": {"rotation": ["math.sin(query.anim_time * 180) * 2", 0, 0],
                      "position": [0, "math.sin(query.anim_time * 180 - 40) * 0.4", 0]}}},
    "animation.embestidor.andar": {"loop": True, "animation_length": 0.5, "bones": {
        "cuerpo": {"position": [0, "math.abs(math.sin(query.anim_time * 360)) * 1.5", 0],
                   "rotation": ["math.sin(query.anim_time * 720) * 4", 0, "math.sin(query.anim_time * 360) * 3"]},
        "caparazon": {"rotation": ["math.sin(query.anim_time * 720 - 60) * 5", 0, 0]}}},
    "animation.embestidor.embestir": {"loop": False, "animation_length": 0.9, "bones": {
        # se agacha y echa el caparazón atrás (0-0,35 s) y se lanza hacia delante
        "cuerpo": {"rotation": {"0.0": [0, 0, 0], "0.35": [-12, 0, 0], "0.5": [18, 0, 0], "0.9": [0, 0, 0]},
                   "position": {"0.0": [0, 0, 0], "0.35": [0, -1, 1.5], "0.5": [0, 0.5, -2], "0.9": [0, 0, 0]}},
        "caparazon": {"rotation": {"0.0": [0, 0, 0], "0.35": [-25, 0, 0], "0.5": [10, 0, 0], "0.9": [0, 0, 0]}}}},
}


# ---------------------------------------------------------------- exportar
BONES = {"cuerpo": {"pivot": (0, 0, 0), "rotation": (0, 0, 0)},
         "caparazon": {"pivot": SHELL_CENTER, "rotation": SHELL_ROT, "parent": "cuerpo"}}


def to_bedrock(P, place):
    bones = {}
    order = []
    for name, bone, a, b, pv, rot, faces in P:
        if bone not in bones:
            B = BONES[bone]
            bones[bone] = {"name": bone, "pivot": [-B["pivot"][0], B["pivot"][1], B["pivot"][2]], "cubes": []}
            if any(B["rotation"]):
                r = B["rotation"]
                bones[bone]["rotation"] = [-r[0], -r[1], r[2]]
            if "parent" in B:
                bones[bone]["parent"] = B["parent"]
            order.append(bone)
        size = [b[i] - a[i] for i in range(3)]
        cube = {"origin": [-b[0], a[1], a[2]], "size": size,
                "uv": {f: {"uv": [place[(name, f)][0], place[(name, f)][1]],
                           "uv_size": [place[(name, f)][2], place[(name, f)][3]]} for f in faces}}
        if any(rot):
            cube["pivot"] = [-pv[0], pv[1], pv[2]]
            cube["rotation"] = [-rot[0], -rot[1], rot[2]]
        bones[bone]["cubes"].append(cube)
    return {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": "geometry.embestidor", "texture_width": TEX_W, "texture_height": TEX_H,
                        "visible_bounds_width": 3, "visible_bounds_height": 2.5, "visible_bounds_offset": [0, 1, 0]},
        "bones": [bones[b] for b in order]}]}


def to_bbmodel(P, place, png):
    elements, groups = [], {}
    for name, bone, a, b, pv, rot, faces in P:
        eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "emb." + name))
        fx = {}
        for f in faces:
            x, y, w, h = place[(name, f)]
            fx[f] = {"uv": [x, y, x + w, y + h], "texture": 0}
        elements.append({"name": name, "box_uv": False, "from": list(a), "to": list(b), "origin": list(pv),
                         "rotation": list(rot), "faces": fx, "type": "cube", "uuid": eid})
        if bone not in groups:
            groups[bone] = {"name": bone, "origin": list(BONES[bone]["pivot"]), "rotation": list(BONES[bone]["rotation"]),
                            "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "emb.g." + bone)), "export": True,
                            "isOpen": True, "visibility": True, "children": []}
        groups[bone]["children"].append(eid)
    groups["cuerpo"]["children"].append(groups["caparazon"])
    anims = []
    for n, a in ANIMS.items():
        anim = {"uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, n)), "name": n, "loop": "loop" if a["loop"] is True else "once",
                "length": a["animation_length"], "snapping": 20, "animators": {}}
        for bone, chans in a["bones"].items():
            kfs = []
            for ch, data in chans.items():
                if isinstance(data, list):
                    data = {"0.0": data}
                for t, v in data.items():
                    kfs.append({"channel": ch, "time": float(t), "interpolation": "linear", "uuid": str(uuid.uuid4()),
                                "data_points": [{"x": v[0], "y": v[1], "z": v[2]}]})
            anim["animators"][groups[bone]["uuid"]] = {"name": bone, "type": "bone", "keyframes": kfs}
        anims.append(anim)
    return {"meta": {"format_version": "4.10", "model_format": "bedrock", "box_uv": False},
            "name": "embestidor", "model_identifier": "embestidor", "visible_box": [3, 2.5, 1],
            "resolution": {"width": TEX_W, "height": TEX_H}, "elements": elements, "outliner": [groups["cuerpo"]],
            "textures": [{"name": "embestidor.png", "id": "0", "width": TEX_W, "height": TEX_H, "uv_width": TEX_W,
                          "uv_height": TEX_H, "internal": True, "saved": True, "uuid": str(uuid.uuid4()),
                          "source": "data:image/png;base64," + base64.b64encode(png).decode()}],
            "animations": anims}


def main():
    P, place, atlas = build()
    for d in ("models/entity", "textures/entity", "animations"):
        (RP / d).mkdir(parents=True, exist_ok=True)
    atlas.save(RP / "textures" / "entity" / "embestidor.png")
    (RP / "models" / "entity" / "embestidor.geo.json").write_text(json.dumps(to_bedrock(P, place), indent=1) + "\n")
    (RP / "animations" / "embestidor.animation.json").write_text(
        json.dumps({"format_version": "1.8.0", "animations": ANIMS}, indent=1) + "\n")
    buf = io.BytesIO()
    atlas.save(buf, "PNG")
    (ROOT / "embestidor.bbmodel").write_text(json.dumps(to_bbmodel(P, place, buf.getvalue())))
    print(f"{len(P)} cubos, textura {TEX_W}x{TEX_H}")


if __name__ == "__main__":
    main()
