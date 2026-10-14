"""EXACT-SIZES A1, A2, A3 and A4 over symbols: the texts and strokes a symbol prints.

One invented page carries a placement of each symbol kind the bundle draws, motor-3ph and
motor-1ph included (the only symbols with texts). It is compiled at `module_mm` 2.5 and at 3.0.
A symbol's body follows the module (E9: the grid pitch), but its texts and strokes are fixed in mm
(E1): both PDFs print the same capital heights and line widths. No logo cell is on the page.
"""

from __future__ import annotations

import re

import pytest
from _pdf_measure import font_names, stroke_widths, text_objects
from fransys_render import pages
from test_exact_sizes_pdf import _compile, _model

from fransys_model.derive.print_sizes import (
    LINE_RULE_MM,
    LINE_THICK_MM,
    LINE_THIN_MM,
    TextRole,
    role_height_mm,
)
from fransys_model.layout import default_profile

pytestmark = pytest.mark.wp("pdf")

_SYMBOLS = (
    "motor-3ph",
    "motor-1ph",
    "circuit-breaker",
    "make-contact",
    "break-contact",
    "change-over-contact",
    "operating-device",
    "fuse",
    "terminal",
)
_SIZES_MM = {float(role_height_mm(role, default_profile().text_height_mm)) for role in TextRole}
_WIDTHS_MM = {float(w) for w in (LINE_THIN_MM, LINE_THICK_MM, LINE_RULE_MM)}
_FACES = {"DejaVuSansCondensed", "DejaVuSansCondensed-Bold"}
_CAP_TOLERANCE_MM = 0.02
_WIDTH_TOLERANCE_MM = 0.005


@pytest.fixture(scope="module")
def pdfs() -> dict[str, bytes]:
    """The same page at module 2.5 and 3.0, and the page with no symbol at all."""
    return {
        "2.5": _compile(symbols=_SYMBOLS, module_mm="2.5"),
        "3.0": _compile(symbols=_SYMBOLS, module_mm="3.0"),
        "none": _compile(),
    }


def _caps(pdf: bytes) -> list[float]:
    return [o.cap_mm for o in text_objects(pdf)]


def _on(value: float, allowed: set[float], tolerance: float) -> bool:
    return any(abs(value - one) <= tolerance for one in allowed)


def test_the_symbols_add_texts_and_strokes_to_the_page(pdfs):
    """The symbol content is really measured: more text objects and more strokes than without."""
    assert len(_caps(pdfs["2.5"])) > len(_caps(pdfs["none"]))
    assert sum(stroke_widths(pdfs["2.5"]).values()) > sum(stroke_widths(pdfs["none"]).values())


@pytest.mark.parametrize("module", ["2.5", "3.0"])
def test_every_text_object_with_symbols_is_a_role_size(pdfs, module):
    """A1: symbol texts too (the motor "M" and "3") print 1.8/2.5/3.5/5 mm capitals."""
    off = [c for c in _caps(pdfs[module]) if not _on(c, _SIZES_MM, _CAP_TOLERANCE_MM)]
    assert off == []


@pytest.mark.parametrize("module", ["2.5", "3.0"])
def test_every_stroke_with_symbols_is_a_line_width(pdfs, module):
    """A2: symbol strokes too print 0.18/0.25/0.5 mm, through every matrix."""
    widths = stroke_widths(pdfs[module])
    assert [w for w in widths if not _on(w, _WIDTHS_MM, _WIDTH_TOLERANCE_MM)] == []
    assert {w for w in widths if _on(w, {float(LINE_THICK_MM)}, _WIDTH_TOLERANCE_MM)}


def test_symbols_do_not_follow_the_module(pdfs):
    """A3: module 2.5 and 3.0 print the same capital heights and line widths, symbols included."""
    small, large = pdfs["2.5"], pdfs["3.0"]
    assert {round(c, 2) for c in _caps(small)} == {round(c, 2) for c in _caps(large)}
    assert set(stroke_widths(small)) == set(stroke_widths(large))


def test_every_symbol_pdf_font_is_dejavu_sans_condensed(pdfs):
    """A4: the symbol texts resolve to the bundled face, whatever the module."""
    for pdf in pdfs.values():
        assert {name.split("+")[-1] for name in font_names(pdf)} <= _FACES


def test_every_symbol_text_names_the_house_face():
    """A4: the symbol texts ("M" and "3") carry font-family "DejaVu Sans" in the page SVG.

    With system fonts off a PDF compile falls back to the bundled face whatever the family, so
    the PDF cannot show a generic `sans-serif`; the SVG the symbol body is drawn into can.
    """
    model, _document = _model(symbols=("motor-3ph",))
    svg = "".join(str(page) for page in pages(model).values())
    texts = re.findall(r"<text [^>]*>([^<]*)</text>", svg)
    assert {"M", "3"} <= set(texts)
    symbol_texts = re.findall(r'<text [^>]*font-family="([^"]*)"[^>]*>[MS3]</text>', svg)
    assert symbol_texts
    assert set(symbol_texts) == {"DejaVu Sans"}
