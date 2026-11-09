"""Keep adapters. The pipeline creates a new note before it deletes the old one."""

from watchlist_enricher.keep.official import OfficialKeep, note_from_api, note_to_create_body
from watchlist_enricher.keep.unofficial import UnofficialKeep

__all__ = [
    "OfficialKeep",
    "UnofficialKeep",
    "note_from_api",
    "note_to_create_body",
]
