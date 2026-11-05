"""Stage 7, widen: gaps take the tracks the router used, and the cut runs again (layout-0298).

The reserve of a gap is the wanted demand, the extent of a block is its solved span (layout-0374);
`widen` cuts again once with both, places, marks the references and routes around their boxes.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

from .anchors import anchor_pages, page_keeps
from .arrow_reserve import block_reserves, keep_legs
from .blocks import assign_blocks
from .cut import cut_pages
from .cut_costs import with_wires
from .cut_measured import Measured
from .errors import CoreError
from .fallback import fallback
from .order import order_blocks
from .outputs import Demand, Placement, Refused, Routes
from .place import place_pages
from .route import route_pages
from .route_env import LostKey, lost_key
from .route_fixed import Laid, fixed_wires
from .text_markers import placed_marks
from .topology import build_flow
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from .annex_values import AnnexBox
    from .arrow_reserve import RowReserve
    from .flow_values import BlockList, CutResult, FlowGraph
    from .outputs import Marker, PagePlacement
    from .route_fixed import Fixed
    from .values import Options, PagePlan, PinRef, PlacementProblem, Ref


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


def measured_of(cut: CutResult, placement: Placement, routes: Routes, problem: PlacementProblem, options: Options) -> Measured:
    """The reserves, and the solved span of each block and of each column (layout-0374)."""
    return _spans_of(Measured(reserves_of(placement, routes)), cut, placement, (problem, options))


def _spans_of(measured: Measured, cut: CutResult, placement: Placement, env: tuple[PlacementProblem, Options]) -> Measured:
    """The measure with the spans and the row reserves of this cut and placement, its gap reserves kept.

    Read off `PagePlacement.spans` alone: a column keeps its own span and the wires round it
    (as `item_height` counts), never its block's.
    """
    problem, options = env
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
    return Measured(measured.reserves, heights, own, rises, keep_legs(measured.arrows, block_reserves(cut, problem.annexes, options)))


def _grew(placement: Placement, routes: Routes) -> bool:
    """True when some gap is wanted wider than the tracks it holds (at least one), a blocked label's need included."""
    held = {g.id: max(g.tracks, 1) for page in placement.pages for g in page.gaps}
    return any(d.tracks > held.get(d.gap, 1) for page in routes.pages for d in (*page.demand, *page.needs))


def _counted(placement: Placement, reserves: Mapping[tuple[str, str], int]) -> Placement:
    """The placement with each gap's `tracks` set to what it now holds: its reserve, else one."""
    pages = tuple(replace(pg, gaps=tuple(replace(g, tracks=reserves.get((g.left, g.right), 1)) for g in pg.gaps)) for pg in placement.pages)
    return replace(placement, pages=pages)


def _over(page: PagePlacement, room_w: int, room_h: int) -> tuple[int, int]:
    """How far the page passes the room, in width and in height (both at most 0 when it fits)."""
    wide = max((w for _, w in page.rows), default=0) - room_w
    tops, bottoms = [t for t, _ in page.bands], [b for _, b in page.bands]
    return wide, (max(bottoms) - min(tops) if page.bands else 0) - room_h


def _culprit(plan: PagePlan, page: PagePlacement, *, tall: bool) -> str | None:
    """The first block of the page's tallest (or widest) placed row: the block a PAGE_OVERFLOW fix names."""
    sizes = [b - t for t, b in page.bands] if tall else [w for _, w in page.rows]
    rows = [(size, row.blocks[0]) for size, row in zip(sizes, plan.rows, strict=False) if row.blocks]
    return max(rows)[1] if rows else None


def overflows(placement: Placement, cut: CutResult, problem: PlacementProblem, options: Options) -> tuple[Finding, ...]:
    """PAGE_OVERFLOW, the one home of the verdict: each page, in page order, whose rows or bands pass the page less margin."""
    room_w = problem.area.w - 2 * options.margin.w
    room_h = problem.area.h - options.page_headroom
    out = []
    for page, plan in zip(placement.pages, cut.spec.pages, strict=True):
        wide, tall = _over(page, room_w, room_h)
        if wide > 0 or tall > 0:
            by = f"{max(wide, 0)} G wide and {max(tall, 0)} G high"
            msg = f"page {page.page} is over by {by}: enlarge the page, split the unit or shorten the column"
            out.append(Finding("PAGE_OVERFLOW", msg, page.page, _culprit(plan, page, tall=tall > 0)))
    return tuple(out)


def _excess(placement: Placement, problem: PlacementProblem, options: Options) -> int:
    """The most any page passes the room in height, else 0."""
    room_w, room_h = problem.area.w - 2 * options.margin.w, problem.area.h - options.page_headroom
    return max((max(_over(pg, room_w, room_h)[1], 0) for pg in placement.pages), default=0)


def _wider(placement: Placement) -> bool:
    """True when the placer named a row wider than its page: the legs a cut makes stand are known only once it is placed (R1618)."""
    return any(f.code == "WIDER_THAN_PAGE" for f in placement.findings)


