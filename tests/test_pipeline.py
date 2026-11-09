from watchlist_enricher.errors import VerificationError
from watchlist_enricher.models import Note, Offer, SearchHit
from watchlist_enricher.pipeline import run_sync
from watchlist_enricher.textutil import fold_title


class MapResolver:
    def resolve(self, query: str) -> str | None:
        return {"Nuermberg": "Nuremberg"}.get(query)


class Catalog:
    def __init__(self, fail: str | None = None):
        self.fail = fail

    def search(self, query: str):
        if self.fail and fold_title(query) == self.fail:
            raise RuntimeError("boom")
        if fold_title(query) == "nuremberg":
            return [
                SearchHit("Nuremberg", 2000, "nuremberg-2000"),
                SearchHit("Nuremberg", 2025, "nuremberg-2025"),
            ]
        if fold_title(query) == "bare":
            return [SearchHit("Bare", 1999, "bare-1999")]
        raise RuntimeError(query)

    def availability(self, hit: SearchHit):
        if hit.slug == "bare-1999":
            return [Offer("Movistar Plus+", ("Spain",), "catalog")]
        return [Offer("Netflix", ("United States",), "catalog")]


class RecordingKeep:
    def __init__(self, calls: list):
        self.calls = calls
        self.notes = {
            "old": Note(id="old", title="Para ver", text="Inception\nNuermberg", kind="list", checked=[True, False])
        }
        self.fail_create = False
        self.corrupt = False

    def get_note(self, note_id: str) -> Note:
        self.calls.append(("get", note_id))
        note = self.notes[note_id]
        if self.corrupt and note_id == "new":
            return Note(id="new", title=note.title, text="CORRUPTO", kind=note.kind)
        return note

    def create_note(self, title: str, text: str, *, kind: str = "text", checked=None) -> Note:
        self.calls.append(("create", title, text, kind, checked))
        if self.fail_create:
            raise RuntimeError("create failed")
        note = Note(id="new", title=title, text=text, kind=kind, checked=checked)
        self.notes["new"] = note
        return note

    def delete_note(self, note_id: str) -> None:
        self.calls.append(("delete", note_id))
        del self.notes[note_id]


class RecordingSnapshot:
    def __init__(self, text: str, calls: list):
        self.text = text
        self.calls = calls

    def read(self) -> str:
        self.calls.append(("snapshot-read",))
        return self.text

    def write(self, text: str) -> None:
        self.calls.append(("snapshot-write", text))
        self.text = text


def _kinds(calls: list) -> list[str]:
    return [call[0] for call in calls if call[0] != "snapshot-read"]


def test_create_and_verify_happen_before_delete_and_snapshot():
    calls: list = []
    keep = RecordingKeep(calls)
    snapshot = RecordingSnapshot("Inception", calls)
    note = keep.notes["old"]
    report = run_sync(note, snapshot, MapResolver(), Catalog(), keep=keep, publish="keep")
    assert _kinds(calls) == ["create", "get", "delete", "snapshot-write"]
    assert "old" not in keep.notes
    assert keep.notes["new"].text == "Inception\nNuermberg (Netflix, Estados Unidos)"
    assert keep.notes["new"].checked == [True, False]
    assert report.new_note_id == "new"
    assert "Nuermberg (Netflix, Estados Unidos)" in snapshot.text
    created = next(call for call in calls if call[0] == "create")
    assert created[1] == "Para ver"
    assert created[3] == "list"


def test_create_failure_does_not_delete_or_touch_the_snapshot():
    calls: list = []
    keep = RecordingKeep(calls)
    keep.fail_create = True
    snapshot = RecordingSnapshot("Inception", calls)
    try:
        run_sync(keep.notes["old"], snapshot, MapResolver(), Catalog(), keep=keep, publish="keep")
    except VerificationError:
        pass
    else:
        raise AssertionError("la creación fallida tiene que abortar")
    assert "delete" not in _kinds(calls)
    assert "snapshot-write" not in _kinds(calls)
    assert "old" in keep.notes


def test_verify_failure_does_not_delete():
    calls: list = []
    keep = RecordingKeep(calls)
    keep.corrupt = True
    snapshot = RecordingSnapshot("Inception", calls)
    try:
        run_sync(keep.notes["old"], snapshot, MapResolver(), Catalog(), keep=keep, publish="keep")
    except VerificationError:
        pass
    else:
        raise AssertionError("una verificación fallida tiene que abortar")
    assert "delete" not in _kinds(calls)
    assert "old" in keep.notes
    assert "new" in keep.notes
    assert snapshot.text == "Inception"


def test_dry_run_does_not_create_or_delete_and_can_update_only_the_snapshot():
    calls: list = []
    keep = RecordingKeep(calls)
    snapshot = RecordingSnapshot("Inception", calls)
    report = run_sync(
        keep.notes["old"],
        snapshot,
        MapResolver(),
        Catalog(),
        keep=keep,
        publish="none",
        update_snapshot=True,
    )
    assert "create" not in _kinds(calls)
    assert "delete" not in _kinds(calls)
    assert report.dry_run is True
    assert report.snapshot_updated is True
    assert "Nuermberg (Netflix, Estados Unidos)" in snapshot.text


def test_failed_lookup_is_left_out_of_the_snapshot_so_it_can_be_retried():
    calls: list = []
    keep = RecordingKeep(calls)
    keep.notes["old"] = Note(id="old", title="Para ver", text="Nuermberg\nParasite", kind="text")
    snapshot = RecordingSnapshot("", calls)
    report = run_sync(keep.notes["old"], snapshot, MapResolver(), Catalog(fail="parasite"), keep=keep, publish="keep")
    assert report.new_text == "Nuermberg (Netflix, Estados Unidos)\nParasite"
    assert "Parasite" not in snapshot.text
    assert "Nuermberg (Netflix, Estados Unidos)" in snapshot.text
    assert report.failures


def test_unchanged_line_with_no_platforms_updates_the_snapshot_without_recreating_keep():
    calls: list = []
    keep = RecordingKeep(calls)
    keep.notes["old"] = Note(id="old", title="Para ver", text="Bare", kind="text")
    snapshot = RecordingSnapshot("", calls)
    report = run_sync(keep.notes["old"], snapshot, MapResolver(), Catalog(), keep=keep, publish="keep")
    assert report.unchanged is True
    assert "create" not in _kinds(calls)
    assert "delete" not in _kinds(calls)
    assert snapshot.text.strip() == "Bare"
