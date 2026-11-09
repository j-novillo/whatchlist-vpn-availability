from watchlist_enricher.availability import format_availability
from watchlist_enricher.countries import best_country
from watchlist_enricher.models import Offer


def offer(service: str, countries: list[str], section: str = "catalog") -> Offer:
    return Offer(service, tuple(countries), section)


def test_netflix_in_spain_hides_the_country_and_beats_prime():
    assert format_availability(
        [
            offer("Prime Video", ["Spain", "Mexico"]),
            offer("Netflix", ["Spain", "United States"]),
        ]
    ) == "Netflix"


def test_prime_in_spain_beats_netflix_elsewhere():
    assert format_availability(
        [
            offer("Netflix", ["United States"]),
            offer("Prime Video", ["Spain", "Mexico"]),
        ]
    ) == "Prime Video"


def test_netflix_elsewhere_beats_prime_elsewhere():
    assert format_availability(
        [
            offer("Prime Video", ["Poland", "Mexico"]),
            offer("Netflix", ["United States", "United Kingdom"]),
        ]
    ) == "Netflix, Estados Unidos"


def test_prime_elsewhere_uses_the_best_country():
    assert format_availability(
        [offer("Prime Video", ["Australia", "New Zealand"])]
    ) == "Prime Video, Australia"


def test_verified_examples():
    nuremberg = [
        offer("Netflix", ["United States"]),
        offer("Prime Video", ["Mexico", "Argentina", "Colombia", "Chile", "Peru", "Uruguay", "Venezuela", "India", "Poland"]),
        offer("Movistar Plus+", ["Spain"]),
        offer("Netflix", ["Spain"], "dump"),
    ]
    parasite = [
        offer("Netflix", ["Spain", "United States"]),
        offer("Prime Video", ["Spain"]),
    ]
    synecdoche = [offer("Prime Video", ["Australia", "New Zealand"])]
    amelie = [offer("Netflix", ["Canada"])]
    assert format_availability(nuremberg) == "Netflix, Estados Unidos"
    assert format_availability(parasite) == "Netflix"
    assert format_availability(synecdoche) == "Prime Video, Australia"
    assert format_availability(amelie) == "Netflix, Canadá"


def test_rtve_play_is_only_the_free_section_fallback():
    assert format_availability([offer("RTVE Play", ["Spain"], "free")]) == "RTVE Play"
    assert format_availability([offer("RTVE Play", ["Spain"], "catalog")]) is None
    assert format_availability([offer("RTVE Play", ["Spain"], "dump")]) is None
    assert format_availability(
        [
            offer("Netflix", ["France"]),
            offer("RTVE Play", ["Spain"], "free"),
        ]
    ) == "Netflix, Francia"


def test_nothing_relevant_leaves_the_title_bare():
    assert format_availability([offer("Movistar Plus+", ["Spain"]), offer("HBO Max", ["United States"])]) is None


def test_country_priority_levels():
    assert best_country(["United Kingdom", "United States"]) == "Estados Unidos"
    assert best_country(["Australia", "France"]) == "Francia"
    assert best_country(["Australia", "Poland"]) == "Polonia"
    assert best_country(["Iceland", "Australia"]) == "Australia"
    assert best_country(["Malta", "Iceland"]) == "Islandia"
    assert best_country(["Mexico", "Poland"]) == "Polonia"
    assert best_country(["Argentina", "Mexico"]) == "México"
    assert best_country(["Ecuador", "Bolivia"]) == "Bolivia"
    assert best_country(["Japan", "Bolivia"]) == "Bolivia"
    assert best_country(["South Africa", "Japan"]) == "Japón"
    assert best_country(["France", "Spain", "United States"]) == "España"
    assert best_country(["AU"]) == "Australia"
    assert best_country(["AT"]) == "Austria"
    assert best_country(["US", "GB"]) == "Estados Unidos"
