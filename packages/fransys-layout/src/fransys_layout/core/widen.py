"""Stage 7, widen: gaps take the tracks the router used, and the cut runs again (layout-0298).

The reserve of a gap is the wanted demand, the extent of a block is its own symbols and trunks;
`widen` cuts again once with both, places, marks the references and routes around their boxes.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .blocks import assign_blocks
from .cut import cut_pages
from .cut_costs import with_wires
from .cut_measured import Measured
from .geometry import marker_box
from .order import order_blocks
from .outputs import Placement, Routes
from .place import place_pages
from .route import route_pages
from .text_markers import mark_pages
from .topology import build_flow
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .outputs import Marker, PagePlacement, Trunk
    from .values import Block, Column, CutResult, Options, PlacementProblem


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


def _column_syms(ids: Sequence[str], columns: Mapping[str, Column]) -> frozenset[str]:
    return frozenset(c.sym for col in ids for lane in columns[col].lanes for c in lane.cells)


def _block_syms(block: Block, columns: Mapping[str, Column]) -> frozenset[str]:
    return _column_syms(block.columns, columns) | frozenset((block.anchor,) if block.anchor else ())


def _extent(
    syms: frozenset[str], trunks: Sequence[Trunk], page: PagePlacement, grid: int
) -> int | None:
    """Own footprints (max bottom less min top), widened by the block's trunks and their lanes."""
    spans = [(p.footprint.y, p.footprint.y + p.footprint.h) for p in page.placed if p.sym in syms]
    spans += [(t.y - t.lanes * grid, t.y + t.lanes * grid) for t in trunks] if spans else []
    return max(b for _, b in spans) - min(a for a, _ in spans) if spans else None


def measured_of(cut: CutResult, placement: Placement, routes: Routes, options: Options) -> Measured:
    """The reserves, and the extent of each block (with its trunks) and of each column.

    A column's height is its own rows' extent and the wires round them (as `item_height` counts),
    never its block's. Needs the cut (the symbols) and the options (the grid) beside the placement.
    """
    columns = {c.id: c for c in cut.flow.columns}
    heights: dict[str, int] = {}
    own: dict[str, int] = {}
    for page in placement.pages:
        for block in (b for lst in cut.blocks for b in lst.blocks):
            trunks = [t for t in page.trunks if block.fan and t.fan == block.fan]
            grid = options.wiring_grid
            if (h := _extent(_block_syms(block, columns), trunks, page, grid)) is not None:
                heights[block.id] = h
            for col in block.columns:
                if (h := _extent(_column_syms([col], columns), [], page, grid)) is not None:
                    own[col] = with_wires(h, grid)
    return Measured(reserves_of(placement, routes), heights, own)


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
    room_h = problem.area.h - 2 * options.margin.h
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


def _routed(
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
    cut2 = cut_pages(lists, flow, problem, options, measured)
    placement2 = _counted(place_pages(cut2, problem, options, measured.reserves), measured.reserves)
    over = overflows(placement2, problem, options)
    markers = [] if over else mark_pages(cut2, placement2, problem, options)
    return cut2, placement2, _routed(placement2, cut2, problem, options, markers), over
