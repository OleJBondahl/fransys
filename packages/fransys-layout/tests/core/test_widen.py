"""Stage 7: the reserve of a gap (place_pages reserves, reserves_of) and the measured re-cut."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core import Annex, Box, Facts, PinRef, PlacementProblem, Size, Spot, order_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.cut_costs import with_wires
from fransys_layout.core.cut_measured import Measured, RowKey
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.outputs import Demand, PagePlacement
from fransys_layout.core.place import place_pages
from fransys_layout.core.row_extent import held
from fransys_layout.core.solve import solve
from fransys_layout.core.values import Ref, RefEnd, RefKind, StandClass
from fransys_layout.core.widen import measured_of, reserves_of
lazy from fransys_layout.core.flow_values import CutResult

from .conftest import MARKER
from .cut_fixtures import AREA, chain, elem, free, net, page_of
from .pipeline_fixtures import blocks_of, cut_of, flow_of, placed_from, routed_from
from .place_fixtures import card_with_coils, wide_row
from .widen_fixtures import gap_width

PLAIN = core_options(
    marker=MARKER,
)


def three_columns() -> PlacementProblem:
    """Three separate two-element columns in one row."""
    names = [[f"{c}{k}" for k in range(2)] for c in "abc"]
    syms = tuple(elem(n) for col in names for n in col)
    nets = tuple(n for col in names for n in chain(col, prefix=col[0]))
    return PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=()))


def planted() -> list[PlacementProblem]:
    return [three_columns(), card_with_coils(), wide_row()]


def gaps(page: PagePlacement) -> list[tuple[str, str, int]]:
    return [(g.left, g.right, g.x1 - g.x0) for g in page.gaps]


def test_no_reserves_is_the_landed_placement_on_three_planted_problems() -> None:
    for prob in planted():
        cut = cut_of(prob, PLAIN)
        landed = place_pages(cut, prob, PLAIN)
        assert place_pages(cut, prob, PLAIN, None) == landed
        assert place_pages(cut, prob, PLAIN, {}) == landed
        pair = next((g.left, g.right) for g in landed.pages[0].gaps) if landed.pages[0].gaps else None
        if pair:
            assert place_pages(cut, prob, PLAIN, {pair: 1}) == landed


def test_the_reserve_key_is_the_column_pair_not_the_gap_id() -> None:
    prob = three_columns()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    routes = routed_from(cut, prob, PLAIN)
    gap = placement.pages[0].gaps[1]
    page = placement.pages[0]
    respelled = replace(page, gaps=tuple(replace(g, id=f"zz{i}") for i, g in enumerate(page.gaps)))
    placement = replace(placement, pages=(respelled, *placement.pages[1:]))
    demand = (Demand("zz1", 3),)
    routes = replace(routes, pages=(replace(routes.pages[0], demand=demand), *routes.pages[1:]))
    assert reserves_of(placement, routes) == {(gap.left, gap.right): 3}
    assert gap_width(placement, "zz1") == gap.x1 - gap.x0


# the measured re-cut


def recut(prob: PlacementProblem, measured: Measured | None) -> CutResult:
    flow = flow_of(prob, PLAIN)
    lists = order_blocks(blocks_of(prob, PLAIN), flow, PLAIN)
    return cut_pages(lists, flow, prob, PLAIN, measured)


def all_heights(prob: PlacementProblem, height: int) -> Measured:
    flow = flow_of(prob, PLAIN)
    lists = order_blocks(blocks_of(prob, PLAIN), flow, PLAIN)
    blocks = [b for lst in lists for b in lst.blocks]
    return Measured({}, {b.id: height for b in blocks}, {c: height for b in blocks for c in b.columns})


def rows_of(result: CutResult) -> list[list[tuple[str, ...]]]:
    return [[row.columns for row in p.rows] for p in result.spec.pages]


def test_measured_none_and_an_empty_measure_leave_the_cut_as_it_was() -> None:
    for prob in planted():
        landed = recut(prob, None)
        assert recut(prob, Measured()) == landed


def test_a_measured_width_over_the_page_moves_the_column_to_a_new_row() -> None:
    prob = replace(three_columns(), area=Size(96, 854))
    assert rows_of(recut(prob, None)) == [[("c:a0", "c:b0", "c:c0")]]
    wider = Measured({("c:b0", "c:c0"): 2})
    assert rows_of(recut(prob, wider)) == [[("c:a0", "c:b0"), ("c:c0",)]]


def fan_legs() -> PlacementProblem:
    syms = (free("t0"), *(elem(f"k{i}", 40, 32) for i in (1, 2, 3)))
    return PlacementProblem(
        Size(100, 854),
        syms,
        (net("feed", "t0.e", "k1.n", "k2.n", "k3.n"),),
        facts=Facts(far_ends=()),
    )


def test_a_measured_height_over_the_page_moves_the_block_down_and_its_reference_follows() -> None:
    prob = replace(three_columns(), area=Size(70, 854))
    assert [len(p.rows) for p in recut(prob, None).spec.pages] == [3]
    assert [len(p.rows) for p in recut(prob, all_heights(prob, 300)).spec.pages] == [2, 1]
    legs = replace(fan_legs(), area=Size(124, 854))  # layout-0308: a row end holds a 48 G arrow; the 2|1 vs 1|2 split ties exactly (R1685)
    assert page_of(recut(legs, None)) == {"c:k1": 1, "c:k2": 1, "c:k3": 1}
    moved = recut(legs, all_heights(legs, 300))
    assert page_of(moved) == {"c:k1": 1, "c:k2": 1, "c:k3": 2}
    assert moved.spec.reference_plan[-1] == Ref("feed", RefKind.COPY, (RefEnd(2, "c:k1", PinRef("k3", "n"), stand=StandClass.TRUNK_END),))


def two_heights() -> PlacementProblem:
    """Two columns in one row: a stack of two 150 G elements and a stack of two 60 G ones."""
    syms = (elem("a0", 16, 150), elem("a1", 16, 150), elem("b0", 16, 60), elem("b1", 16, 60))
    nets = (*chain(["a0", "a1"], "a"), *chain(["b0", "b1"], "b"))
    return PlacementProblem(AREA, syms, tuple(nets), facts=Facts(far_ends=()))


def test_measured_height_is_the_blocks_own_extent_never_its_rows() -> None:
    prob = two_heights()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    measured = measured_of(cut, placement, routed_from(cut, prob, PLAIN), prob, PLAIN)
    feet = {
        p.sym: (p.y - up, p.y + down) for p in placement.pages[0].placed for up, down in [held(replace(p.footprint, y=p.footprint.y - p.y), PLAIN)]
    }
    own = {k: max(feet[s][1] for s in v) - min(feet[s][0] for s in v) for k, v in {"column:c:a0": ("a0", "a1"), "column:c:b0": ("b0", "b1")}.items()}
    row_height = placement.pages[0].rows[0][0]
    assert measured.heights["column:c:b0"] == own["column:c:b0"] < row_height
    assert measured.heights["column:c:a0"] == own["column:c:a0"]
    assert own["column:c:a0"] > own["column:c:b0"]


def fan_rows() -> PlacementProblem:
    """One fan block of five 40 x 32 legs 100 G wide: its legs stack in five rows."""
    syms = (free("t0"), *(elem(f"k{i}", 40, 32) for i in range(1, 6)))
    pins = ["t0.e", *(f"k{i}.n" for i in range(1, 6))]
    return PlacementProblem(Size(100, 854), syms, (net("feed", *pins),), facts=Facts(far_ends=()))


def test_a_columns_measured_height_is_its_own_never_its_blocks_so_its_rows_stay_on_a_page() -> None:
    prob = fan_rows()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    measured = measured_of(cut, placement, routed_from(cut, prob, PLAIN), prob, PLAIN)
    block = measured.heights["fan:c:k1"]
    assert block > 300 > 2 * max(measured.columns.values())
    page = placement.pages[0]
    foot = {p.sym: p.footprint for p in page.placed}
    # a leg's own trunk counts (layout-0374): its line stands above the leg's footprint
    rise = [foot[f"k{i}"].y - next(t.y for t in page.trunks if t.row == i - 1) for i in range(2, 6)]
    assert rise == [16] * 4  # N2: a row-end arrow keeps its half box and a grid under the lane
    assert [measured.columns[f"c:k{i}"] for i in range(2, 6)] == [
        32 + 16 + PLAIN.wiring_grid + PLAIN.column_wire_lanes * PLAIN.wiring_grid
    ] * 4  # the leg, its rise (with the arrow room), the step held above the trunk line (trunk_room), the lanes
    assert set(page_of(recut(prob, measured)).values()) == {1}


def test_an_annex_owner_s_block_grows_by_the_annex_height_in_its_measure_and_its_reserve() -> None:
    """R1129: block_reserves and the solved span read one number, annex_room, so the recut leaves the annex room."""
    prob = card_with_coils()
    cut = cut_of(prob, PLAIN)
    card = next(b for lst in cut.blocks for b in lst.blocks if b.is_card)
    assert card.anchor is not None
    annexed = replace(prob, annexes=(Annex(card.anchor, Size(40, 16), None, {"R0": (Spot("TL", "TL", 0, -16, "up"),)}),))
    bare = measured_of(cut, placed_from(cut, prob, PLAIN), routed_from(cut, prob, PLAIN), prob, PLAIN)
    held_ = measured_of(cut, placed_from(cut, annexed, PLAIN), routed_from(cut, annexed, PLAIN), annexed, PLAIN)
    assert held_.arrows[card.anchor].y == 16
    assert bare.heights[card.id] < held_.heights[card.id] <= bare.heights[card.id] + 32


def test_a_fold_piece_is_placed_within_the_page_room_with_the_tags_it_places() -> None:
    """KI-542 (R1427, R1430): the fold counts the tag at each piece end, so no placed piece is taller than the page room."""
    syms = [elem(f"e{i}", height=250) for i in range(8)]
    prob = PlacementProblem(AREA, tuple(syms), tuple(chain([s.id for s in syms])), facts=Facts(far_ends=()))
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    sized = {c.id for c in cut.flow.columns if "#" in c.id}
    room = AREA.h - PLAIN.page_headroom - with_wires(0, PLAIN) - 2 * PLAIN.open_stub
    placed = {k: bottom - top for page in placement.pages for k, (top, bottom) in page.spans.items() if k in sized}
    assert len(sized) > 1
    assert all(h <= room for h in placed.values())


def wide_annex_columns(width: int) -> PlacementProblem:
    """three_columns() with one annex a symbol, beside its body at the top right, `width` wide: it fits only once the gap is that wide."""
    prob = three_columns()
    return replace(prob, annexes=tuple(Annex(s.id, Size(width, 8), None, {"R0": (Spot("TR", "TR", 0, 0, "down"),)}) for s in prob.symbols))


@pytest.mark.rule("TAG-CORNERS")
def test_a_label_blocked_at_every_candidate_widens_its_gap_before_it_is_a_finding() -> None:
    """A6: a box 100 wide beside a body stands in a gap of 8 nowhere; its need goes to the recut, the gaps grow, and every label stands."""
    layout = solve(wide_annex_columns(100), PLAIN)
    assert [f for f in layout.findings if f.code == "ANNEX_UNPLACED"] == []
    assert len(layout.annotations.annexes) == 6
    assert min(g.x1 - g.x0 for g in layout.placement.pages[0].gaps) >= 100


def edge_column_annexes() -> PlacementProblem:
    """three_columns() with a 100-wide box a symbol, first at its left (outside the page for the first column), then at its right."""
    prob = three_columns()
    spots = (Spot("TL", "TL", -100, 0, "down"), Spot("TR", "TR", 0, 0, "down"))
    return replace(prob, annexes=tuple(Annex(s.id, Size(100, 8), None, {"R0": spots}) for s in prob.symbols))


@pytest.mark.rule("TAG-CORNERS")
def test_a_label_blocked_at_the_page_edge_widens_the_gap_at_its_other_side() -> None:
    """LABEL-PLACE 3: the first column's left spot lies outside the page; its need goes to the gap on its right and every label stands."""
    layout = solve(edge_column_annexes(), PLAIN)
    assert [f for f in layout.findings if f.code == "ANNEX_UNPLACED"] == []
    assert min(g.x1 - g.x0 for g in layout.placement.pages[0].gaps) >= 100


