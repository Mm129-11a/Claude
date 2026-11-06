# Genera texturas, partículas y nieblas del eclipse.
# Uso (desde eclipse-addon/):  python3 -I tools/build.py RP BP
# Los tamaños dependen de las distancias en BP/scripts/main.js (DIST); si cambias una, cambia la otra.
import json, math, os, sys
from PIL import Image, ImageDraw
RP, BP = sys.argv[1], sys.argv[2]
for d in ("particles", "textures/particle", "textures/environment", "fogs"):
    os.makedirs(f"{RP}/{d}", exist_ok=True)

# --- medidas (deben coincidir con main.js) ---
# 1.6 veces más lejos que antes: cada salto entre actualizaciones se nota menos
DIST = {"flash": 22.4, "moon": 23.2, "sun": 24.0, "corona": 24.3, "glow": 25.0, "sky": 30.4}
SUN_DEG, MOON_DEG, SKY_DEG = 5.5, 5.72, 28.0
DISK_FILL, CORONA_HOLE = 0.96, 0.385
t = lambda deg: math.tan(math.radians(deg))
SIZE = {
    "sun": DIST["sun"] * t(SUN_DEG) / DISK_FILL,
    "moon": DIST["moon"] * t(MOON_DEG) / DISK_FILL,
    "corona": DIST["corona"] * t(MOON_DEG) / CORONA_HOLE,
    "glow_in": DIST["glow"] * t(SUN_DEG * 3.2),
    "glow_out": DIST["glow"] * t(34),
    "flash": DIST["flash"] * t(22),
    "sky": DIST["sky"] * t(SKY_DEG),
}

def radial(size, f):
    im = Image.new("RGBA", (size, size)); px = im.load(); c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            px[x, y] = f(math.hypot(x - c, y - c) / (size / 2), math.atan2(y - c, x - c))
    return im
clamp = lambda v: max(0, min(255, int(v)))

# Disco redondo blanco (sol y luna; se pintan con color en la partícula)
radial(128, lambda r, a: (255, 255, 255, 255 if r < DISK_FILL - 0.02 else clamp((DISK_FILL + 0.02 - r) / 0.04 * 255))
       ).save(f"{RP}/textures/particle/eclipse_disk.png")
# Resplandor del sol
radial(128, lambda r, a: (255, 255, 255, clamp((math.exp(-r * 5) * 0.9 + math.exp(-r * 2.2) * 0.35) * (1 - r ** 6) * 255 if r < 1 else 0))
       ).save(f"{RP}/textures/particle/eclipse_glow.png")
# Mancha suave para oscurecer el cielo
radial(64, lambda r, a: (255, 255, 255, clamp(math.exp(-3 * r * r) * (1 - r ** 8) * 255) if r < 1 else 0)
       ).save(f"{RP}/textures/particle/eclipse_sky.png")

# Corona: anillo blanco pegado a la luna + rayos finos hacia afuera (como en el video)
import random
random.seed(3)
streams = [(random.uniform(0, 2 * math.pi), random.uniform(0.04, 0.16), random.uniform(0.015, 0.05)) for _ in range(70)]
def corona(r, a):
    m = CORONA_HOLE
    if r < m - 0.02: return (255, 255, 255, 0)
    d = max(0.0, r - m)
    ring = math.exp(-(d / 0.018) ** 2)
    v = ring + math.exp(-d / 0.05) * 0.6 + math.exp(-d / 0.16) * 0.18
    for ang, length, width in streams:
        da = abs(math.atan2(math.sin(a - ang), math.cos(a - ang)))
        v += 0.45 * math.exp(-(da / width) ** 2) * math.exp(-d / length)
    v = min(1.0, v) * (1 if r < 0.97 else max(0, (1 - r) / 0.03))
    return (255, 255, 255, clamp(v * 255))
radial(256, corona).save(f"{RP}/textures/particle/eclipse_corona.png")

# Destello (anillo de diamante): punto muy brillante con rayos, dos largos en diagonal
def star(r, a):
    v = math.exp(-(r / 0.05) ** 2) + 0.7 * math.exp(-(r / 0.14) ** 2) + 0.25 * math.exp(-r / 0.3)
    for k in range(8):
        ang = k * math.pi / 4 + math.pi / 8
        length = 1.0 if k in (1, 5) else 0.35
        da = abs(math.atan2(math.sin(a - ang), math.cos(a - ang)))
        v += math.exp(-(da * max(r, 0.01) / 0.007) ** 2) * max(0, 1 - r / length) * 0.9
    return (255, 255, 255, clamp(min(1, v) * 255 * (1 if r < 0.98 else 0)))
radial(256, star).save(f"{RP}/textures/particle/eclipse_flash.png")

# Sol y luna normales del juego, redondos
def sun(r, a):
    if r < 0.27: return (255, 255, 250, 255)
    return (255, 252, 235, clamp(math.exp(-(r - 0.27) / 0.16) * 255))
