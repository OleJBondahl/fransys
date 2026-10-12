"""`cap_strips`, `wrap_strips`: a path along three sides of a box gets the strip behind its cap."""

from samples import hid

from fransys_layout.geometry import Box, Point
from fransys_layout.stages.space import Shape
from fransys_layout.stages.wrap import WRAP_GAP, cap_strips, wrap_strips

OWNER = hid("function", 1)
BOX = Box(x=40, y=40, width=32, height=24)
ROOM = Box(x=0, y=0, width=200, height=200)


def _path(*pairs: tuple[int, int]) -> tuple[Point, ...]:
    return tuple(Point(x=x, y=y) for x, y in pairs)


def test_a_path_left_over_and_down_the_box_gets_the_strip_above_it() -> None:
    over = _path((32, 100), (32, 32), (80, 32), (80, 100))
    assert cap_strips(over, [BOX], ROOM) == (Box(x=40, y=0, width=32, height=40),)


def test_a_path_along_two_sides_or_far_from_the_box_gets_none() -> None:
    corner = _path((32, 100), (32, 32), (80, 32))
    far = _path((8, 100), (8, 8), (120, 8), (120, 100))
    assert cap_strips(corner, [BOX], ROOM) == ()
    assert cap_strips(far, [BOX], ROOM) == ()


def test_the_cap_may_be_on_any_side() -> None:
    under = _path((32, 0), (32, 72), (80, 72), (80, 0))
    beside = _path((100, 32), (32, 32), (32, 72), (100, 72))
    assert cap_strips(under, [BOX], ROOM) == (Box(x=40, y=64, width=32, height=136),)
    assert cap_strips(beside, [BOX], ROOM) == (Box(x=0, y=40, width=40, height=24),)


OVER = _path((32, 100), (32, 32), (80, 32), (80, 100))
STRIP = Box(x=40, y=0, width=32, height=40)


def test_wrap_strips_skips_own_boxes_and_a_strip_holding_an_end_and_is_off_for_no_gap() -> None:
    shapes = (Shape(owner=OWNER, box=BOX),)
    far = (Point(x=150, y=150),)
    assert wrap_strips(OVER, shapes, set(), far, (ROOM, WRAP_GAP)) == (STRIP,)
    assert wrap_strips(OVER, shapes, {OWNER}, far, (ROOM, WRAP_GAP)) == ()
    assert wrap_strips(OVER, shapes, set(), (Point(x=50, y=10),), (ROOM, WRAP_GAP)) == ()
    assert wrap_strips(OVER, shapes, set(), far, (ROOM, None)) == ()
