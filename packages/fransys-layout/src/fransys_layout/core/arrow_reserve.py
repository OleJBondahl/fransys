"""The arrow reserve: a row end that holds a planned arrow keeps `Options.marker.w` free beyond it.

One home for the number. Stage 4 widens a row's size with it; stage 5 widens the row's extent and
the arrow's fan span with it. A row end without an arrow reserves nothing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from itertools import count, takewhile
from typing import TYPE_CHECKING

from .band import arrow_box, arrow_hang, lane_line, lane_offset, lane_rows, trunk_room
from .clearance import Keep, clear
from .cut_costs import item_height
from .cut_end_rooms import arrow_ends, arrow_room, cut_ends, stub_room
from .errors import CoreError
from .geometry import inside, marker_box_at, stub_views
from .ref_kind import kind_of
from .values import Box, RefKind, StandClass

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .annex_values import Annex
    from .flow_values import Block, CutResult, Fan
    from .outputs import Placed, Trunk
    from .values import XY, Options, PagePlan, PinRef, Ref, Size

    ArrowEnds = Mapping[tuple[int, str, int], tuple[tuple[int, tuple[PinRef, str]], ...]]  # (page, fan, row) -> (pole, key) of each right cut end


@dataclass(frozen=True, slots=True)
class RowReserve:
    """What a block's planned row keeps free: `x` beyond its row ends, `y` about its anchor for the annexes it owns (R1129).

    A column's own entry holds `legs` (each fan's x for its legs there) and `tail` (the last leg's overhang): a row adds the legs of a fan's columns.
    """

    x: int = 0
    y: int = 0
    legs: tuple[tuple[str, int], ...] = ()
    tail: int = 0


def reserve_x(reserves: Mapping[str | tuple[str, str], RowReserve], block: str, column: str | None = None) -> int:
    """The x the row of `column` of `block` keeps free, else the block's; 0 with no entry (the first round, or no arrow at its ends)."""
    key = (block, column) if column is not None and (block, column) in reserves else block
    return reserves[key].x if key in reserves else 0


def reserve_y(reserves: Mapping[str | tuple[str, str], RowReserve], block: str, column: str) -> int:
    """The y the row of `column` of `block` keeps free for the stub boxes at its trunk end; 0 with no entry (R1634)."""
    return reserves[block, column].y if (block, column) in reserves else 0


def legs_x(arrows: Mapping[str | tuple[str, str], RowReserve], block: str, columns: Iterable[str]) -> int:
    """The x the legs of `columns` of `block` take in one row: their legs added, and the widest last-leg overhang (R1618).

    The one sum the cut's row size and its wrap test both read; the placed row's exact figure is `row_legs`.
    """
    parts = [arrows[k] for c in columns if (k := (block, c)) in arrows]
    fans = Counter[str]()
    for p in parts:
        for fan, x in p.legs:
            fans[fan] += x
    return max(fans.values(), default=0) + max((p.tail for p in parts), default=0)


def keep_legs(
    held: Mapping[str | tuple[str, str], RowReserve], fresh: Mapping[str | tuple[str, str], RowReserve]
) -> dict[str | tuple[str, str], RowReserve]:
    """`fresh` with the legs of every column in `held` kept: each fan's x and the tail only grow across rounds (R1673).

    A pin that stood a leg in an earlier plan may stand none in the next and one again after; the reserve follows the larger, so the rounds end.
    """
    out = dict(fresh)
    for key, was in held.items():
        if was.legs:
            now = out.get(key, RowReserve())
            legs = dict(was.legs)
            legs |= {fan: max(x, legs.get(fan, 0)) for fan, x in now.legs}
            out[key] = replace(now, legs=tuple(legs.items()), tail=max(now.tail, was.tail))
    return out


def reserve(arrows: int, options: Options) -> int:
    """The x kept beyond a row end that holds `arrows` planned arrows."""
    if not arrows:
        return 0
    if options.marker is None:
        msg = "arrow reserve: Options.marker is unset; pass the marker symbol keepout box"
        raise CoreError(msg)
    return (options.link_fit or options.marker)["R0"].w


def lead_reserve(arrows: int, options: Options) -> int:
    """The `reserve` of a row end plus the grid step the walk leaves clear of a footprint (R1362); the right end holds it as the left does."""
    return reserve(arrows, options) + options.wiring_grid * bool(arrows)


def leg_rows(refs: Iterable[Ref], page: int) -> dict[PinRef, int]:
    """Each one-sided pin whose leg stands on `page`, with the row of the trunk end its leg leaves (ONE-SIDED-PIN)."""
    return {
        e.pin: e.row
        for r in refs
        if kind_of(r) is RefKind.STUB
        for e in r.ends
        if e.pin and e.row is not None and e.stand is StandClass.LEG and e.page == page
    }


def leg_fit(options: Options, refs: Iterable[Ref], page: int) -> Options:
    """`options` with the box of each stub whose leg stands on `page` sized for the lines its ledger end holds: what a leg reads (R1598)."""
    fit = {
        (e.pin, str(RefKind.STUB)): views
        for r in refs
        if kind_of(r) is RefKind.STUB
        for e in r.ends
        if e.pin and e.row is not None and e.stand is StandClass.LEG and e.page == page
        if (views := stub_views(options.stub_lines, options.stub_table, e.pin, e.also, e.far))
    }
    return replace(options, marker_fit={**options.marker_fit, **fit}) if fit else options


def arrow_rows(refs: Iterable[Ref], plans: Iterable[PagePlan], fans: Iterable[Fan]) -> ArrowEnds:
    """Each page, fan and row whose trunk stands a cut end at its right end, with each end's (pole, key) (R875)."""
    refs, fans = tuple(refs), tuple(fans)
    ats = {(e.page, f.id) for r in refs for f in fans if r.net in (f.id, *f.nets) for e in r.ends}
    return {
        (p.page, f.id, row): ends
        for p in plans
        for f in fans
        if (p.page, f.id) in ats
        for row in range(len(p.rows))
        if (ends := tuple((c.lead, (c.key[0], c.key[1])) for c in cut_ends(refs, p, (f,), row) if c.right and c.key[0] is not None))
    }


def leg_pins(fan: Fan, rows: Mapping[PinRef, int], row: int, column: str | None = None) -> tuple[tuple[int, PinRef], ...]:
    """Each one-sided pin of `fan` (of `column`, when given) that stands a leg at this row's trunk end, with its lane: one leg a pin (R1235)."""
    return tuple((a.pole, a.pin) for a in (*fan.drivers, *fan.legs) if rows.get(a.pin) == row and column in (None, a.column))


def leg_depth(fan: Fan, rows: Mapping[PinRef, int], row: int, options: Options, arrow: int = 0) -> int:
    """The y a row holds under its trunk band: the tallest leg marker or the `arrow` room hung past the band, whichever is deeper (R1719).

    The marker and the arrow hang in the same space, so they combine as a max, never a sum.
    """
    heights = [marker_box_at(0, 0, options, options.marker_facing["S"], (pin, str(RefKind.STUB))).h for _, pin in leg_pins(fan, rows, row)]
    return max(*heights, arrow_hang(fan.lanes, options.wiring_grid, arrow), 0)


def leg_unit(legs: Sequence[tuple[int, PinRef]], options: Options) -> int:
    """The x the legs of one trunk end take: each its marker width and one grid; the arrow steps out by it (R903)."""
    widths = [marker_box_at(0, 0, options, options.marker_facing["S"], (pin, str(RefKind.STUB))).w for _, pin in legs]
    return (max(widths) + options.wiring_grid) * len(legs) if widths else 0


def leg_offsets(legs: Sequence[tuple[int, PinRef]], options: Options) -> dict[int, int]:
    """Per leg index, the x its start takes past `leg_cut`: (rank+1) units, the rank counted by (pole, index) (R1454)."""
    step = leg_unit(legs, options) // len(legs) if legs else 0
    return {j: (sum(1 for i, (q, _) in enumerate(legs) if (q, i) < (p, j)) + 1) * step for j, (p, _) in enumerate(legs)}


def legged_offsets(legs: Sequence[tuple[int, PinRef]], options: Options) -> dict[int, int]:
    """Per pole that stands legs, the offset past `leg_cut` of its last leg's start: where its lane ends (R1684)."""
    return {legs[j][0]: o for j, o in leg_offsets(legs, options).items()}


def leg_hull(trunk: Trunk, reach: int) -> int:
    """The x of the trunk end's last tap: the hull for a many-lane trunk, the arrow's step-out `reach` back for a one-lane one."""
    return trunk.x1 if len(trunk.lane_ends) > 1 else trunk.x1 - reach


def step_out(hull: int, grid: int) -> int:
    """The common step-out of the lanes that stand legs: one `grid` past the trunk end's hull; the x every leg leaves from (BUNDLE-LANE-END)."""
    return hull + grid


def leg_cut(trunk: Trunk, legs: Sequence[tuple[int, PinRef]], reach: int, grid: int) -> int:
    """The one x every leg of a trunk end leaves from: the largest end of the lanes that stand legs, else the last tap (`leg_hull`).

    A lane that stands the arrow ends past the legs' room (BUNDLE-LEGS: the arrow's box after the last leg drop), so its end
    counts as the lanes' common step-out, one `grid` past the hull: the legs never leave from the arrow's own end.
    """
    hull = leg_hull(trunk, reach)
    ends = [min(e[1], step_out(hull, grid)) for q, _ in legs if (e := trunk.lane_ends[q])] if len(trunk.lane_ends) > 1 else []
    return max(ends) if ends else hull


def _clear(c: int, mark: Box, start: XY, room: tuple[Sequence[Keep], frozenset[int], Size | None]) -> bool:
    """True when a leg dropping at x `c` with its marker box `mark` is inside `room` = (keeps, drop xs of its trunk, page) and meets none."""
    keeps, drops, area = room
    y = start[1]
    if (area is not None and not inside(mark, area)) or c in drops or any(mark.x < d < mark.x + mark.w for d in drops):
        return False
    probes = (mark, Box(start[0], y, c - start[0], 0), Box(c, y, 0, mark.y - y))
    return not any(clear(p, keeps, {}, edge="open") for p in probes)


def _arrow_keeps(trunk: Trunk, lines: Sequence[Trunk], arrowed: ArrowEnds, options: Options) -> list[Keep]:
    """The drawn box of every other fan's arrow at the right end of its lane, where the marker stage stands it (R1514)."""
    side = options.arrow_sides[0]
    out: list[Keep] = []
    for t in lines:
        for pole, key in () if t.fan == trunk.fan else arrowed.get((t.page, t.fan, t.row), ()):
            x0, x1, y, stood = lane_line(t, pole, t.lanes, options.wiring_grid)
            if stood[side == "E"]:
                out.append(Keep("", arrow_box(options, side, x1 if side == "E" else x0, y, key), "marker", t.fan))
    return out


def _lane_y(trunk: Trunk, grid: int, pole: int | None = None) -> int:
    """The y of lane `pole` of a trunk's lane ends, the lowest lane with none; the trunk's own y when it has one lane."""
    if len(trunk.lane_ends) <= 1:
        return trunk.y
    rows = lane_rows(trunk.lane_ends)
    return trunk.y + lane_offset(max(rows) if pole is None else rows[pole], grid)


def leg_line(
    trunk: Trunk,
    leg: int,
    legs: Sequence[tuple[int, PinRef]],
    options: Options,
    around: tuple[Sequence[Box], Sequence[Box], ArrowEnds, Sequence[Trunk], Size | None] = ((), (), {}, (), None),
) -> tuple[XY, XY, XY] | None:
    """The leg `leg` of `legs` (one a pin), on its lane: out from the cut x, then down below the bundle to its marker (ONE-SIDED-PIN).

    Leg k starts at `leg_cut` + (k+1) units (R1454); `around` is (footprints and hangings, placed legs' boxes, arrowed, trunks, page).
    The run is clear of a footprint's pin tips (gap 0); the stand is the first x past cut + (rank+1)*unit clear of all (R1299, R1465, R887).
    """
    feet, placed, arrowed, lines, area = around
    span, grid = leg_unit(legs, options), options.wiring_grid
    pole, pin = legs[leg]
    reach = (grid + span) * ((trunk.page, trunk.fan, trunk.row) in arrowed)
    others = (
        legged_offsets(legs, options).keys() - {pole} - {p for p, _ in arrowed.get((trunk.page, trunk.fan, trunk.row), ())}
    )  # lanes that end at their leg
    cut = leg_cut(trunk, legs, reach, grid)
    end, y = (trunk.lane_ends[pole] or (0, cut))[1] if len(trunk.lane_ends) > 1 else cut, _lane_y(trunk, grid, pole)
    x = cut + leg_offsets(legs, options)[leg]
    low = _lane_y(trunk, grid) + grid
    box = marker_box_at(0, 0, options, options.marker_facing["S"], (pin, str(RefKind.STUB)))
    cells = [Keep("", f, "foot", "") for f in feet]
    room = (
        [
            *cells,
            *(Keep("", f, "foot", "") for f in placed),
            *(Keep("", Box(t.x0 - 1, t.y - 1, t.x1 - t.x0 + 2, 2), "foot", "") for t in lines if t.fan != trunk.fan and y < t.y <= low),
            *_arrow_keeps(trunk, lines, arrowed, options),
        ],
        frozenset(
            d for i, e in enumerate(trunk.lane_ends) if e for d in e if not reach or d <= leg_hull(trunk, reach) or i in others
        ),  # an arrow's step-out is no drop; another legged lane's end is one (R1684)
        area,
    )
    runs = takewhile(
        lambda c: not clear(Box(min(end, c), y, c - min(end, c), 0), cells, {}), range(x, area.w) if area else count(x)
    )  # a wire run: a foot's pin tip on it ends the search (ONE-SIDED-PIN)
    x = next((c for c in runs if _clear(c, Box(c + box.x, low, box.w, box.h), (min(end, c), y), room)), None)
    return (
        None
        if x is None
        else ((trunk.x1 if len(trunk.lane_ends) <= 1 and x >= trunk.x1 else min(end, x), y), (x, y), (x, low))  # R1861: no run inside the trunk
    )


def _ahead(line: tuple[XY, XY, XY], other: tuple[XY, XY, XY], low: int) -> bool:
    """True when `other` runs across the span of `line` (its foot and the marker `low` below it): `line` stands after it."""
    return line[1][1] < other[1][1] <= line[2][1] + low


def _stand(placed: tuple[XY, XY, XY], mark: Box, into: tuple[str, list[Box], list[tuple[str, Box]]]) -> None:
    """Record a placed leg: its marker box and its drop stand in the way of later legs, its run in the way of other fans' feet."""
    fan, standing, runs = into
    (x_start, y), (x, _), (_, foot) = placed
    standing += [Box(x + mark.x, foot, mark.w, mark.h), Box(x, y, 0, foot - y)]
    runs.append((fan, Box(x_start, y - 1, x - x_start, 1)))


def leg_feet(placed: Iterable[Placed], hung: Mapping[str, Sequence[Box]]) -> tuple[Box, ...]:
    """The boxes a leg stands clear of: each placed footprint and the hangings at its pins, which are part of the footprint (layout-0547)."""
    return (*(p.footprint for p in placed), *(b for boxes in hung.values() for b in boxes))


def leg_lines(
    trunks: Sequence[Trunk],
    fans: Mapping[str, Fan],
    rows: Mapping[PinRef, int],
    options: Options,
    around: tuple[Sequence[Box], ArrowEnds, Size | None],
) -> dict[tuple[str, int, PinRef], tuple[XY, XY, XY]]:
    """Every leg of a page's trunks that has a clear place, by (fan, row, pin): each stands clear of the legs placed before it (ONE-SIDED-PIN).

    One home for both stages: the router draws each leg and the marker stands at its foot, from the same line.
    A leg stands at the first clear x at or past cut + (rank+1)*unit (R1465), after any leg whose span it crosses; no clear x, no leg.
    """
    feet, arrowed, area = around
    legs = {(t.fan, t.row): leg_pins(fans[t.fan], rows, t.row) for t in trunks if t.fan in fans}
    standing, runs = list[Box](), list[tuple[str, Box]]()  # a leg's marker and drop; its run (no other fan's foot)
    given = {
        (t, i): leg_line(t, i, legs[t.fan, t.row], options, (feet, [b for f, b in runs if f != t.fan], arrowed, trunks, area))
        for t in trunks
        for i in range(len(legs.get((t.fan, t.row), ())))
    }
    out: dict[tuple[str, int, PinRef], tuple[XY, XY, XY]] = {}
    done: set[tuple[str, int, PinRef]] = set()
    while len(done) < len(given):
        for (t, i), line in given.items():
            key = (t.fan, t.row, legs[t.fan, t.row][i][1])
            mark = marker_box_at(0, 0, options, options.marker_facing["S"], (key[2], str(RefKind.STUB)))
            if key not in done and all(
                (k[0].fan, k[0].row, legs[k[0].fan, k[0].row][k[1]][1]) in done
                for k, o in given.items()
                if o is not line and line and o and _ahead(line, o, mark.h)
            ):
                done.add(key)
                if placed := leg_line(
                    t,
                    i,
                    legs[t.fan, t.row],
                    options,
                    (feet, [*standing, *(b for f, b in runs if f != t.fan)], arrowed, trunks, area),
                ):
                    out[key] = placed
                    _stand(placed, mark, (t.fan, standing, runs))
    return out


def leg_room(legs: Sequence[tuple[int, PinRef]], options: Options, *, arrowed: bool) -> int:
    """The x the legs of one trunk end take past its hull, from `leg_line`'s geometry (R1600).

    The legs stand past `leg_cut` by `leg_unit`: with an arrow, the cut is one grid past the hull and the arrow's own reserve covers
    the last box; without one, the last box overhangs its drop x.
    """
    boxes = [marker_box_at(0, 0, options, options.marker_facing["S"], (pin, str(RefKind.STUB))) for _, pin in legs]
    return leg_unit(legs, options) + (options.wiring_grid if arrowed else max(b.x + b.w for b in boxes)) if boxes else 0


def row_legs(refs: Iterable[Ref], plan: PagePlan, fans: Iterable[Fan], r: int, options: Options) -> int:
    """The x the legs take beyond the right end of row r's trunks: the widest fan's `leg_room`, each leg at its ledger box (R903, R1600)."""
    rows, fit = leg_rows(refs, plan.page), leg_fit(options, refs, plan.page)
    return max((leg_room(leg_pins(f, rows, r), fit, arrowed=bool(arrow_ends(refs, plan, (f,), r)[1])) for f in fans), default=0)


def column_legs(refs: Iterable[Ref], plan: PagePlan, fans: Iterable[Fan], at: tuple[int, str], options: Options) -> RowReserve:
    """The x each fan's legs take at column `at[1]` of row `at[0]`, and the widest last-leg overhang (R1618)."""
    rows, fit = leg_rows(refs, plan.page), leg_fit(options, refs, plan.page)
    found = [(f.id, legs, f) for f in fans if (legs := leg_pins(f, rows, *at))]
    units = tuple((fan, leg_unit(legs, fit)) for fan, legs, _ in found)
    rooms = (leg_room(legs, fit, arrowed=bool(arrow_ends(refs, plan, (f,), at[0])[1])) - dict(units)[fan] for fan, legs, f in found)
    return RowReserve(legs=units, tail=max(rooms, default=0))


def row_arrows(refs: Iterable[Ref], plan: PagePlan, blocks: Mapping[str, Block], fans: Iterable[Fan], r: int) -> tuple[int, int]:
    """The arrow ends row r keeps free: its own, and a fan's whose trunk in another row reaches a card of row r.

    An arrow stands at the end of its trunk's hull, so a card pin of this row is a tap of that trunk.
    """
    fans = tuple(fans)
    left, right = arrow_ends(refs, plan, fans, r)
    cards = {blocks[b].anchor for b in plan.rows[r].blocks if blocks[b].is_card}
    for fan in fans:
        ends = (*fan.drivers, *fan.legs)
        if cards.isdisjoint(a.pin.sym for a in ends):
            continue
        for k, row in enumerate(plan.rows):
            if k != r and any(a.column in row.columns for a in ends):
                more = arrow_ends(refs, plan, (fan,), k)
                left, right = left + more[0], right + more[1]
    return left, right


def annex_room(annexes: Iterable[Annex], anchor: str | None) -> int:
    """The G the annexes owned by `anchor` hold together: the one number row_size and the solved spans both read (R1129)."""
    return sum(a.size.h for a in annexes if a.owner == anchor) if anchor else 0


def block_reserves(cut: CutResult, annexes: Sequence[Annex], options: Options) -> dict[str | tuple[str, str], RowReserve]:
    """Each block's anchor to what its planned row keeps free; a non-card column's (anchor, column) to its own row's x (wrapping fans stay apart)."""
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    columns = {c.id: c for c in cut.flow.columns}
    out: dict[str | tuple[str, str], RowReserve] = {}
    for plan in cut.spec.pages:
        for r, row in enumerate(plan.rows):
            left, right = row_arrows(cut.spec.reference_plan, plan, blocks, cut.flow.fans, r)
            wide = lead_reserve(left, options) + lead_reserve(right, options)
            legs = row_legs(cut.spec.reference_plan, plan, cut.flow.fans, r, options)
            stubs = stub_room(cut.spec.reference_plan, plan, cut.flow.fans, r, options)
            dip = (
                trunk_room(
                    1, options.wiring_grid, arrow_hang(1, options.wiring_grid, arrow_room(cut.spec.reference_plan, plan, cut.flow.fans, r, options))
                )[1]
                - options.wiring_grid
            )
            for b in row.blocks:
                blk, key = blocks[b], blocks[b].anchor or b
                out[key] = RowReserve(
                    wide + legs if blk.is_card else 0, annex_room(annexes, blk.anchor) + max(0, stubs - blk.height_est) * blk.is_card + dip
                )
                out |= (
                    {}
                    if blk.is_card
                    else {
                        (key, c): replace(
                            column_legs(cut.spec.reference_plan, plan, cut.flow.fans, (r, c), options),
                            y=max(0, stubs - item_height(columns[c], options)) + dip,
                        )
                        for c in blk.columns
                        if c in row.columns
                    }
                )
    return out
