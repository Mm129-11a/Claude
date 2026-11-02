# offfice studio — réplica

Réplica estática de la web descrita en `DESIGN.md` ("noir gallery swallowed by monolithic type").

Todo vive en un solo archivo: **`index.html`** (HTML + CSS + JS). Para verla, ábrelo en el navegador o sírvelo con cualquier servidor estático:

```bash
python3 -m http.server 8000   # → http://localhost:8000
```

## Qué incluye

| Componente del diseño | Implementación |
|---|---|
| Top navigation | `offfice studio` a la izquierda, **GET IN TOUCH** (700) a la derecha, 12px, sin fondo |
| Locale switcher | `IT / ES / CH` en funcionamiento (EN por defecto). Recuerda el idioma elegido |
| Display headline | 216px (`clamp(96px, 15vw, 216px)`), interlineado 0.80, se sale del viewport por ambos lados y se desplaza en horizontal al hacer scroll |
| Objeto 3D (modo Minecraft) | Un bloque de pasto pixelado (arriba pasto, lados de tierra con el borde verde, abajo tierra; texturas 16×16 generadas por código, sin suavizado) hecho con Three.js (r128). Vive solo en la portada, flota sobre el titular y **se gira arrastrándolo con el dedo o el ratón**: conserva la inercia, vuelve a quedar con el pasto hacia arriba y sigue girando despacio. También responde a las flechas del teclado |
| Description caption | 12px, mayúsculas, interlineado 1.56 |
| Archive list | 8 proyectos: título en serif 72px + año / PROJECT DETAILS / tipo / ámbito en 12px, separados 32px. Al pasar el ratón por una fila, las demás se atenúan |
| Section labels | `US / WW`, `Archive`, `(08)` |

## Tokens

- Colores: Onyx `#0e0e0e` (fondo), Paper White `#fefefe` (tinta), Faint White `#2a2a2a` (solo la selección de texto)
- Tipos: **ak** → Inter como sustituto · **gs** → Playfair Display como sustituto (Google Fonts). Si tienes las fuentes originales, decláralas con `@font-face` como `'ak'` y `'gs'`; las variables `--font-ak` / `--font-gs` ya las ponen primero
- Sin radios, sin bordes, sin sombras, sin degradados

## Notas

- Los nombres de los proyectos y el email (`hello@example.com`) son marcadores: sustitúyelos por los reales.
- Respeta `prefers-reduced-motion`: sin animaciones de entrada, deriva ni giro automático (arrastrar el bloque sigue funcionando).
- El render 3D se pausa cuando la portada sale de pantalla.
- Si Three.js no carga (sin red o sin WebGL), la página sigue funcionando sin el objeto 3D.
