"""Stage 7, widen: gaps take the tracks the router used, and the cut runs again (layout-0298).

The reserve of a gap is the wanted demand, the extent of a block is its solved span (layout-0374);
`widen` cuts again once with both, places, marks the references and routes around their boxes.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import count
from typing import TYPE_CHECKING, NamedTuple

from .anchors import anchor_leads, anchor_pages, page_keeps
from .arrow_reserve import block_reserves, keep_legs
from .blocks import assign_blocks
from .cut import cut_pages
from .cut_costs import with_wires
from .cut_measured import Measured, placed_rows
from .errors import CoreError
from .fallback import fallback
from .geometry import union
from .order import order_blocks
from .outputs import Demand, Placement, Refused, Routes
from .place import place_pages
from .route import route_pages
from .route_env import LostKey, lost_key
from .route_fixed import Laid, fixed_wires
from .route_labels import roomed
from .row_measure import page_rows
from .row_names import row_where
from .text_markers import placed_marks
from .topology import build_flow
from .values import Finding, g_text
from .widen_rounds import settled

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .annex_values import AnnexBox
    from .arrow_reserve import RowReserve
    from .flow_values import BlockList, CutResult, FlowGraph
    from .outputs import Marker, PagePlacement, RowMeasure
    from .route import RouteMemo
    from .route_fixed import Fixed
    from .values import Options, PinRef, PlacementProblem, Ref


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
    arrows = keep_legs(measured.arrows, block_reserves(cut, problem.annexes, options))
    return Measured(measured.reserves, heights, own, rises, arrows, placed_rows(measured.rows, cut, placement))


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


def _culprit(rows: Sequence[RowMeasure], *, tall: bool) -> int | None:
    """The page's row of the tallest `row_term` reach (the value `Drawing.rows` carries), or the widest row: the row a PAGE_OVERFLOW fix names."""
    return max((m.reach if tall else m.width, m.row) for m in rows)[1] if rows else None


def overflows(placement: Placement, cut: CutResult, problem: PlacementProblem, options: Options) -> tuple[Finding, ...]:
    """PAGE_OVERFLOW, the one home of the verdict: each page, in page order, whose rows or bands pass the page less margin."""
    room_w = problem.area.w - 2 * options.margin.w
    room_h = problem.area.h - options.page_headroom
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    columns = {c.id: c for c in cut.flow.columns}
    out = []
    for page, plan in zip(placement.pages, cut.spec.pages, strict=True):
        wide, tall = _over(page, room_w, room_h)
        if wide > 0 or tall > 0:
            rows = page_rows(page, plan, (blocks, columns, block_reserves(cut, problem.annexes, options)))
            row = _culprit(rows, tall=tall > 0)
            where = f"set {plan.unit or 'root'}, page {page.page}" if row is None else row_where(plan, row, blocks, columns)
            by = f"{g_text(max(wide, 0))} G wide and {g_text(max(tall, 0))} G high"
            msg = f"{where}: the page is over by {by}; enlarge the page, split the unit or shorten the column"
            out.append(Finding("PAGE_OVERFLOW", msg, page.page, None if row is None else plan.rows[row].blocks[0]))
    return tuple(out)


def _excess(placement: Placement, problem: PlacementProblem, options: Options) -> tuple[int, int]:
    """The most any page passes the room in height and in width, each else 0: the verdict `overflows` reads (R1876)."""
    room_w, room_h = problem.area.w - 2 * options.margin.w, problem.area.h - options.page_headroom
    over = [_over(pg, room_w, room_h) for pg in placement.pages]
    return max((max(h, 0) for _, h in over), default=0), max((max(w, 0) for w, _ in over), default=0)


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


