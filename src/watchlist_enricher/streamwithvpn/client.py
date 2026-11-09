"""HTTP client for public Stream with VPN pages.

robots.txt allows the site and disallows /api/. This client never requests
that prefix, never solves a checkpoint, and turns a block into a per-title
failure.
"""

from urllib.parse import quote_plus, urlparse

import requests

from watchlist_enricher.errors import CheckpointError, LookupFailure
from watchlist_enricher.models import Offer, SearchHit
from watchlist_enricher.streamwithvpn.parse import is_checkpoint, parse_search_html, parse_title_html

DEFAULT_BASE_URL = "https://www.streamwithvpn.com"
ALLOWED_HOSTS = {"www.streamwithvpn.com", "streamwithvpn.com"}
USER_AGENT = (
    "watchlist-enricher/0.1 (personal Keep watchlist; "
    "public HTML only, does not call /api/)"
)


class HttpCatalog:
    def __init__(self, session=None, timeout: float = 20, base_url: str = DEFAULT_BASE_URL):
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.session = session or _default_session()

    def search(self, query: str) -> list[SearchHit]:
        # Autocomplete on the site is a browser widget. The public search page
        # is the HTTP equivalent; we do not call the disallowed /api/ route.
        url = f"{self.base_url}/search?q={quote_plus(query)}"
        html = self._get(url)
        hits = parse_search_html(html)
        if not hits:
            raise LookupFailure(
                f"Sin resultados de búsqueda para {query!r}. "
                "El autocompletado puede no estar en el HTML y /api/ no se usa."
            )
        return hits

    def availability(self, hit: SearchHit) -> list[Offer]:
        url = f"{self.base_url}/{_safe_slug(hit.slug)}"
        html = self._get(url)
        return parse_title_html(html)

    def _get(self, url: str) -> str:
        _refuse_disallowed(url)
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise LookupFailure(f"No se ha podido descargar {url}: {exc}") from exc
        status = getattr(response, "status_code", 200)
        text = getattr(response, "text", "") or ""
        if is_checkpoint(text, status):
            raise CheckpointError(
                "Stream with VPN ha respondido con un control de Vercel o un bloqueo. "
                "El título se omite."
            )
        if status == 404:
            raise LookupFailure(f"No existe la página {url}")
        if status >= 400:
            raise LookupFailure(f"Stream with VPN respondió {status} al pedir {url}")
        return text


def _default_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.headers["Accept"] = "text/html,application/xhtml+xml"
    return session


def _safe_slug(slug: str) -> str:
    if not slug or "/" in slug or slug.startswith("api") or not slug.replace("-", "").isalnum():
        raise LookupFailure(f"Slug no válido: {slug!r}")
    return slug


def _refuse_disallowed(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise LookupFailure(f"Solo se piden páginas https ({url})")
    host = parsed.hostname or ""
    if host not in ALLOWED_HOSTS:
        raise LookupFailure(f"Host no permitido: {host}")
    path = parsed.path or "/"
    if path == "/api" or path.startswith("/api/"):
        raise LookupFailure("robots.txt no permite /api/; la petición se rechaza")

