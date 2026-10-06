"""R9 (docs/archive/specs/2026-09-22-page-frame.md, amendment) and R11 on the COMPILED page:
acceptance items 9 and R11's 2.

Items 1-6 read the Typst source string and the extracted text; a grid label cut at the paper
edge, or a title-block value crossed by its own cell's auto-shrunk rule, are both still
*present* text there, so those checks passed on the defect (R9's "why the gate missed it").
This module compiles a real document with the pinned `typst` package and checks where the ink
actually lands on the page, against `SheetFormat`'s own geometry (R2, R11.1, R11.2) -- a check
that cannot be fooled by text that is present but clipped.

R11.1 halves the house margin from 10mm to 5mm: the numbered/lettered strip's own depth is
`sheet.content_y_mm` / `sheet.content_x_mm` (the true margin), not a fixed constant, so this
module reads it from `SHEET` too, rather than hard-coding the old 10mm. R11.2 replaces the old
two independently-weighted title-block rows with one grid sharing a column table (`title_columns`
duplicated here, not imported, so a regression in `_frame.py`'s own arithmetic cannot also
silently pass its check).

Route: PNG, decoded with stdlib `zlib`/`struct` (`_png.py`), not the SVG route
`test_compile.py` uses for "did this compile to something visible" (`<use>` glyph counts). The
SVG route would need a glyph-id-to-character mapping to know *which* label is *which* digit or
letter; the PNG route needs none of that, because `_frame.py` draws raster-testable rectangles
by construction -- every check here is "is there ink inside this cell, and only the rules
`SheetFormat` predicts", never "which character is this". `pdf-0004` records this choice.

Fixture: the pdf package's own `_build` model, not the full demo cabinet -- one page of each
kind R9 touches: COVER (no sheet value), a SCHEMATIC page (a sheet value, the SVG placed over
the background), and BOM (a list page, no sheet value). The grid is identical on every page
kind (R2, owner ruling), and the title block's `Sheet` cell is the one field that differs by
page kind (spec R3), so checking all three is not redundant with checking one.
"""

from __future__ import annotations

import pytest
import typst
from _build import document, drawing_set, item, layout_page, location, model, part, place, project
from _png import Box, Raster, decode_png, horizontal_rules, ink_bbox, vertical_rules
from fransys_pdf import source

from fransys_model.kernel.ids import render_id
from fransys_model.layout import default_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
PPI = 72.0
SHEET = default_sheet_format()
TOP_BOTTOM_STRIP_MM = float(SHEET.content_y_mm)  # the numbered strip's depth: the true margin
LEFT_RIGHT_STRIP_MM = float(SHEET.content_x_mm)  # the lettered strip's depth: the true margin
EDGE_CLEARANCE_MM = 1.0  # required clearance from the true paper edge (R9: "inside the paper")
TICK_CLEARANCE_MM = 1.0  # inset from an inter-cell tick boundary before scanning for a label
BAND_TOP = float(SHEET.content_y_mm + SHEET.content_height_mm)  # 267: content box bottom
ROW_HEIGHT = (SHEET.height_mm - SHEET.content_y_mm - BAND_TOP) / 2  # 10
FRAME_BOTTOM = float(SHEET.height_mm - SHEET.content_y_mm)  # 287: band_top + 2*row_height
# R11.2's house column table (c1-c7, then the square logo column), duplicated from
# `_frame._TITLE_COL_WEIGHTS`/`title_columns`, not imported (see module docstring).
_TITLE_COL_WEIGHTS = (60, 60, 100, 55, 35, 35, 45)
# No visible mark: this module checks the frame/grid/title-block ink, never the drawing's own
# content, and an SVG with a stroke could otherwise land inside a margin strip or the band and
# be mistaken for part of the frame by the ink scans below.
_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="380mm" height="240mm"></svg>'


