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
| Product sculpture | Mobiliario 3D procedural con Three.js (r128): butaca, silla, sillón con pedestal y puf. Casi negro, sin suelo ni sombras, flotando por encima del texto |
| Description caption | 12px, mayúsculas, interlineado 1.56 |
| Archive list | 8 proyectos: título en serif 72px + año / PROJECT DETAILS / tipo / ámbito en 12px, separados 32px. La pieza 3D cambia según la fila que esté en el centro de la pantalla o bajo el cursor |
| Section labels | `US / WW`, `Archive`, `(08)` |

## Tokens

- Colores: Onyx `#0e0e0e` (fondo), Paper White `#fefefe` (tinta), Faint White `#2a2a2a` (solo la selección de texto)
- Tipos: **ak** → Inter como sustituto · **gs** → Playfair Display como sustituto (Google Fonts). Si tienes las fuentes originales, decláralas con `@font-face` como `'ak'` y `'gs'`; las variables `--font-ak` / `--font-gs` ya las ponen primero
- Sin radios, sin bordes, sin sombras, sin degradados

## Notas

- Los nombres de los proyectos y el email (`hello@example.com`) son marcadores: sustitúyelos por los reales.
- Respeta `prefers-reduced-motion`: sin animaciones de entrada, deriva ni rotación.
- Si Three.js no carga (sin red o sin WebGL), la página sigue funcionando sin el objeto 3D.
