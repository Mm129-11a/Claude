# Genera todo lo visual del eclipse: textura, modelo, animación y nieblas.
# Uso (desde eclipse-addon/):  python3 -I tools/build.py RP BP
#
# El eclipse es una entidad ("eclipse:sky") que va montada en el jugador, como un loro en el hombro.
# Así el juego la mueve contigo en cada cuadro y se ve suave aunque corras o vueles.
# Todo está dibujado en planos: el sol, la luna, la corona y el destello arriba de ti,
# y una "cúpula" (caja) a tu alrededor que oscurece el cielo.
import json, math, os, random, sys
from PIL import Image, ImageDraw

RP, BP = sys.argv[1], sys.argv[2]
for d in ("textures/entity", "textures/environment", "fogs", "models/entity", "entity",
          "render_controllers", "animations"):
    os.makedirs(f"{RP}/{d}", exist_ok=True)
os.makedirs(f"{BP}/entities", exist_ok=True)

# ---------------- medidas (bloques) ----------------
H = {"flash": 23.5, "moon": 24.0, "sun": 25.0, "corona": 25.3, "glow": 25.6}
DOME = 30          # la cúpula es una caja de 60x60 alrededor de ti, techo a 30 bloques
DOME_LOW = -10     # las paredes bajan 10 bloques bajo tus ojos
SUN_DEG, MOON_DEG = 5.5, 5.72
GLOW_DEG, FLASH_DEG = 30.0, 22.0
DISK_FILL, CORONA_HOLE = 0.96, 0.385
STAGES = 12
tan = lambda deg: math.tan(math.radians(deg))
HALF = {  # mitad del ancho de cada plano, en bloques
    "sun": H["sun"] * tan(SUN_DEG) / DISK_FILL,
    "moon": H["moon"] * tan(MOON_DEG) / DISK_FILL,
    "corona": H["corona"] * tan(MOON_DEG) / CORONA_HOLE,
    "glow": H["glow"] * tan(GLOW_DEG),
    "flash": H["flash"] * tan(FLASH_DEG),
}
clamp = lambda v: max(0, min(255, int(round(v))))
hexc = lambda h: tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

def lerp_colors(stops, x):
    for (x0, c0), (x1, c1) in zip(stops, stops[1:]):
        if x <= x1:
            f = (x - x0) / (x1 - x0)
            return tuple(a + (b - a) * f for a, b in zip(c0, c1))
    return stops[-1][1]

def radial(size, f):
    im = Image.new("RGBA", (size, size)); px = im.load(); c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            px[x, y] = f(math.hypot(x - c, y - c) / (size / 2), math.atan2(y - c, x - c))
    return im

# ---------------- texturas sueltas ----------------
def disk(rgb):
    return radial(128, lambda r, a: (*[clamp(c * 255) for c in rgb],
                                     255 if r < DISK_FILL - 0.02 else clamp((DISK_FILL + 0.02 - r) / 0.04 * 255)))

def glow(r, a):  # brillo del sol: muy fuerte cerca y un halo grande y suave
    if r >= 1: return (255, 255, 255, 0)
    rs = tan(SUN_DEG) / tan(GLOW_DEG)
    d = max(0, r - rs * 0.9)
    v = 0.95 * math.exp(-d / 0.07) + 0.45 * math.exp(-d / 0.28)
    return (255, 252, 238, clamp(min(1, v) * (1 - r ** 4) * 255))

random.seed(3)
streams = [(random.uniform(0, 2 * math.pi), random.uniform(0.04, 0.16), random.uniform(0.015, 0.05)) for _ in range(70)]
def corona(r, a):
    m = CORONA_HOLE
    if r < m - 0.02: return (255, 255, 255, 0)
    d = max(0.0, r - m)
    v = math.exp(-(d / 0.018) ** 2) + math.exp(-d / 0.05) * 0.6 + math.exp(-d / 0.16) * 0.18
    for ang, length, width in streams:
        da = abs(math.atan2(math.sin(a - ang), math.cos(a - ang)))
        v += 0.45 * math.exp(-(da / width) ** 2) * math.exp(-d / length)
    v = min(1.0, v) * (1 if r < 0.97 else max(0, (1 - r) / 0.03))
    return (255, 255, 255, clamp(v * 255))

