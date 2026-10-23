"""Field case: a document of two drawing sets keeps the membership rows of both.

The engineering shape: a cabinet unit nests a relay board with a connector and a lamp; the
cabinet wires a cable to the connector. The cabinet and the board are two drawing sets in one
document.

The bug: writing a set removed every membership row the layout writer had stamped, not only the
set's own, so a built release kept the rows of the last set alone and the overview and the page
navigation lost the other sets (designer R522).

The rule: a set replaces its own membership rows and leaves the others' (decision el-0068).
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model.layout import DrawingSet, Membership, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    X1: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit(
    "demo-board",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Relay board",
)
def _board(u: Any) -> Any:
    pcb = u.device("A1", "DEMO-PCB-IO")
    with u.function("F1", "Board circuit"):
        x = u.device("X1", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
        lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.detail.wire(x[1], lamp["1"], wire=(BK, 0.5))
    return _Io(X1=x)


@fr.unit(
    "demo-cab",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Cabinet",
)
def _cabinet(u: Any) -> _Open:
    board = u.add(_board, "U1")
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.cable("W1", "DEMO-CBL-4G1.5", length_m=1).core(1, board.X1[1], lamp["1"])
    return _Open()


@pytest.mark.rule("OVERVIEW-MEMBERSHIP")
def test_every_drawing_set_keeps_its_membership_rows(tmp_path: Path) -> None:
    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cabinet, "C1", place=None)
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover)
    ).model
    sets = layout_of(model, DrawingSet)
    kept = {m.key[3] for m in layout_of(model, Membership).values()}
    assert len(sets) >= 2
    assert kept == {str(s.number) for s in sets.values()}
