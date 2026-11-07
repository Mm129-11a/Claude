"""Mide el Huevo Eburia en la foto de referencia y guarda lo medido en fuente/.

Uso:  python3 tools/extract_from_photo.py foto.jpg
Necesita: numpy, pillow, scipy, opencv-python-headless

Pasos:
 1. Cámara: con las esquinas del cubo grande y del chico marcadas en la foto calcula la
    cámara (la foto es un recorte, así que el centro óptico queda fuera de la imagen) y la
    posición y tamaño del cubo chico (en píxeles de textura: el grande mide 16).
 2. Textura: proyecta cada píxel de textura de cada cara visible sobre la foto y toma su color.
 3. Luz: las dos caras visibles del cubo grande tienen la misma textura; con eso se separa
    la textura de la luz de la cueva (luz suave de Minecraft = bilineal por cara).
 4. Limpieza: manchas azules de 2x2 exactas y colores reducidos a los tonos de la foto.
Guarda: fuente/camara_foto.json, fuente/textura_grande.png, fuente/textura_chica.png
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "fuente"

# Esquinas marcadas a mano en la foto (515x465), ampliando cada zona
BIG_2D = {"A": (75, 44), "C": (378, 86), "D": (196, 163), "E": (125, 328), "F": (46, 248)}
SMALL_2D = {"P": (209, 193), "Q": (320, 146), "R": (421, 236), "T": (306, 283), "U": (232, 381)}
G = 16  # lado del cubo grande en píxeles de textura
BIG_3D = {"A": (0, G, G), "C": (G, G, 0), "D": (G, G, G), "E": (G, 0, G), "F": (0, 0, G)}

# Tono final: el de la cara más iluminada de la foto (arriba del cubo chico), un 20 % más claro
CREAM_TARGET = np.array([182, 155, 131.0])
SPOT_COLOR = (76, 178, 216)   # azul de las manchas (uniforme, como en la foto)


def small_3d(sx, sy, sz, s):
    return {"P": (sx, sy + s, sz + s), "Q": (sx, sy + s, sz), "R": (sx + s, sy + s, sz),
            "T": (sx + s, sy + s, sz + s), "U": (sx + s, sy, sz + s)}


def project(pts, rv, t, f, cx, cy):
    R = Rot.from_rotvec(rv).as_matrix()
    pc = (R @ np.asarray(pts, float).T).T + t
    return np.stack([cx + f * pc[:, 0] / pc[:, 2], cy + f * pc[:, 1] / pc[:, 2]], 1), pc[:, 2]


# ---------------------------------------------------------------- 1. cámara
def fit_camera():
    def resid(x, small):
        r = []
        for d2, d3 in ((BIG_2D, BIG_3D), (SMALL_2D, small_3d(*small(x)))):
            k = list(d2)
            P, _ = project([d3[n] for n in k], x[0:3], x[3:6], x[6], x[7], x[8])
            r.append((P - np.array([d2[n] for n in k])).ravel())
        return np.concatenate(r)

    keys = list(BIG_2D)
    obj = np.array([BIG_3D[k] for k in keys], float)
    img = np.array([BIG_2D[k] for k in keys], float)
    best = None
    for f in np.geomspace(400, 3000, 25):
        for cx, cy in [(-240, 880), (-100, 700), (0, 600), (-400, 1000), (200, 700), (257, 232)]:
            K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]])
            ok, rv, t = cv2.solvePnP(obj, img, K, None, flags=cv2.SOLVEPNP_SQPNP)
            if not ok:
                continue
            x0 = np.concatenate([rv.ravel(), t.ravel(), [f, cx, cy], [15, 0, 0, 11]])
            sol = least_squares(resid, x0, args=(lambda x: x[9:13],), max_nfev=8000)
            _, z = project(obj, sol.x[0:3], sol.x[3:6], sol.x[6], sol.x[7], sol.x[8])
            if (z <= 0).any() or sol.x[6] <= 0 or sol.x[12] <= 0:
                continue
            e = np.sqrt(np.mean(sol.fun ** 2))
            if best is None or e < best[0]:
                best = (e, sol.x)
    e, free = best
    print(f"cámara: error medio {e:.2f} px")
    # cubo chico en píxeles enteros
    rows = []
    for s in (10, 11, 12):
        for sx in range(12, 18):
            for sz in range(-2, 3):
                for sy in (0, 1):
                    sol = least_squares(resid, free[:9], args=(lambda x, v=(sx, sy, sz, s): v,))
                    rows.append((np.sqrt(np.mean(sol.fun ** 2)), (sx, sy, sz, s), sol.x))
    rows.sort(key=lambda r: r[0])
    # entre las mejores (dentro del error de la foto) se prefiere apoyado en el suelo y alineado atrás
    good = [r for r in rows if r[0] < rows[0][0] + 0.4]
    good.sort(key=lambda r: (r[1][1] != 0, abs(r[1][2]), r[0]))
    e, small, x = good[0]
    print(f"cubo chico: esquina {small[:3]}, lado {small[3]} (error {e:.2f} px)")
    return {"rv": x[0:3].tolist(), "t": x[3:6].tolist(), "f": float(x[6]),
            "pp": [float(x[7]), float(x[8])], "small": list(small)}


class Scene:
    def __init__(self, cam):
        self.R = Rot.from_rotvec(cam["rv"]).as_matrix()
        self.t = np.array(cam["t"])
        self.f = cam["f"]
        self.cx, self.cy = cam["pp"]
        self.C = -self.R.T @ self.t
        sx, sy, sz, s = cam["small"]
        self.boxes = {"big": ((0, 0, 0), (G, G, G)), "small": ((sx, sy, sz), (sx + s, sy + s, sz + s))}

    def proj(self, p):
        pc = self.R @ p + self.t
        return np.array([self.cx + self.f * pc[0] / pc[2], self.cy + self.f * pc[1] / pc[2]])

    def visible(self, p):
        d = p - self.C
        L = np.linalg.norm(d)
        d = d / L
        for a, b in self.boxes.values():
            a = np.array(a, float) + 1e-3
            b = np.array(b, float) - 1e-3
            tmin, tmax = 0.0, L - 0.05
            hit = True
            for k in range(3):
                if abs(d[k]) < 1e-12:
                    if p[k] < a[k] or p[k] > b[k]:
                        hit = False
                        break
                else:
                    t1, t2 = sorted(((a[k] - self.C[k]) / d[k], (b[k] - self.C[k]) / d[k]))
                    tmin, tmax = max(tmin, t1), min(tmax, t2)
                    if tmin > tmax:
                        hit = False
                        break
            if hit:
                return False
        return True

    def rays(self, H, W, y0=0):
        ys, xs = np.mgrid[y0:H, 0:W]
        d = np.stack([(xs - self.cx) / self.f, (ys - self.cy) / self.f, np.ones_like(xs, float)], -1)
        return (self.R.T @ d.reshape(-1, 3).T).T


# ---------------------------------------------------------------- 2. muestreo
def face_point(box, face, u, v):
    (ax, ay, az), (bx, by, bz) = box
    if face == "up":
        return np.array([ax + u, by, az + v])
    if face == "south":
        return np.array([ax + u, by - v, bz])
    return np.array([bx, by - v, bz - u])           # east


def sample_faces(scene, photo):
    H, W = photo.shape[:2]

    def bilinear(x, y):
        x0, y0 = int(np.floor(x)), int(np.floor(y))
        if x0 < 0 or y0 < 0 or x0 + 1 >= W or y0 + 1 >= H:
            return None
        fx, fy = x - x0, y - y0
        return (photo[y0, x0] * (1 - fx) * (1 - fy) + photo[y0, x0 + 1] * fx * (1 - fy)
                + photo[y0 + 1, x0] * (1 - fx) * fy + photo[y0 + 1, x0 + 1] * fx * fy)

    out = {}
    for name, box in scene.boxes.items():
        n = int(box[1][0] - box[0][0])
        for face in ("up", "south"):
            obs = np.full((n, n, 3), np.nan)
            for j in range(n):
                for i in range(n):
                    vals = []
                    for du in (0.3, 0.5, 0.7):
                        for dv in (0.3, 0.5, 0.7):
                            p = face_point(box, face, i + du, j + dv)
                            if scene.visible(p):
                                c = bilinear(*scene.proj(p))
                                if c is not None:
                                    vals.append(c)
                    if len(vals) >= 7:
                        obs[j, i] = np.median(vals, axis=0)
            out[(name, face)] = obs
    return out


# ---------------------------------------------------------------- 3. textura sin luz
def basis(n):
    u, v = np.meshgrid((np.arange(n) + .5) / n, (np.arange(n) + .5) / n)
    return np.stack([np.ones_like(u), u, v, u * v], -1)


def solve_texture(faces):
    n = faces[0].shape[0]
    B = basis(n)
    logs = [np.log(np.maximum(f, 1)) for f in faces]
    masks = [~np.isnan(f[..., 0]) for f in faces]
    with np.errstate(all="ignore"):
        T = np.nanmean(np.stack([l - np.nanmean(l, axis=(0, 1)) for l in logs]), axis=0)
    for _ in range(60):
        Ls = []
        for l, m in zip(logs, masks):
            Lf = np.zeros_like(l)
            for c in range(3):
                coef = np.linalg.lstsq(B[m], (l[..., c] - T[..., c])[m], rcond=None)[0]
                Lf[..., c] = B @ coef
            Ls.append(Lf)
        num = np.zeros_like(T)
        den = np.zeros(T.shape[:2])
        for l, m, Lf in zip(logs, masks, Ls):
            num[m] += (l - Lf)[m]
            den[m] += 1
        T = np.where(den[..., None] > 0, num / np.maximum(den, 1)[..., None], T)
    have = den > 0
    if not have.all():
        yy, xx = np.nonzero(have)
        for j, i in zip(*np.nonzero(~have)):
            k = np.argmin((yy - j) ** 2 + (xx - i) ** 2)
            T[j, i] = T[yy[k], xx[k]]
    # degradado común a las caras: es luz, no textura
    spot = (T[..., 2] - T[..., 0]) > 0.25
    A = B[..., :3]
    for c in range(3):
        coef = np.linalg.lstsq(A[~spot], T[..., c][~spot], rcond=None)[0]
        T[..., c] -= A @ coef - coef[0]
    return np.exp(T)


# ---------------------------------------------------------------- 4. limpieza
def kmeans(x, k, it=50):
    c = np.array(sorted(x[np.random.default_rng(0).choice(len(x), k, replace=False)].tolist(), key=sum))
    for _ in range(it):
        lab = ((x[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        c = np.array([x[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
    return c


def clean(textures):
    prepared, creams = {}, []
    for name, (T, nspots) in textures.items():
        n = T.shape[0]
        blue = T[..., 2] / T[..., 0]
        spots = np.zeros((n, n), bool)
        used = np.zeros((n, n), bool)
        for _ in range(nspots):                       # manchas de 2x2
            best = None
            for j in range(n - 1):
                for i in range(n - 1):
                    if used[j:j + 2, i:i + 2].any():
                        continue
                    sc = blue[j:j + 2, i:i + 2].sum()
                    if best is None or sc > best[0]:
                        best = (sc, j, i)
            _, j, i = best
            spots[j:j + 2, i:i + 2] = True
            used[max(0, j - 1):j + 3, max(0, i - 1):i + 3] = True
        T = T / np.median(T[~spots], axis=0) * CREAM_TARGET
        halo = (T[..., 2] / T[..., 0] > 0.9) & ~spots
        prepared[name] = (T, spots, halo)
        creams.append(T[~spots & ~halo])
    pal = kmeans(np.concatenate(creams), 4)
    out = {}
    for name, (T, spots, halo) in prepared.items():
        n = T.shape[0]
        q = np.zeros((n, n, 3), np.uint8)
        for j in range(n):
            for i in range(n):
                p = T[j, i]
                if spots[j, i]:
                    q[j, i] = SPOT_COLOR
                elif halo[j, i]:
                    q[j, i] = np.round(pal[np.abs(pal.mean(1) - p.mean()).argmin()])
                else:
                    q[j, i] = np.round(pal[((pal - p) ** 2).sum(1).argmin()])
        # quitar píxeles sueltos: la foto muestra zonas, no puntitos aislados
        for _ in range(2):
            r = q.copy()
            for j in range(n):
                for i in range(n):
                    if spots[j, i]:
                        continue
                    nb = [tuple(q[jj, ii]) for jj, ii in ((j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1))
                          if 0 <= jj < n and 0 <= ii < n and not spots[jj, ii]]
                    if nb and tuple(q[j, i]) not in nb:
                        vals, counts = np.unique(np.array(nb), axis=0, return_counts=True)
                        r[j, i] = vals[counts.argmax()]
            q = r
        out[name] = q
    return out


def main(photo_path):
    photo = np.array(Image.open(photo_path).convert("RGB")).astype(float)
    cam = fit_camera()
    scene = Scene(cam)
    obs = sample_faces(scene, photo)
    big = solve_texture([obs[("big", "up")], obs[("big", "south")]])
    small = solve_texture([obs[("small", "up")], obs[("small", "south")]])
    tex = clean({"big": (big, 4), "small": (small, 2)})
    SRC.mkdir(exist_ok=True)
    Image.fromarray(tex["big"]).save(SRC / "textura_grande.png")
    Image.fromarray(tex["small"]).save(SRC / "textura_chica.png")
    (SRC / "camara_foto.json").write_text(json.dumps(cam, indent=1) + "\n")
    print("guardado en", SRC)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 tools/extract_from_photo.py foto.jpg")
    main(sys.argv[1])
