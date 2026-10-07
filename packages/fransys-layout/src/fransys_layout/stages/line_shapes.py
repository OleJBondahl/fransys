"""HL15 to HL18 (layout-0154): a harness line's drawn pieces on one page, as `write/` takes them."""

from typing import Any

from fransys_layout.geometry import Box, Facing, Point
from fransys_model.kernel import Id, value


@value
class DrawnLine:
    """One branch's polyline on one page; `text` is its designation's centre, `label` its box."""

    harness: Id[Any]
    branch: int
    drawing_set: int
    page: int
    points: tuple[Point, ...]
    text: Point
    label: Box


@value
class DrawnLeg:
    """One fan-out leg: the conductor it draws and its points, split first, pin last (HL17)."""

    conductor: Id[Any]
    points: tuple[Point, ...]


@value
class DrawnFanOut:
    """One branch's fan-out on one page: its split point and one leg per conductor (HL8, HL17)."""

    harness: Id[Any]
    branch: int
    drawing_set: int
    page: int
    at: Point
    legs: tuple[DrawnLeg, ...]


@value
class LineStub:
    """A leaving line's one stub (HL18): at the line's end, facing out, its text's box size.

    `port` is the near end's port and `far` the far end's, as an off stub names them.
    """

    harness: Id[Any]
    branch: int
    drawing_set: int
    page: int
    port: Id[Any]
    far: Id[Any]
    at: Point
    facing: Facing
    box: Box
