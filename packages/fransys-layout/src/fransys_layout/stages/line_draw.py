"""Layout-0154: one line's pieces on one page, from its ends drawn there.

An end is a plug's box edge on the line's side, or a fan-out's split. A line some of whose ends
are elsewhere leaves: it runs `LEAVE` straight out and ends in one stub (layout-0154).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import OPPOSITE, WIRING_GRID, Box, Facing, Point, pad, port_exit
from fransys_layout.geometry.meet import contains_point

from .harness_route import LineEnd, line_paths, root
from .line_shapes import DrawnLeg
from .line_side import (
    across_by_room,
    aim,
    aside,
    crosses_keepout,
    faced,
    stub_in,
    stub_on_wire,
    turned,
)
from .line_trunk import edge, halves, holding_ends, tip, trunk_end
from .space import End

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id

    from .harness_route import Grid

FAN_GRIDS = 4  # layout-0154: the split stands 32 G, four grids, before its pins' row
FAN_CLEAR = 2 * WIRING_GRID  # layout-0172: and that far from another symbol's keep-out, or nearer


@dataclass(frozen=True)
class PinAt:
    """A fan-out end's pin on the page: the conductor that lands on it, and where it points.

    `row`: its keep-out along the facing axis. A pin re-faced (layout-0172) takes `across` as
    `row`; `reach` is the keep-out's edge it faces, `lead` the point one grid out of the pin.
    """

    conductor: Id[Any]
    end: End
    row: tuple[int, int] = (0, 0)
    across: tuple[int, int] = (0, 0)
    reach: Point | None = None
    lead: Point | None = None

    @property
    def stands(self) -> Point:
        """Where the fan counts its split from: `reach`, else the pin."""
        return self.reach or self.end.at


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
    toward: tuple[int, int] | None = (
        None  # layout-0206: the rows of the line's far ends, for a plug-less box
    )


@dataclass(frozen=True)
class Fan:
    """One fan-out: its branch, split point and legs (render-0010, layout-0154).

    `rows` are the further pin rows' splits, each facing out of its row: the line runs on to
    each in turn (layout-0154).
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
class Way:
    """How an end's pins fan: toward a point, clear of boxes, or turned to a side (layout-0172).

    `turn` is a side every pin faces and the grids its split stands past them: a lone core
    clear of a symbol (round 5).
    """

    toward: Point | None = None
    apart: Sequence[Box] = ()
    turn: tuple[Facing, int] | None = None


NO_WAY = Way()


@dataclass(frozen=True)
class Pieces:
    """What one line draws on one page: polylines by branch, fan-outs and stubs."""

    paths: tuple[tuple[int, tuple[Point, ...]], ...]
    fans: tuple[Fan, ...]
    stubs: tuple[Stub, ...]


def line_pieces(
    ends: Sequence[EndOnPage],
    absent: int | None,
    grid: Grid,
    *,
    margin: int = 0,
    trunk: tuple[Facing, tuple[int, int]] | None = None,
) -> Pieces:
    """Layout-0154: the line among its joint ends; each leaving end and a lone end leave.

    `absent` is the first end's branch off this page; `margin` keeps a fan-out's split inside
    (layout-0158); `trunk` is set when the root is off the page (`line_trunk`).
    """
    drawn = _all_drawn(ends, absent, _within(grid.region, margin), grid)
    others = [end.branch for _, end, _ in drawn]
    joint = [end for one, end, _ in drawn if not one.leaving]
    leave = [end for one, end, _ in drawn if one.leaving]
    if len(joint) == 1:
        leave.append(joint.pop())
    paths = [(end.branch, _out(end.end)) for end in leave]
    stubs = [Stub(end.branch, _far(absent, others, end.branch), tip(end.end)) for end in leave]
    more, stub = _joint_pieces(joint, absent, grid, trunk)
    fans = tuple(fan for _, _, fan in drawn if fan)
    return _through_rows([*paths, *more], fans, [*stubs, *stub], grid)


def _all_drawn(
    ends: Sequence[EndOnPage],
    absent: int | None,
    bounds: tuple[int, int],
    grid: Grid,
) -> Sequence[tuple[EndOnPage, LineEnd, Fan | None]]:
    """Each end drawn, its mixed pins fanned toward the line's other end (layout-0172).

    Two ends whose splits then coincide leave no bundle between them: the line fans as before.
    """
    toward = aim(ends, absent)
    drawn = _clear_of_symbols(
        [_drawn(one, bounds, grid, Way(toward.get(one.branch))) for one in ends], ends, bounds, grid
    )
    apart = _side_boxes([fan for _, _, fan in drawn if fan], grid)
    if apart:
        drawn = [_drawn(one, bounds, grid, Way(toward.get(one.branch), apart)) for one in ends]
        drawn = _clear_of_symbols(drawn, ends, bounds, grid)
    if len({end.end.at for _, end, _ in drawn}) < len(drawn):
        return [_drawn(one, bounds, grid) for one in ends]
    return drawn


