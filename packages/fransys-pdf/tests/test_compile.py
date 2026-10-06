"""Compile `_markdown.to_typst` output for real, with the dev-only `typst` package.

A golden string proves `source` is stable; it does not prove Typst can parse it. `typst` is
never imported outside a test module: `fransys_pdf` stays free of it (spec P1 - the
facade's dependency, pinned for Stage 2), and `tests/test_boundaries.py` would fail a `src/`
import of it.
"""

import typst
from _build import (
    bridged_terminal,
    conductor,
    document,
    item,
    location,
    model,
    part,
    pin,
    place,
    project,
)
from _png import Box, decode_png, horizontal_rules, ink_bbox, vertical_rules
from fransys_pdf import source
from fransys_pdf._lists import _humanise, _table, _terminal_table, bom_page
from fransys_pdf._markdown import parse, to_typst

from fransys_model.derive import BOM_COLUMNS, CABLE_LIST_COLUMNS, terminal_rows
from fransys_model.vocab import ConductorKind, DocumentPreset, PageKind, documents

_PAGE = "#set page(width: 210mm, height: 297mm, margin: 15mm)\n"
_9PT = '#set text(font: "Liberation Serif", size: 9pt)\n'


def _glyph_count(body: str) -> int:
    """How many glyphs Typst places for `body`: a real proxy for "this text is visible"."""
    svg = typst.compile((_PAGE + body).encode("utf-8"), format="svg")
    return svg.decode("utf-8").count("<use ")


def test_every_construct_compiles():
    text = (
        "# Heading one\n\n"
        "## Heading two\n\n"
        "### Heading three\n\n"
        "A paragraph with **bold** and *italic* text.\n\n"
        "- one\n- two\n\n"
        "1. first\n2. second"
    )
    body = to_typst(parse(text))
    assert _glyph_count(body) > 0


def test_an_unsupported_line_compiles_as_a_literal_paragraph():
    body = to_typst(parse("`inline code`"))
    assert _glyph_count(body) > 0


def test_injected_typst_code_is_printed_not_executed():
    """Can-fail twin: source() escapes every run; an emitter that instead interpolated the
    text into Typst markup would let `#let` execute silently, producing no visible glyphs.
    """
    escaped_body = to_typst(parse("#let x = 1"))
    escaped_glyphs = _glyph_count(escaped_body)
    assert escaped_glyphs > 0

    broken_body = "#par[#let x = 1]"
    broken_glyphs = _glyph_count(broken_body)
    assert broken_glyphs == 0

    assert escaped_glyphs > broken_glyphs


def test_injected_emphasis_marker_is_printed_not_applied():
    """Can-fail twin for the spec's other named case: an unclosed `*` stays a literal glyph,
    never opens `emph`, so it renders alongside the text rather than being swallowed.
    """
    escaped_body = to_typst(parse("*not emphasis"))
    escaped_glyphs = _glyph_count(escaped_body)

    without_star_body = to_typst(parse("not emphasis"))
    without_star_glyphs = _glyph_count(without_star_body)

    # The `*` is one more visible glyph than the same text without it -- proof it was kept,
    # not consumed as a markup delimiter (which would leave the two byte counts equal).
    assert escaped_glyphs == without_star_glyphs + 1


def test_a_full_cover_and_notes_document_compiles():
    """`source`'s own page setup (paper, margins, header, footer, type sizes), not just a
    markdown fragment, compiles to a real PDF.
    """
    c1 = location("C1", "Demo cabinet")
    p = project()
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=c1,
        cover="# Cover\n\nCover text with **bold** and *italic*.\n\n- a\n- b",
        notes="Notes text.",
        remove=(PageKind.CONTENTS, PageKind.HARNESS_DRAWING, PageKind.BOM),
    )
    m = model(c1, p, doc)
    pdf_bytes = typst.compile(source(m, doc.id, {}).encode("utf-8"))
    assert pdf_bytes.startswith(b"%PDF-")


