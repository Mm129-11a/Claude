# Genera texturas, partículas y nieblas del eclipse.
# Uso (desde eclipse-addon/):  python3 -I tools/build.py RP BP
# Los tamaños dependen de las distancias en BP/scripts/main.js (DIST); si cambias una, cambia la otra.
import json, math, os, sys
from PIL import Image, ImageDraw
RP, BP = sys.argv[1], sys.argv[2]
for d in ("particles", "textures/particle", "textures/environment", "fogs"):
    os.makedirs(f"{RP}/{d}", exist_ok=True)

# --- medidas (deben coincidir con main.js) ---
DIST = {"flash": 14.0, "moon": 14.5, "sun": 15.0, "corona": 15.2, "glow": 15.6, "sky": 19.0}
SUN_DEG, MOON_DEG, SKY_DEG = 5.5, 5.72, 28.0
DISK_FILL, CORONA_HOLE = 0.96, 0.385
t = lambda deg: math.tan(math.radians(deg))
SIZE = {
    "sun": DIST["sun"] * t(SUN_DEG) / DISK_FILL,
    "moon": DIST["moon"] * t(MOON_DEG) / DISK_FILL,
    "corona": DIST["corona"] * t(MOON_DEG) / CORONA_HOLE,
    "glow": DIST["glow"] * t(26),
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
TENT = "(1 - math.abs(variable.particle_age - 0.1) / 0.1)"  # aparece y se va suave: sin parpadeo
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
def tent(r, g, b, alpha):
    return [r, g, b, f"{alpha:.3f} * {TENT}"]

put("sun", "particles_alpha", "disk", SIZE["sun"], [1, 0.985, 0.93, 1], 0.1)
sky_rgb = (0.47, 0.65, 1.0)
for k in range(8):                       # luna: azul oscuro con cielo claro, negra con cielo oscuro
    f = 1 - k / 7
    put(f"moon_{k}", "particles_alpha", "disk", SIZE["moon"],
        [round(c * 0.62 * f + 0.012, 3) for c in sky_rgb] + [1], 0.1)
for k in range(1, 7):
    put(f"glow_{k}", "particles_blend", "glow", SIZE["glow"], tent(1, 1, 0.97, 0.55 * k / 6), 0.2)
for k in range(1, 13):
    put(f"sky_{k}", "particles_blend", "sky", SIZE["sky"], tent(0.012, 0.016, 0.035, 0.6 * k / 12), 0.2)
for k in range(1, 5):
    put(f"corona_{k}", "particles_blend", "corona", SIZE["corona"], tent(1, 1, 1, 0.75 * k / 4), 0.2)
    put(f"flash_{k}", "particles_blend", "flash", SIZE["flash"], tent(1, 1, 1, 0.85 * k / 4), 0.2)

# --- niebla: oscurece lo lejano y deja el horizonte naranja (empieza lejos para no tapar el eclipse) ---
fogs = {"dark1": (40, 200, "#7f93bd"), "dark2": (34, 170, "#5d6684"), "dark3": (30, 150, "#5e4a48"),
        "dark4": (28, 130, "#4a3226"), "totality": (30, 150, "#8a4a26")}
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
