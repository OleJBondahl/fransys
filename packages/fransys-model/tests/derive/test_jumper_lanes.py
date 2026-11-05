"""Jumper groups take lanes by first fit over their row spans (pdf-0007)."""

import pytest

from fransys_model.derive import first_fit_lanes, jumper_lane_count, jumper_lanes


def _lanes(result):
    return [(lane.group, lane.first, lane.last, lane.lane) for lane in result.lanes]


def test_no_group_uses_no_lane():
    result = jumper_lanes((None, None))
    assert jumper_lane_count(result) == 0
    assert result.lanes == ()


@pytest.mark.parametrize(
    ("groups", "lanes", "count"),
    [
        ((1, 1, None, 2, 2), [(1, 0, 1, 0), (2, 3, 4, 0)], 1),  # non-overlapping groups share lane zero
        ((1, 2, 1, 2), [(1, 0, 2, 0), (2, 1, 3, 1)], 2),  # overlapping groups get two lanes
        ((1, 2, 1, 3, 3), [(1, 0, 2, 0), (2, 1, 1, 1), (3, 3, 4, 0)], 2),  # group 3 starts after group 1 ends and reuses lane zero
        ((2, 1, 2, 1), [(1, 1, 3, 0), (2, 0, 2, 1)], 2),  # groups place by group number, not row order
    ],
)
def test_groups_take_lanes_by_first_fit_in_group_number_order(groups, lanes, count):
    result = jumper_lanes(groups)
    assert _lanes(result) == lanes
    assert jumper_lane_count(result) == count


def test_first_fit_lanes_follows_the_free_before_first_rule():
    # span 3 starts at row 3; lane 0 is last used through row 2, so it is free and takes lane 0
    assert first_fit_lanes([(0, 2), (1, 3), (3, 4)]) == (0, 1, 0)
    assert first_fit_lanes([]) == ()
    # a span that starts on the row another ends on overlaps it: its own lane
    assert first_fit_lanes([(0, 2), (2, 3)]) == (0, 1)
