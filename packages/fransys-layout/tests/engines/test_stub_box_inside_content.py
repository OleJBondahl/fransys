"""A stub box that grows with its far positions slides inside the content box, never out (5b)."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from fransys_layout.engines.schematic.read.line_texts import _inside
from fransys_layout.geometry import Box

if TYPE_CHECKING:
    from fransys_layout.stages.types import SheetFormat

SHEET = cast("SheetFormat", SimpleNamespace(content_width=400, content_height=400))  # all it reads


def test_a_box_over_the_left_edge_slides_right_and_one_inside_stays() -> None:
    inside = Box(x=40, y=8, width=20, height=12)
    assert _inside(inside, SHEET) == inside
    out = Box(x=-4, y=8, width=20, height=12)
    assert _inside(out, SHEET).x == 0
    right = Box(x=390, y=8, width=20, height=12)
    assert _inside(right, SHEET).x + 20 <= 400


def test_no_sheet_leaves_the_box_alone() -> None:
    box = Box(x=-4, y=8, width=20, height=12)
    assert _inside(box, None) == box
