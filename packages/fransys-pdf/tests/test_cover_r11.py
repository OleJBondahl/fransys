"""page-frame spec R11.5, R11.6 (`docs/archive/specs/2026-09-22-page-frame.md`); acceptance R11 5.

`_pages.cover_page` (R11.5, R11.6) and `_cover_checks.cover_overflow_findings` (R11.6's
`COVER_OVERFLOW`). Positions are measured on the COMPILED page, the same PNG route
`test_frame_compiled.py` uses (`pdf-0004`), within the acceptance's own 0.5 mm tolerance.
"""

from __future__ import annotations

import pytest
import typst
from _build import document, model, project, revision_entry
from _png import Box, Raster, decode_png, ink_bbox, vertical_rules
from fransys_pdf import source
from fransys_pdf._cover_checks import (
    _cover_text_height_mm,
    _element_text,
    _line_count,
    _table_height_mm,
    _text_height_mm,
    cover_overflow_findings,
)
from fransys_pdf._markdown import Paragraph, Run, Unsupported
from fransys_pdf._pages import DESCRIPTION_WIDTH_MM, TABLE_HEADER_MM
from fransys_pdf.document import document_pages

from fransys_model.kernel import Severity
from fransys_model.layout import default_sheet_format
from fransys_model.vocab import DocumentPreset, documents

PPI = 72.0
SHEET = default_sheet_format()
CENTRE_TOLERANCE_MM = 0.5  # acceptance R11 5's own tolerance
BOTTOM_EDGE_TOLERANCE_MM = 2.0  # Typst's own cell inset (measured 0.7-1.5 mm), not the 0.5 mm above
_COVER_TEXT = (
    "Some short intro text.\n"
    "\n"
    "- A short item\n"
    "- A somewhat longer bullet item text goes here for testing\n"
    "\n"
    "1. First\n"
    "2. Second numbered item with more text\n"
)


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


def _mm(px: float) -> float:
    return px * 25.4 / PPI


def _cover_raster(*records) -> Raster:
    """Compile a `SYSTEM`-preset document (COVER only, no location/item/unit subject) to PNG."""
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=_COVER_TEXT)
    m = model(*records, doc)
    text = source(m, doc.id, {})
    pngs = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=PPI)
    page = pngs[0] if isinstance(pngs, list) else pngs  # a one-page document is one `bytes`
    assert isinstance(page, bytes)
    return decode_png(page)


def _text_bands(raster: Raster) -> list[tuple[float, float, float, float]]:
    """`(y0mm, y1mm, x0mm, x1mm)` ink bands inside the content box, clear of the frame, the
    grid strips and the title-block band -- the cover's own flowed text only.
    """
    x0mm = SHEET.content_x_mm + 12
    x1mm = SHEET.width_mm - SHEET.content_x_mm - 12
    # 11.0, not `SHEET.content_y_mm + 1`: the top grid strip is 10 mm deep regardless of the
    # content box's own top (`_frame._GRID_STRIP_MM`, this package's own R2), and R11.1's 5 mm
    # content-box margin now sits inside that strip's depth -- a pending `_frame.py` fix outside
    # this part's scope (`test_frame_compiled.py`'s own R11 failures are exactly this). Scanning
    # from just clear of the strip keeps this module's own bands to the cover's real text.
    y0mm = 11.0
    y1mm = SHEET.content_y_mm + SHEET.content_height_mm - 15  # clear of the revision table
    x0, x1 = _px(x0mm), _px(x1mm)
    y0, y1 = _px(y0mm), _px(y1mm)

    def row_has_ink(y: int) -> bool:
        return any(raster.is_dark(x, y, threshold=200) for x in range(x0, x1))

    rows = [y for y in range(y0, y1) if row_has_ink(y)]
    bands: list[tuple[int, int]] = []
    if rows:
        start = prev = rows[0]
        for y in rows[1:]:
            if y - prev <= 2:
                prev = y
            else:
                bands.append((start, prev))
                start = prev = y
        bands.append((start, prev))

    out = []
    for y0b, y1b in bands:
        bbox = ink_bbox(raster, Box(x0=x0, x1=x1, y0=y0b, y1=y1b + 1))
        assert bbox is not None
        bx0, by0, bx1, by1 = bbox
        out.append((_mm(by0), _mm(by1), _mm(bx0), _mm(bx1)))
    return out


