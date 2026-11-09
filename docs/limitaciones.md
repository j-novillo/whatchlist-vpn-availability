# Limitaciones

## Control de Vercel

Stream with VPN puede responder con un *Vercel Security Checkpoint* o con un 403 a un cliente automático. Esta versión **no intenta saltarlo**: ni resuelve captchas, ni reutiliza una cookie de desafío, ni llama a un proxy para esquivar el bloqueo.

Si la respuesta es un checkpoint, un 403 de ese tipo o un error de red, ese título se anota como fallo, la línea se queda como la escribiste y la pasada continúa. Esas líneas no se copian al snapshot, para que la siguiente ejecución las vuelva a intentar.

Al escribir esta v1, tanto `curl` como Chrome sin interfaz recibieron un 403 / checkpoint desde el entorno de desarrollo. El lector en vivo está escrito para cuando la web sí entregue HTML, pero no se pudo contrastar contra el DOM real. Hasta entonces, `--fixtures` es la forma segura de probar el resto del programa.

## No hay API pública

`robots.txt` permite el sitio y **prohíbe `/api/`** (también `/redirect/` y `/person/`). El cliente HTTP solo pide páginas `https` de `streamwithvpn.com` y rechaza cualquier ruta `/api/` antes de enviarla.

La búsqueda de la web es un autocompletado. El cliente pide `https://www.streamwithvpn.com/search?q=...` y la ficha `https://www.streamwithvpn.com/<slug>`. No inventa slugs: el de Amélie en la web real es `/amlie-2001`, no `/amelie-2001`, así que el slug sale del resultado de búsqueda.

Si el HTML no trae resultados (porque el autocompletado solo vive en el navegador y llama a `/api/`), el título falla con un mensaje y no se llama a esa API.

### Qué sabe leer el parser

Por este orden:

1. JSON embebido (`<script type="application/json">`, `__NEXT_DATA__`, o un objeto JSON suelto). Busca servicios con países (`service` / `provider` / `name` y `countries` / `regions` / códigos) y resultados con título, año y slug.
2. Bloques con `data-section="catalog|free|dump"`.
3. Encabezados (`h2`–`h4`) seguidos de una lista de países. Un encabezado *Free* o *Ad-supported* abre la sección gratuita. *Available in N other streaming services* abre el montón de logos, que se ignora salvo para no confundirlo con las fichas con nombre.

Si ninguna de las tres cosas aparece, el título se omite. No se usa el audio de pago, los subtítulos ni los enlaces directos.

### Navegador

Un backend de navegador sería el siguiente paso si la ficha solo se pinta en el cliente: abrir la página pública, leer el DOM como un usuario, y abortar en cuanto aparezca el checkpoint o un captcha, sin intentar resolverlo. No está en la v1. `STREAMWITHVPN_BACKEND=browser` lo dice y termina.

## Suscripción, alquiler o compra

Las listas de países de Stream with VPN, en la práctica, no dicen si Netflix o Prime Video es suscripción, alquiler o compra. La v1 no lo distingue. Un país en la ficha de Netflix cuenta como «está en Netflix».

## Recrear la nota de Keep

La API oficial no tiene update. El programa:

1. Crea una nota nueva con el texto completo.
2. La vuelve a leer y compara el texto.
3. Solo si coincide, borra la nota anterior.
4. Después actualiza el Doc.

Si crear falla, o si el texto leído no coincide, **no se borra** la nota vieja. Puede quedar también la nueva: el mensaje de error incluye los dos ids.

Ese recrear **no conserva**:

- color
- fijado
- etiquetas
- colaboradores
- enlace compartido
- recordatorios

Tampoco la anidación de una lista: las subtareas pasan a ser líneas sueltas. Los adjuntos no se copian.

El id cambia siempre. `KEEP_NOTE_TITLE` evita tener que actualizar el id, siempre que no haya dos notas vivas con el mismo título (puede pasar si la verificación falló y no se borró la antigua: se elige la de `updateTime` más reciente).

El backend no oficial también crea, sincroniza y solo entonces borra. Su «comprobación» es la copia local tras el `sync`, no un get independiente al servidor.

## El snapshot y los fallos

Si todos los títulos nuevos se resuelven, el Doc queda igual que la nota.

Si alguno falla, el Doc se actualiza **sin** esas líneas. La nota de Keep sí las conserva, escritas como las dejaste. Así la siguiente pasada las ve como nuevas. Una línea que ya lleva `(Netflix)`, `(Prime Video)`, `(RTVE Play)` o ⚠️ no se vuelve a buscar aunque el Doc esté atrasado.

Si la nota no cambia (no hay nada que anotar, o todo falló), no se recrea Keep. Si el Doc estaba atrasado y esta pasada no tuvo fallos, se actualiza el Doc sin tocar Keep.

## TMDB

Se usa el primer resultado de película o serie. Suele bastar para una errata (`Nuermberg` → `Nuremberg`) o un título en español, pero puede elegir otra obra si el nombre es ambiguo. Las personas que devuelva la búsqueda se ignoran.

Sin clave, no hay resolución.

## Países que el mapa no conoce

Un nombre que no esté en la tabla se muestra tal cual y cae en el nivel 3 (el resto del mundo, por orden alfabético español). Inglaterra, Escocia, Gales e Irlanda del Norte se tratan como Reino Unido, porque en estas webs suelen ser el catálogo británico.

## Datos que no entran en la v1

- El montón sin nombre «Available in N other streaming services», excepto para no tomarlo por Netflix o Prime. RTVE Play solo cuenta en la sección gratuita o con anuncios.
- Audio, subtítulos y enlaces directos de pago.
- Varias cuentas de streaming, precios, o si el plan es con anuncios. Un nombre que empiece por «Netflix» cuenta como Netflix (incluido un plan con anuncios). «Prime Video» y «Amazon Prime Video» cuentan como Prime Video.
