"""The cable pen's shapes are the toolkit's, placed where the grid says (CABLE-DRAWING)."""

import re
from decimal import Decimal

import pytest
from fransys_render._cable_pen import Pen

from electrical_symbols import LIBRARY

_PEN = Pen(LIBRARY, module_mm=Decimal("2.5"), text_height_mm=Decimal("2.5"), pad_g=2)
_MM = 2.5 / 8  # one grid unit
_FONT = float(_PEN.font_mm)
assert LIBRARY.font is not None
_ASCENT = LIBRARY.font.ascent / LIBRARY.font.units_per_em


def _attr(element: str, name: str) -> float:
    found = re.search(rf'\b{name}="([^"]+)"', element)
    assert found is not None
    return float(found.group(1))


def test_a_level_text_hangs_its_top_at_the_given_row() -> None:
    text = _PEN.text("pin", (8, 16), "A1")
    assert _attr(text, "x") == pytest.approx(8 * _MM, abs=1e-4)
    assert _attr(text, "y") == pytest.approx(16 * _MM + _FONT * _ASCENT, abs=1e-4)


def test_an_upward_text_is_centred_on_its_point_and_turned_about_its_baseline() -> None:
    text = _PEN.upward_text("core", (8, 16), "BU")
    x, y = _attr(text, "x"), _attr(text, "y")
    assert x == pytest.approx(8 * _MM - _FONT / 2 + _FONT * _ASCENT, abs=1e-4)
    assert y == pytest.approx(16 * _MM, abs=1e-4)
    assert f"rotate(-90 {x:g} {y:g})" in text
    assert 'text-anchor="middle"' in text


def test_a_dashed_outline_is_four_edges_and_a_solid_one_a_rect() -> None:
    dashed = _PEN.outline("end-box", (0, 0, 16, 8), dashed=True)
    assert dashed.count("<line") == 4
    assert dashed.count('stroke-dasharray="4 1"') == 4
    solid = _PEN.outline("end-box", (0, 0, 16, 8), dashed=False)
    assert solid.count("<rect") == 1
    assert "stroke-dasharray" not in solid


def test_a_wire_is_the_library_style_through_the_grid_points() -> None:
    drawn = _PEN.wire("core", ((0, 0), (8, 0), (8, 16)))
    assert 'points="0,0 2.5,0 2.5,5"' in drawn
    assert 'stroke-width="0.25"' in drawn


def test_the_block_is_padded_half_a_stroke() -> None:
    svg = _PEN.svg(16, 8, "")
    assert 'viewBox="-0.125 -0.125 5.25 2.75"' in svg
