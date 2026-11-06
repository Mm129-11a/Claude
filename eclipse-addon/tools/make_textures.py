# Dibuja las texturas del eclipse. Uso: python3 -I make_textures.py <carpeta RP> <carpeta BP>
import math, sys
from PIL import Image, ImageDraw, ImageFilter
RP, BP = sys.argv[1], sys.argv[2]

def radial(size, f):
    im = Image.new("RGBA", (size, size)); px = im.load(); c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            px[x, y] = f(math.hypot(x - c, y - c) / (size / 2), math.atan2(y - c, x - c))
    return im

# Luna: disco negro con borde suave (ocupa todo el cuadro)
moon = radial(128, lambda r, a: (4, 4, 6, 255 if r < 0.96 else int(max(0, 1 - (r - 0.96) / 0.04) * 255)))
moon.save(f"{RP}/textures/particle/eclipse_moon.png")

# Corona: anillo blanco brillante pegado a la luna y resplandor que se apaga hacia afuera.
# El disco de la luna mide 1/2.6 del cuadro (radio 0.385).
def corona(r, a):
    m = 0.385
    if r < m - 0.01: return (0, 0, 0, 0)
    d = r - m
    ring = math.exp(-(d / 0.012) ** 2)
    rays = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(a * 7 + 1.3) * math.sin(a * 3))
    glow = math.exp(-d / 0.09) * 0.85 * rays + math.exp(-d / 0.3) * 0.25
    v = min(1.0, ring + glow)
    if r > 0.98: v *= max(0, (1 - r) / 0.02)
    return (255, 255, int(250 - 20 * (1 - ring)), int(v * 255))
radial(256, corona).save(f"{RP}/textures/particle/eclipse_corona.png")

# Destello (anillo de diamante): estrella de 4 puntas finas con centro brillante
def star(r, a):
    core = math.exp(-(r / 0.06) ** 2) + 0.6 * math.exp(-(r / 0.18) ** 2)
    spike = 0
    for k in range(4):
        ang = a - (math.pi / 4 + k * math.pi / 2)
        da = abs(math.atan2(math.sin(ang), math.cos(ang)))
        spike = max(spike, math.exp(-(da * r / 0.006) ** 2) * max(0, 1 - r))
    v = min(1.0, core + spike)
    return (255, 255, 255, int(v * 255))
radial(256, star).save(f"{RP}/textures/particle/eclipse_flash.png")

# Sol redondo con resplandor, como en el video (reemplaza el sol cuadrado)
def sun(r, a):
    if r < 0.27: return (255, 255, 250, 255)
    v = math.exp(-(r - 0.27) / 0.16)
    return (255, 252, 235, int(v * 255))
radial(32, sun).save(f"{RP}/textures/environment/sun.png")

# Icono del pack
icon = Image.new("RGBA", (128, 128), (14, 16, 32, 255))
d = ImageDraw.Draw(icon)
for y in range(80, 128):
    t = (y - 80) / 48
    d.line([(0, y), (127, y)], fill=(int(14 + 190 * t), int(16 + 80 * t), int(32 + 10 * t), 255))
cor = Image.open(f"{RP}/textures/particle/eclipse_corona.png").resize((96, 96), Image.LANCZOS)
icon.alpha_composite(cor, (16, 8))
d.ellipse([16 + 48 - 18, 8 + 48 - 18, 16 + 48 + 18, 8 + 48 + 18], fill=(4, 4, 6, 255))
icon.save(f"{RP}/pack_icon.png"); icon.save(f"{BP}/pack_icon.png")
