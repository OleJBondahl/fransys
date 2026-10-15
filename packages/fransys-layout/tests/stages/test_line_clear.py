"""Layout-0246: a fan split and a box end keep off wires and keep-outs."""

from samples import hid

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages.line_draw import Fan
from fransys_layout.stages.line_shapes import DrawnLeg
from fransys_layout.stages.line_side import (
    clear_column,
    fan_clear,
    fan_on_wire,
    split_in,
    stub_cover,
)
from fransys_layout.stages.space import End, Obstacle

SPLIT = Point(x=120, y=328)


def _leg(name: int, *points: tuple[int, int]) -> DrawnLeg:
    return DrawnLeg(
        conductor=hid("conductor", name), points=tuple(Point(x=x, y=y) for x, y in points)
    )


def _fan(*legs: DrawnLeg) -> Fan:
    return Fan(1, SPLIT, legs, (), Facing.N)


def test_a_split_on_a_wire_is_not_clear() -> None:
    wire = Box(x=32, y=328, width=96, height=0)
    fan = _fan(_leg(1, (120, 328), (112, 336), (112, 344)))
    assert fan_on_wire(fan, [wire])
    assert not fan_clear(fan, [wire])
    assert fan_clear(fan, [])
    assert fan_clear(None, [wire])


def test_two_legs_sharing_a_run_are_not_clear() -> None:
    fan = _fan(
        _leg(1, (120, 336), (136, 336), (136, 344)),
        _leg(2, (120, 336), (152, 336), (152, 344)),
    )
    assert not fan_clear(fan, [])
    apart = _fan(_leg(1, (120, 336), (112, 336), (112, 344)), _leg(2, (120, 336), (136, 336)))
    assert fan_clear(apart, [])


def test_a_leg_touching_a_keep_out_that_holds_not_its_pin_is_not_clear() -> None:
    fan = _fan(_leg(1, (120, 328), (120, 336), (112, 344)))
    body = Obstacle(Box(x=116, y=330, width=8, height=8), ())
    assert not fan_clear(fan, [], [body])
    assert fan_clear(fan, [], [Obstacle(Box(x=0, y=0, width=8, height=8), ())])


def test_a_split_on_a_keep_outs_edge_is_in_it_unless_the_keep_out_holds_a_pin() -> None:
    fan = _fan(_leg(1, (120, 328), (112, 344)))
    edge = Obstacle(Box(x=104, y=312, width=16, height=16), ())
    assert not split_in(None, [edge])
    assert split_in(fan, [Obstacle(Box(x=120, y=328, width=16, height=16), ())])
    assert not split_in(fan, [Obstacle(Box(x=104, y=312, width=64, height=48), ())])


def test_a_box_end_slides_to_the_nearest_column_clear_of_a_wire() -> None:
    box = Box(x=16, y=32, width=64, height=32)
    end = End(at=Point(x=48, y=32), facing=Facing.N)
    wire = Box(x=48, y=16, width=0, height=16)
    moved = clear_column(end, box, None, [wire], [])
    assert moved.at == Point(x=40, y=32)
    assert clear_column(end, box, None, [], []) == end


def test_a_leaving_end_takes_the_far_edge_when_every_column_is_blocked() -> None:
    box = Box(x=16, y=64, width=32, height=32)
    end = End(at=Point(x=32, y=64), facing=Facing.N)
    lane = Box(x=0, y=16, width=200, height=0)
    moved = clear_column(end, box, (56, 12), [lane], [])
    assert moved.facing is Facing.S
    assert moved.at.y == 96


def test_a_stub_box_is_covered_by_the_keep_outs_and_wires_it_lies_on() -> None:
    """The stub text box stands below its tip; its area on keep-outs, or the whole box on a wire."""
    end = End(at=Point(x=408, y=480), facing=Facing.S)
    size = (67, 12)  # the box is x 375 to 442, y 488 to 500
    symbol = Obstacle(Box(x=432, y=474, width=32, height=38), ())
    assert stub_cover(end, size, [symbol], []) == 10 * 12
    assert stub_cover(end, size, [Obstacle(Box(x=0, y=0, width=8, height=8), ())], []) == 0
    wire = Box(x=400, y=470, width=0, height=40)
    assert stub_cover(end, size, [], [wire]) == 67 * 12
