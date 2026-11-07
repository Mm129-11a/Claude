"""Genera las partículas de la supernova (SupernovaRP/particles/*.json).

Uso:  python3 tools/make_particles.py

Los tamaños salen de las capturas de referencia (pantalla de 2576x1171, campo de visión de 60°):
  - estrella: en la foto mide 158 px de radio -> 5,0 bloques a 32 bloques (y sus piezas igual)
  - explosión: el borde rosa a ~490 px        -> unos 15 bloques a 31 bloques
  - destello: llena la pantalla hasta el suelo -> 68 x 24 bloques a 35 bloques
(en las partículas de Bedrock el tamaño es la mitad del ancho y del alto)

Las capas que brillan (halo, brasas, núcleo, rayos, relámpagos, anillo y chispas) se suman a la
luz de lo que hay detrás (material aditivo); las sólidas (estrella, piezas, cuerpo de la
explosión, destello) se mezclan normal.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "SupernovaRP" / "particles"
T = "textures/particle/supernova/"
A = "variable.particle_age"
LIFE = "variable.particle_lifetime"

STAR_R = 5.15        # mitad del ancho de la textura de la estrella (5,0 bloques de bola / 0,97)
EXP_R = 19.3         # mitad del ancho del cuerpo de la explosión (borde rosa a 0,77 de la textura)
FLASH_H = 24.0       # mitad del alto del destello; el ancho es 2,85 veces (proporción de la captura)
STAR_LIFE = 3.35     # desde que está completa hasta que explota
STAR_FPS = 8         # 64 fotogramas = una vuelta en 8 s


def ease_out(t_end, power=3, age=A):
    return f"(1 - math.pow(1 - math.clamp({age} / {t_end}, 0, 1), {power}))"


def grid_uv(fps, cols, frames, cell, offset="0"):
    """Coordenadas del fotograma actual en una textura con los fotogramas en cuadrícula."""
    f = f"math.mod(math.floor({A} * {fps} + {offset}), {frames})"
    return [f"math.mod({f}, {cols}) * {cell}", f"math.floor({f} / {cols}) * {cell}"]


def particle(ident, tex, material, components):
    return {"format_version": "1.10.0",
            "particle_effect": {
                "description": {"identifier": ident,
                                "basic_render_parameters": {"material": material, "texture": T + tex}},
                "components": components}}


def single(lifetime):
    return {"minecraft:emitter_rate_instant": {"num_particles": 1},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_point": {"offset": [0, 0, 0]},
            "minecraft:particle_lifetime_expression": {"max_lifetime": lifetime},
            "minecraft:particle_initial_speed": 0}


def billboard(size_x, size_y, tex_w, tex_h, uv=(0, 0), uv_size=None):
    return {"size": [size_x, size_y], "facing_camera_mode": "rotate_xyz",
            "uv": {"texture_width": tex_w, "texture_height": tex_h, "uv": list(uv),
                   "uv_size": list(uv_size or (tex_w, tex_h))}}


def simple(ident, tex, material, lifetime, size, alpha, tex_size, spin=0.0, aspect=1.0, uv=(0, 0),
           uv_size=None, tint=(1, 1, 1)):
    w, h = tex_size
    c = single(lifetime)
    c.update({
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360" if spin else 0,
                                            "rotation_rate": spin},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_initialization": {"per_render_expression": f"variable.s = {size};"},
        "minecraft:particle_appearance_billboard": billboard(f"variable.s * {aspect}", "variable.s", w, h, uv, uv_size),
        "minecraft:particle_appearance_tinting": {"color": [*tint, alpha]},
    })
    return particle(ident, tex, material, c)


K = "math.pow(1 - math.clamp(variable.particle_age / variable.flight, 0, 1), 3)"   # 1 lejos -> 0 encajada
SWELL = f"(1 + math.clamp(({A} - 2.2) / 1.0, 0, 1) * 0.3)"                        # se hincha antes de explotar
TT = f"({A} / {LIFE})"

EFFECTS = {
    # ---------------------------------------------------------------- formación
    # Núcleo que brilla en el centro mientras llegan las piezas (dura variable.life, lo pone el script)
    "nucleo": simple("supernova:nucleo", "nucleo", "particles_add", "variable.life",
                     f"{STAR_R} * 1.2 * (0.45 + 0.55 * math.clamp({A} / (variable.life - 0.3), 0, 1))"
                     f" * (1 + 0.08 * math.sin({A} * 720))",
                     f"math.clamp({A} / 0.4, 0, 1) * (1 - math.clamp(({A} - variable.life + 0.3) / 0.3, 0, 1))",
                     (256, 256)),
    # Una pieza de la bola: vuela desde (ox, oy, oz) girando y se enciende al encajar.
    # El script pone su trozo de textura (pu, pv, pw, ph), su tamaño (sw, sh), el vuelo y la vida.
    "pieza": particle("supernova:pieza", "piezas", "particles_blend", {
        **single("variable.life"),
        "minecraft:particle_motion_parametric": {
            "relative_position": [f"variable.ox * {K}", f"variable.oy * {K}", f"variable.oz * {K}"],
            "rotation": f"variable.rot * {K}"},
        "minecraft:particle_appearance_billboard": billboard(
            "variable.sw", "variable.sh", "ATLAS_W", "ATLAS_H", ("variable.pu", "variable.pv"),
            ("variable.pw", "variable.ph")),
        "minecraft:particle_appearance_tinting": {"color": [
            f"0.5 + 0.5 * (1 - {K})", f"0.45 + 0.55 * (1 - {K})", f"0.4 + 0.6 * (1 - {K})",
            f"math.clamp({A} / 0.12, 0, 1) * (1 - math.clamp(({A} - variable.life + 0.15) / 0.15, 0, 1))"]},
    }),

    # ---------------------------------------------------------------- la estrella
    # La bola de lava en 3D: 64 fotogramas dando una vuelta, con las grietas latiendo
    "estrella": simple("supernova:estrella", "estrella_giro", "particles_blend", STAR_LIFE,
                       f"{STAR_R} * {SWELL} * (1 + math.sin({A} * 300) * 0.02)",
                       f"math.clamp({A} / 0.12, 0, 1) * (1 - math.clamp(({A} - 3.2) / 0.12, 0, 1))",
                       (2048, 2048), uv=grid_uv(STAR_FPS, 8, 64, 256), uv_size=(256, 256)),
    # Resplandor de calor alrededor de la estrella
    "halo": simple("supernova:halo", "halo", "particles_add", STAR_LIFE,
                   f"{STAR_R} * 1.9 * {SWELL} * (1 + math.sin({A} * 250) * 0.05)",
                   f"(0.5 + 0.15 * math.sin({A} * 400)) * math.clamp({A} / 0.4, 0, 1)"
                   f" * (1 - math.clamp(({A} - 3.2) / 0.12, 0, 1))", (256, 256)),
    # Brasas que se desprenden de la superficie y suben
    "brasas": particle("supernova:brasas", "brasa", "particles_add", {
        "minecraft:emitter_rate_steady": {"spawn_rate": 45, "max_particles": 200},
        "minecraft:emitter_lifetime_once": {"active_time": STAR_LIFE - 0.2},
        "minecraft:emitter_shape_sphere": {"radius": STAR_R * 0.9, "surface_only": True, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.2, 2.6)"},
        "minecraft:particle_initial_speed": "math.random(1.0, 3.0)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 0.6},
        "minecraft:particle_appearance_billboard": billboard(
            f"(0.12 + 0.12 * variable.particle_random_1) * (1 - {TT})",
            f"(0.12 + 0.12 * variable.particle_random_1) * (1 - {TT})", 64, 64),
        "minecraft:particle_appearance_tinting": {"color": [1, f"0.95 - 0.45 * {TT}", f"0.7 - 0.55 * {TT}", f"1 - {TT}"]},
    }),

    # ---------------------------------------------------------------- la explosión (por capas)
    # Núcleo blanco: el golpe de luz del primer instante
    "exp_nucleo": simple("supernova:exp_nucleo", "exp_nucleo", "particles_add", 0.9,
                         f"3 + {EXP_R} * 0.6 * {ease_out(0.25, 2)}",
                         f"0.7 * (1 - math.clamp(({A} - 0.1) / 0.8, 0, 1))", (256, 256)),
    # Cuerpo: blanco con el centro lavanda, manchas celestes y el borde rosa ondulando (4 fotogramas)
    "exp_cuerpo": simple("supernova:exp_cuerpo", "exp_cuerpo", "particles_blend", 3.2,
                         f"{EXP_R} * (0.25 + 0.75 * {ease_out(0.55)}) + {A} * 0.5",
                         f"1 - math.clamp(({A} - 2.0) / 1.2, 0, 1)", (1024, 1024), spin=3,
                         uv=grid_uv(6, 2, 4, 512), uv_size=(512, 512)),
    # Rayos de luz celestes y lavanda que salen del centro y giran despacio
    "exp_rayos": simple("supernova:exp_rayos", "exp_rayos", "particles_add", 2.8,
                        f"{EXP_R} * 0.95 * (0.3 + 0.7 * {ease_out(0.5)})",
                        f"0.9 * (1 - math.clamp(({A} - 1.5) / 1.3, 0, 1))", (512, 512), spin=12),
    # Relámpagos morados que chisporrotean (16 fotogramas)
    "exp_morados": simple("supernova:exp_morados", "exp_morados", "particles_blend", 2.6,
                          f"{EXP_R} * 0.8 * (0.3 + 0.7 * {ease_out(0.5)})",
                          f"1 - math.clamp(({A} - 1.8) / 0.8, 0, 1)", (2048, 2048), spin=-6,
                          uv=grid_uv(18, 4, 16, 512, "variable.particle_random_1 * 16"), uv_size=(512, 512)),
    # Anillo rosa de la onda expansiva
    "exp_anillo": simple("supernova:exp_anillo", "exp_anillo", "particles_add", 1.6,
                         f"{EXP_R} * (0.5 + 1.4 * {ease_out(1.6, 2)})",
                         f"1 - math.clamp({A} / 1.6, 0, 1)", (512, 512)),
    # Chispas blancas, rosas, moradas y celestes disparadas hacia afuera
    "chispas": particle("supernova:chispas", "brasa", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 240},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 3, "surface_only": True, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.0, 2.6)"},
        "minecraft:particle_initial_speed": "math.random(18, 42)",
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.1},
        "minecraft:particle_appearance_billboard": billboard(
            f"(0.25 + 0.3 * variable.particle_random_2) * (1 - {TT})",
            f"(0.25 + 0.3 * variable.particle_random_2) * (1 - {TT})", 64, 64),
        "minecraft:particle_appearance_tinting": {"color": [
            "variable.particle_random_1 < 0.5 ? 1 : (variable.particle_random_1 < 0.75 ? 0.75 : 0.88)",
            "variable.particle_random_1 < 0.25 ? 1 : (variable.particle_random_1 < 0.5 ? 0.55 : "
            "(variable.particle_random_1 < 0.75 ? 0.6 : 1))",
            "variable.particle_random_1 < 0.25 ? 1 : (variable.particle_random_1 < 0.5 ? 0.75 : 1)",
            f"1 - {TT} * {TT}"]},
    }),
    # Las piezas de la estrella saliendo disparadas al explotar, al rojo vivo y enfriándose
    "pieza_estalla": particle("supernova:pieza_estalla", "piezas", "particles_blend", {
        **single(2.2),
        "minecraft:particle_motion_parametric": {
            "relative_position": [f"variable.ox * {ease_out('variable.flight', 2)}",
                                  f"variable.oy * {ease_out('variable.flight', 2)}",
                                  f"variable.oz * {ease_out('variable.flight', 2)}"],
            "rotation": f"variable.rot * {A}"},
        "minecraft:particle_appearance_billboard": billboard(
            "variable.sw", "variable.sh", "ATLAS_W", "ATLAS_H", ("variable.pu", "variable.pv"),
            ("variable.pw", "variable.ph")),
        "minecraft:particle_appearance_tinting": {"color": [
            1, f"1 - 0.45 * math.clamp({A} / 1.2, 0, 1)", f"1 - 0.65 * math.clamp({A} / 1.2, 0, 1)",
            f"1 - math.clamp(({A} - 1.4) / 0.8, 0, 1)"]},
    }),

    # ---------------------------------------------------------------- el destello (captura 3)
    "destello": simple("supernova:destello", "destello", "particles_blend", 4.0,
                       f"{FLASH_H} * (0.3 + 0.7 * {ease_out(0.35, 2)})",
                       f"math.clamp({A} / 0.15, 0, 1) * (1 - math.clamp(({A} - 1.6) / 2.4, 0, 1))",
                       (1024, 359), aspect=2.85),
}


def atlas_size():
    from PIL import Image
    return Image.open(ROOT / "SupernovaRP" / "textures" / "particle" / "supernova" / "piezas.png").size


if __name__ == "__main__":
    P.mkdir(parents=True, exist_ok=True)
    for old in P.glob("*.json"):
        old.unlink()
    aw, ah = atlas_size()
    for name, data in EFFECTS.items():
        text = json.dumps(data, indent=2, ensure_ascii=False)
        text = text.replace('"ATLAS_W"', str(aw)).replace('"ATLAS_H"', str(ah))
        (P / f"{name}.json").write_text(text + "\n")
    print("ok:", sorted(p.name for p in P.iterdir()))
