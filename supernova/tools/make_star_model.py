"""Genera la estrella como MODELO 3D (entidad), para que se vea 3D desde cualquier lado.

Uso:  python3 tools/make_star_model.py
Necesita: numpy, pillow (y usa tools/make_vfx.py para la superficie de lava)

La estrella es una esfera de 5 bloques de radio partida en sus placas de roca (las mismas que
dibujan las grietas). Cada placa es una pieza 3D hecha con cubos planos (como en Blockbench):
  - una lámina por fuera con la roca y las grietas (recortada con la forma de la placa),
  - tres láminas por dentro con lava, para que se vea el grosor,
y va colocada en su sitio de la esfera con dos giros (horizontal y vertical).

Crea:
  SupernovaRP/models/entity/supernova_estrella.geo.json      la geometría
  SupernovaRP/textures/entity/supernova/estrella.png         la textura de todas las piezas
  SupernovaRP/animations/supernova_estrella.animation.json   formación, giro, hincharse y estallar
  SupernovaRP/entity/supernova_estrella*.entity.json         cómo se dibujan las dos entidades
  SupernovaBP/entities/supernova_estrella*.json              las entidades (flotan, no se pueden dañar)
  SupernovaBP/scripts/estrella_modelo.js                     cuántas piezas y cuándo llega cada una
  estrella_3d.bbmodel                                        el modelo para abrirlo en Blockbench

Todo se calcula en el espacio de Blockbench y se convierte a Bedrock como lo hace Blockbench:
x cambiada de signo en posiciones y pivotes, y giros [-x, -y, z].
"""
import base64
import io
import json
import math
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

import make_vfx as vfx

ROOT = Path(__file__).resolve().parent.parent
RP, BP = ROOT / "SupernovaRP", ROOT / "SupernovaBP"

R = 80.0                     # radio en píxeles de modelo (16 = 1 bloque): 5 bloques
D_ROCK = 3                   # texeles de textura por píxel de modelo en la roca
D_LAVA = 1                   # y en la lava
LAYERS = [0.0, 1.5, 3.0, 4.5]  # profundidad de cada lámina bajo la superficie (grosor 4,5 px)
LAYER_THICK = 0.6            # grosor de cada lámina (separa la cara de roca de la de lava)
ATLAS_W = 2048
PAD = 1

# Tiempos (segundos desde que aparece la entidad); deben cuadrar con T en scripts/main.js
FORM_SPREAD = 3.0            # la primera pieza sale en 0 s y la última en 3 s
FLIGHT = 1.1                 # lo que tarda cada pieza en llegar
SWELL = (6.3, 7.3)           # se hincha antes de explotar
SPIN_PERIOD = 7.3            # una vuelta entera justo cuando explota (así la rota empieza igual)
BURST = 2.2                  # lo que dura la estrella rota

LAVA_COLS = np.array([[255, 214, 120], [240, 150, 55], [200, 85, 25]], float)


# ---------------------------------------------------------------- superficie (de make_vfx)
def warped_cells(p):
    warp = np.stack([vfx.fbm(p * 4 + 10, 3, 61), vfx.fbm(p * 4 + 20, 3, 67), vfx.fbm(p * 4 + 30, 3, 71)], -1) - 0.5
    pw = p + warp * 0.16
    pw /= np.linalg.norm(pw, axis=1, keepdims=True)
    dots = pw @ vfx.SITES.T
    idx = np.argsort(-dots, axis=1)[:, :2]
    d1 = np.sqrt(np.maximum(0, 2 - 2 * np.take_along_axis(dots, idx[:, :1], 1)[:, 0]))
    d2 = np.sqrt(np.maximum(0, 2 - 2 * np.take_along_axis(dots, idx[:, 1:], 1)[:, 0]))
    return idx[:, 0], (d2 - d1) / 2


