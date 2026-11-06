# Eclipse para Minecraft Bedrock

## Instalar
1. Abre `Eclipse.mcaddon` (se importa solo en Minecraft).
   Si ya tenías la versión anterior, bórrala primero (Configuración → Almacenamiento).
2. En tu mundo: Paquetes de comportamiento → activa **Eclipse**.
   En Paquetes de recursos pon **Eclipse (texturas)** hasta arriba de la lista.
3. Usa gráficos normales (no "Vibrant Visuals").

Necesita Minecraft Bedrock 1.21.100 o más nuevo.

## Usar
- `/eclipse` → empieza el eclipse (solo operadores).
- `/eclipse` otra vez → termina y regresa la hora que tenías.

El eclipse sale **justo arriba de cada jugador**: todo el server lo ve, solo hay que mirar hacia arriba.

## Qué pasa (como en el video)
1. Se hace mediodía. Sale un sol redondo que brilla fuerte, justo arriba.
2. La luna redonda entra desde arriba a la derecha y lo va tapando (22 s).
   Mientras lo tapa, el cielo pasa de azul a naranja, luego rojo oscuro y al final negro.
3. Queda una rayita de sol, sale el destello en forma de estrella,
   se hace de noche y aparecen las estrellas.
4. Queda la luna negra con el anillo de luz (corona) hasta que lo apagues.

El sol y la luna normales del juego también quedan redondos.

## Cómo funciona
A cada jugador se le monta en el hombro una entidad invisible (como un loro) que dibuja
el sol, la luna y el cielo oscuro arriba de él. Como va montada, el juego la mueve contigo
en cada cuadro: se ve suave aunque camines, corras o vueles. Cada quien ve solo el suyo.

## Editar
- `BP/scripts/main.js`: arriba está `CONFIG` (cuánto dura, de dónde viene la luna).
- `tools/build.py`: dibuja la textura, el modelo y los colores del cielo. Cámbialo y córrelo con
  `python3 tools/build.py RP BP` para regenerar todo.
- `RP/textures/entity/eclipse_sky.png`: todas las imágenes del eclipse juntas.
- `RP/models/entity/eclipse_sky.geo.json`: el modelo (se puede abrir en Blockbench).
- `RP/fogs/`: colores del horizonte.
