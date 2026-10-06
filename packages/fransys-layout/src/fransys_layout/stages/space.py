"""One page model of space (layout-0083): D2's three edge predicates over a page's shapes.

Why each predicate stands as it does, and the exemption table by kind: docs/design/pages.md 6.9.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Point,
    boxes_meet,
    contains,
    meets,
    port_exit,
)
from fransys_model.kernel import Id, value

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .types import Handle

# A wiring-grid point as a plain pair, so the search can key dicts and sets with it.
type Cell = tuple[int, int]


@dataclass(frozen=True, slots=True)
class End:
    """One end of an edge: the port's page position and the way it points."""

    at: Point
    facing: Facing


@dataclass(frozen=True, slots=True)
class Run:
    """An axis-aligned segment, ends ordered: `x <= to_x`, `y <= to_y`; zero length is a point."""

    x: int
    y: int
    to_x: int
    to_y: int


@dataclass(frozen=True, slots=True)
class Lane:
    """A port's exit (D2): the port's end, and the extent of the wire that leaves through a box."""

    end: End
    extent: Box

    @property
    def run(self) -> Run:
        """The extent as a `Run`: the extent has no width, so it is a run of its own."""
        one = self.extent
        return Run(x=one.x, y=one.y, to_x=one.x + one.width, to_y=one.y + one.height)


@dataclass(frozen=True, slots=True)
class Obstacle:
    """A box no step may touch, with the endpoint lanes it is not allowed to block."""

    box: Box
    lanes: tuple[Lane, ...]


@value
class Shape:
    """A placed box and the handle whose own lane may cross it."""

    owner: Id[Any] | None
    box: Box


@value
class Space:
    """A page's placed shapes, frozen (D2), and the content box a text is placed inside (S18)."""

    shapes: tuple[Shape, ...]
    content: Box | None = None

    def holds(self, box: Box) -> bool:
        """P3's containment: `box` lies inside `content`, closed (flush is inside), or none."""
        return self.content is None or contains(self.content, box)

    def obstacles(
        self, own_ends: Mapping[Handle, tuple[End, ...]], region: Box
    ) -> tuple[Obstacle, ...]:
        """The boxes that can block an edge inside `region`, each with its exempt lanes."""
        owners: dict[Box, list[Handle | None]] = {}
        for shape in self.shapes:
            owners.setdefault(shape.box, []).append(shape.owner)
        return tuple(
            Obstacle(
                box=shape.box,
                lanes=tuple(
                    lane(end, shape.box)
                    for sharer in owners[shape.box]
                    if sharer is not None
                    for end in own_ends.get(sharer, ())
                ),
            )
            for shape in self.shapes
            if _reaches(region, shape.box)
        )


def span(one: Point, other: Point) -> Box:
    """The box two points span: a segment when they share a coordinate."""
    return Box(
        x=min(one.x, other.x),
        y=min(one.y, other.y),
        width=abs(one.x - other.x),
        height=abs(one.y - other.y),
    )


def lane(end: End, box: Box) -> Lane:
    """The wire lane of `end` through `box`, the box its port leaves through."""
    far = {
        Facing.N: Point(x=end.at.x, y=box.y),
        Facing.S: Point(x=end.at.x, y=box.y + box.height),
        Facing.W: Point(x=box.x, y=end.at.y),
        Facing.E: Point(x=box.x + box.width, y=end.at.y),
    }[end.facing]
    return Lane(end=end, extent=span(end.at, port_exit(far, end.facing)))


def _on_lane(one: Lane, run: Run) -> bool:
    """Whether `run` lies on the lane: directed, collinear, from the port along its facing."""
    at = one.end.at
    if one.end.facing is Facing.N:
        return run.x == run.to_x == at.x and run.to_y <= at.y
    if one.end.facing is Facing.S:
        return run.x == run.to_x == at.x and run.y >= at.y
    if one.end.facing is Facing.W:
        return run.y == run.to_y == at.y and run.to_x <= at.x
    return run.y == run.to_y == at.y and run.x >= at.x