def stacked_column_annexes() -> PlacementProblem:
    """One column of two elements; the lower one has a 60-high box above it, where the upper one stands."""
    names = ["a0", "a1"]
    prob = PlacementProblem(AREA, tuple(elem(n) for n in names), tuple(chain(names, prefix="a0")), facts=Facts(far_ends=()))
    return replace(prob, annexes=(Annex("a1", Size(16, 60), None, {"R0": (Spot("TR", "TR", 0, -60, "down", 8),)}),))


@pytest.mark.rule("TAG-CORNERS")
def test_a_label_with_no_gap_beside_its_column_asks_for_room_above_its_owner() -> None:
    """LABEL-PLACE 3: a column with no gap has no width to give; the tag's need is vertical room, and the label stands clear of both bodies."""
    layout = solve(stacked_column_annexes(), PLAIN)
    assert [f for f in layout.findings if f.code == "ANNEX_UNPLACED"] == []
    bodies = [p.body for p in layout.placement.pages[0].placed]
    assert len(layout.annotations.annexes) == 1
    assert not any(overlaps(a.box, b) for a in layout.annotations.annexes for b in bodies)


@pytest.mark.rule("TAG-CORNERS")
def test_a_label_still_blocked_after_the_widen_is_a_finding_naming_it_and_stands_at_its_first_spot() -> None:
    """T6: a box wider than the page fits no gap; the finding names its owner and the label is neither dropped nor moved."""
    layout = solve(wide_annex_columns(AREA.w + 8), PLAIN)
    named = {f.subject for f in layout.findings if f.code == "ANNEX_UNPLACED"}
    assert named == {s.id for s in three_columns().symbols}
    assert len(layout.annotations.annexes) == 6


