"""The one-grid title block, its logo and notice cells, and one-line fields (spec R11.2-R11.4,
R11.7; acceptance R11 2, 3, 4, 6).

Companion to `test_frame.py` (source-string checks) and `test_frame_compiled.py` (R9/R11.2's
own compiled-page grid and ink checks): this module adds the parts R11 introduced that those
two do not cover -- the logo cell (R11.3), the notice cell and its overflow finding (R11.4),
and the one-line-field cut mechanism and its finding (R11.7).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from itertools import pairwise

import typst
from _build import (
    cable_facet,
    cable_product_facet,
    document,
    drawing_set,
    function_node,
    item,
    layout_page,
    location,
    model,
    page_group,
    part,
    place,
    project,
    unit,
)
from _png import Box, Raster, decode_png, horizontal_rules, ink_bbox, vertical_rules
from fransys_pdf import check, source
from fransys_pdf._frame import (
    TitleBlockFields,
    background,
    band_height_mm,
    cut_to_width,
    fits,
    notice_cell_size_mm,
    notice_fits,
    one_line_field,
    text_width_mm,
    title_columns,
)

from fransys_model.derive import unit_cable_page_key
from fransys_model.derive.designation import own_nodes
from fransys_model.kernel import Severity, make_id
from fransys_model.kernel.ids import render_id
from fransys_model.layout import SheetFormat, default_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
PPI = 72.0
_SVG_LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<rect x="0" y="0" width="10" height="10"/></svg>'
)


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


def _mm(px: float) -> float:
    return px * 25.4 / PPI


def _compile_one_page(text: str, *, ppi: float = PPI):
    png = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=ppi)
    assert isinstance(png, bytes)
    return decode_png(png)


def _minimal_page(sheet: SheetFormat, fields: TitleBlockFields) -> str:
    """A one-page Typst document with only `background(sheet, fields)`, nothing else -- for
    testing `_frame.py`'s own output in isolation, the same fixture shape `test_frame.py`'s
    `_build`-based tests use for `source()`, but skipping the rest of the document pipeline.
    """
    return (
        '#set text(font: "Liberation Serif", size: 10pt)\n'
        f"#set page(width: {sheet.width_mm}mm, height: {sheet.height_mm}mm, margin: 0mm, "
        f"background: {background(sheet, fields)})\n"
    )


def _fields(**overrides: object) -> TitleBlockFields:
    base = TitleBlockFields(
        title="Demo cabinet",
        number="DEMO-1",
        customer="Demo Co",
        revision="1.1",
        revision_date="2026-09-22",
        author="demo",
        page_title="Cover",
        scope="C1 Demo cabinet",
        sheet_counter="",
    )
    return dataclasses.replace(base, **overrides)


# ---------------------------------------------------------------------------
# R11.2 acceptance 2: one shared grid, checked on the compiled page.
# ---------------------------------------------------------------------------


def test_row2_column_boundaries_lie_on_the_shared_column_grid() -> None:
    """Acceptance R11 2: every title-block cell boundary lies on the shared column grid.

    R11.2: "no boundary of one row falls inside a cell of the other unless that cell spans
    it." `Title` spans c1-c3 (row 1), so two of row 2's own boundaries (`customer`|`author`
    at c1, `author`|`page title` at c2) fall *inside* that spanning cell and must show as a
    rule for row 2's own height only, never crossing into row 1's -- that is what "unless
    that cell spans it" permits. The other three (`page title`|`scope` at c3, `scope`|`sheet`
    at c4, `sheet`|`page` at c5) are real edges in both rows and must run the whole band, top
    to bottom: if row 1 used different boundaries there (the old two-independently-weighted-
    rows defect this replaces), the line would stop at the row divider instead of continuing.

    Can-fail: in a scratch copy of `_frame._title_block`, add `5` to `c4` and subtract `5`
    from `c5` before building `columns` (a row-2-only boundary shift) -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k shared_column_grid`, quote the
    `FAILED` id, then restore with Edit.
    """
    sheet = default_sheet_format()
    fields = _fields()
    raster = _compile_one_page(_minimal_page(sheet, fields))

    c1, c2, c3, c4, c5, _c6, _c7, _logo = title_columns(sheet)
    x0 = sheet.content_x_mm
    shared = [x0 + c1 + c2 + c3, x0 + c1 + c2 + c3 + c4, x0 + c1 + c2 + c3 + c4 + c5]
    row2_only = [x0 + c1, x0 + c1 + c2]
    assert len(shared) == 3  # non-zero count before any position check
    assert len(row2_only) == 2

    band_top = float(sheet.content_y_mm + sheet.content_height_mm)
    row_divider = band_top + band_height_mm(sheet) / 2
    band_bottom = float(sheet.height_mm - sheet.content_y_mm)

    for x_mm in shared:
        box = Box(
            x0=_px(x_mm - 1.0),
            x1=_px(x_mm + 1.0),
            y0=_px(band_top + 0.5),
            y1=_px(band_bottom - 0.5),
        )
        rules = vertical_rules(raster, box, min_coverage=0.9)
        assert rules, f"no vertical rule spans the whole band at shared boundary x={x_mm}mm"

    for x_mm in row2_only:
        row2_box = Box(
            x0=_px(x_mm - 1.0),
            x1=_px(x_mm + 1.0),
            y0=_px(row_divider + 0.5),
            y1=_px(band_bottom - 0.5),
        )
        assert vertical_rules(raster, row2_box, min_coverage=0.9), (
            f"no vertical rule in row 2 at its own boundary x={x_mm}mm"
        )
        row1_box = Box(
            x0=_px(x_mm - 1.0),
            x1=_px(x_mm + 1.0),
            y0=_px(band_top + 0.5),
            y1=_px(row_divider - 0.5),
        )
        assert not vertical_rules(raster, row1_box, min_coverage=0.9), (
            f"a vertical rule crosses into row 1's spanning Title cell at x={x_mm}mm"
        )


def test_every_title_block_boundary_is_drawn_exactly_once() -> None:
    """The designer's rule: one stroke per shared boundary, everywhere in the title block --
    no two parallel strokes (of either orientation) closer than 1 mm, which a viewer reads as
    a doubled line.

    Scans row 1's own height and row 2's own height separately for vertical rules (each with
    `min_coverage=0.9`, reliable since every rule in a row-height scan spans that row's full
    10 mm, unlike a scan of the whole 20 mm band, which would under-count a row-2-only
    boundary at half coverage) -- row 1 must show exactly the 5 shared interior boundaries
    plus the frame's own left/right edges (7); row 2 must show those same 7 plus its own two
    boundaries inside `Title`'s span (9, R11.2's "unless that cell spans it"). Consecutive
    positions in either list closer than 1 mm apart are a doubled stroke. The horizontal scan
    (columns c1-c6, R11.2's shared span) must show exactly the band's top edge, the row
    divider and the frame border's own bottom edge (3), same 1 mm rule. Non-zero counts are
    asserted before any spacing check.

    Can-fail (probe, undone with Edit): in `_frame._title_block`, after building `columns` and
    `rows`, add a second `#place` rect: a 0.5 mm-wide black bar about 0.8-1 mm to the right of
    the `Customer`/`Author` boundary (`dx: {x0 + c1 + 0.8}mm`, `dy` at row 2's own top, `height`
    one row) -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k boundary_is_drawn_exactly_once`,
    quote the `FAILED` id, then restore with Edit.
    """
    # A higher PPI than this module's own default: two strokes under 1mm apart (the doubled
    # line this test guards against) are under 3px at 72 PPI, too close to reliably resolve
    # as two separate runs rather than one merged one -- 300 PPI gives over 11px/mm.
    scan_ppi = 300.0

    def _scan_px(mm: float) -> int:
        return round(mm * scan_ppi / 25.4)

    def _scan_mm(p: float) -> float:
        return p * 25.4 / scan_ppi

    sheet = default_sheet_format()
    fields = _fields(notice="A short notice.", logo=None)
    raster = _compile_one_page(_minimal_page(sheet, fields), ppi=scan_ppi)

    c1, c2, c3, c4, c5, c6, c7, logo_w = title_columns(sheet)
    x0 = float(sheet.content_x_mm)
    frame_right = x0 + c1 + c2 + c3 + c4 + c5 + c6 + c7 + logo_w
    band_top = float(sheet.content_y_mm + sheet.content_height_mm)
    row_height = band_height_mm(sheet) / 2
    row_divider = band_top + row_height
    frame_bottom = float(sheet.height_mm - sheet.content_y_mm)

    def _verticals(y0mm: float, y1mm: float) -> list[float]:
        box = Box(
            x0=_scan_px(x0 - 1.0),
            x1=_scan_px(frame_right + 1.0),
            y0=_scan_px(y0mm),
            y1=_scan_px(y1mm),
        )
        return sorted(_scan_mm(p) for p in vertical_rules(raster, box, min_coverage=0.9))

    row1_verticals = _verticals(band_top + 0.5, row_divider - 0.5)
    row2_verticals = _verticals(row_divider + 0.5, frame_bottom - 0.5)
    assert len(row1_verticals) == 7, row1_verticals  # non-zero count before any spacing check
    assert len(row2_verticals) == 9, row2_verticals

    horiz_box = Box(
        x0=_scan_px(x0 + c1 + c2 + 0.5),
        x1=_scan_px(x0 + c1 + c2 + c3 + c4 + c5 + c6 - 0.5),
        y0=_scan_px(band_top - 1.0),
        y1=_scan_px(frame_bottom + 1.0),
    )
    horizontals = sorted(_scan_mm(p) for p in horizontal_rules(raster, horiz_box, min_coverage=0.9))
    assert len(horizontals) == 3, horizontals

    for label, positions in (
        ("row 1", row1_verticals),
        ("row 2", row2_verticals),
        ("band", horizontals),
    ):
        for a, b in pairwise(positions):
            gap = b - a
            assert gap >= 1.0, f"{label}: two parallel strokes {gap:.3f}mm apart: {positions}"


# ---------------------------------------------------------------------------
# R11.3: the square logo cell.
# ---------------------------------------------------------------------------


def test_logo_cell_is_square_and_the_svg_is_drawn_inside_it() -> None:
    """Acceptance R11 3: the logo cell is square, 20x20mm, and an SVG logo is drawn inside it.

    Can-fail (probe, undone with Edit): in `_frame._logo_cell`, replace `image(...)` with `[]`
    (as the "no logo" branch already renders) -- the logo cell then has no ink, and this test
    fails.
    """
    sheet = default_sheet_format()
    _c1, _c2, _c3, _c4, _c5, _c6, c7, logo = title_columns(sheet)
    logo_w, logo_h = logo, band_height_mm(sheet)
    assert logo_w == 20  # R11.3's own number, on the house sheet
    assert logo_h == logo_w  # square: the column width equals the band height
    fields = _fields(logo=_SVG_LOGO)
    raster = _compile_one_page(_minimal_page(sheet, fields))
    band_top = float(sheet.content_y_mm + sheet.content_height_mm)
    x0 = float(sheet.content_x_mm) + sum(title_columns(sheet)[:6]) + c7
    # Inset 1.5mm clear of the cell's own 0.5mm grid-line stroke on every side: the border
    # itself is ink too, so a box that touches it can never tell "the logo was drawn" apart
    # from "the cell is merely bordered" -- exactly the mistake a first version of this test
    # made (it passed even with the logo rendering disabled entirely).
    inset = 1.5
    box = Box(
        x0=_px(x0 + inset),
        x1=_px(x0 + logo - inset),
        y0=_px(band_top + inset),
        y1=_px(band_top + logo - inset),
    )
    bbox = ink_bbox(raster, box)
    assert bbox is not None, "the logo cell has no ink at all"
    bx0, by0, bx1, by1 = bbox
    assert bx0 >= box.x0
    assert bx1 <= box.x1
    assert by0 >= box.y0
    assert by1 <= box.y1


def test_logo_cell_is_empty_with_no_logo() -> None:
    """Acceptance R11 3: no logo leaves the cell empty."""
    sheet = default_sheet_format()
    fields = _fields(logo=None)
    raster = _compile_one_page(_minimal_page(sheet, fields))

    _c1, _c2, _c3, _c4, _c5, _c6, c7, logo = title_columns(sheet)
    band_top = float(sheet.content_y_mm + sheet.content_height_mm)
    x0 = float(sheet.content_x_mm) + sum(title_columns(sheet)[:6]) + c7
    box = Box(
        x0=_px(x0 + 1), x1=_px(x0 + logo - 1), y0=_px(band_top + 1), y1=_px(band_top + logo - 1)
    )
    assert ink_bbox(raster, box) is None, "the logo cell has ink with no logo set"


# ---------------------------------------------------------------------------
# R11.4: the notice cell, wrapped and clipped, and TITLE_BLOCK_NOTICE_OVERFLOW.
# ---------------------------------------------------------------------------


def test_notice_fits_a_short_project_notice() -> None:
    sheet = default_sheet_format()
    width_mm, height_mm = notice_cell_size_mm(sheet)
    assert notice_fits("MIT licence. Not for resale.", width_mm=width_mm, height_mm=height_mm)


def test_notice_does_not_fit_a_long_project_notice() -> None:
    sheet = default_sheet_format()
    width_mm, height_mm = notice_cell_size_mm(sheet)
    long_notice = " ".join(["confidential"] * 40)
    assert not notice_fits(long_notice, width_mm=width_mm, height_mm=height_mm)


def _model_with_notice(notice: str):
    c1 = location("C1", "Demo cabinet")
    proj = project(notice=notice)
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, proj, ds, page, doc)
    return m, doc, page


def test_title_block_notice_overflow_finding_present_for_a_long_notice() -> None:
    """Acceptance R11 4: a notice longer than its cell gives `TITLE_BLOCK_NOTICE_OVERFLOW`.

    Can-fail (probe, undone with Edit): in `checks._notice_overflow_findings`, change
    `if not notice_fits(...)` to `if False` -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k notice_overflow_finding_present`,
    quote the `FAILED` id, then restore with Edit.
    """
    long_notice = " ".join(["confidential"] * 40)
    m, _doc, page = _model_with_notice(long_notice)
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    codes = [f.code for f in findings if f.code == "TITLE_BLOCK_NOTICE_OVERFLOW"]
    assert codes, findings


def test_title_block_notice_overflow_finding_absent_for_a_short_notice() -> None:
    """Acceptance R11 4: a short notice gives no `TITLE_BLOCK_NOTICE_OVERFLOW`."""
    m, _doc, page = _model_with_notice("MIT licence.")
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    codes = [f.code for f in findings if f.code == "TITLE_BLOCK_NOTICE_OVERFLOW"]
    assert not codes, findings


# ---------------------------------------------------------------------------
# R11.7: one-line fields, the page-title rule's mechanism, the `…` cut, and
# TITLE_BLOCK_TEXT_OVERFLOW.
# ---------------------------------------------------------------------------


def test_one_line_field_keeps_the_preferred_text_when_it_fits() -> None:
    result = one_line_field(
        "Field connections, Board", size_pt=10.0, width_mm=100.0, fallback="=FLD =BRD"
    )
    assert result == "Field connections, Board"


def test_one_line_field_falls_back_to_the_equals_labels_when_the_joined_text_does_not_fit() -> None:
    """R11.7's page-title rule: the groups' `=` labels when the joined descriptions don't fit."""
    preferred = "Field connections, Board"
    fallback = "=FLD =BRD"
    width_mm = text_width_mm(fallback, size_pt=10.0) + 2  # fits the fallback, not the preferred
    assert not fits(preferred, size_pt=10.0, width_mm=width_mm)
    assert fits(fallback, size_pt=10.0, width_mm=width_mm)
    result = one_line_field(preferred, size_pt=10.0, width_mm=width_mm, fallback=fallback)
    assert result == fallback


