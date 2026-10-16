"""Stage 7: the reserve of a gap (place_pages reserves, reserves_of) and the measured re-cut."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Options, PinRef, PlacementProblem, Size, order_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.cut_costs import HEIGHT_WIRES
from fransys_layout.core.cut_measured import Measured
from fransys_layout.core.outputs import Demand, PagePlacement
from fransys_layout.core.place import place_pages
from fransys_layout.core.values import CutResult, Ref, RefEnd, RefKind
from fransys_layout.core.widen import measured_of, reserves_of

from .conftest import MARKER_BOX
from .cut_fixtures import AREA, chain, elem, free, net, page_of
from .pipeline_fixtures import blocks_of, cut_of, flow_of, placed_from, routed_from
from .place_fixtures import card_with_coils, wide_row
from .widen_fixtures import gap_width

PLAIN = Options(justify=False, marker=MARKER_BOX)


def three_columns() -> PlacementProblem:
    """Three separate two-element columns in one row."""
    names = [[f"{c}{k}" for k in range(2)] for c in "abc"]
    syms = tuple(elem(n) for col in names for n in col)
    nets = tuple(n for col in names for n in chain(col, prefix=col[0]))
    return PlacementProblem(AREA, syms, nets)


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
        pair = (
            next((g.left, g.right) for g in landed.pages[0].gaps) if landed.pages[0].gaps else None
        )
        if pair:
            assert place_pages(cut, prob, PLAIN, {pair: 1}) == landed


def test_a_reserve_of_two_widens_that_gap_by_one_grid_and_no_other() -> None:
    prob = three_columns()
    cut = cut_of(prob, PLAIN)
    base = place_pages(cut, prob, PLAIN)
    first = base.pages[0].gaps[0]
    wide = place_pages(cut, prob, PLAIN, {(first.left, first.right): 2})
    before, after = gaps(base.pages[0]), gaps(wide.pages[0])
    assert after[0][2] == before[0][2] + PLAIN.wiring_grid
    assert after[1:] == before[1:]


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
    return Measured(
        {}, {b.id: height for b in blocks}, {c: height for b in blocks for c in b.columns}
    )


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
    return PlacementProblem(Size(100, 854), syms, (net("feed", "t0.e", "k1.n", "k2.n", "k3.n"),))


def test_a_measured_height_over_the_page_moves_the_block_down_and_its_reference_follows() -> None:
    prob = replace(three_columns(), area=Size(70, 854))
    assert [len(p.rows) for p in recut(prob, None).spec.pages] == [3]
    assert [len(p.rows) for p in recut(prob, all_heights(prob, 300)).spec.pages] == [2, 1]
    legs = replace(fan_legs(), area=Size(124, 854))  # layout-0308: a row end holds a 48 G arrow
    assert page_of(recut(legs, None)) == {"c:k1": 1, "c:k2": 1, "c:k3": 1}
    moved = recut(legs, all_heights(legs, 300))
    assert page_of(moved) == {"c:k1": 1, "c:k2": 1, "c:k3": 2}
    assert moved.spec.reference_plan[-1] == Ref(
        "feed", RefKind.COPY, (RefEnd(2, "c:k1", PinRef("k3", "n")),)
    )


def two_heights() -> PlacementProblem:
    """Two columns in one row: a stack of two 150 G elements and a stack of two 60 G ones."""
    syms = (elem("a0", 16, 150), elem("a1", 16, 150), elem("b0", 16, 60), elem("b1", 16, 60))
    nets = (*chain(["a0", "a1"], "a"), *chain(["b0", "b1"], "b"))
    return PlacementProblem(AREA, syms, tuple(nets))


def test_measured_height_is_the_blocks_own_extent_never_its_rows() -> None:
    prob = two_heights()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    measured = measured_of(cut, placement, routed_from(cut, prob, PLAIN), PLAIN)
    feet = {
        p.sym: (p.footprint.y, p.footprint.y + p.footprint.h) for p in placement.pages[0].placed
    }
    own = {
        k: max(feet[s][1] for s in v) - min(feet[s][0] for s in v)
        for k, v in {"column:c:a0": ("a0", "a1"), "column:c:b0": ("b0", "b1")}.items()
    }
    row_height = placement.pages[0].rows[0][0]
    assert measured.heights["column:c:b0"] == own["column:c:b0"] < row_height
    assert measured.heights["column:c:a0"] == own["column:c:a0"]
    assert own["column:c:a0"] > own["column:c:b0"]


def fan_rows() -> PlacementProblem:
    """One fan block of five 40 x 32 legs 100 G wide: its legs stack in five rows."""
    syms = (free("t0"), *(elem(f"k{i}", 40, 32) for i in range(1, 6)))
    pins = ["t0.e", *(f"k{i}.n" for i in range(1, 6))]
    return PlacementProblem(Size(100, 854), syms, (net("feed", *pins),))


def test_a_columns_measured_height_is_its_own_never_its_blocks_so_its_rows_stay_on_a_page() -> None:
    prob = fan_rows()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    measured = measured_of(cut, placement, routed_from(cut, prob, PLAIN), PLAIN)
    block = measured.heights["fan:c:k1"]
    assert block > 300 > 2 * max(measured.columns.values())
    assert [measured.columns[f"c:k{i}"] for i in range(2, 6)] == [
        32 + HEIGHT_WIRES * PLAIN.wiring_grid
    ] * 4
    assert set(page_of(recut(prob, measured)).values()) == {1}
