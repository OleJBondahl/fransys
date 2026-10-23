"""Field case: the system write's lists fill a nested unit's boundary pin's outside end (S3).

The engineering shape: a box unit nests an inner unit whose boundary strip pin `X1:1` is wired
(inside the box) to the box's own boundary strip pin `X9:1`; a top-level cable core runs from the
box's `X9:1` to a motor `M9`. The pin therefore has something outside the inner unit.

The rule (SYSTEM-CONTEXT S3, spec 2026-10-15): with `unit=None` every list fills the outside end of
that boundary pin; in the inner unit's own write the outside end is empty, because a unit knows
only below (decision model-0090). Measured on main 2c9f70d34 the lists already did, since the
system write passes no list context (`pipeline._list_context`); these tests guard it. The PDF list
pages are a different path (`fransys_pdf._lists`), not covered here.

The unit-owned cable (decision model-0191): a second unit holds cable `W1` between two relays, so
its own `cables.csv` lists `W1` and the system `cables.csv` lists only the top-level `W9`.
"""

import csv
import io
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

_TB = "DEMO-TB-2.5"
_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-10-16"}


class _Io(NamedTuple):
    X1: Any


@fr.unit("demo-edge-inner", text="1", by="AB", **_REL)
def _inner(d: Any) -> _Io:
    x1 = d.terminal_strip("X1", _TB, 1, interface=True)
    d.detail.wire(x1[1], d.device("M1", "DEMO-MOTOR-4KW")["U"], wire=(BK, 2.5))
    return _Io(x1)


@fr.unit("demo-edge-box", text="1", by="AB", **_REL)
def _box(d: Any) -> _Io:
    inner = d.add(_inner, "U1")
    x9 = d.terminal_strip("X9", _TB, 1, interface=True)
    d.detail.wire(inner.X1[1], x9[1].inner, wire=(BK, 2.5))
    return _Io(x9)


class _Open(NamedTuple):
    pass


@fr.unit("demo-edge-cab", text="1", by="AB", **_REL)
def _cab(d: Any) -> _Open:
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    k2 = d.device("K2", "DEMO-RLY-2CO-24")
    cable = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, k1.coil["A1"], k2.coil["A1"])
    return _Open()


class _Written(NamedTuple):
    system: Path
    unit: Path


def _rows(folder: Path, pattern: str) -> list[dict[str, str]]:
    (path,) = sorted((folder / "data").glob(pattern))
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory) -> _Written:
    root = tmp_path_factory.mktemp("edge")
    d = fr.design("demo_parts")
    box = d.add(_box, "C1", place=None)
    d.cable("W1", "DEMO-CBL-4G1.5").core(1, box.X1[1].outer, d.device("M9", "DEMO-MOTOR-4KW")["U"])
    (root / "inner.md").write_text("# inner\n", encoding="utf-8")
    inner = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-edge-inner", cover=root / "inner.md"
    )
    result = fr.build(d, inner)
    assert [f.code for f in result.findings if f.severity.name == "ERROR"] == []
    fr.write(result, root / "all", intermediates=root / "im")
    fr.write(result, root / "inner", unit="demo-edge-inner", intermediates=root / "im2")
    return _Written(root / "all", root / "inner")


def test_the_wire_list_fills_the_boundary_row(written: _Written) -> None:
    """Acceptance 4: the system wire list names the strip the boundary pin is wired to."""
    rows = _rows(written.system, "wires.csv")
    assert [(r["from"], r["to"]) for r in rows if r["from"] == "-C1-U1-X1:1" and r["to"]] == [
        ("-C1-U1-X1:1", "-C1-U1-M1:U"),
        ("-C1-U1-X1:1", "-C1-X9:1"),
    ]


def test_the_units_wire_list_has_no_outside_row(written: _Written) -> None:
    rows = _rows(written.unit, "*-wires.csv")
    assert [(r["from"], r["to"]) for r in rows] == [("-X1:1", "-M1:U")]


def test_the_terminal_list_fills_the_outside_side(written: _Written) -> None:
    (row,) = _rows(written.system, "terminals-C1-U1-X1.csv")
    assert (row["side_a"], row["side_b"]) == ("-C1-U1-M1:U", "-C1-X9:1")


def test_the_units_terminal_list_prints_the_outside_side_empty(written: _Written) -> None:
    (row,) = _rows(written.unit, "*-terminals-X1.csv")
    assert (row["side_a"], row["side_b"]) == ("-M1:U", "")


def test_the_parent_strip_list_reaches_the_far_pin(written: _Written) -> None:
    """The strip above the boundary pin prints both its sides: the pin and the motor beyond."""
    (row,) = _rows(written.system, "terminals-C1-X9.csv")
    assert (row["side_a"], row["side_b"]) == ("-C1-U1-X1:1", "-M9:U")


def test_the_cable_and_core_lists_fill_both_ends(written: _Written) -> None:
    (cable,) = _rows(written.system, "cables.csv")
    assert (cable["from_label"], cable["to_label"]) == ("-C1-X9", "-M9")
    (core,) = _rows(written.system, "cores.csv")
    assert (core["end_a"], core["end_b"]) == ("-C1-X9:1", "-M9:U")


def test_the_units_own_cable_and_core_lists_name_nothing_outside(written: _Written) -> None:
    assert _rows(written.unit, "*-cables.csv") == []
    assert _rows(written.unit, "*-cores.csv") == []


@pytest.fixture(scope="module")
def written_unit_cable(tmp_path_factory: pytest.TempPathFactory) -> _Written:
    root = tmp_path_factory.mktemp("unit-cable")
    d = fr.design("demo_parts")
    d.add(_cab, "C2", place=None)
    k9 = d.device("K9", "DEMO-RLY-2CO-24")
    d.cable("W9", "DEMO-CBL-4G1.5").core(1, k9.coil["A1"], d.device("M9", "DEMO-MOTOR-4KW")["U"])
    (root / "cab.md").write_text("# cab\n", encoding="utf-8")
    cab = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-edge-cab", cover=root / "cab.md")
    result = fr.build(d, cab)
    assert [f.code for f in result.findings if f.severity.name == "ERROR"] == []
    fr.write(result, root / "all", intermediates=root / "im")
    fr.write(result, root / "unit", unit="demo-edge-cab", intermediates=root / "im2")
    return _Written(root / "all", root / "unit")


def test_a_unit_owned_cable_is_in_its_units_cables_csv_not_the_system_list(
    written_unit_cable: _Written,
) -> None:
    """Decision model-0191: a cable inside a unit is in that unit's `cables.csv`, not in the system
    list, which holds the top-level cables only (the top-level `W9` is the system row)."""
    assert [r["designation"] for r in _rows(written_unit_cable.unit, "*-cables.csv")] == ["-W1"]
    assert [r["designation"] for r in _rows(written_unit_cable.system, "cables.csv")] == ["-W9"]