def star(r, a):
    v = math.exp(-(r / 0.05) ** 2) + 0.7 * math.exp(-(r / 0.14) ** 2) + 0.25 * math.exp(-r / 0.3)
    for k in range(8):
        ang = k * math.pi / 4 + math.pi / 8
        length = 1.0 if k in (1, 5) else 0.35
        da = abs(math.atan2(math.sin(a - ang), math.cos(a - ang)))
        v += math.exp(-(da * max(r, 0.01) / 0.007) ** 2) * max(0, 1 - r / length) * 0.9
    return (255, 255, 255, clamp(min(1, v) * 255 * (1 if r < 0.98 else 0)))

# Cielo: color según la etapa (azul -> naranja -> rojo oscuro -> negro) y más claro hacia el horizonte
SKY_STOPS = [(0, hexc("#f4b070")), (0.45, hexc("#ec6c1a")), (0.75, hexc("#6e260c")), (1, hexc("#050405"))]
HORIZON_STOPS = [(0, hexc("#f8c890")), (0.45, hexc("#f08a3a")), (0.75, hexc("#a8441a")), (1, hexc("#1a0c08"))]
MOON_STOPS = [(0, hexc("#3e5490")), (0.4, hexc("#3a2418")), (0.75, hexc("#160a06")), (1, hexc("#030303"))]

def sky_rgba(stage, elev_deg):
    d = stage / STAGES
    strength = 0.97 * min(1, d / 0.3) ** 0.6
    if elev_deg < 0:
        fall = max(0, 1 + elev_deg / 10) * 0.8
    else:
        fall = 0.8 + 0.2 * min(1, elev_deg / 50) ** 0.7
    h = max(0, 1 - max(0, elev_deg) / 40)
    top, hor = lerp_colors(SKY_STOPS, d), lerp_colors(HORIZON_STOPS, d)
    rgb = [t + (o - t) * h for t, o in zip(top, hor)]
    return (*[clamp(c * 255) for c in rgb], clamp(strength * fall * 255))

def dome_top(stage, n=256):
    im = Image.new("RGBA", (n, n)); px = im.load()
    for y in range(n):
        for x in range(n):
            u, v = (x + 0.5) / n * 2 - 1, (y + 0.5) / n * 2 - 1
            dist = math.hypot(u, v) * DOME
            px[x, y] = sky_rgba(stage, math.degrees(math.atan2(DOME, dist)))
    return im

SIDE_H = 176
def dome_side(stage, n=256):
    im = Image.new("RGBA", (n, SIDE_H)); px = im.load()
    for y in range(SIDE_H):
        h = DOME - (y + 0.5) / SIDE_H * (DOME - DOME_LOW)
        for x in range(n):
            u = ((x + 0.5) / n * 2 - 1) * DOME
            px[x, y] = sky_rgba(stage, math.degrees(math.atan2(h, math.hypot(DOME, u))))
    return im

# ---------------- atlas (una sola textura para la entidad) ----------------
AW, AH = 2048, 2048
atlas = Image.new("RGBA", (AW, AH))
UV = {}
PAD = 4  # borde alrededor de cada pieza, copiando su orilla, para que no se cuelen líneas de la vecina
cursor = {"x": 0, "y": 0, "row": 0}
def place(name, im):
    w, h = im.width + 2 * PAD, im.height + 2 * PAD
    if cursor["x"] + w > AW:
        cursor["x"], cursor["y"], cursor["row"] = 0, cursor["y"] + cursor["row"], 0
    x, y = cursor["x"] + PAD, cursor["y"] + PAD
    big = im.resize((w, h), Image.NEAREST)          # orilla estirada
    big.paste(im, (PAD, PAD))
    atlas.paste(big, (x - PAD, y - PAD))
    UV[name] = (x, y, im.width, im.height)
    cursor["x"] += w
    cursor["row"] = max(cursor["row"], h)

place("sun", disk(hexc("#fffbea")))
for k in range(8):
    place(f"moon_{k}", disk(lerp_colors(MOON_STOPS, k / 7)))
place("glow", radial(256, glow))
place("corona", radial(256, corona))
place("flash", radial(256, star))
for s in range(1, STAGES + 1):
    place(f"top_{s}", dome_top(s))
for s in range(1, STAGES + 1):
    place(f"side_{s}", dome_side(s))
assert cursor["y"] + cursor["row"] <= AH
atlas.save(f"{RP}/textures/entity/eclipse_sky.png")

# ---------------- modelo ----------------
P = 16  # píxeles por bloque
def face(name, f):
    x, y, w, h = UV[name]
    return {f: {"uv": [x, y], "uv_size": [w, h]}}

