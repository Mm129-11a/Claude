"""Escribe los archivos del addon del Embestidor (entidad, cliente, controlador, manifiestos, nombres).

Uso:  python3 tools/make_addon.py      (el modelo, la textura y las animaciones los hace make_mob.py)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BP, RP = ROOT / "EmbestidorBP", ROOT / "EmbestidorRP"
ID = "embestidor:embestidor"

UUID_BP, UUID_BP_DATA, UUID_BP_SCRIPT = ("4cdbe38d-e469-45b1-8ed0-912aff788aca", "cce0bf66-867c-4fa0-afc9-cc5621dbcb71",
                                         "32e8b9f8-40ed-4a65-9572-9c9cc4c3bba8")
UUID_RP, UUID_RP_RES = "a622809c-f69c-4d14-beb7-affa47283321", "1a3e5297-b77c-4011-b9c0-11c9c46d14e3"
VERSION = [1, 0, 0]


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def manifests():
    write(BP / "manifest.json", {
        "format_version": 2,
        "header": {"name": "Embestidor (BP)", "description": "Un mob que embiste y explota al morir.",
                   "uuid": UUID_BP, "version": VERSION, "min_engine_version": [1, 21, 50]},
        "modules": [{"type": "data", "uuid": UUID_BP_DATA, "version": VERSION},
                    {"type": "script", "language": "javascript", "uuid": UUID_BP_SCRIPT,
                     "entry": "scripts/main.js", "version": VERSION}],
        "dependencies": [{"module_name": "@minecraft/server", "version": "1.16.0"},
                         {"uuid": UUID_RP, "version": VERSION}]})
    write(RP / "manifest.json", {
        "format_version": 2,
        "header": {"name": "Embestidor (RP)", "description": "Modelo, textura y animaciones del Embestidor.",
                   "uuid": UUID_RP, "version": VERSION, "min_engine_version": [1, 21, 50]},
        "modules": [{"type": "resources", "uuid": UUID_RP_RES, "version": VERSION}]})


def behavior():
    write(BP / "entities" / "embestidor.json", {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {"identifier": ID, "is_spawnable": True, "is_summonable": True},
            "components": {
                "minecraft:type_family": {"family": ["embestidor", "monster", "mob"]},
                "minecraft:health": {"value": 20, "max": 20},          # los mismos corazones que Steve
                "minecraft:collision_box": {"width": 0.9, "height": 1.1},
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
                "minecraft:movement": {"value": 0.25},
                "minecraft:movement.basic": {},
                "minecraft:jump.static": {},
                "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": True, "avoid_damage_blocks": True},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
                "minecraft:nameable": {},
                "minecraft:experience_reward": {"on_death": "query.last_hit_by_player ? 5 : 0"},
                # el daño lo pone la embestida (scripts/main.js); el golpe normal no quita nada
                "minecraft:attack": {"damage": 0},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.hurt_by_target": {"priority": 1},
                "minecraft:behavior.nearest_attackable_target": {
                    "priority": 2, "must_see": True, "reselect_targets": True, "within_radius": 20,
                    "entity_types": [{"filters": {"test": "is_family", "subject": "other", "value": "player"},
                                      "max_dist": 20}]},
                "minecraft:behavior.move_towards_target": {"priority": 3, "speed_multiplier": 1.1, "within_radius": 20},
                "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.8},
                "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 8},
                "minecraft:behavior.random_look_around": {"priority": 8}}}})


def client():
    write(RP / "entity" / "embestidor.entity.json", {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": ID,
            "materials": {"default": "entity_alphatest"},
            "textures": {"default": "textures/entity/embestidor"},
            "geometry": {"default": "geometry.embestidor"},
            "render_controllers": ["controller.render.default"],
            "animations": {"quieto": "animation.embestidor.quieto", "andar": "animation.embestidor.andar",
                           "embestir": "animation.embestidor.embestir",
                           "mover": "controller.animation.embestidor.mover"},
            "scripts": {"animate": ["mover"]},
            "spawn_egg": {"base_color": "#0e322b", "overlay_color": "#aaa39b"}}}})
    write(RP / "animation_controllers" / "embestidor.animation_controllers.json", {
        "format_version": "1.10.0",
        "animation_controllers": {"controller.animation.embestidor.mover": {
            "initial_state": "quieto",
            "states": {
                "quieto": {"animations": ["quieto"], "transitions": [{"andar": "query.modified_move_speed > 0.1"}],
                           "blend_transition": 0.2},
                "andar": {"animations": ["andar"], "transitions": [{"quieto": "query.modified_move_speed < 0.1"}],
                          "blend_transition": 0.2}}}}})
    (RP / "texts").mkdir(parents=True, exist_ok=True)
    (RP / "texts" / "es_ES.lang").write_text(f"entity.{ID}.name=Embestidor\nitem.spawn_egg.entity.{ID}.name=Generar Embestidor\n")
    (RP / "texts" / "es_MX.lang").write_text((RP / "texts" / "es_ES.lang").read_text())
    (RP / "texts" / "en_US.lang").write_text(f"entity.{ID}.name=Rammer\nitem.spawn_egg.entity.{ID}.name=Spawn Rammer\n")
    write(RP / "texts" / "languages.json", ["es_ES", "es_MX", "en_US"])


if __name__ == "__main__":
    manifests()
    behavior()
    client()
    print("ok")