def _title_columns_mm() -> tuple[float, float, float, float, float, float, float, float]:
    """`(c1, c2, c3, c4, c5, c6, c7, logo)` widths (mm), independently of `_frame.title_columns`."""
    frame_width = SHEET.width_mm - 2 * SHEET.content_x_mm
    logo = 2 * ROW_HEIGHT  # the band height: the logo column is exactly as wide as the band is tall
    remaining = frame_width - logo
    total = sum(_TITLE_COL_WEIGHTS)
    c1, c2, c3, c4, c5, c6, c7 = (remaining * w / total for w in _TITLE_COL_WEIGHTS)  # ty: ignore[division-by-zero] total is 390; ty types a tuple sum as int | 0
    return (c1, c2, c3, c4, c5, c6, c7, logo)


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


def _mm(px: float) -> float:
    return px * 25.4 / PPI


def _column_bounds() -> list[tuple[float, float]]:
    """`(left, right)` mm bounds of the 8 numbered cells, top or bottom strip (R2)."""
    n = SHEET.frame_columns
    step = SHEET.content_width_mm / n
    x0 = SHEET.content_x_mm
    return [(x0 + i * step, x0 + (i + 1) * step) for i in range(n)]


def _row_bounds() -> list[tuple[float, float]]:
    """`(top, bottom)` mm bounds of the 6 lettered cells, left or right strip (R2)."""
    n = SHEET.frame_rows
    step = SHEET.content_height_mm / n
    y0 = SHEET.content_y_mm
    return [(y0 + i * step, y0 + (i + 1) * step) for i in range(n)]


def _grid_cells() -> list[tuple[str, float, float, float, float]]:
    """The 28 grid-label cells: `(side, x0mm, x1mm, y0mm, y1mm)`."""
    cells: list[tuple[str, float, float, float, float]] = []
    for x0, x1 in _column_bounds():
        cells.append(("top", x0, x1, 0.0, TOP_BOTTOM_STRIP_MM))
        cells.append(("bottom", x0, x1, SHEET.height_mm - TOP_BOTTOM_STRIP_MM, SHEET.height_mm))
    for y0, y1 in _row_bounds():
        cells.append(("left", 0.0, LEFT_RIGHT_STRIP_MM, y0, y1))
        cells.append(("right", SHEET.width_mm - LEFT_RIGHT_STRIP_MM, SHEET.width_mm, y0, y1))
    return cells


def _title_cells() -> dict[str, tuple[float, float, float, float]]:
    """The 12 title-block cells, by field name: `(x0mm, x1mm, y0mm, y1mm)` (R3, R11.2).

    One shared column grid (`_title_columns_mm`): `title` spans c1-c3 in row 1; `notice` and
    `logo` each span both rows in their own column (R11.3, R11.4); the other nine are one row
    each. Row 2's boundaries are exactly row 1's own (R11.2's "no boundary of one row falls
    inside a cell of the other unless that cell spans it"), which is what makes this a dict of
    named cells sharing one coordinate space meaningful to assert on, rather than two
    independently-bounded rows.
    """
    c1, c2, c3, c4, c5, c6, c7, logo = _title_columns_mm()
    x0 = SHEET.content_x_mm
    row1_y = (BAND_TOP, BAND_TOP + ROW_HEIGHT)
    row2_y = (BAND_TOP + ROW_HEIGHT, FRAME_BOTTOM)
    both_y = (BAND_TOP, FRAME_BOTTOM)
    # Cumulative column boundaries, left to right: x0, then one column's width at a time --
    # the same running total both rows share (R11.2), so row 2's boundaries below are these
    # same six numbers, never independently computed.
    b1 = x0 + c1
    b2 = b1 + c2
    b3 = b2 + c3
    b4 = b3 + c4
    b5 = b4 + c5
    b6 = b5 + c6
    b7 = b6 + c7
    b8 = b7 + logo
    assert abs(b8 - (SHEET.width_mm - x0)) < 1e-6, (b8, SHEET.width_mm - x0)
    return {
        "title": (x0, b3, *row1_y),
        "number": (b3, b4, *row1_y),
        "revision": (b4, b5, *row1_y),
        "revision_date": (b5, b6, *row1_y),
        "notice": (b6, b7, *both_y),
        "logo": (b7, b8, *both_y),
        "customer": (x0, b1, *row2_y),
        "author": (b1, b2, *row2_y),
        "page_title": (b2, b3, *row2_y),
        "scope": (b3, b4, *row2_y),
        "sheet_counter": (b4, b5, *row2_y),
        "page": (b5, b6, *row2_y),
    }


