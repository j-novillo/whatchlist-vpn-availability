from watchlist_enricher.enrich import enrich_line, enrich_text
from watchlist_enricher.errors import CheckpointError, LookupFailure
from watchlist_enricher.models import Offer, SearchHit
from watchlist_enricher.textutil import fold_title


class MapResolver:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def resolve(self, query: str) -> str | None:
        return self.mapping.get(query)


class DictCatalog:
    def __init__(self, searches: dict[str, list[SearchHit]], pages: dict[str, list[Offer]]):
        self.searches = searches
        self.pages = pages
        self.pages_fetched: list[str] = []

    def search(self, query: str) -> list[SearchHit]:
        key = fold_title(query)
        if key not in self.searches:
            raise LookupFailure(f"sin resultados para {query}")
        return self.searches[key]

    def availability(self, hit: SearchHit) -> list[Offer]:
        self.pages_fetched.append(hit.slug)
        if hit.slug not in self.pages:
            raise LookupFailure(f"sin ficha {hit.slug}")
        return self.pages[hit.slug]


NUREMBERG_HITS = [
    SearchHit("Judgment at Nuremberg", 1961, "judgment-at-nuremberg-1961"),
    SearchHit("Nuremberg", 2000, "nuremberg-2000"),
    SearchHit("Nuremberg", 2025, "nuremberg-2025"),
]
NUREMBERG_PAGE = [Offer("Netflix", ("United States",), "catalog")]


def test_typo_fixed_by_tmdb_matches_exactly_and_keeps_the_original_wording():
    catalog = DictCatalog(
        {"nuremberg": NUREMBERG_HITS},
        {"nuremberg-2025": NUREMBERG_PAGE, "nuremberg-2000": [Offer("Prime Video", ("Spain",), "catalog")]},
    )
    rewritten, change = enrich_line("Nuermberg", MapResolver({"Nuermberg": "Nuremberg"}), catalog)
    assert rewritten == "Nuermberg (Netflix, Estados Unidos)"
    assert change.exact is True
    assert change.matched_year == 2025
    assert catalog.pages_fetched == ["nuremberg-2025"]
    assert not rewritten.startswith("⚠️")


def test_no_exact_match_warns_and_still_formats_platforms():
    catalog = DictCatalog(
        {"nuremberg": [SearchHit("Judgment at Nuremberg", 1961, "judgment-at-nuremberg-1961")]},
        {"judgment-at-nuremberg-1961": NUREMBERG_PAGE},
    )
    rewritten, change = enrich_line("[ ] Nuremberg", MapResolver({}), catalog)
    assert rewritten == "[ ] ⚠️ Nuremberg (Netflix, Estados Unidos)"
    assert change.exact is False


def test_one_lookup_failure_does_not_drop_the_other_title():
    class Flaky(DictCatalog):
        def search(self, query: str):
            if fold_title(query) == "parasite":
                raise CheckpointError("checkpoint")
            return super().search(query)

    catalog = Flaky(
        {"nuremberg": NUREMBERG_HITS},
        {"nuremberg-2025": NUREMBERG_PAGE},
    )
    result = enrich_text("Nuermberg\nParasite", "", MapResolver({"Nuermberg": "Nuremberg"}), catalog)
    assert result.text.split("\n") == [
        "Nuermberg (Netflix, Estados Unidos)",
        "Parasite",
    ]
    assert len(result.failures) == 1
    assert "checkpoint" in result.failures[0].message
