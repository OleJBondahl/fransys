"""`fr.verify` re-hashes every released file (WORKFLOW-BLOCKS W5, W6; acceptance 1 to 4, 13).

One module fixture releases the board once; each test edits its own copy.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import fransys as fr
import fransys_author
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from release_folders_fixture import build_board, release_board


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    into = tmp_path_factory.mktemp("integrity")
    release_board(into)
    return into, build_board()[0]


@pytest.fixture
def copy(base, tmp_path):
    into, _result = base
    shutil.copytree(into, tmp_path / "r")
    return tmp_path / "r", base[1]


def _folder(into):
    return into / "wb-board" / "1.1"


def _csv(into):
    return min(_folder(into).glob("*-bom.csv"))


def _codes(result, into):
    return [(f.code, f.message) for f in fr.verify(result, into)]


def test_an_untouched_release_gives_no_file_finding(copy):
    into, result = copy
    assert _codes(result, into) == []


def test_a_changed_byte_in_a_released_csv_gives_release_file_changed(copy):
    into, result = copy
    path = _csv(into)
    path.write_bytes(path.read_bytes() + b"x")
    assert _codes(result, into) == [("RELEASE_FILE_CHANGED", f"wb-board 1.1: {path.name}")]


def test_a_deleted_released_file_gives_release_file_missing(copy):
    into, result = copy
    path = _csv(into)
    path.unlink()
    assert _codes(result, into) == [("RELEASE_FILE_MISSING", f"wb-board 1.1: {path.name}")]


def test_a_deleted_manifest_gives_release_file_missing(copy):
    into, result = copy
    (_folder(into) / "baseline" / "manifest.json").unlink()
    assert _codes(result, into) == [
        ("RELEASE_FILE_MISSING", "wb-board 1.1: baseline/manifest.json")
    ]


def test_a_file_added_to_a_release_folder_gives_release_file_changed(copy):
    into, result = copy
    (_folder(into) / "Thumbs.db").write_bytes(b"x")
    assert _codes(result, into) == [
        ("RELEASE_FILE_CHANGED", "wb-board 1.1: Thumbs.db (not in the manifest)")
    ]


def test_crlf_line_ends_in_every_text_file_pass(copy):
    into, result = copy
    for path in _folder(into).rglob("*"):
        if path.suffix in {".csv", ".json", ".md", ".xml"}:
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert _codes(result, into) == []


def _list_a_binary_file(into, data):
    """Add `x.pdf` to the folder and to its manifest, as a release with a document would."""
    manifest = _folder(into) / "baseline" / "manifest.json"
    parsed = json.loads(manifest.read_text(encoding="utf-8"))
    parsed["files"].append({"path": "x.pdf", "sha256": hashlib.sha256(data).hexdigest()})
    manifest.write_text(json.dumps(parsed), encoding="utf-8")
    (_folder(into) / "x.pdf").write_bytes(data)


def test_a_pdf_with_changed_line_ends_still_counts(copy):
    into, result = copy
    _list_a_binary_file(into, b"%PDF\nbody\n")
    assert _codes(result, into) == []
    (_folder(into) / "x.pdf").write_bytes(b"%PDF\r\nbody\r\n")
    assert _codes(result, into) == [("RELEASE_FILE_CHANGED", "wb-board 1.1: x.pdf")]


def test_a_manifest_cut_in_half_is_a_changed_file_for_verify_and_value_error_for_releases(copy):
    """Acceptance 13: the folder is reported, never skipped."""
    into, result = copy
    manifest = _folder(into) / "baseline" / "manifest.json"
    manifest.write_bytes(manifest.read_bytes()[:40])
    assert _codes(result, into) == [
        ("RELEASE_FILE_CHANGED", "wb-board 1.1: baseline/manifest.json")
    ]
    with pytest.raises(ValueError, match=r"manifest\.json"):
        fr.releases(into)


def test_a_release_the_model_no_longer_has_is_still_checked(copy):
    into, _result = copy
    other = fr.build(fr.parts("demo_parts"), fransys_author.Design(fr.parts("demo_parts")).draft())
    path = _csv(into)
    path.write_bytes(b"changed")
    assert _codes(other, into) == [("RELEASE_FILE_CHANGED", f"wb-board 1.1: {path.name}")]


def test_a_folder_with_a_manifest_and_no_listing_is_listed_but_not_a_previous_release(copy):
    """Acceptance 14: `fr.releases` lists it; the previous-release lookup still skips it."""
    into, _result = copy
    (_folder(into) / "baseline" / "listing.json").unlink()
    (release,) = fr.releases(into)
    assert (release.name, release.version, release.revision) == ("wb-board", 1, 1)
    assert release.listing_digest != ""
    next_result, _scope = build_board(revision=2)
    with pytest.raises(FileNotFoundError):
        fr.diff(next_result, into, unit="wb-board")