def test_heading_first_and_every_cover_line_centred() -> None:
    """R11.5: the heading is the first text in the content box; every cover line -- the
    heading, the paragraph, both list kinds -- is centred within 0.5 mm.

    Can-fail (probe, undone with Edit): removing `_pages.cover_page`'s `align(center, [...])`
    wrap (bare `[heading, body]` instead) fails this test -- confirmed -- because every band's
    centre then sits flush left instead of at the page centre.
    """
    raster = _cover_raster(project())
    bands = _text_bands(raster)
    # non-zero count before any position check (the acceptance's own pattern, R9/R11.2)
    assert len(bands) >= 6, bands  # heading, paragraph, 2 bullets, 2 numbered items

    page_centre_mm = _mm(raster.width / 2)
    for y0mm, _y1mm, x0mm, x1mm in bands:
        centre = (x0mm + x1mm) / 2
        assert abs(centre - page_centre_mm) <= CENTRE_TOLERANCE_MM, (y0mm, x0mm, x1mm, centre)

    heading_top = min(y0mm for y0mm, _y1, _x0, _x1 in bands)
    assert heading_top < SHEET.content_y_mm + 10, (
        "the first cover line is not near the content box top",
        heading_top,
    )


def test_revision_table_bottom_edge_at_content_box_bottom() -> None:
    """R11.6: the history table's bottom edge sits at the content box bottom (on the title
    block), within `BOTTOM_EDGE_TOLERANCE_MM`.

    Measured on the last row's own text ink, not a rule: the table's rows are auto height
    (R11.6, amended 2026-09-24, "sized to its content"), so unlike before this module cannot
    compute one exact expected mm value for the table's own top edge without compiling. A
    rule-based measurement has its own problem regardless of row height: the table's bottom
    border sits within a pixel of the title-block band's own top rule (R2's frame border)
    whether or not the table itself is where R11.6 asks for it, so it cannot itself tell a
    right position from a wrong one. `BOTTOM_EDGE_TOLERANCE_MM` (2 mm, not the acceptance's
    0.5 mm) covers Typst's own default cell inset between a row's text baseline and the
    table's real box edge (confirmed empirically at 0.7-1.5 mm) -- a genuine mispositioning
    (the can-fail below, a missing 5 mm) is still well outside it.

    Can-fail (probe, undone with Edit): zeroing `_pages.cover_page`'s table `dy` (so the table
    aligns to the margin box's own bottom, not the content box's, 5 mm short) fails this test.
    """
    r1 = revision_entry("r1", unit=None, revision=1, date="2026-01-01", text="First release")
    r2 = revision_entry("r2", unit=None, revision=2, date="2026-02-01", text="Second release")
    raster = _cover_raster(project(), r1, r2)

    content_bottom_mm = SHEET.content_y_mm + SHEET.content_height_mm
    box = Box(
        x0=_px(SHEET.content_x_mm + 20),
        x1=_px(SHEET.width_mm - SHEET.content_x_mm - 20),
        y0=_px(content_bottom_mm - 30),
        # `- 0.5`, not `+ 1`: the title-block band's own top rule (R2's frame border) sits
        # within a pixel of the content box bottom regardless of the table's own position, so
        # a window reaching past it would find that ink instead of the table's real bottom,
        # even when the table itself is wrong (confirmed: this can-fail's own probe passed
        # before this fix, for exactly that reason).
        y1=_px(content_bottom_mm - 0.5),
    )
    bbox = ink_bbox(raster, box)
    assert bbox is not None, "no table ink found near the content box bottom"
    _bx0, _by0, _bx1, by1 = bbox
    table_bottom_mm = _mm(by1)
    assert content_bottom_mm - table_bottom_mm <= BOTTOM_EDGE_TOLERANCE_MM, (
        table_bottom_mm,
        content_bottom_mm,
    )


