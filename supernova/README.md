# Supernova (addon de Minecraft Bedrock)

Con un comando, una estrella nace en el cielo, todo se oscurece, explota y llega un destello.

![Referencias arriba, el addon abajo](preview.png)

*Arriba, las imágenes de referencia; abajo, cada fase del addon. Video de la simulación:
[`preview.mp4`](preview.mp4) (hecho fuera del juego con las mismas texturas, tamaños y tiempos).*

Las tres imágenes salen de las referencias, sin dibujar nada a mano:
- **La estrella** es la bola de lava del modelo de Blockbench (roca con grietas de lava), recortada tal cual.
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

## Qué pasa (unos 12 segundos)

| Momento | Qué se ve |
|---|---|
| 0 s | La pantalla se funde a negro un instante y retumba un trueno. |
| 0,5 s | Se hace de noche, entra una niebla rojo oscura y **nace la estrella**: la bola de lava, que crece, gira despacio y late. |
| 5,5 s | La estrella se hincha y la pantalla tiembla. |
| 6,5 s | **Explota**: estallido blanco con rayos morados y borde rosa, temblor fuerte y explosión. |
| 7,5 s | **El destello**: un parpadeo blanco y el resplandor de la captura 3, que llena el cielo hasta el suelo, con niebla clara. |
| 8,3 s | Vuelve la hora que había antes. |
| 12 s | Se quita la niebla y todo queda como estaba. |

Mientras dura, no se puede lanzar otra.

## Cómo está hecho

- **BP** `scripts/main.js`: escucha el evento `supernova:iniciar` y va lanzando cada fase con
  partículas, `fog`, `camera ... fade`, `camerashake`, sonidos y la hora del día.
  `functions/supernova.mcfunction` es el comando `/function supernova`.
- **RP** `particles/`: `estrella`, `explosion` y `destello` (imágenes que siempre miran a la cámara).
  `fogs/`: niebla oscura, de explosión y del destello.
- `tools/extract_from_photos.py` saca las texturas de las tres imágenes de referencia,
  `tools/make_particles.py` escribe las partículas (tamaños medidos en las capturas),
  `tools/make_preview.py` hace la simulación y `tools/build.sh` empaqueta el addon:

```bash
./tools/build.sh bola.jpg explosion.jpg destello.jpg   # sin imágenes, usa las texturas que ya hay
python3 tools/make_preview.py bola.jpg explosion.jpg destello.jpg
```

Para cambiar distancia, altura o tiempos: constantes `DISTANCE`, `HEIGHT` y `T` en `scripts/main.js`.
Tamaños de cada fase: `tools/make_particles.py`.
