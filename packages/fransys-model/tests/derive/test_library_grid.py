"""GRID-HOME G6: the drawing library record is the one home of the grid and font numbers.

A build whose record says 16 divisions moves every derive fact that reads `mm_per_division`; a
model with no record raises; the record survives the kernel's text form.
"""

from decimal import Decimal

import pytest
from derive_helpers import drawing_library, frozen_with_library

from fransys_model.derive import mm_per_division, text_room_g
from fransys_model.derive.frame_position import content_extent
from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.library_grid import divisions, library_grid
from fransys_model.derive.print_sizes import TextRole, font_size_mm, role_height_mm
from fransys_model.kernel import Draft, SchemaError, dumps, loads
from fransys_model.layout import default_profile, default_sheet_format

SHEET = default_sheet_format()
EIGHT = frozen_with_library(Draft(), 8)
SIXTEEN = frozen_with_library(Draft(), 16)


def test_a_model_with_no_record_raises() -> None:
    from fransys_model.kernel import freeze

    with pytest.raises(SchemaError, match="no drawing library record"):
        mm_per_division(freeze(Draft()), SHEET)


def test_the_record_gives_the_division_and_the_length_of_one() -> None:
    assert divisions(EIGHT) == 8
    assert mm_per_division(EIGHT, SHEET) == Decimal("0.3125")
    assert library_grid(EIGHT).wire_pitch == 8


def test_sixteen_divisions_halve_the_length_and_double_the_counts() -> None:
    """Every conversion that reads `mm_per_division` follows the record, not a constant 8."""
    per = mm_per_division(SIXTEEN, SHEET)
    assert per == Decimal("0.15625")
    assert grid_to_mm(5, 16, per) == 5 + Decimal("2.5")
    assert content_extent(SHEET.content_width_mm, per) == 2 * content_extent(
        SHEET.content_width_mm, mm_per_division(EIGHT, SHEET)
    )
    height = default_profile().text_height_mm
    assert text_room_g(SIXTEEN, height, SHEET) == 2 * text_room_g(EIGHT, height, SHEET)


def test_the_text_heights_are_the_records() -> None:
    assert role_height_mm(EIGHT, TextRole.BODY, Decimal("1.8")) == Decimal("2.5")
    assert font_size_mm(EIGHT, Decimal("1.8")).quantize(Decimal("0.001")) == Decimal("2.469")


def test_the_record_round_trips_through_the_kernel_text_form() -> None:
    assert loads(dumps(EIGHT)) == EIGHT
    assert library_grid(loads(dumps(SIXTEEN))) == drawing_library(16)


def test_the_pitches_font_and_descender_are_read_from_the_record() -> None:
    from fransys_model.derive.library_grid import descent_ratio, font_family, wire_pitch

    assert (wire_pitch(EIGHT), wire_pitch(EIGHT, fine=True)) == (8, 4)
    assert font_family(EIGHT) == "DejaVu Sans"
    assert descent_ratio(EIGHT) == Decimal(426) / Decimal(2048)


def test_the_record_kind_is_outside_the_derived_and_cable_kinds() -> None:
    from fransys_model.layout.kinds import CABLE_KINDS, DERIVED_KINDS, LIBRARY_KINDS

    assert LIBRARY_KINDS
    assert not set(LIBRARY_KINDS) & (set(DERIVED_KINDS) | set(CABLE_KINDS))
