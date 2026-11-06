# Animación de muerte (addon de Minecraft Bedrock)

Cada vez que un jugador muere, **todos** los jugadores ven en pantalla:

1. un destello rojo con rayos blancos que salen del centro,
2. una calavera pixelada que late (con una gema que cambia de color),
3. el **nombre del jugador** y la **causa de la muerte** (en español),
4. la calavera se rompe con un glitch y se desintegra en píxeles blancos.

Dura unos 5 segundos y suena un trueno. Vista previa: [`preview.gif`](preview.gif).

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

## Cómo funciona

- **BP** (`scripts/main.js`): escucha `world.afterEvents.entityDie` para jugadores, calcula la causa
  y manda a todos un título `"_death_:<nombre>"` con la causa como subtítulo.
- **RP** (`ui/`): el HUD detecta el prefijo `_death_:` en el título, oculta el título normal y
  muestra la animación (`ui/death_anim.json`): destello, rayos y calavera son *flipbooks* de
  `textures/ui/death_anim/`. Los títulos normales (`/title`) siguen funcionando igual.

## Cambiar el dibujo

Las texturas se generan con `tools/generate_textures.py` (Python + Pillow). Edita el dibujo
`LEFT` (mitad izquierda de la calavera, se refleja sola) o los colores y ejecuta:

```bash
./tools/build.sh   # regenera texturas, preview.gif y DeathAnimation.mcaddon
```
