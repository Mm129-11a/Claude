# Eclipse para Minecraft Bedrock

## Instalar
1. Abre `Eclipse.mcaddon` (se importa solo en Minecraft).
2. En tu mundo: Configuración → Paquetes de comportamiento → activa **Eclipse**
   (el de texturas se activa solo).
3. Usa gráficos normales (Elegantes), no "Vibrant Visuals".

Necesita Minecraft Bedrock 1.21.100 o más nuevo.

## Usar
- `/eclipse` → empieza el eclipse (solo operadores).
- `/eclipse` otra vez → termina y regresa la hora que tenías.

Mira hacia el **oeste** (donde se pone el sol).

## Qué pasa
1. Se pone la hora con el sol al oeste y se congela el ciclo de día.
2. Durante 20 s la luna negra tapa el sol y el horizonte se va oscureciendo.
3. Sale el destello (anillo de diamante), se hace de noche y queda la luna negra
   con su anillo de luz (corona) y el horizonte naranja, hasta que lo apagues.

## Editar
- `BP/scripts/main.js`: arriba está `CONFIG` (duración, hora, tamaño de la luna...).
  Si el sol se asoma por un lado de la luna, sube `sunRadiusDeg`.
- `RP/textures/particle/`: luna, corona y destello (PNG).
- `RP/textures/environment/sun.png`: sol redondo como el del video.
  Bórralo si quieres el sol cuadrado normal.
- `RP/fogs/`: colores del cielo oscuro y del horizonte naranja.
