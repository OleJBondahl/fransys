"""Jumper groups take lanes by first fit over their row spans (pdf-0007)."""

from fransys_model.derive import first_fit_lanes, jumper_lane_count, jumper_lanes


def _lanes(result):
    return [(lane.group, lane.first, lane.last, lane.lane) for lane in result.lanes]


def test_no_group_uses_no_lane():
    result = jumper_lanes((None, None))
    assert jumper_lane_count(result) == 0
    assert result.lanes == ()


def test_non_overlapping_groups_share_lane_zero():
    result = jumper_lanes((1, 1, None, 2, 2))
    assert _lanes(result) == [(1, 0, 1, 0), (2, 3, 4, 0)]
    assert jumper_lane_count(result) == 1


def test_overlapping_groups_get_two_lanes():
    result = jumper_lanes((1, 2, 1, 2))
    assert _lanes(result) == [(1, 0, 2, 0), (2, 1, 3, 1)]
    assert jumper_lane_count(result) == 2


def test_third_group_after_first_ends_reuses_lane_zero():
    # group 1 spans rows 0-2, group 2 rows 1-1 (lane 1), group 3 rows 3-4 (lane 0: 2 < 3)
    result = jumper_lanes((1, 2, 1, 3, 3))
    assert _lanes(result) == [(1, 0, 2, 0), (2, 1, 1, 1), (3, 3, 4, 0)]
    assert jumper_lane_count(result) == 2


def test_groups_place_by_group_number_not_row_order():
    # group 2 starts first in the rows, but group 1 is placed first and takes lane 0
    result = jumper_lanes((2, 1, 2, 1))
    assert _lanes(result) == [(1, 1, 3, 0), (2, 0, 2, 1)]
    assert jumper_lane_count(result) == 2


def test_first_fit_lanes_follows_the_free_before_first_rule():
    # span 3 starts at row 3; lane 0 is last used through row 2, so it is free and takes lane 0
    assert first_fit_lanes([(0, 2), (1, 3), (3, 4)]) == (0, 1, 0)
    assert first_fit_lanes([]) == ()
    # a span that starts on the row another ends on overlaps it: its own lane
    assert first_fit_lanes([(0, 2), (2, 3)]) == (0, 1)
