"""The derive width table equals the TTFs' `hmtx` advances, every code point, both weights."""

from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import fransys_pdf
import pytest
from fontTools.ttLib import TTFont

from fransys_model.derive import _text_widths as table
from fransys_model.derive.text_width import text_units

FONTS = Path(fransys_pdf.__file__).parent / "fonts"
FILES = {"Regular": "DejaVuSansCondensed.ttf", "Bold": "DejaVuSansCondensed-Bold.ttf"}
WEIGHTS = {"Regular": table.REGULAR_PAIRS, "Bold": table.BOLD_PAIRS}


@pytest.mark.parametrize("weight", WEIGHTS)
def test_table_matches_font(weight):
    font = TTFont(FONTS / FILES[weight])
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    assert cast("Any", font["head"]).unitsPerEm == table.UNITS_PER_EM
    pairs = [pair.split("=") for pair in WEIGHTS[weight].split()]
    assert len(pairs) > 190
    for code, advance in pairs:
        assert hmtx[cmap[int(code, 16)]][0] == int(advance), (weight, code)


@pytest.mark.parametrize("weight", WEIGHTS)
def test_norwegian_letters_are_measured_with_the_ttf_width(weight):
    font = TTFont(FONTS / FILES[weight])
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    in_table = {int(pair.split("=")[0], 16) for pair in WEIGHTS[weight].split()}
    for letter in "ÆØÅæøå":
        assert ord(letter) in in_table, (weight, letter)  # a table entry, not the widest fallback
        assert text_units(letter, bold=weight == "Bold") == hmtx[cmap[ord(letter)]][0], letter


def test_capital_ratio_and_ascent_equal_the_regular_ttf():
    """A5 (E4): derive's ratios are the glyph H's top and `sTypoAscender` over unitsPerEm.

    The font's OS/2 table is version 1, so it has no `sCapHeight`; the H glyph's top is the cap.
    """
    from fransys_model.derive import print_sizes

    font = TTFont(FONTS / FILES["Regular"])
    cmap: Any = font.getBestCmap()
    glyf: Any = font["glyf"]
    units = cast("Any", font["head"]).unitsPerEm
    assert Decimal(glyf[cmap[ord("H")]].yMax) / units == print_sizes.CAPITAL_RATIO
    assert Decimal(cast("Any", font["OS/2"]).sTypoAscender) / units == print_sizes.ASCENT_RATIO