def _detect_band_rules(raster: Raster, *, x0mm: float, x1mm: float) -> list[float]:
    """Horizontal rule centres (mm) inside `[x0mm, x1mm)` of the title-block band, R2's
    frame-border rule at `FRAME_BOTTOM` excluded -- that rule is R2's, not one of R3's
    title-block rows.

    `x1mm` is a parameter, not always the full frame width: R11.2's row divider only spans
    columns c1-c6 (`notice`/`logo` are one cell for both rows, so no divider crosses them),
    so a caller checking that divider narrows the scan to where it actually is -- a full-width
    scan would find it at under 90% coverage and miss it (`horizontal_rules`' own threshold).

    `y1mm` stops at `FRAME_BOTTOM + 0.75`, not further: the bottom number strip starts right
    there, and its own margin-strip grid (checked separately, `test_grid_labels_...`) draws a
    rule of its own a little further down -- a wider window pulled that rule in here too, one
    title-block-band rule too many.
    """
    y0mm, y1mm = BAND_TOP - 2.0, FRAME_BOTTOM + 0.75
    box = Box(x0=_px(x0mm), x1=_px(x1mm), y0=_px(y0mm), y1=_px(y1mm))
    rules_mm = [_mm(p) for p in horizontal_rules(raster, box)]
    return [r for r in rules_mm if abs(r - FRAME_BOTTOM) > 0.75]


def _document() -> tuple[str, object]:
    """Cover, one SCHEMATIC page and a BOM list page, on the house sheet (spec R2, R3, R9)."""
    c1 = location("C1", "Demo cabinet")
    proj = project()
    ds = drawing_set("ds1", location=c1)
    page = layout_page("p1", drawing_set=ds, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover\n\nSome cover text.",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST),
    )
    demo_part = part(
        "relay", description="Invented relay"
    )  # a BOM row, else no BOM page (pdf-0019)
    demo_item = item("k1", description="Invented relay", part=demo_part.id)
    m = model(
        c1, proj, ds, page, doc, demo_part, demo_item, place("p1", item=demo_item.id, node=c1.id)
    )
    svgs = {render_id(page.id): _SVG}
    return source(m, doc.id, svgs), page


@pytest.fixture(scope="module")
def pages() -> list[Raster]:
    """The three compiled pages -- COVER, SCHEMATIC, BOM -- decoded once for this module."""
    text, _page = _document()
    assert text.count("#pagebreak()") == 2  # COVER|SCHEMATIC, SCHEMATIC|BOM
    # `typst.compile`'s free-function overloads narrow to `-> bytes` when `output` is omitted,
    # but it returns one `bytes` per page at runtime for a multi-page document (confirmed
    # against this project's own multi-page fixtures); `Compiler.compile` is typed
    # `Optional[Union[bytes, List[bytes]]]` without that mismatch, so `ty` sees the real shape.
    pngs = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=PPI)
    assert isinstance(pngs, list)
    rasters = [decode_png(p) for p in pngs]
    assert len(rasters) == 3
    return rasters


