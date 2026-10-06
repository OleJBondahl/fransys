"""D1 (layout deep dive): chains from connectivity, tested through the laid-out records.

Each design is a handful of invented parts (`examples/demo-parts`), built by `fr.build`; a test
reads the `SymbolPlacement` of a function by its authoring key (same x = one column, larger y =
further down). Not covered here: "the end net with the higher potential rank is on top". Every
library through path runs N to S, so a chain with no directed pole is terminals and mated pins
only, and those all sit on one physical net (their ends have the same rank).
"""

import pytest
from dd_chain_fixtures import MCB, TERMINAL, build, design, placed, route_between, terminal_key

from fransys_layout.engines.schematic import lay_out_schematic
from fransys_model.kernel import Severity
from fransys_model.layout import Orientation

XA1, XA2, XA3, XA4 = (terminal_key("XA", n) for n in (1, 2, 3, 4))
Q1, Q2, Q3 = (("Q1", "fn", "element"), ("Q2", "fn", "element"), ("Q3", "fn", "element"))
Z1, Z2, Z3 = (("Z1", "fn", "element"), ("Z2", "fn", "element"), ("Z3", "fn", "element"))
CO_1 = ("K1", "fn", "co_1")


def _strip_of_terminals(count: int):
    """Design with a location, a group, a strip XA of `count` terminals and a wire maker."""
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    terminals = [strip.terminal(TERMINAL, group=g) for _ in range(count)]
    return parts, d, c, g, terminals, d.wiring(colour="BU", gauge="0.75")


@pytest.mark.parametrize("sense", ["forward", "backward"])
def test_a_chain_runs_the_way_its_directed_pole_points(sense: str) -> None:
    """D1: a chain runs top to bottom the way its breaker's in-port (N) to out-port (S) points."""
    # UNDO: stages/_chain_walk.py `_vote_direction`, delete the `if backward > forward:` reversal
    forward = sense == "forward"
    parts, d, c, g, (t1, t2), wire = _strip_of_terminals(2)
    q = d.item(MCB, tag="Z1", at=c, group=g)
    wire(t1.outer, q["1" if forward else "2"])
    wire(q["2" if forward else "1"], t2.inner)
    model = build(parts, d).model
    top, bottom = (XA1, XA2) if forward else (XA2, XA1)
    ys = [placed(model, *key).y for key in (top, Z1, bottom)]
    assert ys == sorted(ys)
    assert len(set(ys)) == 3
    assert len({placed(model, *key).x for key in (top, Z1, bottom)}) == 1


def test_the_way_most_directed_poles_point_decides_the_whole_chain() -> None:
    """D1: two breakers pointing down and one pointing up run down, the odd one out included."""
    # UNDO: stages/_chain_walk.py `_vote_direction`, delete the `if backward > forward:` reversal
    parts, d, c, g, (t1, t2), wire = _strip_of_terminals(2)
    z1, z2, z3 = (d.item(MCB, tag=f"Z{n}", at=c, group=g) for n in (1, 2, 3))
    wire(t1.outer, z1["1"])
    wire(z1["2"], z2["2"])  # Q2 is wired upside down
    wire(z2["1"], z3["1"])
    wire(z3["2"], t2.inner)
    model = build(parts, d).model
    keys = (XA1, Z1, Z2, Z3, XA2)
    ys = [placed(model, *key).y for key in keys]
    assert ys == sorted(ys)
    assert len(set(ys)) == 5
    assert len({placed(model, *key).x for key in keys}) == 1


def test_a_net_of_three_ports_ends_both_chains_that_reach_it() -> None:
    """D1: two wires from XA:1's outer port make a net of three, so it links no pole to a pole.

    Each breaker still chains with the terminal on its other side, in a column of its own;
    XA:1, the net's only other member, stands in a third column.
    """
    # UNDO: stages/_chain_sides.py `build_nets`, the net union skips the connections
    parts, d, c, g, (t1, t2, t3), wire = _strip_of_terminals(3)
    z1, z2 = (d.item(MCB, tag=tag, at=c, group=g) for tag in ("Z1", "Z2"))
    wire(t1.outer, z1["1"])
    wire(t1.outer, z2["1"])
    wire(z1["2"], t2.inner)
    wire(z2["2"], t3.inner)
    model = build(parts, d).model
    x = {key: placed(model, *key).x for key in (XA1, XA2, XA3, Z1, Z2)}
    assert x[Z1] == x[XA2]
    assert x[Z2] == x[XA3]
    assert len({x[Z1], x[Z2], x[XA1]}) == 3


