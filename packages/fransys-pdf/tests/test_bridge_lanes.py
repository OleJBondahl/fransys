"""The Bridge column draws the lanes derive names: a guard for pdf-0045.

The lane of each jumper group is `derive.jumper_lanes`; pdf only draws the marks it is given. These
tests fail if pdf draws a different number of lanes than derive names, or puts a group's tick on
rows that are not that group's, so a second lane rule in pdf cannot drift unseen.
"""

import pytest
from fransys_pdf._bridge import bridge_geometry

from fransys_model.derive import jumper_lanes

GROUPS_CASES = [
    (),
    (None, None),
    (1, 1, None, 2, 2),
    (1, 2, 1, 2),
    (1, 2, 3, 1, 2, 3, None, 4),
    (3, 3, 1, 1, 2, None, 2),
]


@pytest.mark.parametrize("groups", GROUPS_CASES)
def test_drawn_lane_count_is_derives(groups: tuple[int | None, ...]) -> None:
    lanes = jumper_lanes(groups)
    geometry = bridge_geometry(groups, lanes)
    drawn = max((len(row) for row in geometry), default=0)
    expected = max((span.lane for span in lanes.lanes), default=-1) + 1
    assert drawn == expected


@pytest.mark.parametrize("groups", GROUPS_CASES)
def test_each_group_ticks_exactly_its_own_rows(groups: tuple[int | None, ...]) -> None:
    lanes = jumper_lanes(groups)
    geometry = bridge_geometry(groups, lanes)
    for span in lanes.lanes:
        ticked = {
            index
            for index, row in enumerate(geometry)
            if (mark := row[span.lane]) is not None and mark.tick
        }
        own = {index for index, group in enumerate(groups) if group == span.group}
        assert {index for index in ticked if groups[index] == span.group} == own
        assert all(groups[index] is not None for index in ticked)
