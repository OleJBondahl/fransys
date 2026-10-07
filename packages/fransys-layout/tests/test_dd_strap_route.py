"""EF-D part 3: a wire that turns on another port's first step must not seal that port (D9).

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

from typing import TYPE_CHECKING, Any

from dd_chain_fixtures import (
    MCB,
    TERMINAL,
    build,
    design,
    markers_on,
    placed,
    route_between,
    terminal_key,
)

from fransys_layout.geometry import WIRING_GRID, Facing, Point
from fransys_layout.stages.grid_path import reserve_exits
from fransys_layout.stages.space import End
from fransys_model.layout import Route, StarKind, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

K1, K2 = ("K1", "fn", "main"), ("K2", "fn", "main")
Q1 = ("Q1", "fn", "element")
CTR = "DEMO-CTR-3P-24"


def _routes_on(model: Model, key: tuple[str, ...], name: str) -> int:
    """How many routes end on port `name` of the function keyed `key`."""
    return sum(
        1
        for route in layout_of(model, Route).values()
        for end in (route.a, route.b)
        if functions(model)[ports(model)[end].function].key == key
        and ports(model)[end].name == name
    )


def _errors(result: Any) -> list[str]:
    """The codes of the two errors a port left with no wire and no marker gives."""
    return [f.code for f in result.findings if f.code in {"ROUTE_FAILED", "CONNECTION_NOT_DRAWN"}]


def test_a_port_reserves_the_cell_in_front_of_it_along_its_own_axis() -> None:
    """The cell one step out of a S facing port is its net's, along "v" only."""
    # UNDO: stages/grid_path.py reserve_exits, `axis = "h"` for every facing
    south, east = (
        End(at=Point(x=0, y=0), facing=Facing.S),
        End(at=Point(x=80, y=0), facing=Facing.E),
    )
    assert reserve_exits([("a", south), ("b", east)]) == {
        (0, WIRING_GRID): {"a": frozenset({"v"})},
        (80 + WIRING_GRID, 0): {"b": frozenset({"h"})},
    }


def test_a_cell_in_front_of_two_nets_ports_is_reserved_for_neither() -> None:
    """Two facing ports two steps apart share their step: no net can keep it, so none does."""
    # UNDO: stages/grid_path.py reserve_exits, `if len(nets) == 1` -> `if nets`
    down, up = (
        End(at=Point(x=0, y=0), facing=Facing.S),
        End(at=Point(x=0, y=2 * WIRING_GRID), facing=Facing.N),
    )
    assert reserve_exits([("a", down), ("b", up)]) == {}
    assert reserve_exits([("a", down), ("a", up)]) == {(0, WIRING_GRID): {"a": frozenset({"v"})}}


def test_a_strap_between_neighbouring_cells_is_drawn_when_a_wire_turns_before_its_port() -> None:
    """D9: K1:1 - K2:1 draws, and each of its ports shows a route or a marker."""
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
    assert not [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.page == one.page and one.x < p.x < two.x
    ]
    assert _errors(result) == []
    for key in (K1, K2):
        assert _routes_on(model, key, "1") + len(markers_on(model, key, "1")) >= 1
    assert route_between(model, (K1, "1"), (K2, "1")).points


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
    relay = scope.item("DEMO-CO-4P-24", tag="K1", at=c)
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
    """D1/D9, M12: Q1:2 - K1:4 draws though XA:4 - K1:3 would go round K1 past Q1:2's first step.

    XA:4 - K1:3 turns back on K1's own device, so it is a turned reference pair (S12, M12): a
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
    assert route_between(result.model, (Q1, "2"), (K1, "4")).points
    strip_4 = (terminal_key("XA", 4), "internal")
    (reference,) = markers_on(result.model, *strip_4)
    (branch,) = markers_on(result.model, K1, "3")
    assert (reference.star, branch.star) == (StarKind.REF, StarKind.BRANCH)
    assert branch.partner == reference.id
