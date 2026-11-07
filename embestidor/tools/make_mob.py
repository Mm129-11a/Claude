"""Genera el modelo del Embestidor copiando la imagen de referencia, para Blockbench y Bedrock.

Uso:  python3 tools/make_mob.py

Lee (en fuente/):
  referencia.png    la imagen del mob
  camara.json       la cámara de esa imagen (sacada de las esquinas del cubo y del aro)
  caparazon.json    las cajas del caparazón (ajustadas a la silueta de la imagen)

Las texturas NO se dibujan a mano: cada píxel de textura de cada cara se coloca en 3D, se mira
dónde cae en la imagen con la cámara de la imagen y, si esa cara se ve ahí, toma ese color
(como un proyector). Así, desde el ángulo de la imagen el modelo se ve igual que la imagen.
Se compensa la luz que pone el juego para que no oscurezca dos veces. Las caras que no se ven
en la imagen copian la cara de enfrente.

Crea:
  embestidor.bbmodel                                   proyecto de Blockbench
  EmbestidorRP/models/entity/embestidor.geo.json       geometría de Bedrock
  EmbestidorRP/textures/entity/embestidor.png          textura
  EmbestidorRP/animations/embestidor.animation.json    animaciones (quieto, andar, embestir)
"""
import base64
import io
import json
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation as Rot

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "fuente"
RP = ROOT / "EmbestidorRP"
DENS = 6                      # píxeles de textura por píxel de modelo (la imagen tiene unos 13)
ATLAS_W = 512

