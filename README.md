# Netvy Studios

Web de Netvy Studios: un estudio que hace réplicas de proyectos muy famosos (DEDsafio, Extremo…).
Todo vive en un solo archivo, **`index.html`**.

## Qué tiene

- **Portada:** "NETVY STUDIOS" en tipografía gigante y un bloque de pasto 3D (Three.js) que se gira arrastrándolo con el dedo o el ratón. Mientras lo arrastras, la página no se mueve.
- **Proyectos:** lista con nombre, año, estado (Próximamente / En proceso con % / Terminado / Pausado), tipo y enlace opcional.
- **Personaje:** un muñeco de bloques con el logo de Netvi como cabeza. Saluda al entrar, se sorprende y presenta los proyectos con los brazos abiertos (si aún no hay, se encoge de hombros) y al final hace la seña de «espera» y señala el botón de contacto.
- **Contacto:** el botón «Contáctanos» abre una ventana con los datos de contacto que se ponen desde el admin.
- **Admin** (oculto): se abre tocando «© 2026 netvy studios» al final de la página, y siempre pide la contraseña. Sirve para añadir, editar, ordenar y borrar proyectos, y para gestionar los datos de contacto.
- Idiomas: español (por defecto) e inglés.

## Bot de Discord

En [`discord-bot/`](discord-bot/) está Netvi, el muñeco de la web, como bot de Discord: pasea por los canales, habla con los miembros (con Claude) y responde a comandos como `/llamar` o `/bailar`. Está desplegado en Render (`netvi-discord-bot`) y la web muestra debajo del muñeco en qué canal de Discord está Netvi ahora mismo. Las instrucciones están en su README.

## Addon de Minecraft: animación de muerte

En [`minecraft-death-animation/`](minecraft-death-animation/) hay un addon de Minecraft Bedrock que muestra una animación con el nombre del jugador y la causa cada vez que alguien muere.

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
