# Huevo Eburia

Modelo de un fruto para Minecraft (Bedrock): dos huevos-bloque color crema con manchas azules,
uno grande y otro pequeño, sobre raíces rojizas. Hecho para editar en **Blockbench**.

![Vista previa](preview.png)

## Archivos

| Archivo | Para qué |
|---|---|
| `huevo_eburia.bbmodel` | Proyecto de Blockbench, con la textura incluida. Ábrelo y edítalo. |
| `huevo_eburia.png` | Textura 64x64 (por si la quieres pintar en otro programa). |
| `huevo_eburia.geo.json` | Geometría de Bedrock lista para usar en un addon. |

## Abrir en Blockbench

1. Abre Blockbench (escritorio o https://web.blockbench.net).
2. **Archivo → Abrir modelo** y elige `huevo_eburia.bbmodel` (o arrástralo a la ventana).
3. Está en formato *Bedrock Block* con **Box UV**: cada pieza tiene su nombre
   (`huevo_grande`, `huevo_chico`, `raiz_1`…`raiz_4`) y se puede mover, rotar o repintar.

## Regenerar

```bash
python3 tools/make_model.py
```
Las posiciones, tamaños y giros de cada pieza están en `PIECES`, y los colores al principio del script.
