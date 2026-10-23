"""Shared core-test values: the one marker box the core tests pass in (layout-0305)."""

import pytest
from options_fixtures import core_options
from turn_fixtures import marker_views

from fransys_layout.core.values import Box, Options

# The reference-marker symbol's keepout_box ((0, -1), (6, 1) in M) at 8 grid units to the M.
# fransys_el computes the real one from symdef; the core types no size of its own.
MARKER_BOX = Box(0, -8, 48, 16)
# Its eight views, turned by symdef (SB4); the layer measures the real ones.
MARKER = marker_views(MARKER_BOX)


@pytest.fixture
def marker_options() -> Options:
    return core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
