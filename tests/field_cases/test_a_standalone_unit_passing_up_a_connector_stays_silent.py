"""Field case: a unit built alone, whose passed-up connector an enclosing standalone unit offers as its own, stays silent.
The bug: the assembly's plug is outside the board's subtree, so the passed-up X1 fired BOUNDARY_UNCONNECTED and the build wrote nothing.
Fixed by model-0184, the check skips a nested unit's boundary function that a standalone enclosing unit offers as its own."""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BK


class _Board(NamedTuple):
    X1: fr.Device
    X2: fr.Device


class _Up(NamedTuple):
    X1: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Board:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x1 = u.device("X1", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    x2 = u.device("X2", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    k1 = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.series(x1[1], k1["1"], wire=(BK, 0.5))
    u.series(x2[1], k1["2"], wire=(BK, 0.5))
    return _Board(x1, x2)


@fr.unit("demo-asm", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _asm(u: Any) -> _Up:
    board = u.add(_board, "U1")
    lamp = u.device("P1", "DEMO-LAMP-24")
    w1 = u.cable("W1", "DEMO-CBL-4G1.5")
    w1.core(1, board.X2[1], lamp["1"])
    w1.core(2, board.X2[2], lamp["2"])
    return _Up(board.X1)


@fr.unit("demo-ship", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _ship(u: Any) -> _Open:
    u.add(_asm, "A1")
    u.device("K9", "DEMO-LAMP-24")  # the parent's own item: the assembly is no longer alone
    return _Open()


def _errors(result: fr.BuildResult) -> list[tuple[str, str]]:
    return [(f.code, f.message) for f in result.findings if f.severity.name == "ERROR"]


def test_the_assembly_built_alone_has_no_boundary_unconnected() -> None:
    d = fr.design("demo_parts")
    d.add(_asm, "A1", place=None)
    result = fr.build(d)
    assert _errors(result) == []
    out = Path(tempfile.mkdtemp())
    fr.write(result, out)
    assert any(out.rglob("*"))


def test_the_same_assembly_inside_a_parent_that_leaves_x1_open_still_errors() -> None:
    d = fr.design("demo_parts")
    d.add(_ship, "S1", place=None)
    result = fr.build(d)
    expect_codes(result, "BOUNDARY_UNCONNECTED")
    assert any("of " in msg and "S1/A1" not in msg for code, msg in _errors(result) if code == "BOUNDARY_UNCONNECTED")
