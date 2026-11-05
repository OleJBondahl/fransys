"""The library font table equals the TTFs' `hmtx` advances, every code point, both weights."""

from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from fontTools.ttLib import TTFont
from symdef import Weight, text_width

import electrical_symbols
from electrical_symbols import LIBRARY

FONTS = Path(electrical_symbols.__file__).parent / "fonts"
FILES = {"Regular": "DejaVuSansCondensed.ttf", "Bold": "DejaVuSansCondensed-Bold.ttf"}
WEIGHTS = {"Regular": Weight.NORMAL, "Bold": Weight.THICK}


@pytest.mark.parametrize("weight", WEIGHTS)
def test_table_matches_font(weight):
    font = TTFont(FONTS / FILES[weight])
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    spec = LIBRARY.font
    assert spec is not None
    assert cast("Any", font["head"]).unitsPerEm == spec.units_per_em
    table = spec.advances[WEIGHTS[weight]]
    assert len(table) > 190
    for char, advance in table.items():
        assert hmtx[cmap[ord(char)]][0] == advance, (weight, char)


@pytest.mark.parametrize("weight", WEIGHTS)
def test_norwegian_letters_are_measured_with_the_ttf_width(weight):
    font = TTFont(FONTS / FILES[weight])
    cmap: Any = font.getBestCmap()
    hmtx: Any = font["hmtx"]
    spec = LIBRARY.font
    assert spec is not None
    for letter in "ÆØÅæøå":
        assert letter in spec.advances[WEIGHTS[weight]], (weight, letter)  # not the fallback
        units = text_width(spec, letter, spec.units_per_em, WEIGHTS[weight])
        assert units == hmtx[cmap[ord(letter)]][0], letter


def test_capital_ratio_and_ascent_equal_the_regular_ttf():
    """A5 (E4): derive's ratios are the glyph H's top and `sTypoAscender` over unitsPerEm.

    The font's OS/2 table is version 1, so it has no `sCapHeight`; the H glyph's top is the cap.
    """
    spec = LIBRARY.font
    assert spec is not None
    font = TTFont(FONTS / FILES["Regular"])
    cmap: Any = font.getBestCmap()
    glyf: Any = font["glyf"]
    units = cast("Any", font["head"]).unitsPerEm
    assert Decimal(glyf[cmap[ord("H")]].yMax) / units == Decimal(spec.cap_height) / Decimal(spec.units_per_em)
    assert Decimal(cast("Any", font["OS/2"]).sTypoAscender) / units == Decimal(spec.ascent) / Decimal(spec.units_per_em)


def test_descent_ratio_equals_the_regular_ttf():
    """The descent ratio is the glyph p's bottom, negated, over unitsPerEm (A5, E4)."""
    spec = LIBRARY.font
    assert spec is not None
    font = TTFont(FONTS / FILES["Regular"])
    cmap: Any = font.getBestCmap()
    glyf: Any = font["glyf"]
    units = cast("Any", font["head"]).unitsPerEm
    assert Decimal(-glyf[cmap[ord("p")]].yMin) / units == Decimal(spec.descent) / Decimal(spec.units_per_em)
