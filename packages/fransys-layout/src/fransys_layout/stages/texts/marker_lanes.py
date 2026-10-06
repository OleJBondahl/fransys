"""WIRE-X56: a port's lane on a page and its plain-int reach, what marker rows test against."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Point,
    meets,
    port_page_at,
    translate,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.types import BodyBox, PlacedFunction
    from fransys_model.kernel import Id

FAR = 1 << 20  # the clamp's bound is x only: no marker is refused for its y

type Reach = tuple[int, int, int]  # a lane's x and its y-extent low and high: plain ints


@dataclass(frozen=True, slots=True)
class Lane:
    """A port's lane: its function, its port, its x, the y it starts at, its facing, its end."""

    function: Id[Any]
    port: Id[Any]
    x: int
    y: int
    facing: Facing
    end: int


def lanes_of(here: Sequence[PlacedFunction], model_port: Mapping[Any, Any]) -> tuple[Lane, ...]:
    """WIRE-X56: the lane of every N or S port of the page, from the port outward (S20 8b)."""
    bodies = [
        (one.function, translate(one.geometry.body, dx=one.at.x, dy=one.at.y)) for one in here
    ]
    found = []
    for one in here:
        for g in one.geometry.ports:
            port = model_port.get((one.function, g.name))
            if port is None or g.facing not in (Facing.N, Facing.S):
                continue
            at = port_page_at(one.at, g)
            end = _lane_end(one.function, at, g.facing, bodies)
            found.append(
                Lane(function=one.function, port=port, x=at.x, y=at.y, facing=g.facing, end=end)
            )
    return tuple(found)


def _lane_end(function: Id[Any], at: Point, facing: Facing, bodies: Sequence[BodyBox]) -> int:
    """The y a lane from `at` stops at: the near edge of the next other function's body on x."""
    spanning = [
        box for other, box in bodies if other != function and box.x <= at.x <= box.x + box.width
    ]
    if facing is Facing.S:
        return min((b.y for b in spanning if b.y >= at.y), default=FAR)
    return max((b.y + b.height for b in spanning if b.y + b.height <= at.y), default=-FAR)


def reach_of(lanes: Sequence[Lane]) -> tuple[Reach, ...]:
    """Each lane as plain ints, built once per row: its x and the y-extent it runs over."""
    return tuple((lane.x, min(lane.y, lane.end), max(lane.y, lane.end)) for lane in lanes)


def meets_lane(box: Box, lane: Reach) -> bool:
    """Whether `box`'s y-extent meets the lane's, which runs from its port outward to its end."""
    return meets((lane[1], lane[2]), (box.y, box.y + box.height), closed=False)


def on_lane(box: Box, lane: Reach, *, clear: bool) -> bool:
    """WIRE-X56: `box` on the lane: covering it closed, or within one grid of it when `clear`."""
    near = (box.x - WIRING_GRID * clear, box.x + box.width + WIRING_GRID * clear)
    return meets(near, (lane[0], lane[0]), closed=not clear) and meets_lane(box, lane)
