"""Field case: an order hint naming a group whose devices another group's column took.

Engineering shape: one unit, group A (a 2-terminal strip and two fuses) and group B (a series
string of four cells). One current loop runs strip:1 - fuse 1 - the string - fuse 2 - strip:2.
The layout puts the loop's column in B, so A holds no column and `d.layout.order(A, B)` names a
group with no column. Only a build with documents reaches the check.

The bug: the AuthorError named only group A. It now names group B (whose column took A's
devices), the loop, and the fix `d.layout.chain(<strip point>, <fuse function>)` over their real
designations, which keeps them in A.

Fixing decision: layout-0195.
"""

from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

if TYPE_CHECKING:
    from pathlib import Path

WIRE = ("BK", 2.5)


class Io(NamedTuple):
    X1: fr.TerminalStrip


def _make(*, chained: bool):
    @fr.unit(
        "loop",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AB",
        title="Loop",
        number="L-1",
    )
    def loop(d: fr.Design) -> Io:
        with d.function("A", "Strip and fuses") as a:
            x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
            f1 = d.device("F1", "DEMO-FUSE-DC-160")
            f2 = d.device("F2", "DEMO-FUSE-DC-160")
            d.detail.wire(x1[1], f1.element["1"], wire=WIRE)
            d.detail.wire(x1[2], f2.element["1"], wire=WIRE)
        with d.function("B", "String") as b:
            cells = [d.device(f"G{k}", "DEMO-CELL-3V6") for k in range(1, 5)]
            d.detail.wire(f2.element["2"], cells[0].cell["-"], wire=WIRE)
            for lower, upper in pairwise(cells):
                d.detail.wire(lower.cell["+"], upper.cell["-"], wire=WIRE)
            d.detail.wire(cells[-1].cell["+"], f1.element["2"], wire=WIRE)
        d.layout.order(a, b)
        if chained:
            d.layout.chain(x1[1], f1.element)
            d.layout.chain(x1[2], f2.element)
        return Io(x1)

    return loop


def _build(tmp_path: Path, *, chained: bool) -> None:
    d = fr.design("demo_parts")
    d.add(_make(chained=chained), "U1")
    (tmp_path / "c.md").write_text("# Loop\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "loop", cover=tmp_path / "c.md")
    fr.build(d, document)


def test_the_error_names_the_group_that_took_the_devices_the_loop_and_the_fix(
    tmp_path: Path,
) -> None:
    with pytest.raises(fr.AuthorError) as raised:
        _build(tmp_path, chained=False)
    message = str(raised.value)
    assert "group =A (Strip and fuses) has none" in message
    assert "column of group =B (String)" in message
    assert "the loop =A-U1-X1:1 - =A-U1-F1 - =B-U1-G4" in message
    assert "d.layout.chain(<function of =A-U1-X1:1>, <function of =A-U1-F1>) keeps them" in message
    assert "d.layout.chain(<function of =A-U1-X1:2>, <function of =A-U1-F2>) keeps them" in message


def test_the_two_chain_hints_keep_the_devices_in_group_a(tmp_path: Path) -> None:
    _build(tmp_path, chained=True)
