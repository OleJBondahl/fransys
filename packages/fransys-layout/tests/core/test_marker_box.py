"""Tests for the marker footprint in core/geometry.py (layout-0305): the symbol box, turned."""

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core import stub_views
from fransys_layout.core.errors import CoreError
from fransys_layout.core.geometry import marker_box, marker_box_at, marker_drawn_box, overlaps
from fransys_layout.core.outputs import Marker
from fransys_layout.core.values import Box, Orientation, PinRef, RefKind

from .conftest import MARKER_BOX

END = PinRef("K1", "A1")


def make_marker(x: int, y: int, orient: Orientation = "R0") -> Marker:
    return Marker("N1", RefKind.COPY, 0, "c", x, y, END, orient)


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
    with pytest.raises(CoreError, match=r"Options\.marker is unset"):
        marker_box_at(
            0,
            0,
            core_options(),
        )


def test_the_fixture_is_the_keepout_box_in_grid_units(marker_options):
    assert marker_options.marker["R0"] == MARKER_BOX == Box(0, -8, 48, 16)


def test_markers_one_box_apart_do_not_overlap_and_closer_ones_do(marker_options):
    box = marker_box_at(0, 0, marker_options)
    assert not overlaps(box, marker_box_at(48, 0, marker_options))
    assert overlaps(box, marker_box_at(40, 0, marker_options))


def test_a_tag_is_drawn_in_the_link_fit_box_and_placed_by_the_plain_one(marker_options):
    wide = {**marker_options.marker, "R90": Box(2, 10, 12, 75)}
    options = replace(marker_options, link_fit=wide)
    tag = replace(make_marker(10, 10, "R90"), kind=RefKind.TAG)
    assert marker_drawn_box(tag, options) == Box(12, 20, 12, 75)
    assert marker_box(tag, options) == marker_box_at(10, 10, options, "R90")


def test_any_other_kind_is_drawn_in_its_placed_box(marker_options):
    options = replace(marker_options, link_fit=dict(marker_options.marker))
    m = make_marker(10, 10, "R90")
    assert marker_drawn_box(m, options) == marker_box(m, options)


def test_the_route_grid_keeps_a_tags_drawn_box(marker_options):
    from fransys_layout.core.anchors import _marker_keeps

    options = replace(marker_options, link_fit={**marker_options.marker, "R90": Box(2, 10, 12, 75)})
    tag = replace(make_marker(10, 10, "R90"), kind=RefKind.TAG)
    (keep,) = _marker_keeps(0, [tag], options)
    assert keep.box == marker_drawn_box(tag, options) == Box(12, 20, 12, 75)


NEAR, ALSO, FAR_A, FAR_B = PinRef("K1", "A1"), PinRef("K1", "A2"), PinRef("X1", "1"), PinRef("X2", "1")
STUB_TABLE: dict[tuple[int, int], dict[Orientation, Box]] = {(w, n): {"R0": Box(w, n, 1, 1)} for w in (2, 4) for n in (1, 2, 3)}


def test_stub_views_is_none_when_lines_names_no_far_pin():
    assert stub_views({(NEAR, FAR_B): (2,)}, STUB_TABLE, NEAR, [], [FAR_A]) is None


def test_stub_views_takes_the_widest_width_and_the_count_across_far_pins():
    lines = {(NEAR, FAR_A): (2, 2), (NEAR, FAR_B): (4,)}
    assert stub_views(lines, STUB_TABLE, NEAR, [], [FAR_A, FAR_B]) == STUB_TABLE[4, 3]


def test_stub_views_reads_each_far_pin_at_the_first_of_pin_and_also_with_lines():
    lines = {(NEAR, FAR_A): (2,), (ALSO, FAR_A): (4, 4), (ALSO, FAR_B): (2,)}
    assert stub_views(lines, STUB_TABLE, NEAR, [ALSO], [FAR_A, FAR_B]) == STUB_TABLE[2, 2]


def test_stub_views_refuses_a_table_without_the_entry():
    with pytest.raises(CoreError, match="stub_table has no box for 4 lines of width 2"):
        stub_views({(NEAR, FAR_A): (2, 2, 2, 2)}, STUB_TABLE, NEAR, [], [FAR_A])


def test_a_tag_whose_link_fit_lacks_the_orientation_is_refused(marker_options):
    options = replace(marker_options, link_fit={"R0": marker_options.marker["R0"]})
    tag = replace(make_marker(10, 10, "R90"), kind=RefKind.TAG)
    with pytest.raises(CoreError, match="link_fit has no box for orientation R90"):
        marker_drawn_box(tag, options)
