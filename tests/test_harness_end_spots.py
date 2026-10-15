"""layout-0206: a plug-less line end whose connector stands as a box has a spot on that page.

The shape is the L2 field case's: cable `-W1` from a header to a nested unit's interface `-X7`,
whose pin views are not drawn. `end_spots` returns the interface's box corner, so an arrow box
that names the end prints its page and cell.
"""

from types import SimpleNamespace
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

from fransys_layout.engines.schematic.read.stub_places import end_spots
from fransys_model.derive import harness_line_ends
from fransys_model.vocab.tables import functions, items, ports


class _Io(NamedTuple):
    X7: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.detail.wire(x7[1], lamp["1"], wire=(BK, 0.5))
    u.detail.wire(x7[2], lamp["2"], wire=(BK, 0.5))
    return _Io(x7)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    board = u.add(_board, "U1")
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, board.X7[1], j1[1])
    cable.core(2, board.X7[2], j1[2])
    return _Open()


def test_a_plug_less_end_with_no_placed_pin_has_its_boxs_corner_as_its_spot() -> None:
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    model = fr.build(d).model
    cable = next(i.id for i in items(model).values() if i.tag == "W1")
    end = next(e for e in harness_line_ends(model, cable) if _tag(model, e) == "X7")
    function = ports(model)[end.ports[0]].function
    box: Any = SimpleNamespace(box=SimpleNamespace(x=44, y=160))
    placed: Any = {function: {(1, 2): box}}
    assert end_spots(model, end, placed, {}, frozenset()) == {(1, 2): (44, 160)}
    assert end_spots(model, end, {}, {}, frozenset()) == {}


def _tag(model: Any, end: Any) -> str | None:
    return items(model)[functions(model)[ports(model)[end.ports[0]].function].item].tag
