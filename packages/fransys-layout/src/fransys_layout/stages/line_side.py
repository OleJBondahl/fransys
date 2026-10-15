"""Layout-0172: a line's pins at one end that face apart fan to one side, toward its other end.

The side is a value computed once from the root's end (`harness_route.root`); `line_draw` fans
the re-faced pins as one row, so the bundle runs straight between the ends.
"""

from dataclasses import replace
from itertools import combinations, pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    OPPOSITE,
    WIRING_GRID,
    Box,
    Facing,
    Point,
    boxes_meet,
    contains,
    contains_point,
    pad,
    port_exit,
    through,
)
from fransys_layout.geometry.units import TEXT_GAP

from .harness_route import root
from .line_trunk import edge, tip
from .space import End, span
from .texts.candidates import Candidate, box_of, stub_anchor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .harness_route import LineEnd
    from .line_draw import EndOnPage, Fan, PinAt
    from .space import Obstacle


def aside(at: Point, target: Point, facing: Facing) -> Facing:
    """Across `facing`, toward `target` (east or south on a tie)."""
    if facing in (Facing.N, Facing.S):
        return Facing.E if target.x >= at.x else Facing.W
    return Facing.S if target.y >= at.y else Facing.N


def aim(ends: Sequence[EndOnPage], absent: int | None) -> dict[int, Point]:
    """Each end's branch to where its line's other end stands: the root aims at the next end.

    A line with an end off the page, or with one end here, aims nowhere: its ends fan as before.
    """
    if absent is not None or not ends[1:]:
        return {}
    first = next((one for one in ends if one.interface), ends[0])
    second = next(one for one in ends if one is not first)
    return {one.branch: _centre(second if one is first else first) for one in ends}