def flat(name, half, height):
    return {"origin": [-half * P, height * P, -half * P], "size": [2 * half * P, 0, 2 * half * P],
            "uv": face(name, "down")}

bones = [{"name": "root", "pivot": [0, 0, 0]}]
for s in range(1, STAGES + 1):
    D, L, T = DOME * P, DOME_LOW * P, (DOME - DOME_LOW) * P
    bones.append({"name": f"dome_{s}", "parent": "root", "pivot": [0, 0, 0], "cubes": [
        {"origin": [-D, D, -D], "size": [2 * D, 0, 2 * D], "uv": face(f"top_{s}", "down")},
        {"origin": [-D, L, D], "size": [2 * D, T, 0], "uv": face(f"side_{s}", "north")},
        {"origin": [-D, L, -D], "size": [2 * D, T, 0], "uv": face(f"side_{s}", "south")},
        {"origin": [D, L, -D], "size": [0, T, 2 * D], "uv": face(f"side_{s}", "west")},
        {"origin": [-D, L, -D], "size": [0, T, 2 * D], "uv": face(f"side_{s}", "east")},
    ]})
bones.append({"name": "sun", "parent": "root", "pivot": [0, H["sun"] * P, 0], "cubes": [flat("sun", HALF["sun"], H["sun"])]})
bones.append({"name": "moon", "parent": "root", "pivot": [0, H["moon"] * P, 0]})
for k in range(8):
    bones.append({"name": f"moon_{k}", "parent": "moon", "pivot": [0, H["moon"] * P, 0],
                  "cubes": [flat(f"moon_{k}", HALF["moon"], H["moon"])]})
for n in ("glow", "corona", "flash"):
    bones.append({"name": n, "parent": "root", "pivot": [0, H[n] * P, 0], "cubes": [flat(n, HALF[n], H[n])]})

json.dump({"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.eclipse_sky", "texture_width": AW, "texture_height": AH,
                    "visible_bounds_width": 2 * DOME + 4, "visible_bounds_height": DOME - DOME_LOW + 4,
                    "visible_bounds_offset": [0, (DOME + DOME_LOW) / 2, 0]},
    "bones": bones}]}, open(f"{RP}/models/entity/eclipse_sky.geo.json", "w"), indent=1)

# ---------------- línea de tiempo (la calcula el celular de cada jugador, cuadro por cuadro) ----------------
# t = segundos desde que empezó el eclipse = tiempo de vida de la entidad + "variant"
# (variant = segundos que ya llevaba el eclipse cuando apareció la entidad, para los que entran tarde).
PARTIAL = 22.0                     # segundos que tarda la luna en tapar el sol
MOON_FROM = (1.0, -1.0)            # de qué lado viene la luna (x, z)
MAX_VARIANT = 30
fl = math.hypot(*MOON_FROM); FX, FZ = MOON_FROM[0] / fl, MOON_FROM[1] / fl
R2 = MOON_DEG / SUN_DEG
MOON_PX = H["moon"] * P
FLASH_PX = -tan(SUN_DEG * 0.92) * H["flash"] * P
Pp = f"{PARTIAL}"
TIMELINE = [
    "v.t = q.life_time + q.variant;",
    f"v.u = math.clamp(v.t / {Pp}, 0, 1);",
    "v.sm = v.u * v.u * (3 - 2 * v.u);",
    f"v.off = v.t < {Pp} ? 2.45 - 2.33 * v.sm : 0.12 * (1 - math.clamp((v.t - {Pp}) / 2, 0, 1));",
    "v.dd = math.max(v.off, 0.0001);",
    f"v.a1 = math.acos(math.clamp((v.dd * v.dd + 1 - {R2 * R2:.5f}) / (2 * v.dd), -1, 1)) * math.pi / 180;",
    f"v.a2 = {R2 * R2:.5f} * math.acos(math.clamp((v.dd * v.dd + {R2 * R2 - 1:.5f}) / (2 * v.dd * {R2:.5f}), -1, 1)) * math.pi / 180;",
    f"v.kk = 0.5 * math.sqrt(math.max(0, ({1 + R2:.5f} - v.dd) * (v.dd - {R2 - 1:.5f}) * (v.dd + {R2 - 1:.5f}) * (v.dd + {1 + R2:.5f})));",
    f"v.cov = v.off >= {1 + R2:.5f} ? 0 : (v.off <= {R2 - 1:.5f} ? 1 : (v.a1 + v.a2 - v.kk) / math.pi);",
    f"v.dark = v.t < {Pp} ? math.pow(math.clamp((v.cov - 0.05) / 0.9, 0, 1), 1.2) : 1;",
    f"v.stage = v.t < {Pp} ? math.round(v.dark * {STAGES}) : 0;",
    "v.moonk = math.round(v.dark * 7);",
    f"v.mpx = math.sin(v.off * {SUN_DEG}) / math.cos(v.off * {SUN_DEG}) * {MOON_PX};",
    f"v.glow = v.t < {PARTIAL + 0.5} ? 0.35 + 0.65 * math.pow(1 - v.cov, 0.3) : 0;",
    f"v.flash = (v.t >= {PARTIAL - 0.3} && v.t < {PARTIAL + 2.5}) ? math.clamp(v.t < {PARTIAL + 0.3} ? (v.t - {PARTIAL - 0.3}) / 0.6 : 1 - (v.t - {PARTIAL + 0.3}) / 2.2, 0, 1) : 0;",
    f"v.cu = math.clamp((v.t - {PARTIAL + 0.75}) / 2.25, 0, 1);",
    f"v.corona = v.t < {PARTIAL + 0.75} ? 0 : (0.85 + 0.15 * v.cu * v.cu * (3 - 2 * v.cu)) * (1 + 0.02 * math.sin(v.t * 127));",
    f"v.sun = v.t < {PARTIAL + 2};",
    # Solo lo ve quien lo lleva en el hombro (los demás jugadores están más lejos de él)
    "v.show = q.distance_from_camera < 5;",
]

