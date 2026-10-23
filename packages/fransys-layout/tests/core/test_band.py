"""The band of a trunk: its lane lines (layout-0312)."""

from __future__ import annotations

import pytest

from fransys_layout.core.band import (
    band_extent,
    centred_span,
    lane_offset,
    lane_offsets,
    lane_rows,
    level_offset,
    on_band_side,
)


@pytest.mark.parametrize(
    ("lanes", "step", "offsets", "extent"),
    [
        (1, 8, (0,), (0, 0)),
        (2, 8, (0, 8), (0, 8)),
        (3, 8, (0, 8, 16), (0, 16)),
        (1, 4, (0,), (0, 0)),
        (2, 4, (0, 4), (0, 4)),
        (3, 4, (0, 4, 8), (0, 8)),
    ],
)
def test_the_band_is_the_lane_lines_from_the_trunk_line(
    lanes: int, step: int, offsets: tuple[int, ...], extent: tuple[int, int]
) -> None:
    assert lane_offsets(lanes, step) == offsets
    assert band_extent(lanes, step) == extent


@pytest.mark.parametrize("step", [4, 8])
@pytest.mark.parametrize("lanes", [0, 1, 2, 3, 4])
def test_the_band_helpers_equal_the_formulas_they_replace(lanes: int, step: int) -> None:
    assert centred_span(lanes, step) == lanes * step * 2
    for level in range(3):
        assert level_offset(lanes, level, step) == step * (lanes + level)
    for lane in range(5):
        assert lane_offset(lane, step) == lane * step


def test_the_band_grows_towards_east_and_south_only() -> None:
    assert [on_band_side(s) for s in "NESW"] == [False, True, True, False]


def test_a_lane_whose_leg_column_is_the_next_lanes_driver_column_takes_the_row_behind_it() -> None:
    """R505: lane 1 stands on the driver side of lane 0; an unrelated lane keeps its row."""
    assert lane_rows([(0, 20), (20, 40), (30, 50)]) == (1, 0, 2)
    assert lane_rows([(0, 20), (20, 40), (40, 60)]) == (2, 1, 0)
    assert lane_rows([(0, 20), (10, 40), None]) == (0, 1, 2)
