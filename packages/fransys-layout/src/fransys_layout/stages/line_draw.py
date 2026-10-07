"""HL15, HL17, HL18 (layout-0154): one line's pieces on one page, from its ends drawn there.

An end is a plug's box edge on the line's side, or a fan-out's split. A line some of whose ends
are elsewhere leaves: it runs `LEAVE` straight out and ends in one stub (HL1, owner C1).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import OPPOSITE, WIRING_GRID, Box, Facing, Point, port_exit

from .harness_route import LineEnd, line_paths, root
from .line_shapes import DrawnLeg
from .space import End
from .texts.candidates import Candidate, box_of, stub_anchor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id

    from .harness_route import Grid

FAN_GRIDS = 4  # HL17: the split stands 32 G, four grids, before its pins' row
LEAVE_GRIDS = 6  # HL18: a leaving line runs 48 G, one column gap, straight out


@dataclass(frozen=True)
class PinAt:
    """A fan-out end's pin on the page: the conductor that lands on it, and where it points.

    `row` is its symbol's keep-out along the facing axis: pins whose rows meet share a fan (HL17).
    """

    conductor: Id[Any]
    end: End
    row: tuple[int, int] = (0, 0)


@dataclass(frozen=True)
class EndOnPage:
    """One end of a line drawn on the page: a plug's box (and its mate's), or its pins.

    `leaving`: a middle interface's end that `line_reach` reached nowhere (condition 1).
    """

    branch: int
    interface: bool = False
    leaving: bool = False
    box: Box | None = None
    mate: Box | None = None
    pins: tuple[PinAt, ...] = ()


@dataclass(frozen=True)
class Fan:
    """One fan-out: its branch, split point and legs (HL8, HL17).

    `rows` are the further pin rows' splits, each facing out of its row: the line runs on to
    each in turn (HL15).
    """

    branch: int
    at: Point
    legs: tuple[DrawnLeg, ...]
    rows: tuple[End, ...] = ()
    facing: Facing = Facing.N


@dataclass(frozen=True)
class Stub:
    """A leaving line's stub: the near end's branch, the far end's, where it stands and faces."""

    near: int
    far: int
    end: End


@dataclass(frozen=True)
class Pieces:
    """What one line draws on one page: polylines by branch, fan-outs and stubs."""

    paths: tuple[tuple[int, tuple[Point, ...]], ...]
    fans: tuple[Fan, ...]
    stubs: tuple[Stub, ...]


def line_pieces(
    ends: Sequence[EndOnPage], absent: int | None, grid: Grid, *, margin: int = 0
) -> Pieces:
    """HL15, HL18: the line among its joint ends; each leaving end and a lone end leave.

    `absent` is the branch of the first end not on this page, `None` when every end is here.
    A fan-out's split keeps `margin` (half its widest stub) inside the region (layout-0158).
    """
    drawn = [_drawn(one, _within(grid.region, margin)) for one in ends]
    others = [end.branch for _, end, _ in drawn]
    joint = [end for one, end, _ in drawn if not one.leaving]
    leave = [end for one, end, _ in drawn if one.leaving]
    if len(joint) == 1:
        leave.append(joint.pop())
    paths = [(end.branch, _out(end.end)) for end in leave]
    stubs = [Stub(end.branch, _far(absent, others, end.branch), _tip(end.end)) for end in leave]
    if joint and absent is not None:
        first = root(joint)
        stubs.append(Stub(first.branch, absent, _tip(first.end)))
        joint.append(LineEnd(branch=absent, end=_goal(first.end)))
    if len(joint) > 1:
        paths.extend(line_paths(joint, grid).items())
    return _through_rows(paths, tuple(fan for _, _, fan in drawn if fan), stubs, grid)


def _within(region: Box, margin: int) -> tuple[int, int]:
    """The x span a fan-out's split may take: the region less `margin` each side."""
    return region.x + margin, region.x + region.width - margin


def _far(absent: int | None, others: Sequence[int], branch: int) -> int:
    """The far end a stub names: the first end off the page, else the line's next other end."""
    if absent is not None:  # the root's branch is 0
        return absent
    return next((b for b in others if b != branch), branch)


def _drawn(one: EndOnPage, bounds: tuple[int, int]) -> tuple[EndOnPage, LineEnd, Fan | None]:
    """The end's `LineEnd`, and its fan-out when it ends in pins."""
    if one.box is not None:
        return one, LineEnd(one.branch, _box_end(one.box, one.mate), one.interface), None
    rows = _pin_rows(one.pins)
    facing = rows[0][0].end.facing  # the line ends at the first row's split, out of that row
    fans = [fan_out(row, bounds) for row in rows]
    (split, _), legs = fans[0], tuple(leg for _, row in fans for leg in row)
    further = tuple(
        End(at, row[0].end.facing) for (at, _), row in zip(fans[1:], rows[1:], strict=True)
    )
    fan = Fan(one.branch, split, legs, further, facing)
    return one, LineEnd(one.branch, End(at=split, facing=facing), one.interface), fan


def _pin_rows(pins: Sequence[PinAt]) -> list[list[PinAt]]:
    """HL17: the pins grouped in rows (facing alike, `row` spans meeting), the outermost first."""
    facing = pins[0].end.facing
    sign = 1 if facing in (Facing.S, Facing.E) else -1
    rows: list[list[PinAt]] = []
    for pin in sorted(pins, key=lambda pin: (-sign * pin.row[1], -sign * pin.row[0])):
        row = next((one for one in rows if _meet(one, pin)), None)
        if row is None:
            rows.append([pin])
        else:
            row.append(pin)
    return rows


