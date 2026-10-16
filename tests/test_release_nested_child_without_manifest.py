"""A nested child release folder keeps its listing but loses its manifest (a bad checkout).

`fr.release` of the parent must not pass silently: it reads the child's `baseline/` and finds
the manifest gone, so it raises `RELEASE_FILE_MISSING` and names the child folder. The fix
routes a child whose manifest is unreadable to `folder_findings`, which reports the missing file.
"""

import shutil
import sys
from pathlib import Path

import fransys as fr
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from release_folders_fixture import build_cabinet


@pytest.fixture(scope="module")
def released(tmp_path_factory):
    """The cabinet with its board at 1.1, both released."""
    into = tmp_path_factory.mktemp("nested_manifest")
    result, _scope = build_cabinet()
    for name in ("wb-board", "wb-cabinet"):
        fr.release(result, into, unit=name)
    return into


def _copy_without_board_manifest(released: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "released"
    shutil.copytree(released, copy)
    (copy / "wb-board" / "1.1" / "baseline" / "manifest.json").unlink()
    return copy


def test_a_nested_child_without_its_manifest_is_named_by_release(released, tmp_path):
    copy = _copy_without_board_manifest(released, tmp_path)
    result, _scope = build_cabinet()
    with pytest.raises(fr.BuildErrors) as exc:
        fr.release(result, copy, unit="wb-cabinet")
    missing = [f for f in exc.value.findings if f.code == "RELEASE_FILE_MISSING"]
    assert missing, "the missing child manifest must raise RELEASE_FILE_MISSING"
    (finding,) = missing
    assert "wb-board 1.1" in finding.message
    assert "baseline/manifest.json" in finding.message


def test_the_same_release_with_the_child_manifest_intact_does_not_raise(released, tmp_path):
    copy = tmp_path / "released"
    shutil.copytree(released, copy)
    result, _scope = build_cabinet()
    fr.release(result, copy, unit="wb-cabinet")
