"""Stage 7, widen: gaps take the tracks the router used, and the cut runs again (layout-0298).

The reserve of a gap is the wanted demand, the extent of a block is its solved span (layout-0374);
`widen` cuts again once with both, places, marks the references and routes around their boxes.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .anchors import anchor_pages
from .blocks import assign_blocks
from .cut import cut_pages
from .cut_costs import with_wires
from .cut_measured import Measured
from .geometry import marker_box
from .order import order_blocks
from .outputs import Placement, Routes
from .place import place_pages
from .route import route_pages
from .text_markers import placed_marks
from .topology import build_flow
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .outputs import Marker, PagePlacement
    from .values import BlockList, CutResult, FlowGraph, Options, PlacementProblem


def reserves_of(placement: Placement, routes: Routes) -> Mapping[tuple[str, str], int]:
    """Per column pair, the tracks its gap must hold: the larger of its tracks and the demand.

    The key is (Gap.left, Gap.right), never read from the gap id. Only pairs holding more than
    one track are listed; `RowSpec.reserves` turns each into grids.
    """
    demand = {d.gap: d.tracks for page in routes.pages for d in page.demand}
    out: dict[tuple[str, str], int] = {}
    for page in placement.pages:
        for gap in page.gaps:
            tracks = max(gap.tracks, demand.get(gap.id, 0))
            if tracks > 1:
                out[(gap.left, gap.right)] = tracks
    return out


def measured_of(cut: CutResult, placement: Placement, routes: Routes, options: Options) -> Measured:
    """The reserves, and the solved span of each block and of each column (layout-0374)."""
    return _spans_of(Measured(reserves_of(placement, routes)), cut, placement, options)


def _spans_of(
    measured: Measured, cut: CutResult, placement: Placement, options: Options
) -> Measured:
    """The measure with the spans of this placement, its reserves kept.

    Read off `PagePlacement.spans` alone: a column keeps its own span and the wires round it
    (as `item_height` counts), never its block's.
    """
    blocks = {b.id for lst in cut.blocks for b in lst.blocks}
    columns = {c.id for c in cut.flow.columns}
    heights: dict[str, int] = {}
    own: dict[str, int] = {}
    rises: dict[str, int] = {}
    for page in placement.pages:
        for key, (top, bottom) in page.spans.items():
            if key in blocks:
                heights[key] = bottom - top
                rises[key] = top
            if key in columns:
                own[key] = with_wires(bottom - top, options)
                rises[key] = top
    return Measured(measured.reserves, heights, own, rises)


def _grew(placement: Placement, routes: Routes) -> bool:
    """True when some gap is wanted wider than the tracks it holds (at least one)."""
    held = {g.id: max(g.tracks, 1) for page in placement.pages for g in page.gaps}
    return any(d.tracks > held.get(d.gap, 1) for page in routes.pages for d in page.demand)


def _counted(placement: Placement, reserves: Mapping[tuple[str, str], int]) -> Placement:
    """The placement with each gap's `tracks` set to what it now holds: its reserve, else one."""
    pages = tuple(
        replace(
            pg, gaps=tuple(replace(g, tracks=reserves.get((g.left, g.right), 1)) for g in pg.gaps)
        )
        for pg in placement.pages
    )
    return replace(placement, pages=pages)


def _over(page: PagePlacement, room_w: int, room_h: int) -> tuple[int, int]:
    """How far the page passes the room, in width and in height (both at most 0 when it fits)."""
    wide = max((w for _, w in page.rows), default=0) - room_w
    tops, bottoms = [t for t, _ in page.bands], [b for _, b in page.bands]
    return wide, (max(bottoms) - min(tops) if page.bands else 0) - room_h


def overflows(
    placement: Placement, problem: PlacementProblem, options: Options
) -> tuple[Finding, ...]:
    """PAGE_OVERFLOW for each page, in page order, whose rows or bands pass the page less margin."""
    room_w = problem.area.w - 2 * options.margin.w
    room_h = problem.area.h - options.page_headroom
    out = []
    for page in placement.pages:
        wide, tall = _over(page, room_w, room_h)
        if wide > 0 or tall > 0:
            by = f"{max(wide, 0)} G wide and {max(tall, 0)} G high"
            fix = "enlarge the page, split the unit or shorten the column"
            out.append(
                Finding("PAGE_OVERFLOW", f"page {page.page} is over by {by}: {fix}", page.page)
            )
    return tuple(out)


def _excess(placement: Placement, problem: PlacementProblem, options: Options) -> int:
    """The most any page passes the room in height, else 0."""
    room_w, room_h = problem.area.w - 2 * options.margin.w, problem.area.h - options.page_headroom
    return max((max(_over(pg, room_w, room_h)[1], 0) for pg in placement.pages), default=0)