def _grid_label_scan_box(side: str, x0mm: float, x1mm: float, y0mm: float, y1mm: float) -> Box:
    """The pixel box to scan for one grid label's own ink -- the cell minus two things that
    are not the label: the interior tick at the along-strip axis's cell boundaries
    (`TICK_CLEARANCE_MM`), and R2's frame border, which sits exactly on the strip's
    border-facing edge and, being a full-width/height rule, would otherwise stretch the
    scanned box's own ink to that edge on every cell -- a first version of this test measured
    the border instead of the label this way, its bbox equal to the scan box on both axes.
    The paper-facing edge is left unclipped, so a label sitting at the paper edge (R9's
    defect) is still ink inside this box, not excluded from it.
    """
    if side in ("top", "bottom"):
        sx0, sx1 = x0mm + TICK_CLEARANCE_MM, x1mm - TICK_CLEARANCE_MM
        depth = TOP_BOTTOM_STRIP_MM
        sy0, sy1 = (0.0, depth - 1.0) if side == "top" else (y1mm - depth + 1.0, y1mm)
    else:
        sy0, sy1 = y0mm + TICK_CLEARANCE_MM, y1mm - TICK_CLEARANCE_MM
        depth = LEFT_RIGHT_STRIP_MM
        sx0, sx1 = (0.0, depth - 1.0) if side == "left" else (x1mm - depth + 1.0, x1mm)
    return Box(x0=_px(sx0), x1=_px(sx1), y0=_px(sy0), y1=_px(sy1))


def test_grid_labels_present_centred_and_clear_of_the_paper_edge(pages: list[Raster]) -> None:
    """R9: every grid label's ink lies inside its margin cell and inside the paper, centred."""
    cells = _grid_cells()
    assert len(cells) == 2 * SHEET.frame_columns + 2 * SHEET.frame_rows == 28

    for raster in pages:
        boxes = [
            _grid_label_scan_box(side, x0mm, x1mm, y0mm, y1mm)
            for side, x0mm, x1mm, y0mm, y1mm in cells
        ]
        bboxes = [ink_bbox(raster, box) for box in boxes]

        # non-zero count, before any position check (acceptance 9)
        missing = [c for c, b in zip(cells, bboxes, strict=True) if b is None]
        assert not missing, f"{len(missing)} of 28 grid label cells have no ink: {missing}"

        for (side, x0mm, x1mm, y0mm, y1mm), box, bbox in zip(cells, boxes, bboxes, strict=True):
            assert bbox is not None  # `missing` above already proved every cell has ink
            bx0, by0, bx1, by1 = bbox
            # the label's own ink must not fill the scan box: touching an edge means either
            # the label overflows what R9 calls its cell, or this box still lets contamination
            # (a rule, a neighbouring cell) in -- either way, not just the label's own glyph
            assert bx0 > box.x0, (side, x0mm, x1mm, y0mm, y1mm, bbox, box)
            assert bx1 < box.x1, (side, x0mm, x1mm, y0mm, y1mm, bbox, box)
            assert by0 > box.y0, (side, x0mm, x1mm, y0mm, y1mm, bbox, box)
            assert by1 < box.y1, (side, x0mm, x1mm, y0mm, y1mm, bbox, box)
            cx_mm, cy_mm = _mm((bx0 + bx1) / 2), _mm((by0 + by1) / 2)
            want_cx, want_cy = (x0mm + x1mm) / 2, (y0mm + y1mm) / 2
            assert abs(cx_mm - want_cx) <= 1.0, (side, x0mm, x1mm, y0mm, y1mm, bbox, cx_mm, cy_mm)
            assert abs(cy_mm - want_cy) <= 1.0, (side, x0mm, x1mm, y0mm, y1mm, bbox, cx_mm, cy_mm)
            if side == "top":
                assert _mm(by0) >= EDGE_CLEARANCE_MM, ("top label at the paper edge", bbox)
            elif side == "bottom":
                assert SHEET.height_mm - _mm(by1) >= EDGE_CLEARANCE_MM, (
                    "bottom label at the paper edge",
                    bbox,
                )
            elif side == "left":
                assert _mm(bx0) >= EDGE_CLEARANCE_MM, ("left label at the paper edge", bbox)
            else:
                assert SHEET.width_mm - _mm(bx1) >= EDGE_CLEARANCE_MM, (
                    "right label at the paper edge",
                    bbox,
                )