@pytest.mark.parametrize("wired", ["down", "up"])
def test_a_direction_free_chain_puts_the_lower_designation_on_top(wired: str) -> None:
    """D1: two terminals, no directed pole: the lower designation (XA:1) is on top either way."""
    # UNDO: stages/_chain_ties.py `_designation_after`: `return False`
    parts, d, _, _, (t1, t2), wire = _strip_of_terminals(2)
    if wired == "down":
        wire(t1.outer, t2.inner)
    else:
        wire(t2.outer, t1.inner)
    model = build(parts, d).model
    first, second = placed(model, *XA1), placed(model, *XA2)
    assert first.x == second.x
    assert first.y < second.y


@pytest.mark.parametrize(
    ("wired", "orientation"), [("down", Orientation.R0), ("up", Orientation.R180)]
)
def test_a_terminal_is_drawn_with_its_entry_port_facing_north(
    wired: str, orientation: Orientation
) -> None:
    """D1: the chain enters XA:1 at its inner port when XA:1 wires down, else at its outer one."""
    # UNDO: stages/_chain_walk.py `_note_turns`, drop `out.flipped.add(pole.function)` for terminals
    parts, d, _, _, (t1, t2), wire = _strip_of_terminals(2)
    if wired == "down":
        wire(t1.outer, t2.inner)
    else:
        wire(t2.outer, t1.inner)
    model = build(parts, d).model
    assert placed(model, *XA1).orientation is orientation
    assert placed(model, *XA2).orientation is orientation


@pytest.mark.parametrize("strip", ["directed", "free"])
def test_a_direction_free_chain_follows_a_strip_a_directed_chain_passes(strip: str) -> None:
    """D1: XA:4 leads XA:3 only when a directed chain enters the strip at its inner port."""
    # UNDO: stages/_chain_ties.py `_strip_entry_outvoted`: `return False`
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    if strip == "directed":
        q = d.item(MCB, tag="Q1", at=c, group=g)
        wire(t1.outer, q["1"])
        wire(q["2"], t2.inner)
    wire(t4.outer, t3.inner)
    model = build(parts, d).model
    three, four = placed(model, *XA3), placed(model, *XA4)
    if strip == "directed":
        # the strip's row (C15) takes XA:4 first, in the lane ahead of XA:3, both drawn upright
        assert (four.y, three.y) == (placed(model, *XA1).y,) * 2
        assert four.x < three.x
        assert four.orientation is three.orientation is Orientation.R0
    else:
        assert three.x == four.x
        assert three.y < four.y
        assert three.orientation is four.orientation is Orientation.R180


def test_a_changeover_contact_is_a_pole_from_com_to_no_and_nc_stays_off_the_chain() -> None:
    """D1: COM to NO carries the chain through K1:co_1; NC only feeds a terminal below it."""
    # UNDO: stages/_chain_poles.py `_changeover_pairs`: delete the I4 branch (through path)
    parts, d, c, g, (t1, t2, t3), wire = _strip_of_terminals(3)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c, group=g)
    f1, f2 = (d.item(MCB, tag=tag, at=c, group=g) for tag in ("Q1", "Q2"))
    co = k1.fn("co_1")
    wire(t1.outer, f1["1"])
    wire(f1["2"], co["11"])  # COM
    wire(co["14"], f2["1"])  # NO
    wire(f2["2"], t2.inner)
    wire(co["12"], t3.inner)  # NC
    model = build(parts, d).model
    column = (XA1, Q1, CO_1, Q2, XA2)
    ys = [placed(model, *key).y for key in column]
    assert ys == sorted(ys)
    assert len(set(ys)) == 5
    assert len({placed(model, *key).x for key in column}) == 1
    nc_terminal, contact = placed(model, *XA3), placed(model, *CO_1)
    assert nc_terminal.x != contact.x
    assert nc_terminal.y > contact.y
    assert contact.orientation is Orientation.R0


