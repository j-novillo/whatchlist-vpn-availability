# Dónde verlo

Programa para Jorge. Lee una nota de Google Keep con películas y series (una por línea), detecta los títulos nuevos respecto a un Google Doc que guarda la versión anterior, y anota en cada línea nueva si está en Netflix, Prime Video o RTVE Play según [Stream with VPN](https://www.streamwithvpn.com/).

Es una primera versión para iterar. No hace falta ninguna clave para probar el flujo con los ejemplos y los fixtures.

Repositorio previsto: [j-novillo/whatchlist-vpn-availability](https://github.com/j-novillo/whatchlist-vpn-availability).

## Qué hace en cada pasada

1. Lee la nota actual (texto libre o lista de verificación).
2. Lee el snapshot: el texto plano de la última versión, guardado en un Google Doc.
3. Se queda solo con las líneas realmente nuevas. No vuelve a buscar una línea que solo se movió, que se editó poco en el sitio, o que ya lleva el formato de una pasada anterior.
4. Para cada título nuevo pide a TMDB el nombre en inglés (vale escribirlo en español o con una errata) y busca ese nombre en Stream with VPN. En la nota se conserva la frase original.
5. Escribe la disponibilidad y, si hace falta, recrea la nota de Keep **creando primero la nota nueva, comprobándola y solo entonces borrando la antigua**.
6. Actualiza el Doc para que coincida con lo ya resuelto.

Si no puede consultar un título (checkpoint de Vercel, página ilegible, sin resultados), deja esa línea como está y sigue con las demás. Esas líneas no entran en el snapshot, así que la siguiente pasada las reintenta.

## Instalación

Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

El extra `unofficial` (`pip install -e ".[unofficial]"`) solo hace falta si vas a usar gkeepapi. No es el camino recomendado.

Las dependencias directas van fijadas en `pyproject.toml`. El árbol completo que se usó al desarrollar está en `requirements.lock`.

## Prueba sin claves

Los fixtures reproducen cuatro fichas ya contrastadas en la web (no están escritas a fuego en el formateador: si cambian las reglas, el test falla).

```bash
python -m watchlist_enricher sync \
  --note-file ejemplos/nota.txt \
  --snapshot-file ejemplos/snapshot.txt \
  --fixtures tests/fixtures/streamwithvpn/catalog.json \
  --tmdb-fixtures tests/fixtures/tmdb.json \
  --dry-run
```

Con esa nota de ejemplo la salida incluye:

- `Nuremberg (Netflix, Estados Unidos)` — Netflix no está en España; Prime tampoco, aunque sí Movistar.
- `Parásito (Netflix)` — el usuario lo escribió en español; TMDB lo busca como Parasite; Netflix está en España, así que no se escribe el país y no se menciona Prime.
- `Synecdoche, New York (Prime Video, Australia)`
- `Amélie (Netflix, Canadá)` — la ficha real usa el slug `/amlie-2001`.
- `Nuermberg (Netflix, Estados Unidos)` — la errata se corrige solo para buscar. No lleva ⚠️ porque, una vez resuelta, el título coincide exactamente.

`Inception` ya estaba en el snapshot y `The Matrix (Netflix)` ya estaba enriquecida: no se tocan. `--dry-run` no escribe nada. Para guardar los ficheros locales, cambia `--dry-run` por `--apply-local`.

Los tests no usan red:

```bash
pytest
```

## Qué tienes que aportar después

Nada de esto bloquea la prueba de arriba. Cuando quieras la pasada real:

| Variable | Para qué | Dónde se consigue |
| --- | --- | --- |
| `TMDB_API_KEY` | Nombre en inglés y erratas | [Ajustes de API de TMDB](https://www.themoviedb.org/settings/api) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` o el par OAuth | Leer y escribir el Doc | Ver [docs/configuracion.md](docs/configuracion.md) |
| `DOCS_SNAPSHOT_ID` | El documento snapshot | El id de la URL del Doc (`/document/d/<id>/edit`) |
| `KEEP_NOTE_TITLE` o `KEEP_NOTE_ID` | La nota de la lista | Título único, o el id `notes/<id>` |
| Credencial de Keep | Crear y borrar la nota | API oficial solo con Workspace y delegación de dominio. Cuenta personal: dry-run, ficheros, o el backend no oficial si ya tienes token |

Stream with VPN no tiene API pública y esta versión **no inicia sesión**. No hay clave que pegar.

## Apuntar a la nota y al Doc

En `.env`:

```bash
KEEP_NOTE_TITLE=Para ver
DOCS_SNAPSHOT_ID=el-id-del-documento
GOOGLE_SERVICE_ACCOUNT_FILE=/ruta/al-service-account.json
TMDB_API_KEY=tu-clave
```

Simulación contra Keep y el Doc de verdad (lee, no borra; con `--update-snapshot` sí actualiza el Doc):

```bash
python -m watchlist_enricher sync --dry-run
python -m watchlist_enricher sync --dry-run --update-snapshot
```

Pasada real:

```bash
python -m watchlist_enricher sync
```

El id de la nota cambia en cada recreación. Si usas `KEEP_NOTE_ID`, el programa imprime el id nuevo y hay que copiarlo. Con `KEEP_NOTE_TITLE` y un título único, la siguiente pasada encuentra la nota nueva sola.

## Formato de la línea

Se respeta el texto que escribiste, incluido el marcador de lista (`[ ]`, `[x]`, `☐`…).

1. Netflix en España: `Título (Netflix)`.
2. Si no, Prime Video en España: `Título (Prime Video)`.
3. Si no, Netflix en otro país: `Título (Netflix, Estados Unidos)`.
4. Si no, Prime Video en otro país: `Título (Prime Video, Australia)`.
5. Si no aparece ninguno de los dos, y RTVE Play está en la sección gratuita o con anuncios: `Título (RTVE Play)`.
6. Si tampoco: el título solo, sin paréntesis.

Si hay Netflix y Prime, se escribe solo Netflix. Los países van en español. España no se nombra. El país extranjero es el primero del nivel más alto de la lista de [docs/decisiones.md](docs/decisiones.md).

Si en Stream with VPN no hay un título idéntico (mayúsculas y acentos no importan: Amélie y Amelie son el mismo), se usa el más parecido, se escriben sus plataformas y la línea lleva ⚠️ delante del título. Una errata que TMDB corrige y que luego coincide exactamente **no** lleva ⚠️.

## Recrear la nota borra metadatos

Keep no deja actualizar una nota por la API: se crea otra y se borra la vieja. Eso **pierde el color, el fijado, las etiquetas, los colaboradores, el enlace compartido y los recordatorios**. Las subtareas de una lista se aplanan. Por eso nunca se borra primero: si crear o comprobar falla, la nota anterior sigue en su sitio.

## Limitaciones

Resumen; el detalle está en [docs/limitaciones.md](docs/limitaciones.md).

- Stream with VPN puede responder con un control de Vercel. No se intenta saltar. Ese título se omite y el resto sigue.
- `robots.txt` prohíbe `/api/`. El cliente solo pide HTML público y rechaza esa ruta.
- Desde el entorno en el que se escribió esta v1 la web respondió 403 / checkpoint, así que el lector en vivo aún no está contrastado con el DOM real. Los tests usan HTML y JSON de ejemplo.
- Las listas de países de la web no distinguen suscripción de alquiler o compra.
- Sin `TMDB_API_KEY` no hay traducción ni corrección de erratas.

## Tests

Cubren el diff (nuevo, ya enriquecido, reordenado, edición leve), la coincidencia exacta frente a un título que solo contiene el nombre, el desempate por año, la errata sin ⚠️, el aproximado con ⚠️ y plataformas, Netflix por delante de Prime, España sin país, los niveles de países, RTVE Play, y que Keep no se borra si crear o verificar falla.
