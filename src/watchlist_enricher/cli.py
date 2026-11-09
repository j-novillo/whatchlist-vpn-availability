"""Command line entry point. Messages are Spanish; identifiers stay English."""

import argparse
import os
import sys
from pathlib import Path

from watchlist_enricher import __version__
from watchlist_enricher.errors import ConfigError, EnricherError
from watchlist_enricher.google_docs import FileSnapshot
from watchlist_enricher.models import Note
from watchlist_enricher.pipeline import run_sync
from watchlist_enricher.streamwithvpn.client import HttpCatalog
from watchlist_enricher.streamwithvpn.fixtures import FixtureCatalog
from watchlist_enricher.textutil import normalize_note_text
from watchlist_enricher.tmdb import FixtureResolver, NullResolver, TmdbClient


def main(argv: list[str] | None = None) -> int:
    load_environment()
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False) or getattr(args, "command", None) == "version":
        print(__version__)
        return 0
    if getattr(args, "command", None) != "sync":
        parser.print_help()
        return 2
    try:
        report = execute(args)
    except EnricherError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(render_report(report))
    return 1 if report.failures else 0


def execute(args):
    note, keep, file_writer = load_note(args)
    snapshot = load_snapshot(args)
    publish = publish_mode(args)
    if publish == "keep" and keep is None:
        raise ConfigError("Falta el adaptador de Keep")
    report = run_sync(
        note,
        snapshot,
        build_resolver(args),
        build_catalog(args),
        keep=keep,
        publish=publish,
        update_snapshot=args.update_snapshot,
        file_writer=file_writer,
    )
    report.implied_dry_run = implied_local_dry_run(args)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watchlist-enricher",
        description=(
            "Compara una nota de Google Keep con el snapshot de un Google Doc, "
            "busca los títulos nuevos en Stream with VPN y reescribe la nota."
        ),
    )
    parser.add_argument("--version", action="store_true", help="Muestra la versión y sale")
    sub = parser.add_subparsers(dest="command")
    sync = sub.add_parser("sync", help="Enriquecer los títulos nuevos")
    sync.add_argument("--note-file", help="Nota local (una línea por título), sin Google Keep")
    sync.add_argument("--snapshot-file", help="Snapshot local en vez del Google Doc")
    sync.add_argument("--note-id", default=os.environ.get("KEEP_NOTE_ID") or None)
    sync.add_argument("--note-title", default=os.environ.get("KEEP_NOTE_TITLE") or None)
    sync.add_argument("--doc-id", default=os.environ.get("DOCS_SNAPSHOT_ID") or None)
    sync.add_argument(
        "--dry-run",
        action="store_true",
        default=env_bool("DRY_RUN"),
        help="No crea ni borra notas. Imprime el texto nuevo.",
    )
    sync.add_argument(
        "--update-snapshot",
        action="store_true",
        default=env_bool("UPDATE_SNAPSHOT_IN_DRY_RUN"),
        help="En dry-run, actualiza solo el snapshot (Doc o fichero).",
    )
    sync.add_argument(
        "--apply-local",
        action="store_true",
        help="Con --note-file, escribe la nota y el snapshot en disco. No toca Keep.",
    )
    sync.add_argument("--fixtures", default=os.environ.get("STREAMWITHVPN_FIXTURES") or None)
    sync.add_argument("--tmdb-fixtures", default=os.environ.get("TMDB_FIXTURES") or None)
    sync.add_argument(
        "--keep-backend",
        default=os.environ.get("KEEP_BACKEND") or "auto",
        choices=("auto", "official", "unofficial"),
    )
    sync.add_argument(
        "--swv-backend",
        default=os.environ.get("STREAMWITHVPN_BACKEND") or "live",
        choices=("live", "fixtures", "browser"),
    )
    version = sub.add_parser("version", help="Muestra la versión")
    version.set_defaults(command="version")
    return parser


def load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)


def env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "si", "sí"}


def implied_local_dry_run(args) -> bool:
    return bool(args.note_file) and not args.apply_local and not args.dry_run


def publish_mode(args) -> str:
    if args.dry_run or implied_local_dry_run(args):
        return "none"
    if args.note_file:
        return "files"
    return "keep"


def load_note(args):
    if args.note_file:
        path = Path(args.note_file)
        if not path.is_file():
            raise ConfigError(f"No existe la nota local {path}")
        text = path.read_text(encoding="utf-8")
        note = Note(id=str(path), title=path.stem, text=normalize_note_text(text), kind="text")

        def writer(new_text: str, target=path) -> None:
            payload = new_text if new_text.endswith("\n") or new_text == "" else new_text + "\n"
            target.write_text(payload, encoding="utf-8")

        return note, None, writer
    if not args.note_id and not args.note_title:
        raise ConfigError(
            "Indica la nota: --note-file para una prueba local, o --note-id / --note-title "
            "(KEEP_NOTE_ID, KEEP_NOTE_TITLE) para Google Keep."
        )
    keep = build_keep(args)
    if args.note_id:
        note = keep.get_note(args.note_id)
    else:
        note = keep.find_by_title(args.note_title)
    return note, keep, None