def _clear_of_symbols(
    drawn: Sequence[tuple[EndOnPage, LineEnd, Fan | None]],
    ends: Sequence[EndOnPage],
    bounds: tuple[int, int],
    grid: Grid,
) -> Sequence[tuple[EndOnPage, LineEnd, Fan | None]]:
    """A lone core's bundle that would leave over a symbol turns to a side that is clear.

    The core leaves its pin along the lead, then turns; its split stands nearer its pins until
    the stub's box sits on no wire (layout-0172, round 5).
    """
    if len(drawn) != 1 or drawn[0][2] is None or len(ends[0].pins) != 1:
        return drawn
    one, end, _ = drawn[0]
    pin = ends[0].pins[0].end.at
    if not crosses_keepout(end.end, pin, grid.obstacles):
        return drawn
    tries = [
        found
        for side in across_by_room(end.end.facing, end.end.at, grid.region)
        for grids in range(FAN_GRIDS, 0, -1)
        if _clear_leave(found := _drawn(one, bounds, grid, Way(turn=(side, grids))), pin, grid)
    ]
    off_wires = (f for f in tries if not stub_on_wire(f[1].end, grid.stub, grid.wires))
    return [next(off_wires, tries[0])] if tries else drawn


def _clear_leave(found: tuple[EndOnPage, LineEnd, Fan | None], pin: Point, grid: Grid) -> bool:
    """Whether the leaving run out of `found` crosses no keep-out and its stub box stands in."""
    end = found[1].end
    return not crosses_keepout(end, pin, grid.obstacles) and stub_in(end, grid.stub, grid.region)


def _side_boxes(fans: Sequence[Fan], grid: Grid) -> list[Box]:
    """The obstacle boxes that hold the pins of a side fan (two or more legs): its cores' lanes."""
    pins = [leg.points[-1] for fan in fans if fan.legs[1:] for leg in fan.legs]
    return [
        one.box for one in grid.obstacles if any(contains_point(one.box, p.x, p.y) for p in pins)
    ]


def _joint_pieces(
    joint: Sequence[LineEnd],
    absent: int | None,
    grid: Grid,
    trunk: tuple[Facing, tuple[int, int]] | None,
) -> tuple[list[tuple[int, tuple[Point, ...]]], list[Stub]]:
    grid = holding_ends(grid, joint)
    out = _trunk(joint, absent, grid, trunk)
    if out is not None:
        return out[0], [out[1]]
    stubs: list[Stub] = []
    if joint and absent is not None:
        first = root(joint)
        stubs.append(Stub(first.branch, absent, tip(first.end)))
        joint = [*joint, LineEnd(branch=absent, end=_goal(first.end))]
    return (list(line_paths(joint, grid).items()) if len(joint) > 1 else []), stubs


def _trunk(
    joint: Sequence[LineEnd],
    absent: int | None,
    grid: Grid,
    trunk: tuple[Facing, tuple[int, int]] | None,
) -> tuple[list[tuple[int, tuple[Point, ...]]], Stub] | None:
    """The bar of the ends here and the trunk out of it to its stub; `None` leaves as before."""
    if trunk is None or absent is None or not joint[1:]:
        return None
    bar = line_paths(joint, grid)
    end = trunk_end(bar, grid, *trunk)
    if end is None:
        return None
    first = root(joint)
    return [*_branches(bar, joint, end.at), (absent, _out(end))], Stub(
        first.branch, absent, tip(end)
    )


def _branches(
    bar: Mapping[int, tuple[Point, ...]], joint: Sequence[LineEnd], at: Point
) -> list[tuple[int, tuple[Point, ...]]]:
    """The bar's paths, each end keeping its own branch: two ends' one polyline is cut at `at`."""
    if joint[2:]:  # a pair is the one bar that is a single polyline
        return list(bar.items())
    first = root(joint)
    other = next(one for one in joint if one is not first)
    near, far = halves(bar[first.branch], at)
    return [(first.branch, near), (other.branch, far)]


def _within(region: Box, margin: int) -> tuple[int, int]:
    """The x span a fan-out's split may take: the region less `margin` each side."""
    return region.x + margin, region.x + region.width - margin


def _far(absent: int | None, others: Sequence[int], branch: int) -> int:
    """The far end a stub names: the first end off the page, else the line's next other end."""
    if absent is not None:  # the root's branch is 0
        return absent
    return next((b for b in others if b != branch), branch)


def _drawn(
    one: EndOnPage,
    bounds: tuple[int, int],
    grid: Grid,
    way: Way = NO_WAY,
) -> tuple[EndOnPage, LineEnd, Fan | None]:
    """The end's `LineEnd`, and its fan-out when it ends in pins (to one side, as `way` says)."""
    if one.box is not None:
        end = _box_end(one.box, one.mate, one.toward)
        return one, LineEnd(one.branch, end, one.interface), None
    rows = _pin_rows(turned(one.pins, way.turn[0]) if way.turn else faced(one.pins, way.toward))
    facing = rows[0][0].end.facing  # the line ends at the first row's split, out of that row
    avoid = [one.box for one in grid.obstacles]
    fans = [
        fan_out(row, bounds, avoid, way.apart, way.turn[1] if way.turn else FAN_GRIDS)
        for row in rows
    ]
    (split, _), legs = fans[0], tuple(leg for _, row in fans for leg in row)
    further = tuple(
        End(at, row[0].end.facing) for (at, _), row in zip(fans[1:], rows[1:], strict=True)
    )
    fan = Fan(one.branch, split, legs, further, facing)
    return one, LineEnd(one.branch, End(at=split, facing=facing), one.interface), fan


