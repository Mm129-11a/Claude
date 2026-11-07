"""Genera DeathAnimation_RP/ui/death_anim.json a partir de las constantes del extractor."""
import json
from pathlib import Path

import extract_from_video as ex

ROOT = Path(__file__).resolve().parent.parent
FPS = 15
n_frames = len(range(ex.FIRST, ex.LAST + 1, ex.STEP))
n_tex = -(-n_frames // ex.FRAMES_PER_TEXTURE)
intro_frames = len([i for i in range(ex.FIRST, ex.LAST + 1, ex.STEP) if i <= ex.INTRO_LAST]) + 1
cw, ch = ex.CX1 - ex.CX0, ex.CY1 - ex.CY0
pct = lambda v, total: f"{v / total * 100:.3f}%"
EVENT = "hud_title_text_show"
total = n_frames / FPS

ui = {"namespace": "death_anim"}

ui["intro_uv"] = {
    "anim_type": "flip_book", "initial_uv": [0, 0], "frame_count": intro_frames,
    "frame_step": ex.SH, "fps": FPS, "looping": False, "easing": "linear",
    "play_event": EVENT, "resettable": True,
}

creature_controls = []
for k in range(n_tex):
    frames = min(ex.FRAMES_PER_TEXTURE, n_frames - k * ex.FRAMES_PER_TEXTURE)
    start = k * ex.FRAMES_PER_TEXTURE / FPS
    show = frames / FPS
    flip = {"anim_type": "flip_book", "initial_uv": [0, 0], "frame_count": frames,
            "frame_step": ch, "fps": FPS, "looping": False, "easing": "linear"}
    if k == 0:
        ui[f"c{k}_uv"] = dict(flip, play_event=EVENT, resettable=True)
        ui[f"c{k}_alpha"] = {"anim_type": "alpha", "from": 1, "to": 1, "duration": show,
                             "play_event": EVENT, "resettable": True, "next": f"@death_anim.c{k}_off"}
    else:
        ui[f"c{k}_uv"] = {"anim_type": "wait", "duration": start, "play_event": EVENT,
                          "resettable": True, "next": f"@death_anim.c{k}_flip"}
        ui[f"c{k}_flip"] = flip
        ui[f"c{k}_alpha"] = {"anim_type": "alpha", "from": 0, "to": 0, "duration": start,
                             "play_event": EVENT, "resettable": True, "next": f"@death_anim.c{k}_on"}
        ui[f"c{k}_on"] = {"anim_type": "alpha", "from": 1, "to": 1, "duration": show,
                          "next": f"@death_anim.c{k}_off"}
    ui[f"c{k}_off"] = {"anim_type": "alpha", "from": 0, "to": 0, "duration": 60}
    creature_controls.append({f"creature_{k}": {
        "type": "image",
        "texture": f"textures/ui/death_anim/creature_{k}",
        "anchor_from": "top_left", "anchor_to": "top_left",
        "offset": [pct(ex.CX0, ex.SW), pct(ex.CY0, ex.SH)],
        "size": [pct(cw, ex.SW), pct(ch, ex.SH)],
        "layer": 2 + k,
        "uv_size": [cw, ch],
        "uv": f"@death_anim.c{k}_uv",
        "alpha": f"@death_anim.c{k}_alpha",
    }})

# Texto: aparece cuando se va el destello y se va cuando la criatura se rompe
ui["text_wait"] = {"anim_type": "alpha", "from": 0, "to": 0, "duration": 0.35,
                   "play_event": EVENT, "resettable": True, "next": "@death_anim.text_in"}
ui["text_in"] = {"anim_type": "alpha", "easing": "out_quad", "from": 0, "to": 1,
                 "duration": 0.3, "next": "@death_anim.text_hold"}
ui["text_hold"] = {"anim_type": "alpha", "from": 1, "to": 1, "duration": 7.55,
                   "next": "@death_anim.text_out"}
ui["text_out"] = {"anim_type": "alpha", "easing": "in_quad", "from": 1, "to": 0, "duration": 0.4}

marker_visible = [
    {"binding_name": "#hud_title_text_string"},
    {"binding_type": "view",
     "source_property_name": "(not ((#hud_title_text_string - '_death_:') = #hud_title_text_string))",
     "target_property_name": "#visible"},
]

ui["root"] = {
    "type": "panel", "size": ["100%", "100%"], "layer": 40,
    "bindings": marker_visible,
    "controls": [{"strip@death_anim.strip": {}}],
}
ui["strip"] = {
    # mismas proporciones que la franja del video (576x320)
    "type": "panel", "size": ["100%", pct(ex.SH, ex.SW) + "x"],
    "anchor_from": "center", "anchor_to": "center",
    "controls": [
        {"intro": {"type": "image", "texture": "textures/ui/death_anim/intro",
                   "size": ["100%", "100%"], "layer": 1,
                   "uv_size": [ex.SW, ex.SH], "uv": "@death_anim.intro_uv"}},
        *creature_controls,
        {"text@death_anim.text": {}},
    ],
}
ui["text"] = {
    "type": "stack_panel", "orientation": "vertical",
    "anchor_from": "top_middle", "anchor_to": "top_middle",
    "offset": [0, pct(ex.CY1 - 14, ex.SH)],
    "size": ["100%", "100%c"], "layer": 20,
    "alpha": "@death_anim.text_wait", "propagate_alpha": True,
    "controls": [
        {"player_name": {
            "type": "label", "size": ["100%", "default"], "text_alignment": "center",
            "font_type": "MinecraftTen", "font_scale_factor": 1.6,
            "color": [1.0, 0.33, 0.33], "shadow": True, "text": "#text",
            "bindings": [
                {"binding_name": "#hud_title_text_string"},
                {"binding_type": "view",
                 "source_property_name": "(#hud_title_text_string - '_death_:')",
                 "target_property_name": "#text"}]}},
        {"gap": {"type": "panel", "size": ["100%", 2]}},
        {"reason": {
            "type": "label", "size": ["100%", "default"], "text_alignment": "center",
            "font_scale_factor": 1.1, "color": [1.0, 1.0, 1.0], "shadow": True, "text": "#text",
            "bindings": [{"binding_name": "#hud_subtitle_text_string",
                          "binding_name_override": "#text"}]}},
    ],
}

out = ROOT / "DeathAnimation_RP" / "ui" / "death_anim.json"
out.write_text(json.dumps(ui, indent=2, ensure_ascii=False) + "\n")
print(f"ui ok: {n_tex} texturas de criatura, intro {intro_frames} fotogramas, {total:.2f} s")
