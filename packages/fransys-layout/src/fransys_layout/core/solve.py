"""`solve`: the stages in the order of E11, from a problem to a CoreLayout (layout-0296)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .anchors import anchor_misses, reserved
from .blocks import assign_blocks
from .cut import cut_pages
from .fallback import announced, handed
from .order import order_blocks
from .outline import framed
from .outputs import CoreLayout
from .place import place_pages
from .row_measure import row_measures
from .solve_steps import annotate, scored
from .topology import build_flow
from .topology_elements import netted_pins
from .widen import route_round, widen

if TYPE_CHECKING:
    from .values import Options, PinRef, PlacementProblem

__all__ = ("solve",)


def solve(problem: PlacementProblem, options: Options) -> CoreLayout:
    """The layout of `problem`, laid again while hangings miss and it gains (H12).

    A hanging misses when its placed box meets a body, an outline or the frame. Only an anchor
    has a miss test so far: a card's anchored outline joins its footprint once an earlier layout
    left it missing, and a layout is kept only if fewer hangings miss.
    """
    problem = framed(problem, options)
    best, held = _solve(reserved(problem, options), options), frozenset[tuple[str, str]]()
    for _ in range(options.solve_rounds):
        gone = anchor_misses(best.placement, best.annotations.anchored, problem, options, best.annotations.markers)
        if not gone:
            break
        held |= {(a.sym, a.pin) for a, _ in gone}
        again = _solve(reserved(problem, options, held), options)
        after = anchor_misses(again.placement, again.annotations.anchored, problem, options, again.annotations.markers)
        if len(after) >= len(gone):
            break
        best = again
    return best


def _solve(problem: PlacementProblem, options: Options) -> CoreLayout:
    """Flow, blocks, order, cut, place, mark, route round the markers, widen, then text, score.

    `widen` cuts, places, marks and routes again once. Findings run in stage order.
    """
    problem = reserved(problem, options)
    flow = build_flow(problem, options)
    lists = order_blocks(assign_blocks(flow, problem, options), flow, options)
    cut = cut_pages(lists, flow, problem, options)
    placement = place_pages(cut, problem, options)
    cut, placement, rnd, problem, over = widen(cut, placement, route_round(cut, placement, problem, options), problem, options)
    markers, missed, routes = rnd.markers, rnd.missed, rnd.routes
    notes = replace(annotate(placement, markers, problem, options), annexes=routes.labels)
    found = (
        *flow.findings,
        *(f for bl in lists for f in bl.findings),
        *cut.spec.findings,
        *placement.findings,
        *routes.findings,
        *over,
        *missed,
        *announced((*handed(cut, placement, problem), *rnd.refs)),
    )
    layout = CoreLayout(
        problem.area,
        cut.spec.pages,
        placement,
        routes,
        notes,
        (*cut.spec.reference_plan, *rnd.refs),
        _wired(problem),
        None,
        found,
        cut.spec.drawn,
        row_measures(placement, cut, problem, options),
    )
    return scored(layout, problem, cut.flow)


def _wired(problem: PlacementProblem) -> frozenset[tuple[PinRef, str]]:
    """Each pin a lead or a wire reaches, with its net: a pin that only an anchored lead reaches has the empty net."""
    return frozenset({**{a.pin: "" for a in problem.anchors}, **netted_pins(problem)}.items())
