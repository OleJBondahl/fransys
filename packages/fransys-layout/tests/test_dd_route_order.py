"""Wires route in drawn order, never in handle order.

Two identical coil columns on `examples/demo-parts`: a feed terminal, a breaker, a carrier relay
coil, a side relay coil strapped to it (D2), and a zero terminal. The long wire runs from the
breaker's port 2 to the side coil's A1, the join from the carrier's A1 to the side coil's A1. A
conductor's handle is content-hashed from its authoring key, so the order the router draws two
wires in must not depend on it: the same design under another handle order draws the same page.
"""

from typing import TYPE_CHECKING

from _drawn_pages import drawn_pages
from dd_chain_fixtures import MCB, TERMINAL, build, design, placed

if TYPE_CHECKING:
    from fransys_model.kernel import Model

RELAY = "DEMO-RLY-2CO-24"
# (carrier tag, side tag, breaker tag) per column. With these tags the handle of column 1's long
# wire sorts before its join and column 2's long wire sorts after its join (the guard in the first
# test checks it), found by a scratch search over the tags K1 to K6: the base router then draws
# column 1's long wire first, down the side coil's lane, and column 2's second, down the carrier's.
COLUMNS = (("K1", "K2", "Q1"), ("K3", "K4", "Q2"))
# `wire(..., n=12)` renames column 1's long conductor and nothing else: only its handle changes,
# and it then sorts after its join. Found by scratch search over n = 2 to 13.
RENAMED = 12

Point = tuple[int, int]


def _build(rename: int | None = None) -> Model:
    """The two columns, built and laid out; `rename` is the `n=` key of column 1's long wire."""
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    wire = d.wiring(colour="BU", gauge="0.75")
    for column, (carrier_tag, side_tag, breaker_tag) in enumerate(COLUMNS):
        carrier = d.item(RELAY, tag=carrier_tag, at=c, group=g).fn("coil")
        side = d.item(RELAY, tag=side_tag, at=c, group=g).fn("coil")
        wire(carrier["A1"], side["A1"])
        wire(carrier["A2"], side["A2"])
        feed, zero = (strip.terminal(TERMINAL, group=g) for _ in range(2))
        breaker = d.item(MCB, tag=breaker_tag, at=c, group=g)
        wire(feed.outer, breaker["1"])
        wire(breaker["2"], side["A1"], n=rename if column == 0 else None)
        wire(side["A2"], zero.inner)
    return build(parts, d).model


def _wires(model: Model) -> list[tuple[Point, ...]]:
    """Every drawn wire's points, read in the lesser direction so a flip is moot, in page order."""
    return [
        min(w.points, w.points[::-1])
        for drawing in drawn_pages(model).values()
        for w in drawing.wires
    ]


def test_the_long_wire_of_a_side_element_net_runs_on_the_carriers_lane() -> None:
    """In both columns the long wire runs down the carrier's lane, drawn the same way.

    The handles of the two columns' wires sort opposite ways, so a handle-ordered router draws
    the long wire first in one column and second in the other, and the two columns differ.
    """
    # UNDO: stages/_sides.py drawn_order, sort by `(edge.connection, edge.a.port, edge.b.port)`
    model = _build()
    columns = []
    for carrier_tag, side_tag, breaker_tag in COLUMNS:
        carrier = placed(model, f"-{carrier_tag}", "operating-device")
        side = placed(model, f"-{side_tag}", "operating-device")
        breaker = placed(model, f"-{breaker_tag}", "circuit-breaker")
        assert carrier.page == side.page == breaker.page
        lanes = {carrier.x, side.x, breaker.x}
        mine = [
            tuple((x - carrier.x, y - carrier.y) for x, y in w.points)
            for w in carrier.drawing.wires
            if {x for x, _ in w.points} <= set(range(min(lanes), max(lanes) + 1))
        ]
        runs = [
            w for w in carrier.drawing.wires if {x for x, _ in w.points} == {breaker.x, carrier.x}
        ]
        assert runs, "the long wire runs from the breaker's lane to the carrier's, not the side's"
        columns.append(sorted(min(w, w[::-1]) for w in mine))
    assert columns[0] == columns[1]


def test_renaming_a_conductors_authoring_key_leaves_every_route_byte_identical() -> None:
    """A conductor's key feeds only its handle, so renaming one moves no route.

    Column 1's long wire is renamed with `n=`; its handle then sorts after its join, where it
    sorted before, and a handle-ordered router draws the column the other way round.
    """
    # UNDO: stages/_sides.py drawn_order, sort by `(edge.connection, edge.a.port, edge.b.port)`
    before, after = _build(), _build(rename=RENAMED)
    wires = _wires(before)
    assert wires
    assert _wires(after) == wires
