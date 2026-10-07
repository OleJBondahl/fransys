"""The page frame, grid and title block (page-frame spec R1-R6, acceptance 1-5)."""

from decimal import Decimal

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
)
from fransys_pdf import source
from fransys_pdf._drawings import harness_cables_for
from fransys_pdf._frame import (
    _wrap_lines,
    band_height_mm,
    cut_to_width,
    fits,
    notice_fits,
    text_width_mm,
    title_block_fits,
)

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel import make_id
from fransys_model.kernel.ids import render_id
from fransys_model.layout import SheetFormat, default_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind, documents

K = PageKind
_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm"></svg>'


def test_house_sheet_band_is_20mm_and_fits():
    house = default_sheet_format()
    assert band_height_mm(house) == 20
    assert title_block_fits(house)


def test_a_19mm_band_does_not_fit():
    """One mm under 20 already trips `TITLE_BLOCK_NO_ROOM` -- the off-by-one, not just 12 mm."""
    key = ("sheet_format", "tight19")
    tight = SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="tight19",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=258,  # band = (297-10) - (10+258) = 19
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    assert band_height_mm(tight) == 19
    assert not title_block_fits(tight)


def test_title_block_band_too_small_still_draws_frame_and_grid_with_no_title_block():
    """R6: a band under 20mm leaves the frame and grid drawn; only the title block is empty."""
    c1 = location("C1", "Demo cabinet")
    key = ("sheet_format", "tight12")
    tight = SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="tight12",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=265,  # band = (297-10) - (10+265) = 12
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1, sheet_format=tight)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, tight, ds, page, doc)
    svgs = {render_id(page.id): _SVG}
    text = source(m, doc.id, svgs)
    # Frame border, sized from width_mm/height_mm/content_x_mm/content_y_mm alone, still drawn.
    assert "rect(width: 400mm, height: 277mm, stroke: 0.5mm)" in text
    # Grid still drawn: column 1's label is present.
    assert 'text(size: 8pt, "1")' in text
    # No title-block content at all: `_cell`'s own label/value stack never appears. (The
    # cover page's own project-facts table also says "Title", so that alone isn't specific
    # enough -- this checks for the title-block cell's distinctive `stack(dir: ttb, ...)`.)
    assert 'stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Title")' not in text
    assert 'stack(dir: ttb, spacing: 1mm, text(size: 8pt, "Customer")' not in text


def test_row_strips_sit_in_the_true_left_and_right_margins():
    """The row (lettered) strips flank the frame border, not overlap its rightmost column.

    Left strip: `dx: 0mm` to the frame border's left edge (`content_x_mm`). Right strip must
    mirror it on the other side: `dx:` the frame border's *right* edge
    (`width_mm - content_x_mm`), not `width_mm - content_x_mm - <strip depth>`, which would
    place it one strip-depth short -- inside the frame border and the content box's own
    rightmost column, drawing grid letters over live content instead of in the margin.
    """
    house = default_sheet_format()
    right_x = house.width_mm - house.content_x_mm  # 410 on the house sheet
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    text = source(m, doc.id, {})
    assert f"#place(top+left, dx: {right_x}mm, dy: {house.content_y_mm}mm, " in text


def test_grid_columns_come_from_the_sheet_format_not_a_constant():
    """Acceptance 2: the grid's column count and content width are `sheet`'s, not hard-coded.

    `content_width_mm=380` on a 420 mm sheet with `content_x_mm=10` is deliberately *not*
    `width_mm - 2*content_x_mm` (400): a grid strip that read the frame border's own width
    instead of `sheet.content_width_mm` would still pass a sheet where the two coincide, so
    the two field values must differ here for the assertion to actually pin the field.
    """
    c1 = location("C1", "Demo cabinet")
    key = ("sheet_format", "wide8")
    fmt = SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="wide8",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=380,
        content_height_mm=257,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
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
    m = model(c1, fmt, ds, page, doc)
    svgs = {render_id(page.id): _SVG}
    text = source(m, doc.id, svgs)
    for label in ("1", "2", "3", "4", "5", "6", "7", "8"):
        assert f'text(size: 8pt, "{label}")' in text
    assert 'text(size: 8pt, "9")' not in text
    # The grid strip's own width is `content_width_mm` (380), not the frame border's
    # `width_mm - 2*content_x_mm` (400, which the border rect legitimately also emits).
    assert "block(width: 380mm, height: 10mm" in text