# ---------------------------------------------------------------- medidas
cam = json.loads((SRC / "camara.json").read_text())
CAM_R = Rot.from_rotvec(cam["rv"]).as_matrix()
CAM_S, CAM_T = cam["s"], cam["t"]
HX, HZ, RING_H, RING_Y = cam["box"]
BODY = (2 * HX, 12.0, 2 * HZ)
shell_x = json.loads((SRC / "caparazon.json").read_text())
SHELL = [(tuple(shell_x[9 * k:9 * k + 3]), tuple(shell_x[9 * k + 3:9 * k + 6]), tuple(shell_x[9 * k + 6:9 * k + 9]))
         for k in range(len(shell_x) // 9)]


def round_box(c, size, rot):
    r = lambda v, q: round(float(v) / q) * q
    return tuple(r(v, 0.25) for v in c), tuple(max(1.0, r(v, 0.25)) for v in size), tuple(r(v, 0.5) for v in rot)


def parts():
    """(nombre, hueso, desde, hasta, pivote, giro): en el espacio de Blockbench."""
    bx, by, bz = BODY
    P = [("cuerpo", "cuerpo", (-bx / 2, 0, -bz / 2), (bx / 2, by, bz / 2), (0, 0, 0), (0, 0, 0))]
    h = round(RING_H * 2) / 2
    y0, y1 = RING_Y - h, RING_Y + h
    z0, z1 = -bz / 2 - 1, -bz / 2
    P += [("aro_arriba", "cuerpo", (-h, y1 - 2, z0), (h, y1, z1), (0, 0, 0), (0, 0, 0)),
          ("aro_abajo", "cuerpo", (-h, y0, z0), (h, y0 + 2, z1), (0, 0, 0), (0, 0, 0)),
          ("aro_izq", "cuerpo", (-h, y0 + 2, z0), (-h + 2, y1 - 2, z1), (0, 0, 0), (0, 0, 0)),
          ("aro_der", "cuerpo", (h - 2, y0 + 2, z0), (h, y1 - 2, z1), (0, 0, 0), (0, 0, 0))]
    for k, (c, size, rot) in enumerate(SHELL):
        c, size, rot = round_box(c, size, rot)
        a = tuple(c[i] - size[i] / 2 for i in range(3))
        b = tuple(c[i] + size[i] / 2 for i in range(3))
        P.append((f"caparazon_{k + 1}", "caparazon", a, b, c, rot))
    return P


# ---------------------------------------------------------------- caras (convenio de Blockbench)
FACES = ("north", "south", "east", "west", "up", "down")
NORMALS = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
# caras que no se ven en la imagen y de qué cara copian (si no, la de enfrente)
FILL_FROM = {("cuerpo", "south"): "east", ("cuerpo", "down"): "east", ("cuerpo", "west"): "east"}


def face_frame(face, a, b):
    """Para una cara: origen (esquina de arriba-izquierda de su textura), vector u, vector v, ancho, alto."""
    x0, y0, z0 = a
    x1, y1, z1 = b
    if face == "north":
        return np.array([x1, y1, z0]), np.array([-1, 0, 0.]), np.array([0, -1, 0.]), x1 - x0, y1 - y0
    if face == "south":
        return np.array([x0, y1, z1]), np.array([1, 0, 0.]), np.array([0, -1, 0.]), x1 - x0, y1 - y0
    if face == "east":
        return np.array([x1, y1, z1]), np.array([0, 0, -1.]), np.array([0, -1, 0.]), z1 - z0, y1 - y0
    if face == "west":
        return np.array([x0, y1, z0]), np.array([0, 0, 1.]), np.array([0, -1, 0.]), z1 - z0, y1 - y0
    if face == "up":
        return np.array([x0, y1, z0]), np.array([1, 0, 0.]), np.array([0, 0, 1.]), x1 - x0, z1 - z0
    return np.array([x0, y0, z1]), np.array([1, 0, 0.]), np.array([0, 0, -1.]), x1 - x0, z1 - z0   # down


def rot_matrix(rot):
    return Rot.from_euler("xyz", rot, degrees=True).as_matrix()      # orden ZYX de Blockbench


def world(points, pivot, rot):
    return (rot_matrix(rot) @ (np.asarray(points, float) - pivot).T).T + np.asarray(pivot, float)


def project(P):
    q = (CAM_R @ np.asarray(P, float).T).T
    return np.stack([CAM_S * q[:, 0] + CAM_T[0], -CAM_S * q[:, 1] + CAM_T[1]], 1), q[:, 2]


# luz del juego (aproximada): para no oscurecer dos veces las caras de lado
L1 = np.array([0.2, 1.0, -0.7]); L1 /= np.linalg.norm(L1)
L2 = np.array([-0.2, 1.0, 0.7]); L2 /= np.linalg.norm(L2)


def game_shade(n):
    return min(1.0, 0.4 + 0.6 * (max(0, n @ L1) + max(0, n @ L2)))


def textures(P, compensate=True):
    ref = np.array(Image.open(SRC / "referencia.png").convert("RGBA")).astype(np.float32)
    H, W = ref.shape[:2]
    # profundidad de lo más cercano en cada píxel de la imagen
    zbuf = np.full((H, W), -1e9)
    for name, bone, a, b, pv, rot in P:
        for f in FACES:
            o, u, v, w, h = face_frame(f, a, b)
            C = np.array([o, o + u * w, o + u * w + v * h, o + v * h])
            p2, z = project(world(C, pv, rot))
            m = np.zeros((H, W), np.uint8)
            cv2.fillConvexPoly(m, np.round(p2).astype(np.int32), 1)
            ys, xs = np.nonzero(m)
            if len(xs) == 0:
                continue
            coef = np.linalg.lstsq(np.c_[p2, np.ones(4)], z, rcond=None)[0]
            zbuf[ys, xs] = np.maximum(zbuf[ys, xs], coef[0] * xs + coef[1] * ys + coef[2])
    cam_dir = CAM_R.T @ np.array([0, 0, 1.0])
    tex = {}
    for name, bone, a, b, pv, rot in P:
        for f in FACES:
            n_world = rot_matrix(rot) @ np.array(NORMALS[f], float)
            o, u, v, w, h = face_frame(f, a, b)
            tw, th = max(1, int(round(w * DENS))), max(1, int(round(h * DENS)))
            ii, jj = np.meshgrid((np.arange(tw) + 0.5) / tw * w, (np.arange(th) + 0.5) / th * h)
            pts = o + ii[..., None] * u + jj[..., None] * v
            p2, z = project(world(pts.reshape(-1, 3), pv, rot))
            xs, ys = p2[:, 0], p2[:, 1]
            inside = (xs >= 0) & (xs < W - 1) & (ys >= 0) & (ys < H - 1)
            xi = np.clip(np.round(xs).astype(int), 0, W - 1)
            yi = np.clip(np.round(ys).astype(int), 0, H - 1)
            vis = inside & (n_world @ cam_dir > 0.02) & (z >= zbuf[yi, xi] - 0.3)
            col = np.zeros((len(xs), 4), np.float32)
            if vis.any():
                x0_ = np.floor(xs[vis]).astype(int); y0_ = np.floor(ys[vis]).astype(int)
                fx = (xs[vis] - x0_)[:, None]; fy = (ys[vis] - y0_)[:, None]
                col[vis] = (ref[y0_, x0_] * (1 - fx) * (1 - fy) + ref[y0_, x0_ + 1] * fx * (1 - fy)
                            + ref[y0_ + 1, x0_] * (1 - fx) * fy + ref[y0_ + 1, x0_ + 1] * fx * fy)
            ok = (vis & (col[:, 3] > 128)).reshape(th, tw)
            img = col[:, :3].reshape(th, tw, 3)
            if compensate:
                img = np.clip(img / max(0.55, game_shade(n_world)), 0, 255)
            tex[(name, f)] = {"img": img, "ok": ok, "frac": ok.mean()}
    # rellenar: lo tapado con lo de alrededor; las caras que no se ven, con la de enfrente
    for t in tex.values():
        if t["frac"] >= 0.15 and not t["ok"].all():
            t["img"] = cv2.inpaint(np.clip(t["img"], 0, 255).astype(np.uint8), (~t["ok"]).astype(np.uint8), 3,
                                   cv2.INPAINT_TELEA).astype(np.float32)
    for (name, f), t in tex.items():
        if t["frac"] < 0.15:
            opp = tex[(name, FILL_FROM.get((name, f), OPPOSITE[f]))]
            if opp["frac"] >= 0.15:
                t["img"] = cv2.resize(opp["img"], (t["img"].shape[1], t["img"].shape[0]), interpolation=cv2.INTER_NEAREST)
            else:
                vis = [x["img"][x["ok"]] for (n2, f2), x in tex.items() if n2 == name and x["frac"] >= 0.15]
                c = np.median(np.concatenate(vis), axis=0) if vis else np.array([20, 20, 20.])
                t["img"] = np.tile(c * 0.8, (t["img"].shape[0], t["img"].shape[1], 1))
    return tex


def pack(tex):
    x = y = row = 0
    place = {}
    for key, t in sorted(tex.items(), key=lambda kv: -kv[1]["img"].shape[0]):
        h, w = t["img"].shape[:2]
        if x + w > ATLAS_W:
            x, y, row = 0, y + row, 0
        place[key] = (x, y, w, h)
        x += w
        row = max(row, h)
    H = y + row
    H += (-H) % 16
    atlas = np.zeros((H, ATLAS_W, 4), np.uint8)
    for key, t in tex.items():
        x, y, w, h = place[key]
        atlas[y:y + h, x:x + w, :3] = np.clip(t["img"], 0, 255)
        atlas[y:y + h, x:x + w, 3] = 255
    return place, Image.fromarray(atlas, "RGBA")


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
SHELL_PIVOT = (0, 12, 0)


# ---------------------------------------------------------------- exportar
def to_bedrock(P, place, tw, th):
    bones = {"cuerpo": {"name": "cuerpo", "pivot": [0, 0, 0], "cubes": []},
             "caparazon": {"name": "caparazon", "parent": "cuerpo",
                           "pivot": [-SHELL_PIVOT[0], SHELL_PIVOT[1], SHELL_PIVOT[2]], "cubes": []}}
    for name, bone, a, b, pv, rot in P:
        size = [round(b[i] - a[i], 4) for i in range(3)]
        cube = {"origin": [round(-b[0], 4), round(a[1], 4), round(a[2], 4)], "size": size,
                "uv": {f: {"uv": list(place[(name, f)][:2]), "uv_size": list(place[(name, f)][2:])} for f in FACES}}
        if any(rot):
            cube["pivot"] = [round(-pv[0], 4), round(pv[1], 4), round(pv[2], 4)]
            cube["rotation"] = [-rot[0], -rot[1], rot[2]]
        bones[bone]["cubes"].append(cube)
    return {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": "geometry.embestidor", "texture_width": tw, "texture_height": th,
                        "visible_bounds_width": 3, "visible_bounds_height": 3, "visible_bounds_offset": [0, 1, 0]},
        "bones": [bones["cuerpo"], bones["caparazon"]]}]}


