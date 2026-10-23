"""Corridors between bands: plain values, no overview types."""

from hypothesis import given, settings
from hypothesis import strategies as st

from fransys_layout.engines.overview.lanes.corridor import (
    corridor_height,
    corridor_y,
    plan_corridors,
)

BANDS = 2


def test_long_line_takes_a_corridor_and_a_short_one_none():
    plan = plan_corridors([(1, 0, 1, 0, 3), (2, 0, 1, 0, 1)], BANDS)
    assert plan.corridor == {1: 1}
    assert plan.load == (0, 1, 0)


def test_two_lines_share_a_corridor_with_distinct_ranks():
    plan = plan_corridors([(1, 0, 1, 0, 3), (2, 0, 1, 1, 4)], BANDS)
    assert plan.corridor[1] == plan.corridor[2] == 1
    assert plan.rank == {1: 0, 2: 1}


def test_loads_differ_so_corridors_differ_within_one_band():
    plan = plan_corridors([(1, 0, 0, 0, 3), (2, 0, 0, 1, 4)], BANDS)
    assert sorted(plan.corridor.values()) == [0, 1]
    assert plan.load == (1, 1, 0)


def test_a_tie_in_one_band_goes_below_and_between_bands_to_the_lower_index():
    assert plan_corridors([(1, 1, 1, 0, 3)], 3).corridor == {1: 2}
    assert plan_corridors([(1, 0, 2, 0, 3)], 3).corridor == {1: 1}


def test_input_order_does_not_matter():
    lines = [(k, k % 2, 1, k, k + 2 + k % 3) for k in range(8)]
    assert plan_corridors(lines, BANDS) == plan_corridors(lines[::-1], BANDS)


def test_height_and_y():
    assert corridor_height(0, 16) == 0
    assert corridor_height(3, 16) == 64
    assert corridor_height(1, 16, floor=40) == 40
    assert [corridor_y(100, 64, 3, r, 16) for r in range(3)] == [116, 132, 148]


_LINES = st.lists(
    st.tuples(st.integers(0, 3), st.integers(0, 3), st.integers(0, 9), st.integers(0, 9)),
    max_size=12,
)


@settings(derandomize=True)
@given(_LINES)
def test_corridor_stays_in_range_and_tracks_are_distinct(raw):
    lines = [(i, a, b, c, d) for i, (a, b, c, d) in enumerate(raw)]
    plan = plan_corridors(lines, 4)
    for key, a, b, _, _ in lines:
        if key in plan.corridor:
            lo, hi = min(a, b), max(a, b)
            allowed = {lo, lo + 1} if lo == hi else set(range(lo + 1, hi + 1))
            assert plan.corridor[key] in allowed
    ys = {
        (c, corridor_y(0, corridor_height(plan.load[c], 16), plan.load[c], plan.rank[k], 16))
        for k, c in plan.corridor.items()
    }
    assert len(ys) == len(plan.corridor)
    assert all(plan.rank[k] < plan.load[c] for k, c in plan.corridor.items())