def test_grid_columns_with_six_columns_differ_from_eight():
    """The sibling of the can-fail probe: a `frame_columns=6` sheet never shows a `"7"` or `"8"`."""
    c1 = location("C1", "Demo cabinet")
    fmt = sheet_format("narrow", width_mm=420, height_mm=297, frame_columns=6)
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
    m = model(c1, fmt, ds, page, doc)
    svgs = {render_id(page.id): _SVG}
    text = source(m, doc.id, svgs)
    for label in ("1", "2", "3", "4", "5", "6"):
        assert f'text(size: 8pt, "{label}")' in text
    assert 'text(size: 8pt, "7")' not in text
    assert 'text(size: 8pt, "8")' not in text


def test_no_header_or_footer_argument_on_any_page_kind():
    """Acceptance 4: the header/footer P4 gave every page are gone (page-frame R4)."""
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
    text = source(m, doc.id, {})
    assert "header:" not in text
    assert "footer:" not in text
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
    """CT2: a cable run's page keeps the same 5 mm content-box margin (R3, R4;
    decision pdf-0009, RULING W3's clearance) the WireViz image used, even with no image left
    to protect the frame border from -- the house text-page padding, not a bare content-box
    fit.
    """
    m, doc, cable = _harness_with_one_cable()
    text = source(m, doc.id, {cable_block_key(None, cable.id): "<svg>block</svg>"})
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
    (found,) = harness_cables_for(m, documents(m)[doc.id], (K.HARNESS_DRAWING,))
    assert found.cable == cable.id
    assert "<svg>block</svg>" in text
    assert "#strong(text(" not in text


# -- direct, lower-level calls into the width/wrap/fit helpers (mutmut kill order) ----------


def test_bold_text_width_differs_from_regular():
    """`bold=True` picks `_BOLD_WIDTHS_EM` over `_REGULAR_WIDTHS_EM`, a genuinely different
    table (not a no-op): the same text set bold measures a different width.
    """
    text = "A somewhat long value"
    regular = text_width_mm(text, size_pt=10.0, bold=False)
    bold = text_width_mm(text, size_pt=10.0, bold=True)
    assert regular != bold


def test_cut_to_width_bold_needs_more_cutting_than_regular():
    """`bold` reaches every width computation inside `cut_to_width` (`fits`, the ellipsis's own
    width, and the per-character loop): at a width between the two tables' whole-text widths,
    the regular text fits untouched while the bold text must be cut.
    """
    text = "A somewhat long value"
    size_pt = 10.0
    regular_width = text_width_mm(text, size_pt=size_pt, bold=False)
    bold_width = text_width_mm(text, size_pt=size_pt, bold=True)
    width_mm = (regular_width + bold_width) / 2
    assert fits(text, size_pt=size_pt, bold=False, width_mm=width_mm)
    assert not fits(text, size_pt=size_pt, bold=True, width_mm=width_mm)
    assert cut_to_width(text, size_pt=size_pt, bold=False, width_mm=width_mm) == (text, False)
    bold_cut, bold_was_cut = cut_to_width(text, size_pt=size_pt, bold=True, width_mm=width_mm)
    assert bold_was_cut is True
    assert bold_cut != text
    assert bold_cut.endswith("…")


def test_cut_to_width_default_bold_is_false():
    """`cut_to_width`'s own default (`bold=False`) is exercised by omitting the keyword: at a
    width where only the bold rendering needs cutting, the default call must not cut.
    """
    text = "A somewhat long value"
    size_pt = 10.0
    regular_width = text_width_mm(text, size_pt=size_pt, bold=False)
    bold_width = text_width_mm(text, size_pt=size_pt, bold=True)
    width_mm = (regular_width + bold_width) / 2
    assert cut_to_width(text, size_pt=size_pt, width_mm=width_mm) == (text, False)


