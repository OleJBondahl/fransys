"""One step out from a point along a side (layout-0318): the stub and the marker stand read it."""

from __future__ import annotations

import pytest

from fransys_layout.core.sides import SIDE_STEP, step_out
lazy from fransys_layout.core.values import Side


@pytest.mark.parametrize("length", [0, 4, 16])
@pytest.mark.parametrize("side", ["N", "E", "S", "W"])
def test_step_out_equals_the_unit_step_times_the_length(side: Side, length: int) -> None:
    dx, dy = SIDE_STEP[side]
    assert step_out(side, 100, 200, length) == (100 + dx * length, 200 + dy * length)


def test_step_out_moves_along_the_side_axis_only() -> None:
    assert step_out("E", 10, 20, 8) == (18, 20)
    assert step_out("N", 10, 20, 8) == (10, 12)
