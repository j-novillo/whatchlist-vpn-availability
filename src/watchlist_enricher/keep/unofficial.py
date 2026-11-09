"""Optional gkeepapi backend.

This is not the happy path. Google Keep's official API does not fit a personal
account, and gkeepapi talks to a private mobile API that can break without
notice. The master token is read from the environment only. This module does
not scrape cookies and does not tell the caller how to mint a token.

Create syncs before returning. If that sync fails, delete is never called by
this object — the pipeline is what deletes, and only after create succeeds.
"""

import sys

from watchlist_enricher.errors import ConfigError, NoteNotFound
from watchlist_enricher.models import Note
from watchlist_enricher.textutil import normalize_note_text, split_note_lines


class UnofficialKeep:
    def __init__(self, email: str | None = None, master_token: str | None = None, *, keep=None, device_id: str | None = None):
        if keep is not None:
            self._keep = keep
            return
        else:
            if not email or not master_token:
                raise ConfigError(
                    "KEEP_BACKEND=unofficial necesita KEEP_USERNAME y KEEP_MASTER_TOKEN. "
                    "Es una vía no oficial e inestable. No está documentado cómo extraer el token."
                )
            gkeepapi = _load_library()
            client = gkeepapi.Keep()
            try:
                client.authenticate(email, master_token, device_id=device_id)
            except Exception as exc:  # noqa: BLE001 — library raises several login errors
                raise ConfigError(
                    "gkeepapi no ha aceptado KEEP_USERNAME / KEEP_MASTER_TOKEN. "
                    "El backend no oficial puede dejar de funcionar sin aviso."
                ) from exc
            self._keep = client
            print(
                "Aviso: KEEP_BACKEND=unofficial usa gkeepapi, una biblioteca no oficial "
                "que Google no soporta. Puede romperse. No es el camino recomendado.",
                file=sys.stderr,
            )

    def get_note(self, note_id: str) -> Note:
        gnote = self._keep.get(note_id)
        if gnote is None or _is_gone(gnote):
            raise NoteNotFound(f"No existe la nota de Keep {note_id}")
        return _to_note(gnote)

    def create_note(
        self,
        title: str,
        text: str,
        *,
        kind: str = "text",
        checked: list[bool] | None = None,
    ) -> Note:
        if kind == "list":
            lines = split_note_lines(text)
            flags = list(checked or [])
            items = [
                (line, bool(flags[index]) if index < len(flags) else False)
                for index, line in enumerate(lines)
            ]
            gnote = self._keep.createList(title, items)
        else:
            gnote = self._keep.createNote(title, text)
        try:
            self._keep.sync()
        except Exception as exc:  # noqa: BLE001
            raise ConfigError(
                "gkeepapi no ha podido subir la nota nueva. La nota antigua no se toca."
            ) from exc
        return _to_note(gnote)

    def delete_note(self, note_id: str) -> None:
        gnote = self._keep.get(note_id)
        if gnote is None:
            raise NoteNotFound(f"No existe la nota de Keep {note_id}")
        gnote.delete()
        self._keep.sync()

    def find_by_title(self, title: str) -> Note:
        matches = []
        for gnote in self._keep.all():
            if _is_gone(gnote):
                continue
            if (getattr(gnote, "title", None) or "") == title:
                matches.append(gnote)
        if not matches:
            raise NoteNotFound(f"No hay una nota de Keep con el título {title!r}")
        matches.sort(key=_updated_stamp, reverse=True)
        return _to_note(matches[0])


def _load_library():
    try:
        import gkeepapi
    except ImportError as exc:
        raise ConfigError(
            "El backend no oficial necesita el extra opcional: pip install -e '.[unofficial]'."
        ) from exc
    return gkeepapi


def _is_gone(gnote) -> bool:
    return bool(getattr(gnote, "trashed", False) or getattr(gnote, "deleted", False))


def _updated_stamp(gnote) -> str:
    timestamps = getattr(gnote, "timestamps", None)
    updated = getattr(timestamps, "updated", None)
    return "" if updated is None else str(updated)


def _to_note(gnote) -> Note:
    if type(gnote).__name__ == "List":
        lines: list[str] = []
        checked: list[bool] = []
        for item in gnote.items:
            text = (getattr(item, "text", "") or "").strip()
            if not text:
                continue
            lines.append(text)
            checked.append(bool(getattr(item, "checked", False)))
        return Note(
            id=str(gnote.id),
            title=gnote.title or "",
            text="\n".join(lines),
            kind="list",
            checked=checked,
        )
    return Note(
        id=str(gnote.id),
        title=getattr(gnote, "title", "") or "",
        text=normalize_note_text(getattr(gnote, "text", "") or ""),
        kind="text",
    )
