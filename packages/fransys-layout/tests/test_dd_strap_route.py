"""A wire that turns on another port's first step must not seal that port.

The K1/K2 straps of `test_dd_chains.py::test_the_straps_of_a_function_that_is_a_side_element_
nowhere_are_drawn`, with two contactors and no group tags, so the lanes are narrow and K2 stands
right beside K1 (a lane that carries a coil image is wide, and the earlier test passes only
because K2 then stands clear of K1). K1:1, K2:1 and XA:1 share a net. The strap K1:1 - K2:1 and
the wire XA:1 - K1:1 are both between neighbouring cells (C3), so no star is made and the router
draws the strap. XA:3 stands over K2's pole 1 but feeds its pole 2, so its wire turns on the one
cell in front of K2:1. Routed before the strap, it sealed that port: `ROUTE_FAILED` and
`CONNECTION_NOT_DRAWN`. The router now keeps every port's first step for that port's net and lets
a foreign wire only cross it (`stages/grid_path.py`, `reserve_exits`).

The second test is the reviewer's mixed chain (`test_dd_turned_poles.py`): the same seal on a
two-port net, where D9's markers never apply.
"""

from typing import Any

from dd_chain_fixtures import MCB, TERMINAL, build, design, pin_at, placed, wires_ending_at

K1, K2 = ("-K1", "make-contact", 3), ("-K2", "make-contact", 3)
CTR = "DEMO-CTR-3P-24"


def _errors(result: Any) -> list[str]:
    """The codes of the two errors a port left with no wire and no marker gives."""
    return [f.code for f in result.findings if f.code in {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"}]


def test_a_strap_between_neighbouring_cells_is_drawn_when_a_wire_turns_before_its_port() -> None:
    """K1:1 - K2:1 draws, and each of its ports shows a route or a marker."""
    # UNDO: stages/route.py route, start `along` empty (drop the `reserve_exits` seed)
    parts, d = design()
    c = d.location("C1", "Cabinet")
    strip = d.strip("XA", at=c)
    t1, t2, t3, t4 = (strip.terminal(TERMINAL) for _ in range(4))
    k1, k2 = (d.item(CTR, tag=tag, at=c).fn("main") for tag in ("K1", "K2"))
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(k1["1"], k2["1"])
    wire(k1["2"], k2["2"])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, k2["3"])
    wire(k2["4"], t4.inner)
    result = build(parts, d)
    model = result.model
    one, two = placed(model, *K1), placed(model, *K2)
    # the fault stays reproduced: K2 beside K1, nothing between them
    assert (one.page, one.y) == (two.page, two.y)
    assert one.x < two.x
    assert not [s for s in one.drawing.symbols if one.x < s.x < two.x]
    assert _errors(result) == []
    for p in (one, two):
        top = pin_at(p, "1.in")
        assert wires_ending_at(p.drawing, top) or [m for m in p.drawing.markers if m.x == top[0]]
    assert [
        w for w in one.drawing.wires if {pin_at(one, "1.in"), pin_at(two, "1.in")} <= set(w.points)
    ], "no strap between K1:1 and K2:1"


def test_a_neighbours_straight_run_no_longer_crosses_a_ports_own_first_step() -> None:
    """layout-0088 (amends this file's own layout-0064): a foreign net could still cross a
    port's reserved first step straight through, so a long straight run left no clean turn
    near it for that port's own edge afterward (found by a consumer; the minimal case is
    `tests/field_cases/test_changeover_throws_to_two_strips.py`, two adjacent poles of a
    4-pole changeover, each wired to its own terminal of a field strip, inside a `Unit`). The
    cell is now a hard obstacle for every net but the one that reserved it, so both poles draw.
    """
    # UNDO: stages/route.py _draw, drop `foreign_exits` from `obstacles`
    parts, d = design()
    scope = d.scope("unit").unit("unit", revision=1, interface="1")
    scope.revision(1, date="2026-09-26", text="First issue", created="XX")
    c = scope.location("CAB", "Cabinet")
    field = scope.location("FIELD", "Field strips")
    make = scope.strip("X01", at=field)
    brk = scope.strip("X02", at=field)
    relay = scope.item("DEMO-RLY-4CO-24", tag="K1", at=c)
    wire = scope.wiring(colour="BU", gauge="0.75")
    for pole in (3, 4):
        make_t = make.terminal(TERMINAL, f"RUN{pole}")
        brk_t = brk.terminal(TERMINAL, f"RUN{pole}")
        fn = relay.fn(f"co_{pole}")
        wire(brk_t.inner, fn[f"{pole}2"])
        wire(make_t.inner, fn[f"{pole}4"])
    result = build(parts, d)
    assert _errors(result) == []


def test_a_wire_round_a_symbol_does_not_seal_the_exit_of_another_port() -> None:
    """Q1:2 - K1:4 draws though XA:4 - K1:3 would go round K1 past Q1:2's first step.

    XA:4 - K1:3 turns back on K1's own device, so it is a turned reference pair (layout-0090): a
    reference at XA:4 and a branch at K1:3, no wire to seal anything.
    """
    # UNDO: stages/route.py route, start `along` empty (drop the `reserve_exits` seed)
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    t1, t2, t3, t4 = (strip.terminal(TERMINAL, group=g) for _ in range(4))
    q1 = d.item(MCB, tag="Q1", at=c, group=g)
    k1 = d.item(CTR, tag="K1", at=c, group=g).fn("main")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, q1["1"])
    wire(q1["2"], k1["4"])
    wire(k1["3"], t4.inner)
    result = build(parts, d)
    assert _errors(result) == []
    q1 = placed(result.model, "-Q1", "circuit-breaker")
    k1 = placed(result.model, *K1)
    assert [
        w
        for w in q1.drawing.wires
        if q1.x in {x for x, _ in w.points} and k1.x in {x for x, _ in w.points}
    ], "Q1:2 - K1:4 is not drawn"
    # a reference at XA:4 and a branch at K1:3 (the marker's star kind is not on the Drawing):
    # two markers, one standing over K1's lane
    markers = q1.drawing.markers
    assert len(markers) == 2
    assert sum(m.x == k1.x for m in markers) == 1