def test_a_terminal_list_with_a_bridge_column_compiles_to_one_page_per_strip():
    """Compile guard (spec T2, pdf-0007): a Bridge cell's percentage-based marks resolve
    against its own row only because the cell is `breakable: false`; a breakable cell in an
    `auto` row resolves them against the whole page instead, which made this same fixture
    balloon to 7 physical pages instead of 2 in an earlier draft -- caught only by actually
    compiling, not by any string check on the Typst source.
    """
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(PageKind.SCHEMATIC, PageKind.PLC_LIST, PageKind.BOM),
    )
    strip = item("x1", description="Strip one")
    t1, t1f, t1fn, t1p = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    t2, t2f, t2fn, t2p = bridged_terminal("t2", strip=strip.id, group="T", index=2)
    t3, t3f, t3fn, t3p = bridged_terminal("t3", strip=strip.id, group="T", index=3)
    jumper = conductor("j1", a=t1p.id, b=t3p.id, kind=ConductorKind.JUMPER)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(
        c1, doc, strip, t1, t1f, t1fn, t1p, t2, t2f, t2fn, t2p, t3, t3f, t3fn, t3p, jumper, p1
    )
    pages = typst.compile(source(m, doc.id, {}).encode("utf-8"), format="svg")
    assert len(pages) == 2  # COVER, TERMINAL_LIST -- no runaway pagination


_PPI = 150.0


def _px(mm: float) -> int:
    return round(mm * _PPI / 25.4)


def test_a_wrapped_non_member_row_still_draws_a_continuous_bridge_line():
    """Ruling 2 (spec T2 amendment, pdf-0007): rows keep their automatic height; a non-member
    row inside a group's span draws the line at its own full, real height -- however many
    lines its own wrapped text takes -- so the group's line still reads as one continuous
    line through it. Asserted on the compiled page's ink, not the Typst source: a string
    check cannot tell a three-line row's segment from a one-line row's, which is exactly how
    the first build's page-breaking defect passed every text-only test (`test_lists.py`'s
    own `_bridge_geometry` tests stayed green throughout).

    Can-fail (quoted in the work order's hand-back): `_bridge_geometry`'s per-row loop
    skipping a non-member row (`if groups[index] != group: continue`, dropping its full-height
    segment) turns 0 of ~190 scanned pixel rows blank in the tall row's span into ~150 -- the
    line visibly breaks. Undone with Edit.
    """
    strip = item("x1", description="Strip one")
    t1, t1f, t1fn, t1p = bridged_terminal("t1", strip=strip.id, group="T", index=1)
    t2, t2f, t2fn, t2p = bridged_terminal("t2", strip=strip.id, group="T", index=2)
    # Several wires on t2's internal port, so "Internal ends" wraps to several lines on a
    # narrow page: t2 is the non-member row whose real (tall) height must not break the line.
    far_records = []
    wires = []
    for i in range(6):
        far_item, far_fn, far_port = pin(f"far{i}", f"K{i}:A1")
        far_records += [far_item, far_fn, far_port]
        wires.append(conductor(f"w{i}", a=t2p.id, b=far_port.id))
    t3, t3f, t3fn, t3p = bridged_terminal("t3", strip=strip.id, group="T", index=3)
    jumper = conductor("j1", a=t1p.id, b=t3p.id, kind=ConductorKind.JUMPER)
    m = model(
        strip,
        t1,
        t1f,
        t1fn,
        t1p,
        t2,
        t2f,
        t2fn,
        t2p,
        *far_records,
        *wires,
        t3,
        t3f,
        t3fn,
        t3p,
        jumper,
    )
    rows = terminal_rows(m, strip.id)
    table_source = _terminal_table(m, rows)
    # A narrow page forces "Internal ends" to wrap; `_terminal_table`'s own table is compiled
    # standalone, not through `source()`'s wide house sheet, where nothing here would wrap.
    page = (
        "#set page(width: 80mm, height: 150mm, margin: 5mm)\n"
        '#set text(font: "Liberation Serif", size: 9pt)\n' + table_source
    )
    raw = typst.compile(page.encode("utf-8"), format="png", ppi=_PPI)
    raster = decode_png(raw[0] if isinstance(raw, list) else raw)

    full = Box(x0=0, x1=raster.width, y0=0, y1=raster.height)
    page_bbox = ink_bbox(raster, full, threshold=200)
    assert page_bbox is not None
    min_x, min_y, max_x, max_y = page_bbox
    table_box = Box(x0=min_x, x1=max_x + 1, y0=min_y, y1=max_y + 1)
    rules = horizontal_rules(raster, table_box, threshold=200, min_coverage=0.8)
    assert len(rules) == 5  # top, header/T:1, T:1/T:2, T:2/T:3, bottom
    _header_top, row1_top, row1_bottom, row2_bottom, _row3_bottom = rules

    # T:1's tick lives in the Bridge column, the table's own last 15mm; find its x there.
    bridge_x0 = max_x - _px(15)
    row1_box = Box(x0=bridge_x0, x1=max_x, y0=round(row1_top), y1=round(row1_bottom))
    row1_bbox = ink_bbox(raster, row1_box, threshold=200)
    assert row1_bbox is not None
    lane_min_x, _lane_min_y, lane_max_x, _lane_max_y = row1_bbox
    lane_x = (lane_min_x + lane_max_x) // 2

    blank_rows = [
        y
        for y in range(round(row1_bottom) + 1, round(row2_bottom) - 1)
        if not any(raster.is_dark(x, y, threshold=200) for x in range(lane_x - 2, lane_x + 3))
    ]
    assert blank_rows == []


