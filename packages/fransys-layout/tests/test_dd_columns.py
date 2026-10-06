"""D2 (layout deep dive): columns, bundles, side elements, end cells, splits and star nets.

Same method as `test_dd_chains.py`: small invented designs on `examples/demo-parts`, read back
through the laid-out `SymbolPlacement`, `Route` and `LinkMarker` records.
"""

import pytest
from dd_chain_fixtures import (
    MCB,
    TERMINAL,
    build,
    design,
    markers_on,
    placed,
    route_between,
    terminal_key,
    three_breakers,
)

from fransys_model.layout import Orientation, StarKind

Q1, Q2, Q3 = (("Q1", "fn", "element"), ("Q2", "fn", "element"), ("Q3", "fn", "element"))
MAIN = ("K1", "fn", "main")
LAMP = ("H1", "fn", "lamp")
POLE_PITCH = 32  # G, the distance between poles 1 and 2 of the house make-contact symbol


def _pair(d, g1, g2=None):
    """A location and two terminals XA:1, XA:2 (XA:2 in `g2` when given), with a wire maker."""
    c = d.location("C1", "Cabinet")
    strip = d.strip("XA", at=c)
    return c, strip.terminal(TERMINAL, group=g1), strip.terminal(TERMINAL, group=g2 or g1)


def test_chains_through_a_multi_pole_function_are_one_bundle_at_the_exact_pole_pitch() -> None:
    """D2: three chains through K1:main are one bundle column, its lanes one pole pitch apart."""
    # UNDO: _chain_walk.py `_group_bundles` `and multi` -> False AND engine.py `join_strip_rows`
    # call removed
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    top, bottom = d.strip("XA", at=c), d.strip("XB", at=c)
    k1 = d.item("DEMO-CTR-3P-24", tag="K1", at=c, group=g)
    wire = d.wiring(colour="BU", gauge="0.75")
    for pole in (1, 3, 5):
        wire(top.terminal(TERMINAL, group=g).outer, k1.fn("main")[str(pole)])
        wire(k1.fn("main")[str(pole + 1)], bottom.terminal(TERMINAL, group=g).inner)
    model = build(parts, d).model
    main = placed(model, *MAIN)
    for strip in ("XA", "XB"):
        row = [placed(model, *terminal_key(strip, n)) for n in (1, 2, 3)]
        assert [p.x for p in row] == [main.x + lane * POLE_PITCH for lane in range(3)]
        assert len({p.y for p in row}) == 1
    assert (
        placed(model, *terminal_key("XA", 1)).y < main.y < placed(model, *terminal_key("XB", 1)).y
    )


def test_a_two_port_pole_on_the_same_two_nets_is_a_side_element_one_lane_right() -> None:
    """D2: Q2 in parallel with Q1 stands in Q1's row to its right, its wires kept (no markers)."""
    # UNDO: stages/_chain_sides.py `_picks`: `if len(group) < 2:` -> `if True:`
    parts, d = design()
    g = d.group("G1", "Group")
    c, t1, t2 = _pair(d, g)
    q1, q2 = (d.item(MCB, tag=tag, at=c, group=g) for tag in ("Q1", "Q2"))
    wire = d.wiring(colour="BU", gauge="0.75")
    for q in (q1, q2):
        wire(t1.outer, q["1"])
        wire(q["2"], t2.inner)
    model = build(parts, d).model
    first, side = placed(model, *Q1), placed(model, *Q2)
    assert side.y == first.y
    assert first.x < side.x < first.x + 96
    assert (
        placed(model, *terminal_key("XA", 1)).x
        == placed(model, *terminal_key("XA", 2)).x
        == first.x
    )
    for key in (Q1, Q2):
        assert route_between(model, (terminal_key("XA", 1), "external"), (key, "1"))
        assert route_between(model, (key, "2"), (terminal_key("XA", 2), "internal"))
        assert markers_on(model, key, "1") == []


def test_a_lone_terminal_is_an_end_cell_above_a_north_port_and_below_a_south_port() -> None:
    """D2: a lamp's port 1 (N) has its terminal above, port 2 (S) below, one column, wired."""
    # UNDO: stages/chains.py _attach: `continue` just before `found[host, facing].append(...)`
    parts, d = design()
    g = d.group("G1", "Group")
    c, t1, t2 = _pair(d, g)
    lamp = d.item("DEMO-LAMP-24", tag="H1", at=c, group=g)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, lamp["1"])
    wire(lamp["2"], t2.inner)
    model = build(parts, d).model
    above, box, below = (
        placed(model, *key) for key in (terminal_key("XA", 1), LAMP, terminal_key("XA", 2))
    )
    assert above.y < box.y < below.y
    assert above.x == box.x == below.x
    assert above.orientation is below.orientation is Orientation.R0
    assert route_between(model, (terminal_key("XA", 1), "external"), (LAMP, "1"))
    assert route_between(model, (LAMP, "2"), (terminal_key("XA", 2), "internal"))