def test_cut_to_width_loop_uses_bold_metrics_not_regular():
    """The per-character loop's own `text_width_mm(candidate, ..., bold=bold)` call must use
    the bold table too, not just the initial `fits` check: at a width between the bold and
    regular cumulative widths of a bold-heavy repeated character, cutting bold text stops
    three characters earlier than cutting the same text with the loop's bold flag dropped.
    """
    size_pt = 10.0
    text = "m" * 20  # bold 'm' (0.833 em) is noticeably wider than regular 'm' (0.7778 em)
    ellipsis_width = text_width_mm("…", size_pt=size_pt, bold=True)
    budget = 28.0  # between 9 bold m's (26.45) and 10 bold m's (29.39) cumulative width
    width_mm = budget + ellipsis_width
    assert not fits(text, size_pt=size_pt, bold=True, width_mm=width_mm)
    kept, was_cut = cut_to_width(text, size_pt=size_pt, bold=True, width_mm=width_mm)
    assert was_cut is True
    assert kept == "m" * 9 + "…"


def test_cut_to_width_stops_strictly_before_the_width_not_at_it():
    """The loop's own `> budget` (not `>=`) keeps a character whose running width lands
    exactly on the budget: at that exact boundary, "AB" is kept whole and only the following
    character is cut, proving the comparison is strict.
    """
    size_pt = 10.0
    text = "ABCDEFGH"
    ellipsis_width = text_width_mm("…", size_pt=size_pt, bold=False)
    candidate_width = text_width_mm("AB", size_pt=size_pt, bold=False)
    width_mm = ellipsis_width + candidate_width
    assert not fits(text, size_pt=size_pt, width_mm=width_mm)
    assert cut_to_width(text, size_pt=size_pt, width_mm=width_mm) == ("AB…", True)


def test_wrap_lines_of_empty_text_is_one_empty_line():
    """The `not words` guard: no words at all still returns one (empty) line, never none."""
    assert _wrap_lines("", size_pt=10, width_mm=100) == [""]


def test_wrap_lines_of_one_word_returns_it_unwrapped():
    """A single word never enters the `for` loop body at all -- the post-loop
    `lines.append(current)` is what actually returns it.
    """
    assert _wrap_lines("OneWord", size_pt=10, width_mm=100) == ["OneWord"]


def test_wrap_lines_splits_two_words_that_do_not_fit_together():
    """The loop's `else` branch: when the combined candidate is too wide, the first word
    ends its own line and the second starts a new one -- neither dropped nor merged.
    """
    size_pt = 10
    word1, word2 = "wordone", "wordtwo"
    combined_width = text_width_mm(f"{word1} {word2}", size_pt=size_pt)
    single_widths = (text_width_mm(word1, size_pt=size_pt), text_width_mm(word2, size_pt=size_pt))
    width_mm = (max(single_widths) + combined_width) / 2
    assert width_mm > max(single_widths)  # each word alone fits
    assert width_mm < combined_width  # together they do not
    assert _wrap_lines(f"{word1} {word2}", size_pt=size_pt, width_mm=width_mm) == [word1, word2]


def test_wrap_lines_keeps_two_words_together_at_the_exact_boundary():
    """The loop's own `<= width_mm` (not `<`) keeps two words on one line when their combined
    width lands exactly on `width_mm`, proving the comparison is inclusive, not strict.
    """
    size_pt = 10
    text = "wordone wordtwo"
    width_mm = text_width_mm(text, size_pt=size_pt)
    assert _wrap_lines(text, size_pt=size_pt, width_mm=width_mm) == [text]


def test_notice_fits_empty_text_is_always_true():
    """The `not text` early return: even a width and height too small for any real text
    still reports a fit, because there is no text to wrap.
    """
    assert notice_fits("", width_mm=1, height_mm=1) is True
