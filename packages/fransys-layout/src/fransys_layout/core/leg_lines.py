"""The legs of a one-sided pin: each leg's line out from its trunk end and down to its marker, one home for both stages (ONE-SIDED-PIN)."""

from __future__ import annotations

from itertools import count, takewhile
from typing import TYPE_CHECKING

from .arrow_reserve import leg_cut, leg_hull, leg_offsets, leg_pins, leg_unit
from .band import arrow_box, lane_line, lane_offset, lane_rows
from .clearance import Keep, clear, through_keeps
from .geometry import inside, marker_box_at
from .values import Box, RefKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .arrow_reserve import ArrowEnds
    from .flow_values import Fan
    from .outputs import Placed, Trunk
    from .values import XY, Options, PinRef, Size


def _clear(c: int, mark: Box, start: XY, room: tuple[Sequence[Keep], frozenset[int], Size | None]) -> bool:
    """True when a leg dropping at x `c` with its marker box `mark` is inside `room` = (keeps, drop xs of its trunk, page) and meets none.

    The marker box and a run past a non-body keep touch open; a run past a body is `through_keeps` (no pins: an outline run is refused).
    """
    keeps, drops, area = room
    y = start[1]
    if (area is not None and not inside(mark, area)) or c in drops or any(mark.x < d < mark.x + mark.w for d in drops):
        return False
    runs = [r for r in (Box(start[0], y, c - start[0], 0), Box(c, y, 0, mark.y - y)) if r.w or r.h]
    bodies = [k for k in keeps if k.kind == "body"]
    return not (
        any(clear(mark, keeps, {}, edge="open"))
        or any(clear(r, [k for k in keeps if k.kind != "body"], {}, edge="open") or through_keeps(r, bodies, (), frozenset(), {}) for r in runs)
    )


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
        frozenset(d for e in trunk.lane_ends if e for d in e if not reach or d <= leg_hull(trunk, reach)),  # an arrow's step-out is no drop
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
