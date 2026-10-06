"""The sheet's content box: the one place `Box(0, 0, content_width, content_height)` is built."""

from typing import TYPE_CHECKING

from fransys_layout.geometry import Box

if TYPE_CHECKING:
    from .types import SheetFormat


def content_box(sheet: SheetFormat) -> Box:
    """`sheet`'s content box in page coordinates, whose edge no text may cross (S18)."""
    return Box(x=0, y=0, width=sheet.content_width, height=sheet.content_height)
