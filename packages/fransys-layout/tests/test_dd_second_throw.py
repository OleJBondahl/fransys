"""Step 5 Part 5 (layout-0090, S13): D1's second throw stands under its own port, in its lane.

The changeover fixture of `test_dd_strap_route.py::test_a_neighbours_straight_run_no_longer_
crosses_a_ports_own_first_step` (two adjacent poles of a 4-pole changeover inside a `Unit`,
each throw wired to its own terminal of a different field strip): `chains.py`'s `_stack_
attachments` (S13, decision layout-0090) puts the break throw's terminal in row 1, glued under
the pole as today, and the make throw's terminal -- the second throw -- in row 2, under the
same pole, in the pole's own lane, on a straight vertical wire, with no reference at either
end. That neighbour test only proves the wire routes clean (no `ROUTE_FAILED`/
`CONNECTION_NOT_DRAWN`); it says nothing about where the second throw's terminal actually
lands (the designer's gap, 2026-09-26 evening amendment), which is what this test asserts
directly.
"""

from typing import TYPE_CHECKING, Any

from dd_chain_fixtures import TERMINAL, build, design

from fransys_model.layout import LinkMarker, Route, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_CHANGEOVER = "DEMO-CO-4P-24"


def _built() -> Model:
    """Poles 3 and 4 of one changeover, inside a `Unit`: each throw to its own strip terminal."""
    parts, d = design()
    scope = d.scope("unit").unit("unit", revision=1, interface="1")
    scope.revision(1, date="2026-09-26", text="First issue", created="XX")
    c = scope.location("CAB", "Cabinet")
    field = scope.location("FIELD", "Field strips")
    make_strip, brk_strip = scope.strip("X01", at=field), scope.strip("X02", at=field)
    relay = scope.item(_CHANGEOVER, tag="K1", at=c)
    wire = scope.wiring(colour="BU", gauge="0.75")
    for pole in (3, 4):
        make_t = make_strip.terminal(TERMINAL, f"RUN{pole}")
        brk_t = brk_strip.terminal(TERMINAL, f"RUN{pole}")
        fn = relay.fn(f"co_{pole}")
        wire(brk_t.inner, fn[f"{pole}2"])
        wire(make_t.inner, fn[f"{pole}4"])
    return build(parts, d).model


def _placement(model: Model, *needles: str) -> SymbolPlacement:
    """The one placement whose function key contains every needle."""
    found = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if all(needle in functions(model)[p.function].key for needle in needles)
    ]
    assert len(found) == 1, f"{needles}: {len(found)} placements"
    return found[0]


def _port_id(model: Model, function: Any, name: str) -> Any:
    """The id of `function`'s port named `name`."""
    found = [p.id for p in ports(model).values() if p.function == function and p.name == name]
    assert len(found) == 1, f"{function} {name}: {len(found)} ports"
    return found[0]


def _route_on(model: Model, port: Any) -> Route:
    """The one route with `port` as one of its ends."""
    found = [r for r in layout_of(model, Route).values() if port in (r.a, r.b)]
    assert len(found) == 1, f"{port}: {len(found)} routes"
    return found[0]


def _markers_on(model: Model, port: Any) -> list[LinkMarker]:
    return [m for m in layout_of(model, LinkMarker).values() if m.port == port]


def test_each_second_throw_stands_under_its_own_pole_in_its_own_lane() -> None:
    """S13 (layout-0090): row 2, in its throw's own lane, on a straight wire, no reference."""
    model = _built()
    row2_x = {}
    for pole in (3, 4):
        co = _placement(model, "K1", f"co_{pole}")
        row1 = _placement(model, "X02", f"RUN{pole}")  # break throw, row 1: unchanged today
        row2 = _placement(model, "X01", f"RUN{pole}")  # make throw, row 2: D1's second throw
        assert co.page == row1.page == row2.page
        # row 2 stands further below the pole than row 1, both below it, under the pole
        assert co.y < row1.y < row2.y
        # under its own throw: the make port's lane is exactly the pole's own x
        assert row2.x == co.x
        make_port = _port_id(model, co.function, f"{pole}4")
        route = _route_on(model, make_port)
        assert route.points, "no wire drawn"
        assert {point.x for point in route.points} == {row2.x}, "not a straight vertical wire"
        other_end = next(p for p in (route.a, route.b) if p != make_port)
        assert not _markers_on(model, make_port), "a reference at the pole's end"
        assert not _markers_on(model, other_end), "a reference at the terminal's end"
        row2_x[pole] = row2.x
    assert row2_x[3] != row2_x[4], "each pole's second throw should stand in its own lane"
