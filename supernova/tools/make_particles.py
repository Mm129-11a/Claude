"""Genera las partículas de la supernova (SupernovaRP/particles/*.json).

Uso:  python3 tools/make_particles.py

Los tamaños son el radio en bloques. La estrella sale a 32 bloques; con ese radio se ve en
pantalla del mismo tamaño que en las fotos de referencia.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "SupernovaRP" / "particles"
T = "textures/particle/supernova/"
A = "variable.particle_age"


def ease_out(t_end, power=3):
    return f"(1 - math.pow(1 - math.clamp({A} / {t_end}, 0, 1), {power}))"


def effect(ident, tex, lifetime, size, alpha, height, fps=None):
    uv = {"texture_width": 256, "texture_height": height}
    if fps:
        uv["flipbook"] = {"base_UV": [0, 0], "size_UV": [256, 256], "step_UV": [0, 256],
                          "frames_per_second": fps, "max_frame": height // 256, "loop": True}
    else:
        uv.update({"uv": [0, 0], "uv_size": [256, 256]})
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
                "minecraft:particle_motion_dynamic": {},
                "minecraft:particle_initialization": {"per_render_expression": f"variable.s = {size};"},
                "minecraft:particle_appearance_billboard": {
                    "size": ["variable.s", "variable.s"], "facing_camera_mode": "rotate_xyz", "uv": uv},
                "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, alpha]},
            },
        },
    }


EFFECTS = {
    # 1. La estrella: crece en 2 s, late, se hincha antes de explotar y se apaga al explotar
    "estrella": effect("supernova:estrella", "estrella", 6.6,
                       f"3.2 * ({ease_out(2.0)} + math.clamp(({A} - 5.0) / 1.0, 0, 1) * 0.3"
                       f" + math.sin({A} * 300) * 0.03)",
                       f"1 - math.clamp(({A} - 6.1) / 0.5, 0, 1)", 1536, fps=6),
    # 2. La explosión: se abre rápido y luego sigue creciendo despacio
    "explosion": effect("supernova:explosion", "explosion", 3.2,
                        f"4.0 + 6.0 * {ease_out(1.0)} + {A} * 0.6",
                        f"1 - math.clamp(({A} - 2.0) / 1.2, 0, 1)", 1536, fps=12),
    # 3. El destello: llena el cielo, blanco en el centro y rosa en los bordes de la pantalla
    "destello": effect("supernova:destello", "destello", 4.5,
                       f"10 + 24 * {ease_out(1.2, 2)}",
                       f"math.clamp({A} / 0.2, 0, 1) * (1 - math.clamp(({A} - 1.8) / 2.5, 0, 1))", 256),
}

if __name__ == "__main__":
    P.mkdir(parents=True, exist_ok=True)
    for old in P.glob("*.json"):
        old.unlink()
    for name, data in EFFECTS.items():
        (P / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("ok:", sorted(p.name for p in P.iterdir()))