def test_a_chain_never_spans_two_units() -> None:
    """D1: two breakers of a unit form their own chain; the terminals wired to them stay outside."""
    # UNDO: engines/schematic/engine.py: discover_chains gets all connections, not same-unit ones
    parts, d = design()
    c = d.location("C1", "Cabinet")
    g = d.group("G1", "Group")
    unit = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    unit.revision(1, date="2026-01-01", text="First release", created="XX")
    unit_at, unit_group = unit.location("C1", "Cabinet"), unit.group("G1", "Group")
    strip = d.strip("XA", at=c)
    t1, t2 = (strip.terminal(TERMINAL, group=g) for _ in range(2))
    q1, q2 = (unit.item(MCB, tag=tag, at=unit_at, group=unit_group) for tag in ("Q1", "Q2"))
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, q1["1"])
    wire(q1["2"], q2["1"])
    wire(q2["2"], t2.inner)
    result = build(parts, d)
    # The wires bypass the unit's boundary on purpose: `UNIT_BOUNDARY_BYPASSED` is an ERROR, so
    # `fr.build` runs no layout (decision 0028); lay the numbered model out directly.
    assert {f.code for f in result.findings if f.severity is Severity.ERROR} == {
        "UNIT_BOUNDARY_BYPASSED"
    }
    model, _findings = lay_out_schematic(result.model)
    inner = [placed(model, "cab", *key) for key in (Q1, Q2)]
    assert inner[0].x == inner[1].x
    assert inner[0].y < inner[1].y
    outside = [placed(model, *key) for key in (XA1, XA2)]
    assert {p.page for p in outside}.isdisjoint({p.page for p in inner})


@pytest.mark.parametrize("wired", ["down", "up"])
def test_terminals_of_two_strips_order_by_their_strip_qualified_designation(wired: str) -> None:
    """D1: XA:1 and XB:1 (both `=G1-1`) tie on group+number; XA, the lower strip, is on top."""
    # UNDO: _chain_ties.py `_designation_after`: drop the `tie_key` comparison
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    xa, xb = (
        d.strip("XA", at=c).terminal(TERMINAL, group=g),
        d.strip("XB", at=c).terminal(TERMINAL, group=g),
    )
    wire = d.wiring(colour="BU", gauge="0.75")
    if wired == "down":
        wire(xa.outer, xb.inner)
    else:
        wire(xb.outer, xa.inner)
    model = build(parts, d).model
    top, bottom = placed(model, *terminal_key("XA", 1)), placed(model, *terminal_key("XB", 1))
    assert top.x == bottom.x
    assert top.y < bottom.y


@pytest.mark.parametrize(
    ("wired", "orientation"), [("down", Orientation.R0), ("up", Orientation.R180)]
)
def test_an_authored_chain_draws_a_terminal_with_its_entry_port_facing_north(
    wired: str, orientation: Orientation
) -> None:
    """D1: a `layout.chain` of XA:1, XA:2 enters each by its inner port when it wires down."""
    # UNDO: stages/columns.py columns_from_chains, build every authored `Cell` with `flip=False`
    parts, d, _, _, (t1, t2), wire = _strip_of_terminals(2)
    if wired == "down":
        wire(t1.outer, t2.inner)
    else:
        wire(t2.outer, t1.inner)
    d.chain(t1, t2)
    model = build(parts, d).model
    assert placed(model, *XA1).orientation is orientation
    assert placed(model, *XA2).orientation is orientation


def test_poles_strapped_in_parallel_keep_the_chain_running() -> None:
    """D1: a pole on the same two nets as another is its side element, so the strap ends nothing.

    Q1 feeds K1's main contact, whose poles 1-2 and 3-4 are strapped 1-3 and 2-4: one chain,
    XA:1, Q1, K1:main, XA:2, with K1:main drawn once, its two poles side by side.
    """
    # UNDO: stages/_chain_sides.py `_picks`, side elements: drop the same-function grouping
    parts, d, c, g, (t1, t2), wire = _strip_of_terminals(2)
    q = d.item(MCB, tag="Q1", at=c, group=g)
    k = d.item("DEMO-CTR-3P-24", tag="K1", at=c, group=g)
    main = k.fn("main")
    wire(t1.outer, q["1"])
    wire(q["2"], main["1"])
    wire(main["1"], main["3"])
    wire(main["2"], main["4"])
    wire(main["2"], t2.inner)
    model = build(parts, d).model
    column = (XA1, Q1, ("K1", "fn", "main"), XA2)
    ys = [placed(model, *key).y for key in column]
    assert ys == sorted(ys)
    assert len(set(ys)) == 4
    assert len({placed(model, *key).x for key in column}) == 1


def test_a_pole_of_two_functions_strapped_pole_to_pole_is_a_side_element() -> None:
    """D1: K1 pole 1 and K2 pole 1 on the same two nets: K1, the lower designation, carries it.

    Q1 feeds both contactors' pole 1, whose outputs are strapped and reach XA:2. K2:main is K1's
    side element: one chain, XA:1, Q1, K1:main, XA:2, with K2:main in K1:main's row, one lane over.
    """
    # UNDO: stages/_chain_sides.py `_picks`, side elements: group only poles of one function
    parts, d, c, g, (t1, t2), wire = _strip_of_terminals(2)
    q = d.item(MCB, tag="Q1", at=c, group=g)
    k1main, k2main = (
        d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2")
    )
    wire(t1.outer, q["1"])
    wire(q["2"], k1main["1"])
    wire(k1main["1"], k2main["1"])
    wire(k1main["2"], k2main["2"])
    wire(k1main["2"], t2.inner)
    model = build(parts, d).model
    k1, k2 = ("K1", "fn", "main"), ("K2", "fn", "main")
    column = (XA1, Q1, k1, XA2)
    ys = [placed(model, *key).y for key in column]
    assert ys == sorted(ys)
    assert len(set(ys)) == 4
    assert len({placed(model, *key).x for key in column}) == 1
    side = placed(model, *k2)
    assert side.y == placed(model, *k1).y
    assert side.x != placed(model, *k1).x