def surface(p):
    """Color de la roca con grietas de lava en los puntos p (sin luz: la pone el juego)."""
    cell, e = warped_cells(p)
    wobble = vfx.fbm(p * 7, 2, 3)
    width = 0.006 + 0.02 * wobble ** 2
    core = np.clip(1 - e / width, 0, 1) ** 0.7
    glow = np.exp(-e / (0.022 + 0.03 * wobble))
    tex = vfx.fbm(p * 6, 4, 11) * 0.5 + vfx.fbm(p * 30, 3, 29) * 0.5
    tone = np.clip((tex - 0.22) / 0.5, 0, 1) * vfx.CELL_TONE[cell]
    rock = vfx.ramp(np.clip(tone, 0, 1), vfx.ROCK) * 1.15
    flow = vfx.fbm(p * 3.2 + np.array([1.3, 0, 0.0]), 3, 41)
    pulse = 0.85 + 0.4 * flow
    hot = vfx.HOT[cell] * (0.6 + 0.4 * vfx.fbm(p * 5 + np.array([0, 1.0, 0]), 2, 53))
    g = glow * (1 - core)
    emis = core[:, None] * (vfx.CRACK_CORE * 0.6 + vfx.CRACK * 0.4) + g[:, None] * (vfx.CRACK * 0.5 + vfx.CRACK_GLOW * 0.5)
    emis = emis * pulse[:, None] + hot[:, None] * vfx.CRACK_GLOW * (0.5 + 0.5 * glow[:, None])
    mix = np.clip(core + g * 0.85 + hot * 0.9, 0, 1)[:, None]
    col = rock * (1 - mix) + emis * np.clip(mix * 1.2, 0, 1)
    return np.clip(col, 0, 255), cell


def lava(p):
    n = vfx.fbm(p * 5 + 3, 3, 91)
    t = np.clip((n - 0.3) / 0.4, 0, 1)[:, None]
    return LAVA_COLS[0] * (1 - t) + LAVA_COLS[2] * t


# ---------------------------------------------------------------- piezas
def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def make_pieces():
    # puntos repartidos por toda la esfera para saber qué ocupa cada placa
    m = 300000
    k = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * k / m)
    th = math.pi * (1 + 5 ** 0.5) * k
    pts = np.stack([np.sin(phi) * np.cos(th), np.cos(phi), np.sin(phi) * np.sin(th)], -1)
    cell, _ = warped_cells(pts)
    pieces = []
    for c in range(len(vfx.SITES)):
        P = pts[cell == c]
        if len(P) < 50:
            continue
        d = P.mean(0)
        d /= np.linalg.norm(d)
        yaw = math.atan2(d[0], d[2])
        pitch = -math.asin(max(-1, min(1, d[1])))
        M = rot_y(yaw) @ rot_x(pitch)            # (0,0,1) -> d
        ex, ey, ez = M[:, 0], M[:, 1], M[:, 2]
        q = P * (R / (P @ ez))[:, None]           # sobre el plano tangente
        lx, ly = q @ ex, q @ ey
        x0, x1 = math.floor(lx.min() - 1), math.ceil(lx.max() + 1)
        y0, y1 = math.floor(ly.min() - 1), math.ceil(ly.max() + 1)
        pieces.append({"cell": c, "dir": d, "yaw": yaw, "pitch": pitch, "M": M,
                       "x0": x0, "x1": x1, "y0": y0, "y1": y1})
    return pieces


def tile_image(pc, dens, colorize, mirror=False):
    """Textura de la cara de una pieza: cada texel -> punto del plano -> dirección -> ¿es de la placa?"""
    w = (pc["x1"] - pc["x0"]) * dens
    h = (pc["y1"] - pc["y0"]) * dens
    ii, jj = np.meshgrid(np.arange(w), np.arange(h))
    if mirror:   # cara de atrás (norte): vista desde fuera, la x va al revés
        lx = pc["x1"] - (ii + 0.5) / dens
    else:
        lx = pc["x0"] + (ii + 0.5) / dens
    ly = pc["y1"] - (jj + 0.5) / dens
    M = pc["M"]
    P = (R * M[:, 2])[None, :] + lx.reshape(-1, 1) * M[:, 0] + ly.reshape(-1, 1) * M[:, 1]
    p = P / np.linalg.norm(P, axis=1, keepdims=True)
    col, cell = colorize(p)
    inside = cell == pc["cell"]
    img = np.zeros((h * w, 4), np.uint8)
    img[:, :3] = np.clip(col, 0, 255)
    img[:, 3] = np.where(inside, 255, 0)
    return img.reshape(h, w, 4)