def test_revision_table_narrower_than_content_box_and_description_wraps_at_120mm() -> None:
    """R11.6 (amended 2026-09-24): "sized to its content" -- the table is narrower than the
    content box and centred (0.5 mm), and a long `description` wraps inside 120 mm.

    The table's own outer and internal column-divider strokes (`stroke: 0.5pt` on every
    cell) span the table's full height, so `vertical_rules` finds exactly 7 of them (6
    columns) reliably, regardless of how many lines a wrapped description takes -- unlike
    ink, which cannot be told apart from the frame's own border this close to the title
    block (`test_revision_table_bottom_edge_at_content_box_bottom`'s own problem).

    Can-fail (probe, undone with Edit): widening `_pages._revision_table`'s description
    column back to `1fr` (this module's old, pre-amendment design) fails this test.
    """
    long_text = (
        "This is a very long description of the revision that should wrap across several "
        "lines because it is much longer than one hundred twenty millimetres can hold on a "
        "single line at nine points."
    )
    r1 = revision_entry("r1", unit=None, revision=1, date="2026-01-01", text=long_text)
    raster = _cover_raster(project(), r1)

    content_bottom_mm = SHEET.content_y_mm + SHEET.content_height_mm
    x0mm = SHEET.content_x_mm + 10
    x1mm = SHEET.width_mm - SHEET.content_x_mm - 10
    # A wide search window first, to find the table's own y-extent regardless of how many
    # lines the description wraps to; `vertical_rules`' coverage ratio needs a box no taller
    # than the table's own content, or the divider strokes' real, full-height coverage is
    # diluted by the empty rows above them and none reach its threshold.
    search = Box(
        x0=_px(x0mm), x1=_px(x1mm), y0=_px(content_bottom_mm - 40), y1=_px(content_bottom_mm - 0.5)
    )
    table_bbox = ink_bbox(raster, search)
    assert table_bbox is not None, "no table ink found near the content box bottom"
    _bx0, by0, _bx1, by1 = table_bbox

    box = Box(x0=_px(x0mm), x1=_px(x1mm), y0=by0, y1=by1 + 1)
    vlines = vertical_rules(raster, box, min_coverage=0.9)
    assert len(vlines) == 7, vlines  # 6 columns: the table's own outer + 5 internal dividers
    xs_mm = [_mm(v) for v in vlines]

    table_width_mm = xs_mm[-1] - xs_mm[0]
    assert table_width_mm < SHEET.content_width_mm - 50, table_width_mm  # meaningfully narrower
    table_centre_mm = (xs_mm[0] + xs_mm[-1]) / 2
    page_centre_mm = _mm(raster.width / 2)
    assert abs(table_centre_mm - page_centre_mm) <= CENTRE_TOLERANCE_MM, (
        table_centre_mm,
        page_centre_mm,
    )

    description_width_mm = xs_mm[3] - xs_mm[2]  # revision|date|[description]|created|...
    assert description_width_mm <= DESCRIPTION_WIDTH_MM + 0.5, description_width_mm  # stroke slack


def test_revision_table_rows_oldest_first_with_six_columns() -> None:
    """R11.6: columns revision/date/description/created/checked/approved, oldest entry first."""
    r_new = revision_entry(
        "rb", unit=None, revision=2, date="2026-02-01", text="Second", created="AB"
    )
    r_old = revision_entry(
        "ra", unit=None, revision=1, date="2026-01-01", text="First", created="OJB"
    )
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=_COVER_TEXT)
    m = model(project(), r_new, r_old, doc)
    body = source(m, doc.id, {})

    for header in ("Revision", "Date", "Description", "Created", "Checked", "Approved"):
        assert f'"{header}"' in body, header
    # oldest first: the "1.1"/"First"/"OJB" row's own text appears before "1.2"/"Second"/"AB"'s
    assert body.index('"First"') < body.index('"Second"')
    assert body.index('"1.1"') < body.index('"1.2"')


def test_no_table_when_history_is_empty() -> None:
    """R11.6: no `Revision` entries (project's or the unit's) gives no table at all."""
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=_COVER_TEXT)
    m = model(project(), doc)
    body = source(m, doc.id, {})
    assert "#table(" not in body


