"""WP3: `text_width` and the advance table (RR-O5, layout-0132)."""

import ast
from pathlib import Path

import pytest

import electrical_symbols
from electrical_symbols import text_width
from electrical_symbols.text_metrics import ADVANCES, FONT_NAME, UNITS_PER_EM


def test_advance_table_covers_the_characters_designations_use() -> None:
    """Every ASCII letter, digit and the designation punctuation has an advance."""
    needed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-+=:/. "
    assert all(glyph in ADVANCES for glyph in needed)
    assert all(0 < advance <= UNITS_PER_EM for advance in ADVANCES.values())


def test_width_is_the_sum_of_advances_rounded_up() -> None:
    """`-K1` at height 8 is the three advances, scaled by the height, rounded up."""
    thousandths = ADVANCES["-"] + ADVANCES["K"] + ADVANCES["1"]
    assert text_width("-K1", height=8) == -(-thousandths * 8 // UNITS_PER_EM)


def test_width_is_monotone_in_text_and_height_and_never_below_exact() -> None:
    """Appending a glyph or growing the height never narrows; the ceiling never undercuts."""
    assert text_width("-K1", height=8) <= text_width("-K12", height=8)
    assert text_width("-K1", height=8) <= text_width("-K1", height=9)
    thousandths = ADVANCES["-"] + ADVANCES["K"] + ADVANCES["1"]
    assert text_width("-K1", height=8) * UNITS_PER_EM >= thousandths * 8


def test_the_table_is_liberation_serif() -> None:
    """The table names the openly licensed font it was generated from."""
    assert FONT_NAME == "Liberation Serif"


def test_narrow_and_wide_glyphs_differ() -> None:
    """The reason for the table: `iii` is narrower than `WWW`."""
    assert text_width("iii", height=8) < text_width("WWW", height=8)


def test_unknown_glyph_uses_the_widest_advance() -> None:
    """A glyph missing from the table is never estimated too small."""
    widest = max(ADVANCES.values())
    assert text_width("☃", height=8) == -(-widest * 8 // UNITS_PER_EM)


def test_empty_text_has_no_width() -> None:
    """The empty string is zero wide."""
    assert text_width("", height=8) == 0


def _thousandths(text: str) -> int:
    return sum(ADVANCES[glyph] for glyph in text)


def test_norwegian_letters_and_label_symbols_have_an_advance() -> None:
    """Norwegian labels and the usual electrical symbols are in the table, not estimated."""
    # AE, O-slash, A-ring (upper and lower case); degree, micro, plus-minus, Greek omega,
    # euro, en dash, em dash.
    codepoints = (
        0xC6,
        0xD8,
        0xC5,
        0xE6,
        0xF8,
        0xE5,
        0xB0,
        0xB5,
        0xB1,
        0x3A9,
        0x20AC,
        0x2013,
        0x2014,
    )
    assert all(chr(codepoint) in ADVANCES for codepoint in codepoints)


def test_the_table_holds_single_characters_and_positive_integer_advances() -> None:
    """Every key is one character, every advance a positive `int`, and `UNITS_PER_EM` is 1000."""
    assert UNITS_PER_EM == 1000
    assert type(ADVANCES) is frozendict
    assert all(len(glyph) == 1 for glyph in ADVANCES)
    assert all(type(advance) is int and advance > 0 for advance in ADVANCES.values())


@pytest.mark.parametrize("height", range(1, 41))
def test_width_is_exactly_the_ceiling_of_the_scaled_advance_sum(height: int) -> None:
    """Never below the exact value, and never more than one unit above it."""
    for text in ("-K1", "-K12", "Wii", "ÆØÅ"):
        width = text_width(text, height=height)
        exact_thousandths = _thousandths(text) * height
        assert width * UNITS_PER_EM >= exact_thousandths
        assert (width - 1) * UNITS_PER_EM < exact_thousandths


def test_height_one_thousand_gives_the_advance_sum_itself() -> None:
    """At height 1000 the ceiling is exact, so a width is the raw sum of advances."""
    assert text_width("-K1", height=1000) == _thousandths("-K1")
    assert text_width("Wii", height=1000) == _thousandths("Wii")


def test_appending_a_glyph_widens_and_a_taller_height_widens() -> None:
    """Every prefix is at most as wide as the next one; every height at most as wide as the next."""
    sample = "-K1:13/A2.+="
    prefixes = [text_width(sample[:n], height=8) for n in range(len(sample) + 1)]
    assert prefixes == sorted(prefixes)
    assert prefixes[-1] > prefixes[0]
    heights = [text_width(sample, height=h) for h in range(1, 41)]
    assert heights == sorted(heights)
    assert heights[-1] > heights[0]


def test_an_unknown_glyph_counts_as_the_widest_advance_and_each_one_counts() -> None:
    """Two unknown glyphs are two widest advances; a known one keeps its own advance."""
    widest = max(ADVANCES.values())
    assert text_width("a☃", height=1000) == ADVANCES["a"] + widest
    assert text_width("☃☃", height=1000) == 2 * widest


def test_an_unknown_glyph_is_never_narrower_than_any_known_glyph() -> None:
    """The estimate for something missing from the table is a safe upper bound."""
    for glyph in ADVANCES:
        assert text_width("☃", height=8) >= text_width(glyph, height=8)


def test_a_zero_height_has_no_width() -> None:
    """Zero-high text is zero wide."""
    assert text_width("-K1", height=0) == 0


GEOMETRY = Path(electrical_symbols.__file__).parent
# Neither `importlib.metadata` nor `importlib.resources` is allowed: the library version comes from
# the `LIBRARY_VERSION` constants the symbol packages export (decision layout-0020).
FORBIDDEN_MODULES = {
    "fontTools",
    "fonttools",
    "pathlib",
    "io",
    "os",
    "tempfile",
    "shutil",
    "codecs",
    "importlib.metadata",
    "importlib.resources",
}


def _file_access(source: str) -> list[str]:
    """Imports of a font library or file module, and calls to `open`, in `source`."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported = [f"{node.module}.{a.name}" for a in node.names]
            imported.append(node.module or "")
        else:
            imported = []
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                found.append("open()")
        found += [
            name
            for name in imported
            if any(name == banned or name.startswith(f"{banned}.") for banned in FORBIDDEN_MODULES)
        ]
    return found


def test_geometry_opens_no_file_and_imports_no_font_library() -> None:
    """The table is committed data; no text module reads a font or any file."""
    problems = {
        path.name: found
        for path in sorted(GEOMETRY.glob("text*.py"))
        if (found := _file_access(path.read_text(encoding="utf-8")))
    }
    assert problems == {}


def test_the_file_access_check_can_fail() -> None:
    """A font import, a file-module import and an `open` call each trip it; clean code does not."""
    assert "fontTools.ttLib" in _file_access("from fontTools.ttLib import TTFont")
    assert _file_access("import pathlib") == ["pathlib"]
    assert _file_access("with open('f.ttf', 'rb') as f: ...") == ["open()"]
    assert "importlib.resources" in _file_access("import importlib.resources")
    assert _file_access("from importlib import resources") == ["importlib.resources"]
    assert _file_access("from decimal import Decimal\nx = max(1, 2)") == []
    assert "importlib.metadata" in _file_access("from importlib.metadata import version")
    assert "importlib.metadata" in _file_access("import importlib.metadata")
    assert _file_access("from importlib import metadata") == ["importlib.metadata"]


def test_the_advance_table_module_imports_nothing() -> None:
    """`text_metrics.py` is a literal: no import of any kind, so no font library."""
    tree = ast.parse((GEOMETRY / "text_metrics.py").read_text(encoding="utf-8"))
    assert [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)] == []