# -- pdf-0008 amendment: fr-vs-auto probes ---------------------------------------------------
#
# The designer's own words, amending the ruling after reviewing the first build's PNG: "a
# column whose content has no length bound is 1fr -- free text, or a joined list of
# designations or labels; a code-like column ... stays auto." The first build made only
# `description` 1fr for BOM; review found a line with many designations starves it down to
# clipping. These probes measure, from the compiled PNG, whether a `wide` column's own header
# text stays inside its own column (no overlap into its neighbour) and is at least as wide as
# its own header word -- not just whether the Typst source names it `1fr`.


def _measured_column_holds(table_source: str, headers: tuple[str, ...], target: str) -> bool:
    """Whether `target`'s own column, in `table_source`'s header row, holds: no header cell
    overlaps its neighbour, and `target`'s own column is at least as wide as its header word
    rendered alone.

    Measured from the compiled PNG (Typst gives no other layout introspection this package
    reaches for): the header row's own drawn cell-border rules (`vertical_rules`, the same
    primitive the Bridge-column tests above use for row boundaries) give each column's
    `[left, right)` span. "No overlap" is read off the rule count itself (see below); "at
    least as wide as its header word" compares that span to the same word rendered alone.
    """
    page = _PAGE + _9PT + table_source
    raw = typst.compile(page.encode("utf-8"), format="png", ppi=_PPI)
    raster = decode_png(raw[0] if isinstance(raw, list) else raw)

    full = Box(x0=0, x1=raster.width, y0=0, y1=raster.height)
    page_bbox = ink_bbox(raster, full, threshold=200)
    if page_bbox is None:
        return False
    min_x, min_y, max_x, _max_y = page_bbox
    table_box = Box(x0=min_x, x1=max_x + 1, y0=min_y, y1=raster.height)
    row_rules = horizontal_rules(raster, table_box, threshold=200, min_coverage=0.8)
    if len(row_rules) < 2:
        return False
    header_box = Box(
        x0=table_box.x0, x1=table_box.x1, y0=round(row_rules[0]), y1=round(row_rules[1])
    )
    col_rules = vertical_rules(raster, header_box, threshold=200, min_coverage=0.8)
    # "No header cell overlaps its neighbour", measured: a column squeezed hard enough to
    # overlap pushes its own two border rules together until they merge into one detected
    # rule (`_merge_runs`), so fewer than `len(headers) + 1` distinct boundaries for
    # `len(headers)` columns is exactly that condition. Confirmed against BOM's own old
    # layout below: 6 rules found where 7 are needed, for the six-column table whose
    # Description/Count headers visually overprint in the reviewed PNG. (An earlier version
    # of this check instead asked each header's own ink to stay strictly inside `[left,
    # right)`; that miscounted the border stroke's own pixel, one column in eight, as
    # "outside" its cell purely from `round()` landing on a `.5` rule centre -- a measurement
    # artifact, not a real overlap, caught by testing this check itself against a real
    # multi-column render, not just the one BOM case it was written against.)
    if len(col_rules) < len(headers) + 1:
        return False

    index = headers.index(target)
    left, right = col_rules[index], col_rules[index + 1]

    word_page = _PAGE + _9PT + f'#strong(text("{_humanise(target)}"))'
    word_raw = typst.compile(word_page.encode("utf-8"), format="png", ppi=_PPI)
    word_raster = decode_png(word_raw[0] if isinstance(word_raw, list) else word_raw)
    word_full = Box(x0=0, x1=word_raster.width, y0=0, y1=word_raster.height)
    word_bbox = ink_bbox(word_raster, word_full, threshold=200)
    if word_bbox is None:
        return False
    word_min_x, _wy0, word_max_x, _wy1 = word_bbox
    word_width = word_max_x - word_min_x
    return (right - left) >= word_width


_BOM_LONG_DESCRIPTION = (
    "Invented relay with an unusually long catalogue description, the kind a real "
    "manufacturer part sheet actually carries, to see whether Description still holds "
    "its own share of the page."
)


