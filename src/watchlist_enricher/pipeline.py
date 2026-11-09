"""Orchestrate diff, lookup, and the create-then-delete Keep write.

The old note is deleted only after the new note has been created and its text
has been read back. A failed create or a failed check leaves the old note
untouched. Recreating a note drops Keep metadata; that is documented for Jorge
and repeated in the run output.
"""

from watchlist_enricher.enrich import enrich_text, snapshot_text_for
from watchlist_enricher.errors import EnricherError, VerificationError
from watchlist_enricher.models import Note, RunReport
from watchlist_enricher.textutil import normalize_note_text, split_note_lines


def aligned_checked(note: Note, new_text: str) -> list[bool] | None:
    if note.kind != "list":
        return None
    flags = list(note.checked or [])
    size = len(split_note_lines(new_text))
    if len(flags) < size:
        flags.extend([False] * (size - len(flags)))
    return flags[:size]


def publish_to_keep(keep, snapshot, original: Note, new_text: str, snapshot_body: str) -> Note:
    """Create, verify, delete, then update the snapshot. Never the other way around."""

    try:
        created = keep.create_note(
            original.title,
            new_text,
            kind=original.kind,
            checked=aligned_checked(original, new_text),
        )
    except EnricherError:
        raise
    except Exception as exc:
        raise VerificationError(
            "No se ha podido crear la nota nueva. La nota anterior no se ha borrado. "
            f"Detalle: {exc}"
        ) from exc
    try:
        verified = keep.get_note(created.id)
    except EnricherError:
        raise
    except Exception as exc:
        raise VerificationError(
            "No se ha podido leer la nota nueva para comprobarla. "
            f"La nota anterior ({original.id}) no se ha borrado. Detalle: {exc}"
        ) from exc
    if normalize_note_text(verified.text) != normalize_note_text(new_text):
        raise VerificationError(
            "La nota nueva no coincide con el texto que se iba a guardar. "
            f"Se conserva la nota anterior ({original.id}). "
            f"La nota nueva, si existe, es {created.id}. No se ha borrado nada."
        )
    try:
        keep.delete_note(original.id)
    except EnricherError:
        raise
    except Exception as exc:
        raise VerificationError(
            f"La nota nueva {created.id} está creada y verificada, pero no se ha podido "
            f"borrar la anterior ({original.id}). El snapshot no se ha actualizado. "
            f"Detalle: {exc}"
        ) from exc
    snapshot.write(snapshot_body)
    return created


def run_sync(
    note: Note,
    snapshot,
    resolver,
    catalog,
    *,
    keep=None,
    publish: str = "keep",
    update_snapshot: bool = True,
    file_writer=None,
) -> RunReport:
    """Enrich ``note`` against the snapshot.

    ``publish`` is ``keep`` (create, verify, delete), ``files`` (overwrite the
    local note file), or ``none`` (dry-run). ``update_snapshot`` lets a dry-run
    refresh the Doc or the snapshot file without touching Keep.
    """

    previous = snapshot.read()
    enriched = enrich_text(note.text, previous, resolver, catalog)
    new_text = enriched.text
    desired_snapshot = snapshot_text_for(new_text, enriched.failures)
    keep_changed = normalize_note_text(new_text) != normalize_note_text(note.text)
    snapshot_differs = normalize_note_text(desired_snapshot) != normalize_note_text(previous)
    report = RunReport(
        original_text=normalize_note_text(note.text),
        new_text=normalize_note_text(new_text),
        snapshot_text=normalize_note_text(desired_snapshot),
        changes=enriched.changes,
        failures=enriched.failures,
        dry_run=publish == "none",
        keep_written=False,
        snapshot_updated=False,
        new_note_id=None,
        old_note_id=note.id,
        unchanged=not keep_changed,
    )
    write_snapshot = snapshot_differs and (publish != "none" or update_snapshot)

    if publish == "none":
        if write_snapshot:
            snapshot.write(desired_snapshot)
            report.snapshot_updated = True
        return report

    if publish == "files":
        if keep_changed:
            if file_writer is None:
                raise VerificationError("Falta el escritor del fichero de la nota")
            file_writer(new_text)
            report.keep_written = True
        if write_snapshot:
            snapshot.write(desired_snapshot)
            report.snapshot_updated = True
        return report

    if keep is None:
        raise VerificationError("Falta el adaptador de Keep")
    if not keep_changed:
        if write_snapshot:
            snapshot.write(desired_snapshot)
            report.snapshot_updated = True
        return report

    created = publish_to_keep(
        keep=keep,
        snapshot=snapshot,
        original=note,
        new_text=new_text,
        snapshot_body=desired_snapshot,
    )
    report.keep_written = True
    report.snapshot_updated = True
    report.new_note_id = created.id
    return report