def test_cover_overflow_clean_case() -> None:
    """`COVER_OVERFLOW`'s clean case: short cover text, a short history, no finding."""
    r1 = revision_entry("r1", unit=None, revision=1, date="2026-01-01", text="Release")
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=_COVER_TEXT)
    m = model(project(), r1, doc)
    pages = document_pages(m, doc.id)
    findings = cover_overflow_findings(m, doc.id, documents(m)[doc.id], pages)
    assert findings == ()


def test_cover_overflow_failing_case() -> None:
    """`COVER_OVERFLOW`'s failing case: a long enough history alone overflows the content box,
    even with the same short cover text as the clean case -- the table "keeps its place"
    (R11.6), it does not shrink to fit, so a big enough history alone is already too tall.
    """
    entries = tuple(
        revision_entry(f"r{i}", unit=None, revision=i, date=f"2026-{(i % 12) + 1:02d}-01", text="x")
        for i in range(1, 61)
    )
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=_COVER_TEXT)
    m = model(project(), *entries, doc)
    pages = document_pages(m, doc.id)
    findings = cover_overflow_findings(m, doc.id, documents(m)[doc.id], pages)
    assert len(findings) == 1
    assert findings[0].code == "COVER_OVERFLOW"
    assert findings[0].severity is Severity.WARNING
    assert findings[0].subjects == (doc.id,)


# -- Direct calls to `_cover_checks`'s five private pure helpers (never called directly by the
# -- tests above, only through `cover_overflow_findings`'s pass/fail boundary). Each assertion
# -- is a hand-computed value from the module's own documented formula (`_pt_to_mm`, the 0.5
# -- char-width fraction, the 1.3 line height), not a re-read of its private structure.


def test_line_count_empty_text_returns_one() -> None:
    """`_line_count`'s own empty-text guard fires before the wrapping formula runs at all."""
    assert _line_count("", width_mm=100, size_pt=10) == 1


def test_line_count_exact_wrapped_count() -> None:
    """Hand-computed from the formula: `chars_per_line=20` (from `width_mm`) wraps 40 characters
    to exactly 2 lines -- `20.5`, not `20.0`, keeps the case off the `int()` truncation boundary.
    """
    size_pt = 10
    char_width_mm = (size_pt * 25.4 / 72.0) * 0.5
    width_mm = 20.5 * char_width_mm
    assert _line_count("x" * 40, width_mm=width_mm, size_pt=size_pt) == 2


def test_line_count_chars_per_line_floors_at_one() -> None:
    """`chars_per_line`'s own `max(1, ...)` floor: a ratio of `1.5` (above 1, below 2) still
    floors to exactly 1 char per line, so 3 characters take 3 lines, not `ceil(3 / 2) == 2`."""
    size_pt = 10
    char_width_mm = (size_pt * 25.4 / 72.0) * 0.5
    width_mm = 1.5 * char_width_mm
    assert _line_count("abc", width_mm=width_mm, size_pt=size_pt) == 3


def test_line_count_short_text_floors_result_at_one_not_two() -> None:
    """The outer `max(1, ceil(...))` floor: a short string in a wide column is exactly 1 line,
    never bumped past that by the floor itself."""
    assert _line_count("hi", width_mm=1000, size_pt=10) == 1


def test_line_count_larger_size_gives_more_lines_not_fewer() -> None:
    """Bigger glyphs (`size_pt`) mean fewer characters fit per line and so MORE wrapped lines --
    a multiply/divide swap on the `width_mm / char_width_mm` ratio would invert this direction."""
    text = "x" * 100
    smaller_size = _line_count(text, width_mm=50, size_pt=8)
    larger_size = _line_count(text, width_mm=50, size_pt=16)
    assert larger_size > smaller_size


def test_text_height_mm_hand_computed() -> None:
    """`_text_height_mm` is `_line_count` lines at `size_pt`'s own mm height times the 1.3 line
    height -- computed by hand from the same formula, at a width that keeps this text to 1 line.
    """
    size_pt = 10.0
    width_mm = 1000.0
    line_count = _line_count("x" * 20, width_mm=width_mm, size_pt=size_pt)
    assert line_count == 1
    expected = line_count * (size_pt * 25.4 / 72.0) * 1.3
    assert _text_height_mm("x" * 20, width_mm=width_mm, size_pt=size_pt) == pytest.approx(expected)


