# Animación de muerte (addon de Minecraft Bedrock)

Cada vez que un jugador muere, **todos** los jugadores ven en pantalla la misma animación
del video de referencia, fotograma a fotograma y con su sonido original:

1. la mini-criatura, el destello rojo con la silueta y el destello negro,
2. los rayos blancos,
3. la criatura flotando,
4. el glitch final que la deshace en píxeles blancos,

y debajo de la criatura el **nombre del jugador** y la **causa de la muerte** (en español).
Dura 8,9 s, igual que el efecto del video. Vista previa: [`preview.gif`](preview.gif).

## Instalar

1. Descarga [`DeathAnimation.mcaddon`](DeathAnimation.mcaddon) y ábrelo con Minecraft (se importan los dos paquetes).
2. En el mundo, activa **los dos**: el paquete de comportamiento (BP) y el de recursos (RP).
3. Necesita Minecraft Bedrock **1.21.50 o superior**. En versiones antiguas activa «Beta APIs» en los experimentos del mundo.

## Ejemplos de mensajes

| Causa | Texto |
|---|---|
| Lava | `Steve` — intentó nadar en lava |
| Flecha de esqueleto | `Steve` — fue disparado por un Esqueleto |
| Otro jugador | `Steve` — fue asesinado por Alex |
| Creeper | `Steve` — voló por los aires por un Creeper |

Los textos se cambian en `DeathAnimation_BP/scripts/main.js` (`CAUSES` y `MOBS`).

## De dónde sale la animación

Las texturas y el sonido se sacan **directamente del video** (efecto de pantalla verde propio,
publicado en TikTok como @simplenovelero) con `tools/extract_from_video.py`: no hay nada redibujado. El
script quita el fondo verde y la marca de agua de TikTok, y guarda:

- `textures/ui/death_anim/intro.png`: rayos y destellos (franja completa).
- `textures/ui/death_anim/creature_0..6.png`: la criatura a resolución original.
- `sounds/death_anim/death.ogg`: el audio del efecto.

El efecto original va a ~15 fps (el video de 30 fps repite cada fotograma), así que se usa a 15 fps.

Para regenerarlo (necesita Python con Pillow y NumPy, y ffmpeg):

```bash
./tools/build.sh ruta/al/video.mp4   # texturas, sonido, ui, preview.gif y DeathAnimation.mcaddon
```

## Cómo funciona

- **BP** (`scripts/main.js`): escucha `world.afterEvents.entityDie` para jugadores, calcula la causa,
  manda a todos un título `"_death_:<nombre>"` con la causa como subtítulo y reproduce el sonido.
- **RP** (`ui/`): el HUD detecta el prefijo `_death_:` en el título, oculta el título normal y
  muestra la animación (`ui/death_anim.json`, generado con `tools/make_ui.py`). Los títulos
  normales (`/title`) siguen funcionando igual.
