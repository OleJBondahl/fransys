"""Axis-aligned boxes in grid units."""

from typing import TYPE_CHECKING

from fransys_model.kernel import value

from .errors import GeometryError

if TYPE_CHECKING:
    from .units import Coord


@value
class Box:
    """An axis-aligned rectangle: top-left corner plus size."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        """Reject a box that is inside out."""
        if self.width < 0 or self.height < 0:
            msg = f"box size must not be negative, got {self.width} x {self.height}"
            raise GeometryError(msg)


def overlaps(a: Box, b: Box) -> bool:
    """Whether `a` and `b` share interior area; touching edges do not count."""
    return (
        a.width > 0
        and a.height > 0
        and b.width > 0
        and b.height > 0
        and a.x < b.x + b.width
        and b.x < a.x + a.width
        and a.y < b.y + b.height
        and b.y < a.y + a.height
    )


def contains(outer: Box, inner: Box) -> bool:
    """Whether `inner` lies entirely inside `outer`, edges included."""
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and inner.x + inner.width <= outer.x + outer.width
        and inner.y + inner.height <= outer.y + outer.height
    )


def translate(box: Box, *, dx: Coord, dy: Coord) -> Box:
    """Return `box` moved by `(dx, dy)`."""
    return Box(x=box.x + dx, y=box.y + dy, width=box.width, height=box.height)
