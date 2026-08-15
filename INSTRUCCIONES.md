# Cómo publicar la web con estadísticas automáticas

## Qué hay en esta carpeta
- `index.html` → la web (ya lista para leer `stats.json`)
- `stats.json` → los 4 datos que se muestran en el "ticket". Se actualiza solo.
- `scripts/scrape_blogabet.py` → el script que va a Blogabet y saca los datos
- `.github/workflows/update-stats.yml` → la tarea programada que ejecuta el script cada día

## Importante sobre el winrate
El scraper solo puede leer **picks, profit (unidades) y yield**, porque son los únicos
datos visibles en la portada pública de tu perfil. El **winrate (58%)** está en la
pestaña "Statistics" de Blogabet, que se carga con JavaScript y no es tan sencilla de
leer automáticamente. Por ahora ese número seguirá siendo manual: edítalo tú directamente
en `stats.json` cuando quieras.

## Paso 1 — Crear el repositorio en GitHub
1. Entra en github.com (crea una cuenta si no tienes) y pulsa **New repository**.
2. Nómbralo, por ejemplo, `thegreentipster-web`. Que sea **público** (necesario para
   GitHub Pages gratis).
3. Sube todos los archivos de esta carpeta a ese repositorio (arrastrándolos desde la
   web de GitHub es suficiente, o con `git push` si prefieres terminal).

## Paso 2 — Activar GitHub Pages
1. En el repositorio, ve a **Settings → Pages**.
2. En "Source" elige **Deploy from a branch**, rama `main`, carpeta `/ (root)`.
3. Guarda. En 1-2 minutos tu web estará en algo como:
   `https://tu-usuario.github.io/thegreentipster-web/`

## Paso 3 — Comprobar que la automatización funciona
1. Ve a la pestaña **Actions** del repositorio.
2. Verás el workflow "Actualizar estadísticas de Blogabet".
3. Púlsalo y dale a **Run workflow** para probarlo manualmente la primera vez.
4. Si todo va bien, verás un commit nuevo actualizando `stats.json` con la fecha de hoy.
5. A partir de ahí se ejecutará solo, todos los días a las 07:00 UTC — no tienes que
   tocar nada más.

## Si algún día quieres cambiar algo a mano
Solo tienes que editar `stats.json` directamente desde GitHub (botón del lápiz ✏️
en la propia web de GitHub) y guardar. Se actualiza en la web al momento.

## Nota sobre Blogabet
El script visita tu perfil público una vez al día, algo discreto y dentro de un uso
razonable. Aun así, técnicamente entra en la categoría de "acceso automatizado", que
algunas plataformas restringen en sus términos de uso. Si en algún momento Blogabet
cambia el diseño de la página, el scraper puede dejar de encontrar los datos: en ese
caso el workflow fallará (lo verás en rojo en la pestaña Actions) y tendrás que
avisarme para ajustar el script.
