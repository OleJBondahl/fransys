"""`solve` runs the stages in E11's order (layout-0296): IS.1 pure, IS.8 order, IS.9 trade."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

import fransys_layout.core.widen as widen_stage
from fransys_layout.core.route import route_pages
from fransys_layout.core.solve import solve
from fransys_layout.core.solve_steps import route_round
from fransys_layout.core.text_markers import mark_pages
lazy from fransys_layout.core import PlacementProblem

from . import text_fixtures
from .conftest import MARKER
from .cycle_fixtures import ring_problem
from .pipeline_fixtures import solved_of
from .solve_fixtures import ring_beside_a_tall_chain, tag_on_the_wire
from .test_invariants import check_marker_cells, check_trade

PLANTS = {
    "ring": ring_problem,
    "ring_beside_a_tall_chain": ring_beside_a_tall_chain,
    "tag_chain": text_fixtures.tag_chain,
    "copied_hub": text_fixtures.copied_hub,
    "unit_boundary_stubs": text_fixtures.unit_boundary_stubs,
}


@pytest.fixture(params=sorted(PLANTS))
def planted(request: pytest.FixtureRequest) -> PlacementProblem:
    return PLANTS[request.param]()


def test_solve_is_pure(planted: PlacementProblem) -> None:
    opts = core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    assert solve(planted, opts) == solve(planted, opts)


def test_a_routed_wire_passes_no_marker_cell_on_the_planted_problems(
    planted: PlacementProblem,
) -> None:
    layout = solved_of(planted)
    assert (
        check_marker_cells(
            layout.routes,
            layout.annotations.markers,
            core_options(
                marker=MARKER,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
        == []
    )


def test_the_wire_bends_round_a_planned_tag() -> None:
    prob, cut, placement, opts = tag_on_the_wire()
    bare = route_pages(placement, cut, prob, opts)
    marks = mark_pages(cut, placement, prob, opts)
    assert [m for m in marks if m.net == "x9"], "the plant plans a tag x9"
    # control: with no obstacle the routed wire runs through the tag's box, so the plant bites
    assert check_marker_cells(bare, marks, opts)
    markers, routes = route_round(cut, placement, prob, opts)
    assert markers == marks
    assert check_marker_cells(routes, markers, opts) == []
    assert {w.net for p in routes.pages for w in p.wires if w.kind == "routed"} == {"n3"}


def test_the_markers_are_marked_before_the_route_and_again_after_widen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    real_mark, real_route = widen_stage.placed_marks, widen_stage.route_pages

    def mark(*args: object) -> object:
        order.append("mark")
        return real_mark(*args)  # ty: ignore[invalid-argument-type] -- a spy forwards its arguments

    def route(*args: object) -> object:
        order.append("route")
        return real_route(*args)  # ty: ignore[invalid-argument-type] -- a spy forwards its arguments

    monkeypatch.setattr(widen_stage, "placed_marks", mark)
    monkeypatch.setattr(widen_stage, "route_pages", route)
    solved_of(ring_beside_a_tall_chain())
    assert order[:2] == ["mark", "route"]
    assert order[-1] == "mark"


def test_the_router_trades_as_the_scorer_does_on_the_defaults() -> None:
    assert (
        check_trade(
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            )
        )
        == []
    )


def test_the_trade_check_names_a_penalty_that_drifts() -> None:
    (msg,) = check_trade(
        core_options(
            crossing_penalty=1,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        )
    )
    assert "crossing_penalty" in msg
