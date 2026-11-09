from pathlib import Path

from watchlist_enricher.availability import format_availability
from watchlist_enricher.errors import CheckpointError, LookupFailure
from watchlist_enricher.streamwithvpn.client import HttpCatalog
from watchlist_enricher.streamwithvpn.parse import parse_search_html, parse_title_html

HTML = Path(__file__).parent / "fixtures" / "streamwithvpn" / "html"
BASE = "https://www.streamwithvpn.com"


def read(name: str) -> str:
    return (HTML / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text: str, status: int):
        self.text = text
        self.status_code = status


class FakeSession:
    def __init__(self, pages: dict[str, FakeResponse]):
        self.pages = pages
        self.urls: list[str] = []

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.urls.append(url)
        if url not in self.pages:
            return FakeResponse("missing", 404)
        return self.pages[url]


def test_checkpoint_page_is_not_parsed_as_a_title():
    try:
        parse_title_html(read("checkpoint.html"))
    except CheckpointError:
        return
    raise AssertionError("el checkpoint tendría que abortar el título")


def test_search_links_keep_the_unusual_amelie_slug_and_the_year():
    hits = parse_search_html(read("search-nuremberg.html"))
    by_slug = {hit.slug: hit for hit in hits}
    assert by_slug["nuremberg-2025"].title == "Nuremberg"
    assert by_slug["nuremberg-2025"].year == 2025
    assert by_slug["nuremberg-2000"].year == 2000
    assert by_slug["amlie-2001"].title == "Amélie"
    assert by_slug["amlie-2001"].year == 2001


def test_html_fixtures_format_the_verified_examples():
    assert format_availability(parse_title_html(read("nuremberg-2025.html"))) == "Netflix, Estados Unidos"
    assert format_availability(parse_title_html(read("parasite-2019.html"))) == "Netflix"
    assert format_availability(parse_title_html(read("synecdoche-new-york-2008.html"))) == "Prime Video, Australia"
    assert format_availability(parse_title_html(read("amlie-2001.html"))) == "Netflix, Canadá"


def test_dump_netflix_does_not_count_and_free_rtve_is_a_fallback():
    mixed = parse_title_html(read("headings-free-and-dump.html"))
    assert format_availability(mixed) == "Netflix, Estados Unidos"
    assert any(offer.section == "dump" and offer.service == "Netflix" for offer in mixed)
    assert format_availability(parse_title_html(read("rtve-only.html"))) == "RTVE Play"


def test_embedded_json_uses_codes_and_ignores_the_dump():
    offers = parse_title_html(read("embedded.json.html"))
    assert format_availability(offers) == "Netflix, Estados Unidos"
    assert any(offer.section == "free" and offer.service == "RTVE Play" for offer in offers)
    assert any(offer.section == "dump" for offer in offers)


def test_http_client_refuses_api_and_parses_public_pages():
    session = FakeSession(
        {
            f"{BASE}/search?q=Nuremberg": FakeResponse(read("search-nuremberg.html"), 200),
            f"{BASE}/nuremberg-2025": FakeResponse(read("nuremberg-2025.html"), 200),
            f"{BASE}/search?q=blocked": FakeResponse(read("checkpoint.html"), 403),
        }
    )
    client = HttpCatalog(session=session)
    try:
        client._get(f"{BASE}/api/search?q=Nuremberg")
    except LookupFailure as exc:
        assert "/api/" in str(exc)
    else:
        raise AssertionError("tenía que rechazar /api/")
    assert session.urls == []

    hits = client.search("Nuremberg")
    exact = [hit for hit in hits if hit.slug == "nuremberg-2025"]
    assert exact
    assert format_availability(client.availability(exact[0])) == "Netflix, Estados Unidos"
    try:
        client.search("blocked")
    except CheckpointError:
        return
    raise AssertionError("el checkpoint del cliente tenía que fallar el título")
