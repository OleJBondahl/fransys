"""A wire that turns on another port's first step must not seal that port.

The K1/K2 straps of `test_dd_chains.py::test_the_straps_of_a_function_that_is_a_side_element_
nowhere_are_drawn`, with two contactors and no group tags, so the lanes are narrow and K2 stands
"""

from typing import Any

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from dd_chain_fixtures import MCB, TERMINAL, build, design, markers_in, pin_at, placed, wires_ending_at

from fransys_model.derive import port_power_kind
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import ports as ports_of

K1, K2 = ("-K1", "make-contact", 3), ("-K2", "make-contact", 3)
CTR = "DEMO-CTR-3P-24"


def _net(wire: Any) -> str:
    """The net id of a drawn wire, without the `f:` a trunk's net id may carry."""
    return str(wire.net.removeprefix("f:"))


def _errors(result: Any) -> list[str]:
    """The codes of the two errors a port left with no wire and no marker gives."""
    return [f.code for f in result.findings if f.code == "CONNECTION_NOT_DRAWN"]


@pytest.mark.rule("BUNDLE")
def test_a_strap_between_neighbouring_cells_is_drawn_when_a_wire_turns_before_its_port() -> None:
    """K1:1, K2:1 and XA:1 draw as one trunk with a drop to each port, a dot at the inner drop
    and none where the trunk ends at its last drop, no marker and no strap (ROUTING, BUNDLE,
    R467, R477; not a power net)."""
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
    result = build(parts, d, prints=c)
    model = result.model
    # not a power net (Q21): POWER-NET would otherwise decide this shape
    assert {port_power_kind(model, p) for p in ports_of(model)} == {PowerKind.NONE}
    one, two = placed(model, *K1), placed(model, *K2)
    # the fault stays reproduced: K2 beside K1, nothing between them
    assert (one.page, one.y) == (two.page, two.y)
    assert one.x < two.x
    assert not [s for s in one.drawing.symbols if one.x < s.x < two.x]
    assert _errors(result) == []
    assert not markers_in(one.drawing)
    ports = {pin_at(one, "1.in"), pin_at(two, "1.in")}
    drops = [w for p in ports for w in wires_ending_at(one.drawing, p)]
    assert drops
    (net,) = {_net(w) for w in drops}
    net_wires = [w for w in one.drawing.wires if _net(w) == net]
    trunks = [w for w in net_wires if w.points[0][1] == w.points[-1][1]]
    assert len(trunks) == 1
    assert not [w for w in net_wires if ports <= set(w.points)], "a strap joins K1:1 and K2:1"
    dots = [s for s in one.drawing.symbols if s.key == "junction-dot" and s.y == trunks[0].points[0][1]]
    assert len(dots) == 1
    assert dots[0].x == min(x for w in net_wires for x, _ in w.points)


def test_a_neighbours_straight_run_no_longer_crosses_a_ports_own_first_step() -> None:
    """layout-0088 (amends this file's own layout-0064): a foreign net could still cross a
    port's reserved first step straight through, so a long straight run left no clean turn
    near it for that port's own edge afterward (found by a consumer; the minimal case is
    `tests/field_cases/test_changeover_throws_to_two_strips.py`, two adjacent poles of a
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
    result = fr.build(parts, d.draft(), cabinet_document(c), cabinet_document("unit"))
    assert _errors(result) == []


def test_a_wire_round_a_symbol_does_not_seal_the_exit_of_another_port() -> None:
    """Q1:2 - K1:4 draws though XA:4 - K1:3 would go round K1 past Q1:2's first step.

    K1:4 is pole 2's lower pin, so the wire stands in pole 2's column, not the symbol's x.
    """
    # UNDO: core/route.py: the router keeps no wire off Q1:2's first step (no wire is drawn)
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
    result = build(parts, d, prints=c)
    assert _errors(result) == []
    q1 = placed(result.model, "-Q1", "circuit-breaker")
    k1 = placed(result.model, *K1)
    top = pin_at(k1, "2.out")
    assert [w for w in wires_ending_at(q1.drawing, top) if q1.x in {x for x, _ in w.points}], "Q1:2 - K1:4 is not drawn"
    # XA:4 - K1:3 is a plain wire at K1's pin 3 and no marker stands in for it. The old engine drew a turned reference
    # pair here (layout-0090, a reference at XA:4 and a branch at K1:3); the core engine of FLIP (2a612cdf3) draws wires.
    assert wires_ending_at(q1.drawing, pin_at(k1, "2.in")), "XA:4 - K1:3 is not drawn"