def test_title_block_band_has_exactly_two_row_rules(pages: list[Raster]) -> None:
    """Acceptance 9: 'the band holds exactly two row rules, not four.'

    Scans columns c1-c6 (R11.2: the only span the row divider crosses -- `notice`/`logo` are
    one cell for both rows) for horizontal rules, drops the one at the frame border's own
    bottom edge (R2's border, not a title-block rule), and asserts the rest are exactly the
    band's own top edge and the divider between its two rows -- not the four an auto-shrunk
    row leaves behind (its own top and its own too-early bottom, twice).
    """
    cells = _title_cells()
    x0mm = SHEET.content_x_mm
    x1mm = cells["sheet_counter"][1]  # the right edge of c6, where the row divider ends
    for raster in pages:
        band_rules = _detect_band_rules(raster, x0mm=x0mm, x1mm=x1mm)
        assert band_rules, "no title-block row rules found in the band at all"
        assert len(band_rules) == 2, (
            f"expected exactly two row rules in the band, found {len(band_rules)}: {band_rules}"
        )
        want = [BAND_TOP, BAND_TOP + ROW_HEIGHT]
        for got, expected in zip(sorted(band_rules), want, strict=True):
            assert abs(got - expected) <= 0.5, (sorted(band_rules), want)


def test_title_block_cells_have_ink_clear_of_any_interior_rule(pages: list[Raster]) -> None:
    """R9, R11.2: every title-block label and value lies inside its cell, clear of every rule.

    At `faef7d6` the auto-shrunk row leaves a rule inside each cell's own 10 mm height,
    crossing the label/value stack instead of bounding the row top and bottom. `notice` (R11.4)
    carries no label/value stack of its own kind -- its wrapped 6 pt text is checked for
    overflow separately (`test_title_block.py`) -- so it is skipped here, along with `page`
    (its value is a dynamic page counter, still checked for presence by the sheet-counter
    test below); the other 9 named cells (`logo` is also excluded, since the demo
    fixture below gives no logo, so it is expected to have no ink and is skipped too) are
    checked the same way R9 always has.
    """
    cells = _title_cells()
    checked = {
        name: bounds for name, bounds in cells.items() if name not in ("notice", "logo", "page")
    }
    assert len(checked) == 9, checked

    for raster in pages:
        boxes = {
            name: Box(
                x0=_px(x0mm + 1.0), x1=_px(x1mm - 1.0), y0=_px(y0mm + 0.75), y1=_px(y1mm - 0.75)
            )
            for name, (x0mm, x1mm, y0mm, y1mm) in checked.items()
        }
        bboxes = {name: ink_bbox(raster, box) for name, box in boxes.items()}
        missing = [name for name, b in bboxes.items() if b is None]
        assert not missing, (
            f"{len(missing)} of {len(checked)} title-block cells have no ink: {missing}"
        )

        for name, box in boxes.items():
            bbox = bboxes[name]
            assert bbox is not None  # `missing` above already proved every cell has ink
            bx0, by0, bx1, by1 = bbox
            # ink touching this inset box's own edge means the label/value overflows the
            # cell (or a rule reaches in) -- inset alone would silently clip that overflow
            # out of the scan and let it pass, so overflow is checked, not just presence.
            assert bx0 > box.x0, (name, bbox, box)
            assert bx1 < box.x1, (name, bbox, box)
            assert by0 > box.y0, (name, bbox, box)
            assert by1 < box.y1, (name, bbox, box)

        for name, (x0mm, x1mm, y0mm, y1mm) in checked.items():
            # Local rule detection, this cell's own x-range: a global scan over the whole band
            # would (correctly) find no rule crossing `notice`/`logo` at all, since R11.2's
            # divider does not reach their column -- but would also (wrongly) flag every other
            # cell whose y-range happens to contain that divider's y-position, even though the
            # divider does not cross *their* x-range either. Scanning `[x0mm, x1mm)` for this
            # cell alone is the same distinction `_detect_band_rules` draws by column.
            local_rules = _detect_band_rules(raster, x0mm=x0mm, x1mm=x1mm)
            interior_top, interior_bottom = y0mm + 0.5, y1mm - 0.5
            crossing = [r for r in local_rules if interior_top < r < interior_bottom]
            assert not crossing, (
                f"cell {name!r} (y=[{y0mm},{y1mm}]): a rule crosses it at {crossing}"
            )


