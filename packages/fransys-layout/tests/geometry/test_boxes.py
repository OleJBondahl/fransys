"""WP1: `geometry.boxes` (ROADMAP WP1, docs/design/geometry.md 5)."""

import dataclasses

import pytest

from fransys_layout.geometry import (
    Box,
    GeometryError,
    LayoutError,
    contains,
    hull,
    overlaps,
    pad,
    translate,
    union,
)
from fransys_model.kernel import ModelError


def test_overlapping_boxes_overlap() -> None:
    """Boxes sharing interior area overlap, in either argument order."""
    a = Box(x=0, y=0, width=16, height=16)
    b = Box(x=8, y=8, width=16, height=16)
    assert overlaps(a, b)
    assert overlaps(b, a)


def test_touching_boxes_do_not_overlap() -> None:
    """Boxes that share only an edge do not overlap."""
    a = Box(x=0, y=0, width=16, height=16)
    b = Box(x=16, y=0, width=16, height=16)
    assert not overlaps(a, b)


def test_contains_includes_the_edges_and_can_fail() -> None:
    """A box contains itself; a box sticking out by one unit is not contained."""
    outer = Box(x=0, y=0, width=32, height=32)
    assert contains(outer, outer)
    assert not contains(outer, Box(x=0, y=0, width=33, height=32))


def test_union_covers_both() -> None:
    """The union is the smallest box covering both arguments."""
    a = Box(x=0, y=0, width=8, height=8)
    b = Box(x=16, y=-8, width=8, height=8)
    assert union(a, b) == Box(x=0, y=-8, width=24, height=16)


def test_translate_moves_without_resizing() -> None:
    """`translate` shifts the corner and keeps the size."""
    assert translate(Box(x=0, y=0, width=8, height=8), dx=16, dy=-8) == Box(
        x=16, y=-8, width=8, height=8
    )


def test_pad_grows_all_four_sides() -> None:
    """`pad` by 8 moves the corner out by 8 and adds 16 to each size."""
    assert pad(Box(x=0, y=0, width=8, height=8), 8) == Box(x=-8, y=-8, width=24, height=24)


def test_a_negative_size_raises_and_zero_is_allowed() -> None:
    """A box cannot be inside out; a degenerate one is a legal value."""
    assert Box(x=0, y=0, width=0, height=0).width == 0
    with pytest.raises(GeometryError):
        Box(x=0, y=0, width=-1, height=8)
    with pytest.raises(GeometryError):
        Box(x=0, y=0, width=8, height=-1)


def test_box_is_frozen() -> None:
    """A `Box` cannot be mutated. Its `int` fields are enforced by `ty`, not at runtime."""
    box = Box(x=0, y=0, width=8, height=8)
    with pytest.raises(dataclasses.FrozenInstanceError):
        box.x = 1  # ty: ignore[invalid-assignment] -- assigning to a frozen field, testing the refusal named in the raises


def test_layout_error_is_a_model_error() -> None:
    """Everything this repo raises can be caught as the model's `ModelError`."""
    assert issubclass(LayoutError, ModelError)
    assert issubclass(GeometryError, LayoutError)


def test_boxes_separated_on_one_axis_do_not_overlap() -> None:
    """Overlapping x ranges are not enough: y must overlap too, and the reverse."""
    a = Box(x=0, y=0, width=16, height=16)
    assert not overlaps(a, Box(x=8, y=16, width=16, height=16))
    assert not overlaps(a, Box(x=16, y=8, width=16, height=16))
    assert not overlaps(a, Box(x=32, y=0, width=16, height=16))


def test_corner_touching_boxes_do_not_overlap_but_one_unit_of_depth_does() -> None:
    """A shared corner is not overlap; moving one box one unit inward is."""
    a = Box(x=0, y=0, width=16, height=16)
    assert not overlaps(a, Box(x=16, y=16, width=16, height=16))
    assert overlaps(a, Box(x=15, y=15, width=16, height=16))


def test_a_box_inside_another_overlaps_it_and_a_box_overlaps_itself() -> None:
    """Containment and equality are overlap."""
    outer = Box(x=0, y=0, width=32, height=32)
    assert overlaps(outer, Box(x=8, y=8, width=8, height=8))
    assert overlaps(outer, outer)