def build_atlas(pieces):
    regions = []
    for pc in pieces:
        pc["img_rock"] = tile_image(pc, D_ROCK, surface)
        lava_c = lambda p: (lava(p), warped_cells(p)[0])
        pc["img_lava"] = tile_image(pc, D_LAVA, lava_c)
        pc["img_lava_m"] = tile_image(pc, D_LAVA, lava_c, mirror=True)
        regions += [(pc, "rock"), (pc, "lava"), (pc, "lava_m")]
    x = y = row_h = 0
    for pc, kind in sorted(regions, key=lambda r: -r[0]["img_" + r[1]].shape[0]):
        im = pc["img_" + kind]
        h, w = im.shape[:2]
        if x + w > ATLAS_W:
            x, y, row_h = 0, y + row_h + PAD, 0
        pc["uv_" + kind] = (x, y, w, h)
        x += w + PAD
        row_h = max(row_h, h)
    H = y + row_h
    H += (-H) % 16
    atlas = np.zeros((H, ATLAS_W, 4), np.uint8)
    for pc in pieces:
        for kind in ("rock", "lava", "lava_m"):
            u, v, w, h = pc["uv_" + kind]
            atlas[v:v + h, u:u + w] = pc["img_" + kind]
    return Image.fromarray(atlas, "RGBA")


# ---------------------------------------------------------------- geometría
def to_bedrock_vec(v):
    return [round(-v[0], 4), round(v[1], 4), round(v[2], 4)]


def geometry(pieces, tex_w, tex_h):
    bones = [{"name": "estrella", "pivot": [0, 0, 0]}]
    for i, pc in enumerate(pieces):
        bones.append({"name": f"y{i}", "parent": "estrella", "pivot": [0, 0, 0],
                      "rotation": [0, round(-math.degrees(pc["yaw"]), 4), 0]})
        bones.append({"name": f"x{i}", "parent": f"y{i}", "pivot": [0, 0, 0],
                      "rotation": [round(-math.degrees(pc["pitch"]), 4), 0, 0]})
        x0, x1, y0, y1 = pc["x0"], pc["x1"], pc["y0"], pc["y1"]
        cubes = []
        for k, dz in enumerate(LAYERS):
            south = pc["uv_rock"] if k == 0 else pc["uv_lava"]
            north = pc["uv_lava_m"]
            # cada lámina tiene un poco de grosor: la cara de fuera y la de dentro NO están en el
            # mismo plano (el juego dibuja las caras por los dos lados y si coinciden se pelean)
            th = LAYER_THICK
            cubes.append({"origin": [-x1, y0, R - dz - th], "size": [x1 - x0, y1 - y0, th],
                          "uv": {"south": {"uv": list(south[:2]), "uv_size": list(south[2:])},
                                 "north": {"uv": list(north[:2]), "uv_size": list(north[2:])}}})
        bones.append({"name": f"p{i}", "parent": f"x{i}",
                      "pivot": to_bedrock_vec([(x0 + x1) / 2, (y0 + y1) / 2, R]), "cubes": cubes})
    return {"format_version": "1.12.0",
            "minecraft:geometry": [{
                "description": {"identifier": "geometry.supernova_estrella", "texture_width": tex_w,
                                "texture_height": tex_h, "visible_bounds_width": 64,
                                "visible_bounds_height": 64, "visible_bounds_offset": [0, 0, 0]},
                "bones": bones}]}


# ---------------------------------------------------------------- animaciones
def num(v):
    return round(float(v), 3)


