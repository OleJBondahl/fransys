"""`fan_tags.tags_out_of_fans`: a tag a side fan wraps takes its symbol's mirror side."""

from samples import SHEET, hid, through_geometry

from fransys_layout.geometry import Box, Point
from fransys_layout.stages.fan_tags import tags_out_of_fans
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLeg
from fransys_layout.stages.types import LabelKind, PlacedFunction, PlacedLabel

_F = hid("function", 1)


def _function() -> PlacedFunction:
    return PlacedFunction(
        function=_F,
        drawing_set=1,
        page=1,
        column=(),
        at=Point(x=100, y=100),
        geometry=through_geometry(),
    )


def _tag(x: int) -> PlacedLabel:
    box = Box(x=x, y=96, width=32, height=8)
    return PlacedLabel(kind=LabelKind.TAG, subject=_F, slot="tag", drawing_set=1, page=1, box=box)


def _fan(*, legs: int = 2) -> DrawnFanOut:
    split = Point(x=160, y=100)
    ends = (Point(x=100, y=84), Point(x=100, y=116))[:legs]
    drawn = tuple(
        DrawnLeg(conductor=hid("conductor", n), points=(split, Point(x=140, y=end.y), end))
        for n, end in enumerate(ends)
    )
    return DrawnFanOut(
        harness=hid("harness", 1), branch=1, drawing_set=1, page=1, at=split, legs=drawn
    )


def test_a_tag_inside_a_side_fans_outline_moves_to_its_symbols_mirror_side() -> None:
    """The tag east of the symbol, between the fan's legs, stands west of it after.

    UNDO: `tags_out_of_fans` returns its labels as given, and the tag stays at x 116.
    """
    (moved,) = tags_out_of_fans([_tag(116)], [_function()], [_fan()], [], SHEET)
    assert moved.box == Box(x=52, y=96, width=32, height=8)


def test_a_tag_a_lone_leg_does_not_wrap_stays() -> None:
    (kept,) = tags_out_of_fans([_tag(116)], [_function()], [_fan(legs=1)], [], SHEET)
    assert kept.box.x == 116


def test_a_tag_stays_when_its_mirror_place_is_taken() -> None:
    """A label on the west side keeps the tag where it is: the fan check will report it."""
    west = PlacedLabel(
        kind=LabelKind.MARKING,
        subject=_F,
        slot="m",
        drawing_set=1,
        page=1,
        box=Box(x=52, y=96, width=32, height=8),
    )
    kept = tags_out_of_fans([_tag(116), west], [_function()], [_fan()], [], SHEET)
    assert kept[0].box.x == 116


def test_a_tag_a_south_opening_fan_wraps_moves_to_its_symbols_north_side() -> None:
    """A fan opening south of the symbol wraps the tag standing below it: the tag goes above.

    UNDO: `_mirrored` always mirrors x, and the tag stays at y 118.
    """
    tag = PlacedLabel(
        kind=LabelKind.TAG,
        subject=_F,
        slot="tag",
        drawing_set=1,
        page=1,
        box=Box(x=92, y=118, width=32, height=8),
    )
    split = Point(x=108, y=150)
    legs = tuple(
        DrawnLeg(
            conductor=hid("conductor", n), points=(split, Point(x=x, y=128), Point(x=x, y=116))
        )
        for n, x in enumerate((96, 120))
    )
    fan = DrawnFanOut(
        harness=hid("harness", 1), branch=1, drawing_set=1, page=1, at=split, legs=legs
    )
    (moved,) = tags_out_of_fans([tag], [_function()], [fan], [], SHEET)
    assert moved.box == Box(x=92, y=74, width=32, height=8)
