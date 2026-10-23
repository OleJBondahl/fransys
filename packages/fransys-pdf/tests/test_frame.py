"""The page frame, grid and title block as `source` places them: render's SVG behind each page."""

import re
from decimal import Decimal
from typing import Any

import fransys_render
from _build import (
    cable_facet,
    cable_product_facet,
    document,
    drawing_set,
    item,
    layout_page,
    location,
    model,
    part,
    sheet_format,
    source,
)
from fransys_pdf._background import PAGE_COUNTER_LABEL

from fransys_model.derive import SheetKey, document_sheets_of, harness_cables_for
from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import SheetFormat, default_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm"></svg>'


def _texts(svg: str) -> list[str]:
    return re.findall(r">([^<]+)</text>", svg)


def _cabinet(fmt: SheetFormat | None = None):
    """A cabinet document with one drawn page on `fmt`: the model, the document and the page."""
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=fmt)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    parts = (c1, ds, page, doc) if fmt is None else (c1, fmt, ds, page, doc)
    return model(*parts), doc, page


def _format(name: str, **numbers) -> SheetFormat:
    key = ("sheet_format", name)
    fields: dict[str, Any] = {
        "width_mm": 420,
        "height_mm": 297,
        "content_x_mm": 10,
        "content_y_mm": 10,
        "content_width_mm": 400,
        "content_height_mm": 258,
        "frame_columns": 6,
        "frame_rows": 4,
        "module_mm": Decimal("2.5"),
    } | numbers
    return SheetFormat(id=make_id(SheetFormat, key), key=key, name=name, **fields)


def test_a_20mm_band_gets_a_title_block_and_a_19mm_band_does_not():
    """One mm under 20 already leaves the title block out -- the off-by-one, not just 12 mm."""
    for height, has_block in ((257, True), (258, False)):
        fmt = _format(f"band{height}", content_height_mm=height)  # band = 277 - height
        m, doc, _page = _cabinet(fmt)
        back = fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.COVER, 0)]
        assert (back.counter_box is not None) is has_block
        assert (back.logo_box is not None) is has_block


def test_title_block_band_too_small_still_draws_frame_and_grid_with_no_title_block():
    """A band under 20mm leaves the frame and grid drawn; only the title block is empty."""
    m, doc, page = _cabinet(_format("tight12", content_height_mm=265))
    text = source(
        m, doc.id, {render_id(page.id): _SVG}, fransys_render.sheets(document_sheets_of(m))
    )
    back = fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.COVER, 0)]
    assert '<polygon points="10,10 410,10 410,287 10,287"' in back.svg  # the frame border
    assert sorted(set(_texts(back.svg))) == ["1", "2", "3", "4", "5", "6", "A", "B", "C", "D"]
    assert "Customer" not in _texts(back.svg)  # no title-block label
    assert PAGE_COUNTER_LABEL not in text  # and nothing for the page counter to sit in


def test_the_title_block_prints_its_labels_and_leaves_the_page_cell_to_typst():
    m, doc, page = _cabinet()
    text = source(
        m, doc.id, {render_id(page.id): _SVG}, fransys_render.sheets(document_sheets_of(m))
    )
    back = fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.COVER, 0)]
    assert {"Title", "Customer", "Page"} <= set(_texts(back.svg))
    assert PAGE_COUNTER_LABEL in text  # the counter is Typst's: render's SVG holds no number
    assert "<fransys-page-counter>" in text


def test_grid_columns_come_from_the_sheet_format_not_a_constant():
    """The grid's column count is the sheet's `frame_columns`, not a constant.

    `content_width_mm=380` on a 420 mm sheet with `content_x_mm=10` is deliberately *not*
    `width_mm - 2*content_x_mm` (400): the two must differ for the check to pin the field.
    """
    fmt = _format(
        "wide8", content_width_mm=380, content_height_mm=257, frame_columns=8, frame_rows=6
    )
    m, doc, _page = _cabinet(fmt)
    texts = _texts(fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.COVER, 0)].svg)
    for label in ("1", "2", "3", "4", "5", "6", "7", "8"):
        assert label in texts
    assert "9" not in texts
    # 8 cells over the content width 380: a tick every 47.5 mm from the content x (10).
    assert (
        'x1="57.5" y1="0" x2="57.5" y2="10"'
        in fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.COVER, 0)].svg
    )


def test_grid_columns_with_six_columns_differ_from_eight():
    """The sibling of the can-fail probe: a `frame_columns=6` sheet never shows a `"7"` or `"8"`."""
    fmt = sheet_format("narrow", width_mm=420, height_mm=297, frame_columns=6)
    m, doc, _page = _cabinet(fmt)
    texts = _texts(fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.COVER, 0)].svg)
    for label in ("1", "2", "3", "4", "5", "6"):
        assert label in texts
    assert "7" not in texts
    assert "8" not in texts


def test_no_header_or_footer_argument_on_any_page_kind():
    """The header and footer every page had are gone."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes="Some notes.",
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    text = source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m)))
    assert "header:" not in text
    assert text.count("footer:") == text.count("footer: none") == 1  # no page number (NV4)
    # Absence alone is also true of a blank page with no frame at all: pin that the same
    # page setup that has no header and no footer still has a background (the frame).
    assert "background:" in text


def _harness_with_one_cable():
    harness = item("wh1", description="Demo harness")
    demo_part = part("cab1", description="Invented 4-core cable")
    demo_product = cable_product_facet("cab1", subject=demo_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=demo_part.id, parent=harness.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=1500)
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=(K.CONTENTS, K.BOM),
    )
    m = model(harness, demo_part, demo_product, cable, cf, doc)
    return m, doc, cable


def test_harness_table_page_keeps_the_content_box_margin():
    """A cable run's page keeps the same 5 mm content-box margin (decision pdf-0009)
    the WireViz image used, even with no image left
    to protect the frame border from -- the house text-page padding, not a bare content-box
    fit.
    """
    m, doc, cable = _harness_with_one_cable()
    text = source(
        m,
        doc.id,
        {cable_block_key(None, cable.id): "<svg>block</svg>"},
        fransys_render.sheets(document_sheets_of(m)),
    )
    house = default_sheet_format()
    padding = 5
    content_left = house.content_x_mm + padding
    content_top = house.content_y_mm + padding
    content_right = house.width_mm - house.content_x_mm - house.content_width_mm + padding
    content_bottom = house.height_mm - house.content_y_mm - house.content_height_mm + padding
    margin = (
        f"(left: {content_left}mm, top: {content_top}mm, "
        f"right: {content_right}mm, bottom: {content_bottom}mm)"
    )
    assert f"#page(margin: {{ let m = {margin};" in text
    assert 'fit: "contain"' not in text  # no image anywhere on this page any more
    # The page body is the cable's block image; the per-cable heading line is gone (pdf-0022).
    (found,) = harness_cables_for(m, doc.id, (K.HARNESS_DRAWING,))
    assert found.cable == cable.id
    assert "<svg>block</svg>" in text
    assert "#strong(text(" not in text
