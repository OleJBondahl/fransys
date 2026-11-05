"""Field case: a document of two drawing sets, a cabinet and a board inside it, keeps the membership rows of both.
The bug: writing a set removed every membership row, not only its own, so the other sets were lost (designer R522).
Fixed by el-0068, a set replaces its own membership rows and leaves the others'."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BK, BU

from fransys_model.layout import DrawingSet, Membership, layout_of


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
    u.series(x[1], lamp["1"], wire=(BK, 0.5))
    u.series(x[2], lamp["2"], wire=(BU, 0.5))
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
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, board.X1[1], lamp["1"])
    cable.core(2, board.X1[2], lamp["2"])
    return _Open()


@pytest.mark.rule("OVERVIEW-MEMBERSHIP")
def test_every_drawing_set_keeps_its_membership_rows() -> None:
    d = fr.design("demo_parts")
    d.add(_cabinet, "C1", place=None)
    model = fr.build(d, unit_document("demo-cab")).model
    sets = layout_of(model, DrawingSet)
    kept = {m.key[3] for m in layout_of(model, Membership).values()}
    assert len(sets) >= 2
    assert kept == {str(s.number) for s in sets.values()}
