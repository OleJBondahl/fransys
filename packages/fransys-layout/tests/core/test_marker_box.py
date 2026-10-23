"""Tests for the marker footprint in core/geometry.py (layout-0305): the symbol box, turned."""

import pytest
from options_fixtures import core_options

from fransys_layout.core.geometry import marker_box, marker_box_at, overlaps
from fransys_layout.core.outputs import Marker
from fransys_layout.core.values import Box, PinRef, RefKind

from .conftest import MARKER_BOX

END = PinRef("K1", "A1")


def make_marker(x: int, y: int, orient: str = "R0") -> Marker:
    return Marker("N1", RefKind.COPY, 0, "c", x, y, END, orient)  # ty: ignore[invalid-argument-type] -- an Orientation literal


def test_marker_box_at_moves_the_symbols_box_to_its_origin(marker_options):
    assert marker_box_at(100, 40, marker_options) == Box(100, 32, 48, 16)


@pytest.mark.parametrize(
    ("orient", "box"),
    [
        ("R0", Box(10, 2, 48, 16)),
        ("R90", Box(2, 10, 16, 48)),
        ("R180", Box(-38, 2, 48, 16)),
        ("R270", Box(2, -38, 16, 48)),
    ],
)
def test_marker_box_at_turns_the_box_about_the_origin(marker_options, orient, box):
    assert marker_box_at(10, 10, marker_options, orient) == box


def test_marker_box_is_marker_box_at_its_origin_and_orient(marker_options):
    m = make_marker(-16, 24, "R90")
    assert marker_box(m, marker_options) == marker_box_at(-16, 24, marker_options, "R90")


def test_an_unset_marker_option_is_refused_by_name():
    with pytest.raises(ValueError, match=r"Options\.marker is unset"):
        marker_box_at(
            0,
            0,
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )


def test_the_fixture_is_the_keepout_box_in_grid_units(marker_options):
    assert marker_options.marker["R0"] == MARKER_BOX == Box(0, -8, 48, 16)


def test_markers_one_box_apart_do_not_overlap_and_closer_ones_do(marker_options):
    box = marker_box_at(0, 0, marker_options)
    assert not overlaps(box, marker_box_at(48, 0, marker_options))
    assert overlaps(box, marker_box_at(40, 0, marker_options))
