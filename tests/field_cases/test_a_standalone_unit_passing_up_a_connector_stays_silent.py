"""Field case: a unit built alone that passes up a nested connector stays silent (model-0184).

The engineering shape: a board unit has two interface connectors, `X1` and `X2`. An assembly
unit holds the board, mates a harness plug onto `X2` inside itself, and offers `X1` as its own
interface (author-0032). The guide promises that a unit built alone leaves its interface open and
`BOUNDARY_UNCONNECTED` stays silent.

The bug: the assembly's own plug is not in the board's subtree, so the board was not standalone and
its passed-up `X1` fired `BOUNDARY_UNCONNECTED`; the build was an error and wrote nothing. The rule
(model-0184): the check skips a nested unit's boundary function that a standalone enclosing unit
offers as its own. Inside a larger design that neither connects `X1` nor declares it unused, the
error stays.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
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
    u.wire(x1[1], k1["1"], wire=(BK, 0.5))
    u.wire(x2[1], k1["2"], wire=(BK, 0.5))
    return _Board(x1, x2)


@fr.unit("demo-asm", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _asm(u: Any) -> _Up:
    board = u.add(_board, "U1")
    w1 = u.harness("W1")
    p1 = u.device("P1", "DEMO-HSG-4M", parent=w1, contacts="DEMO-CRIMP-M")
    p2 = u.device("P2", "DEMO-HSG-4M", parent=w1, contacts="DEMO-CRIMP-M")
    u.mate(p1, board.X2)
    u.wire(p1[1], p2[1], wire=(BK, 0.5))
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
    errors = _errors(fr.build(d))
    assert any(
        code == "BOUNDARY_UNCONNECTED" and "of unit S1/A1/U1/unit" in msg for code, msg in errors
    )
