"""The sheet's content box is built in one place."""

from fransys_layout.geometry import Box
from fransys_layout.stages.content import content_box
from fransys_layout.stages.types import SheetFormat


def test_the_content_box_spans_the_sheets_drawable_area_from_the_origin() -> None:
    sheet = SheetFormat(
        name="x", content_width=120, content_height=80, frame_columns=6, frame_rows=4
    )
    assert content_box(sheet) == Box(x=0, y=0, width=120, height=80)