def _rows(cut: CutResult, placement: Placement) -> Iterator[tuple[int, int]]:
    """Each row's cut height and the band the solve gave it, in page and row order."""
    for plan, page in zip(cut.spec.pages, placement.pages, strict=True):
        for row, (top, bottom) in zip(plan.rows, page.bands, strict=True):
            yield row.height_est, bottom - top


def _short(cut: CutResult, placement: Placement) -> bool:
    """True when some row was cut shorter than the band the solve gave it (layout-0375)."""
    return any(cut_h < band for cut_h, band in _rows(cut, placement))


def _stale(cut: CutResult, placement: Placement, room_h: int) -> bool:
    """True when a row was cut taller than the page from a height the placement no longer holds.

    The measure came off the round before; a row that now stands within the page is cut again
    from its own height, or the cut names PAGE_OVERFLOW for a page that fits.
    """
    return any(band <= room_h < cut_h for cut_h, band in _rows(cut, placement))


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


def _lanes(lanes: int, excess: int, fresh: Measured, problem: PlacementProblem, options: Options) -> int:
    """The headroom lanes for the next cut, never past the cap (R460).

    Never so many that the page falls under the tallest block that fits the page alone.
    """
    room = problem.area.h - options.page_headroom
    tallest = max((h for h in fresh.heights.values() if h <= room), default=0)
    want = lanes + -(-excess // options.wiring_grid)
    cap = max(lanes, (room - tallest) // options.wiring_grid)
    return min(want, cap)


def _room(problem: PlacementProblem, options: Options) -> int:
    """The page height a cut may fill: the area less the headroom."""
    return problem.area.h - options.page_headroom


def _keep(best: tuple[int, CutResult, Placement] | None, excess: int, cut: CutResult, placed: Placement) -> tuple[int, CutResult, Placement]:
    """The attempt with the least excess, the latest among equals (R1714): a bounded loop's last iterate may be worse than an earlier one."""
    return (excess, cut, placed) if best is None or excess <= best[0] else best


def _recut(
    lists: tuple[BlockList, ...],
    flow: FlowGraph,
    problem: PlacementProblem,
    options: Options,
    measured: Measured,
) -> tuple[CutResult, Placement]:
    """Cut and place with the measures; a page still over is cut again with less room. Returns the least-excess attempt (R1714)."""
    lanes, best = 0, None
    cut, placed = _attempt(lists, flow, (problem, options, measured), lanes)
    for _ in range(options.recut_rounds):
        excess = _excess(placed, problem, options)
        best = _keep(best, excess, cut, placed)
        if not excess and not _short(cut, placed) and not _stale(cut, placed, _room(problem, options)) and not _wider(placed):
            break
        lanes = _lanes(lanes, excess, measured := _spans_of(measured, cut, placed, (problem, options)), problem, options)
        if _room(problem, options) - lanes * options.wiring_grid <= 0:
            break  # no page height is left to cut into: the page stays over, PAGE_OVERFLOW names it
        again, replaced = _attempt(lists, flow, (problem, options, measured), lanes)
        if again == cut:
            break  # the same cut as the round before: more lanes will not move it
        cut, placed = again, replaced
    else:
        best = _keep(best, _excess(placed, problem, options), cut, placed)
    return best[1], best[2]


class Standing(NamedTuple):
    """What stands before the A* round: the markers, the fixed wires of stage 6a, and the conductors withheld."""

    markers: Sequence[Marker]
    fixed: Mapping[int, Fixed]
    lost: frozenset[LostKey] = frozenset[LostKey]()


def routed(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    standing: Standing,
) -> Routes:
    """Stage 6 once per page, each with that page's marker and anchor keeps as obstacles."""
    anchored, found = anchor_pages(placement, problem, options, standing.markers)
    parts = []
    for page in placement.pages:
        keeps = page_keeps(page, standing.markers, anchored, problem, options)
        parts.append(route_pages(Placement((page,)), cut, problem, options, Laid(keeps, standing.fixed, standing.lost, standing.markers)))
    return Routes(
        tuple(p for r in parts for p in r.pages),
        tuple(n for r in parts for n in r.failed),
        (*found, *(f for r in parts for f in r.findings)),
    )


class Round(NamedTuple):
    """What the loop leaves: the markers with their MARKER_UNPLACED findings, the routes, and the references of the lost conductors."""

    markers: tuple[Marker, ...]
    missed: tuple[Finding, ...]
    routes: Routes
    refs: tuple[Ref, ...]
    lost: tuple[Refused, ...] = ()


def _stand(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options, held: tuple[Mapping[LostKey, Refused], Sequence[AnnexBox]]
) -> Round:
    """One round of the loop: fixed wires, the references (planned and fallback) as markers, then labels and A* round their boxes (E11).

    `held` is what the rounds before left: the conductors lost, and the labels, which do not move.
    """
    lost, labels = held
    keys, refs = frozenset(lost), fallback(cut, placement, (*lost.values(), *(Refused(n, pair) for n, pair in cut.spec.unjoined)))
    fixed = {
        pg: f._replace(labels=tuple(a for a in labels if a.page == pg)) for pg, f in fixed_wires(placement, cut, problem, options, lost=keys).items()
    }
    planned = replace(cut, spec=replace(cut.spec, reference_plan=(*cut.spec.reference_plan, *refs)))
    markers, missed = placed_marks(planned, placement, problem, options, fixed)
    return Round(markers, missed, routed(placement, cut, problem, options, Standing(markers, fixed, keys)), refs, tuple(lost.values()))


def route_round(cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options) -> Round:
    """The routing and reference loop (R1222): round k routes what no earlier round lost; round k's losses stand as references in round k+1.

    It stops after the first round that loses nothing (R1245), or at `route_fallback_rounds`, where the
    last round's losses still become references (R1244).
    """
    lost: dict[LostKey, Refused] = {}
    labels: Sequence[AnnexBox] = ()
    for _ in range(options.route_fallback_rounds):
        rnd = _stand(cut, placement, problem, options, (lost, labels))
        new = {k: r for r in rnd.routes.failed if r.ends and (k := lost_key(r.net, r.ends)) not in lost}
        if not new:
            return rnd
        lost |= new
        labels = rnd.routes.labels
    return _stand(cut, placement, problem, options, (lost, labels))


def tagged_by(problem: PlacementProblem, lost: Iterable[Refused]) -> PlacementProblem:
    """The problem whose nets hold each lost link as a tagged one (layout-0508): the cut plans its tag pair, placement reserves its room."""
    by_net: dict[str, list[tuple[PinRef, ...]]] = {}
    for r in lost:
        if r.ends and len(r.ends) > 1:
            by_net.setdefault(r.net, []).append(r.ends)
    if not by_net:
        return problem
    return replace(problem, nets=tuple(replace(n, tagged=(*n.tagged, *by_net[n.id])) if n.id in by_net else n for n in problem.nets))


def _floored(routes: Routes) -> Routes:
    """The routes with each page's label needs read as demands: the gap beside a blocked label is wanted as wide as the label (T6)."""
    pages = []
    for p in routes.pages:
        want: dict[str, int] = {}
        for d in (*p.demand, *p.needs):
            want[d.gap] = max(want.get(d.gap, 0), d.tracks)
        pages.append(replace(p, demand=tuple(Demand(g, t) for g, t in want.items())))
    return replace(routes, pages=tuple(pages))


def _widen_to(
    cut: CutResult, placement: Placement, routes: Routes, env: tuple[PlacementProblem, Options, Mapping[str | tuple[str, str], RowReserve]]
) -> tuple[CutResult, Placement]:
    """The re-cut with the measures of `routes`."""
    problem, options, held = env
    measured = measured_of(cut, placement, routes, problem, options)
    measured = replace(measured, arrows=keep_legs(held, measured.arrows))
    flow = build_flow(problem, options)
    lists = order_blocks(assign_blocks(flow, problem, options, measured.arrows), flow, options)
    return _recut(lists, flow, problem, options, measured)


def _widened(
    cut: CutResult,
    placement: Placement,
    routes: Routes,
    env: tuple[PlacementProblem, Options, Mapping[str | tuple[str, str], RowReserve]],
) -> tuple[CutResult, Placement, tuple[Finding, ...]]:
    """The re-cut, a blocked label's gap widened first (T6); a page that then no longer fits, or a row no pitch can hold, is cut without it.

    The label then stays ANNEX_UNPLACED, a finding naming it: a label never costs the page its fit.
    """
    problem, options, _ = env
    if any(p.needs for p in routes.pages):
        try:
            tried = _widen_to(cut, placement, _floored(routes), env)
        except CoreError:
            tried = None
        if tried and not overflows(tried[1], tried[0], problem, options):
            return (*tried, ())
    cut2, placement2 = _widen_to(cut, placement, routes, env)
    return cut2, placement2, overflows(placement2, cut2, problem, options)


def widen(
    cut: CutResult,
    placement: Placement,
    rnd: Round,
    problem: PlacementProblem,
    options: Options,
) -> tuple[CutResult, Placement, Round, PlacementProblem, tuple[Finding, ...]]:
    """Widen until a pass loses nothing, at most `recut_rounds` passes: cut again with the measures, place, re-mark, route.

    Each pass hands its round's lost links to the cut as `Net.tagged` (layout-0508); the losses left at the bound stay the fallback.
    With no gap grown, no page over and no loss at the start, the inputs come back with the gap tracks filled.
    """
    over: tuple[Finding, ...] = ()
    held: dict[str | tuple[str, str], RowReserve] = {}
    for i in range(options.recut_rounds):
        problem2 = tagged_by(problem, rnd.lost)
        if (
            i == 0
            and problem2 is problem
            and not _grew(placement, rnd.routes)
            and not overflows(placement, cut, problem, options)
            and not _wider(placement)
        ):
            return cut, _counted(placement, reserves_of(placement, rnd.routes)), rnd, problem, ()
        if i and problem2 is problem:
            break
        held = keep_legs(held, block_reserves(cut, problem.annexes, options))
        cut, placement, over = _widened(cut, placement, rnd.routes, (problem2, options, held))
        problem, rnd = problem2, route_round(cut, placement, problem2, options)
    return cut, placement, rnd, problem, over
