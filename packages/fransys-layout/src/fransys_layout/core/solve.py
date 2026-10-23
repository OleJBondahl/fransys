"""`solve`: the stages in the order of E11, from a problem to a CoreLayout (layout-0296)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .anchors import anchor_misses, reserved
from .blocks import assign_blocks
from .cut import cut_pages
from .order import order_blocks
from .outputs import CoreLayout
from .place import place_pages
from .solve_steps import annotate, route_round, scored
from .topology import build_flow
from .topology_elements import wired_pins
from .widen import marks, widen

if TYPE_CHECKING:
    from .values import Options, PlacementProblem

__all__ = ("solve",)


def solve(problem: PlacementProblem, options: Options) -> CoreLayout:
    """The layout of `problem`, laid again while a card's anchored outlines miss and it gains.

    A card's anchored outline joins its footprint only once an earlier layout left it meeting a
    body, an outline or the frame; a layout is kept only if fewer outlines miss.
    """
    best, held = _solve(reserved(problem), options), frozenset[tuple[str, str]]()
    for _ in range(options.solve_rounds):
        gone = anchor_misses(best.placement, best.annotations.anchored, problem, options)
        if not gone:
            break
        held |= {(a.sym, a.pin) for a, _ in gone}
        again = _solve(reserved(problem, held), options)
        after = anchor_misses(again.placement, again.annotations.anchored, problem, options)
        if len(after) >= len(gone):
            break
        best = again
    return best


def _solve(problem: PlacementProblem, options: Options) -> CoreLayout:
    """Flow, blocks, order, cut, place, mark, route round the markers, widen once, then text, score.

    `widen` cuts, places, marks and routes again once. Findings run in stage order.
    """
    problem = reserved(problem)
    flow = build_flow(problem, options)
    lists = order_blocks(assign_blocks(flow, problem, options), flow, options)
    cut = cut_pages(lists, flow, problem, options)
    placement = place_pages(cut, problem, options)
    routes = route_round(cut, placement, problem, options)[1]
    cut, placement, routes, over = widen(cut, placement, routes, problem, options)
    markers, missed = marks(cut, placement, problem, options)
    notes, text_found = annotate(placement, routes, markers, problem, options)
    found = (
        *flow.findings,
        *(f for bl in lists for f in bl.findings),
        *cut.spec.findings,
        *placement.findings,
        *routes.findings,
        *over,
        *missed,
        *text_found,
    )
    layout = CoreLayout(
        problem.area,
        cut.spec.pages,
        placement,
        routes,
        notes,
        cut.spec.reference_plan,
        frozenset(wired_pins(problem).items()),
        None,
        found,
    )
    return scored(layout, problem, cut.flow)
