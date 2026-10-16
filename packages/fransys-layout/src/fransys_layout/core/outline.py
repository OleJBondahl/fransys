"""A padded bounding box around boxes, with optional left and top edge floors (layout-0300)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .values import Box

if TYPE_CHECKING:
    from collections.abc import Sequence


def outline_hull(
    boxes: Sequence[Box],
    margin: int,
    *,
    floor_x: int | None = None,
    floor_y: int | None = None,
) -> Box:
    """The smallest box holding every box, grown by margin on all four sides.

    The left edge never goes below floor_x, nor the top edge below floor_y; the right
    and bottom edges stay where the margin puts them. The caller passes a margin on its grid.
    """
    if not boxes:
        msg = "outline_hull: no boxes; pass at least one box to outline"
        raise ValueError(msg)
    if margin < 0:
        msg = f"outline_hull: margin {margin} is negative; pass 0 or more"
        raise ValueError(msg)
    x0 = min(b.x for b in boxes) - margin
    y0 = min(b.y for b in boxes) - margin
    x1 = max(b.x + b.w for b in boxes) + margin
    y1 = max(b.y + b.h for b in boxes) + margin
    if floor_x is not None:
        x0 = max(x0, floor_x)
    if floor_y is not None:
        y0 = max(y0, floor_y)
    return Box(x0, y0, x1 - x0, y1 - y0)
