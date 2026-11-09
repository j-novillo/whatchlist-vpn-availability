# Decisiones de la v1

Estas reglas las confirmó Jorge. Los ejemplos de Nuremberg (2025), Parasite (2019), Synecdoche, New York (2008) y Amélie (2001) están en los fixtures y en los tests. No están escritos como casos especiales en el formateador: sirven para comprobar que las reglas generales dan ese resultado.

## Qué línea es nueva

Se comparan la nota actual y el snapshot, sin mirar el orden.

- Misma línea en otro sitio: no es nueva.
- La misma obra ya anotada (`Título (Netflix)`, `Título (Prime Video, Francia)`, `Título (RTVE Play)` o con ⚠️): no se vuelve a buscar. El título base, sin el sufijo y sin el ⚠️, es lo que se compara.
- Un retoque pequeño en el sitio tampoco es nuevo: un carácter de diferencia, o dos si el título tiene al menos 6 caracteres. `Inception` → `Incepton` se queda. `Nuermberg` frente a un snapshot que ya dice `Nuremberg` también. `It` → `Us` sí es otra línea (es corta y cambia dos letras). `Dune` → `Dune: Part Two` es otra obra: lleva una palabra de más.
- Una línea nueva que se parece a otra que ya estaba no se come a la antigua. Si el snapshot tiene `Inception` y la nota tiene `Inception` e `Incepton`, solo `Incepton` se busca.

Los marcadores `[ ]`, `[x]`, `☐` y `☑` no forman parte del título. Se conservan al reescribir la línea.

## TMDB y la búsqueda

El nombre se puede escribir en español. TMDB devuelve el título en inglés (`language=en-US`), que es el que se busca en Stream with VPN. La nota no se traduce.

Mayúsculas, acentos y puntuación no separan dos títulos: `Amélie` y `Amelie` son iguales, igual que `Synecdoche, New York` y `Synecdoche New York`.

En los resultados:

- Gana un título **igual** al nombre resuelto. No vale uno que solo lo contenga: para `Nuremberg` se elige Nuremberg, no Judgment at Nuremberg ni Nuremberg Trials.
- Si hay varios iguales, gana el año más reciente (Nuremberg 2025 antes que Nuremberg 2000).
- Si no hay ninguno igual, se usa el más parecido, se anotan sus plataformas y la línea lleva ⚠️. Por debajo de un parecido mínimo (un título sin relación, tipo El Padrino frente a Nuremberg) no se fuerza una ficha: la línea se deja y se reintenta.
- Una errata que TMDB deja en un título que luego coincide exactamente no lleva ⚠️. `Nuermberg` queda `Nuermberg (Netflix, Estados Unidos)` si la ficha de Nuremberg 2025 es esa.

## Plataformas

Solo importan Netflix y Prime Video, en ese orden, y como último recurso RTVE Play.

1. Netflix en España → `Título (Netflix)`. Sin nombre de país.
2. Si no, Prime Video en España → `Título (Prime Video)`.
3. Si no, Netflix en cualquier otro país → `Título (Netflix, <país>)`.
4. Si no, Prime Video en cualquier otro país → `Título (Prime Video, <país>)`.
5. Si no aparece ninguno, y RTVE Play está en la sección Free / Ad-supported → `Título (RTVE Play)`.
6. Si no → el título solo.

Prime en España gana a Netflix en el extranjero. Netflix en España gana a todo lo demás, incluido Prime en España: se escribe solo Netflix.

Movistar Plus+, HBO Max, Canal+ y el resto no cuentan. El bloque «Available in N other streaming services» tampoco, aunque un logo de ahí diga Netflix. RTVE Play en el catálogo de pago o en ese bloque no cuenta; solo la sección gratuita o con anuncios.

Con los datos contrastados, las reglas dan:

| Título resuelto | Por qué | Línea si el usuario escribió el nombre inglés |
| --- | --- | --- |
| Nuremberg (2025) | Netflix solo en Estados Unidos. Prime está en varios países de Latinoamérica, India y Polonia, no en España. Movistar en España no es Netflix ni Prime. | `Nuremberg (Netflix, Estados Unidos)` |
| Parasite (2019) | Netflix y Prime incluyen España. | `Parasite (Netflix)` |
| Synecdoche, New York (2008) | Prime en Australia y Nueva Zelanda. No hay Netflix en las fichas principales. | `Synecdoche, New York (Prime Video, Australia)` |
| Amélie (2001) | Netflix en Canadá. Slug real: `/amlie-2001`. | `Amélie (Netflix, Canadá)` |

## País

España es el nivel 0. Fuera de España se elige el primer país del nivel más alto que de verdad esté en la ficha. Dentro del nivel, primero va la lista explícita y después el resto por orden alfabético en español (la eñe va después de la ene; los acentos no cambian el orden).

Nivel 1, en este orden: Estados Unidos, Reino Unido, Francia, Alemania, Italia, Portugal, Países Bajos, Irlanda, Bélgica, Suiza, Austria, Suecia, Noruega, Dinamarca, Finlandia, Polonia, Canadá, Australia. Después, el resto de países europeos por orden alfabético (Islandia antes que Malta, y ambos después de Australia, que está en la lista explícita).

Nivel 2, en este orden: México, Argentina, Colombia, Chile, Perú, Uruguay, Venezuela. Después, el resto de países de habla hispana salvo España, por orden alfabético (Bolivia antes que Ecuador, y México antes que Argentina aunque el alfabeto diga lo contrario).

Nivel 3: todos los demás, por orden alfabético en español (Japón antes que Sudáfrica). Un nivel más alto siempre gana: Polonia antes que México, Bolivia antes que Japón.

Los nombres salen en español. `US` y `United States` son Estados Unidos; `CA` es Canadá y `AU` es Australia (no Austria).

## Orden al escribir en Keep

1. Crear la nota nueva con el texto entero.
2. Leerla y comprobar que el texto coincide.
3. Borrar la antigua.
4. Actualizar el Doc.

Nunca al revés. Los detalles de lo que se pierde al recrear están en [limitaciones.md](limitaciones.md).
