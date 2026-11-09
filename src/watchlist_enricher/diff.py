"""Find newly added watchlist lines.

Moved lines, already enriched lines, and light in-place edits are not new.
"""

from collections import Counter

from watchlist_enricher.textutil import (
    is_already_enriched,
    is_light_edit,
    levenshtein,
    line_key,
    split_note_lines,
)


def new_line_indexes(current_text: str, previous_text: str) -> list[int]:
    """Indexes in the current note that still need a lookup."""

    current = split_note_lines(current_text)
    previous = split_note_lines(previous_text)
    available: Counter[str] = Counter()
    for line in previous:
        key = line_key(line)
        if key:
            available[key] += 1

    unmatched: list[int] = []
    for index, line in enumerate(current):
        key = line_key(line)
        if not key:
            continue
        if is_already_enriched(line):
            if available[key]:
                available[key] -= 1
            continue
        if available[key]:
            available[key] -= 1
            continue
        unmatched.append(index)

    remaining: list[str] = []
    for key, count in available.items():
        remaining.extend([key] * count)

    pairs: list[tuple[int, int, int]] = []
    for index in unmatched:
        key = line_key(current[index])
        for previous_index, previous_key in enumerate(remaining):
            if is_light_edit(key, previous_key):
                pairs.append((levenshtein(key, previous_key), index, previous_index))
    pairs.sort()

    matched_current: set[int] = set()
    matched_previous: set[int] = set()
    for _distance, index, previous_index in pairs:
        if index in matched_current or previous_index in matched_previous:
            continue
        matched_current.add(index)
        matched_previous.add(previous_index)

    return [index for index in unmatched if index not in matched_current]
