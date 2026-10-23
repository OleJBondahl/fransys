"""The band of a trunk: its lane lines (layout-0312), and `lane_runs` reads them unchanged."""

from __future__ import annotations

import itertools

import pytest

from fransys_layout.core.band import (
    band_extent,
    centred_span,
    lane_offset,
    lane_offsets,
    level_offset,
    on_band_side,
)
from fransys_layout.core.outputs import Wire
from fransys_layout.core.text_label_grid import lane_runs


@pytest.mark.parametrize(
    ("lanes", "step", "offsets", "extent"),
    [
        (1, 8, (0,), (0, 0)),
        (2, 8, (0, 8), (0, 8)),
        (3, 8, (0, 8, 16), (0, 16)),
        (1, 4, (0,), (0, 0)),
        (2, 4, (0, 4), (0, 4)),
        (3, 4, (0, 4, 8), (0, 8)),
    ],
)
def test_the_band_is_the_lane_lines_from_the_trunk_line(
    lanes: int, step: int, offsets: tuple[int, ...], extent: tuple[int, int]
) -> None:
    assert lane_offsets(lanes, step) == offsets
    assert band_extent(lanes, step) == extent


@pytest.mark.parametrize("step", [4, 8])
@pytest.mark.parametrize("lanes", [1, 2, 3, 4, 5])
def test_lane_runs_match_the_p5b_arithmetic_written_out(lanes: int, step: int) -> None:
    points = ((0, 0), (40, 0), (40, 24))
    wire = Wire("n", 0, points, "trunk", lanes)
    expected = []
    for (ax, ay), (bx, by) in itertools.pairwise(points):
        for k in range(lanes):
            dx, dy = (0, k * step) if ay == by else (k * step, 0)
            expected.append(((ax + dx, ay + dy), (bx + dx, by + dy)))
    assert list(lane_runs(wire, step)) == expected


@pytest.mark.parametrize("step", [4, 8])
@pytest.mark.parametrize("lanes", [0, 1, 2, 3, 4])
def test_the_band_helpers_equal_the_formulas_they_replace(lanes: int, step: int) -> None:
    assert centred_span(lanes, step) == lanes * step * 2
    for level in range(3):
        assert level_offset(lanes, level, step) == step * (lanes + level)
    for lane in range(5):
        assert lane_offset(lane, step) == lane * step


def test_the_band_grows_towards_east_and_south_only() -> None:
    assert [on_band_side(s) for s in "NESW"] == [False, True, True, False]
