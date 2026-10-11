"""The derive width table equals the TTFs' `hmtx` advances, every code point, both weights."""

from pathlib import Path
from typing import Any, cast

import fransys_pdf
import pytest
from fontTools.ttLib import TTFont

from fransys_model.derive import _text_widths as table
from fransys_model.derive.text_width import text_units

FONTS = Path(fransys_pdf.__file__).parent / "fonts"
WEIGHTS = {"Regular": table.REGULAR_PAIRS, "Bold": table.BOLD_PAIRS}


@pytest.mark.parametrize("weight", WEIGHTS)
def test_table_matches_font(weight):
    font = TTFont(FONTS / f"LiberationSerif-{weight}.ttf")
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    assert cast("Any", font["head"]).unitsPerEm == table.UNITS_PER_EM
    pairs = [pair.split("=") for pair in WEIGHTS[weight].split()]
    assert len(pairs) > 190
    for code, advance in pairs:
        assert hmtx[cmap[int(code, 16)]][0] == int(advance), (weight, code)


@pytest.mark.parametrize("weight", WEIGHTS)
def test_norwegian_letters_are_measured_with_the_ttf_width(weight):
    font = TTFont(FONTS / f"LiberationSerif-{weight}.ttf")
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    in_table = {int(pair.split("=")[0], 16) for pair in WEIGHTS[weight].split()}
    for letter in "ÆØÅæøå":
        assert ord(letter) in in_table, (weight, letter)  # a table entry, not the widest fallback
        assert text_units(letter, bold=weight == "Bold") == hmtx[cmap[ord(letter)]][0], letter


def test_cover_line_estimate_follows_the_measured_width():
    from fransys_pdf._cover_checks import _line_count

    assert _line_count("W" * 60, width_mm=50, size_pt=10) > _line_count(
        "i" * 60, width_mm=50, size_pt=10
    )
    assert _line_count("", width_mm=50, size_pt=10) == 1
