"""Line normalization for watchlist notes."""

import re
import unicodedata

# Checkbox markers used by Keep exports and by our own plain-text round trip.
# A bare bullet ("- title") is intentionally not stripped: it can be part of a title.
_CHECKLIST_RE = re.compile(
    r"^((?:\s*[-*]\s+)?(?:\[[ xX]\]|[☐☑✓✔□])\s+)"
)
_WARNING_RE = re.compile(r"^⚠\ufe0f?\s*")
# Only the suffixes this program writes. A year in parentheses stays in the title.
_SERVICE_SUFFIX_RE = re.compile(
    r"\s+\((?:Netflix|Prime Video|RTVE Play)(?:,\s*[^)]+)?\)\s*$"
)


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def fold_title(value: str) -> str:
    """Case, accent, and punctuation insensitive key for a title."""

    folded = strip_accents(value).casefold()
    folded = re.sub(r"[^\w\s]", " ", folded, flags=re.UNICODE)
    return re.sub(r"\s+", " ", folded).strip()


def split_note_lines(text: str) -> list[str]:
    """Split a note into lines, ignoring a single surrounding blank edge."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized:
        return []
    return normalized.split("\n")


def normalize_note_text(text: str) -> str:
    return "\n".join(split_note_lines(text))


def split_checklist_prefix(line: str) -> tuple[str, str]:
    match = _CHECKLIST_RE.match(line)
    if not match:
        return "", line
    return match.group(1), line[match.end() :]


def strip_warning(body: str) -> str:
    return _WARNING_RE.sub("", body, count=1)


def strip_service_suffix(body: str) -> str:
    return _SERVICE_SUFFIX_RE.sub("", body)


def line_key(line: str) -> str:
    """Identity of a line, ignoring checklist marks, warnings, and our suffix."""

    _prefix, body = split_checklist_prefix(line)
    body = strip_warning(body.strip())
    body = strip_service_suffix(body).strip()
    return fold_title(body)


def is_already_enriched(line: str) -> bool:
    """True when a previous run already wrote a warning or a service suffix."""

    _prefix, body = split_checklist_prefix(line)
    body = body.strip()
    if _WARNING_RE.match(body):
        return True
    return _SERVICE_SUFFIX_RE.search(body) is not None


def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for index, left_char in enumerate(left, start=1):
        current = [index]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current[right_index - 1] + 1
            delete_cost = previous[right_index] + 1
            replace_cost = previous[right_index - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def is_light_edit(left: str, right: str) -> bool:
    """True when ``right`` is a small in-place edit of ``left``, not a new title.

    One-character typos always count. Two-character typos count only on longer
    titles, so short replacements ("It" → "Us") stay new. An extra word
    ("Dune" → "Dune 2") is a different title.
    """

    if not left or not right:
        return False
    if left == right:
        return True
    tokens_left = left.split()
    tokens_right = right.split()
    if len(tokens_left) != len(tokens_right):
        shorter, longer = (
            (tokens_left, tokens_right)
            if len(tokens_left) < len(tokens_right)
            else (tokens_right, tokens_left)
        )
        if longer[: len(shorter)] == shorter:
            return False
    distance = levenshtein(left, right)
    gap = abs(len(left) - len(right))
    if distance <= 1 and gap <= 1:
        return True
    return distance <= 2 and gap <= 2 and min(len(left), len(right)) >= 6


def render_line(original: str, suffix: str | None, warn: bool) -> str:
    """Keep the user's wording and checklist prefix; optionally warn and annotate."""

    prefix, body = split_checklist_prefix(original)
    title = body.strip()
    shown = f"⚠️ {title}" if warn else title
    if suffix:
        shown = f"{shown} ({suffix})"
    return f"{prefix}{shown}"
