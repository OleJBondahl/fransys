"""Run the stages on a problem: the one place stage tests build flow, cut, placement, routes."""

from __future__ import annotations

from fransys_layout.core import (
    BlockList,
    CutResult,
    FlowGraph,
    Options,
    Placement,
    PlacementProblem,
    Routes,
    build_flow,
    order_blocks,
)


def flow_of(prob: PlacementProblem, options: Options | None = None) -> FlowGraph:
    """Stage 1 on a problem."""
    return build_flow(prob, options or Options())


def blocks_of(prob: PlacementProblem, options: Options | None = None) -> tuple[BlockList, ...]:
    """Stages 1 and 2 on a problem; assign_blocks is imported late (it lands with stage 2)."""
    from fransys_layout.core.blocks import assign_blocks

    opts = options or Options()
    return assign_blocks(flow_of(prob, opts), prob, opts)


def cut_of(prob: PlacementProblem, options: Options | None = None) -> CutResult:
    """Stages 1 to 4 on a problem; cut_pages is imported late (it lands with stage 4)."""
    from fransys_layout.core.cut import cut_pages

    opts = options or Options()
    flow = flow_of(prob, opts)
    lists = order_blocks(blocks_of(prob, opts), flow, opts)
    return cut_pages(lists, flow, prob, opts)


def placed_from(cut: CutResult, prob: PlacementProblem, opts: Options) -> Placement:
    """Stage 5 on a cut already made, so a caller that needs the cut too runs stages 1 to 4 once."""
    from fransys_layout.core.place import place_pages

    return place_pages(cut, prob, opts)


def placed_of(prob: PlacementProblem, options: Options | None = None) -> Placement:
    """Stages 1 to 5 on a problem."""
    opts = options or Options()
    return placed_from(cut_of(prob, opts), prob, opts)


def routed_from(cut: CutResult, prob: PlacementProblem, opts: Options) -> Routes:
    """Stage 6 on a cut already made (a test may edit the cut first, e.g. Fan.crossed)."""
    from fransys_layout.core.route import route_pages

    return route_pages(placed_from(cut, prob, opts), cut, prob, opts)


def routed_of(prob: PlacementProblem, options: Options | None = None) -> Routes:
    """Stages 1 to 6 on a problem; route_pages is imported late (it lands with stage 6)."""
    opts = options or Options()
    return routed_from(cut_of(prob, opts), prob, opts)
