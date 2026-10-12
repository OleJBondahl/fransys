"""model-0195 (A3): render's font size on a label, a marker and a symbol text is `text_size_mm`."""

import dataclasses
import re

import pytest
from fransys_render._labels import _label_element
from fransys_render._markers import _text_element, marker_facing
from fransys_render._symbols import _text_glyph, symbols_on_page

from fransys_model.derive import text_size_mm
from fransys_model.layout import (
    Label,
    LinkMarker,
    Page,
    default_profile,
    layout_of,
    sheet_format_of,
)

pytestmark = pytest.mark.wp("render")

_PROFILE = dataclasses.replace(default_profile(), text_height=5)


def _font_size(svg: str) -> str:
    match = re.search(r'font-size="([^"]+)"', svg)
    assert match
    return match.group(1)


def _expected(sheet) -> str:
    return format(text_size_mm(_PROFILE.text_height, sheet.module_mm).normalize(), "f")


def _page_and_sheet(model):
    page = next(iter(layout_of(model, Page).values()))
    return page, sheet_format_of(model, page.sheet_format)


def test_a_label_prints_at_the_derived_size(cabinet_laid_out):
    page, sheet = _page_and_sheet(cabinet_laid_out)
    label = next(
        item
        for item in layout_of(cabinet_laid_out, Label).values()
        if item.page == page.id and item.slot not in ("contact_no", "contact_nc")
    )
    svg = _label_element(cabinet_laid_out, sheet, _PROFILE, label)
    assert _font_size(svg) == _expected(sheet)


@pytest.mark.parametrize("vertical", [False, True])
def test_a_marker_prints_at_the_derived_size(cabinet_laid_out, vertical):
    _, sheet = _page_and_sheet(cabinet_laid_out)
    marker = next(
        m for m in layout_of(cabinet_laid_out, LinkMarker).values() if m.vertical == vertical
    )
    facing = marker_facing(cabinet_laid_out, marker)
    svg = _text_element(sheet, _PROFILE, cabinet_laid_out, marker, facing)
    assert _font_size(svg) == _expected(sheet)


def test_a_symbol_text_prints_at_the_derived_size(cabinet_laid_out):
    page, sheet = _page_and_sheet(cabinet_laid_out)
    placement = symbols_on_page(cabinet_laid_out, page)[0]
    svg = _text_glyph(sheet, _PROFILE, dataclasses.replace(placement, symbol="unknown"))
    assert _font_size(svg) == _expected(sheet)
