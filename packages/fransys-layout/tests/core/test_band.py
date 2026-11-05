"""The band of a trunk: its lane lines (layout-0312)."""

from __future__ import annotations

import pytest

from fransys_layout.core.band import (
    arrow_hang,
    lane_offset,
    lane_rows,
    level_offset,
    trunk_room,
)


@pytest.mark.parametrize("step", [4, 8])
@pytest.mark.parametrize("lanes", [0, 1, 2, 3, 4])
def test_the_band_helpers_equal_the_formulas_they_replace(lanes: int, step: int) -> None:
    for level in range(3):
        assert level_offset(lanes, level, step) == step * (lanes + level)
    for lane in range(5):
        assert lane_offset(lane, step) == lane * step


def test_a_lane_whose_leg_column_is_the_next_lanes_driver_column_takes_the_row_behind_it() -> None:
    """R505: lane 1 stands on the driver side of lane 0; an unrelated lane keeps its row."""
    assert lane_rows([(0, 20), (20, 40), (30, 50)]) == (1, 0, 2)
    assert lane_rows([(0, 20), (20, 40), (40, 60)]) == (2, 1, 0)
    assert lane_rows([(0, 20), (10, 40), None]) == (0, 1, 2)


@pytest.mark.parametrize("lanes", [1, 2, 3])
def test_a_lane_end_arrow_keeps_its_room_under_the_last_lane(lanes: int) -> None:
    """N2, R1719: an arrow of room 16 under the last lane hangs `arrow_hang` past the band; one inside the band hangs 0."""
    assert trunk_room(lanes, 8) == (8, lanes * 8)
    assert arrow_hang(lanes, 8, 16) == 8
    assert arrow_hang(lanes, 8, 4) == 0
    assert trunk_room(lanes, 8, arrow_hang(lanes, 8, 16)) == (8, lanes * 8 + 8)