def _meet(row: Sequence[PinAt], pin: PinAt) -> bool:
    """Whether `pin` faces as `row`'s pins and its row span meets one of theirs."""
    return row[0].end.facing is pin.end.facing and any(
        one.row[0] <= pin.row[1] and pin.row[0] <= one.row[1] for one in row
    )


def _through_rows(
    paths: Sequence[tuple[int, tuple[Point, ...]]],
    fans: tuple[Fan, ...],
    stubs: Sequence[Stub],
    grid: Grid,
) -> Pieces:
    """HL15: the pieces, the path that ends at a fan's split run on to each further row's."""
    found: list[tuple[int, tuple[Point, ...]]] = list(paths)
    for fan in (one for one in fans if one.rows):
        found = [(b, _joined(points, fan, grid)) for b, points in found]
    return Pieces(tuple(found), fans, tuple(stubs))


def _joined(points: tuple[Point, ...], fan: Fan, grid: Grid) -> tuple[Point, ...]:
    """`points` run on from whichever of its ends stands at `fan.at`, through `fan.rows`.

    The run may go back along the line's last run: drawn twice, it reads as the line's branch.
    """
    if points[-1] == fan.at:
        return (*points, *_row_run(fan, grid)[1:])
    if points[0] == fan.at:
        return (*reversed(_row_run(fan, grid)), *points[1:])
    return points


def _row_run(fan: Fan, grid: Grid) -> tuple[Point, ...]:
    """The run from `fan.at` through each further row's split, entered from outside.

    It leaves each split along its row, toward the next.
    """
    run: list[Point] = [fan.at]
    facing = fan.facing
    for end in fan.rows:
        start = End(run[-1], _aside(run[-1], end.at, facing))
        run.extend(line_paths((LineEnd(0, start), LineEnd(0, end)), grid)[0][1:])
        facing = end.facing
    return tuple(run)


def _aside(at: Point, target: Point, facing: Facing) -> Facing:
    """Across `facing`, toward `target` (east or south on a tie)."""
    if facing in (Facing.N, Facing.S):
        return Facing.E if target.x >= at.x else Facing.W
    return Facing.S if target.y >= at.y else Facing.N


def _box_end(box: Box, mate: Box | None) -> End:
    """A plug box's edge middle away from the box it mates, on the grid: up unless it is below."""
    below = mate is not None and mate.y + mate.height <= box.y
    x = box.x + box.width // 2
    x -= x % WIRING_GRID
    if below:
        y = box.y + box.height
        return End(at=Point(x=x, y=y + (-y) % WIRING_GRID), facing=Facing.S)
    return End(at=Point(x=x, y=box.y - box.y % WIRING_GRID), facing=Facing.N)


def fan_out(
    pins: Sequence[PinAt], bounds: tuple[int, int] | None = None
) -> tuple[Point, tuple[DrawnLeg, ...]]:
    """HL17: the split `FAN_GRIDS` past the pins' row, centred; each leg split, knee, pin.

    The knee stands one grid out of its pin; the leg's slant follows from the split distance.
    A split across a vertical row stays within `bounds` (x), so its stub stays on the page.
    """
    facing = pins[0].end.facing
    points = [pin.end.at for pin in pins]
    if facing in (Facing.N, Facing.S):
        row = min(p.y for p in points) if facing is Facing.N else max(p.y for p in points)
        mid = sum(p.x for p in points) // len(points)
        if bounds is not None:
            mid = min(max(mid, bounds[0] + (-bounds[0]) % WIRING_GRID), bounds[1])
        base = Point(x=mid - mid % WIRING_GRID, y=row)
    else:
        row = min(p.x for p in points) if facing is Facing.W else max(p.x for p in points)
        mid = sum(p.y for p in points) // len(points)
        base = Point(x=row, y=mid - mid % WIRING_GRID)
    split = port_exit(base, facing, FAN_GRIDS)
    legs = tuple(
        DrawnLeg(conductor=pin.conductor, points=(split, port_exit(pin.end.at, facing), pin.end.at))
        for pin in sorted(pins, key=lambda pin: (pin.end.at.x, pin.end.at.y, pin.conductor))
    )
    return split, legs


def _tip(end: End) -> End:
    """Where a leaving line ends and its stub starts, facing on out (HL18)."""
    return End(at=port_exit(end.at, end.facing, LEAVE_GRIDS), facing=end.facing)


def _edge(end: End) -> Point:
    """Where a leaving line meets its stub's box: its near edge's middle, as `stub_box` has it."""
    edge = box_of(Candidate(side=end.facing, offset=0), stub_anchor(_tip(end).at), (0, 0))
    return Point(x=edge.x, y=edge.y)


def _goal(end: End) -> End:
    """The leaving end as a goal of the search: its stub box's edge, entered from the line."""
    return End(at=_edge(end), facing=OPPOSITE[end.facing])


def _out(end: End) -> tuple[Point, ...]:
    """A leaving line: straight out from its end to its stub box's edge (layout-0158)."""
    return (end.at, _edge(end))
