"""Shared core-test values: the one marker box the core tests pass in (layout-0305)."""

import pytest

from fransys_layout.core.values import Box, Options

# The reference-marker symbol's keepout_box ((0, -1), (6, 1) in M) at 8 grid units to the M.
# fransys_el computes the real one from symdef; the core types no size of its own.
MARKER_BOX = Box(0, -8, 48, 16)


@pytest.fixture
def marker_options() -> Options:
    return Options(marker=MARKER_BOX)