def test_block_reserves_hold_only_the_stub_box_below_the_row_content_on_a_card_and_on_each_column() -> None:
    """R1636: `RowReserve.y` is the part of the tallest trunk-end stub box below the row's own content; a stub that fits reserves 0."""
    from fransys_layout.core.arrow_reserve import block_reserves
    from fransys_layout.core.cut_costs import item_height

    pin, far = PinRef("a", "out"), PinRef("x", "1")
    refs = (Ref("n", RefKind.STUB, (RefEnd(1, "c", pin, 0, StandClass.LEG, far=(far,)),)),)
    for box_h in (472, 8):
        options = replace(PLAIN, stub_lines={(pin, far): (2,)}, stub_table={(2, 1): {"R0": Box(0, -8, 71, box_h)}})
        for prob in (card_with_coils(), three_columns()):
            cut = cut_of(prob, options)
            cut = replace(cut, spec=replace(cut.spec, reference_plan=refs))
            reserves = block_reserves(cut, (), options)
            columns = {c.id: c for c in cut.flow.columns}
            blocks = [b for lst in cut.blocks for b in lst.blocks]
            held = [reserves[b.anchor or b.id].y if b.is_card else reserves[b.anchor or b.id, c].y for b in blocks for c in b.columns[:1]]
            want = [max(0, box_h - (b.height_est if b.is_card else item_height(columns[c], options))) for b in blocks for c in b.columns[:1]]
            assert held
            assert held == want
            assert any(held) == (box_h == 472)


