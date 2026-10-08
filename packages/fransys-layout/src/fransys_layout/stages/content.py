"""The sheet's content box: the one place `Box(0, 0, content_width, content_height)` is built.

Also the page's drawn extent, the box a harness line routes in (layout-0166).
"""

from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, hull

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .types import SheetFormat


def content_box(sheet: SheetFormat) -> Box:
    """`sheet`'s content box in page coordinates, whose edge no text may cross (S18)."""
    return Box(x=0, y=0, width=sheet.content_width, height=sheet.content_height)


def drawn_extent(content: Box, keepouts: Iterable[Box], room: int) -> Box:
    """The content box joined with every placed keep-out, and `room` more past each edge it passes.

    A line's fan-out and stub stand `room` outside the pins' keep-outs (layout-0166). A page that
    is not overfull (`PAGE_OVERFULL`, layout-0083) has the content box itself.
    """
    joined = hull((content, *keepouts))
    x0 = joined.x - room * (joined.x < content.x)
    y0 = joined.y - room * (joined.y < content.y)
    x1 = joined.x + joined.width + room * (joined.x + joined.width > content.x + content.width)
    y1 = joined.y + joined.height + room * (joined.y + joined.height > content.y + content.height)
    return Box(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
