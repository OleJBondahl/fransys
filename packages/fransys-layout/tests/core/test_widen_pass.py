"""Stage 7 widen: the gap takes the wanted demand, the page is cut again, the references follow."""

from __future__ import annotations

import importlib
from dataclasses import replace

from fransys_layout.core import Box, Placement, PlacementProblem, Size
from fransys_layout.core.geometry import marker_box
from fransys_layout.core.outputs import Demand, Routes
from fransys_layout.core.text_markers import mark_pages
from fransys_layout.core.widen import measured_of, overflows, widen

from .conftest import MARKER, MARKER_BOX
from .pipeline_fixtures import cut_of, placed_from, routed_from, widened_of
from .test_widen import PLAIN, fan_legs, three_columns
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
    return (cut, placement, routes), widen(cut, placement, routes, prob, OPTS)


def crossings(routes: Routes) -> int:
    return sum(p.counts.crossings for p in routes.pages)


def test_two_nets_wanted_in_one_8_g_gap_widen_that_gap_by_one_grid_and_no_crossing() -> None:
    prob = three_columns()
    (_, before, routes), (_, after, routes2, found) = run(prob, demand=2)
    ids = [g.id for g in before.pages[0].gaps]
    assert gap_width(after, ids[1]) == gap_width(before, ids[1]) + GRID
    assert gap_width(after, ids[0]) == gap_width(before, ids[0])
    assert crossings(routes2) == crossings(routes) == 0
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
    prob = replace(fan_legs(), area=Size(124 + MARKER_BOX.w, 150))
    seen: list[tuple[int, tuple[Box, ...]]] = []
    real = widen_module.route_pages

    def spy(placement, cut, problem, options, obstacles=()):
        seen.append((placement.pages[0].page, tuple(obstacles)))
        return real(placement, cut, problem, options, obstacles)

    monkeypatch.setattr(widen_module, "route_pages", spy)
    _, (cut2, after, _, found) = run(prob, demand=2, gap=0)
    markers = mark_pages(cut2, after, prob, OPTS)
    want = {
        p.page: tuple(marker_box(m, OPTS) for m in markers if m.page == p.page) for p in after.pages
    }
    assert markers
    assert len(after.pages) == 2
    assert found == ()
    assert dict(seen[-2:]) == want


def test_a_page_over_its_room_gets_page_overflow_naming_page_overflow_and_fix() -> None:
    prob = overflowing_row()
    _, (_, after, _, found) = run(prob)
    assert [f.code for f in found] == ["PAGE_OVERFLOW"]
    assert found[0].page == 1
    assert f"{8 + 2 * OPTS.margin.w} G wide" in found[0].text
    assert "enlarge the page" in found[0].text
    assert len(after.pages) == 1


def test_a_page_the_placement_gave_too_tall_is_cut_again_into_room() -> None:
    prob = three_columns()
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    page = replace(placement.pages[0], bands=((16, 5000),))
    tall = Placement((page,), placement.findings)
    routes = routed_from(cut, prob, OPTS)
    _, after, _, found = widen(cut, tall, routes, prob, OPTS)
    assert after.pages[0].placed == placement.pages[0].placed
    assert overflows(after, prob, OPTS) == ()
    assert found == ()


def test_widen_returns_the_inputs_when_nothing_grew_and_nothing_overflows() -> None:
    prob = three_columns()
    (cut, placement, routes), out = run(prob)
    assert (out[0], out[2], out[3]) == (cut, routes, ())
    assert [p.placed for p in out[1].pages] == [p.placed for p in placement.pages]
    assert {g.tracks for p in out[1].pages for g in p.gaps} == {1}


def test_widen_twice_is_widen_once_on_the_planted_cases() -> None:
    for prob, demand in [(three_columns(), 2), (overflowing_row(), 0)]:
        _, once = run(prob, demand)
        assert widen(*once[:3], prob, OPTS) == once


def test_the_extent_of_a_fan_block_holds_its_trunk_and_lanes() -> None:
    prob = fan_legs()
    cut = cut_of(prob, OPTS)
    placement = placed_from(cut, prob, OPTS)
    routes = routed_from(cut, prob, OPTS)
    assert measured_of(cut, placement, routes, OPTS).heights["fan:c:k1"] == 224


def test_widened_of_runs_the_pipeline_to_stage_7() -> None:
    placement, routes, found = widened_of(three_columns(), OPTS)
    assert placement.pages
    assert routes.pages
    assert found == ()