def to_bbmodel(P, place, png, tw, th):
    elements, groups = [], {}
    for name, bone, a, b, pv, rot in P:
        eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "emb." + name))
        fx = {}
        for f in FACES:
            x, y, w, h = place[(name, f)]
            fx[f] = {"uv": [x, y, x + w, y + h], "texture": 0}
        elements.append({"name": name, "box_uv": False, "from": list(a), "to": list(b), "origin": list(pv),
                         "rotation": list(rot), "faces": fx, "type": "cube", "uuid": eid})
        if bone not in groups:
            groups[bone] = {"name": bone, "origin": [0, 0, 0] if bone == "cuerpo" else list(SHELL_PIVOT),
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
            "name": "embestidor", "model_identifier": "embestidor", "visible_box": [3, 3, 1],
            "resolution": {"width": tw, "height": th}, "elements": elements, "outliner": [groups["cuerpo"]],
            "textures": [{"name": "embestidor.png", "id": "0", "width": tw, "height": th, "uv_width": tw,
                          "uv_height": th, "internal": True, "saved": True, "uuid": str(uuid.uuid4()),
                          "source": "data:image/png;base64," + base64.b64encode(png).decode()}],
            "animations": anims}


def build(compensate=True):
    P = parts()
    place, atlas = pack(textures(P, compensate))
    return P, place, atlas