def test_a_function_that_carries_and_is_a_side_element_is_a_side_element_nowhere() -> None:
    """D1: K2 carries K3 (pole 2) and is K1's side element (pole 1), so it is nobody's side.

    K1 and K2 share pole 1 (chain XA:1, K1, XA:2); K2 and K3 share pole 2 (chain XA:3, K2, XA:4).
    K2 keeps its own cell, in its own chain's column, and is not drawn in K1's row; K3 stands
    beside K2, not in K2's place.
    """
    # UNDO: stages/_chain_sides.py `_side_nowhere`, side elements: make `nowhere` empty
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    k1, k2, k3 = (
        d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2", "K3")
    )
    wire(k1["1"], k2["1"])
    wire(k1["2"], k2["2"])
    wire(k2["3"], k3["3"])
    wire(k2["4"], k3["4"])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, k2["3"])
    wire(k2["4"], t4.inner)
    model = build(parts, d).model
    keys = {n: ("K" + str(n), "fn", "main") for n in (1, 2, 3)}
    first = tuple(placed(model, *key) for key in (XA1, keys[1], XA2))
    assert len({p.x for p in first}) == 1
    assert first[0].y < first[1].y < first[2].y
    second = tuple(placed(model, *key) for key in (XA3, keys[2], XA4))
    assert len({p.x for p in second}) == 1
    assert second[0].y < second[1].y < second[2].y
    beside = placed(model, *keys[3])
    assert beside.y == second[1].y
    assert beside.x != second[1].x
    assert placed(model, *keys[2]).x != first[1].x


