"""G4: a parent wired straight to a nested unit's connector is drawn, and a boundary pin is open.

`lint_chains` reads the drawn boundary functions of every unit as open ends (units spec U2).
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.units import boundary_edge_set
from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN, LONE_CELL
from fransys_layout.stages.exempt import open_ends
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Boundary pins",
    "number": "P-1006",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _keys(model, handles) -> set[tuple[str, ...]]:
    """The authoring key of each function a set of drawn functions stands for."""
    found = set()
    for handle in handles:
        function = ports(model)[handle].function if handle.kind == "port" else handle
        found.add(functions(model)[function].key[:-2])
    return found


def test_the_boundary_pins_hold_the_outer_and_the_nested_boundary_function_and_no_other() -> None:
    """`open_ends` is the set `lint_chains` reads as open ends: X1 and J1, not the lamp H1.

    The lamp is a drawn function of the model too, so the set is not just everything.

    # UNDO: stages/exempt.py, `open_ends` returns `frozenset()`
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    cab = d.scope("cab", at=d.location("C1", "Cabinet")).unit(
        "demo-pump-cabinet", revision=2, interface="1"
    )
    cab.revision(2, date="2026-01-01", text="First release", created="XX")
    board = cab.scope("brd").unit("demo-io-board", revision=1, interface="1")
    board.revision(1, date="2026-01-01", text="First release", created="XX")
    at_c1 = cab.location("C1", "Cab")
    net = cab.group("NET", "Net")
    cab.boundary(cab.item("DEMO-CONN-2P", tag="X1", at=at_c1, group=net))
    board.boundary(board.item("DEMO-CONN-2P", tag="J1", at=at_c1, group=net))
    cab.item("DEMO-LAMP-24", tag="H1", at=at_c1, group=net)
    model = fr.build(parts, d.draft(), system_document()).model
    inputs = read_inputs(model)
    drawn = _keys(model, {spec.function for spec in inputs.functions})
    assert ("cab", "H1") in drawn
    edges = open_ends(inputs.functions, boundary_edge_set(model))
    assert _keys(model, edges) == {("cab", "X1"), ("cab", "brd", "J1")}


def test_a_parent_wired_straight_to_a_nested_connector_is_drawn_and_x1_is_open() -> None:
    """A real build: the cabinet's lamp is wired to the board's connector `J1`.

    Since layout-0080 the parent's set draws that wire at the black box's pin, so there is no
    `CONNECTION_NOT_DRAWN`. The cabinet's own unwired boundary connector `X1` is open, so no
    `LONE_CELL`.

    # UNDO: engines/schematic/engine.py, pass `open_ends=frozenset()` to `_lint_findings`
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    cab = d.scope("cab", at=d.location("C1", "Cabinet")).unit(
        "demo-pump-cabinet", revision=2, interface="1"
    )
    cab.revision(2, date="2026-01-01", text="First release", created="XX")
    board = cab.scope("brd").unit("demo-io-board", revision=1, interface="1")
    board.revision(1, date="2026-01-01", text="First release", created="XX")
    at_c1 = cab.location("C1", "Cab")
    net = cab.group("NET", "Net")
    cab.boundary(cab.item("DEMO-CONN-2P", tag="X1", at=at_c1, group=net))
    j1 = board.item("DEMO-CONN-2P", tag="J1", at=at_c1, group=net)
    board.boundary(j1)
    lamp = cab.item("DEMO-LAMP-24", tag="H1", at=at_c1, group=net)
    wire = cab.wiring(colour="BU", gauge="0.75")
    wire(lamp["1"], j1["1"])
    wire(lamp["2"], j1["2"])
    found = fr.build(parts, d.draft(), system_document()).findings
    assert not [one for one in found if one.code == CONNECTION_NOT_DRAWN]
    assert not [one for one in found if one.code == LONE_CELL]
