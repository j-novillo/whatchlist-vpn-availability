# Configuración

Todo lo secreto va en `.env` (copia de `.env.example`) o en variables de entorno. No lo pongas en el repositorio.

Puedes saltarte Google y TMDB y trabajar con ficheros y fixtures. Ver el README, sección «Prueba sin claves».

## TMDB

1. Crea una cuenta en [themoviedb.org](https://www.themoviedb.org/).
2. Entra en Ajustes → API y pide una clave de API (v3).
3. Ponla en `TMDB_API_KEY`.

El programa llama a `GET /3/search/multi` con `language=en-US` y se queda con el primer resultado que sea película o serie. Ese título en inglés es solo para buscar. La nota sigue mostrando lo que escribiste.

Sin clave, y sin `--tmdb-fixtures`, cada línea se busca tal cual. Una errata o un título en español puede no coincidir y acabar en ⚠️, o no encontrarse.

Para pruebas, `--tmdb-fixtures` apunta a un JSON:

```json
{ "Nuermberg": "Nuremberg", "Parásito": "Parasite" }
```

## Google: el Doc snapshot

El Doc guarda el texto plano de la última versión ya considerada. Sirve cualquier documento de Google Docs vacío o con la lista anterior.

### Cuenta de servicio (lo más simple para el Doc)

1. En [Google Cloud Console](https://console.cloud.google.com/) crea un proyecto.
2. Activa **Google Docs API**.
3. Crea una cuenta de servicio y descarga el JSON.
4. Guarda el JSON fuera del repositorio y apunta `GOOGLE_SERVICE_ACCOUNT_FILE` a esa ruta.
5. Comparte el Doc con el email de la cuenta de servicio (lector no basta: necesita poder editar).
6. Copia el id del Doc a `DOCS_SNAPSHOT_ID`.

Con esto el snapshot funciona. La API oficial de Keep es otro tema: una cuenta de servicio normal no puede leer la Keep de un Gmail personal.

### OAuth de usuario

Si prefieres entrar con tu usuario de Google:

1. En el mismo proyecto, configura la pantalla de consentimiento.
2. Crea un cliente OAuth de tipo «Aplicación de escritorio» y descarga el JSON.
3. `GOOGLE_OAUTH_CLIENT_FILE` apunta a ese JSON.
4. `GOOGLE_TOKEN_FILE` es donde el programa guardará el token (por ejemplo `token.json`, que está en `.gitignore`).
5. La primera ejecución abre el navegador. Acepta el acceso a Documentos. Si también vas a usar Keep oficial, incluye ese alcance en la misma autorización.

Alcances que pide el programa, solo los que hagan falta en esa pasada:

- `https://www.googleapis.com/auth/documents`
- `https://www.googleapis.com/auth/keep` (solo con el backend oficial)

## Google Keep oficial

La API de Keep puede crear, leer, listar y borrar notas. **No puede modificar** una nota existente. Está pensada para cuentas de Google Workspace con delegación de dominio, no para un Gmail personal con un consentimiento OAuth normal.

Si tienes Workspace:

1. Activa **Google Keep API** en el proyecto.
2. En la cuenta de servicio, activa la delegación de dominio para el alcance `https://www.googleapis.com/auth/keep`.
3. En la consola de administración del dominio, autoriza ese cliente y ese alcance.
4. `GOOGLE_DELEGATED_USER` es el email del usuario cuya Keep se va a leer (el tuyo).
5. `KEEP_BACKEND=official` (o `auto`, que elige la API oficial en cuanto hay credenciales de Google).
6. `KEEP_NOTE_TITLE` con el título exacto de la nota, o `KEEP_NOTE_ID` con el id.

`auto` no activa nunca el backend no oficial por su cuenta.

## Backend no oficial

Solo si la API oficial no te vale y **ya** tienes un master token de gkeepapi.

```bash
pip install -e ".[unofficial]"
```

```bash
KEEP_BACKEND=unofficial
KEEP_USERNAME=tu-email
KEEP_MASTER_TOKEN=el-token-que-ya-tienes
# KEEP_DEVICE_ID=opcional
```

Esa biblioteca usa una API privada de la app móvil. Google no la soporta y puede dejar de funcionar sin aviso. El token equivale a una sesión con acceso amplio a la cuenta: trátalo como una contraseña y no lo subas al repositorio.

No documentamos cómo extraer cookies ni cómo fabricar ese token. Si no lo tienes, usa `--note-file`, `--dry-run` o la API oficial.

Al crear, el adaptador hace `sync` antes de devolver la nota. Si ese sync falla, no se llama a borrar. La comprobación posterior lee la copia local que gkeepapi tiene después del sync; es más débil que un `get` de la API oficial.

## Ficheros locales

Útiles mientras faltan las claves, y también para ensayar el texto antes de tocar Keep.

```bash
python -m watchlist_enricher sync \
  --note-file mi-nota.txt \
  --snapshot-file mi-snapshot.txt \
  --fixtures tests/fixtures/streamwithvpn/catalog.json \
  --tmdb-fixtures tests/fixtures/tmdb.json \
  --dry-run
```

Sin `--dry-run` ni `--apply-local`, un `--note-file` sigue siendo una simulación: no se pisa el fichero. `--apply-local` escribe la nota y el snapshot en disco y no habla con Keep.

`--fixtures` sustituye la web. `--swv-backend fixtures` hace lo mismo y exige la ruta del catálogo.

## Stream with VPN

No hay login en esta versión. `STREAMWITHVPN_BACKEND=live` (el valor por defecto) descarga HTML público. `STREAMWITHVPN_TIMEOUT` está en segundos.

`STREAMWITHVPN_BACKEND=browser` responde con un error claro: la v1 no automatiza el navegador. Ver [limitaciones.md](limitaciones.md).
