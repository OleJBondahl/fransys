"""`check`: `MARKDOWN_UNSUPPORTED`, `DOCUMENT_MIXED_SHEET_FORMATS`, `DOCUMENT_NO_DRAWINGS`,
`DOCUMENT_EMPTY_LIST` and
`DOCUMENT_NO_TOP_LEVEL_CABLES` (decision pdf-0006).
"""

import pytest
from _build import (
    PDF,
    cable_facet,
    cable_product_facet,
    connector,
    document,
    drawing_set,
    item,
    layout_page,
    location,
    model,
    part,
    pcb_facet,
    place,
    plc_channel,
    sheet_format,
    terminal,
)
from fransys_pdf import check

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel import Severity, render_id
from fransys_model.layout import default_sheet_format
from fransys_model.vocab import DocumentPreset, SignalType

_PRESET = DocumentPreset.CABINET_SCHEMATIC


def test_no_findings_for_a_fully_supported_cover_and_notes():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover\n\nplain text.",
        notes="Also plain.",
    )
    ds = drawing_set("ds1", location=c1)
    p1 = layout_page("p1", drawing_set=ds, number=1)
    m = model(c1, ds, p1, doc)
    findings = check(m, {render_id(p1.id): "<svg>one</svg>"}, diagrams=(), laid=frozendict(), pdf=PDF)
    assert [f for f in findings if f.code != "DOCUMENT_EMPTY_LIST"] == []


def test_check_without_laid_is_a_type_error():
    """`laid` has no default (R628): a caller that omits it fails, never skips the measurement."""
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=_PRESET, subject=c1, cover="# Cover")
    m = model(c1, doc)
    with pytest.raises(TypeError, match="laid"):
        check(m, {}, diagrams=())  # ty: ignore[missing-argument] -- the omitted laid is the refusal under test


def test_markdown_unsupported_in_the_cover_names_cover_the_line_and_the_construct():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="ok\n\n`code`",
        notes=None,
    )
    m = model(c1, doc)
    (finding,) = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "MARKDOWN_UNSUPPORTED"]
    assert finding.code == "MARKDOWN_UNSUPPORTED"
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "cover" in finding.message
    assert "3" in finding.message
    assert "inline code" in finding.message


def test_markdown_unsupported_in_the_notes_names_notes():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="ok",
        notes="> quoted",
    )
    m = model(c1, doc)
    (finding,) = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "MARKDOWN_UNSUPPORTED"]
    assert "notes" in finding.message


def test_findings_are_sorted_by_code_subjects_message():
    c1 = location("C1", "Demo cabinet")
    doc_a = document("a", preset=_PRESET, subject=c1, cover="`a`", notes=None)
    doc_b = document("b", preset=_PRESET, subject=c1, cover="`b`", notes=None)
    m = model(c1, doc_a, doc_b)
    findings = check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF)
    findings = [f for f in findings if f.code == "MARKDOWN_UNSUPPORTED"]
    assert [f.subjects for f in findings] == sorted(f.subjects for f in findings)


def _cabinet_with_pages(*, formats):
    """A cabinet whose drawing set has one page per entry of `formats` (each `SheetFormat` or
    `None` for the house sheet), plus a document requesting `SCHEMATIC`.
    """
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    records = [c1, ds]
    for index, fmt in enumerate(formats, start=1):
        if fmt is not None:
            records.append(fmt)
        records.append(layout_page(f"p{index}", drawing_set=ds, number=index, sheet_format=fmt))
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    records.append(doc)
    return model(*records), doc


def test_mixed_sheet_formats_is_an_error_naming_each_format_and_its_pages():
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    a3 = sheet_format("a3", width_mm=420, height_mm=297)
    m, doc = _cabinet_with_pages(formats=(a4, a3))
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_MIXED_SHEET_FORMATS"]
    (finding,) = findings
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "a4" in finding.message
    assert "a3" in finding.message
    assert "1" in finding.message
    assert "2" in finding.message


