"""Run the stages on a problem: the one place stage tests build flow, cut, placement, routes."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Options, Placement, PlacementProblem, build_flow, order_blocks
lazy from fransys_layout.core.outputs import Routes

if TYPE_CHECKING:
    from fransys_layout.core import AnnexBox
    from fransys_layout.core.outputs import CoreLayout, WireLabel
    from fransys_layout.core.values import BlockList, CutResult, Finding, FlowGraph

from .conftest import MARKER


def flow_of(prob: PlacementProblem, options: Options | None = None) -> FlowGraph:
    """Stage 1 on a problem."""
    return build_flow(
        prob,
        options
        or core_options(
            marker=MARKER,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def blocks_of(prob: PlacementProblem, options: Options | None = None) -> tuple[BlockList, ...]:
    """Stages 1 and 2 on a problem; assign_blocks is imported late (it lands with stage 2)."""
    from fransys_layout.core.blocks import assign_blocks

    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    return assign_blocks(flow_of(prob, opts), prob, opts)


def cut_of(prob: PlacementProblem, options: Options | None = None) -> CutResult:
    """Stages 1 to 4 on a problem; cut_pages is imported late (it lands with stage 4)."""
    from fransys_layout.core.cut import cut_pages

    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
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
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    return placed_from(cut_of(prob, opts), prob, opts)


def routed_from(cut: CutResult, prob: PlacementProblem, opts: Options) -> Routes:
    """Stage 6 on a cut already made (a test may edit the cut first, e.g. Fan.crossed)."""
    from fransys_layout.core.route import route_pages

    return route_pages(placed_from(cut, prob, opts), cut, prob, opts)


def routed_of(prob: PlacementProblem, options: Options | None = None) -> Routes:
    """Stages 1 to 6 on a problem; route_pages is imported late (it lands with stage 6)."""
    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    return routed_from(cut_of(prob, opts), prob, opts)


def widened_of(
    prob: PlacementProblem, options: Options | None = None
) -> tuple[Placement, Routes, tuple[Finding, ...]]:
    """Stages 1 to 7 on a problem; widen is imported late (it lands with stage 7)."""
    from fransys_layout.core.route import route_pages
    from fransys_layout.core.widen import widen

    opts = options or core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = cut_of(prob, opts)
    placement = placed_from(cut, prob, opts)
    routes = route_pages(placement, cut, prob, opts)
    _, placement, routes, findings = widen(cut, placement, routes, prob, opts)
    return placement, routes, findings


def with_annexes(prob: PlacementProblem, options: Options) -> PlacementProblem:
    """The problem with el's designation annexes, one per symbol, as fransys_el builds them."""
    from fransys_el.placement_annexes import label_annexes

    return replace(prob, annexes=label_annexes(prob.symbols, options))


def labelled_of(
    prob: PlacementProblem, options: Options | None = None
) -> tuple[tuple[AnnexBox, ...], tuple[Finding, ...]]:
    """Stages 1 to 6 and 8a on a problem, then place_annexes on its designation annexes."""
    from fransys_layout.core import place_annexes
    from fransys_layout.core.outputs import Annotations
    from fransys_layout.core.route import route_pages
    from fransys_layout.core.text_markers import mark_pages

    opts = options or core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = cut_of(prob, opts)
    placement = placed_from(cut, prob, opts)
    routes = route_pages(placement, cut, prob, opts)
    markers = mark_pages(cut, placement, prob, opts)
    return place_annexes(
        placement, routes, Annotations(markers=markers), with_annexes(prob, opts), opts
    )


def wire_labelled_of(
    prob: PlacementProblem, options: Options | None = None
) -> tuple[tuple[WireLabel, ...], tuple[Finding, ...]]:
    """Stages 1 to 6, 8a and 8b, then label_nets; the stage modules are imported late."""
    from fransys_layout.core import place_annexes
    from fransys_layout.core.outputs import Annotations
    from fransys_layout.core.route import route_pages
    from fransys_layout.core.text_markers import mark_pages
    from fransys_layout.core.text_wires import label_nets

    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = cut_of(prob, opts)
    placement = placed_from(cut, prob, opts)
    routes = route_pages(placement, cut, prob, opts)
    markers = mark_pages(cut, placement, prob, opts)
    labelled = with_annexes(prob, opts)
    annexes, _ = place_annexes(placement, routes, Annotations(markers=markers), labelled, opts)
    notes = Annotations(markers=markers, annexes=annexes)
    return label_nets(placement, routes, notes, prob, opts)


def solved_of(prob: PlacementProblem, options: Options | None = None) -> CoreLayout:
    """The whole pipeline, `solve`, on a problem with its designation annexes; imported late."""
    from fransys_layout.core.solve import solve

    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    return solve(with_annexes(prob, opts), opts)
