"""Offline catalog built from a JSON file. Tests and dry-runs use this."""

import json
from pathlib import Path

from watchlist_enricher.errors import LookupFailure
from watchlist_enricher.models import Offer, SearchHit
from watchlist_enricher.textutil import fold_title


class FixtureCatalog:
    def __init__(self, path: Path):
        source = path
        if path.is_dir():
            source = path / "catalog.json"
        raw = json.loads(source.read_text(encoding="utf-8"))
        self.searches: dict[str, list[SearchHit]] = {}
        for key, hits in (raw.get("searches") or {}).items():
            parsed = [
                SearchHit(title=hit["title"], year=hit.get("year"), slug=hit["slug"])
                for hit in hits
            ]
            self.searches[fold_title(str(key))] = parsed
        self.pages: dict[str, list[Offer]] = {}
        for slug, page in (raw.get("pages") or {}).items():
            self.pages[slug] = [
                Offer(
                    service=offer["service"],
                    countries=tuple(offer.get("countries") or ()),
                    section=offer.get("section") or "catalog",
                )
                for offer in page.get("offers") or []
            ]

    def search(self, query: str) -> list[SearchHit]:
        hits = self.searches.get(fold_title(query))
        if not hits:
            raise LookupFailure(f"Sin resultados de búsqueda para {query!r}")
        return list(hits)

    def availability(self, hit: SearchHit) -> list[Offer]:
        try:
            return list(self.pages[hit.slug])
        except KeyError as exc:
            raise LookupFailure(f"Sin ficha para {hit.slug}") from exc
