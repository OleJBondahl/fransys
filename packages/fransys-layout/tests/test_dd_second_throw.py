"""D1's second throw stands under its own port, in its lane.

The changeover fixture of `test_dd_strap_route.py::test_a_neighbours_straight_run_no_longer_
crosses_a_ports_own_first_step` (two adjacent poles of a 4-pole changeover inside a `Unit`,
each throw wired to its own terminal of a different field strip): `chains.py`'s `_stack_
attachments` (decision layout-0090) puts the break throw's terminal in row 1, glued under
the pole as today, and the make throw's terminal -- the second throw -- in row 2, under the
same pole, in the pole's own lane, on a straight vertical wire, with no reference at either
end. That neighbour test only proves the wire routes clean (no `ROUTE_FAILED`/
`CONNECTION_NOT_DRAWN`); it says nothing about where the second throw's terminal actually
lands (the gap, 2026-09-26 evening amendment), which is what this test asserts
directly.
"""

from typing import TYPE_CHECKING

from dd_chain_fixtures import TERMINAL, build, design, placed

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_CHANGEOVER = "DEMO-RLY-4CO-24"


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


def test_each_second_throw_stands_under_its_own_pole_in_its_own_lane() -> None:
    """Row 2, in its throw's own lane, on a straight wire, no reference."""
    model = _built()
    row2_x = {}
    for pole in (3, 4):
        co = placed(model, "-K1", "change-over-contact", marking=f"{pole}1")
        row1 = placed(model, f"-X02:RUN{pole}:1", "terminal")  # break throw, row 1: unchanged today
        row2 = placed(model, f"-X01:RUN{pole}:1", "terminal")  # make throw, row 2: the second throw
        assert co.page == row1.page == row2.page
        # row 2 stands further below the pole than row 1, both below it, under the pole
        assert co.y < row1.y < row2.y
        # under its own throw: the make port's lane is exactly the pole's own x
        assert row2.x == co.x
        wires = [w for w in co.drawing.wires if any(point[0] == row2.x for point in w.points)]
        assert wires, "no wire drawn"
        assert any({point[0] for point in w.points} == {row2.x} for w in wires), (
            "not a straight vertical wire"
        )
        assert not co.drawing.markers, "a reference at either end"
        row2_x[pole] = row2.x
    assert row2_x[3] != row2_x[4], "each pole's second throw should stand in its own lane"
