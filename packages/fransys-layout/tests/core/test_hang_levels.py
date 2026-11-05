"""The stagger of a symbol's flags: overlapping boxes stand one box further out (R362)."""

from __future__ import annotations

import pytest

from fransys_layout.core import Box, PinRef
from fransys_layout.core.hang_levels import raised
from fransys_layout.core.hangings import Hanging

UP = Box(-6, -18, 12, 18)
DOWN = Box(-6, 0, 12, 18)


def _tag(box: Box, kind: str = "tag") -> Hanging:
    return Hanging(PinRef("A", "p"), "N", box, kind)


def test_two_overlapping_flags_above_stand_one_longest_box_apart() -> None:
    _, second = raised([(0, _tag(Box(-6, -30, 12, 30))), (8, _tag(UP))])  # the first stretched to link_fit
    assert second == Box(-6, -48, 12, 48)  # the stem to the second level included


def test_flags_that_do_not_overlap_stay_at_the_first_level() -> None:
    assert raised([(0, _tag(UP)), (40, _tag(UP))]) == [UP, UP]


def test_flags_below_stagger_downwards_and_apart_from_those_above() -> None:
    boxes = raised([(0, _tag(UP)), (0, _tag(DOWN)), (8, _tag(DOWN))])
    assert boxes[0] == UP
    assert boxes[1] == DOWN
    assert boxes[2] == Box(-6, 0, 12, 36)


def test_the_order_along_the_row_decides_the_level_not_the_list_order() -> None:
    far, near = raised([(8, _tag(UP)), (0, _tag(UP))])
    assert near == UP
    assert far.y == -36


def test_an_arrow_and_a_lead_are_not_staggered() -> None:
    boxes = raised([(0, _tag(UP, "arrow")), (8, _tag(UP, "arrow")), (8, _tag(UP, "lead"))])
    assert boxes == [UP, UP, UP]


@pytest.mark.rule("MARKER-STAGGER")
def test_each_group_of_overlapping_flags_steps_by_its_own_longest_box() -> None:
    """KI-360: a tall flag far along the row does not stretch the step of a short pair."""
    tall = Box(-6, -30, 12, 30)
    boxes = raised([(0, _tag(UP)), (8, _tag(UP)), (100, _tag(tall)), (108, _tag(tall))])
    assert [b.y for b in boxes] == [-18, -36, -30, -60]
