# Supernova (addon de Minecraft Bedrock)

Con un comando, una estrella nace en el cielo, todo se oscurece, explota y llega un destello.

![Las tres fases](preview.png)

Video de la simulación: [`preview.mp4`](preview.mp4) (hecho fuera del juego con las mismas
texturas, tamaños y tiempos que el addon).

## Usarlo

1. Abre [`Supernova.mcaddon`](Supernova.mcaddon) con Minecraft y activa **los dos** paquetes
   (comportamiento y recursos) en el mundo. Necesita Bedrock **1.21.50 o superior** y trucos activados.
2. Escribe **`/function supernova`**. La supernova sale delante de ti, a 32 bloques y en lo alto.

También se puede lanzar con `/scriptevent supernova:iniciar` (por ejemplo desde un bloque de comandos;
en ese caso sale hacia el norte del bloque).

## Qué pasa (unos 12 segundos)

| Momento | Qué se ve |
|---|---|
| 0 s | La pantalla se funde a negro un instante y retumba un trueno. |
| 0,5 s | Se hace de noche, entra una niebla rojo oscura y **nace la estrella**: una bola de fuego con llamas que crece y late. |
| 5,5 s | La estrella se hincha y la pantalla tiembla. |
| 6,5 s | **Explota**: estallido blanco con rayos morados y borde rosa, temblor fuerte y explosión. |
| 7,5 s | **El destello**: un parpadeo blanco y un resplandor blanco con bordes rosas que llena el cielo, con niebla clara. |
| 8,3 s | Vuelve la hora que había antes. |
| 12 s | Se quita la niebla y todo queda como estaba. |

Mientras dura, no se puede lanzar otra.

## Cómo está hecho

- **BP** `scripts/main.js`: escucha el evento `supernova:iniciar` y va lanzando cada fase con
  partículas, `fog`, `camera ... fade`, `camerashake`, sonidos y la hora del día.
  `functions/supernova.mcfunction` es el comando `/function supernova`.
- **RP** `particles/`: `estrella`, `explosion` y `destello` (imágenes que siempre miran a la cámara,
  con animación). `fogs/`: niebla oscura, de explosión y del destello.
- `tools/make_textures.py` pinta las texturas, `tools/make_particles.py` escribe las partículas,
  `tools/make_preview.py` hace la simulación y `tools/build.sh` empaqueta el addon.

Para cambiar distancia, altura o tiempos: constantes `DISTANCE`, `HEIGHT` y `T` en `scripts/main.js`.
Tamaños de cada fase: `tools/make_particles.py`.
