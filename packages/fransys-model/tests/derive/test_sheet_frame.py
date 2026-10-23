"""A sheet's frame values in mm (`sheet_frame`) and the notice's line pitch and count."""

from decimal import Decimal

import pytest
from derive_helpers import house_record

from fransys_model.derive import (
    FrameStrip,
    notice_line_count,
    notice_pitch_mm,
    sheet_frame,
)
from fransys_model.kernel import Id
from fransys_model.layout import FrameForm, SheetFormat, default_sheet_format


def _a4_test_sheet() -> SheetFormat:
    """A4 landscape with unequal margins (6 mm left and right, 4 mm top and bottom), 5 x 3."""
    return SheetFormat(
        id=Id(kind="layout.sheet_format", value="e" * 32),
        key=("tests", "derive", "a4t"),
        name="A4 test",
        width_mm=297,
        height_mm=210,
        content_x_mm=6,
        content_y_mm=4,
        content_width_mm=285,
        content_height_mm=170,
        frame_columns=5,
        frame_rows=3,
        module_mm=Decimal("2.5"),
    )


def test_the_house_frame_is_the_old_border_band_and_strips():
    frame = sheet_frame(house_record(FrameForm), default_sheet_format())
    assert frame.border == (5, 5, 410, 287)
    assert (frame.band, frame.band_top, frame.title_width, frame.logo_x) == (20, 272, 390, 395)
    top, bottom, left, right = frame.strips
    assert top == FrameStrip("top", 5, 0, 410 / 8, 5, "x", ("1", "2", "3", "4", "5", "6", "7", "8"))
    assert (bottom.side, bottom.x, bottom.y) == ("bottom", 5, 292)
    assert left == FrameStrip("left", 0, 5, 5, 267 / 6, "y", ("A", "B", "C", "D", "E", "F"))
    assert (right.side, right.x, right.y, right.cell_width) == ("right", 415, 5, 5)


def test_unequal_margins_give_each_strip_its_own_depth_and_a_taller_band():
    frame = sheet_frame(house_record(FrameForm), _a4_test_sheet())
    assert frame.border == (6, 4, 285, 202)
    assert (frame.band, frame.band_top, frame.title_width, frame.logo_x) == (32, 174, 253, 259)
    top, bottom, left, right = frame.strips
    assert (top.cell_width, top.cell_height, len(top.labels)) == (57, 4, 5)
    assert (bottom.y, left.cell_width, right.x) == (206, 6, 291)
    assert left.cell_height == pytest.approx(170 / 3)
    assert left.labels == ("A", "B", "C")


@pytest.mark.parametrize(
    ("height", "font", "count"), [(18, 1.8, 8), (30, 1.8, 13), (18, 2.5, 6), (2.15, 1.8, 0)]
)
def test_the_notice_holds_whole_lines_of_one_and_a_fifth_em(height, font, count):
    assert notice_pitch_mm(font) == pytest.approx(font * 1.2)
    assert notice_line_count(height, font_mm=font) == count
