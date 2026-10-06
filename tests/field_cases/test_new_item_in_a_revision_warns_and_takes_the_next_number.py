"""Field case: a new floating item in a later revision warns and takes the next free number.

The engineering shape: a pump cabinet is released as unit revision 1.1 with floating relays
and floating I/O board instances. Revision 1.2 adds one more relay, or one more board.

The bug: tags floated in development with nothing to hold them after a release, and a new item
could not take a number without a written tag. The unit's container is the test, not the
system: system pins are deferred, so a system-level case would pass without proving anything.

The rule (UT4, FD1): within a version a released number never moves and is never given again.
A new item with no tag takes the next free number and gives the WARNING
`DESIGNATION_NEW_IN_REVISION`, naming its key and its number, where the pins are read and at
`fr.release`. A new item with a written tag gives none. Retagging a released item is
`DESIGNATION_MOVED`, an ERROR.

The decisions that fix it: model-0135 (the warning) and model-0134 (instance numbers in the pins).
"""

import json
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.vocab.tables import items, units

if TYPE_CHECKING:
    from pathlib import Path

_CODE = "DESIGNATION_NEW_IN_REVISION"


class _Io(NamedTuple):
    J1: fr.Device


class _Open(NamedTuple):
    """The cabinet hands nothing back."""


@pytest.fixture(scope="module")
def released(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Revision 1.1 released once: relays `k_a`, `k_b`; boards `m1`, `m2`."""
    into = tmp_path_factory.mktemp("cabinet_releases")
    result = _build(1, relays=("k_a", "k_b"), modules=("m1", "m2"))
    model = result.model
    board = next(  # two instances share the name, so release by one instance's id
        u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-board"
    )
    fr.release(result, into, unit=board)
    fr.release(result, into, unit="demo-cab")
    return into


def _build(
    revision: int,
    *,
    relays: tuple[str, ...],
    modules: tuple[str, ...],
    written: dict[str, str] | None = None,
    releases: Path | None = None,
) -> fr.BuildResult:
    """The cabinet at `revision`: floating relays and boards, except those with a `written` tag."""
    tags = written or {}

    @fr.unit(
        "demo-board",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AB",
        class_code="U",
    )
    def board(u: Any) -> _Io:
        root = u.device("U9", "DEMO-PCB-IO")
        return _Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True, unused=True))

    history = [
        {"revision": r, "date": "2026-01-01", "text": f"revision {r}", "created": "AB"}
        for r in range(1, revision)
    ]

    @fr.unit(
        "demo-cab",
        revision=revision,
        interface_version=1,
        date="2026-02-01",
        text=f"revision {revision}",
        by="AB",
        history=history,
        class_code="U",
    )
    def cab(u: Any) -> _Open:
        for name in relays:
            u.device(tags.get(name), "DEMO-RLY-2CO-24", name=name)
        for name in modules:
            u.add(board, tags.get(name), name=name)
        return _Open()

    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(cab, "U1")
    return fr.build(d, releases=releases)


def _inside(model: fr.Model, unit: Any, cabinet: Any) -> bool:
    """Whether `unit` is the cabinet or one of its direct board instances."""
    return unit == cabinet or (unit is not None and units(model)[unit].parent == cabinet)


def _numbers(result: fr.BuildResult) -> dict[str, str]:
    """Each relay and board by name: the unit's own printed text for it (a board by its `J1`)."""
    model = result.model
    unit = next(
        u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-cab"
    )
    found = {}
    for item in items(model).values():
        if item.key[-1] != "U9" and _inside(model, item.unit, unit):
            name = item.key[-2] if item.key[-1] == "J1" else item.key[-1]
            found[name] = fr.derive.printed_designation(model, item.id, unit=unit)
    return found


def _warnings(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(result) if f.code == _CODE]


def test_a_new_floating_relay_warns_and_takes_the_next_free_number(released: Path) -> None:
    first = _build(1, relays=("k_a", "k_b"), modules=("m1", "m2"))
    assert _warnings(first) == []
    assert _numbers(first) == {"k_a": "-K1", "k_b": "-K2", "m1": "-U1-J1", "m2": "-U2-J1"}
    # revision 1.2 retires `k_b` (K2) and adds `k_c`: K3, never K2 again
    second = _build(2, relays=("k_a", "k_c"), modules=("m1", "m2"), releases=released)
    (warning,) = _warnings(second)
    assert warning.severity is fr.Severity.WARNING
    assert "k_c" in warning.message
    assert "K3" in warning.message
    assert _numbers(second) == {"k_a": "-K1", "k_c": "-K3", "m1": "-U1-J1", "m2": "-U2-J1"}


def test_a_new_floating_board_instance_warns_and_takes_the_next_free_number(released: Path) -> None:
    second = _build(2, relays=("k_a", "k_b"), modules=("m1", "m2", "m3"), releases=released)
    (warning,) = _warnings(second)
    assert "m3" in warning.message
    assert "U3" in warning.message
    assert _numbers(second) == {
        "k_a": "-K1",
        "k_b": "-K2",
        "m1": "-U1-J1",
        "m2": "-U2-J1",
        "m3": "-U3-J1",
    }


def test_a_new_item_with_a_written_tag_gives_no_such_finding(released: Path) -> None:
    second = _build(
        2,
        relays=("k_a", "k_b", "k_n"),
        modules=("m1", "m2"),
        written={"k_n": "K7"},
        releases=released,
    )
    assert _warnings(second) == []
    assert _numbers(second)["k_n"] == "-K7"
    assert _numbers(second)["k_a"] == "-K1"
    # the unit's boards are floating and released: the written relay alone proves the other half
    assert _numbers(second)["m2"] == "-U2-J1"


def test_retagging_a_released_item_is_designation_moved_at_release(released: Path) -> None:
    second = _build(
        2, relays=("k_a", "k_b"), modules=("m1", "m2"), written={"k_a": "K9"}, releases=released
    )
    with pytest.raises(fr.BuildErrors) as raised:
        fr.release(second, released, unit="demo-cab")
    assert "DESIGNATION_MOVED" in {f.code for f in raised.value.findings}


def test_releasing_the_revision_reports_the_warning_in_the_manifest(released: Path) -> None:
    """`fr.release` returns only a path: the warning is read back from `baseline/manifest.json`."""
    second = _build(2, relays=("k_a", "k_b", "k_c"), modules=("m1", "m2"), releases=released)
    target = fr.release(second, released, unit="demo-cab")
    manifest = json.loads((target / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    codes = [w["code"] for w in manifest["warnings"]]
    assert _CODE in codes
