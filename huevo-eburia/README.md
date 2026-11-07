# Huevo Eburia

Modelo de un fruto para Minecraft (Bedrock), copiado de la foto de referencia: un huevo-bloque
grande (8x8x8) y uno chico (5x5x5) color crema con manchas azules y una franja tostada, sobre
raíces rojizas. Hecho para editar en **Blockbench**.

La textura está leída de la foto píxel por píxel (1 píxel = 1 unidad, como en Minecraft).
En la vista previa: a la izquierda la foto, al centro y a la derecha el modelo.

![Vista previa](preview.png)

## Archivos

| Archivo | Para qué |
|---|---|
| `huevo_eburia.bbmodel` | Proyecto de Blockbench, con la textura incluida. Ábrelo y edítalo. |
| `huevo_eburia.png` | Textura 16x16 (por si la quieres pintar en otro programa). |
| `huevo_eburia.geo.json` | Geometría de Bedrock lista para usar en un addon. |

## Abrir en Blockbench

1. Abre Blockbench (escritorio o https://web.blockbench.net).
2. **Archivo → Abrir modelo** y elige `huevo_eburia.bbmodel` (o arrástralo a la ventana).
3. Está en formato *Bedrock Block*: cada pieza tiene su nombre (`huevo_grande`, `huevo_chico`,
   `raiz_1`…`raiz_5` con sus `_pie`) y se puede mover, rotar o repintar.

## Regenerar

```bash
python3 tools/make_model.py
```
La textura está escrita como cuadrícula de letras (`BIG`, `SMALL`) con sus colores en `PALETTE`,
y las piezas en `PIECES`.