# ---------------- animación: anula el giro del jugador y mueve luna/destello ----------------
json.dump({"format_version": "1.8.0", "animations": {"animation.eclipse_sky.follow": {"loop": True, "bones": {
    "root": {"rotation": [0, "-q.body_y_rotation", 0]},
    "moon": {"position": [f"v.mpx * {FX:.5f}", 0, f"v.mpx * {FZ:.5f}"]},
    "flash": {"position": [round(FLASH_PX * FX, 3), 0, round(FLASH_PX * FZ, 3)], "scale": "math.max(0.001, v.flash)"},
    "glow": {"scale": "math.max(0.001, v.glow)"},
    "corona": {"scale": "math.max(0.001, v.corona)"},
}}}}, open(f"{RP}/animations/eclipse_sky.animation.json", "w"), indent=1)

# ---------------- cómo se dibuja (3 pasadas: cielo, sol/luna, brillos) ----------------
def rc(material, visible):
    return {"geometry": "Geometry.default", "materials": [{"*": f"Material.{material}"}],
            "textures": ["Texture.default"], "ignore_lighting": True,
            "part_visibility": [{"*": False}, {"root": True}] + [{b: e} for b, e in visible.items()]}
json.dump({"format_version": "1.8.0", "render_controllers": {
    "controller.render.eclipse_sky_dome": rc("blend", {f"dome_{k}": f"v.show && v.stage == {k}" for k in range(1, STAGES + 1)}),
    "controller.render.eclipse_sky_solid": rc("solid", {"sun": "v.show && v.sun", "moon": True,
                                                        **{f"moon_{k}": f"v.show && v.moonk == {k}" for k in range(8)}}),
    "controller.render.eclipse_sky_glow": rc("blend", {n: f"v.show && v.{n} > 0.01" for n in ("glow", "corona", "flash")}),
}}, open(f"{RP}/render_controllers/eclipse_sky.render_controllers.json", "w"), indent=1)

json.dump({"format_version": "1.10.0", "minecraft:client_entity": {"description": {
    "identifier": "eclipse:sky",
    "materials": {"blend": "entity_alphablend", "solid": "entity_alphatest"},
    "textures": {"default": "textures/entity/eclipse_sky"},
    "geometry": {"default": "geometry.eclipse_sky"},
    "animations": {"follow": "animation.eclipse_sky.follow"},
    "scripts": {"pre_animation": TIMELINE, "animate": ["follow"]},
    "render_controllers": ["controller.render.eclipse_sky_dome", "controller.render.eclipse_sky_solid",
                           "controller.render.eclipse_sky_glow"],
    "enable_attachables": False}}}, open(f"{RP}/entity/eclipse_sky.entity.json", "w"), indent=1)

