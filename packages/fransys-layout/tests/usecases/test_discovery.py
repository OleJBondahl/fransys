"""End-to-end chain discovery on the invented cabinet (deep-dive D1 and D2).

`build_cabinet(discovery=True)` suppresses every `layout.chain` and adds the potentials and
the three invented circuits `discovery=False` never exercises (multi-pole, branch,
reconvergent). D1 replaced the WP16 ladder discovery (rail-to-rail rungs, trunk and branch
children, refused reconvergent pairs): every function takes part, a net of exactly two pole
ports links two poles, and any other net ends a chain (a star, D9). The tests below assert the
D1 and D2 results derived by hand from the fixture's wiring. All data invented.
"""

from functools import cache
from typing import Any

from dd_chain_fixtures import MCB, TERMINAL, build, design, placed, terminal_key
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import StageInputs, read_inputs
from fransys_model.kernel import Id, Model, Origin, Severity, freeze, make_id
from fransys_model.layout import Chain as ModelChain
from fransys_model.layout import ChainEntry as ModelChainEntry
from fransys_model.vocab.tables import functions

_HINTED = freeze(build_cabinet())
_DISCOVERED = freeze(build_cabinet(discovery=True))
_ORIGIN = Origin(file="tests/usecases/test_discovery.py", line=1, note="hinted-chain-wins probe")


def _model(*, discovery: bool) -> Model:
    return _DISCOVERED if discovery else _HINTED


@cache
def _inputs(*, discovery: bool) -> StageInputs:
    return read_inputs(_model(discovery=discovery))


def _function(model: Model, key: tuple[str, ...]) -> Id[Any]:
    (spec,) = (f for f in functions(model).values() if f.key == key)
    return spec.id


def _cells_of(function: Id[Any]) -> tuple[Id[Any], ...] | None:
    """The cells (function handles, in order) of the discovered column placing `function`.

    `None` if `function` is placed alone (`FUNCTION_UNPLACED_IN_COLUMN`) rather than in a
    rung of more than one cell.
    """
    results, _ = stage_results(_model(discovery=True), _inputs(discovery=True))
    for column in results.columns:
        cells = tuple(cell.function for cell in column.cells)
        if function in cells and len(cells) > 1:
            return cells
    return None


def test_no_coherence_error_on_the_discovery_cabinet() -> None:
    """Discovery's extra circuits and the wider sheet they need draw with no coherence error."""
    _, _, findings = run_stages(_model(discovery=True), _inputs(discovery=True))
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert errors == []


def test_the_recovery_table_matches_the_hinted_chains_exactly() -> None:
    """The recovery table is spec-derived (D1), not the hinted chains cell for cell (layout-0034).

    D1: K1's main contact is wired on two parallel poles (`_discovery_extras`); the second
    pole is the first one's side element, its ports do not count on Q1's outlet net, so
    `p1/power` recovers as one chain (layout-0050, as in the ladder era's merge of
    parallel poles).
    `p1/control` runs on through X4:1's cable core to the lamp H1, which D1 joins to it (a
    two-port net with a pole).
    """
    results, _ = stage_results(_model(discovery=True), _inputs(discovery=True))
    discovered = {
        tuple(cell.function for cell in column.cells): column for column in results.columns
    }
    rungs = {
        "sup": (
            ("cabinet", "x1", "1", "fn", "terminal"),
            ("cabinet", "f1", "fn", "element"),
            ("cabinet", "x2", "1", "fn", "terminal"),
        ),
        "p1/power": (
            ("cabinet", "x1", "2", "fn", "terminal"),
            ("cabinet", "q1", "fn", "element"),
            ("cabinet", "k1", "fn", "main"),
            ("cabinet", "x3", "1", "fn", "terminal"),
        ),
        "p2/power": (
            ("cabinet", "x1", "3", "fn", "terminal"),
            ("cabinet", "q2", "fn", "element"),
            ("cabinet", "k2", "fn", "main"),
            ("cabinet", "x3", "2", "fn", "terminal"),
        ),
        "p1/control": (
            ("cabinet", "s1", "fn", "nc_1"),
            ("cabinet", "k1", "fn", "coil"),
            ("cabinet", "x4", "1", "fn", "terminal"),
            ("cabinet", "h1", "fn", "lamp"),
        ),
        "p2/control": (
            ("cabinet", "s2", "fn", "nc_1"),
            ("cabinet", "k2", "fn", "coil"),
            ("cabinet", "x4", "2", "fn", "terminal"),
        ),
    }
    for name, keys in rungs.items():
        expected = tuple(_function(_DISCOVERED, key) for key in keys)
        assert expected in discovered, f"{name}: no discovered column has exactly these cells"


def _columns() -> dict[tuple[Id[Any], ...], Any]:
    """The discovered columns of the discovery cabinet, by their cells' functions in order."""
    results, _ = stage_results(_model(discovery=True), _inputs(discovery=True))
    return {tuple(cell.function for cell in column.cells): column for column in results.columns}


