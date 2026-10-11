"""`line_shapes.slant_boxes`: thin boxes along a slanted polyline, so a label can stand by it."""

from fransys_layout.geometry import Box, Point
from fransys_layout.stages.line_shapes import slant_boxes


def _inside(point: Point, box: Box) -> bool:
    return box.x < point.x < box.x + box.width and box.y < point.y < box.y + box.height


def test_a_slant_is_boxed_along_its_line_and_not_across_its_bounding_box() -> None:
    """The slant (0,0)-(32,16) leaves its far corner (0,16) free, and covers its middle.

    UNDO: `slant_boxes` returns one box per segment: the bounding box holds (4, 12).
    """
    boxes = slant_boxes((Point(x=0, y=0), Point(x=32, y=16)))
    assert any(_inside(Point(x=14, y=7), box) for box in boxes)
    assert not any(_inside(Point(x=4, y=12), box) for box in boxes)
    assert len(boxes) == 8


def test_an_axis_run_gets_boxes_of_its_own_length_and_no_width() -> None:
    boxes = slant_boxes((Point(x=0, y=0), Point(x=0, y=8)))
    assert [(b.x, b.width, b.y + b.height) for b in boxes] == [(0, 0, 4), (0, 0, 8)]