def drawn_end(one: EndOnPage, bounds: tuple[int, int], grid: Grid) -> LineEnd:
    """The end's `LineEnd` as `line_pieces` draws it: its point and the way it faces."""
    return _drawn(one, bounds, grid)[1]


def _pin_rows(pins: Sequence[PinAt]) -> list[list[PinAt]]:
    """The pins grouped in rows (facing alike, `row` spans meeting), the outermost first."""
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
    """Layout-0154: the pieces, the path that ends at a fan's split run on to each further row's."""
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
        start = End(run[-1], aside(run[-1], end.at, facing))
        run.extend(line_paths((LineEnd(0, start), LineEnd(0, end)), grid)[0][1:])
        facing = end.facing
    return tuple(run)


def _box_end(box: Box, mate: Box | None, toward: tuple[int, int] | None = None) -> End:
    """A plug box's edge middle away from the box it mates, on the grid: up unless it is below.

    A plug-less box (layout-0206) takes the edge facing the rows of the line's other ends.
    """
    below = mate is not None and mate.y + mate.height <= box.y
    if toward is not None:
        below = toward[0] >= box.y + box.height
    x = box.x + box.width // 2
    x -= x % WIRING_GRID
    if below:
        y = box.y + box.height
        return End(at=Point(x=x, y=y + (-y) % WIRING_GRID), facing=Facing.S)
    return End(at=Point(x=x, y=box.y - box.y % WIRING_GRID), facing=Facing.N)


def fan_out(
    pins: Sequence[PinAt],
    bounds: tuple[int, int] | None = None,
    avoid: Sequence[Box] = (),
    apart: Sequence[Box] = (),
    grids: int = FAN_GRIDS,
) -> tuple[Point, tuple[DrawnLeg, ...]]:
    """Layout-0154: the split `FAN_GRIDS` past the pins' row, centred; each leg split, knee, pin.

    A split across a vertical row stays within `bounds` (x). It stands nearer its pins when it
    would stand within `FAN_CLEAR` of a box of `avoid` that holds none of them (layout-0172).
    """
    facing = pins[0].end.facing
    points = [pin.stands for pin in pins]
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
    split = _split(base, facing, _foreign(avoid, pins), _foreign(apart, pins), grids)
    legs = tuple(
        DrawnLeg(conductor=pin.conductor, points=(split, *_knees(pin, facing), pin.end.at))
        for pin in sorted(pins, key=lambda pin: (pin.end.at.x, pin.end.at.y, pin.conductor))
    )
    return split, legs


def _foreign(avoid: Sequence[Box], pins: Sequence[PinAt]) -> list[Box]:
    """The boxes of `avoid` that hold none of the pins: another symbol's keep-out."""
    ats = [pin.end.at for pin in pins]
    return [pad(b, FAN_CLEAR) for b in avoid if not any(contains_point(b, a.x, a.y) for a in ats)]


def _split(
    base: Point,
    facing: Facing,
    foreign: Sequence[Box],
    apart: Sequence[Box] = (),
    most: int = FAN_GRIDS,
) -> Point:
    """The split `FAN_GRIDS` past `base`, or nearer, clear of the `foreign` boxes' insides.

    The grid past it, where the bundle line arrives, is also clear of the `apart` boxes (a side
    fan's symbol): else the bundle runs over that fan's cores (layout-0172 round 4).
    """
    for grids in range(most, 1, -1):
        split = port_exit(base, facing, grids)
        if not _in(split, foreign) and not _in(port_exit(base, facing, grids + 1), apart):
            return split
    return port_exit(base, facing, 1)


def _in(at: Point, boxes: Sequence[Box]) -> bool:
    return any(b.x < at.x < b.x + b.width and b.y < at.y < b.y + b.height for b in boxes)


def _knees(pin: PinAt, facing: Facing) -> tuple[Point, ...]:
    """The knees of a leg: one grid out of the pin, or a re-faced pin's lead (layout-0172).

    A re-faced pin's core turns at `lead`, then runs to the keep-out's edge, off any outline.
    """
    if pin.reach is None or pin.lead is None:
        return (pin.reach or port_exit(pin.end.at, facing),)
    sideways = facing in (Facing.E, Facing.W)
    turn = Point(x=pin.reach.x, y=pin.lead.y) if sideways else Point(x=pin.lead.x, y=pin.reach.y)
    return (turn, pin.lead)


def _goal(end: End) -> End:
    """The leaving end as a goal of the search: its stub box's edge, entered from the line."""
    return End(at=edge(end), facing=OPPOSITE[end.facing])


def _out(end: End) -> tuple[Point, ...]:
    """A leaving line: straight out from its end to its stub box's edge (layout-0158)."""
    return (end.at, edge(end))
