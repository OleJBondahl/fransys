"""`SIDE_STEP` is on the core surface, the one side-to-step table (layout-0306, R583)."""

from fransys_layout import core
from fransys_layout.core import sides


def test_the_core_door_hands_out_the_sides_table_itself():
    assert core.SIDE_STEP is sides.SIDE_STEP