def test_one_line_field_cuts_with_ellipsis_when_neither_candidate_fits() -> None:
    preferred = "Field connections, Board"
    fallback = "=FLD =BRD"
    width_mm = 10.0  # narrower than either candidate at 10pt
    result = one_line_field(preferred, size_pt=10.0, width_mm=width_mm, fallback=fallback)
    assert result.endswith("…")
    assert fits(result, size_pt=10.0, width_mm=width_mm)


def test_cut_to_width_never_widens_the_text() -> None:
    cut, was_cut = cut_to_width(
        "A somewhat long value that will not fit", size_pt=10.0, width_mm=15.0
    )
    assert was_cut
    assert cut.endswith("…")
    assert fits(cut, size_pt=10.0, width_mm=15.0)


def _narrow_customer_sheet() -> SheetFormat:
    """A sheet format whose `customer` cell (c1, less its 2mm inset) is about 8mm wide --
    narrow enough that "Demo Customer Company Ltd" cannot possibly fit at 10pt.
    """
    key = ("sheet_format", "narrowcust")
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="narrowcust",
        width_mm=95,
        height_mm=200,
        content_x_mm=5,
        content_y_mm=10,
        content_width_mm=85,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )


def test_title_block_text_overflow_finding_present_for_a_long_customer_name() -> None:
    """Acceptance R11 6 (the one-line-field half): a value cut to a narrow cell gives
    `TITLE_BLOCK_TEXT_OVERFLOW`, naming the field.

    Can-fail (probe, undone with Edit): in `checks._text_overflow_findings`, change
    `if not fits(...)` to `if False` -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k text_overflow_finding_present`,
    quote the `FAILED` id, then restore with Edit.
    """
    fmt = _narrow_customer_sheet()
    c1 = location("C1", "Demo cabinet")
    proj = project(customer="Demo Customer Company Ltd")
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
    m = model(c1, fmt, proj, ds, page, doc)
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    customer_findings = [
        f for f in findings if f.code == "TITLE_BLOCK_TEXT_OVERFLOW" and "customer" in f.message
    ]
    assert customer_findings, findings
    assert all(f.severity is Severity.WARNING for f in customer_findings)
    # the source itself cuts the same value, ending in the ellipsis, never the full name
    text = source(m, doc.id, svgs)
    assert "Demo Customer Company Ltd" not in text


