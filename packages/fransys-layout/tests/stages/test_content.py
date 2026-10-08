"""The sheet's content box is built in one place."""

from fransys_layout.geometry import Box
from fransys_layout.stages.content import content_box, drawn_extent
from fransys_layout.stages.types import SheetFormat


def test_the_content_box_spans_the_sheets_drawable_area_from_the_origin() -> None:
    sheet = SheetFormat(
        name="x", content_width=120, content_height=80, frame_columns=6, frame_rows=4
    )
    assert content_box(sheet) == Box(x=0, y=0, width=120, height=80)


def test_an_overfull_page_extends_the_extent_by_the_room_past_each_edge_it_passes() -> None:
    content = Box(x=0, y=0, width=120, height=80)
    below = Box(x=8, y=60, width=16, height=40)
    assert drawn_extent(content, [below], 48) == Box(x=0, y=0, width=120, height=148)


def test_a_page_inside_its_content_box_has_the_content_box_as_extent() -> None:
    content = Box(x=0, y=0, width=120, height=80)
    assert drawn_extent(content, [Box(x=8, y=60, width=16, height=20)], 48) == content
