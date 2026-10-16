"""Tests for core/outline.py: the padded hull around boxes (layout-0300)."""

import pytest

from fransys_layout.core.outline import outline_hull
from fransys_layout.core.values import Box


def test_one_box_grows_by_margin():
    assert outline_hull([Box(10, 20, 30, 40)], 4) == Box(6, 16, 38, 48)


def test_two_apart_boxes_span_both():
    assert outline_hull([Box(0, 0, 10, 10), Box(20, 30, 5, 5)], 2) == Box(-2, -2, 29, 39)


def test_nested_inner_box_is_ignored():
    assert outline_hull([Box(0, 0, 100, 50), Box(10, 10, 5, 5)], 3) == Box(-3, -3, 106, 56)


def test_touching_boxes_join_without_gap():
    assert outline_hull([Box(0, 0, 10, 10), Box(10, 0, 10, 10)], 0) == Box(0, 0, 20, 10)


def test_zero_size_box_is_a_point():
    assert outline_hull([Box(7, 8, 0, 0)], 2) == Box(5, 6, 4, 4)


def test_margin_zero_is_the_box_itself():
    assert outline_hull([Box(10, 20, 30, 40)], 0) == Box(10, 20, 30, 40)


def test_floor_x_clamps_left_edge_only():
    assert outline_hull([Box(10, 20, 30, 40)], 4, floor_x=8) == Box(8, 16, 36, 48)


def test_floor_y_clamps_top_edge_only():
    assert outline_hull([Box(10, 20, 30, 40)], 4, floor_y=20) == Box(6, 20, 38, 44)


def test_floor_below_natural_edge_changes_nothing():
    assert outline_hull([Box(10, 20, 30, 40)], 4, floor_x=0, floor_y=0) == Box(6, 16, 38, 48)


def test_empty_boxes_raise():
    with pytest.raises(ValueError, match="no boxes"):
        outline_hull([], 4)


def test_negative_margin_raises():
    with pytest.raises(ValueError, match="negative"):
        outline_hull([Box(0, 0, 1, 1)], -1)


def test_hull_takes_each_edge_from_whichever_box_reaches_furthest():
    boxes = [Box(10, 0, 10, 10), Box(0, 5, 5, 20)]
    assert outline_hull(boxes, 1) == Box(-1, -1, 22, 27)
