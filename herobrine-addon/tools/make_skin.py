import random, sys
from PIL import Image
random.seed(7)
img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
px = img.load()

def h(c):
    c = c.lstrip("#"); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

HAIR = [h("37270d"), h("2f210b"), h("3d2b11")]
SKIN = [h("b48a6e"), h("a88369"), h("af866b")]
SKIN_D = h("9a6a52")
BEARD = [h("5a3720"), h("4e2f1a")]
NOSE = h("8a5a42")
EYE = h("ffffff")
SHIRT = [h("0ba9ac"), h("0a9fa2"), h("0cb4b7")]
PANTS = [h("4e3fb4"), h("473aa8"), h("5243bb")]
PANTS_D = h("3e3699")
SHOE = [h("5e5e5e"), h("515151")]

def fill(x, y, w, hgt, pal):
    for i in range(x, x + w):
        for j in range(y, y + hgt):
            px[i, j] = random.choice(pal)

def put(x, y, c): px[x, y] = c

# ---------- HEAD (uv 0,0 ; 8x8x8) ----------
fill(8, 0, 8, 8, HAIR)            # top
fill(16, 0, 8, 8, SKIN)           # bottom (chin)
fill(24, 8, 8, 8, HAIR)           # back
# front face at (8,8)
fx, fy = 8, 8
fill(fx, fy, 8, 8, SKIN)
fill(fx, fy, 8, 2, HAIR)          # hair rows 0-1
put(fx+0, fy+2, HAIR[0]); put(fx+7, fy+2, HAIR[1])
for x in (1, 2, 5, 6): put(fx+x, fy+4, EYE)   # white eyes
put(fx+3, fy+5, NOSE); put(fx+4, fy+5, NOSE)  # nose
put(fx+3, fy+6, h("7b4237")); put(fx+4, fy+6, h("7b4237"))  # mouth
for x in (2, 5): put(fx+x, fy+6, BEARD[0])  # beard
for x in (1, 6): put(fx+x, fy+6, SKIN_D)
for x in range(2, 6): put(fx+x, fy+7, BEARD[1])
# sides: right (0,8) front edge = col 7 ; left (16,8) front edge = col 0
for sx, front in ((0, 7), (16, 0)):
    fill(sx, 8, 8, 8, SKIN)
    fill(sx, 8, 8, 2, HAIR)
    for c in range(8):
        dist = abs(c - front)          # 0 = next to face
        if dist >= 4:                  # back half is hair
            fill(sx + c, 10, 1, 6, HAIR)
    for r in range(2, 6):              # sideburn next to face
        put(sx + (6 if front == 7 else 1), 8 + r, HAIR[1])
    for r in (6, 7):
        put(sx + front, 8 + r, BEARD[0])

# ---------- BODY (uv 16,16 ; 8x12x4) ----------
fill(20, 16, 8, 4, SHIRT)   # top
fill(28, 16, 8, 4, SHIRT)   # bottom
fill(16, 20, 4, 12, SHIRT)  # right
fill(20, 20, 8, 12, SHIRT)  # front
fill(28, 20, 4, 12, SHIRT)  # left
fill(32, 20, 8, 12, SHIRT)  # back
for x in range(2, 6): put(20 + x, 20, SKIN[1])   # neck under the beard
put(23, 21, SKIN[0]); put(24, 21, SKIN[0])
put(25, 31, PANTS[0]); put(26, 31, PANTS[0]); put(27, 31, PANTS[0])  # shirt tucked

# ---------- ARM / LEG helper (4x12x4) ----------
def limb(u, v, kind):
    faces = [(u+4, v, 4, 4, "top"), (u+8, v, 4, 4, "bottom"),
             (u, v+4, 4, 12, "s"), (u+4, v+4, 4, 12, "s"),
             (u+8, v+4, 4, 12, "s"), (u+12, v+4, 4, 12, "s")]
    for x, y, w, hh, f in faces:
        if kind == "arm":
            if f == "top": fill(x, y, w, hh, SHIRT)
            elif f == "bottom": fill(x, y, w, hh, SKIN)
            else:
                fill(x, y, w, 4, SHIRT)       # short sleeve
                fill(x, y+4, w, 8, SKIN)
        else:
            if f == "top": fill(x, y, w, hh, PANTS)
            elif f == "bottom": fill(x, y, w, hh, SHOE)
            else:
                fill(x, y, w, 10, PANTS)
                put(x+1, y+6, PANTS_D); put(x+2, y+6, PANTS_D)  # knee patch
                fill(x, y+10, w, 2, SHOE)     # gray shoes

limb(40, 16, "arm")   # right arm
limb(32, 48, "arm")   # left arm
limb(0, 16, "leg")    # right leg
limb(16, 48, "leg")   # left leg

img.save(sys.argv[1])
