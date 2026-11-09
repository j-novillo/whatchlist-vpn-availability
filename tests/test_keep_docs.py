import json
from pathlib import Path

from watchlist_enricher.errors import ConfigError
from watchlist_enricher.google_docs import build_replace_requests, document_end_index, extract_plain_text
from watchlist_enricher.keep.official import OfficialKeep, note_from_api, note_to_create_body
from watchlist_enricher.keep.unofficial import UnofficialKeep
from watchlist_enricher.models import Note
from watchlist_enricher.tmdb import pick_tmdb_title

FIXTURES = Path(__file__).parent / "fixtures"


def test_keep_text_and_list_payloads_round_trip():
    text_note = note_from_api(json.loads((FIXTURES / "keep" / "text_note.json").read_text(encoding="utf-8")))
    assert text_note.id == "abc123"
    assert text_note.kind == "text"
    assert text_note.text == "Nuremberg\nParasite"
    assert note_to_create_body(text_note)["body"]["text"]["text"] == "Nuremberg\nParasite"

    list_note = note_from_api(json.loads((FIXTURES / "keep" / "list_note.json").read_text(encoding="utf-8")))
    assert list_note.kind == "list"
    assert list_note.text == "Nuremberg\ncomentario\nParasite"
    assert list_note.checked == [False, False, True]


class _Exec:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Notes:
    def __init__(self):
        self.created = []
        self.deleted = []

    def get(self, name):
        return _Exec({"name": name, "title": "Para ver", "body": {"text": {"text": "Nuremberg"}}})

    def create(self, body):
        self.created.append(body)
        return _Exec({"name": "notes/new-id", "title": body["title"], "body": body["body"]})

    def delete(self, name):
        self.deleted.append(name)
        return _Exec({})

    def list(self, pageSize=100, pageToken=None):
        return _Exec(
            {
                "notes": [
                    {"name": "notes/old", "title": "Para ver", "trashed": True, "updateTime": "2026-11-03T00:00:00Z", "body": {"text": {"text": "no"}}},
                    {"name": "notes/a", "title": "Para ver", "updateTime": "2026-11-01T00:00:00Z", "body": {"text": {"text": "vieja"}}},
                    {"name": "notes/b", "title": "Para ver", "updateTime": "2026-11-02T00:00:00Z", "body": {"text": {"text": "nueva"}}},
                ]
            }
        )


class _Service:
    def __init__(self):
        self._notes = _Notes()

    def notes(self):
        return self._notes


def test_official_adapter_creates_before_any_delete_and_finds_the_newest_title():
    service = _Service()
    keep = OfficialKeep(service)
    created = keep.create_note("Para ver", "Nuremberg")
    assert created.id == "new-id"
    assert service._notes.deleted == []
    assert service._notes.created[0]["title"] == "Para ver"
    found = keep.find_by_title("Para ver")
    assert found.id == "b"
    assert found.text == "nueva"
    keep.delete_note("old")
    assert service._notes.deleted == ["notes/old"]


class _GNote:
    def __init__(self):
        self.id = "local-1"
        self.title = ""
        self.text = ""
        self.deleted = False
        self.trashed = False

    def delete(self):
        self.deleted = True


class _GList:
    def __init__(self):
        self.id = "local-list"
        self.title = ""
        self.items = []
        self.deleted = False

    def delete(self):
        self.deleted = True


class _Item:
    def __init__(self, text, checked):
        self.text = text
        self.checked = checked


class _GKeep:
    def __init__(self):
        self.calls: list[str] = []
        self.fail_sync = False
        self.note = None

    def createNote(self, title, text):
        self.calls.append("createNote")
        self.note = _GNote()
        self.note.title = title
        self.note.text = text
        return self.note

    def createList(self, title, items):
        self.calls.append("createList")
        self.note = _GList()
        self.note.title = title
        self.note.items = [_Item(text, checked) for text, checked in items]
        return self.note

    def sync(self):
        self.calls.append("sync")
        if self.fail_sync:
            raise RuntimeError("sync failed")

    def get(self, node_id):
        self.calls.append("get")
        return self.note

    def all(self):
        return [] if self.note is None else [self.note]


def test_unofficial_adapter_syncs_create_and_does_not_delete_if_sync_fails():
    client = _GKeep()
    keep = UnofficialKeep(keep=client)
    created = keep.create_note("Para ver", "Hola", kind="text")
    assert created.text == "Hola"
    assert client.calls == ["createNote", "sync"]
    assert client.note.deleted is False

    client.fail_sync = True
    try:
        keep.create_note("Para ver", "Otra", kind="list", checked=[True])
    except ConfigError as exc:
        assert "no se toca" in str(exc)
    else:
        raise AssertionError("un sync fallido tiene que abortar la creación")
    assert "delete" not in client.calls
    assert client.note.deleted is False


def test_unofficial_delete_is_a_separate_step():
    client = _GKeep()
    keep = UnofficialKeep(keep=client)
    keep.create_note("Para ver", "Hola")
    keep.delete_note("local-1")
    assert client.calls == ["createNote", "sync", "get", "sync"]
    assert client.note.deleted is True


def test_docs_replace_requests_leave_the_trailing_newline_slot():
    assert build_replace_requests(1, "Hola") == [
        {"insertText": {"location": {"index": 1}, "text": "Hola\n"}}
    ]
    requests = build_replace_requests(10, "")
    assert requests == [
        {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": 9}}}
    ]
    document = {
        "body": {
            "content": [
                {"endIndex": 1, "sectionBreak": {}},
                {
                    "endIndex": 18,
                    "paragraph": {"elements": [{"textRun": {"content": "Nuremberg\nParasite\n"}}]},
                },
            ]
        }
    }
    assert extract_plain_text(document) == "Nuremberg\nParasite"
    assert document_end_index(document) == 18


def test_tmdb_skips_people_and_reads_tv_name():
    assert pick_tmdb_title(
        {
            "results": [
                {"media_type": "person", "name": "Alguien"},
                {"media_type": "movie", "title": "Nuremberg"},
            ]
        }
    ) == "Nuremberg"
    assert pick_tmdb_title({"results": [{"media_type": "tv", "name": "The Wire"}]}) == "The Wire"
    assert pick_tmdb_title({"results": []}) is None


def test_create_body_uses_the_note_model():
    payload = note_to_create_body(Note(id="", title="Para ver", text="Una", kind="text"))
    assert payload["body"]["text"]["text"] == "Una"