# ---------------- entidad (comportamiento) ----------------
groups = {f"eclipse:at_{n}": {"minecraft:variant": {"value": n}} for n in range(1, MAX_VARIANT + 1)}
events = {f"eclipse:at_{n}": {"add": {"component_groups": [f"eclipse:at_{n}"]}} for n in range(1, MAX_VARIANT + 1)}
json.dump({"format_version": "1.20.80", "minecraft:entity": {
    "description": {"identifier": "eclipse:sky", "is_spawnable": False, "is_summonable": True, "is_experimental": False},
    "component_groups": groups,
    "components": {
        # "parrot_tame" deja que vaya montada en el hombro del jugador
        "minecraft:type_family": {"family": ["eclipse_sky", "parrot_tame", "inanimate"]},
        "minecraft:variant": {"value": 0},
        "minecraft:collision_box": {"width": 0.1, "height": 0.1},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:damage_sensor": {"triggers": {"cause": "all", "deals_damage": False}},
        "minecraft:health": {"value": 1, "max": 1},
        "minecraft:knockback_resistance": {"value": 1},
        "minecraft:fire_immune": {},
        "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "suffocate_time": 0}},
    "events": events}}, open(f"{BP}/entities/eclipse_sky.json", "w"), indent=1)

# Los mismos números para el script del servidor (hora, niebla)
open(f"{BP}/scripts/timeline.js", "w").write(
    "// Generado por tools/build.py: no lo edites a mano, cambia build.py y vuelve a correrlo.\n"
    f"export const PARTIAL_SECONDS = {PARTIAL};\n"
    f"export const SUN_DEG = {SUN_DEG};\n"
    f"export const MOON_DEG = {MOON_DEG};\n"
    f"export const MAX_VARIANT = {MAX_VARIANT};\n")

# ---------------- sol y luna normales del juego, redondos ----------------
def sun_env(r, a):
    if r < 0.27: return (255, 255, 250, 255)
    return (255, 252, 235, clamp(math.exp(-(r - 0.27) / 0.16) * 255))
radial(32, sun_env).save(f"{RP}/textures/environment/sun.png")
moon = Image.new("RGBA", (128, 64), (0, 0, 0, 0)); mp = moon.load()
for k in range(8):
    th = k * math.pi / 4
    for y in range(32):
        for x in range(32):
            nx, ny = (x - 15.5) / 7.5, (y - 15.5) / 7.5
            if nx * nx + ny * ny > 1 or k == 4: continue
            s = math.sqrt(max(0, 1 - ny * ny))
            if nx <= math.cos(th) * s if k < 4 else nx >= -math.cos(th) * s:
                c = 0.86 if (int(x * 1.7 + y * 0.6) % 7 == 0 and (x + y) % 3 == 0) else 1
                mp[(k % 4) * 32 + x, (k // 4) * 32 + y] = (clamp(225 * c), clamp(228 * c), clamp(240 * c), 255)
moon.save(f"{RP}/textures/environment/moon_phases.png")

# ---------------- niebla: tiñe lo lejano y el horizonte ----------------
fogs = {"dark1": "#e0a070", "dark2": "#d0682a", "dark3": "#7a3214", "dark4": "#24100a", "totality": "#5a2a12"}
for n, c in fogs.items():
    json.dump({"format_version": "1.16.100", "minecraft:fog_settings": {
        "description": {"identifier": f"eclipse:{n}"},
        "distance": {"air": {"fog_start": 45, "fog_end": 160, "fog_color": c, "render_distance_type": "fixed"}}}},
        open(f"{RP}/fogs/eclipse_{n}.json", "w"), indent=1)

# ---------------- icono ----------------
icon = Image.new("RGBA", (128, 128), (10, 12, 24, 255)); d = ImageDraw.Draw(icon)
for y in range(84, 128):
    k = (y - 84) / 44; d.line([(0, y), (127, y)], fill=(int(10 + 150 * k), int(12 + 60 * k), int(24 + 6 * k), 255))
cor = radial(256, corona).resize((110, 110), Image.LANCZOS)
icon.alpha_composite(cor, (9, 4)); r = 110 * CORONA_HOLE / 2
d.ellipse([64 - r, 59 - r, 64 + r, 59 + r], fill=(3, 3, 5, 255))
icon.save(f"{RP}/pack_icon.png"); icon.save(f"{BP}/pack_icon.png")
print("listo:", {k: round(v, 2) for k, v in HALF.items()})