def _short(cut: CutResult, placement: Placement) -> bool:
    """True when some row was cut shorter than the band the solve gave it (layout-0375)."""
    return any(
        row.height_est < bottom - top
        for plan, page in zip(cut.spec.pages, placement.pages, strict=True)
        for row, (top, bottom) in zip(plan.rows, page.bands, strict=True)
    )


def _attempt(
    lists: tuple[BlockList, ...],
    flow: FlowGraph,
    env: tuple[PlacementProblem, Options, Measured],
    lanes: int,
) -> tuple[CutResult, Placement]:
    """The cut with `lanes` more bottom headroom lanes than the options, placed with the options."""
    problem, options, measured = env
    less = replace(options, bottom_headroom_lanes=options.bottom_headroom_lanes + lanes)
    cut = cut_pages(lists, flow, problem, less, measured)
    return cut, _counted(place_pages(cut, problem, options, measured.reserves), measured.reserves)


def _lanes(
    lanes: int, excess: int, fresh: Measured, problem: PlacementProblem, options: Options
) -> int:
    """The headroom lanes for the next cut, never past the cap (R460).

    Never so many that the page falls under the tallest block that fits the page alone.
    """
    room = problem.area.h - options.page_headroom
    tallest = max((h for h in fresh.heights.values() if h <= room), default=0)
    want = lanes + -(-excess // options.wiring_grid)
    cap = max(lanes, (room - tallest) // options.wiring_grid)
    return min(want, cap)


def _recut(
    lists: tuple[BlockList, ...],
    flow: FlowGraph,
    problem: PlacementProblem,
    options: Options,
    measured: Measured,
) -> tuple[CutResult, Placement]:
    """Cut and place with the measures; a page still over is cut again with less room."""
    env = (problem, options, measured)
    lanes = 0
    cut, placed = _attempt(lists, flow, env, lanes)
    for _ in range(options.recut_rounds):
        excess = _excess(placed, problem, options)
        if not excess and not _short(cut, placed):
            break
        lanes = _lanes(
            lanes, excess, fresh := _spans_of(env[2], cut, placed, options), problem, options
        )
        if problem.area.h - options.page_headroom - lanes * options.wiring_grid <= 0:
            break  # no page height is left to cut into: the page stays over, PAGE_OVERFLOW names it
        env = (problem, options, fresh)
        again, replaced = _attempt(lists, flow, env, lanes)
        if again == cut:
            break  # the same cut as the round before: more lanes will not move it
        cut, placed = again, replaced
    return cut, placed


def marks(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options
) -> tuple[tuple[Marker, ...], tuple[Finding, ...]]:
    """The markers of the cut's plan and MARKER_UNPLACED; a page over the sheet gets none."""
    if overflows(placement, problem, options):
        return (), ()
    return placed_marks(cut, placement, problem, options)


def routed(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    markers: Sequence[Marker],
) -> Routes:
    """Stage 6 once per page, each with the boxes of that page's markers as obstacles."""
    parts = []
    for page in placement.pages:
        boxes = [marker_box(m, options) for m in markers if m.page == page.page]
        boxes += [
            a.outline
            for a in anchor_pages(Placement((page,)), problem, options)
            if a.page == page.page
        ]
        parts.append(route_pages(Placement((page,)), cut, problem, options, boxes))
    return Routes(
        tuple(p for r in parts for p in r.pages),
        tuple(n for r in parts for n in r.failed),
        tuple(f for r in parts for f in r.findings),
    )


def widen(
    cut: CutResult,
    placement: Placement,
    routes: Routes,
    problem: PlacementProblem,
    options: Options,
) -> tuple[CutResult, Placement, Routes, tuple[Finding, ...]]:
    """One pass: the reserves and measures cut again, placed, re-marked and routed around markers.

    With no gap grown and no page over, the inputs come back with the gap tracks filled.
    PAGE_OVERFLOW lists the pages still over after the pass; such a page gets no markers.
    """
    if not _grew(placement, routes) and not overflows(placement, problem, options):
        return cut, _counted(placement, reserves_of(placement, routes)), routes, ()
    measured = measured_of(cut, placement, routes, options)
    flow = build_flow(problem, options)
    lists = order_blocks(assign_blocks(flow, problem, options), flow, options)
    cut2, placement2 = _recut(lists, flow, problem, options, measured)
    over = overflows(placement2, problem, options)
    markers = marks(cut2, placement2, problem, options)[0]
    return cut2, placement2, routed(placement2, cut2, problem, options, markers), over
