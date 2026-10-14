"""Layout-0172: a line's pins at one end that face apart fan to one side, toward its other end.

The side is a value computed once from the root's end (`harness_route.root`); `line_draw` fans
the re-faced pins as one row, so the bundle runs straight between the ends.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    OPPOSITE,
    WIRING_GRID,
    Box,
    Facing,
    Point,
    contains,
    contains_point,
    pad,
    port_exit,
    through,
)
from fransys_layout.geometry.units import TEXT_GAP

from .harness_route import root
from .line_trunk import edge, tip
from .space import End
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
