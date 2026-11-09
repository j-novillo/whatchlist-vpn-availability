"""Choose a Stream with VPN hit for a resolved title."""

from difflib import SequenceMatcher

from watchlist_enricher.models import SearchHit
from watchlist_enricher.textutil import fold_title

# Below this, the closest title is treated as a miss rather than a warning.
# "Nuremberg" vs "The Godfather" is about 0.27; a real near-miss is above 0.5.
MIN_SIMILARITY = 0.45


def titles_equal(left: str, right: str) -> bool:
    """Case-insensitive equality. Accents and punctuation do not count.

    Containment is not equality: "Nuremberg" is not "Judgment at Nuremberg".
    """

    return fold_title(left) == fold_title(right)


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, fold_title(left), fold_title(right)).ratio()


def pick_hit(hits: list[SearchHit], resolved_name: str) -> tuple[SearchHit | None, bool]:
    """Return ``(hit, exact)``.

    Exact matches win over titles that merely contain the name. Several exact
    matches resolve to the most recent year. With no exact match, the closest
    title is returned and ``exact`` is False so the line can be flagged.
    """

    if not hits:
        return None, False
    exact = [hit for hit in hits if titles_equal(hit.title, resolved_name)]
    if exact:
        exact.sort(key=lambda hit: (hit.year is None, -(hit.year or 0)))
        return exact[0], True
    ranked = sorted(
        hits,
        key=lambda hit: (similarity(hit.title, resolved_name), hit.year or -1),
        reverse=True,
    )
    best = ranked[0]
    if similarity(best.title, resolved_name) < MIN_SIMILARITY:
        return None, False
    return best, False
