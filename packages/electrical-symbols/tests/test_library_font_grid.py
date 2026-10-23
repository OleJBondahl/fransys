"""The library's `[grid]` and `[font]` are the one home of the grid and the Regular font table.

SB8: the font is measured from the house TTFs (SETTINGS-A2); derive's frozen copy
(`_text_widths.REGULAR_PAIRS`) is unchanged, equals the measured Regular table and measures like
`text_units`, on the literal strings of `tests/test_dd_rack_boxes.py`
(`test_a_boxs_port_pitch_*`) and `tests/test_marker_fit.py` (its texts come from golden models,
so a marker-like set stands in). Bold stays in `derive` until MODEL-TEXT (es-0069); the
`derive` copy is deleted there and this test goes with it.
"""

import pytest
from symdef import Weight, text_width

from electrical_symbols import LIBRARY
from fransys_model.derive import text_width as tw
from fransys_model.derive._text_widths import (
    REGULAR_PAIRS,
    UNITS_PER_EM,
)

STRINGS = ["ABC", "internal", "do_1.1", "1", "X12", "-Q1 / 24 V", 'Hello 12.5 A"\\', "中", ""]


def test_the_grid_is_the_houses() -> None:
    assert LIBRARY.grid.divisions_per_module == 8
    assert LIBRARY.grid.module_mm == 2.5


def test_the_loaded_library_carries_the_family_and_the_line_widths() -> None:
    assert LIBRARY.font is not None
    assert LIBRARY.font.family == "DejaVu Sans"
    assert dict(LIBRARY.lines) == {Weight.NORMAL: 0.25, Weight.THICK: 0.5}


def test_the_measured_regular_table_equals_derives_frozen_copy() -> None:
    expected = {
        chr(int(code, 16)): int(adv) for code, adv in (p.split("=") for p in REGULAR_PAIRS.split())
    }
    font = LIBRARY.font
    assert font is not None
    assert dict(font.advances[Weight.NORMAL]) == expected
    assert font.units_per_em == UNITS_PER_EM
    assert font.default_advance == max(expected.values())


def test_the_bold_table_is_measured_from_the_bold_face() -> None:
    """Thick is the Bold TTF's advances, not a copy of Regular (known: 170 of 197 differ)."""
    font = LIBRARY.font
    assert font is not None
    normal, thick = font.advances[Weight.NORMAL], font.advances[Weight.THICK]
    assert thick[" "] == 641
    assert sum(thick[c] != normal[c] for c in normal) == 170


def test_the_font_record_is_the_houses() -> None:
    font = LIBRARY.font
    assert font is not None
    assert (font.name, font.family) == ("DejaVu Sans Condensed", "DejaVu Sans")
    assert (font.cap_height, font.ascent, font.descent) == (1493, 1556, 426)
    assert dict(font.heights) == {"smallest": 1.8, "body": 2.5, "heading_2": 3.5, "heading_1": 5.0}


@pytest.mark.parametrize("height", [1, 1.5, 2.5])
@pytest.mark.parametrize("text", STRINGS)
def test_a_text_measures_as_derives_text_units(text: str, height: float) -> None:
    assert text_width(LIBRARY.font, text, height=height) == pytest.approx(
        tw.text_units(text) / UNITS_PER_EM * height, abs=1e-9
    )


def test_the_shared_library_is_frozen() -> None:
    with pytest.raises(TypeError):
        LIBRARY.symbols["x"] = 1  # ty: ignore[invalid-assignment] -- the freeze is the point
