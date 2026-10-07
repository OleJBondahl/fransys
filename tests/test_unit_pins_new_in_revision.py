"""UT4, FD1, FD5, FD6: floating tags hold after release; a new floating one warns.

A cabinet unit holds floating relays and board instances (floating tags need a release
`class_code`, which `_cabinet` gives each release). Revision 1 is released; revision 2 builds
against it (`releases=`) or releases directly.
One cabinet and one board release serve every test: released once, copied per test.
The cabinet is built per call, never shared.
"""

import json
import shutil
lazy from pathlib import Path

import fransys as fr
import fransys_author
import pytest

_CODE = "DESIGNATION_NEW_IN_REVISION"
_DATE = "2026-10-05"


def _cabinet(revision, *, relays=("k_a", "k_b"), boards=("m1", "m2"), written=None, releases=None):
    """The cabinet at `revision`: floating relays and boards, but those named in `written`."""
    tags = written or {}
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    cab = design.scope("cab").unit("pins-cabinet", revision=revision, interface="1", class_code="U")
    cab.revision(revision, date=_DATE, text=f"Revision {revision}", created="OJB")
    for name in relays:
        cab.item("DEMO-RLY-2CO-24", name=name, tag=tags.get(name))
    board = None
    for name in boards:
        board = cab.scope(name).unit(
            "pins-board", revision=1, interface="1", tag=tags.get(name), class_code="U"
        )
        board.revision(1, date=_DATE, text="First", created="OJB")
        board.item("DEMO-PCB-IO", name="pcb")
    return fr.build(parts, design.draft(), releases=releases), cab, board


@pytest.fixture(scope="module")
def _released_once(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Revision 1 released once into a folder no test writes to: relays K1, K2; boards U1, U2."""
    target = tmp_path_factory.mktemp("released")
    result, cab, board = _cabinet(1)
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []
    fr.release(result, target, unit=board)
    fr.release(result, target, unit=cab)
    return target


@pytest.fixture
def released(_released_once: Path, tmp_path: Path) -> Path:
    """A private copy of the revision 1 release, for tests that release revision 2 into it."""
    return shutil.copytree(_released_once, tmp_path / "released")


def _texts(target: Path) -> dict[str, str]:
    """Each pinned relay and board instance by name, its released text."""
    text = (target / "baseline" / "numbering.json").read_text(encoding="utf-8")
    rows = json.loads(text)["items"]
    return {r["key"][-2] if r["key"][-1] == "unit" else r["key"][-1]: r["text"] for r in rows}


def _warnings(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(result) if f.code == _CODE]


def test_revision_one_is_numbered_from_the_class_codes(released: Path) -> None:
    assert _texts(released / "pins-cabinet" / "1.1") == {
        "k_a": "K1",
        "k_b": "K2",
        "m1": "U1",
        "m2": "U2",
    }


def test_a_new_floating_relay_warns_and_takes_the_next_number_after_a_retired_one(
    released: Path,
) -> None:
    result, cab, _ = _cabinet(2, relays=("k_a", "k_c"), releases=released)
    (warning,) = _warnings(result)
    assert warning.severity is fr.Severity.WARNING
    assert "k_c" in warning.message
    assert "K3" in warning.message
    assert _texts(fr.release(result, released, unit=cab)) == {
        "k_a": "K1",
        "k_c": "K3",
        "m1": "U1",
        "m2": "U2",
    }


def test_a_new_floating_instance_warns_and_takes_the_next_number_after_a_retired_one(
    released: Path,
) -> None:
    result, cab, _ = _cabinet(2, boards=("m0", "m2"), releases=released)
    (warning,) = _warnings(result)
    assert "m0" in warning.message
    assert "U3" in warning.message
    assert _texts(fr.release(result, released, unit=cab)) == {
        "k_a": "K1",
        "k_b": "K2",
        "m0": "U3",
        "m2": "U2",
    }


def test_a_new_item_with_a_written_tag_gives_no_warning(released: Path) -> None:
    written = {"k_n": "K7", "m3": "U8"}
    result, _, _ = _cabinet(
        2,
        relays=("k_a", "k_b", "k_n"),
        boards=("m1", "m2", "m3"),
        written=written,
        releases=released,
    )
    assert _warnings(result) == []
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []


@pytest.mark.usefixtures("released")
def test_a_build_with_no_releases_gives_no_warning() -> None:
    result, _, _ = _cabinet(2, relays=("k_a", "k_b", "k_c"))
    assert _warnings(result) == []


def test_the_release_warns_when_the_build_did_not_read_the_pins(released: Path) -> None:
    """Built free, k_c is K2 and `k_b`'s K2 is gone: no move, a new item, and a manifest warning."""
    result, cab, _ = _cabinet(2, relays=("k_a", "k_c"))
    target = fr.release(result, released, unit=cab)
    manifest = json.loads((target / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    (entry,) = [w for w in manifest["warnings"] if w["code"] == _CODE]
    assert "k_c" in entry["message"]


def test_the_release_after_a_pinned_build_lists_the_warning_once(released: Path) -> None:
    result, cab, _ = _cabinet(2, relays=("k_a", "k_b", "k_c"), releases=released)
    target = fr.release(result, released, unit=cab)
    manifest = json.loads((target / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    assert [w["code"] for w in manifest["warnings"]].count(_CODE) == 1


def test_a_floating_number_that_moved_without_the_pins_is_designation_moved(
    released: Path,
) -> None:
    """Built free, dropping `m1`, `m2` becomes U1: the released U2 moved."""
    result, cab, _ = _cabinet(2, boards=("m2",))
    with pytest.raises(fr.BuildErrors) as raised:
        fr.release(result, released, unit=cab)
    (moved,) = [f for f in raised.value.findings if f.code == "DESIGNATION_MOVED"]
    assert "m2" in moved.message


def test_retagging_a_released_item_is_designation_moved(released: Path) -> None:
    result, cab, _ = _cabinet(2, written={"k_a": "K9"}, releases=released)
    with pytest.raises(fr.BuildErrors) as raised:
        fr.release(result, released, unit=cab)
    assert "DESIGNATION_MOVED" in {f.code for f in raised.value.findings}


def test_retagging_a_released_instance_is_designation_moved(released: Path) -> None:
    result, cab, _ = _cabinet(2, written={"m1": "U9"}, releases=released)
    with pytest.raises(fr.BuildErrors) as raised:
        fr.release(result, released, unit=cab)
    (moved,) = [f for f in raised.value.findings if f.code == "DESIGNATION_MOVED"]
    assert "m1" in moved.message
