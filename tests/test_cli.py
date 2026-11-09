from pathlib import Path

from watchlist_enricher.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
NOTE = ROOT / "ejemplos" / "nota.txt"
SNAPSHOT = ROOT / "ejemplos" / "snapshot.txt"


def test_version():
    assert main(["version"]) == 0
    assert main(["--version"]) == 0


def test_missing_note_is_a_config_error():
    assert main(["sync"]) == 2


def test_dry_run_examples_use_fixtures_and_do_not_write(capsys):
    note_before = NOTE.read_text(encoding="utf-8")
    snapshot_before = SNAPSHOT.read_text(encoding="utf-8")
    code = main(
        [
            "sync",
            "--note-file",
            str(NOTE),
            "--snapshot-file",
            str(SNAPSHOT),
            "--fixtures",
            str(FIXTURES / "streamwithvpn" / "catalog.json"),
            "--tmdb-fixtures",
            str(FIXTURES / "tmdb.json"),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0, captured.err
    output = captured.out
    assert "Nuremberg (Netflix, Estados Unidos)" in output
    assert "Parásito (Netflix)" in output
    assert "Synecdoche, New York (Prime Video, Australia)" in output
    assert "Amélie (Netflix, Canadá)" in output
    assert "Nuermberg (Netflix, Estados Unidos)" in output
    assert "⚠️" not in output
    assert "Inception →" not in output
    assert "Simulación" in output
    assert NOTE.read_text(encoding="utf-8") == note_before
    assert SNAPSHOT.read_text(encoding="utf-8") == snapshot_before


def test_unknown_title_fails_that_line_only(tmp_path, capsys):
    note = tmp_path / "nota.txt"
    snapshot = tmp_path / "snapshot.txt"
    note.write_text("Nuremberg\nPelícula inventada\n", encoding="utf-8")
    snapshot.write_text("", encoding="utf-8")
    code = main(
        [
            "sync",
            "--note-file",
            str(note),
            "--snapshot-file",
            str(snapshot),
            "--fixtures",
            str(FIXTURES / "streamwithvpn" / "catalog.json"),
            "--tmdb-fixtures",
            str(FIXTURES / "tmdb.json"),
            "--dry-run",
        ]
    )
    output = capsys.readouterr().out
    assert code == 1
    assert "Nuremberg (Netflix, Estados Unidos)" in output
    assert "Película inventada:" in output
    assert note.read_text(encoding="utf-8").startswith("Nuremberg\n")