def test_block_reserves_hold_the_arrow_room_under_the_lane_where_it_exceeds_the_row_content() -> None:
    """R1692: a lane-end arrow reserves `arrow_room` less one grid, whatever the row content, as the solve deepens the legs by it; none reserves 0."""
    from fransys_layout.core.arrow_reserve import block_reserves
    from fransys_layout.core.cut_end_rooms import arrow_room
    from fransys_layout.core.flow_values import Attach, Fan

    options = replace(PLAIN, wiring_grid=400)
    for prob in (card_with_coils(),):
        cut = cut_of(prob, PLAIN)
        pin = PinRef("a", "p")
        fan = Fan("f", ("n",), (), (Attach(None, 0, 0, pin, 0, net="n"),), None, 1, "below")
        cut = replace(cut, flow=replace(cut.flow, fans=(fan,)))
        page = cut.spec.pages[0]
        arrow = Ref(fan.id, RefKind.ARROW, (RefEnd(page.page, None, pin, 0), RefEnd(page.page, None, pin, 1)))
        refs = (arrow,)
        room = arrow_room(refs, page, cut.flow.fans, 0, options)
        cut = replace(cut, spec=replace(cut.spec, reference_plan=refs))
        reserves = block_reserves(cut, (), options)
        blocks = [b for b in (x for lst in cut.blocks for x in lst.blocks) if b.id in page.rows[0].blocks]
        held = [reserves[b.anchor or b.id].y if b.is_card else reserves[b.anchor or b.id, c].y for b in blocks for c in b.columns[:1]]
        want = [max(0, room - options.wiring_grid) for b in blocks for c in b.columns[:1]]
        assert held == want
        assert any(held)
        assert not any(r.y for r in block_reserves(replace(cut, spec=replace(cut.spec, reference_plan=())), (), options).values())


