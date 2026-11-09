"""Parse Stream with VPN HTML or embedded JSON.

The live site is often behind a Vercel Security Checkpoint from automated
clients, and robots.txt disallows /api/. This parser therefore only reads
documents we already fetched. It understands:

* a Vercel checkpoint or block page
* ``<script type="application/json">`` blobs (including a loose walk for
  service/country objects)
* elements marked ``data-section="catalog|free|dump"``
* headings followed by country lists, including a "Free" section and the
  unnamed "Available in N other streaming services" pile

When the live DOM drifts, a title fails for that line instead of crashing.
"""

import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from watchlist_enricher.availability import canonical_service_name, normalize_section, service_kind
from watchlist_enricher.errors import CheckpointError, LookupFailure
from watchlist_enricher.models import Offer, SearchHit
from watchlist_enricher.textutil import fold_title

_SLUG_RE = re.compile(r"^/([a-z0-9]+(?:-[a-z0-9]+)*)-(\d{4})/?$")
_OTHER_SERVICES_RE = re.compile(r"available in \d+ other", re.IGNORECASE)
_FREE_HEADINGS = {
    "free",
    "ad supported",
    "free ad supported",
    "free with ads",
    "gratis",
    "con anuncios",
}


def is_checkpoint(html: str, status: int | None = None) -> bool:
    lowered = html.lower()
    if "vercel security checkpoint" in lowered:
        return True
    if "attention required" in lowered and "cloudflare" in lowered:
        return True
    if status in {401, 403, 429} and any(
        token in lowered for token in ("vercel", "checkpoint", "forbidden", "captcha")
    ):
        return True
    return False


def parse_title_html(html: str) -> list[Offer]:
    if is_checkpoint(html):
        raise CheckpointError(
            "Stream with VPN ha mostrado un control de seguridad (Vercel). "
            "No se intenta saltarlo; el título se deja igual."
        )
    soup = BeautifulSoup(html, "html.parser")
    for payload in _embedded_json(soup):
        offers = offers_from_json(payload)
        if offers:
            return _dedupe_offers(offers)
    offers = offers_from_data_sections(soup)
    if offers:
        return offers
    offers = offers_from_headings(soup)
    if offers:
        return offers
    raise LookupFailure(
        "La página no contiene una disponibilidad que se pueda leer. "
        "Puede que la ficha se pinte solo en el navegador."
    )


def parse_search_html(html: str) -> list[SearchHit]:
    if is_checkpoint(html):
        raise CheckpointError(
            "Stream with VPN ha mostrado un control de seguridad (Vercel) en la búsqueda. "
            "No se intenta saltarlo."
        )
    soup = BeautifulSoup(html, "html.parser")
    for payload in _embedded_json(soup):
        hits = hits_from_json(payload)
        if hits:
            return hits
    return hits_from_links(soup)


def offers_from_json(payload: object) -> list[Offer]:
    found: list[Offer] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            offer = _offer_from_mapping(node)
            if offer is not None:
                found.append(offer)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return _dedupe_offers(found)


def hits_from_json(payload: object) -> list[SearchHit]:
    found: list[SearchHit] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            hit = _hit_from_mapping(node)
            if hit is not None:
                found.append(hit)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return _dedupe_hits(found)


def offers_from_data_sections(soup: BeautifulSoup) -> list[Offer]:
    offers: list[Offer] = []
    for node in soup.select("[data-section]"):
        descendants = [child for child in node.find_all(attrs={"data-section": True}) if child is not node]
        if descendants:
            continue
        heading = node.find(["h2", "h3", "h4"])
        if heading is None:
            continue
        countries = tuple(item.get_text(" ", strip=True) for item in node.find_all("li"))
        section = normalize_section(str(node.get("data-section") or "catalog"))
        offers.append(Offer(heading.get_text(" ", strip=True), countries, section))
    return offers