def test_title_block_text_overflow_finding_absent_for_a_short_customer_name() -> None:
    fmt = _narrow_customer_sheet()
    c1 = location("C1", "Demo cabinet")
    proj = project(customer="X")
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
    m = model(c1, fmt, proj, ds, page, doc)
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    customer_findings = [
        f for f in findings if f.code == "TITLE_BLOCK_TEXT_OVERFLOW" and "customer" in f.message
    ]
    assert not customer_findings, findings


def _title_cell_ink_height_mm(fmt: SheetFormat, title: str) -> float:
    fields = _fields(title=title)
    raster = _compile_one_page(_minimal_page(fmt, fields))
    band_top = float(fmt.content_y_mm + fmt.content_height_mm)
    row_height = band_height_mm(fmt) / 2
    c1, c2, c3, _c4, _c5, _c6, _c7, _logo = title_columns(fmt)
    x0 = float(fmt.content_x_mm)
    box = Box(
        x0=_px(x0 + 1),
        x1=_px(x0 + c1 + c2 + c3 - 1),
        y0=_px(band_top),
        y1=_px(band_top + row_height),
    )
    bbox = ink_bbox(raster, box)
    assert bbox is not None, "the title cell has no ink"
    _bx0, by0, _bx1, by1 = bbox
    return _mm(by1 - by0)


