from watchlist_enricher.diff import new_line_indexes
from watchlist_enricher.textutil import split_note_lines


def _new(current: str, previous: str) -> list[str]:
    lines = split_note_lines(current)
    return [lines[index] for index in new_line_indexes(current, previous)]


def test_brand_new_line_is_detected():
    assert _new("Inception\nParasite", "Inception") == ["Parasite"]


def test_reordered_lines_are_not_new():
    current = "Parasite\nInception\nThe Matrix"
    previous = "The Matrix\nInception\nParasite"
    assert _new(current, previous) == []


def test_already_enriched_line_matches_plain_snapshot():
    current = "Inception\nParasite (Netflix)"
    previous = "Parasite\nInception"
    assert _new(current, previous) == []


def test_already_enriched_line_is_skipped_even_if_snapshot_lacks_it():
    current = "Parasite (Netflix)\n⚠️ Amelie (Prime Video, Francia)"
    assert _new(current, "") == []


def test_light_edit_in_place_is_not_new():
    assert _new("Incepton", "Inception") == []
    assert _new("Nuermberg", "Nuremberg") == []


def test_light_edit_does_not_hide_a_second_similar_title():
    assert _new("Inception\nIncepton", "Inception") == ["Incepton"]


def test_extra_word_is_a_new_title():
    assert _new("Dune: Part Two", "Dune") == ["Dune: Part Two"]


def test_short_replacement_is_new():
    assert _new("Us", "It") == ["Us"]


def test_checklist_prefix_does_not_create_a_false_new_line():
    current = "[x] Parasite (Netflix)\n[ ] Inception"
    previous = "Inception\nParasite"
    assert _new(current, previous) == []


def test_new_checklist_item_keeps_its_place():
    current = "[ ] Inception\n[ ] Amélie"
    previous = "[x] Inception"
    assert _new(current, previous) == ["[ ] Amélie"]