def _centre(one: EndOnPage) -> Point:
    """The middle of the end's box, or of its pins."""
    if one.box is not None:
        return Point(x=one.box.x + one.box.width // 2, y=one.box.y + one.box.height // 2)
    return _mean([pin.end.at for pin in one.pins])


def _mean(points: Sequence[Point]) -> Point:
    return Point(
        x=sum(p.x for p in points) // len(points), y=sum(p.y for p in points) // len(points)
    )


def faced(pins: Sequence[PinAt], toward: Point | None) -> Sequence[PinAt]:
    """`pins`, all facing the one side across their first pin's facing that looks to `toward`."""
    if toward is None or len({pin.end.facing for pin in pins}) == 1 or not _one_line(pins):
        return pins
    side = aside(_mean([pin.end.at for pin in pins]), toward, pins[0].end.facing)
    return [_toward(pin, side) for pin in pins]


def turned(pins: Sequence[PinAt], side: Facing) -> Sequence[PinAt]:
    """`pins` each turned to face `side`; a lone core runs straight out of its lead's turn.

    Its reach stands on the lead's line, so the core is square: pin, lead, then out to the side.
    """
    found = [pin if pin.end.facing is side else _toward(pin, side) for pin in pins]
    if len(found) != 1 or found[0].reach is None or found[0].lead is None:
        return found
    reach, lead = found[0].reach, found[0].lead
    sideways = side in (Facing.E, Facing.W)
    square = Point(x=reach.x, y=lead.y) if sideways else Point(x=lead.x, y=reach.y)
    return [replace(found[0], reach=square)]


def across_by_room(facing: Facing, at: Point, region: Box) -> list[Facing]:
    """The two sides across `facing`, the one with more room in `region` from `at` first."""
    if facing in (Facing.N, Facing.S):
        east, west = region.x + region.width - at.x, at.x - region.x
        return [Facing.E, Facing.W] if east >= west else [Facing.W, Facing.E]
    south, north = region.y + region.height - at.y, at.y - region.y
    return [Facing.S, Facing.N] if south >= north else [Facing.N, Facing.S]


def crosses_keepout(end: End, pin: Point, obstacles: Sequence[Obstacle]) -> bool:
    """Whether the leaving run out of `end` crosses the inside of a keep-out that holds not `pin`.

    The keep-outs are the symbols' ink and texts, passed as values (layout-0172, round 5).
    """
    run = (end.at, edge(end))
    return any(
        through(run, one.box) and not contains_point(one.box, pin.x, pin.y) for one in obstacles
    )


def _stub_box(end: End, size: tuple[int, int]) -> Box:
    """The box of the stub a line leaving `end` ends in."""
    return box_of(Candidate(side=end.facing, offset=0), stub_anchor(tip(end).at), size)


def stub_in(end: End, size: tuple[int, int], region: Box) -> bool:
    """Whether the stub box of a line leaving `end` lies in `region`."""
    return contains(region, _stub_box(end, size))


def stub_on_wire(end: End, size: tuple[int, int], wires: Sequence[Box]) -> bool:
    """Whether the stub box of a line leaving `end` has a routed wire through it (round 5)."""
    box = pad(_stub_box(end, size), TEXT_GAP)
    return any(
        through((Point(x=w.x, y=w.y), Point(x=w.x + w.width, y=w.y + w.height)), box) for w in wires
    )


def stub_cover(
    end: End, size: tuple[int, int], obstacles: Sequence[Obstacle], wires: Sequence[Box]
) -> int:
    """The area of the text box of a stub standing at `end` (its tip) that keep-outs cover.

    A routed wire through the box counts the whole box.
    """
    box = box_of(Candidate(side=end.facing, offset=0), stub_anchor(end.at), size)
    covered = sum(_overlap(box, o.box) for o in obstacles)
    on_wire = any(
        through((Point(x=w.x, y=w.y), Point(x=w.x + w.width, y=w.y + w.height)), pad(box, TEXT_GAP))
        for w in wires
    )
    return covered + (box.width * box.height if on_wire else 0)


def _overlap(one: Box, other: Box) -> int:
    wide = min(one.x + one.width, other.x + other.width) - max(one.x, other.x)
    high = min(one.y + one.height, other.y + other.height) - max(one.y, other.y)
    return max(0, wide) * max(0, high)


def _one_line(pins: Sequence[PinAt]) -> bool:
    """Whether the pins stand on one line across their facing, like a coil's two.

    A side fan's legs then run straight in; pins spread along the axis are reached through the body.
    """
    axis = Facing.N if pins[0].end.facing in (Facing.E, Facing.W) else Facing.E
    along = {p.end.at.y if axis is Facing.N else p.end.at.x for p in pins}
    return len(along) == 1


def _toward(pin: PinAt, side: Facing) -> PinAt:
    """`pin` facing `side`: its row its symbol's keep-out along that axis, its reach that edge."""
    at, (low, high) = pin.end.at, pin.across
    edge = {
        Facing.E: Point(x=high + (-high) % WIRING_GRID, y=at.y),
        Facing.W: Point(x=low - low % WIRING_GRID, y=at.y),
        Facing.S: Point(x=at.x, y=high + (-high) % WIRING_GRID),
        Facing.N: Point(x=at.x, y=low - low % WIRING_GRID),
    }[side]
    lead = port_exit(at, pin.end.facing) if pin.end.facing is not side else None
    return replace(
        pin,
        end=replace(pin.end, facing=side),
        row=pin.across,
        across=pin.row,
        reach=edge,
        lead=lead,
    )


def run_on(joint: Sequence[tuple[LineEnd, Fan | None]]) -> list[LineEnd]:
    """W13-DIP: a non-root joint end whose line runs on to further rows is met on that run.

    Met from its facing side it dipped a grid past the split, then ran on across it.
    """
    first = root([end for end, _ in joint]) if joint else None
    return [
        replace(end, end=_met_on(end.end, fan.rows[0].at))
        if fan and fan.rows and end is not first
        else end
        for end, fan in joint
    ]


def _met_on(end: End, onward: Point) -> End:
    """The split met from behind the run that leaves it toward `onward` (as `_row_run` leaves)."""
    return End(end.at, OPPOSITE[aside(end.at, onward, end.facing)])


def fan_on_wire(fan: Fan | None, wires: Sequence[Box]) -> bool:
    """Whether a fan-out's split stands on a routed wire, which its line would then run along."""
    return fan is not None and any(contains_point(w, fan.at.x, fan.at.y) for w in wires)


def clear_column(
    end: End,
    box: Box,
    size: tuple[int, int] | None,
    wires: Sequence[Box],
    obstacles: Sequence[Obstacle],
) -> End:
    """A box end slid along its edge to the nearest grid column whose run out touches nothing.

    A leaving end's run and stub box, else the end alone, stay off wires and keep-outs but the
    box; it may take the far edge. No clear column leaves it as it was (layout-0246).
    """
    first = box.x + (-box.x) % WIRING_GRID
    columns = sorted(
        range(first, box.x + box.width + 1, WIRING_GRID), key=lambda x: abs(x - end.at.x)
    )
    others = [o for o in obstacles if not contains(o.box, box)]
    low, high = box.y - box.y % WIRING_GRID, box.y + box.height
    far = high + (-high) % WIRING_GRID if end.facing is Facing.N else low
    sides = [(end.at.y, end.facing)] + ([(far, OPPOSITE[end.facing])] if size else [])
    options = (End(at=Point(x=x, y=y), facing=face) for y, face in sides for x in columns)
    return next((one for one in options if _column_clear(one, size, wires, others)), end)


def _column_clear(
    end: End, size: tuple[int, int] | None, wires: Sequence[Box], obstacles: Sequence[Obstacle]
) -> bool:
    run = (end.at, edge(end) if size else end.at)
    body = Box(
        x=min(p.x for p in run),
        y=min(p.y for p in run),
        width=abs(run[0].x - run[1].x),
        height=abs(run[0].y - run[1].y),
    )
    return (
        not (size and stub_on_wire(end, size, wires))
        and not any(boxes_meet(body, w, closed=True) for w in wires)
        and not any(boxes_meet(body, o.box, closed=True) for o in obstacles)
        and not (
            size and any(boxes_meet(_stub_box(end, size), o.box, closed=True) for o in obstacles)
        )
    )


def fan_clear(fan: Fan | None, wires: Sequence[Box], obstacles: Sequence[Obstacle] = ()) -> bool:
    """Whether a fan-out stands off every wire, its legs share no run and cross no other body.

    A leg that runs through a keep-out holding not its pin, or along another leg, reads as a
    joined wire (layout-0246); the split on a wire does too.
    """
    if fan is None:
        return True
    segments = [(leg, pair) for leg in fan.legs for pair in pairwise(leg.points)]
    return (
        not fan_on_wire(fan, wires)
        and not any(
            boxes_meet(span(*pair), o.box, closed=True)
            and not contains_point(o.box, leg.points[-1].x, leg.points[-1].y)
            for leg, pair in segments
            for o in obstacles
        )
        and not any(
            _shared_run(a, b) for (la, a), (lb, b) in combinations(segments, 2) if la is not lb
        )
    )


def _shared_run(one: tuple[Point, Point], other: tuple[Point, Point]) -> bool:
    """Whether two segments lie on one line and overlap by more than a point."""
    for axis, cross in ((0, 1), (1, 0)):
        coords = [(p.x, p.y) for p in (*one, *other)]
        if len({c[cross] for c in coords}) == 1 and one[0] != one[1] and other[0] != other[1]:
            first = sorted(c[axis] for c in coords[:2])
            second = sorted(c[axis] for c in coords[2:])
            return min(first[1], second[1]) > max(first[0], second[0])
    return False


def split_in(fan: Fan | None, obstacles: Sequence[Obstacle]) -> bool:
    """Whether a fan-out split stands in, or on the edge of, a keep-out holding none of its pins."""
    if fan is None:
        return False
    pins = [leg.points[-1] for leg in fan.legs]
    return any(
        contains_point(o.box, fan.at.x, fan.at.y)
        and not any(contains_point(o.box, p.x, p.y) for p in pins)
        for o in obstacles
    )