def test_a_zero_area_box_overlaps_nothing() -> None:
    """A degenerate box has no interior, even when it lies inside another box."""
    outer = Box(x=0, y=0, width=32, height=32)
    zero_width = Box(x=8, y=8, width=0, height=8)
    zero_height = Box(x=8, y=8, width=8, height=0)
    for degenerate in (zero_width, zero_height):
        assert not overlaps(outer, degenerate)
        assert not overlaps(degenerate, outer)
    assert overlaps(outer, Box(x=8, y=8, width=1, height=1))


def test_contains_fails_on_each_of_the_four_sides() -> None:
    """A box sticking out by one unit on any side is not contained; flush edges are."""
    outer = Box(x=0, y=0, width=32, height=32)
    assert contains(outer, Box(x=0, y=0, width=32, height=32))
    assert contains(outer, Box(x=8, y=8, width=24, height=24))
    assert not contains(outer, Box(x=-1, y=0, width=8, height=8))
    assert not contains(outer, Box(x=0, y=-1, width=8, height=8))
    assert not contains(outer, Box(x=25, y=0, width=8, height=8))
    assert not contains(outer, Box(x=0, y=25, width=8, height=8))


def test_contains_is_not_symmetric() -> None:
    """The outer box contains the inner one and not the other way round."""
    outer = Box(x=0, y=0, width=32, height=32)
    inner = Box(x=8, y=8, width=8, height=8)
    assert contains(outer, inner)
    assert not contains(inner, outer)


def test_union_is_symmetric_and_a_nested_pair_gives_the_outer_box() -> None:
    """The union of nested boxes is the outer one, in either order."""
    outer = Box(x=0, y=0, width=32, height=32)
    inner = Box(x=8, y=8, width=8, height=8)
    assert union(outer, inner) == outer
    assert union(inner, outer) == outer
    a = Box(x=0, y=0, width=8, height=8)
    b = Box(x=16, y=-8, width=8, height=8)
    assert union(a, b) == union(b, a)


def test_translate_by_zero_is_the_identity() -> None:
    """A zero shift returns an equal box."""
    box = Box(x=3, y=-5, width=7, height=9)
    assert translate(box, dx=0, dy=0) == box


def test_pad_by_zero_is_the_identity_and_negative_pad_shrinks() -> None:
    """`pad` by 0 changes nothing; by -4 an 8-square becomes a point."""
    box = Box(x=0, y=0, width=8, height=8)
    assert pad(box, 0) == box
    assert pad(box, -4) == Box(x=4, y=4, width=0, height=0)


def test_pad_that_would_invert_the_box_raises() -> None:
    """Shrinking past zero raises; stopping at zero does not."""
    box = Box(x=0, y=0, width=8, height=8)
    with pytest.raises(GeometryError):
        pad(box, -5)


@pytest.mark.parametrize(
    ("touching", "one_unit_closer"),
    [
        ((16, 0), (15, 0)),
        ((-16, 0), (-15, 0)),
        ((0, 16), (0, 15)),
        ((0, -16), (0, -15)),
    ],
)
def test_boxes_touching_on_any_of_the_four_sides_do_not_overlap(
    touching: tuple[int, int], one_unit_closer: tuple[int, int]
) -> None:
    """Each edge is tested: right, left, below and above, and one unit closer overlaps."""
    a = Box(x=0, y=0, width=16, height=16)
    b = Box(x=touching[0], y=touching[1], width=16, height=16)
    closer = Box(x=one_unit_closer[0], y=one_unit_closer[1], width=16, height=16)
    assert not overlaps(a, b)
    assert not overlaps(b, a)
    assert overlaps(a, closer)


def test_hull_covers_every_box_and_a_point_box_is_a_member() -> None:
    """The hull spans all boxes, a zero-size one included; one box is its own hull."""
    a = Box(x=0, y=0, width=8, height=8)
    point = Box(x=20, y=-4, width=0, height=0)
    assert hull([a]) == a
    assert hull([a, point]) == Box(x=0, y=-4, width=20, height=12)
    assert hull(iter([a, point])) == hull([point, a])


def test_hull_of_nothing_is_a_value_error() -> None:
    """There is no empty box to return."""
    with pytest.raises(ValueError, match="empty"):
        hull([])
