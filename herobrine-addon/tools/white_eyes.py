# Uso: python3 -I white_eyes.py entrada.jpg salida.png
import sys
from PIL import Image, ImageFilter, ImageChops
im = Image.open(sys.argv[1]).convert("RGB")
W, H = im.size
box = (230, 55, 330, 100)                      # zona de los ojos
mask = Image.new("L", im.size, 0); mp = mask.load(); px = im.load()
for y in range(box[1], box[3]):
    for x in range(box[0], box[2]):
        r, g, b = px[x, y]
        iris = b > 100 and b - g > 40 and b - r > 10          # morado/azul
        white = r > 215 and g > 205 and b > 200               # parte blanca
        if iris or white: mp[x, y] = 255
mask = mask.filter(ImageFilter.MaxFilter(3))   # tapa los bordes del JPG
out = im.copy(); out.paste((255, 255, 255), mask=mask)
glow = mask.filter(ImageFilter.GaussianBlur(5)).point(lambda v: min(255, v * 2))
out = Image.composite(Image.new("RGB", im.size, (255, 255, 255)), out, glow.point(lambda v: v * 0.55))
out.paste((255, 255, 255), mask=mask)
out.save(sys.argv[2])