def animations(pieces, order):
    rng = np.random.default_rng(21)
    n = len(pieces)
    starts = {}
    form_bones = {}
    burst_bones = {}
    samples = [0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0]
    for rank, i in enumerate(order):
        s = FORM_SPREAD * rank / max(1, n - 1)
        starts[i] = s
        D = rng.uniform(220, 380)                                  # de 14 a 24 bloques hacia fuera
        off = np.array([rng.uniform(-110, 110), rng.uniform(-110, 110), D])
        tumble = rng.choice([-1, 1], 3) * rng.uniform(180, 540, 3)
        pos, rot = {"0.0": [num(v) for v in off]}, {"0.0": [num(v) for v in tumble]}
        for f in samples:
            k = (1 - f) ** 3
            t = f"{num(s + f * FLIGHT)}"
            pos[t] = [num(v * k) for v in off]
            rot[t] = [num(v * k) for v in tumble]
        scale = {"0.0": [0, 0, 0], f"{num(s)}": {"pre": [0, 0, 0], "post": [1, 1, 1]}}
        form_bones[f"p{i}"] = {"position": pos, "rotation": rot, "scale": scale}
        # al estallar: hacia fuera girando, y se apagan
        D2 = rng.uniform(180, 420)
        off2 = np.array([rng.uniform(-120, 120), rng.uniform(-120, 120), D2])
        spin2 = rng.choice([-1, 1], 3) * rng.uniform(200, 700, 3)
        pos2, rot2 = {}, {}
        for f in samples:
            t = num(f * 1.6)
            e = 1 - (1 - f) ** 2
            pos2[f"{t}"] = [num(v * e) for v in off2]
            rot2[f"{t}"] = [num(v * f) for v in spin2]
        burst_bones[f"p{i}"] = {"position": pos2, "rotation": rot2,
                                "scale": {"0.0": [1, 1, 1], "1.4": [1, 1, 1], f"{BURST}": [0, 0, 0]}}
    form_len = FORM_SPREAD + FLIGHT + 0.05
    anims = {
        "animation.supernova.formacion": {"loop": "hold_on_last_frame", "animation_length": num(form_len),
                                          "bones": form_bones},
        "animation.supernova.giro": {"loop": True, "animation_length": SPIN_PERIOD,
                                     "bones": {"estrella": {"rotation": [0, f"query.anim_time * {num(360 / SPIN_PERIOD)}", 0]}}},
        "animation.supernova.hinchar": {"loop": "hold_on_last_frame", "animation_length": SWELL[1],
                                        "bones": {"estrella": {"scale": {"0.0": [1, 1, 1], f"{SWELL[0]}": [1, 1, 1],
                                                                         f"{SWELL[1]}": [1.3, 1.3, 1.3]}}}},
        "animation.supernova.estalla": {"loop": "hold_on_last_frame", "animation_length": BURST,
                                        "bones": {"estrella": {"scale": [1.3, 1.3, 1.3]}, **burst_bones}},
    }
    return {"format_version": "1.8.0", "animations": anims}, starts


# ---------------------------------------------------------------- entidades
def entities():
    for ident, anims, animate in (
            ("supernova:estrella", {"formacion": "animation.supernova.formacion", "giro": "animation.supernova.giro",
                                    "hinchar": "animation.supernova.hinchar"}, ["formacion", "giro", "hinchar"]),
            ("supernova:estrella_rota", {"estalla": "animation.supernova.estalla"}, ["estalla"])):
        name = ident.split(":")[1]
        client = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
            "identifier": ident,
            "materials": {"default": "entity_alphatest"},
            "textures": {"default": "textures/entity/supernova/estrella"},
            "geometry": {"default": "geometry.supernova_estrella"},
            "render_controllers": ["controller.render.default"],
            "animations": anims, "scripts": {"animate": animate}}}}
        (RP / "entity").mkdir(parents=True, exist_ok=True)
        (RP / "entity" / f"supernova_{name}.entity.json").write_text(json.dumps(client, indent=2) + "\n")
        server = {"format_version": "1.21.0", "minecraft:entity": {
            "description": {"identifier": ident, "is_spawnable": False, "is_summonable": True},
            "components": {
                "minecraft:type_family": {"family": ["supernova", "inanimate"]},
                "minecraft:physics": {"has_gravity": False, "has_collision": False},
                "minecraft:collision_box": {"width": 0.1, "height": 0.1},
                "minecraft:health": {"value": 100, "max": 100},
                "minecraft:damage_sensor": {"triggers": {"cause": "all", "deals_damage": "no"}},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:knockback_resistance": {"value": 1},
                "minecraft:fire_immune": {}}}}
        (BP / "entities").mkdir(parents=True, exist_ok=True)
        (BP / "entities" / f"supernova_{name}.json").write_text(json.dumps(server, indent=2) + "\n")