@pytest.mark.parametrize("groups", ["one", "two"])
def test_a_chain_splits_where_the_authored_function_group_changes(groups: str) -> None:
    """D2: Q1 to Q2 is one column in one group; with Q2 and XA:2 in another group they part."""
    # UNDO: _chain_walk.py `_split_at_groups`: `_group_of(a) == _group_of(b)` -> always true
    second_group = groups == "two"
    parts, d = design()
    g1, g2 = d.group("G1", "First"), d.group("G2", "Second")
    c, t1, t2 = _pair(d, g1, g2 if second_group else None)
    q1 = d.item(MCB, tag="Q1", at=c, group=g1)
    q2 = d.item(MCB, tag="Q2", at=c, group=g2 if second_group else g1)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, q1["1"])
    wire(q1["2"], q2["1"])
    wire(q2["2"], t2.inner)
    model = build(parts, d).model
    first, second = placed(model, *Q1), placed(model, *Q2)
    assert placed(model, *terminal_key("XA", 1)).x == first.x
    assert second.page == first.page
    if second_group:
        assert second.x > first.x
        assert second.y == first.y
        assert placed(model, *terminal_key("XA", 2)).x == second.x
    else:
        assert second.x == first.x
        assert second.y > first.y
        assert placed(model, *terminal_key("XA", 2)).x == first.x


def test_a_column_never_spans_two_locations_and_the_conductor_between_ends_in_markers() -> None:
    """D2: Q2 at +C2 is on another page than Q1 at +C1; the wire between them ends in markers."""
    # UNDO: engines/schematic/engine.py: delete the `discovered = cut_locations(...)` line
    parts, d = design()
    g = d.group("G1", "Group")
    c1, c2 = d.location("C1", "Cabinet"), d.location("C2", "Second cabinet")
    strip = d.strip("XA", at=c1)
    t1, t2 = (strip.terminal(TERMINAL, group=g) for _ in range(2))
    q1, q2 = d.item(MCB, tag="Q1", at=c1, group=g), d.item(MCB, tag="Q2", at=c2, group=g)
    wire = d.wiring(colour="BU", gauge="0.75")
    wire(t1.outer, q1["1"])
    wire(q1["2"], q2["1"])
    wire(q2["2"], t2.inner)
    model = build(parts, d).model
    first, second = placed(model, *Q1), placed(model, *Q2)
    assert placed(model, *terminal_key("XA", 1)).page == first.page
    assert second.page != first.page
    (out_marker,) = markers_on(model, Q1, "2")
    (in_marker,) = markers_on(model, Q2, "1")
    assert (out_marker.page, in_marker.page) == (first.page, second.page)


def test_a_feed_fanning_to_three_breakers_joins_each_by_one_level_wire_and_marks_none() -> None:
    """D2, S12, M12: the feed terminal XA:1 stands in the column right of Q3, every port of the
    net facing N at its column's top, so the three joins XA:1 - Q1:1, Q2:1, Q3:1 are LD9 runs
    that the turn test passes at both ends (M12: a same-side join stays a wire at any column
    distance). Each is a route, all three along one level, and no port of the net takes a
    marker."""
    # UNDO: stages/references/joins.py `wired_beside`, the `at_ends` loop's `_add` -> `pass`
    #     (no LD9 run is joined): Q1:1 takes a marker and XA:1 - Q1:1 has no route
    model = three_breakers(daisy=False)
    feed = (terminal_key("XA", 1), "external")
    levels = set()
    for key in (Q1, Q2, Q3):
        assert markers_on(model, key, "1") == []
        wire = route_between(model, (key, "1"), feed)
        levels.add(min(point.y for point in wire.points))
        assert route_between(model, (key, "2"), (terminal_key("XB", int(key[0][1])), "internal"))
    assert len(levels) == 1, "the three joins run along one level"
    assert markers_on(model, *feed) == []


def test_a_daisy_chain_joins_the_columns_it_can_level_and_marks_the_two_wired_parts() -> None:
    """D2, S12, M12: XA:1 feeds Q1:1, which chains to Q2:1 and Q3:1, the breakers side by side.

    Q1 stands below the feed terminal in its column, so Q1:1 is not at the column's end and its
    join to Q2:1 is a level run that would move a column: it is not beside (S12, designer
    2026-09-27: "beside only when join_y puts its ends on one y without moving any column"). The
    net is two wired parts, XA:1 - Q1:1 and Q2:1 - Q3:1, joined by one reference pair: the
    reference at XA:1, the branch at Q3:1 (R7 B4), and no marker at Q1:1 or Q2:1. The test
    asserted a wire Q1:1 - Q2:1 before M12 changed which joins are beside.
    """
    model = three_breakers(daisy=True)
    feed = (terminal_key("XA", 1), "external")
    assert route_between(model, (Q1, "1"), feed)  # the first part is a wire
    assert route_between(model, (Q3, "1"), (Q2, "1"))  # so is the second
    assert markers_on(model, Q1, "1") == markers_on(model, Q2, "1") == []
    (reference,) = markers_on(model, *feed)
    (branch,) = markers_on(model, Q3, "1")
    assert (reference.star, branch.star) == (StarKind.REF, StarKind.BRANCH)
    assert branch.partner == reference.id