def test_no_mixed_sheet_formats_finding_when_every_page_agrees():
    """The clean twin: one format across every page of the drawing set reports nothing."""
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    m, _doc = _cabinet_with_pages(formats=(a4, a4))
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_MIXED_SHEET_FORMATS"]
    assert findings == []


def test_mixed_sheet_formats_names_the_house_default_when_a_page_names_no_format():
    """A page with no explicit `sheet_format` groups under the house default
    (`default_sheet_format`), not a page-formats key error (`_geometry.mixed_sheet_formats`'s
    `default_sheet_format() if key is None else formats[key]`): the mixed-formats message
    still names it alongside the other, explicit format."""
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    m, doc = _cabinet_with_pages(formats=(None, a4))
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_MIXED_SHEET_FORMATS"]
    (finding,) = findings
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "a4" in finding.message
    assert default_sheet_format().name in finding.message


def test_no_top_level_cables_for_a_system_document_over_a_model_with_no_cable():
    """The "cable drawings" bullet (decision pdf-0006):
    a `system` document over a model with no top-level cable at all gives its cable-drawings
    section no page (`test_source.py`'s own proof) and one `DOCUMENT_NO_TOP_LEVEL_CABLES`
    INFO -- never `DOCUMENT_NO_DRAWINGS`'s ERROR, which stays for a harness document naming a
    """
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(doc)
    findings = check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF)
    assert [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"] == []
    top_level_findings = [f for f in findings if f.code == "DOCUMENT_NO_TOP_LEVEL_CABLES"]
    (finding,) = top_level_findings
    assert finding.severity is Severity.INFO
    assert finding.subjects == (doc.id,)


def test_no_top_level_cables_finding_is_absent_once_a_top_level_cable_exists():
    """The clean twin: one top-level cable in the model (`unit=None`, harness or not,
    "harness cables included") clears the INFO -- `harness_cables_for`'s
    `SYSTEM` branch (`derive.top_level_cables`) finds it, so the section has something to
    draw."""
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=None)
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(cable, cf, cable_part, cable_product, doc)
    findings = check(m, {render_id(cable.id): "<svg>cable</svg>"}, diagrams=(), laid=frozendict(), pdf=PDF)
    assert [f for f in findings if f.code == "DOCUMENT_NO_TOP_LEVEL_CABLES"] == []
    assert [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"] == []


def _harness_with_one_cable():
    harness = item("wh1", description="Demo harness")
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", parent=harness.id, part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=1500)
    doc = document(
        "d1",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        notes=None,
    )
    m = model(harness, cable, cf, cable_part, cable_product, doc)
    return m, doc, cable


def test_no_drawings_finding_for_a_harness_cable_with_no_block_svg():
    """The cable's block is keyed by `cable_block_key`; with no SVG for it the
    ERROR names that key, as a missing schematic page key does, and with the SVG it is gone."""
    m, _doc, cable = _harness_with_one_cable()
    key = cable_block_key(None, cable.id)
    (finding,) = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert finding.severity is Severity.ERROR
    assert finding.message == f"HARNESS_DRAWING: missing drawing for {key}"
    assert [f for f in check(m, {key: "<svg>b</svg>"}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_NO_DRAWINGS"] == []


def _cabinet_with_drawing_set():
    c1 = location("C1", "Demo cabinet")
    ds = drawing_set("ds1", location=c1)
    p1 = layout_page("p1", drawing_set=ds, number=1)
    p2 = layout_page("p2", drawing_set=ds, number=2)
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    m = model(c1, ds, p1, p2, doc)
    return m, doc, p1, p2


def test_no_drawings_for_a_cabinet_drawing_set_with_a_missing_key_names_it():
    m, doc, p1, p2 = _cabinet_with_drawing_set()
    svgs = {render_id(p1.id): "<svg>one</svg>"}  # p2's key is missing
    findings = [f for f in check(m, svgs, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_NO_DRAWINGS"]
    (finding,) = findings
    assert finding.subjects == (doc.id,)
    assert render_id(p2.id) in finding.message


def test_no_drawings_finding_when_every_schematic_key_is_present():
    """The clean twin: every drawing-set page's key present in `svgs` reports nothing."""
    m, _doc, p1, p2 = _cabinet_with_drawing_set()
    svgs = {render_id(p1.id): "<svg>one</svg>", render_id(p2.id): "<svg>two</svg>"}
    findings = [f for f in check(m, svgs, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert findings == []


def test_empty_list_finding_for_a_page_kind_added_with_no_rows():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    m = model(c1, doc)
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_EMPTY_LIST" and "PLC_LIST" in f.message]
    (finding,) = findings
    assert finding.severity is Severity.INFO
    assert finding.subjects == (doc.id,)
    assert finding.message == "PLC_LIST has no rows: the page is left out"  # pdf-0019
    assert "PLC_LIST" in finding.message


def test_no_empty_list_finding_for_plc_list_when_it_has_rows():
    """The clean twin: a PLC channel present reports nothing for `PLC_LIST`."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    module = item("mod1", description="PLC module")
    module_part, template, fn, facet, channel_pin = plc_channel("ch1", module=module.id, name="ch1", signal=SignalType.DI, channel=1)
    m = model(c1, doc, module, module_part, template, fn, facet, channel_pin)
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_EMPTY_LIST" and "PLC_LIST" in f.message]
    assert findings == []


def test_no_empty_list_finding_for_terminal_list_when_a_strip_is_placed():
    """A strip placed at the location gives `TERMINAL_LIST` a row: no finding for that kind."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    strip = item("x1", description="Strip one")
    t1, t1_facet = terminal("t1", strip=strip.id, group="L", index=1)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(c1, doc, strip, t1, t1_facet, p1)
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_EMPTY_LIST" and "TERMINAL_LIST" in f.message]
    assert findings == []


def test_no_empty_list_finding_for_connector_list_when_a_board_has_a_connector():
    """The clean twin: a board placed at the location with one connector port reports nothing
    for `CONNECTOR_LIST` (`checks._list_rows`'s `CONNECTOR_LIST` branch)."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id)
    pcb = pcb_facet("board1", subject=board_part.id)
    conn_part, conn_template, conn_fn, conn_facet, conn_ports = connector("j1", item=board.id, name="J1", markings=("1",))
    p1 = place("p1", item=board.id, node=c1.id)
    m = model(
        c1,
        doc,
        board_part,
        board,
        pcb,
        conn_part,
        conn_template,
        conn_fn,
        conn_facet,
        *conn_ports,
        p1,
    )
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_EMPTY_LIST" and "CONNECTOR_LIST" in f.message]
    assert findings == []


def test_no_empty_list_finding_for_cable_list_when_a_cable_exists():
    """The clean twin: a system document over one cable item reports nothing for `CABLE_LIST`
    (`checks._list_rows`'s `CABLE_LIST` branch); a location document draws no cable (pdf-0042)."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        notes=None,
    )
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=None)
    m = model(c1, doc, cable, cf, cable_part, cable_product)
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_EMPTY_LIST" and "CABLE_LIST" in f.message]
    assert findings == []


def test_no_empty_list_finding_for_bom_when_a_part_linked_item_is_placed():
    """The clean twin: a part-linked item placed at the location reports nothing for `BOM`
    (`checks._list_rows`'s trailing `BOM` branch)."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
    )
    demo_part = part("relay", description="Invented relay")
    demo_item = item("k1", description="Invented relay", part=demo_part.id)
    placement = place("p1", item=demo_item.id, node=c1.id)
    m = model(c1, doc, demo_part, demo_item, placement)
    findings = [f for f in check(m, {}, diagrams=(), laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_EMPTY_LIST" and "BOM" in f.message]
    assert findings == []


def test_a_notice_that_fits_raises_no_overflow_finding():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notice="(c) Demo AS",
    )
    ds = drawing_set("ds1", location=c1)
    p1 = layout_page("p1", drawing_set=ds, number=1)
    findings = check(model(c1, ds, p1, doc), {render_id(p1.id): "<svg>one</svg>"}, diagrams=(), laid=frozendict(), pdf=PDF)
    assert [f for f in findings if f.code != "DOCUMENT_EMPTY_LIST"] == []
