"""The library's `[grid]` and `[font]` are the one home of the grid and the font tables.

SB8: the font is measured from the house TTFs (SETTINGS-A2); derive's frozen copy is deleted
(CC1, model-0373) and symdef's measure is the only one.
"""

import pytest
from symdef import Weight, text_width

from electrical_symbols import LIBRARY


def test_the_grid_is_the_houses() -> None:
    assert LIBRARY.grid.divisions_per_module == 8
    assert LIBRARY.grid.module_mm == 2.5


def test_the_loaded_library_carries_the_family_and_the_line_widths() -> None:
    assert LIBRARY.font.family == "DejaVu Sans"
    assert dict(LIBRARY.lines) == {Weight.NORMAL: 0.25, Weight.THICK: 0.5, Weight.RULE: 0.18}
    assert dict(LIBRARY.dash) == {
        "dashed": (1.25, 0.625),
        "dash_dot": (4.0, 1.0, 0.25, 1.0),
        "long": (4.0, 1.0),
    }


def test_the_bold_table_is_measured_from_the_bold_face() -> None:
    """Thick is the Bold TTF's advances, not a copy of Regular (known: 170 of 197 differ)."""
    font = LIBRARY.font
    normal, thick = font.advances[Weight.NORMAL], font.advances[Weight.THICK]
    assert thick[" "] == 641
    assert sum(thick[c] != normal[c] for c in normal) == 170


def test_the_font_record_is_the_houses() -> None:
    font = LIBRARY.font
    assert (font.name, font.family) == ("DejaVu Sans Condensed", "DejaVu Sans")
    assert (font.cap_height, font.ascent, font.descent) == (1493, 1556, 426)
    assert dict(font.heights) == {"smallest": 1.8, "body": 2.5, "heading_2": 3.5, "heading_1": 5.0}


def test_a_glyph_outside_the_bold_table_is_charged_the_bold_faces_own_default_advance() -> None:
    """The one case derive's old table charged by hand: symdef 0.29 keeps a default advance per face (R590)."""
    font = LIBRARY.font
    assert font is not None
    assert text_width(font, "☃", font.units_per_em, Weight.THICK) == font.default_advance[Weight.THICK]
    assert font.default_advance[Weight.THICK] != font.default_advance[Weight.NORMAL]


def test_the_shared_library_is_frozen() -> None:
    with pytest.raises(TypeError):
        LIBRARY.symbols["x"] = 1  # ty: ignore[invalid-assignment] -- the freeze is the point
