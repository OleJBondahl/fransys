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
    """`_hung`, laid again with each symbol whose row passes the page in its narrow view; a view once narrow stays (R2250)."""
    slim: frozenset[str] = frozenset()
    while True:
        laid = replace(problem, symbols=tuple(s.narrow if s.id in slim and s.narrow else s for s in problem.symbols)) if slim else problem
        layout = _hung(laid, options)
        more = _wide(layout, problem, options) - slim
        if not more:
            return replace(layout, narrow=slim)
        slim |= more


def _wide(layout: CoreLayout, problem: PlacementProblem, options: Options) -> frozenset[str]:
    """The symbols with a narrow view that stand in a row wider than the page: the figure PAGE_OVERFLOW reads."""
    room = layout.area.w - 2 * options.margin.w
    over = {d for m in layout.rows if m.width > room for d in m.devices}
    return frozenset(s.id for s in problem.symbols if s.narrow is not None and s.id in over)


def _hung(problem: PlacementProblem, options: Options) -> CoreLayout:
    """The layout of `problem`, laid again while hangings miss and it gains (H12).

    A hanging misses when its placed box meets a body, an outline or the frame; only an anchor has a miss test so far:
    its card's outline joins the footprint once a layout left it missing, and a layout is kept only if fewer miss.
    """
    best, held = _solve(reserved(problem), options), frozenset[tuple[str, str]]()
    for _ in range(options.solve_rounds):
        gone = anchor_misses(best.placement, best.annotations.anchored, problem, options, best.annotations.markers)
        if not gone:
            break
        held |= {(a.sym, a.pin) for a, _ in gone}
        again = _solve(reserved(problem, held), options)
        after = anchor_misses(again.placement, again.annotations.anchored, problem, options, again.annotations.markers)
        if len(after) >= len(gone):
            break
        best = again
    return best


def _solve(problem: PlacementProblem, options: Options) -> CoreLayout:
    """Flow, blocks, order, cut, place, mark, route round the markers, widen, then text, score.

    `widen` cuts, places, marks and routes again once. Findings run in stage order.
    """
    problem = framed(reserved(problem), options)
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