def run_of(first: Point, second: Point) -> Run:
    """The run between two points that share exactly one coordinate."""
    return Run(
        x=min(first.x, second.x),
        y=min(first.y, second.y),
        to_x=max(first.x, second.x),
        to_y=max(first.y, second.y),
    )


def step_admitted(
    first: Cell, second: Cell, obstacles: Iterable[Obstacle], ends: frozenset[Cell]
) -> bool:
    """P1, a route step admitted closed: no obstacle touches it, but at an end cell or on a lane."""
    for obstacle in obstacles:
        if _touches(obstacle.box, first, second, ends) and not _in_a_lane(obstacle, first, second):
            return False
    return True


def run_admitted(
    first: Cell, second: Cell, obstacles: Iterable[Obstacle], ends: frozenset[Cell]
) -> bool:
    """P1 for a straight run: true iff `step_admitted` holds for every grid step of it."""
    obstacles = tuple(obstacles)
    dx = (second[0] > first[0]) - (second[0] < first[0])
    dy = (second[1] > first[1]) - (second[1] < first[1])
    length = abs(second[0] - first[0]) + abs(second[1] - first[1])
    here = first
    for done in range(0, length, WIRING_GRID):
        step = min(WIRING_GRID, length - done)
        there = (here[0] + dx * step, here[1] + dy * step)
        if not step_admitted(here, there, obstacles, ends):
            return False
        here = there
    return True


def crosses(box: Box, run: Run) -> bool:
    """P2, an interior crossing: `run` passes through the interior of `box`, both axes strict."""
    return meets((run.x, run.to_x), (box.x, box.x + box.width), closed=False) and meets(
        (run.y, run.to_y), (box.y, box.y + box.height), closed=False
    )


def crosses_unless_leaving(box: Box, run: Run, lanes: Iterable[Lane]) -> bool:
    """P2 with D2's row "a route may leave along its own port": `crosses`, but not for a leaver."""
    return crosses(box, run) and not any(_on_lane(one, run) for one in lanes)


def covers(box: Box, run: Run) -> bool:
    """P3, a closed cover: `run` meets the closed `box`, an edge or a corner is enough."""
    return meets((run.x, run.to_x), (box.x, box.x + box.width)) and meets(
        (run.y, run.to_y), (box.y, box.y + box.height)
    )


def _reaches(region: Box, box: Box) -> bool:
    """Whether `box` is near enough to `region` to touch a step inside it."""
    return boxes_meet(region, box, closed=True)


def _in_a_lane(obstacle: Obstacle, first: Cell, second: Cell) -> bool:
    """Whether the step lies wholly inside one of the obstacle's lanes."""
    step = span(Point(x=first[0], y=first[1]), Point(x=second[0], y=second[1]))
    return any(contains(one.extent, step) for one in obstacle.lanes)


def _touches(box: Box, first: Cell, second: Cell, ends: frozenset[Cell]) -> bool:
    """Whether the closed `box` meets the step, with an end that is an endpoint left out."""
    open_ends = (first in ends, second in ends)
    if first[0] == second[0]:
        if not box.x <= first[0] <= box.x + box.width:
            return False
        return _meets((first[1], second[1]), open_ends, box.y, box.y + box.height)
    if not box.y <= first[1] <= box.y + box.height:
        return False
    return _meets((first[0], second[0]), open_ends, box.x, box.x + box.width)


def _meets(reach: tuple[int, int], open_ends: tuple[bool, bool], low: int, high: int) -> bool:
    """Whether the step's `reach` meets `[low, high]`; an endpoint cell end is left out."""
    (one, other), (one_open, other_open) = reach, open_ends
    if one > other:
        one, other, one_open, other_open = other, one, other_open, one_open
    return meets((one, other), (low, high), open_a=(one_open, other_open))