def _keep(
    best: tuple[tuple[int, int], CutResult, Placement] | None, excess: tuple[int, int], cut: CutResult, placed: Placement
) -> tuple[tuple[int, int], CutResult, Placement]:
    """The attempt with the least excess in height and width, the latest among equals (R1714, R1876 i): a bounded loop's last iterate may be worse."""
    return (excess, cut, placed) if best is None or sum(excess) <= sum(best[0]) else best


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
        excess, wide = _excess(placed, problem, options)
        best = _keep(best, (excess, wide), cut, placed)
        if not excess and not wide:
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
    memo: RouteMemo | None = None


def routed(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    standing: Standing,
) -> Routes:
    """Stage 6 once per page, each with that page's marker and anchor keeps as obstacles."""
    anchored, found = anchor_pages(placement, problem, options)
    parts = []
    for page in placement.pages:
        keeps = page_keeps(page, standing.markers, anchored, problem, options)
        leads = anchor_leads(anchored)
        parts.append(
            route_pages(Placement((page,)), cut, problem, options, Laid(keeps, standing.fixed, standing.lost, standing.markers, leads, standing.memo))
        )
    return Routes(
        tuple(p for r in parts for p in r.pages),
        tuple(n for r in parts for n in r.failed),
        (*found, *(f for r in parts for f in r.findings)),
    )


class Round(NamedTuple):
    """What the loop leaves: the markers with their MARKER_UNPLACED findings and room demands.

    Also the routes, and the references of the lost conductors.
    """

    markers: tuple[Marker, ...]
    missed: tuple[Finding, ...]
    routes: Routes
    refs: tuple[Ref, ...]
    lost: tuple[Refused, ...] = ()
    asks: tuple[Demand, ...] = ()
    memo: RouteMemo | None = None


def _stand(
    cut: CutResult,
    placement: Placement,
    problem: PlacementProblem,
    options: Options,
    held: tuple[Mapping[LostKey, Refused], Sequence[AnnexBox], RouteMemo | None],
) -> Round:
    """One round of the loop: fixed wires, the references (planned and fallback) as markers, then labels and A* round their boxes (E11).

    `held` is what the rounds before left: the conductors lost, the labels, which do not move, and the page routes already made.
    """
    lost, labels, memo = held
    keys, refs = frozenset(lost), fallback(cut, placement, (*lost.values(), *(Refused(n, pair) for n, pair in cut.spec.unjoined)))
    fixed = {
        pg: f._replace(labels=tuple(a for a in labels if a.page == pg)) for pg, f in fixed_wires(placement, cut, problem, options, lost=keys).items()
    }
    planned = replace(cut, spec=replace(cut.spec, reference_plan=(*cut.spec.reference_plan, *refs)))
    markers, missed, asks = placed_marks(planned, placement, problem, options, fixed)
    return Round(
        markers, missed, routed(placement, cut, problem, options, Standing(markers, fixed, keys, memo)), refs, tuple(lost.values()), asks, memo
    )


def route_round(cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options, memo: RouteMemo | None = None) -> Round:
    """The routing and reference loop (R1222): round k routes what no earlier round lost; round k's losses stand as references in round k+1.

    It stops after the first round that loses nothing (R1245), or at `route_fallback_rounds`, where the
    last round's losses still become references (R1244).
    """
    lost: dict[LostKey, Refused] = {}
    labels: Sequence[AnnexBox] = ()
    memo = {} if memo is None else memo
    for _ in range(options.route_fallback_rounds):
        rnd = _stand(cut, placement, problem, options, (lost, labels, memo))
        new = {k: r for r in rnd.routes.failed if r.ends and (k := lost_key(r.net, r.ends)) not in lost}
        if not new:
            return rnd
        lost |= new
        labels = rnd.routes.labels
    return _stand(cut, placement, problem, options, (lost, labels, memo))


def tagged_by(problem: PlacementProblem, lost: Iterable[Refused]) -> PlacementProblem:
    """The problem whose nets hold each lost link as a tagged one (layout-0508): the cut plans its tag pair, placement reserves its room."""
    held = {n.id: set(n.tagged) for n in problem.nets}
    by_net: dict[str, list[tuple[PinRef, ...]]] = {}
    for r in lost:
        if r.ends and len(r.ends) > 1 and r.ends not in held.get(r.net, ()) and r.ends not in by_net.get(r.net, ()):
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
            if d.room:
                continue
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