# ---------------------------------------------------------------- Blockbench
def bbmodel(geo, anims, atlas_png, tex_w, tex_h):
    """El mismo modelo como proyecto de Blockbench (formato Bedrock Entity)."""
    bones = geo["minecraft:geometry"][0]["bones"]
    elements, groups = [], {}
    for b in bones:
        pv = [-b["pivot"][0], b["pivot"][1], b["pivot"][2]]
        rot = b.get("rotation", [0, 0, 0])
        g = {"name": b["name"], "origin": pv, "rotation": [-rot[0], -rot[1], rot[2]], "color": 0,
             "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, "sn." + b["name"])), "export": True,
             "isOpen": False, "visibility": True, "children": []}
        groups[b["name"]] = g
        for k, c in enumerate(b.get("cubes", [])):
            x_from = -(c["origin"][0] + c["size"][0])
            frm = [x_from, c["origin"][1], c["origin"][2]]
            to = [frm[i] + c["size"][i] for i in range(3)]
            faces = {}
            for f in ("north", "south"):
                u, v = c["uv"][f]["uv"]
                w, h = c["uv"][f]["uv_size"]
                faces[f] = {"uv": [u, v, u + w, v + h], "texture": 0}
            eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sn.{b['name']}.{k}"))
            elements.append({"name": f"{b['name']}_{k}", "box_uv": False, "from": frm, "to": to,
                             "origin": pv, "rotation": [0, 0, 0], "faces": faces, "type": "cube", "uuid": eid})
            g["children"].append(eid)
    roots = []
    for b in bones:
        g = groups[b["name"]]
        if "parent" in b:
            groups[b["parent"]]["children"].append(g)
        else:
            roots.append(g)
    animators = []
    out_anims = []
    for name, a in anims["animations"].items():
        anim = {"uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, name)), "name": name,
                "loop": "loop" if a["loop"] is True else "hold", "length": a["animation_length"],
                "snapping": 20, "animators": {}}
        for bone, chans in a["bones"].items():
            kfs = []
            for ch, data in chans.items():
                if isinstance(data, list):
                    data = {"0.0": data}
                for t, v in data.items():
                    vals = v["post"] if isinstance(v, dict) else v
                    kfs.append({"channel": ch, "time": float(t), "interpolation": "linear",
                                "data_points": [{"x": vals[0], "y": vals[1], "z": vals[2]}],
                                "uuid": str(uuid.uuid4())})
            anim["animators"][groups[bone]["uuid"]] = {"name": bone, "type": "bone", "keyframes": kfs}
        out_anims.append(anim)
    return {"meta": {"format_version": "4.10", "model_format": "bedrock", "box_uv": False},
            "name": "supernova_estrella", "model_identifier": "supernova_estrella",
            "visible_box": [64, 64, 0], "resolution": {"width": tex_w, "height": tex_h},
            "elements": elements, "outliner": roots,
            "textures": [{"name": "estrella.png", "id": "0", "width": tex_w, "height": tex_h,
                          "uv_width": tex_w, "uv_height": tex_h, "internal": True, "saved": True,
                          "uuid": str(uuid.uuid4()), "render_mode": "default",
                          "source": "data:image/png;base64," + base64.b64encode(atlas_png).decode()}],
            "animations": out_anims}


def main():
    pieces = make_pieces()
    atlas = build_atlas(pieces)
    tex_w, tex_h = atlas.size
    (RP / "textures" / "entity" / "supernova").mkdir(parents=True, exist_ok=True)
    atlas.save(RP / "textures" / "entity" / "supernova" / "estrella.png")
    geo = geometry(pieces, tex_w, tex_h)
    (RP / "models" / "entity").mkdir(parents=True, exist_ok=True)
    (RP / "models" / "entity" / "supernova_estrella.geo.json").write_text(json.dumps(geo) + "\n")
    # orden de llegada: de abajo hacia arriba, con algo de azar
    rng = np.random.default_rng(3)
    order = sorted(range(len(pieces)), key=lambda i: pieces[i]["dir"][1] + rng.uniform(-0.35, 0.35))
    anims, starts = animations(pieces, order)
    (RP / "animations").mkdir(parents=True, exist_ok=True)
    (RP / "animations" / "supernova_estrella.animation.json").write_text(json.dumps(anims) + "\n")
    entities()
    arrivals = sorted(round((starts[i] + FLIGHT) * 20) for i in range(len(pieces)))
    (BP / "scripts" / "estrella_modelo.js").write_text(
        "// Generado por tools/make_star_model.py\n"
        f"export const PIEZAS = {len(pieces)};\n"
        f"export const LLEGADAS = {json.dumps(arrivals)};   // tick (desde que aparece) en que encaja cada pieza\n"
        f"export const RADIO = {R / 16};   // bloques\n")
    buf = io.BytesIO()
    atlas.save(buf, "PNG")
    (ROOT / "estrella_3d.bbmodel").write_text(json.dumps(bbmodel(geo, anims, buf.getvalue(), tex_w, tex_h)))
    cubes = sum(len(b.get("cubes", [])) for b in geo["minecraft:geometry"][0]["bones"])
    print(f"{len(pieces)} piezas, {cubes} cubos, textura {tex_w}x{tex_h}")


if __name__ == "__main__":
    main()