def test_no_strip_rectangle_around_the_grid_labels(pages: list[Raster]) -> None:
    """R9: 'the separate thin strip rectangles ... are not in R2; they go.'

    Absence: no full-span rule sits at the true paper edge (the strip's own outer perimeter,
    R9's defect). Presence: the ticks R2 does ask for, one per interior cell boundary, are
    still there -- the count is checked before the shape, same as the label cells above.
    """
    content_x0, content_x1 = _px(SHEET.content_x_mm), _px(SHEET.width_mm - SHEET.content_x_mm)
    content_y0, content_y1 = _px(SHEET.content_y_mm), _px(SHEET.height_mm - SHEET.content_y_mm)
    for raster in pages:
        top_edge = horizontal_rules(raster, Box(x0=content_x0, x1=content_x1, y0=0, y1=_px(1.0)))
        assert not top_edge, f"a full-width rule sits at the paper's top edge: {top_edge}"
        bottom_edge = horizontal_rules(
            raster,
            Box(
                x0=content_x0, x1=content_x1, y0=_px(SHEET.height_mm - 1.0), y1=_px(SHEET.height_mm)
            ),
        )
        assert not bottom_edge, f"a full-width rule sits at the paper's bottom edge: {bottom_edge}"
        left_edge = vertical_rules(raster, Box(x0=0, x1=_px(1.0), y0=content_y0, y1=content_y1))
        assert not left_edge, f"a full-height rule sits at the paper's left edge: {left_edge}"
        right_edge = vertical_rules(
            raster,
            Box(x0=_px(SHEET.width_mm - 1.0), x1=_px(SHEET.width_mm), y0=content_y0, y1=content_y1),
        )
        assert not right_edge, f"a full-height rule sits at the paper's right edge: {right_edge}"

        top_ticks = vertical_rules(
            raster, Box(x0=content_x0, x1=content_x1, y0=0, y1=_px(TOP_BOTTOM_STRIP_MM))
        )
        assert len(top_ticks) == SHEET.frame_columns - 1, top_ticks
        bottom_ticks = vertical_rules(
            raster,
            Box(
                x0=content_x0,
                x1=content_x1,
                y0=_px(SHEET.height_mm - TOP_BOTTOM_STRIP_MM),
                y1=_px(SHEET.height_mm),
            ),
        )
        assert len(bottom_ticks) == SHEET.frame_columns - 1, bottom_ticks
        left_ticks = horizontal_rules(
            raster, Box(x0=0, x1=_px(LEFT_RIGHT_STRIP_MM), y0=content_y0, y1=content_y1)
        )
        assert len(left_ticks) == SHEET.frame_rows - 1, left_ticks
        right_ticks = horizontal_rules(
            raster,
            Box(
                x0=_px(SHEET.width_mm - LEFT_RIGHT_STRIP_MM),
                x1=_px(SHEET.width_mm),
                y0=content_y0,
                y1=content_y1,
            ),
        )
        assert len(right_ticks) == SHEET.frame_rows - 1, right_ticks


def test_sheet_counter_cell_has_a_value_only_on_the_schematic_page(pages: list[Raster]) -> None:
    """R3's two counters: the sheet cell (`sheet_counter`, row 2) is empty on every page that
    is not a `SCHEMATIC` drawing page (`pdf-0003`'s judgement call) -- proof the compiled-page
    checks above look at real, page-kind-specific content, not one fixed fixture repeated.
    """
    sheet_x0, sheet_x1, sheet_y0, sheet_y1 = _title_cells()["sheet_counter"]
    counts = []
    for raster in pages:
        dark = sum(
            1
            for y in range(_px(sheet_y0 + 0.75), _px(sheet_y1 - 0.75))
            for x in range(_px(sheet_x0 + 1.0), _px(sheet_x1 - 1.0))
            if raster.is_dark(x, y, threshold=200)
        )
        counts.append(dark)
    cover_dark, schematic_dark, bom_dark = counts
    # cover and BOM show only the "Sheet" label; the schematic page also shows "1 / 1"
    assert schematic_dark > cover_dark * 1.5, counts
    assert schematic_dark > bom_dark * 1.5, counts