def _asked(demands: Iterable[Demand], given: Mapping[tuple[str, str], Demand]) -> tuple[list[Demand], dict[tuple[str, str], Demand]]:
    """The room and rung boxes each owner is asked for, per side, beyond what an earlier pass gave (layout-0559, R1831, R1961)."""
    want: dict[tuple[str, str], Demand] = {}
    for d in demands:
        if d.owner and (d.room or d.box):
            old = want.get((d.owner, d.side), Demand("", 0, owner=d.owner, side=d.side))
            box = d.box if old.box is None or d.box is None else union(old.box, d.box)
            want[d.owner, d.side] = Demand("", 0, max(old.room, d.room), d.owner, box=box or old.box, side=d.side)
    asked = []
    for k, w in want.items():
        g = given.get(k, Demand("", 0, owner=k[0], side=k[1]))
        if w.room > g.room or (w.box is not None and w.box != g.box):
            asked.append(Demand("", 0, w.room - g.room if w.room > g.room else 0, k[0], box=w.box if w.box != g.box else None, side=k[1]))
    return asked, {**given, **want}


def _digits(placement: Placement, problem: PlacementProblem, risen: int) -> tuple[PlacementProblem, int]:
    """`problem` with the annexes for the digits of the page count, once they pass the `risen` reserved; digits only rise (R1883)."""
    rise = len(problem.wider[: len(str(len(placement.pages))) - 1])  # capped at the sets `wider` holds
    return (replace(problem, annexes=problem.wider[rise - 1]), rise) if rise > risen else (problem, risen)


def widen(
    cut: CutResult,
    placement: Placement,
    rnd: Round,
    problem: PlacementProblem,
    options: Options,
) -> tuple[CutResult, Placement, Round, PlacementProblem, tuple[Finding, ...]]:
    """Widen until a pass grants nothing new: cut again with the measures, place, re-mark, route.

    Each pass hands its lost links to the cut as `Net.tagged` (layout-0508); grants only grow, so the loop ends (R1967).
    With nothing to grow, no page over and no loss at the start, the inputs come back with the gap tracks filled.
    """
    over: tuple[Finding, ...] = ()
    held: dict[str | tuple[str, str], RowReserve] = {}
    roomed_for: dict[tuple[str, str], Demand] = {}
    risen = 0
    for i in count():
        problem, now = _digits(placement, problem, risen)
        rose, risen = now > risen, now
        asked, roomed_for = _asked((d for p in rnd.routes.pages for d in p.needs), roomed_for)
        problem2 = roomed(tagged_by(problem, rnd.lost), asked)
        marker_only = problem2 is problem and not rose and not _grew(placement, rnd.routes)  # a marker's ask is the last resort (layout-0559)
        if marker_only:
            asked, roomed_for = _asked(rnd.asks, roomed_for)
            problem2 = roomed(problem, asked)
        if i == 0 and problem2 is problem and not rose and not _grew(placement, rnd.routes) and not overflows(placement, cut, problem, options):
            return cut, _counted(placement, reserves_of(placement, rnd.routes)), rnd, problem, ()
        if settled(i, options, asked, quiet=problem2 is problem and not rose):
            break
        held = keep_legs(held, block_reserves(cut, problem.annexes, options))
        grown = _widened(cut, placement, rnd.routes, (problem2, options, held))
        if (
            marker_only and grown[2] and not overflows(placement, cut, problem, options)
        ):  # a room the page cannot hold is no room: the marker stays unplaced, the page does not overflow
            break
        cut, placement, over = grown
        problem, rnd = problem2, route_round(cut, placement, problem2, options, rnd.memo)
    return cut, placement, rnd, problem, over
