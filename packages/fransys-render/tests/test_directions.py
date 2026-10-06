"""Unit directions a wire leaves a grid point (spec D8, `_junctions._directions`)."""

from fransys_render._junctions import _directions


def test_inside_horizontal_segment_gives_both_x_directions() -> None:
    assert _directions((5, 0), [((0, 0), (10, 0))]) == {(1, 0), (-1, 0)}


def test_inside_vertical_segment_gives_both_y_directions() -> None:
    assert _directions((0, 5), [((0, 0), (0, 10))]) == {(0, 1), (0, -1)}


def test_vertical_segment_min_end_gives_one_direction() -> None:
    assert _directions((0, 0), [((0, 0), (0, 10))]) == {(0, 1)}


def test_vertical_segment_max_end_gives_one_direction() -> None:
    assert _directions((0, 10), [((0, 0), (0, 10))]) == {(0, -1)}


def test_horizontal_segment_min_end_gives_one_direction() -> None:
    assert _directions((0, 0), [((0, 0), (10, 0))]) == {(1, 0)}


def test_horizontal_segment_max_end_gives_one_direction() -> None:
    assert _directions((10, 0), [((0, 0), (10, 0))]) == {(-1, 0)}


def test_junction_of_three_segments() -> None:
    segments = [((0, 5), (10, 5)), ((5, 5), (5, 10))]
    assert _directions((5, 5), segments) == {(1, 0), (-1, 0), (0, 1)}


def test_point_past_vertical_segment_end_gives_no_direction() -> None:
    assert _directions((0, 11), [((0, 0), (0, 10))]) == set()


def test_vertical_segment_off_axis_gives_no_direction() -> None:
    assert _directions((0, 5), [((5, 0), (5, 10))]) == set()


def test_horizontal_segment_off_axis_gives_no_direction() -> None:
    assert _directions((5, 0), [((0, 5), (10, 5))]) == set()