def test_element_text_unsupported_returns_its_own_text_unchanged() -> None:
    """An `Unsupported` element's `.text` (its verbatim source line) passes through untouched."""
    element = Unsupported(line=1, construct="table", text="| a | b |")
    assert _element_text(element) == "| a | b |"


def test_element_text_joins_runs_without_a_separator() -> None:
    """Bare `"".join`, not a space-joined join -- two runs concatenate directly, back to back."""
    element = Paragraph(line=1, runs=(Run("plain", "foo"), Run("bold", "bar")))
    assert _element_text(element) == "foobar"


def test_cover_text_height_mm_sums_heading_paragraph_and_bullets() -> None:
    """One document mixing a `#` heading, a plain paragraph and a bullet list: the total is the
    document heading's own height plus every parsed element's, each at the right size (heading
    vs. body) -- hand-computed the same way `_cover_text_height_mm` composes them, at a width
    wide enough that every piece here is exactly 1 line (checked, not assumed).
    """
    cover = "# Heading text\n\nA plain paragraph line here.\n\n- item one\n- item two\n"
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=cover)
    m = model(project(), doc)
    record = documents(m)[doc.id]
    width_mm = 1000.0

    def piece(text: str, size_pt: float) -> float:
        assert _line_count(text, width_mm=width_mm, size_pt=size_pt) == 1
        return (size_pt * 25.4 / 72.0) * 1.3

    expected = (
        piece("System", 16)  # document_heading(m, record): SYSTEM preset, no subject label
        + piece("Heading text", 16)
        + piece("A plain paragraph line here.", 10)
        + piece("item one", 10)
        + piece("item two", 10)
    )
    actual = _cover_text_height_mm(m, record, width_mm=width_mm)
    assert actual == pytest.approx(expected)


def test_table_height_mm_empty_history_is_zero() -> None:
    assert _table_height_mm(()) == 0.0


def test_table_height_mm_hand_computed() -> None:
    """The header plus each entry's own wrapped height at `DESCRIPTION_WIDTH_MM`, `_TABLE_PT`
    (9pt) -- hand-computed the same way, from two short entries that each stay 1 line."""
    r1 = revision_entry("r1", unit=None, revision=1, date="2026-01-01", text="Short one")
    r2 = revision_entry("r2", unit=None, revision=2, date="2026-02-01", text="Short two")
    size_pt = 9.0
    line_count = _line_count("Short one", width_mm=DESCRIPTION_WIDTH_MM, size_pt=size_pt)
    assert line_count == 1
    row_height = line_count * (size_pt * 25.4 / 72.0) * 1.3
    expected = TABLE_HEADER_MM + 2 * row_height
    assert _table_height_mm((r1, r2)) == pytest.approx(expected)


def test_cover_overflow_message_reports_the_computed_heights() -> None:
    """`COVER_OVERFLOW`'s message carries the same `text_height`/`table_height` this module's own
    helpers compute -- not just that the code and severity fire (`test_cover_overflow_failing_case`
    above checks only that).
    """
    entries = tuple(
        revision_entry(f"r{i}", unit=None, revision=i, date=f"2026-{(i % 12) + 1:02d}-01", text="x")
        for i in range(1, 61)
    )
    doc = document("d1", preset=DocumentPreset.SYSTEM, subject=None, cover=_COVER_TEXT)
    m = model(project(), *entries, doc)
    record = documents(m)[doc.id]
    pages = document_pages(m, doc.id)
    findings = cover_overflow_findings(m, doc.id, record, pages)
    assert len(findings) == 1

    padding_mm = 5  # `_cover_checks._PADDING_MM`, R4's spec-fixed inner padding (module docstring)
    width_mm = SHEET.content_width_mm - 2 * padding_mm
    expected_text_height = _cover_text_height_mm(m, record, width_mm=width_mm)
    expected_table_height = _table_height_mm(entries)

    message = findings[0].message
    assert f"~{expected_text_height:.0f}mm" in message
    assert f"~{expected_table_height:.0f}mm" in message