def test_no_one_line_field_ever_spans_two_lines_on_the_compiled_page() -> None:
    """R11.7: 'no title-block field is ever on two lies' -- a title long enough to need cutting
    (R11.7's rule) occupies the same ink height (label line plus one value line) as a title
    short enough to need none, proving the cut value is never itself wrapped across two lines.
    A field that silently wrapped instead of cutting would be noticeably taller: its own extra
    value line, on top of the label line both cases already share.

    No can-fail of its own: disabling `_one_line`'s cut (returning the raw, uncut text) does
    not fail this particular test -- the grid row's own explicit height already bounds the
    scan box this test reads ink from, so an uncut value that overflows *past* the row (rather
    than growing visibly taller within it) is invisible to this measurement. R11.7's own
    can-fail (the same code path) is
    `test_title_block_text_overflow_finding_present_for_a_long_customer_name`, confirmed to
    fail when the cut is disabled.
    """
    fmt = _narrow_customer_sheet()
    short_height = _title_cell_ink_height_mm(fmt, "Short")
    long_height = _title_cell_ink_height_mm(
        fmt, "A very long title that would otherwise wrap across two lines easily"
    )
    # generous tolerance around glyph-height noise (ascenders/descenders differ by string);
    # an extra wrapped value line would add several millimetres, far past this tolerance.
    assert abs(long_height - short_height) <= 1.5, (short_height, long_height)


