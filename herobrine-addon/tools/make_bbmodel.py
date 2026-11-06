# Junta herobrine.geo.json + herobrine_skin.png en un solo archivo de Blockbench (.bbmodel)
import json, base64, uuid, sys
geo = json.load(open(sys.argv[1]))["minecraft:geometry"][0]
tex = base64.b64encode(open(sys.argv[2], "rb").read()).decode()
U = lambda: str(uuid.uuid4())
elements, groups = [], {}
def faces(u, v, w, h, d):
    return {"north": {"uv": [u+d, v+d, u+d+w, v+d+h], "texture": 0},
            "east":  {"uv": [u, v+d, u+d, v+d+h], "texture": 0},
            "south": {"uv": [u+2*d+w, v+d, u+2*d+2*w, v+d+h], "texture": 0},
            "west":  {"uv": [u+d+w, v+d, u+2*d+w, v+d+h], "texture": 0},
            "up":    {"uv": [u+d+w, v+d, u+d, v], "texture": 0},
            "down":  {"uv": [u+d+2*w, v, u+d+w, v+d], "texture": 0}}
for b in geo["bones"]:
    g = {"name": b["name"], "origin": b["pivot"], "rotation": [0, 0, 0], "uuid": U(),
         "export": True, "isOpen": True, "visibility": True, "children": []}
    for c in b.get("cubes", []):
        o, s = c["origin"], c["size"]
        e = {"name": b["name"], "type": "cube", "uuid": U(), "box_uv": True, "rescale": False,
             "locked": False, "from": o, "to": [o[i] + s[i] for i in range(3)],
             "inflate": c.get("inflate", 0), "autouv": 0, "color": 0, "origin": b["pivot"],
             "uv_offset": c["uv"], "faces": faces(*c["uv"], *s)}
        elements.append(e); g["children"].append(e["uuid"])
    groups[b["name"]] = (g, b.get("parent"))
roots = []
for name, (g, parent) in groups.items():
    (groups[parent][0]["children"] if parent else roots).append(g)
model = {
  "meta": {"format_version": "4.5", "model_format": "bedrock", "box_uv": True},
  "name": "herobrine", "model_identifier": "herobrine",
  "visible_box": [2, 3, 1.5], "variable_placeholders": "", "variable_placeholder_buttons": [],
  "resolution": {"width": 64, "height": 64},
  "elements": elements, "outliner": roots,
  "textures": [{"path": "", "name": "herobrine_skin.png", "folder": "", "namespace": "",
                "id": "0", "particle": False, "render_mode": "default", "visible": True,
                "mode": "bitmap", "saved": False, "uuid": U(), "width": 64, "height": 64,
                "uv_width": 64, "uv_height": 64,
                "source": "data:image/png;base64," + tex}]}
json.dump(model, open(sys.argv[3], "w"), indent=1)
