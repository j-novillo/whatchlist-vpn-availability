"""Spanish country names and Jorge's priority order.

Level 0 is Spain. For every other country, the winner is the first country in
the highest level that is actually available. Inside a level, the explicit
list comes first and the remainder is alphabetical in Spanish.
"""

import re
import unicodedata

LEVEL_1 = (
    "Estados Unidos",
    "Reino Unido",
    "Francia",
    "Alemania",
    "Italia",
    "Portugal",
    "Países Bajos",
    "Irlanda",
    "Bélgica",
    "Suiza",
    "Austria",
    "Suecia",
    "Noruega",
    "Dinamarca",
    "Finlandia",
    "Polonia",
    "Canadá",
    "Australia",
)

LEVEL_2 = (
    "México",
    "Argentina",
    "Colombia",
    "Chile",
    "Perú",
    "Uruguay",
    "Venezuela",
)

# European countries written in Spanish. Spain is level 0 and is not ranked here.
EUROPE = frozenset(
    {
        "Albania",
        "Alemania",
        "Andorra",
        "Austria",
        "Bélgica",
        "Bielorrusia",
        "Bosnia y Herzegovina",
        "Bulgaria",
        "Chipre",
        "Ciudad del Vaticano",
        "Croacia",
        "Dinamarca",
        "Eslovaquia",
        "Eslovenia",
        "España",
        "Estonia",
        "Finlandia",
        "Francia",
        "Grecia",
        "Hungría",
        "Irlanda",
        "Islandia",
        "Italia",
        "Kosovo",
        "Letonia",
        "Liechtenstein",
        "Lituania",
        "Luxemburgo",
        "Macedonia del Norte",
        "Malta",
        "Moldavia",
        "Mónaco",
        "Montenegro",
        "Noruega",
        "Países Bajos",
        "Polonia",
        "Portugal",
        "Reino Unido",
        "República Checa",
        "Rumanía",
        "Rusia",
        "San Marino",
        "Serbia",
        "Suecia",
        "Suiza",
        "Ucrania",
    }
)

# Spanish is an official language. Spain itself is level 0.
HISPANIC = frozenset(
    {
        "Argentina",
        "Bolivia",
        "Chile",
        "Colombia",
        "Costa Rica",
        "Cuba",
        "Ecuador",
        "El Salvador",
        "España",
        "Guatemala",
        "Guinea Ecuatorial",
        "Honduras",
        "México",
        "Nicaragua",
        "Panamá",
        "Paraguay",
        "Perú",
        "Puerto Rico",
        "República Dominicana",
        "Uruguay",
        "Venezuela",
    }
)

