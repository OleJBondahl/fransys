"""Stage 7 widen: the gap takes the wanted demand, the page is cut again, the references follow."""

from __future__ import annotations

import importlib
from dataclasses import replace
from itertools import pairwise

import pytest

from fransys_layout.core import Box, Placement, PlacementProblem, Size
from fransys_layout.core.cut_measured import Measured
from fransys_layout.core.flow_values import FlowGraph
from fransys_layout.core.geometry import marker_box
from fransys_layout.core.hangings import hung_keeps
from fransys_layout.core.occupancy import cells_between
from fransys_layout.core.outputs import Demand, Routes
from fransys_layout.core.route_fixed import fixed_wires
from fransys_layout.core.text_markers import placed_marks
from fransys_layout.core.widen import Round, Standing, measured_of, overflows, routed, widen

from .conftest import MARKER
from .pipeline_fixtures import cut_of, placed_from, routed_from, widened_of
from .route_fixtures import two_links_one_gap
from .test_widen import PLAIN, fan_legs, three_columns
from .text_fixtures import PLANTS
from .widen_fixtures import gap_width, overflowing_row

# the name `widen` in core is the function, so the module comes by name
widen_module = importlib.import_module("fransys_layout.core.widen")
OPTS = replace(PLAIN, marker=MARKER)
GRID = OPTS.wiring_grid


def run(prob: PlacementProblem, demand: int = 0, gap: int = 1):
    """Stages 1 to 6, the wanted demand of one gap planted as 2 links' worth, then widen."""
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    routes = routed_from(cut, prob, OPTS)
    if demand:
        gid = placement.pages[0].gaps[gap].id
        page = replace(routes.pages[0], demand=(Demand(gid, demand),))
        routes = replace(routes, pages=(page, *routes.pages[1:]))
    rnd = Round((), (), routes, ())
    cut2, placement2, rnd2, _, over = widen(cut, placement, rnd, prob, OPTS)
    return (cut, placement, rnd), (cut2, placement2, rnd2, over)


def crossings(routes: Routes) -> int:
    return sum(p.counts.crossings for p in routes.pages)


def test_two_nets_wanted_in_one_8_g_gap_widen_that_gap_by_one_grid_and_no_crossing() -> None:
    prob = three_columns()
    (_, before, rnd), (_, after, rnd2, found) = run(prob, demand=2)
    ids = [g.id for g in before.pages[0].gaps]
    assert gap_width(after, ids[1]) == gap_width(before, ids[1]) + GRID
    assert gap_width(after, ids[0]) == gap_width(before, ids[0])
    assert crossings(rnd2.routes) == crossings(rnd.routes) == 0
    assert [g.tracks for g in after.pages[0].gaps] == [1, 2]
    assert found == ()


def test_a_widened_row_that_no_longer_fits_puts_the_third_column_on_a_new_row() -> None:
    prob = replace(three_columns(), area=Size(96, 854))
    (_, before, _), (cut2, after, _, found) = run(prob, demand=2)
    assert [len(p.rows) for p in before.pages] == [1]
    assert [len(p.rows) for p in after.pages] == [2]
    assert [p.columns for p in cut2.spec.pages[0].rows] == [("c:a0", "c:b0"), ("c:c0",)]
    assert found == ()


def test_a_page_too_short_for_the_widened_block_gets_a_second_page() -> None:
    prob = replace(three_columns(), area=Size(96, 128))
    (_, before, _), (_, after, _, found) = run(prob, demand=2)
    assert (len(before.pages), len(after.pages)) == (1, 2)
    assert found == ()


def test_the_re_mark_passes_the_marker_boxes_of_the_re_cut_to_the_router(monkeypatch) -> None:
    prob = replace(fan_legs(), area=Size(184, 120))  # a row end holds a 56 G arrow reserve (R1362): 120 high holds the tag and the copy
    seen: list[tuple[int, tuple[Box, ...]]] = []
    real = widen_module.route_pages

    def spy(placement, cut, problem, options, laid):
        seen.append((placement.pages[0].page, tuple(k.box for k in laid.keeps)))
        return real(placement, cut, problem, options, laid)

    monkeypatch.setattr(widen_module, "route_pages", spy)
    _, (cut2, after, _, found) = run(prob, demand=2, gap=0)
    markers = placed_marks(cut2, after, prob, OPTS, fixed_wires(after, cut2, prob, OPTS))[0]
    want = {p.page: (*(marker_box(m, OPTS) for m in markers if m.page == p.page), *(k.box for k in hung_keeps(p.hangings))) for p in after.pages}
    assert markers
    assert len(after.pages) == 2
    assert found == ()
    assert dict(seen[-2:]) == want


def test_a_page_over_its_room_gets_page_overflow_naming_page_overflow_and_fix() -> None:
    prob = overflowing_row()
    _, (cut2, after, _, found) = run(prob)
    assert [f.code for f in found] == ["PAGE_OVERFLOW"]
    assert found[0].page == 1
    assert found[0].subject == cut2.blocks[0].blocks[0].id
    assert f"{8 + 2 * OPTS.margin.w} G wide" in found[0].text
    assert "enlarge the page" in found[0].text
    assert found[0].text.startswith(f"{'set ' + cut2.spec.pages[0].unit + ', ' if cut2.spec.pages[0].unit else ''}page 1, row 0 (devices ")
    assert len(after.pages) == 1


