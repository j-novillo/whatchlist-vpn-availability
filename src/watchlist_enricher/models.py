"""Shared data objects."""

from dataclasses import dataclass, field


@dataclass
class Note:
    """Plain-text view of a Keep note.

    ``text`` is one title per line. Checklist markers, when the note is a text
    note that already contains them, stay inside ``text``. For list notes,
    ``checked`` is aligned with those lines.
    """

    id: str
    title: str
    text: str
    kind: str = "text"
    checked: list[bool] | None = None


@dataclass(frozen=True)
class SearchHit:
    title: str
    year: int | None
    slug: str


@dataclass(frozen=True)
class Offer:
    """One service block on a title page.

    ``section`` is ``catalog`` (named service cards), ``free`` (free / ad-supported),
    or ``dump`` (the unnamed "other streaming services" logo pile).
    """

    service: str
    countries: tuple[str, ...]
    section: str = "catalog"


@dataclass(frozen=True)
class TitleChange:
    before: str
    after: str
    searched_as: str
    matched_title: str
    matched_year: int | None
    exact: bool
    slug: str


@dataclass(frozen=True)
class TitleFailure:
    line: str
    message: str


@dataclass
class EnrichResult:
    text: str
    changes: list[TitleChange] = field(default_factory=list)
    failures: list[TitleFailure] = field(default_factory=list)


@dataclass
class RunReport:
    original_text: str
    new_text: str
    snapshot_text: str
    changes: list[TitleChange]
    failures: list[TitleFailure]
    dry_run: bool
    keep_written: bool
    snapshot_updated: bool
    new_note_id: str | None
    old_note_id: str | None
    unchanged: bool
    implied_dry_run: bool = False