def _bom_overflow_model():
    """A BOM line with 30 items sharing one part -- pdf-0008's own review found this shape
    (many designations, a long description) starves Description when Designations stays
    `auto`. The normal shape of one BOM line for a single terminal-block MPN in a real
    cabinet, not a contrived edge case (pdf-0008's amendment).
    """
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(PageKind.SCHEMATIC, PageKind.PLC_LIST, PageKind.TERMINAL_LIST),
    )
    demo_part = part("relay", description=_BOM_LONG_DESCRIPTION)
    items = [
        item(f"k{i}", description=_BOM_LONG_DESCRIPTION, part=demo_part.id) for i in range(1, 31)
    ]
    placements = [place(f"p{i}", item=it.id, node=c1.id) for i, it in enumerate(items, start=1)]
    m = model(c1, doc, demo_part, *items, *placements)
    return m, documents(m)[doc.id]


def test_bom_page_description_column_holds_through_production_wiring():
    """Probe 1 (pdf-0008 amendment), through the real production `bom_page` -- so editing
    `_lists.py`'s own `bom_page` call back to `wide=("description",)` (Designations `auto`)
    makes this fail; that revert-and-observe is this amendment's own can-fail, quoted in the
    work order's hand-back, then undone with Edit.
    """
    m, record = _bom_overflow_model()
    text = bom_page(m, record)
    drawn = tuple(h for h in BOM_COLUMNS if h != "revision")  # part lines only: pdf-0011 drops it
    assert _measured_column_holds(text, drawn, "description")


def test_bom_description_column_check_fails_on_the_old_single_fr_layout():
    """Self-test of probe 1's own check: the same row, laid out the old way (only
    `description` `1fr`, `designations` left `auto`) must fail; the new layout (both `1fr`)
    must pass -- proof the check actually distinguishes the two, not a compile-succeeds smoke
    test that would pass either way.
    """
    designations = tuple(f"K{i}" for i in range(1, 31))
    rows: list[tuple[object, ...]] = [
        ("SIM-RELAY", "A", "Example Co", _BOM_LONG_DESCRIPTION, 1, designations)
    ]

    old_layout = _table(BOM_COLUMNS, rows, ("description",))
    assert not _measured_column_holds(old_layout, BOM_COLUMNS, "description")

    new_layout = _table(BOM_COLUMNS, rows, ("description", "designations"))
    assert _measured_column_holds(new_layout, BOM_COLUMNS, "description")


_LONG_LABEL = "extremely-long-invented-unit-name-that-keeps-going-on (Engine room, cabinet C1)"


def test_cable_list_description_and_labels_hold_with_long_from_to_labels():
    """Probe 2 (pdf-0008 amendment): a cable-list row with long `from_label`/`to_label`
    values -- the designer's own explicit ruling for this list ("the description and the
    from/to label columns are all 1fr"). Same fail-old/pass-new shape as probe 1's own
    self-test: the old layout (only `description` `1fr`) must fail on `from_label`; the new
    layout (`description`, `from_label` and `to_label` all `1fr`) must pass on all three.
    """
    rows: list[tuple[object, ...]] = [
        (
            "W1",
            "DEMO-CBL-4G1.5",
            "Invented 4-core control cable with a long catalogue description too",
            4,
            "1.5",
            15000,
            _LONG_LABEL,
            _LONG_LABEL,
        )
    ]

    old_layout = _table(CABLE_LIST_COLUMNS, rows, ("description",))
    assert not _measured_column_holds(old_layout, CABLE_LIST_COLUMNS, "from_label")

    new_layout = _table(CABLE_LIST_COLUMNS, rows, ("description", "from_label", "to_label"))
    assert _measured_column_holds(new_layout, CABLE_LIST_COLUMNS, "description")
    assert _measured_column_holds(new_layout, CABLE_LIST_COLUMNS, "from_label")
    assert _measured_column_holds(new_layout, CABLE_LIST_COLUMNS, "to_label")


# -- CT2: the frame-fit guarantee this test pinned no longer applies to a harness page ---------
#
# `test_harness_drawing_keeps_the_frame_border_intact` (pdf-0009, RULING W3) pinned that a wide
# WireViz drawing's own opaque background never erased the frame border, through `_cable_page`'s
# own `fit: "contain"` image. CT2 removes that image entirely -- `_cable_page` now builds a
# table, never an SVG -- so the specific pixel-level scenario this test measured (an opaque
# full-bleed drawing landing on the border's centreline) can no longer occur in `_cable_page` at
# all: there is no image path left to regress. `test_harness_page_fit_box_equals_the_content_box`
# (`test_frame.py`) is `_cable_page`'s own remaining frame-fit guard: the table page still keeps
# `text_margin`'s 5 mm clearance, the same content-box padding RULING W3 first added it for.