radial(32, sun).save(f"{RP}/textures/environment/sun.png")
moon = Image.new("RGBA", (128, 64), (0, 0, 0, 0)); mp = moon.load()
for k in range(8):
    th = k * math.pi / 4
    for y in range(32):
        for x in range(32):
            nx, ny = (x - 15.5) / 7.5, (y - 15.5) / 7.5
            if nx * nx + ny * ny > 1: continue
            s = math.sqrt(max(0, 1 - ny * ny))
            lit = nx <= math.cos(th) * s if k <= 4 else nx >= -math.cos(th) * s
            if k == 4: lit = False
            if lit:
                crater = 0.86 if (int(x * 1.7 + y * 0.6) % 7 == 0 and (x + y) % 3 == 0) else 1
                mp[(k % 4) * 32 + x, (k // 4) * 32 + y] = (clamp(225 * crater), clamp(228 * crater), clamp(240 * crater), 255)
moon.save(f"{RP}/textures/environment/moon_phases.png")

# --- partículas ---
# Solo se ve la copia más nueva: la anterior se apaga en cuanto llega la siguiente (sin copias dobles)
FRESH = "variable.particle_age < 0.075"
def particle(name, material, tex, size, color, life):
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": f"eclipse:{name}",
                        "basic_render_parameters": {"material": material, "texture": f"textures/particle/eclipse_{tex}"}},
        "components": {
            "minecraft:emitter_rate_instant": {"num_particles": 1},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_point": {"offset": [0, 0, 0]},
            "minecraft:particle_lifetime_expression": {"max_lifetime": life},
            "minecraft:particle_appearance_billboard": {
                "size": [round(size, 3), round(size, 3)], "facing_camera_mode": "rotate_xyz",
                "uv": {"texture_width": 1, "texture_height": 1, "uv": [0, 0], "uv_size": [1, 1]}},
            "minecraft:particle_appearance_tinting": {"color": color}}}}
def put(name, *a):
    json.dump(particle(name, *a), open(f"{RP}/particles/eclipse_{name}.json", "w"), indent=1)
def tent(r, g, b, alpha, additive=False):
    # misma fuerza que antes (cuando se veían ~4 copias juntas), pero en una sola
    eff = min(1, 2 * alpha) if additive else 1 - (1 - 0.25 * alpha) ** 2 * (1 - 0.75 * alpha) ** 2
    return [r, g, b, f"{FRESH} ? {eff:.3f} : 0"]
SOLID = f"{FRESH} ? 1 : 0"

put("sun", "particles_alpha", "disk", SIZE["sun"], [1, 0.985, 0.93, SOLID], 0.1)
def lerp_colors(stops, x):
    for (x0, c0), (x1, c1) in zip(stops, stops[1:]):
        if x <= x1:
            f = (x - x0) / (x1 - x0)
            return [round(a + (b - a) * f, 3) for a, b in zip(c0, c1)]
    return list(stops[-1][1])
hexc = lambda h: tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
# Color del cielo según qué tan tapado está el sol: azul -> naranja -> rojo oscuro -> negro
SKY_STOPS = [(0, hexc("#f4b070")), (0.45, hexc("#ec6c1a")), (0.75, hexc("#6e260c")), (1, hexc("#050405"))]
# Luna: azul oscuro con cielo claro, café oscuro con cielo naranja, negra al final
MOON_STOPS = [(0, hexc("#3e5490")), (0.4, hexc("#3a2418")), (0.75, hexc("#160a06")), (1, hexc("#030303"))]
for k in range(8):
    put(f"moon_{k}", "particles_alpha", "disk", SIZE["moon"], lerp_colors(MOON_STOPS, k / 7) + [SOLID], 0.1)
# Brillo del sol: dos capas que suman luz (aditivas)
for k in range(1, 7):
    put(f"glowin_{k}", "particles_add", "glow", SIZE["glow_in"], tent(1, 0.98, 0.9, 0.5 * k / 6, True), 0.1)
    put(f"glowout_{k}", "particles_add", "glow", SIZE["glow_out"], tent(1, 0.93, 0.8, 0.28 * k / 6, True), 0.1)
# Cielo: etapa s (1..12, color y fuerza) x banda de altura w (0 abajo, 2 arriba)
for st in range(1, 13):
    d = st / 12
    a = 0.6 * min(1, d / 0.45) ** 0.8
    for w, wf in enumerate((0.65, 0.85, 1.0)):
        put(f"sky_{st}_{w}", "particles_blend", "sky", SIZE["sky"], tent(*lerp_colors(SKY_STOPS, d), a * wf), 0.1)
for k in range(1, 5):
    put(f"corona_{k}", "particles_blend", "corona", SIZE["corona"], tent(1, 1, 1, 0.75 * k / 4), 0.1)
    put(f"flash_{k}", "particles_blend", "flash", SIZE["flash"], tent(1, 1, 1, 0.85 * k / 4), 0.1)

# --- niebla: oscurece lo lejano y deja el horizonte naranja (empieza lejos para no tapar el eclipse) ---
fogs = {"dark1": (45, 200, "#e0a070"), "dark2": (45, 170, "#d0682a"), "dark3": (45, 150, "#7a3214"),
        "dark4": (45, 130, "#24100a"), "totality": (45, 150, "#5a2a12")}
for n, (s, e, c) in fogs.items():
    json.dump({"format_version": "1.16.100", "minecraft:fog_settings": {
        "description": {"identifier": f"eclipse:{n}"},
        "distance": {"air": {"fog_start": s, "fog_end": e, "fog_color": c, "render_distance_type": "fixed"}}}},
        open(f"{RP}/fogs/eclipse_{n}.json", "w"), indent=1)

# Icono
icon = Image.new("RGBA", (128, 128), (10, 12, 24, 255)); d = ImageDraw.Draw(icon)
for y in range(84, 128):
    k = (y - 84) / 44; d.line([(0, y), (127, y)], fill=(int(10 + 150 * k), int(12 + 60 * k), int(24 + 6 * k), 255))
cor = Image.open(f"{RP}/textures/particle/eclipse_corona.png").resize((110, 110), Image.LANCZOS)
icon.alpha_composite(cor, (9, 4)); r = 110 * CORONA_HOLE / 2
d.ellipse([64 - r, 59 - r, 64 + r, 59 + r], fill=(3, 3, 5, 255))
icon.save(f"{RP}/pack_icon.png"); icon.save(f"{BP}/pack_icon.png")
print({k: round(v, 2) for k, v in SIZE.items()})