# (canonical Spanish name, aliases including English names and ISO codes).
# Home nations of the UK share the UK catalog on streaming sites.
_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("España", ("Spain", "Espana", "ES")),
    ("Estados Unidos", ("United States", "United States of America", "USA", "US", "U.S.", "U.S.A.", "EEUU", "EE UU")),
    ("Reino Unido", ("United Kingdom", "UK", "Great Britain", "Britain", "GB", "England", "Scotland", "Wales", "Northern Ireland")),
    ("Francia", ("France", "FR")),
    ("Alemania", ("Germany", "DE")),
    ("Italia", ("Italy", "IT")),
    ("Portugal", ("PT",)),
    ("Países Bajos", ("Netherlands", "The Netherlands", "Holland", "NL")),
    ("Irlanda", ("Ireland", "Republic of Ireland", "IE")),
    ("Bélgica", ("Belgium", "BE")),
    ("Suiza", ("Switzerland", "CH")),
    ("Austria", ("AT",)),
    ("Suecia", ("Sweden", "SE")),
    ("Noruega", ("Norway", "NO")),
    ("Dinamarca", ("Denmark", "DK")),
    ("Finlandia", ("Finland", "FI")),
    ("Polonia", ("Poland", "PL")),
    ("Canadá", ("Canada", "CA")),
    ("Australia", ("AU",)),
    ("México", ("Mexico", "MX")),
    ("Argentina", ("AR",)),
    ("Colombia", ("CO",)),
    ("Chile", ("CL",)),
    ("Perú", ("Peru", "PE")),
    ("Uruguay", ("UY",)),
    ("Venezuela", ("VE",)),
    ("Bolivia", ("BO",)),
    ("Costa Rica", ("CR",)),
    ("Cuba", ("CU",)),
    ("Ecuador", ("EC",)),
    ("El Salvador", ("SV",)),
    ("Guatemala", ("GT",)),
    ("Guinea Ecuatorial", ("Equatorial Guinea", "GQ")),
    ("Honduras", ("HN",)),
    ("Nicaragua", ("NI",)),
    ("Panamá", ("Panama", "PA")),
    ("Paraguay", ("PY",)),
    ("Puerto Rico", ("PR",)),
    ("República Dominicana", ("Dominican Republic", "DO")),
    ("Albania", ("AL",)),
    ("Andorra", ("AD",)),
    ("Bielorrusia", ("Belarus", "BY")),
    ("Bosnia y Herzegovina", ("Bosnia and Herzegovina", "Bosnia", "BA")),
    ("Bulgaria", ("BG",)),
    ("Chipre", ("Cyprus", "CY")),
    ("Ciudad del Vaticano", ("Vatican City", "Vatican", "VA")),
    ("Croacia", ("Croatia", "HR")),
    ("Eslovaquia", ("Slovakia", "SK")),
    ("Eslovenia", ("Slovenia", "SI")),
    ("Estonia", ("EE",)),
    ("Grecia", ("Greece", "GR")),
    ("Hungría", ("Hungary", "HU")),
    ("Islandia", ("Iceland", "IS")),
    ("Kosovo", ("XK",)),
    ("Letonia", ("Latvia", "LV")),
    ("Liechtenstein", ("LI",)),
    ("Lituania", ("Lithuania", "LT")),
    ("Luxemburgo", ("Luxembourg", "LU")),
    ("Macedonia del Norte", ("North Macedonia", "MK")),
    ("Malta", ("MT",)),
    ("Moldavia", ("Moldova", "MD")),
    ("Mónaco", ("Monaco", "MC")),
    ("Montenegro", ("ME",)),
    ("República Checa", ("Czech Republic", "Czechia", "CZ")),
    ("Rumanía", ("Romania", "RO")),
    ("Rusia", ("Russia", "RU")),
    ("San Marino", ("SM",)),
    ("Serbia", ("RS",)),
    ("Ucrania", ("Ukraine", "UA")),
    ("Nueva Zelanda", ("New Zealand", "NZ")),
    ("India", ("IN",)),
    ("Japón", ("Japan", "JP")),
    ("Sudáfrica", ("South Africa", "ZA")),
    ("Brasil", ("Brazil", "BR")),
    ("China", ("CN",)),
    ("Corea del Sur", ("South Korea", "Republic of Korea", "Korea", "KR")),
    ("Corea del Norte", ("North Korea", "KP")),
    ("Turquía", ("Turkey", "Türkiye", "TR")),
    ("Indonesia", ("ID",)),
    ("Tailandia", ("Thailand", "TH")),
    ("Vietnam", ("Viet Nam", "VN")),
    ("Filipinas", ("Philippines", "PH")),
    ("Malasia", ("Malaysia", "MY")),
    ("Singapur", ("Singapore", "SG")),
    ("Hong Kong", ("HK",)),
    ("Taiwán", ("Taiwan", "TW")),
    ("Israel", ("IL",)),
    ("Emiratos Árabes Unidos", ("United Arab Emirates", "UAE", "AE")),
    ("Arabia Saudí", ("Saudi Arabia", "SA")),
    ("Egipto", ("Egypt", "EG")),
    ("Marruecos", ("Morocco", "MA")),
    ("Nigeria", ("NG",)),
    ("Kenia", ("Kenya", "KE")),
    ("Jamaica", ("JM",)),
    ("Trinidad y Tobago", ("Trinidad and Tobago", "TT")),
    ("Bahamas", ("BS",)),
    ("Barbados", ("BB",)),
    ("Haití", ("Haiti", "HT")),
    ("Guinea", ("GN",)),
    ("Papúa Nueva Guinea", ("Papua New Guinea", "PG")),
)

_LEVEL_1_INDEX = {name: index for index, name in enumerate(LEVEL_1)}
_LEVEL_2_INDEX = {name: index for index, name in enumerate(LEVEL_2)}


def _fold_country(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    plain = plain.casefold().replace("&", " and ")
    plain = plain.replace("'", "").replace("’", "")
    plain = re.sub(r"[^a-z0-9]+", " ", plain)
    return re.sub(r"\s+", " ", plain).strip()


def _build_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for canonical, extra in _ROWS:
        for name in (canonical, *extra):
            aliases[_fold_country(name)] = canonical
    return aliases


_ALIASES = _build_aliases()


def spanish_sort_key(name: str) -> str:
    """Alphabetical order in Spanish: ñ follows n, accents do not."""

    pieces: list[str] = []
    for char in name.casefold():
        if char == "ñ":
            pieces.append("n~")
            continue
        decomposed = unicodedata.normalize("NFKD", char)
        pieces.append("".join(part for part in decomposed if not unicodedata.combining(part)))
    return "".join(pieces)


def canonicalize_country(name: str) -> str:
    """Map an English name, ISO code, or Spanish name to the Spanish canonical form."""

    raw = name.strip()
    if not raw:
        return raw
    return _ALIASES.get(_fold_country(raw), raw)


def country_sort_key(name: str) -> tuple:
    """Rank a country. Lower is better. ``name`` may be English or Spanish."""

    canonical = canonicalize_country(name)
    if canonical == "España":
        return (0, 0, 0, "")
    level_1 = _LEVEL_1_INDEX.get(canonical)
    if level_1 is not None:
        return (1, 0, level_1, "")
    if canonical in EUROPE:
        return (1, 1, 0, spanish_sort_key(canonical))
    level_2 = _LEVEL_2_INDEX.get(canonical)
    if level_2 is not None:
        return (2, 0, level_2, "")
    if canonical in HISPANIC:
        return (2, 1, 0, spanish_sort_key(canonical))
    return (3, 0, 0, spanish_sort_key(canonical))


def best_country(names: list[str]) -> str:
    """Pick the best country and return its Spanish name."""

    if not names:
        raise ValueError("best_country requires at least one country")
    canonical = [canonicalize_country(name) for name in names if name.strip()]
    if not canonical:
        raise ValueError("best_country requires at least one country")
    winner = min(canonical, key=country_sort_key)
    return winner
