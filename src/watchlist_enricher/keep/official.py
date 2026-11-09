"""Official Google Keep API.

The API can create, get, list, and delete notes. It cannot patch a note.
It is aimed at Workspace accounts with domain-wide delegation, not at a
personal Gmail login. This module only speaks the official REST shape.
"""

from watchlist_enricher.errors import NoteNotFound
from watchlist_enricher.models import Note
from watchlist_enricher.textutil import normalize_note_text, split_note_lines


def note_from_api(payload: dict) -> Note:
    name = payload.get("name") or ""
    note_id = name.split("/", 1)[-1] if name else ""
    title = payload.get("title") or ""
    body = payload.get("body") or {}
    list_body = body.get("list") if isinstance(body.get("list"), dict) else None
    if list_body is not None:
        lines: list[str] = []
        checked: list[bool] = []
        _collect_items(list_body.get("listItems") or [], lines, checked)
        return Note(
            id=note_id,
            title=title,
            text="\n".join(lines),
            kind="list",
            checked=checked,
        )
    text = ""
    text_body = body.get("text")
    if isinstance(text_body, dict):
        text = text_body.get("text") or ""
    return Note(id=note_id, title=title, text=normalize_note_text(text), kind="text")


def note_to_create_body(note: Note) -> dict:
    if note.kind == "list":
        lines = split_note_lines(note.text)
        flags = list(note.checked or [])
        items = []
        for index, line in enumerate(lines):
            items.append(
                {
                    "text": {"text": line},
                    "checked": bool(flags[index]) if index < len(flags) else False,
                }
            )
        return {"title": note.title, "body": {"list": {"listItems": items}}}
    return {"title": note.title, "body": {"text": {"text": note.text}}}


def _collect_items(items: list, lines: list[str], checked: list[bool]) -> None:
    for item in items:
        text = ((item.get("text") or {}).get("text") or "").strip()
        if text:
            lines.append(text)
            checked.append(bool(item.get("checked")))
        children = item.get("childListItems") or []
        if children:
            _collect_items(children, lines, checked)


class OfficialKeep:
    """Thin wrapper. ``service`` is a discovery resource for keep v1."""

    def __init__(self, service):
        self._service = service

    def get_note(self, note_id: str) -> Note:
        payload = self._service.notes().get(name=_resource_name(note_id)).execute()
        note = note_from_api(payload)
        if not note.id:
            note.id = note_id
        return note

    def create_note(
        self,
        title: str,
        text: str,
        *,
        kind: str = "text",
        checked: list[bool] | None = None,
    ) -> Note:
        body = note_to_create_body(Note(id="", title=title, text=text, kind=kind, checked=checked))
        payload = self._service.notes().create(body=body).execute()
        note = note_from_api(payload)
        return note

    def delete_note(self, note_id: str) -> None:
        self._service.notes().delete(name=_resource_name(note_id)).execute()

    def find_by_title(self, title: str) -> Note:
        matches: list[dict] = []
        page_token = None
        while True:
            kwargs = {"pageSize": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            payload = self._service.notes().list(**kwargs).execute()
            for note in payload.get("notes") or []:
                if note.get("trashed"):
                    continue
                if (note.get("title") or "") == title:
                    matches.append(note)
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        if not matches:
            raise NoteNotFound(f"No hay una nota de Keep con el título {title!r}")
        matches.sort(key=lambda note: note.get("updateTime") or "", reverse=True)
        return note_from_api(matches[0])


def _resource_name(note_id: str) -> str:
    if note_id.startswith("notes/"):
        return note_id
    return f"notes/{note_id}"


def build_service(credentials):
    from googleapiclient.discovery import build

    return build("keep", "v1", credentials=credentials, cache_discovery=False)