# ---------------------------------------------------------------------------
# The real document path: `Document.logo`/`Project.notice` reach the title block through
# `source()` (`_section_prefix`/`schematic_source`/`_cable_page`), and R11.7's page-title
# rule (joined descriptions, else the `=` labels) through a real `SCHEMATIC` page's groups.
# ---------------------------------------------------------------------------


def _compile_pages(text: str) -> list[Raster]:
    result = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=PPI)
    pages = [result] if isinstance(result, bytes) else result
    assert pages is not None
    return [decode_png(p) for p in pages]


def test_notice_and_logo_reach_the_title_block_through_the_real_document_path() -> None:
    """The model's own `Document.logo` and `Project.notice` show in the compiled page's title
    block through the real `source()` pipeline, not a hand-built `TitleBlockFields` (this
    module's other tests all use `background()` directly; this one goes through `source()`).

    Can-fail (probe, undone with Edit): in `document._section_prefix`, delete the line
    `logo=record.logo,` (leaving `TitleBlockFields`'s own default `logo=None`) -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k notice_and_logo_reach`, quote the
    `FAILED` id, then restore with Edit.
    """
    c1 = location("C1", "Demo cabinet")
    proj = project(notice="MIT licence. Not for resale outside the project.")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
        logo=_SVG_LOGO,
    )
    m = model(c1, proj, doc)
    text = source(m, doc.id, {})
    raster = _compile_pages(text)[0]  # COVER: the only page left after `remove`

    sheet = default_sheet_format()
    c1w, c2w, c3w, c4w, c5w, c6w, c7w, logo_w = title_columns(sheet)
    band_top = float(sheet.content_y_mm + sheet.content_height_mm)
    x0 = float(sheet.content_x_mm)

    _notice_width_mm, notice_height_mm = notice_cell_size_mm(sheet)
    notice_box = Box(
        x0=_px(x0 + c1w + c2w + c3w + c4w + c5w + c6w + 1.5),
        x1=_px(x0 + c1w + c2w + c3w + c4w + c5w + c6w + c7w - 1.5),
        y0=_px(band_top + 1.5),
        y1=_px(band_top + notice_height_mm + 1.5),
    )
    assert ink_bbox(raster, notice_box) is not None, "the notice cell has no ink"

    logo_x0 = x0 + c1w + c2w + c3w + c4w + c5w + c6w + c7w
    logo_box = Box(
        x0=_px(logo_x0 + 1.5),
        x1=_px(logo_x0 + logo_w - 1.5),
        y0=_px(band_top + 1.5),
        y1=_px(band_top + logo_w - 1.5),
    )
    assert ink_bbox(raster, logo_box) is not None, "the logo cell has no ink"