def test_a_side_element_of_a_pole_in_the_carriers_second_column_stands_beside_the_carrier() -> None:
    """D2: K3 straps K2's pole 2, which lies in chain B; K2 is drawn once, in chain A's column.

    Chain A is XA:1, Q1, K2 pole 1, XA:2; chain B is XA:3, K2 pole 2, XA:4 (two columns). K3 stands
    beside K2's cell, in the row where K2 is drawn, and takes no lane in chain B's column.
    """
    # UNDO: stages/_chain_cells.py `_place_side`: `home_cells = cells` (the side cell is
    # placed in the row that builds it, whether or not its carrier is drawn there)
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    q = d.item(MCB, tag="Q1", at=c, group=g)
    k2, k3 = (d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K2", "K3"))
    wire(t1.outer, q["1"])
    wire(q["2"], k2["1"])
    wire(k2["2"], t2.inner)
    wire(t3.outer, k2["3"])
    wire(k2["4"], t4.inner)
    wire(k2["3"], k3["3"])
    wire(k2["4"], k3["4"])
    model = build(parts, d).model
    k2_at, k3_at = placed(model, "K2", "fn", "main"), placed(model, "K3", "fn", "main")
    assert k2_at.x == placed(model, *XA1).x
    assert k3_at.y == k2_at.y
    assert k3_at.x > k2_at.x
    assert k3_at.x != placed(model, *XA3).x


def test_a_side_element_of_two_carriers_is_a_side_element_nowhere() -> None:
    """D1: K2's pole 1 is strapped to F1's and its pole 2 to K1's: K2 is neither's side element.

    F1 and K1 each feed their own terminals; K2 keeps a cell of its own and is drawn in neither
    F1's row nor K1's.
    """
    # UNDO: stages/_chain_sides.py `_side_nowhere`, side elements: make `nowhere` empty
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    f1 = d.item(MCB, tag="F1", at=c, group=g)
    k1, k2 = (d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2"))
    wire(f1["1"], k2["1"])
    wire(f1["2"], k2["2"])
    wire(k1["1"], k2["3"])
    wire(k1["2"], k2["4"])
    wire(t1.outer, f1["1"])
    wire(f1["2"], t2.inner)
    wire(t3.outer, k1["1"])
    wire(k1["2"], t4.inner)
    model = build(parts, d).model
    f1_at, k1_at = placed(model, "F1", "fn", "element"), placed(model, "K1", "fn", "main")
    k2_at = placed(model, "K2", "fn", "main")
    assert k2_at.y != f1_at.y
    # K2 no longer shares a column with a drawn coil (layout-0112), so its row may meet K1's by
    # the first-row baseline alone: K1's row is excluded by its own x only, and the guard that K2
    # is neither carrier's side element is that no strap is drawn as a route (a side element's are)
    assert k2_at.x not in {f1_at.x, k1_at.x}
    for carrier, pin, k2_pin in (
        (("F1", "fn", "element"), "1", "1"),
        (("F1", "fn", "element"), "2", "2"),
        (("K1", "fn", "main"), "1", "3"),
        (("K1", "fn", "main"), "2", "4"),
    ):
        with pytest.raises(AssertionError, match="0 routes"):
            route_between(model, (carrier, pin), (("K2", "fn", "main"), k2_pin))


def test_an_unwired_pole_is_dropped_with_the_side_poles_strapped_to_it() -> None:
    """D2: K1 and K2 strapped on all three poles; ports 1-2 and 3-4 wired to terminals, 5-6 to none.

    K1's third pole (5-6, strapped to K2:5-6) shares its nets only with its own side poles, so it
    is unwired and opens no column: one bundle column, XA:1 and XA:3 at one y, XA:2 and XA:4 at
    another, K1 between, and every strap drawn as a route (the third pole's like the others').
    """
    # UNDO: stages/_chain_walk.py `_spare`, count the hidden side ports again (no group set)
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    k1, k2 = (d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2"))
    for pin in "123456":
        wire(k1[pin], k2[pin])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, k1["3"])
    wire(k1["4"], t4.inner)
    result = build(parts, d)
    model = result.model
    one, two, three, four = (placed(model, *key) for key in (XA1, XA2, XA3, XA4))
    k1_at = placed(model, "K1", "fn", "main")
    assert one.y == three.y
    assert two.y == four.y
    assert one.y < k1_at.y < two.y
    assert one.x == two.x
    assert three.x == four.x
    assert one.x != three.x
    assert k1_at.x == one.x  # K1 stands in the column of its wired poles, not in one of its own
    codes = {f.code for f in result.findings}
    assert "CONNECTION_NOT_DRAWN" not in codes
    assert "ROUTE_FAILED" not in codes
    main = ("K1", "fn", "main"), ("K2", "fn", "main")
    for pin in "123456":
        route_between(model, (main[0], pin), (main[1], pin))


def test_a_pole_strapped_only_to_a_side_element_nowhere_is_wired_and_keeps_its_own_column() -> None:
    """D2: K1's pole 3 is strapped to K2 only, and K2 is a side element nowhere (it carries K3).

    K1's poles 1 and 2 are wired to the terminals; pole 3 (ports 5-6) shares its nets only with
    K2:5-6. K2 keeps its own cell, so K2's ports are outside pole 3's group: the pole is wired,
    is not dropped, and opens a column of its own, unlike a pole strapped to a side pole (the
    test above), which stands in the column of the wired poles.
    """
    # UNDO: stages/_chain_sides.py `_apply_picks`, side elements: `if True:` on `side_ports[main]`
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    k1, k2, k3 = (
        d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2", "K3")
    )
    wire(k1["5"], k2["5"])
    wire(k1["6"], k2["6"])
    wire(k2["3"], k3["3"])
    wire(k2["4"], k3["4"])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, k1["3"])
    wire(k1["4"], t4.inner)
    model = build(parts, d).model
    one, two, three, four = (placed(model, *key) for key in (XA1, XA2, XA3, XA4))
    assert one.x == two.x
    assert three.x == four.x
    assert placed(model, "K1", "fn", "main").x != one.x


def test_the_straps_of_a_function_that_is_a_side_element_nowhere_are_drawn() -> None:
    """D9: the straps K1-K2 (pole 1) and K2-K3 (pole 2) all draw; none may end in an ERROR."""
    # UNDO: none. EF-D Part 2 (D7 lane width) moved K2 clear of K1, and this layout now routes; the
    # router fault it once showed (a strap in a 3-port star net that D9's fallback misses) has its
    # own test in EF-D Part 3
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    k1, k2, k3 = (
        d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2", "K3")
    )
    wire(k1["1"], k2["1"])
    wire(k1["2"], k2["2"])
    wire(k2["3"], k3["3"])
    wire(k2["4"], k3["4"])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, k2["3"])
    wire(k2["4"], t4.inner)
    codes = [f.code for f in build(parts, d).findings]
    assert "ROUTE_FAILED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes
