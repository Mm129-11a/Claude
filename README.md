# Netvy Studios

Web de Netvy Studios: un estudio que hace réplicas de proyectos muy famosos (DEDsafio, Extremo…).
Todo vive en un solo archivo, **`index.html`**.

## Qué tiene

- **Portada:** "NETVY STUDIOS" en tipografía gigante y un bloque de pasto 3D (Three.js) que se gira arrastrándolo con el dedo o el ratón. Mientras lo arrastras, la página no se mueve.
- **Proyectos:** lista con nombre, año, estado (Próximamente / En proceso con % / Terminado / Pausado), tipo y enlace opcional.
- **Contacto:** el botón «Contáctanos» abre una ventana con los datos de contacto que se ponen desde el admin.
- **Admin** (abajo del todo): con contraseña. Sirve para añadir, editar, ordenar y borrar proyectos, y para gestionar los datos de contacto.
- Idiomas: ES (por defecto), EN, IT, CH.

## Dónde se guardan los cambios del admin

Los proyectos y contactos van **dentro de la propia página** (bloque `<script id="site-data">`).

| Dónde abres la web | Qué hace «Guardar» |
|---|---|
| **claude.ai** (versión publicada) | Vuelve a publicar la página con los cambios; todo el que tenga el enlace los ve. Solo la cuenta dueña puede publicar. |
| **GitHub / archivo local** | Guarda solo en ese navegador. Usa «Descargar index.html» y sube ese archivo al repositorio para publicarlo. |

## Seguridad

La contraseña solo abre el panel. Está guardada como hash SHA-256, no en texto, pero cualquiera que sepa leer código puede intentar adivinarla.
En la versión de claude.ai el permiso real para guardar lo controla claude.ai (solo la cuenta dueña), así que aunque alguien entre en el panel no puede publicar nada.
En la copia de GitHub nadie puede cambiar lo que ven los demás, solo lo que ve en su propio navegador.

## Probarla en local

```bash
python3 -m http.server 8000   # → http://localhost:8000
```