def _schematic_document_with_groups(
    fmt: SheetFormat, descriptions_and_labels: tuple[tuple[str, str], ...]
):
    """A one-page `SCHEMATIC` document whose page carries one group per `(description, label)`
    pair, on `fmt` -- for R11.7's page-title rule.
    """
    c1 = location("C1", "Demo cabinet")
    nodes = [function_node(label, description) for description, label in descriptions_and_labels]
    groups = tuple(page_group(node=node, index=i) for i, node in enumerate(nodes))
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=fmt, groups=groups)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, fmt, ds, page, *nodes, doc)
    return m, doc, page


def test_page_title_falls_back_to_the_equals_labels_on_a_real_schematic_page() -> None:
    """Acceptance R11 6 (the page-title half): a real `SCHEMATIC` page whose groups' joined
    descriptions do not fit its cell shows the `=` labels instead, through the real
    `source()`/`schematic_source`/`_page_title_labels` path.

    Can-fail (probe, undone with Edit): in `_drawings.schematic_source`, delete the line
    `page_title_fallback=_page_title_labels(model, page),` -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k equals_labels_on_a_real_schematic`,
    quote the `FAILED` id, then restore with Edit.
    """
    fmt = SheetFormat(
        id=make_id(SheetFormat, ("sheet_format", "fallbackfmt")),
        key=("sheet_format", "fallbackfmt"),
        name="fallbackfmt",
        width_mm=140,
        height_mm=200,
        content_x_mm=5,
        content_y_mm=10,
        content_width_mm=130,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    m, doc, page = _schematic_document_with_groups(
        fmt, (("Field connections", "FLD"), ("Board", "BRD"))
    )
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    text = source(m, doc.id, svgs)
    assert "=FLD =BRD" in text
    assert "Field connections, Board" not in text


# ---------------------------------------------------------------------------
# R11.7: TITLE_BLOCK_TEXT_OVERFLOW on the page-level fields (page_title, scope,
# sheet_counter) -- the owner's own motivating case is a page title.
# ---------------------------------------------------------------------------


def test_page_title_text_overflow_finding_absent_when_the_equals_labels_fit() -> None:
    """R11.7: when the `=`-label fallback fits (`test_page_title_falls_back_...` above), the
    rendered page title is never cut, so `TITLE_BLOCK_TEXT_OVERFLOW` is not raised for it.
    """
    fmt = SheetFormat(
        id=make_id(SheetFormat, ("sheet_format", "fallbackfmt2")),
        key=("sheet_format", "fallbackfmt2"),
        name="fallbackfmt2",
        width_mm=140,
        height_mm=200,
        content_x_mm=5,
        content_y_mm=10,
        content_width_mm=130,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    m, _doc, page = _schematic_document_with_groups(
        fmt, (("Field connections", "FLD"), ("Board", "BRD"))
    )
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    page_title_findings = [
        f for f in findings if f.code == "TITLE_BLOCK_TEXT_OVERFLOW" and "page_title" in f.message
    ]
    assert not page_title_findings, findings


def test_page_title_fallback_leaks_a_foreign_units_equals_label_on_a_unit_schematic_page() -> None:
    """RW1 A1: a **unit**-subject SCHEMATIC page's fallback title can leak another unit's
    `=` label. `derive.drawing_text.page_title` (the preferred text) already filters
    `page.groups` to `own_nodes(model, unit)`, so the preferred text here is `u_own`'s own
    node's description alone; `_drawings._page_title_labels` (the fallback text) does not
    filter at all, so it joins in `u_other`'s label too, even though `u_other`'s node is
    genuinely foreign to this page's own unit -- a real, owned-by-someone-else group, not
    merely an unowned one (F9 would already exclude that case correctly).

    A page can legitimately carry a foreign group: layout's page builder appends every
    placement's group with no unit filter (this fixture's `page.groups` mirrors that shape).

    Can-fail: the assertion `"=EXT" not in text` below is the one that currently fails --
    `_page_title_labels` renders `"=FLD =EXT"`, leaking `u_other`'s `=EXT` label into
    `u_own`'s page title fallback.
    """
    fmt = SheetFormat(
        id=make_id(SheetFormat, ("sheet_format", "fallbackfmt_unit")),
        key=("sheet_format", "fallbackfmt_unit"),
        name="fallbackfmt_unit",
        width_mm=140,
        height_mm=200,
        content_x_mm=5,
        content_y_mm=10,
        content_width_mm=130,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    u_own = unit("u_own", name="Cabinet Own")
    u_other = unit("u_other", name="Cabinet Other")
    item_own = item("i_own", description="Own item", unit=u_own.id)
    item_other = item("i_other", description="Other item", unit=u_other.id)
    # Same description text as `_schematic_document_with_groups`'s known-not-fitting joined
    # pair above ("Field connections, Board" overflows `fallbackfmt`'s page_title cell) --
    # here it is one own node's *whole* description, so `page_title`'s own-only filtering
    # still overflows the cell even though the foreign node is excluded from it.
    own_node = function_node("FLD", "Field connections, Board")
    foreign_node = function_node("EXT", "External")
    own_placement = place("p_own", item=item_own.id, node=own_node.id)
    foreign_placement = place("p_foreign", item=item_other.id, node=foreign_node.id)
    ds = drawing_set("ds1", unit=u_own)
    page = layout_page(
        "p1",
        drawing_set=ds,
        number=1,
        sheet_format=fmt,
        groups=(page_group(node=own_node, index=0), page_group(node=foreign_node, index=1)),
    )
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u_own,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(
        u_own,
        u_other,
        item_own,
        item_other,
        own_node,
        foreign_node,
        own_placement,
        foreign_placement,
        fmt,
        ds,
        page,
        doc,
    )

    # Precondition sanity: the fixture really does make one node `u_own`'s own and the other
    # genuinely foreign, not merely unowned.
    assert own_node.id in own_nodes(m, u_own.id)
    assert foreign_node.id not in own_nodes(m, u_own.id)

    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    text = source(m, doc.id, svgs)

    # Positive: the fallback path rendered something real, not "No drawings."
    assert "=FLD" in text
    # The own-only description was never printed: the preferred text overflowed, so we are
    # on the fallback path, not the primary-text path.
    assert "Field connections, Board" not in text
    # The bug: a foreign unit's `=` label leaks into `u_own`'s page title fallback.
    assert "=EXT" not in text


def test_page_title_text_overflow_finding_present_when_the_equals_labels_also_dont_fit() -> None:
    """Acceptance R11 6 (the page-title half, the owner's own motivating case): a page title
    whose joined descriptions AND `=`-label fallback both fail to fit is cut with `…`, and
    `TITLE_BLOCK_TEXT_OVERFLOW` names the field and the page.

    Can-fail (probe, undone with Edit): in `checks._schematic_page_overflow_findings`, add
    `return ()` as its first line -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k
    page_title_text_overflow_finding_present`, quote the `FAILED` id, then restore with Edit.
    """
    fmt = _narrow_customer_sheet()  # page_title cell ~14.7mm: too narrow for "=FLD =BRD" (~18.8mm)
    m, doc, page = _schematic_document_with_groups(
        fmt, (("Field connections", "FLD"), ("Board", "BRD"))
    )
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    page_title_findings = [
        f
        for f in findings
        if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"
        and "page_title" in f.message
        and "page 1" in f.message
    ]
    assert page_title_findings, findings
    text = source(m, doc.id, svgs)
    assert "…" in text
    assert "Field connections, Board" not in text
    assert "=FLD =BRD" not in text


# ---------------------------------------------------------------------------
# Mutmut gaps: the `title` field's own bold branch, its severity, the SCHEMATIC-page
# `scope` finding, and the whole HARNESS_DRAWING-page overflow function -- none of the
# tests above exercises any of these four.
# ---------------------------------------------------------------------------


def test_title_block_text_overflow_finding_present_for_a_long_title_and_is_a_warning() -> None:
    """`_one_line_overflow_finding`'s own `bold = field == "title"` branch (checks.py L165) is
    never independently exercised above -- every overflow test overflows `customer`,
    `page_title` or `scope`, never the document's own `title` field, so the bold-vs-regular
    width table (`_BOLD_WIDTHS_EM`) this branch selects was never checked. `long_title` is
    chosen (all `M`/`W`, the widest letters) to sit in the narrow band where the *regular*
    Liberation Serif metrics fit the title cell but the *bold* ones do not -- so a mutant that
    drops or inverts the `bold` selection makes the finding vanish, not merely shrink; a
    string that overflows both ways (as the customer-name candidates elsewhere in this file
    do) would not distinguish the two. Also asserts `.severity is Severity.WARNING` for this
    code (spec `docs/archive/specs/2026-09-22-page-frame.md` R11 6/`TITLE_BLOCK_TEXT_OVERFLOW` is a
    WARNING), never read anywhere else in this file.

    Can-fail (probe, undone with Edit): in `checks._one_line_overflow_finding`, change
    `bold = field == "title"` to `bold = False` -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k
    long_title_and_is_a_warning`, quote the `FAILED` id, then restore with Edit.
    """
    fmt = _narrow_customer_sheet()
    c1 = location("C1", "Demo cabinet")
    long_title = "WWWMMMMMM"  # fits the title cell at 12pt regular, not at 12pt bold
    proj = project(title=long_title)
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
    m = model(c1, fmt, proj, ds, page, doc)
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    title_findings = [
        f
        for f in findings
        if f.code == "TITLE_BLOCK_TEXT_OVERFLOW" and f.message.startswith("title (")
    ]
    assert title_findings, findings
    assert all(f.severity is Severity.WARNING for f in title_findings)


def test_schematic_page_scope_text_overflow_finding_present_for_a_long_unit_label() -> None:
    """`_schematic_page_overflow_findings`'s `scope` finding (checks.py L237-244) is never
    triggered by any test above -- every `SCHEMATIC` document under test there is a
    location subject whose short label ("C1") fits, or has no `scope` check reached at all.
    This is a **unit**-subject `SCHEMATIC` document (`record.location is None`, so `scope`
    reads `subject_label`, the `else` branch at checks.py L240), whose unit's own label is
    long enough to overflow the narrow `scope` cell (~7.2mm on `_narrow_customer_sheet`).

    Can-fail (probe, undone with Edit): in `checks._schematic_page_overflow_findings`,
    change `where="SCHEMATIC"` to `where="X"` for the `scope` finding -- run `pytest
    packages/fransys-pdf/tests/test_title_block.py -q -k
    schematic_page_scope_text_overflow_finding_present`, quote the `FAILED` id, then restore
    with Edit.
    """
    fmt = _narrow_customer_sheet()
    long_name = "A Very Long Unit Name Used Only For Testing The Scope Cell Overflow Path"
    u1 = unit("u1", name=long_name)
    ds = drawing_set("ds1", unit=u1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=fmt)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(u1, fmt, ds, page, doc)
    svgs = {render_id(page.id): "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    scope_findings = [
        f
        for f in findings
        if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"
        and f.message.startswith("scope (")
        and "SCHEMATIC" in f.message
    ]
    assert scope_findings, findings


def test_harness_page_title_text_overflow_finding_present_for_a_long_cable_designation() -> None:
    """`_harness_page_overflow_findings` (checks.py L264-295) has no covering test anywhere in
    this module -- a `HARNESS_DRAWING` page's own `scope` and `page_title` (cable-title)
    overflow checks are otherwise never exercised. Builds a unit's own cable
    (`derive.unit_cables`, decision pdf-0015, the same shape
    `test_unit_harness_drawings._unit_with_cables` uses) whose long tag makes `cable_title`
    (the cable's own `designation` plus its part's `mpn`, model-0108's `is_cable` now needs a
    `cable_product` facet on a real `Part` for this to be a cable at all) overflow the narrow
    `page_title` cell,
    and gives the unit itself a long label so `scope` (`subject_label`, since this document's
    `item` is `None`) overflows too -- both findings this function can raise are asserted,
    not only the cable one.

    The unit also carries a `SCHEMATIC` page on the same narrow sheet, so `resolve_sheet_format`
    picks it: a pure `HARNESS_DRAWING`-only document always resolves to the wide house sheet
    (`_geometry.resolve_sheet_format`'s "no `SCHEMATIC` pages" case), which neither long value
    would overflow. That `SCHEMATIC` page's own svg key is left out of `svgs`, so
    `_schematic_page_overflow_findings` exits early on the missing key and contributes no
    finding of its own, isolating both assertions below to the harness page.

    Can-fail (probe, undone with Edit): in `checks._harness_page_overflow_findings`, add
    `return findings` right after `findings = []` (skipping the scope check and the cable
    loop) -- run `pytest packages/fransys-pdf/tests/test_title_block.py -q -k
    harness_page_title_text_overflow_finding_present`, quote the `FAILED` id, then restore
    with Edit.
    """
    fmt = _narrow_customer_sheet()
    long_unit_name = "A Very Long Unit Name Used Only For Testing The Harness Scope Overflow"
    u1 = unit("u1", name=long_unit_name)
    ds = drawing_set("ds1", unit=u1)
    schem_page = layout_page("p_schem", drawing_set=ds, number=1, sheet_format=fmt)
    long_tag = "wire_with_a_very_long_designation_used_only_for_testing_overflow"
    cable_part = part(long_tag, description="Cable one part")
    cable_product = cable_product_facet(long_tag, subject=cable_part.id, core_count=0)
    w1 = item(long_tag, description="A cable", unit=u1.id, part=cable_part.id)
    w1_facet = cable_facet(long_tag, subject=w1.id, length_mm=None)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
        add=(K.HARNESS_DRAWING,),
    )
    m = model(u1, fmt, ds, schem_page, w1, w1_facet, doc, cable_part, cable_product)
    cable_svg_key = unit_cable_page_key(u1.id, w1.id)
    svgs = {cable_svg_key: "<svg xmlns='http://www.w3.org/2000/svg'/>"}
    findings = check(m, svgs)
    page_title_findings = [
        f for f in findings if f.code == "TITLE_BLOCK_TEXT_OVERFLOW" and "page_title" in f.message
    ]
    assert page_title_findings, findings
    # the finding's `where` and the cut value both carry the cable's own tag-based designation
    assert w1.tag is not None
    assert any(w1.tag in f.message for f in page_title_findings)

    scope_findings = [
        f
        for f in findings
        if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"
        and f.message.startswith("scope (")
        and "HARNESS_DRAWING" in f.message
    ]
    assert scope_findings, findings