def test_a_page_the_placement_gave_too_tall_is_cut_again_into_room() -> None:
    prob = three_columns()
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    page = replace(placement.pages[0], bands=((16, 5000),))
    tall = Placement((page,), placement.findings)
    routes = routed_from(cut, prob, OPTS)
    cut2, after, _, _, found = widen(cut, tall, Round((), (), routes, ()), prob, OPTS)
    assert after.pages[0].placed == placement.pages[0].placed
    assert overflows(after, cut2, prob, OPTS) == ()
    assert found == ()


def test_widen_returns_the_inputs_when_nothing_grew_and_nothing_overflows() -> None:
    prob = three_columns()
    (cut, placement, rnd), out = run(prob)
    assert (out[0], out[2], out[3]) == (cut, rnd, ())
    assert [p.placed for p in out[1].pages] == [p.placed for p in placement.pages]
    assert {g.tracks for p in out[1].pages for g in p.gaps} == {1}


def test_widen_twice_is_widen_once_on_the_planted_cases() -> None:
    for prob, demand in [(three_columns(), 2), (overflowing_row(), 0)]:
        _, once = run(prob, demand)
        again = widen(*once[:3], prob, OPTS)
        assert (*again[:3], again[4]) == once


def test_the_extent_of_a_fan_block_holds_its_trunk_and_lanes() -> None:
    prob = fan_legs()
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    routes = routed_from(cut, prob, OPTS)
    assert measured_of(cut, placement, routes, prob, OPTS).heights["fan:c:k1"] == 248


def test_widened_of_runs_the_pipeline_to_stage_7() -> None:
    placement, routes, found = widened_of(three_columns(), OPTS)
    assert placement.pages
    assert routes.pages
    assert found == ()


def test_an_over_page_keeps_its_markers_and_a_cross_page_pair_both_ends() -> None:
    prob = PLANTS["page_wrapped_fan"]()
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    tall = Placement((placement.pages[0], replace(placement.pages[1], bands=((16, 5000),))), placement.findings)
    assert [f.page for f in overflows(tall, cut, prob, OPTS)] == [2]
    fixed = fixed_wires(tall, cut, prob, OPTS)
    assert sorted(m.page for m in placed_marks(cut, tall, prob, OPTS, fixed)[0]) == [1, 2]


def test_the_recut_keeps_reserved_a_leg_that_an_earlier_plan_stood(monkeypatch) -> None:
    """R1673: the arrows the re-cut reads hold the legs of the plan before and of the plan now, never only the plan now."""
    from fransys_layout.core.arrow_reserve import RowReserve

    plans = iter([{("b", "c1"): RowReserve(legs=(("f", 20),), tail=4)}, {("b", "c2"): RowReserve(legs=(("f", 20),), tail=4)}] * 8)
    monkeypatch.setattr(widen_module, "block_reserves", lambda *_: next(plans))
    seen = []
    real = widen_module._recut
    monkeypatch.setattr(widen_module, "_recut", lambda *a: (seen.append(a[4].arrows), real(*a))[1])
    run(three_columns(), demand=2)
    assert {col for _, col in seen[0]} == {"c1", "c2"}


@pytest.mark.rule("ROUTING")
def test_a_routed_wire_never_runs_through_a_hanging_the_placement_holds() -> None:
    """layout-0547: the hangings of `PagePlacement` are obstacles of stage 6b, so the wire that crossed the box goes round."""
    prob = two_links_one_gap()
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    standing = Standing((), fixed_wires(placement, cut, prob, OPTS), frozenset())
    free = [w for w in routed(placement, cut, prob, OPTS, standing).pages[0].wires if w.kind == "routed"]
    (x0, y0), (x1, y1) = free[0].points[0], free[0].points[-1]
    left = -(-(min(x0, x1) + GRID) // GRID) * GRID  # the hanging stands on whole cells, as the keeps do (the pins sit off the grid)
    box = Box(left, min(y0, y1) - GRID, abs(x1 - x0) // 2 // GRID * GRID, abs(y1 - y0) + 2 * GRID)
    held = replace(placement, pages=(replace(placement.pages[0], hangings={"HOLDER": (box,)}), *placement.pages[1:]))
    wires = [w for w in routed(held, cut, prob, OPTS, standing).pages[0].wires if w.kind == "routed"]
    inside = {(i, j) for i in range(box.x // GRID, (box.x + box.w) // GRID + 1) for j in range(box.y // GRID, (box.y + box.h) // GRID + 1)}
    assert {c for w in free for a, b in pairwise(w.points) for c in cells_between(a, b, GRID)} & inside
    assert not {c for w in wires for a, b in pairwise(w.points) for c in cells_between(a, b, GRID)} & inside


def test_the_recut_returns_the_least_excess_attempt_the_latest_among_equals(monkeypatch) -> None:
    """R1714: attempts of excess 0, 9, 0, 142 return the third, never the last iterate of the bounded loop."""
    attempts = iter([(f"cut{i}", f"placed{i}") for i in range(4)])
    excess = {"placed0": 0, "placed1": 9, "placed2": 0, "placed3": 142}
    monkeypatch.setattr(widen_module, "_attempt", lambda *_: next(attempts))
    monkeypatch.setattr(widen_module, "_excess", lambda placed, *_: excess[placed])
    monkeypatch.setattr(widen_module, "_short", lambda *_: True)
    monkeypatch.setattr(widen_module, "_spans_of", lambda *_: None)
    monkeypatch.setattr(widen_module, "_lanes", lambda lanes, *_: lanes + 1)
    options = replace(OPTS, recut_rounds=3)
    assert widen_module._recut((), FlowGraph((), (), (), (), ()), three_columns(), options, Measured()) == ("cut2", "placed2")
