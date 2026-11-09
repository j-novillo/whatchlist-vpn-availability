"""Resolve a typed title to the English TMDB name.

Spanish input and small typos are TMDB's job. The user's original wording stays
on the Keep line; the English title is only used to search Stream with VPN.
"""

import json
from pathlib import Path

import requests

from watchlist_enricher.errors import LookupFailure
from watchlist_enricher.textutil import fold_title

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/multi"


def pick_tmdb_title(payload: dict) -> str | None:
    """First movie or TV hit. TMDB ranks by relevance, which covers typos.

    ``language=en-US`` makes ``title`` / ``name`` the English name. People
    results are skipped.
    """

    for item in payload.get("results") or []:
        if item.get("media_type") not in {"movie", "tv"}:
            continue
        title = item.get("title") or item.get("name")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return None


class NullResolver:
    """Used when no TMDB key and no fixture map are configured."""

    def resolve(self, query: str) -> str | None:
        return None


class FixtureResolver:
    """Query → English title, for tests and for a local dry-run without a key."""

    def __init__(self, path: Path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise LookupFailure(f"El fichero TMDB {path} debe ser un objeto JSON")
        self._map = {fold_title(str(key)): str(value) for key, value in raw.items()}

    def resolve(self, query: str) -> str | None:
        return self._map.get(fold_title(query))


class TmdbClient:
    def __init__(self, api_key: str, transport=None, timeout: float = 20):
        if not api_key:
            raise LookupFailure("Falta TMDB_API_KEY")
        self.api_key = api_key
        self.transport = transport
        self.timeout = timeout

    def resolve(self, query: str) -> str | None:
        payload = self._fetch(query)
        return pick_tmdb_title(payload)

    def _fetch(self, query: str) -> dict:
        if self.transport is not None:
            return self.transport(query)
        try:
            response = requests.get(
                TMDB_SEARCH_URL,
                params={
                    "query": query,
                    "language": "en-US",
                    "include_adult": "false",
                    "api_key": self.api_key,
                },
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LookupFailure(f"TMDB no disponible: {exc}") from exc
        if response.status_code != 200:
            raise LookupFailure(f"TMDB respondió {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise LookupFailure("TMDB no devolvió JSON") from exc