def test_supply_and_control_chains_are_found_from_connectivity_alone() -> None:
    """D1: each run of two-port nets is one chain, top to bottom, with no authored chain.

    `sup`: X1:1 - F1 - X2:1 (the terminals link through their own pole, F1 through its through
    path). `p2/control`: S2 - K2 coil - X4:2. `p1/control` the same with S1, K1 and X4:1; the
    cable core from X4:1 leads on to the lamp H1, which D1 joins to it (a two-port net with a
    pole), so only the first three cells are asserted here.
    """
    columns = _columns()
    key = _function
    sup = tuple(
        key(_DISCOVERED, k)
        for k in (
            ("cabinet", "x1", "1", "fn", "terminal"),
            ("cabinet", "f1", "fn", "element"),
            ("cabinet", "x2", "1", "fn", "terminal"),
        )
    )
    assert sup in columns
    p2 = tuple(
        key(_DISCOVERED, k)
        for k in (
            ("cabinet", "s2", "fn", "nc_1"),
            ("cabinet", "k2", "fn", "coil"),
            ("cabinet", "x4", "2", "fn", "terminal"),
        )
    )
    assert p2 in columns
    p1 = tuple(
        key(_DISCOVERED, k)
        for k in (
            ("cabinet", "s1", "fn", "nc_1"),
            ("cabinet", "k1", "fn", "coil"),
            ("cabinet", "x4", "1", "fn", "terminal"),
        )
    )
    assert [cells for cells in columns if cells[:3] == p1] != []


def test_a_net_of_three_pole_ports_ends_a_chain() -> None:
    """D1: Q1:2, Q2:1 and Q3:1 are three poles on one net, so the net links nothing.

    X:1 - Q1 stays a chain (a two-port net links them); Q2 and Q3 each head a chain of their own.
    Re-based from K1's strap (layout-0050): a strapped pole is a side element, its ports do not
    count, so the discovery cabinet no longer has a three-pole-port net.
    """
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    t1, t2, t3 = (strip.terminal(TERMINAL, group=g) for _ in range(3))
    q1, q2, q3 = (d.item(MCB, tag=f"Q{n}", at=c, group=g) for n in (1, 2, 3))
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, q1["1"])
    wire(q1["2"], q2["1"])
    wire(q1["2"], q3["1"])
    wire(q2["2"], t2.inner)
    wire(q3["2"], t3.inner)
    model = build(parts, d).model
    x = {n: placed(model, f"Q{n}", "fn", "element").x for n in (1, 2, 3)}
    assert placed(model, *terminal_key("XA", 1)).x == x[1]
    assert placed(model, *terminal_key("XA", 2)).x == x[2] != x[1]
    assert placed(model, *terminal_key("XA", 3)).x == x[3] != x[1]


def test_es_second_contact_is_placed_with_k1_aux_the_chain_cut_where_the_group_changes() -> None:
    """D2: `s0.nc_2` and `k1.aux` are one chain; its group hint (`=P1`) cuts it from `s0.nc_1`
    (`=ES`) upstream and, at `=P2`, from `k2.aux` downstream. Nothing is left out (D1).
    """
    nc_1 = _function(_DISCOVERED, ("cabinet", "s0", "fn", "nc_1"))
    nc_2 = _function(_DISCOVERED, ("cabinet", "s0", "fn", "nc_2"))
    aux = _function(_DISCOVERED, ("cabinet", "k1", "fn", "aux"))
    assert _cells_of(nc_2) == (nc_2, aux)
    assert nc_1 not in (_cells_of(nc_2) or ())


def test_h1_is_newly_placed_a_topologically_real_one_hop_rung() -> None:
    """`H1` spans 24V to 0V through its two cable cores: discovery places it, no hint did."""
    lamp = _function(_DISCOVERED, ("cabinet", "h1", "fn", "lamp"))
    layout, _, _ = run_stages(_model(discovery=True), _inputs(discovery=True))
    placed = {p.function for p in layout.placed}
    assert lamp in placed


def test_the_spare_relay_is_placed_as_one_chain_through_its_declared_net() -> None:
    """D1: K8 (not installed, still drawn) has no conductor, but its declared LATCH net holds
    exactly two pole ports (`coil.A1`, `no_1.13`), which link: one column of both functions.
    """
    coil = _function(_DISCOVERED, ("cabinet", "k8", "fn", "coil"))
    contact = _function(_DISCOVERED, ("cabinet", "k8", "fn", "no_1"))
    cells = _cells_of(coil)
    assert cells is not None
    assert set(cells) == {coil, contact}


def test_the_multi_pole_contact_is_one_cell_not_two() -> None:
    """K1's main contact, wired on two parallel poles, is one cell, not two.

    The strap's second pole is the first one's side element (D1, layout-0050): the chain
    `X1:2, Q1, K1:main, X3:1` runs on through it.
    """
    results, _ = stage_results(_model(discovery=True), _inputs(discovery=True))
    main = _function(_DISCOVERED, ("cabinet", "k1", "fn", "main"))
    (column,) = (c for c in results.columns if main in (cell.function for cell in c.cells))
    assert sum(1 for cell in column.cells if cell.function == main) == 1


