"""CSV and XML exports sit in `<out_dir>/data/`; the top level keeps PDFs, HTML and `changes.md`.

Decision 0197 (amends 0033): `write` and `release` place them, a rewrite cleans `data/` and the old
flat files, and `verify` reads each release's own manifest, so a release stored flat still verifies.
"""

import json
import shutil
import sys
from pathlib import Path

import fransys as fr

sys.path.insert(0, str(Path(__file__).parent))
from release_folders_fixture import build_board, release_board

_DATA_SUFFIXES = {".csv", ".xml"}


def _flat_data_files(folder):
    return sorted(p.name for p in folder.iterdir() if p.suffix in _DATA_SUFFIXES)


def test_write_puts_every_csv_in_data_and_none_at_the_top(tmp_path):
    result, scope = build_board()
    written = fr.write(result, tmp_path, unit=scope)
    in_data = [p for p in written if p.suffix in _DATA_SUFFIXES]
    assert in_data
    assert {p.parent for p in in_data} == {tmp_path / "data"}
    assert _flat_data_files(tmp_path) == []


def test_release_puts_every_csv_including_changes_in_data(tmp_path):
    release_board(tmp_path)
    second = release_board(
        tmp_path, revision=2, colour="RD", history=[(1, 1, "2026-09-26"), (1, 2, "2026-09-27")]
    )
    assert _flat_data_files(second) == []
    assert (second / "data" / "changes.csv").is_file()
    assert (second / "changes.md").is_file()
    assert not (second / "changes.csv").exists()
    manifest = json.loads((second / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    paths = {entry["path"] for entry in manifest["files"]}
    assert "data/changes.csv" in paths
    assert not [p for p in paths if "/" not in p and p.endswith(tuple(_DATA_SUFFIXES))]


def test_a_rewrite_over_a_flat_out_folder_leaves_no_flat_csv(tmp_path):
    result, scope = build_board()
    (tmp_path / "bom.csv").write_text("stale", encoding="utf-8")
    (tmp_path / "wb-board-v1.1-bom.csv").write_text("stale", encoding="utf-8")
    (tmp_path / "wago-R1.xml").write_text("stale", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "wb-board-v0.9-bom.csv").write_text("stale", encoding="utf-8")
    fr.write(result, tmp_path, unit=scope)
    assert _flat_data_files(tmp_path) == []
    assert not (tmp_path / "data" / "wb-board-v0.9-bom.csv").exists()
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "keep"


def _flatten(folder):
    """Rewrite a stored release as releases were stored before `data/`: files on top."""
    manifest_path = folder / "baseline" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["path"].startswith("data/"):
            entry["path"] = entry["path"].removeprefix("data/")
    for path in (folder / "data").iterdir():
        shutil.move(path, folder / path.name)
    (folder / "data").rmdir()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_a_release_stored_flat_still_verifies_clean(tmp_path):
    folder = release_board(tmp_path)
    result, _scope = build_board()
    assert fr.verify(result, tmp_path) == ()
    _flatten(folder)
    assert _flat_data_files(folder)
    assert fr.verify(result, tmp_path) == ()
