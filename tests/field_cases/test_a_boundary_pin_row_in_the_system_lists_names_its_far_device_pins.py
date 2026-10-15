"""Field case: a boundary pin's row in the system lists names the device pins it finally reaches.

The engineering shape: a container nests a cabinet unit whose breaker pole is its boundary pin, and
a pump unit whose motor hands up its pins. The container wires the breaker pole to a strip
terminal `-X1:1` of its own, and a cable carries `-X1:1` on to the motor (one pin, or four).
The system write (`fr.write(result, out_dir)`, no `unit`) prints every list in full.

The question (spec S3, acceptance 4): do the system lists fill the boundary row's outside end?
They do, by the rule that fits each list. A wire row is one physical conductor, so its outside end
is that conductor's other end, the strip terminal `-X1:1`. The terminal list prints every core's
far device pin, with no cap. A nested unit's own write (`unit=`) prints that end empty.

Rule (model-0205, `derive/far_ends.py`; designer ruling 2026-10-15): the far device pins belong in
the terminal and connector lists, never in a wire row.
"""

import csv
import io
from functools import cache
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import BK

WIRE = (BK, 0.75)
MOTOR_PINS = ("U", "V", "W", "PE")


class _Open(NamedTuple):
    pass


class _Breaker(NamedTuple):
    F1: fr.Device


class _Strip(NamedTuple):
    X1: fr.TerminalStrip


class _Motor(NamedTuple):
    M1: fr.Device


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Breaker:
    return _Breaker(u.device("F1", "DEMO-MCB-2P", interface=("pole_1",)))


@fr.unit("demo-cab-strip", revision=1, interface_version=1, date="2026-01-01", text="a", by="AB")
def _cab_strip(u: Any) -> _Strip:
    f1 = u.device("F1", "DEMO-MCB-2P")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 1, interface=(1,))
    u.detail.wire(f1.pole_1["2"], x1[1].inner, wire=WIRE)
    return _Strip(x1)


@fr.unit("demo-pump", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _pump(u: Any) -> _Motor:
    return _Motor(u.device("M1", "DEMO-MOTOR-4KW", interface=("motor",)))


def _system(pins: tuple[str, ...], *, strip_in_unit: bool) -> fr.BuildResult:
    @fr.unit("demo-sys", revision=1, interface_version=1, date="2026-01-01", text="a", by="AB")
    def _sys(u: Any) -> _Open:
        pump = u.add(_pump, "P")
        cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
        if strip_in_unit:
            outer = u.add(_cab_strip, "N").X1[1].outer
        else:
            x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 1)
            u.detail.wire(u.add(_cab, "N").F1.pole_1["2"], x1[1].inner, wire=WIRE)
            outer = x1[1].outer
        for core, pin in enumerate(pins, 1):
            cable.core(core, outer, pump.M1.motor[pin])
        return _Open()

    d = fr.design("demo_parts")
    d.add(_sys, "S")
    return fr.build(d)


@cache
def _one() -> fr.BuildResult:
    return _system(("U",), strip_in_unit=False)


@cache
def _four() -> fr.BuildResult:
    return _system(MOTOR_PINS, strip_in_unit=False)


def _rows(directory: Path, pattern: str) -> list[dict[str, str]]:
    (path,) = directory.glob(f"data/{pattern}")
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def _boundary_row(rows: list[dict[str, str]], pin: str) -> dict[str, str]:
    """The one row that has the boundary pin at either end."""
    (row,) = (r for r in rows if any(v.endswith(pin) for v in r.values()))
    return row


def _outside_wire_end(row: dict[str, str]) -> str:
    return row["to"] if row["from"].endswith("F1:2") else row["from"]


def test_the_wire_list_boundary_row_ends_at_the_strip_terminal(tmp_path: Path) -> None:
    """A wire row is one conductor: its outside end is the strip terminal it lands on."""
    fr.write(_one(), tmp_path)
    row = _boundary_row(_rows(tmp_path, "wires.csv"), "F1:2")
    assert _outside_wire_end(row) == "-S-X1:1"


def test_four_far_pins_leave_the_wire_row_unchanged(tmp_path: Path) -> None:
    """The cores behind the terminal add no wire row and change no end of the pole's wire."""
    fr.write(_four(), tmp_path)
    rows = _rows(tmp_path, "wires.csv")
    assert _outside_wire_end(_boundary_row(rows, "F1:2")) == "-S-X1:1"
    assert not any("M1:" in v for r in rows for v in r.values())


def test_the_terminal_list_names_all_four_far_pins(tmp_path: Path) -> None:
    """The terminal row already prints every far pin, the set the wire list must match."""
    fr.write(_four(), tmp_path)
    row = _boundary_row(_rows(tmp_path, "terminals-*.csv"), "F1:2")
    assert row["side_a"].endswith("F1:2")
    assert row["side_b"] == "-S-P-M1:PE; -S-P-M1:U; -S-P-M1:V; -S-P-M1:W"


def test_a_unit_write_leaves_the_outside_end_empty(tmp_path: Path) -> None:
    """The nested unit's own write keeps its strip row and prints no outside name."""
    result = _system(MOTOR_PINS, strip_in_unit=True)
    fr.write(result, tmp_path / "system")
    fr.write(result, tmp_path / "unit", unit="demo-cab-strip")
    system_row = _boundary_row(_rows(tmp_path / "system", "terminals-*.csv"), "F1:2")
    assert system_row["side_b"].count("M1:") == len(MOTOR_PINS)
    unit_row = _boundary_row(_rows(tmp_path / "unit", "*terminals-*.csv"), "F1:2")
    assert unit_row["side_b"] == ""
