"""Axis-aligned boxes in grid units (docs/design/geometry.md 5)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import value

from .errors import GeometryError

if TYPE_CHECKING:
    from collections.abc import Iterable

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


def union(a: Box, b: Box) -> Box:
    """Return the smallest box covering both `a` and `b`."""
    x = min(a.x, b.x)
    y = min(a.y, b.y)
    return Box(
        x=x,
        y=y,
        width=max(a.x + a.width, b.x + b.width) - x,
        height=max(a.y + a.height, b.y + b.height) - y,
    )


def pad(box: Box, by: Coord) -> Box:
    """Return `box` grown by `by` on all four sides."""
    return Box(x=box.x - by, y=box.y - by, width=box.width + 2 * by, height=box.height + 2 * by)


def translate(box: Box, *, dx: Coord, dy: Coord) -> Box:
    """Return `box` moved by `(dx, dy)`."""
    return Box(x=box.x + dx, y=box.y + dy, width=box.width, height=box.height)


def hull(boxes: Iterable[Box]) -> Box:
    """The smallest box covering every one of `boxes`; none at all is a `ValueError`."""
    held = tuple(boxes)
    x0, y0 = min(b.x for b in held), min(b.y for b in held)
    x1 = max(b.x + b.width for b in held)
    y1 = max(b.y + b.height for b in held)
    return Box(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