def main():
    P, place, atlas = build()
    tw, th = atlas.size
    for d in ("models/entity", "textures/entity", "animations"):
        (RP / d).mkdir(parents=True, exist_ok=True)
    atlas.save(RP / "textures" / "entity" / "embestidor.png")
    (RP / "models" / "entity" / "embestidor.geo.json").write_text(json.dumps(to_bedrock(P, place, tw, th), indent=1) + "\n")
    (RP / "animations" / "embestidor.animation.json").write_text(
        json.dumps({"format_version": "1.8.0", "animations": ANIMS}, indent=1) + "\n")
    buf = io.BytesIO()
    atlas.save(buf, "PNG")
    (ROOT / "embestidor.bbmodel").write_text(json.dumps(to_bbmodel(P, place, buf.getvalue(), tw, th)))
    # versión sin compensar la luz, para comparar con la imagen (dibujada sin luz)
    P2, place2, atlas2 = build(compensate=False)
    buf2 = io.BytesIO()
    atlas2.save(buf2, "PNG")
    (ROOT / "tools" / "comparar_sin_luz.bbmodel").write_text(json.dumps(to_bbmodel(P2, place2, buf2.getvalue(), *atlas2.size)))
    print(f"{len(P)} cubos, textura {tw}x{th}")


if __name__ == "__main__":
    main()
