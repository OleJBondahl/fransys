"""Run the stages on a problem: the one place stage tests build flow, cut, placement, routes."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Options, Placement, PlacementProblem, Size, build_flow, order_blocks
lazy from fransys_layout.core.outputs import Routes

if TYPE_CHECKING:
    from fransys_layout.core import AnnexBox
    from fransys_layout.core.flow_values import BlockList, CutResult, FlowGraph
    from fransys_layout.core.outputs import CoreLayout
    from fransys_layout.core.values import Finding

from .conftest import MARKER


def flow_of(prob: PlacementProblem, options: Options | None = None) -> FlowGraph:
    """Stage 1 on a problem."""
    return build_flow(
        prob,
        options
        or core_options(
            marker=MARKER,
        ),
    )


def blocks_of(prob: PlacementProblem, options: Options | None = None) -> tuple[BlockList, ...]:
    """Stages 1 and 2 on a problem; assign_blocks is imported late (it lands with stage 2)."""
    from fransys_layout.core.blocks import assign_blocks

    opts = options or core_options(
        marker=MARKER,
    )
    return assign_blocks(flow_of(prob, opts), prob, opts)


def cut_of(prob: PlacementProblem, options: Options | None = None) -> CutResult:
    """Stages 1 to 4 on a problem; cut_pages is imported late (it lands with stage 4)."""
    from fransys_layout.core.cut import cut_pages

    opts = options or core_options(
        marker=MARKER,
    )
    flow = flow_of(prob, opts)
    lists = order_blocks(blocks_of(prob, opts), flow, opts)
    return cut_pages(lists, flow, prob, opts)


def placed_from(cut: CutResult, prob: PlacementProblem, opts: Options) -> Placement:
    """Stage 5 on a cut already made, so a caller that needs the cut too runs stages 1 to 4 once."""
    from fransys_layout.core.place import place_pages

    return place_pages(cut, prob, opts)


def placed_of(prob: PlacementProblem, options: Options | None = None) -> Placement:
    """Stages 1 to 5 on a problem."""
    opts = options or core_options(
        marker=MARKER,
    )
    return placed_from(cut_of(prob, opts), prob, opts)


def routed_from(cut: CutResult, prob: PlacementProblem, opts: Options) -> Routes:
    """Stage 6 on a cut already made (a test may edit the cut first)."""
    from fransys_layout.core.route import route_pages

    return route_pages(placed_from(cut, prob, opts), cut, prob, opts)


def routed_of(prob: PlacementProblem, options: Options | None = None) -> Routes:
    """Stages 1 to 6 on a problem; route_pages is imported late (it lands with stage 6)."""
    opts = options or core_options(
        marker=MARKER,
    )
    return routed_from(cut_of(prob, opts), prob, opts)


def widened_of(prob: PlacementProblem, options: Options | None = None) -> tuple[Placement, Routes, tuple[Finding, ...]]:
    """Stages 1 to 7 on a problem; widen is imported late (it lands with stage 7)."""
    from fransys_layout.core.route import route_pages
    from fransys_layout.core.widen import Round, widen

    opts = options or core_options()
    cut = cut_of(prob, opts)
    placement = placed_from(cut, prob, opts)
    routes = route_pages(placement, cut, prob, opts)
    _, placement, rnd, _, findings = widen(cut, placement, Round((), (), routes, ()), prob, opts)
    return placement, rnd.routes, findings


def with_annexes(prob: PlacementProblem, options: Options) -> PlacementProblem:
    """The problem with el's designation annexes, one per symbol and a 24 by 8 strip tag template per strip, as fransys_el builds them."""
    from fransys_el.placement_annexes import label_annexes

    tags = {s.row_group: {"": Size(24, 8)} for s in prob.symbols if s.row_group}
    return replace(prob, annexes=label_annexes(prob.symbols, options, "", tags))


def labelled_of(prob: PlacementProblem, options: Options | None = None) -> tuple[tuple[AnnexBox, ...], tuple[Finding, ...]]:
    """Stages 1 to 6 on a problem, the routing loop given its designation annexes: the labels it stood and its ANNEX_UNPLACED."""
    from fransys_layout.core.widen import route_round

    opts = options or core_options()
    cut = cut_of(prob, opts)
    rnd = route_round(cut, placed_from(cut, prob, opts), with_annexes(prob, opts), opts)
    return rnd.routes.labels, tuple(f for f in rnd.routes.findings if f.code == "ANNEX_UNPLACED")


def solved_of(prob: PlacementProblem, options: Options | None = None) -> CoreLayout:
    """The whole pipeline, `solve`, on a problem with its designation annexes; imported late."""
    from fransys_layout.core.solve import solve

    opts = options or core_options(
        marker=MARKER,
    )
    return solve(with_annexes(prob, opts), opts)
