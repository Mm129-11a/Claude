# Huevo Eburia

Modelo para Blockbench (Bedrock) copiado de la foto de referencia: un huevo-bloque grande
(16×16×16) y uno chico (11×11×11) pegado a su lado derecho, color crema tostado con manchas
azules, sobre patas y una raíz rojizas.

![Comparación](preview.png)

*Izquierda: la foto. Centro: el modelo puesto en la foto con la misma cámara (sustituye a los
cubos originales). Derecha: el modelo desde otro ángulo.*

## Archivos

| Archivo | Para qué |
|---|---|
| `huevo_eburia.bbmodel` | Proyecto de Blockbench con la textura incluida. Ábrelo y edítalo. |
| `huevo_eburia.png` | Textura 32×32 (16×16 del grande, 11×11 del chico y el color de las patas). |
| `huevo_eburia.geo.json` | Geometría de Bedrock lista para un addon. |
| `fuente/` | Lo medido en la foto: texturas de cada cubo, cámara, posiciones y patas. |

## Abrir en Blockbench

1. Abre Blockbench (escritorio o https://web.blockbench.net).
2. **Archivo → Abrir modelo** y elige `huevo_eburia.bbmodel` (o arrástralo a la ventana).
3. Piezas: `huevo_grande`, `huevo_chico`, `pata_1`…`pata_4` (cada una con su `_pie`) y `raiz`.

## Cómo se sacó de la foto

Nada está dibujado a ojo; todo se midió en la foto con `tools/extract_from_photo.py`:

1. **Cámara**: con las esquinas de los dos cubos se calcula la cámara de la foto (la foto es
   un recorte de la pantalla, así que el centro de la cámara queda fuera de la imagen).
   El error medio es de unos 3 px, lo normal en una foto borrosa.
2. **Cubo chico**: con esa cámara sale que mide 11 px (el grande 16), apoya en el mismo
   suelo, está pegado al lado derecho del grande (metido 1 px) y alineado con su parte de atrás.
3. **Textura**: cada píxel de textura se proyecta sobre la foto para tomar su color. Las dos
   caras visibles del cubo grande tienen la misma textura, y eso permite separar la textura
   de la luz de la cueva. Las manchas son de 2×2 y los colores son los tonos de la foto.
4. **Patas**: se ajustan cajas a los píxeles rojizos de la foto, con reglas físicas (salen de
   debajo de un cubo, bajan a un suelo común y hacen un quiebre hacia afuera).

Lo que no se ve en la foto (la parte de atrás y de abajo) repite la misma textura.

## Regenerar

```bash
pip install numpy pillow scipy opencv-python-headless
python3 tools/extract_from_photo.py foto.jpg   # mide la foto y guarda fuente/
python3 tools/make_model.py                    # crea el .bbmodel, la textura y el .geo.json
```
