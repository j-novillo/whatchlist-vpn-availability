"""Look up new lines and rewrite them. One failure does not stop the run."""

from collections import Counter

from watchlist_enricher.availability import format_availability
from watchlist_enricher.diff import new_line_indexes
from watchlist_enricher.errors import LookupFailure
from watchlist_enricher.matching import pick_hit
from watchlist_enricher.models import EnrichResult, TitleChange, TitleFailure
from watchlist_enricher.textutil import render_line, split_note_lines


class TitleResolver:
    """TMDB-shaped resolver. ``resolve`` returns an English title or None."""

    def resolve(self, query: str) -> str | None:
        return None


class Catalog:
    """Search plus availability. Implementations must not raise for one bad title
    without wrapping the error in LookupFailure.
    """

    def search(self, query: str) -> list:
        raise NotImplementedError

    def availability(self, hit) -> list:
        raise NotImplementedError


def enrich_line(line: str, resolver: TitleResolver | None, catalog: Catalog) -> tuple[str, TitleChange]:
    """Rewrite one new line. Raises LookupFailure when the lookup cannot be done."""

    _prefix, body = _split_visible_title(line)
    title = body.strip()
    searched_as = title
    if resolver is not None:
        try:
            resolved = resolver.resolve(title)
        except LookupFailure:
            resolved = None
        if resolved:
            searched_as = resolved
    try:
        hits = catalog.search(searched_as)
        hit, exact = pick_hit(hits, searched_as)
        if hit is None:
            raise LookupFailure(f"Sin una coincidencia usable para {searched_as!r}")
        offers = catalog.availability(hit)
    except LookupFailure:
        raise
    except Exception as exc:  # noqa: BLE001 — a parser bug on one page must not abort the run
        raise LookupFailure(f"No se ha podido leer la ficha de {searched_as!r}: {exc}") from exc
    suffix = format_availability(offers)
    rewritten = render_line(line, suffix, warn=not exact)
    change = TitleChange(
        before=line,
        after=rewritten,
        searched_as=searched_as,
        matched_title=hit.title,
        matched_year=hit.year,
        exact=exact,
        slug=hit.slug,
    )
    return rewritten, change


def enrich_text(current_text: str, previous_text: str, resolver: TitleResolver | None, catalog: Catalog) -> EnrichResult:
    lines = split_note_lines(current_text)
    changes: list[TitleChange] = []
    failures: list[TitleFailure] = []
    for index in new_line_indexes(current_text, previous_text):
        original = lines[index]
        try:
            rewritten, change = enrich_line(original, resolver, catalog)
        except LookupFailure as exc:
            failures.append(TitleFailure(line=original, message=str(exc)))
            continue
        lines[index] = rewritten
        changes.append(change)
    return EnrichResult(text="\n".join(lines), changes=changes, failures=failures)


def snapshot_text_for(note_text: str, failures: list[TitleFailure]) -> str:
    """Snapshot text.

    On a clean run it matches the note. Lines that failed the lookup are left
    out so the next run still sees them as new. Enriched lines stay, and the
    diff will not look them up again.
    """

    if not failures:
        return note_text
    pending: Counter[str] = Counter(failure.line for failure in failures)
    kept: list[str] = []
    for line in split_note_lines(note_text):
        if pending[line]:
            pending[line] -= 1
            continue
        kept.append(line)
    return "\n".join(kept)


def _split_visible_title(line: str) -> tuple[str, str]:
    from watchlist_enricher.textutil import split_checklist_prefix

    return split_checklist_prefix(line)