def _window_cut(rows: dict[RowKey, tuple[int, int]]) -> CutResult:
    prob = three_columns()
    flow = flow_of(prob, PLAIN)
    return cut_pages(order_blocks(blocks_of(prob, PLAIN), flow, PLAIN), flow, prob, PLAIN, Measured(rows=rows))


@pytest.mark.parametrize("record", [(5000, 40), (100, 5000)], ids=["too wide", "too tall"])
def test_a_window_recorded_over_the_page_is_not_cut_as_one_row_and_an_unrecorded_one_is(record: tuple[int, int]) -> None:
    """R2000: `row_size` reads the placed (need width, band height) of a window; a first row over the page splits unless unbreakable."""
    plain = _window_cut({})
    (row,) = plain.spec.pages[0].rows
    assert len(plain.spec.pages) == 1
    recorded = _window_cut({row_key_of(row): record})
    assert len(recorded.spec.pages[0].rows) > 1 or len(recorded.spec.pages) > 1


def row_key_of(row):
    return (row.columns, row.blocks)


def test_the_placed_rows_keep_the_larger_of_every_round() -> None:
    """R1673: a window placed too big stays too big, so no cut that did not fit is chosen twice."""
    from fransys_layout.core.cut_measured import placed_rows

    prob = three_columns()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    (key,) = {row_key_of(r) for r in cut.spec.pages[0].rows}
    (top, bottom), width = placement.pages[0].bands[0], placement.pages[0].rows[0][1]
    band = bottom - top
    big = placed_rows({key: (width + 40, band - 8)}, cut, placement)
    assert big[key] == (width + 40, band)
    assert placed_rows({}, cut, placement)[key] == (width, band)


def test_a_placed_row_is_as_wide_as_it_needs_not_as_justified() -> None:
    """R2001: `PagePlacement.rows` holds the packed width, while the positions carry the justified x."""
    prob = three_columns()
    cut = cut_of(prob, PLAIN)
    page = placed_from(cut, prob, PLAIN).pages[0]
    spread = max(p.footprint.x + p.footprint.w for p in page.placed) - min(p.footprint.x for p in page.placed)
    assert 0 < page.rows[0][1] < spread
