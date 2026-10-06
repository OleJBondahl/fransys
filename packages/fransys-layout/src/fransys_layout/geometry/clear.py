"""Finding or making a free place for a box (cleanup step 2, F3)."""

from dataclasses import replace
from typing import TYPE_CHECKING, Literal

from .boxes import Box, overlaps

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def first_clear[C](
    candidates: Iterable[C],
    *,
    box_of: Callable[[C], Box],
    blocked: Callable[[Box], bool],
    default: C | None = None,
) -> C | None:
    """The first candidate whose box is not `blocked`, else `default`; candidates stay lazy."""
    return next((one for one in candidates if not blocked(box_of(one))), default)


def push_clear(box: Box, blockers: Iterable[Box], *, gap: int, axis: Literal["x", "y"]) -> Box:
    """`box` moved down (y) or right (x) until no blocker overlaps it, `gap` past the last."""
    held = tuple(blockers)
    while hit := [b for b in held if overlaps(box, b)]:
        if axis == "y":
            box = replace(box, y=max(b.y + b.height for b in hit) + gap)
        else:
            box = replace(box, x=max(b.x + b.width for b in hit) + gap)
    return box