def offers_from_headings(soup: BeautifulSoup) -> list[Offer]:
    section = "catalog"
    offers: list[Offer] = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True)
        folded = fold_title(text)
        if folded in _FREE_HEADINGS or "ad supported" in folded:
            section = "free"
            continue
        if _OTHER_SERVICES_RE.search(text):
            section = "dump"
            continue
        countries: list[str] = []
        sibling = heading.find_next_sibling()
        while sibling is not None and sibling.name not in {"h2", "h3", "h4"}:
            if getattr(sibling, "name", None) == "ul":
                countries.extend(item.get_text(" ", strip=True) for item in sibling.find_all("li"))
            sibling = sibling.find_next_sibling()
        if countries or service_kind(text):
            offers.append(Offer(text, tuple(countries), section))
    return offers


def hits_from_links(soup: BeautifulSoup) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for anchor in soup.find_all("a", href=True):
        parsed = slug_and_year(anchor["href"])
        if parsed is None:
            continue
        slug, year = parsed
        title = _clean_title(anchor.get_text(" ", strip=True), year)
        if not title:
            continue
        hits.append(SearchHit(title=title, year=year, slug=slug))
    return _dedupe_hits(hits)


def slug_and_year(href: str) -> tuple[str, int] | None:
    path = urlparse(href).path if href.startswith("http") else href.split("?", 1)[0]
    match = _SLUG_RE.fullmatch(path)
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}", int(match.group(2))


def _embedded_json(soup: BeautifulSoup) -> list[object]:
    payloads: list[object] = []
    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        script_id = script.get("id") or ""
        text = script.string or script.get_text() or ""
        stripped = text.strip()
        if not stripped:
            continue
        looks_json = (
            "json" in script_type
            or script_id == "__NEXT_DATA__"
            or (stripped.startswith("{") and stripped.endswith("}"))
            or (stripped.startswith("[") and stripped.endswith("]"))
        )
        if not looks_json:
            continue
        try:
            payloads.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return payloads


def _offer_from_mapping(node: dict) -> Offer | None:
    name = _first_string(node, ("service", "provider", "serviceName", "name"))
    if not name or service_kind(name) is None:
        return None
    countries = _country_names(node)
    section = "catalog"
    for key in ("section", "group", "category", "type"):
        value = node.get(key)
        if isinstance(value, str):
            section = normalize_section(value)
            break
    if service_kind(name) != "rtve" and not countries:
        return None
    return Offer(canonical_service_name(name), tuple(countries), section)


def _country_names(node: dict) -> list[str]:
    for key in ("countries", "regions", "countryCodes", "availableIn"):
        value = node.get(key)
        names = _coerce_countries(value)
        if names is not None:
            return names
    return []


def _coerce_countries(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            label = item.get("name") or item.get("country") or item.get("code") or item.get("countryCode")
            if isinstance(label, str) and label.strip():
                names.append(label.strip())
            else:
                return None
        else:
            return None
    return names


def _hit_from_mapping(node: dict) -> SearchHit | None:
    title = node.get("title") or node.get("name")
    if not isinstance(title, str) or not title.strip():
        return None
    slug = node.get("slug")
    if not isinstance(slug, str) or not slug:
        href = node.get("url") or node.get("href") or ""
        if isinstance(href, str):
            parsed = slug_and_year(href)
            if parsed is None:
                return None
            slug, year_from_slug = parsed
        else:
            return None
    else:
        year_from_slug = None
        parsed = slug_and_year("/" + slug if not slug.startswith("/") else slug)
        if parsed:
            slug, year_from_slug = parsed
        elif not re.fullmatch(r"[a-z0-9-]+", slug):
            return None
    year = node.get("year") if isinstance(node.get("year"), int) else node.get("releaseYear")
    if not isinstance(year, int):
        year = year_from_slug
    if year is None:
        return None
    return SearchHit(title=_clean_title(title, year), year=year, slug=slug)


def _clean_title(title: str, year: int | None) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip()
    if year is not None and cleaned.endswith(str(year)):
        cleaned = cleaned[: -len(str(year))].strip(" -–—(")
    return cleaned.strip()


def _first_string(node: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _dedupe_offers(offers: list[Offer]) -> list[Offer]:
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    unique: list[Offer] = []
    for offer in offers:
        key = (offer.service, offer.countries, offer.section)
        if key in seen:
            continue
        seen.add(key)
        unique.append(offer)
    return unique


def _dedupe_hits(hits: list[SearchHit]) -> list[SearchHit]:
    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in hits:
        if hit.slug in seen:
            continue
        seen.add(hit.slug)
        unique.append(hit)
    return unique
