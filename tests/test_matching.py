from watchlist_enricher.matching import pick_hit, titles_equal
from watchlist_enricher.models import SearchHit


def hit(title: str, year: int | None, slug: str) -> SearchHit:
    return SearchHit(title=title, year=year, slug=slug)


def test_exact_beats_titles_that_only_contain_the_name():
    chosen, exact = pick_hit(
        [
            hit("Judgment at Nuremberg", 1961, "judgment-at-nuremberg-1961"),
            hit("Nuremberg Trials", 2006, "nuremberg-trials-2006"),
            hit("Nuremberg", 2000, "nuremberg-2000"),
        ],
        "Nuremberg",
    )
    assert exact is True
    assert chosen is not None
    assert chosen.slug == "nuremberg-2000"


def test_most_recent_year_wins_when_the_title_is_the_same():
    chosen, exact = pick_hit(
        [
            hit("Nuremberg", 2000, "nuremberg-2000"),
            hit("Nuremberg", 2025, "nuremberg-2025"),
        ],
        "nuremberg",
    )
    assert exact is True
    assert chosen is not None
    assert chosen.year == 2025


def test_accents_and_case_count_as_the_same_title():
    assert titles_equal("Amélie", "amelie")
    assert titles_equal("Synecdoche, New York", "synecdoche new york")
    chosen, exact = pick_hit([hit("Amelie", 2001, "amlie-2001")], "Amélie")
    assert exact is True
    assert chosen is not None
    assert chosen.slug == "amlie-2001"


def test_no_exact_match_returns_the_closest_and_is_not_exact():
    chosen, exact = pick_hit(
        [
            hit("Judgment at Nuremberg", 1961, "judgment-at-nuremberg-1961"),
            hit("The Godfather", 1972, "the-godfather-1972"),
        ],
        "Nuremberg",
    )
    assert exact is False
    assert chosen is not None
    assert chosen.title == "Judgment at Nuremberg"


def test_unrelated_title_is_not_used():
    chosen, exact = pick_hit([hit("The Godfather", 1972, "the-godfather-1972")], "Nuremberg")
    assert chosen is None
    assert exact is False