def load_snapshot(args):
    if args.snapshot_file:
        return FileSnapshot(args.snapshot_file)
    if not args.doc_id:
        raise ConfigError(
            "Indica el snapshot: --snapshot-file o --doc-id (DOCS_SNAPSHOT_ID)."
        )
    from watchlist_enricher.google_auth import DOCS_SCOPE, load_google_credentials
    from watchlist_enricher.google_docs import GoogleDocsSnapshot, build_docs_service

    credentials = load_google_credentials([DOCS_SCOPE])
    return GoogleDocsSnapshot(build_docs_service(credentials), args.doc_id)


def build_keep(args):
    backend = args.keep_backend
    if backend == "unofficial":
        from watchlist_enricher.keep.unofficial import UnofficialKeep

        return UnofficialKeep(
            os.environ.get("KEEP_USERNAME") or None,
            os.environ.get("KEEP_MASTER_TOKEN") or None,
            device_id=os.environ.get("KEEP_DEVICE_ID") or None,
        )
    if backend not in {"auto", "official"}:
        raise ConfigError(f"KEEP_BACKEND no reconocido: {backend}")
    from watchlist_enricher.google_auth import KEEP_SCOPE, load_google_credentials
    from watchlist_enricher.keep.official import OfficialKeep, build_service

    credentials = load_google_credentials([KEEP_SCOPE])
    return OfficialKeep(build_service(credentials))


def build_catalog(args):
    if args.swv_backend == "browser":
        raise ConfigError(
            "El backend de navegador no está en esta v1. "
            "Usa el cliente HTTP (STREAMWITHVPN_BACKEND=live) o --fixtures. "
            "Ver docs/limitaciones.md: no se salta el control de Vercel ni se llama a /api/."
        )
    if args.fixtures or args.swv_backend == "fixtures":
        if not args.fixtures:
            raise ConfigError("STREAMWITHVPN_BACKEND=fixtures necesita --fixtures o STREAMWITHVPN_FIXTURES")
        return FixtureCatalog(Path(args.fixtures))
    timeout = float(os.environ.get("STREAMWITHVPN_TIMEOUT", "20"))
    return HttpCatalog(timeout=timeout)


def build_resolver(args):
    if args.tmdb_fixtures:
        return FixtureResolver(Path(args.tmdb_fixtures))
    api_key = os.environ.get("TMDB_API_KEY", "").strip()
    if api_key:
        return TmdbClient(api_key=api_key)
    print(
        "Aviso: no hay TMDB_API_KEY ni --tmdb-fixtures. "
        "Se buscará cada título tal como está escrito, sin corregir erratas ni traducir.",
        file=sys.stderr,
    )
    return NullResolver()


def render_report(report) -> str:
    lines: list[str] = []
    if getattr(report, "implied_dry_run", False):
        lines.append(
            "Modo local sin --apply-local: no se escribe la nota ni el snapshot. "
            "Equivale a --dry-run. Añade --apply-local para guardar los ficheros."
        )
    if report.changes:
        lines.append(f"Títulos nuevos: {len(report.changes)}")
        for change in report.changes:
            kind = "coincidencia exacta" if change.exact else "coincidencia aproximada"
            year = "" if change.matched_year is None else f" ({change.matched_year})"
            lines.append(
                f"  - {change.before} → {change.after}  "
                f"[{kind}: {change.matched_title}{year}]"
            )
    else:
        lines.append("No hay títulos nuevos.")
    if report.failures:
        lines.append(f"Fallos: {len(report.failures)}")
        for failure in report.failures:
            lines.append(f"  - {failure.line}: {failure.message}")
        lines.append("Las líneas fallidas se dejan como están y se reintentan en la próxima ejecución.")
    lines.append("----- nota -----")
    lines.append(report.new_text)
    lines.append("----- fin -----")
    if report.dry_run:
        lines.append("Simulación: no se ha creado ni borrado ninguna nota de Keep.")
        if report.snapshot_updated:
            lines.append("Snapshot actualizado (solo el documento o el fichero).")
    elif report.new_note_id:
        lines.append(f"Nota nueva creada: {report.new_note_id}")
        lines.append(f"Nota anterior borrada: {report.old_note_id}")
        lines.append(
            "Recrear la nota borra metadatos de Keep: color, fijado, etiquetas, "
            "colaboradores, enlace compartido y recordatorios."
        )
        lines.append(
            "El id cambia en cada ejecución. Si usas KEEP_NOTE_ID, actualízalo. "
            "Con KEEP_NOTE_TITLE (y un título único) la siguiente pasada encuentra la nota nueva."
        )
    elif report.keep_written:
        lines.append("Nota local actualizada.")
    elif report.unchanged:
        lines.append("La nota no cambia, así que no se recrea.")
    if report.snapshot_updated and not report.dry_run:
        lines.append("Snapshot actualizado.")
    return "\n".join(lines)
