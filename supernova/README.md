# Supernova (addon de Minecraft Bedrock)

Con un comando, una estrella nace en el cielo, todo se oscurece, explota y llega un destello.

![Momentos clave](preview.png)

*La estrella se forma pieza por pieza, explota y llega el destello. Video de la simulación:
[`preview.mp4`](preview.mp4) (hecho fuera del juego con las mismas texturas, piezas, tamaños y tiempos).*

Las tres imágenes salen de las referencias, sin dibujar nada a mano:
- **La estrella** es la bola de lava del modelo de Blockbench (roca con grietas de lava), recortada tal cual.
  Para que se forme pieza por pieza, la bola se corta por sus propias grietas en 75 placas de roca;
  juntas forman la bola exacta.
- **La explosión** es la de la captura 2 (estallido blanco, rayos morados, vetas celestes y borde rosa).
  Lo que tapaba el personaje se rellenó con la propia explosión reflejada.
- **El destello** es la captura 3 entera (blanco, bordes rosas y rayas de luz), sin el personaje
  ni los botones.

## Usarlo

1. Abre [`Supernova.mcaddon`](Supernova.mcaddon) con Minecraft y activa **los dos** paquetes
   (comportamiento y recursos) en el mundo. Necesita Bedrock **1.21.50 o superior** y trucos activados.
2. Escribe **`/function supernova`**. La supernova sale delante de ti, a 32 bloques y un poco por
   encima de la vista (como en las capturas).

También se puede lanzar con `/scriptevent supernova:iniciar` (por ejemplo desde un bloque de comandos;
en ese caso sale hacia el norte del bloque).

## Qué pasa (unos 14 segundos)

| Momento | Qué se ve |
|---|---|
| 0 s | La pantalla se funde a negro un instante y retumba un trueno. |
| 0,5 s | Se hace de noche, entra una niebla rojo oscura y aparece un **núcleo** brillante. |
| 0,7 – 4,8 s | **La estrella se forma pieza por pieza**: las 75 placas de roca llegan volando desde todas partes, una tras otra, girando y apagadas; al encajar se encienden y suena un golpe de piedra. |
| 4,8 s | La última pieza encaja: **la estrella está completa** (la bola de lava), gira despacio y late. |
| 6,8 s | La estrella se hincha y la pantalla tiembla. |
| 8 s | **Explota**: estallido blanco con rayos morados y borde rosa, temblor fuerte y explosión. |
| 9 s | **El destello**: un parpadeo blanco y el resplandor de la captura 3, que llena el cielo hasta el suelo, con niebla clara. |
| 9,8 s | Vuelve la hora que había antes. |
| 13,5 s | Se quita la niebla y todo queda como estaba. |

Mientras dura, no se puede lanzar otra.

## Cómo está hecho

- **BP** `scripts/main.js`: escucha el evento `supernova:iniciar` y va lanzando cada fase con
  partículas, `fog`, `camera ... fade`, `camerashake`, sonidos y la hora del día.
  `functions/supernova.mcfunction` es el comando `/function supernova`.
- **RP** `particles/`: `nucleo`, `pieza` (cada pieza recibe del script su trozo de `piezas.png`,
  de dónde sale y cuánto gira), `estrella`, `explosion` y `destello` (imágenes que siempre miran a la cámara).
  `scripts/piezas.js` dice dónde va cada pieza.
  `fogs/`: niebla oscura, de explosión y del destello.
- `tools/extract_from_photos.py` saca las texturas de las tres imágenes de referencia,
  `tools/make_pieces.py` corta la estrella en sus piezas,
  `tools/make_particles.py` escribe las partículas (tamaños medidos en las capturas),
  `tools/make_preview.py` hace la simulación y `tools/build.sh` empaqueta el addon:

```bash
./tools/build.sh bola.jpg explosion.jpg destello.jpg   # sin imágenes, usa las texturas que ya hay
python3 tools/make_preview.py
```

Para cambiar distancia, altura o tiempos: constantes `DISTANCE`, `HEIGHT` y `T` en `scripts/main.js`.
Tamaños de cada fase: `tools/make_particles.py`.
