"""The one text width (model-0190): table units, grid width rounded up, unknown = widest."""

import ast
from pathlib import Path

import pytest

from fransys_model.derive import _text_widths
from fransys_model.derive.text_width import UNITS_PER_EM, marking_widths, text_units, text_width

DERIVE = Path(_text_widths.__file__).parent
PAIRS = {"regular": _text_widths.REGULAR_PAIRS, "bold": _text_widths.BOLD_PAIRS}
SAMPLES = ("-K1", "-K12", "Wii", "ÆØÅ")


def test_units_sum_the_advances():
    assert text_units("") == 0
    assert text_units("ii") == 2 * text_units("i")
    assert text_units("W") > text_units("i")


def test_bold_differs_from_regular():
    assert text_units("Bold text", bold=True) > text_units("Bold text")


def test_unknown_glyph_is_the_widest_advance():
    widest = max(text_units(chr(c)) for c in range(0x20, 0x7F))
    assert text_units("☃") >= widest
    assert text_units("a☃") == text_units("a") + text_units("☃")


def test_grid_width_rounds_up_and_never_under_measures():
    for height in (1, 7, 8, 9, 40):
        width = text_width("-K12 Wii", height=height)
        exact = text_units("-K12 Wii") * height
        assert width * UNITS_PER_EM >= exact
        assert (width - 1) * UNITS_PER_EM < exact


def test_height_zero_and_empty():
    assert text_width("-K1", height=0) == 0
    assert text_width("", height=8) == 0


def test_one_em_at_em_height():
    assert text_width("0", height=UNITS_PER_EM) == text_units("0")


def test_marking_widths_set_each_marking_one_module_high():
    assert marking_widths(["A1", "", "W"], height=8) == tuple(
        text_width(m, height=8) for m in ("A1", "", "W")
    )
    assert marking_widths(["W"], height=8)[0] > marking_widths(["i"], height=8)[0] > 0


def _advances(weight):
    return {chr(int(c, 16)): int(a) for c, a in (p.split("=") for p in PAIRS[weight].split())}


@pytest.mark.parametrize("weight", PAIRS)
def test_table_covers_designation_characters_and_label_symbols(weight):
    needed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-+=:/. "
    # AE, O-slash, A-ring (both cases); degree, micro, plus-minus, omega, euro, en and em dash.
    needed += "ÆØÅæøå\u00b0\u00b5\u00b1\u03a9\u20ac\u2013\u2014"
    advances = _advances(weight)
    assert [g for g in needed if g not in advances] == []
    assert all(0 < a <= UNITS_PER_EM for a in advances.values())


@pytest.mark.parametrize("weight", PAIRS)
def test_table_holds_single_characters_and_positive_integer_advances(weight):
    advances = _advances(weight)
    assert all(len(g) == 1 for g in advances)
    assert all(type(a) is int and a > 0 for a in advances.values())


@pytest.mark.parametrize("height", range(1, 41))
def test_width_is_exactly_the_ceiling_of_the_scaled_advance_sum(height):
    for text in SAMPLES:
        width = text_width(text, height=height)
        exact = text_units(text) * height
        assert width * UNITS_PER_EM >= exact
        assert (width - 1) * UNITS_PER_EM < exact


def test_height_of_one_em_gives_the_advance_sum_itself():
    for text in ("-K1", "Wii"):
        assert text_width(text, height=UNITS_PER_EM) == text_units(text)
        assert text_width(text, height=UNITS_PER_EM, bold=True) == text_units(text, bold=True)


def test_appending_a_glyph_or_growing_the_height_never_narrows():
    sample = "-K1:13/A2.+="
    prefixes = [text_width(sample[:n], height=8) for n in range(len(sample) + 1)]
    assert prefixes == sorted(prefixes)
    assert prefixes[-1] > prefixes[0]
    heights = [text_width(sample, height=h) for h in range(1, 41)]
    assert heights == sorted(heights)
    assert heights[-1] > heights[0]


@pytest.mark.parametrize("bold", [False, True])
def test_each_unknown_glyph_counts_as_the_widest_advance(bold):
    widest = max(_advances("bold" if bold else "regular").values())
    assert text_units("☃", bold=bold) == widest
    assert text_units("☃☃", bold=bold) == 2 * widest
    assert text_width("☃", height=8, bold=bold) == -(-widest * 8 // UNITS_PER_EM)


@pytest.mark.parametrize("weight", PAIRS)
def test_an_unknown_glyph_is_never_narrower_than_any_known_glyph(weight):
    bold = weight == "bold"
    for glyph in _advances(weight):
        assert text_width("☃", height=8, bold=bold) >= text_width(glyph, height=8, bold=bold)


def test_narrow_and_wide_glyphs_differ():
    assert text_width("iii", height=8) < text_width("WWW", height=8)


def test_the_advance_table_module_imports_nothing():
    tree = ast.parse((DERIVE / "_text_widths.py").read_text(encoding="utf-8"))
    assert [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)] == []