def _port_of(function: Id[Any], name: str) -> Id[Any]:
    """The model port called `name` of `function`."""
    (spec,) = (f for f in _inputs(discovery=True).functions if f.function == function)
    (port,) = (p.port for p in spec.ports if p.name == name)
    return port


def test_the_fork_is_a_star_net_that_ends_three_chains_and_stays_one_level_wire() -> None:
    """D1 + S12: the net `X7:1.external`, `S10:11`, `S11:11` has three ports, so it links nothing.

    `X7:1` is a chain of its own; `S10` and `S11` each head a chain down to their 0V terminal,
    the contact on top (its port `11` faces N). There is no trunk and no branch column. The three
    ports stand on one y, so the net is a joined run (S12, M12: same-side ports at one y stay a
    wire) and gets no star markers: each of its three ports ends a wire that runs along the one
    level (the topmost y of the routes) shared by all three.
    """
    x7 = _function(_DISCOVERED, ("cabinet", "x7", "1", "fn", "terminal"))
    s10 = _function(_DISCOVERED, ("cabinet", "s10", "fn", "nc_1"))
    s11 = _function(_DISCOVERED, ("cabinet", "s11", "fn", "nc_1"))
    x8_1 = _function(_DISCOVERED, ("cabinet", "x8", "1", "fn", "terminal"))
    x8_2 = _function(_DISCOVERED, ("cabinet", "x8", "2", "fn", "terminal"))
    columns = _columns()
    assert (x7,) in columns
    assert (s10, x8_1) in columns
    assert (s11, x8_2) in columns
    layout, _, _ = run_stages(_model(discovery=True), _inputs(discovery=True))
    ports = (_port_of(x7, "external"), _port_of(s10, "11"), _port_of(s11, "11"))
    assert not [marker for marker in layout.markers if marker.port in ports]
    levels = {
        port: {
            min(point.at.y for point in route.points)
            for route in layout.routes
            if port in (route.a, route.b)
        }
        for port in ports
    }
    assert all(len(ys) == 1 for ys in levels.values()), "each port ends a routed wire, on one level"
    assert len({y for ys in levels.values() for y in ys}) == 1, "all three share the one level"


def test_the_parallel_pair_is_one_row_with_a_side_element_and_no_refusal() -> None:
    """D2: K20 and K21 stand on the same two nets, so the later key (`k21`) is K20's side element.

    It is drawn one lane to the right in K20's row, and the column runs on through K22's coil
    to the 0V terminal X9:1.
    """
    k20 = _function(_DISCOVERED, ("cabinet", "k20", "fn", "no_1"))
    k21 = _function(_DISCOVERED, ("cabinet", "k21", "fn", "no_1"))
    k22 = _function(_DISCOVERED, ("cabinet", "k22", "fn", "coil"))
    x9 = _function(_DISCOVERED, ("cabinet", "x9", "1", "fn", "terminal"))
    column = _columns()[k20, k21, k22, x9]
    by_function = {cell.function: cell for cell in column.cells}
    assert by_function[k21].side is True
    assert (by_function[k21].index, by_function[k21].lane) == (by_function[k20].index, 1)
    assert by_function[k22].index == by_function[k20].index + 1
    assert by_function[x9].index == by_function[k22].index + 1


def test_the_default_cabinet_still_declares_no_rails() -> None:
    """`build_cabinet()` declares no `Net.potential`, so the stage inputs carry no rail."""
    assert _inputs(discovery=False).rails == ()


def test_a_hinted_chain_wins_over_discovery_end_to_end() -> None:
    """One authored `layout.chain` over `sup`'s three functions beats discovery for them.

    Built on the `discovery=True` fixture (every other chain suppressed, every rail and
    invented circuit present, so those same three functions are fully rail-to-rail
    discoverable on their own) plus one hand-authored chain over them, keyed differently
    from anything discovery would key. `stage_results` gives exactly one column for the
    three cells, keyed by the chain's own key -- proving the engine's exclusion
    (`chain_claimed` filtered out of `discover_chains`' input, discovery's own placements
    filtered out of `columns_from_chains`' in turn) end to end, not just at the stage level.
    """
    feed = _function(_DISCOVERED, ("cabinet", "x1", "1", "fn", "terminal"))
    fuse = _function(_DISCOVERED, ("cabinet", "f1", "fn", "element"))
    rail = _function(_DISCOVERED, ("cabinet", "x2", "1", "fn", "terminal"))
    chain_key = ("cabinet", "sup", "hinted-again")
    chain = ModelChain(
        id=make_id(ModelChain, chain_key),
        key=chain_key,
        entries=(
            ModelChainEntry(function=feed, index=0),
            ModelChainEntry(function=fuse, index=1),
            ModelChainEntry(function=rail, index=2),
        ),
    )
    draft = build_cabinet(discovery=True)
    draft.extend((chain,), origin=_ORIGIN)
    model = freeze(draft)
    results, _ = stage_results(model, read_inputs(model))

    claiming = [
        column
        for column in results.columns
        if tuple(cell.function for cell in column.cells) == (feed, fuse, rail)
    ]
    assert len(claiming) == 1
    assert claiming[0].key == chain_key
