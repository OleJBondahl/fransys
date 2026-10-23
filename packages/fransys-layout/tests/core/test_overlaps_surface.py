"""`overlaps` is on the core surface: shared interior area meets, touching edges do not (R360)."""

from fransys_layout import core
from fransys_layout.core import Box, overlaps


def test_overlaps_is_a_name_of_the_core_surface():
    assert "overlaps" in core.__all__


def test_boxes_with_shared_area_overlap():
    assert overlaps(Box(0, 0, 10, 10), Box(9, 9, 10, 10))


def test_boxes_that_only_touch_or_stand_apart_do_not_overlap():
    assert not overlaps(Box(0, 0, 10, 10), Box(10, 0, 10, 10))
    assert not overlaps(Box(0, 0, 10, 10), Box(0, 11, 10, 10))
