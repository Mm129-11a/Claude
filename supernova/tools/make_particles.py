"""Genera las partículas de la supernova (SupernovaRP/particles/*.json).

Uso:  python3 tools/make_particles.py

Los tamaños salen de las fotos de referencia (pantalla de 2576x1171, campo de visión de 60°):
  - estrella: en la foto mide 158 px de radio  -> 5,0 bloques a 32 bloques
  - explosión: la textura abarca 560 px de radio -> 17,1 bloques a 31 bloques
  - destello: llena la pantalla hasta el suelo    -> 68 x 24 bloques a 35 bloques
(en las partículas de Bedrock el tamaño es la mitad del ancho y del alto)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "SupernovaRP" / "particles"
T = "textures/particle/supernova/"
A = "variable.particle_age"


def ease_out(t_end, power=3):
    return f"(1 - math.pow(1 - math.clamp({A} / {t_end}, 0, 1), {power}))"


def effect(ident, tex, tex_size, lifetime, size, alpha, spin=0.0, aspect=1.0):
    w, h = tex_size
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": ident,
                            "basic_render_parameters": {"material": "particles_blend", "texture": T + tex}},
            "components": {
                "minecraft:emitter_rate_instant": {"num_particles": 1},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_point": {"offset": [0, 0, 0]},
                "minecraft:particle_lifetime_expression": {"max_lifetime": lifetime},
                "minecraft:particle_initial_speed": 0,
                "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": spin},
                "minecraft:particle_motion_dynamic": {},
                "minecraft:particle_initialization": {"per_render_expression": f"variable.s = {size};"},
                "minecraft:particle_appearance_billboard": {
                    "size": [f"variable.s * {aspect}", "variable.s"],
                    "facing_camera_mode": "rotate_xyz",
                    "uv": {"texture_width": w, "texture_height": h, "uv": [0, 0], "uv_size": [w, h]}},
                "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, alpha]},
            },
        },
    }


STAR_R = 5.15        # 5,0 bloques de bola / 0,97 que ocupa en la textura
EXPLOSION_R = 17.1
FLASH_H = 24.0       # mitad del alto (llega hasta el suelo); el ancho es 2,85 veces (proporción de la foto)

EFFECTS = {
    # 1. La estrella (la bola de lava): crece en 2 s, gira despacio, late, se hincha y se apaga al explotar
    "estrella": effect("supernova:estrella", "estrella", (512, 512), 6.6,
                       f"{STAR_R} * ({ease_out(2.0)} + math.clamp(({A} - 5.0) / 1.0, 0, 1) * 0.3"
                       f" + math.sin({A} * 300) * 0.02)",
                       f"1 - math.clamp(({A} - 6.1) / 0.5, 0, 1)", spin=5),
    # 2. La explosión (foto 2): se abre en 0,6 s y sigue creciendo un poco
    "explosion": effect("supernova:explosion", "explosion", (512, 512), 3.2,
                        f"{EXPLOSION_R} * (0.3 + 0.7 * {ease_out(0.6)}) + {A} * 0.4",
                        f"1 - math.clamp(({A} - 2.0) / 1.2, 0, 1)", spin=4),
    # 3. El destello (foto 3): llena la pantalla y se desvanece
    "destello": effect("supernova:destello", "destello", (1024, 359), 4.0,
                       f"{FLASH_H} * (0.3 + 0.7 * {ease_out(0.35, 2)})",
                       f"math.clamp({A} / 0.15, 0, 1) * (1 - math.clamp(({A} - 1.6) / 2.4, 0, 1))",
                       aspect=2.85),
}

if __name__ == "__main__":
    P.mkdir(parents=True, exist_ok=True)
    for old in P.glob("*.json"):
        old.unlink()
    for name, data in EFFECTS.items():
        (P / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("ok:", sorted(p.name for p in P.iterdir()))
