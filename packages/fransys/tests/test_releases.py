"""`fr.releases`, the one reader of release folders: order, a missing manifest, a broken one."""

import json

import fransys as fr
import pytest


def _manifest(folder, *, interface="1", nested=(), files=(), text=None) -> None:
    (folder / "baseline").mkdir(parents=True, exist_ok=True)
    data = {
        "listing_digest": "d" * 64,
        "unit": {"interface": interface},
        "nested": [dict(n) for n in nested],
        "files": [{"path": p, "sha256": h} for p, h in files],
    }
    (folder / "baseline" / "manifest.json").write_text(
        json.dumps(data) if text is None else text, encoding="utf-8"
    )


def test_releases_sort_by_name_then_integer_version_and_revision(tmp_path):
    for name, folder in (("b", "1.1"), ("a", "1.10"), ("a", "1.9"), ("a", "2.1")):
        _manifest(tmp_path / name / folder)
    got = [(r.name, r.version, r.revision) for r in fr.releases(tmp_path)]
    assert got == [("a", 1, 9), ("a", 1, 10), ("a", 2, 1), ("b", 1, 1)]


def test_a_release_carries_its_manifest_fields(tmp_path):
    pin = {"name": "board", "version": 1, "revision": 3, "listing_digest": "e" * 64}
    _manifest(tmp_path / "cab" / "1.2", interface="7", nested=[pin], files=[("a.csv", "f" * 64)])
    (release,) = fr.releases(tmp_path)
    assert release.interface == "7"
    assert release.listing_digest == "d" * 64
    assert release.nested == (fr.ReleasePin(**pin),)
    assert release.files == (("a.csv", "f" * 64),)
    assert release.path == tmp_path / "cab" / "1.2"


def test_a_folder_with_no_manifest_is_listed_empty(tmp_path):
    (tmp_path / "cab" / "1.1").mkdir(parents=True)
    (release,) = fr.releases(tmp_path)
    assert (release.interface, release.listing_digest, release.nested, release.files) == (
        "",
        "",
        (),
        (),
    )


def test_names_that_are_not_revisions_and_a_missing_root_are_skipped(tmp_path):
    (tmp_path / "cab" / ".release-x").mkdir(parents=True)
    (tmp_path / "cab" / "1.1.1").mkdir()
    (tmp_path / "cab" / "notes.txt").write_text("x", encoding="utf-8")
    assert fr.releases(tmp_path) == ()
    assert fr.releases(tmp_path / "missing") == ()


@pytest.mark.parametrize(
    "text", ['{"listing_digest": "x", "unit"', "[]", '{"listing_digest": "x", "unit": {}}']
)
def test_a_broken_manifest_raises_value_error_naming_the_path(tmp_path, text):
    _manifest(tmp_path / "cab" / "1.1", text=text)
    with pytest.raises(ValueError, match=r"cab.1\.1.baseline.manifest\.json"):
        fr.releases(tmp_path)


def test_a_malformed_nested_entry_raises_value_error(tmp_path):
    _manifest(tmp_path / "a" / "1.1", nested=[{"name": "x"}])
    with pytest.raises(ValueError, match="nested"):
        fr.releases(tmp_path)


def test_a_malformed_files_entry_raises_value_error(tmp_path):
    _manifest(tmp_path / "a" / "1.1")
    manifest = tmp_path / "a" / "1.1" / "baseline" / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"] = [{"path": "a.csv"}]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="files"):
        fr.releases(tmp_path)
