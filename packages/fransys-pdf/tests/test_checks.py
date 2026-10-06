"""`check`: `MARKDOWN_UNSUPPORTED`, `DOCUMENT_MIXED_SHEET_FORMATS`, `DOCUMENT_NO_DRAWINGS`,
`DOCUMENT_EMPTY_LIST` (spec P4, P6, P7, P8, P9, P11), `TITLE_BLOCK_NO_ROOM` (page-frame R6) and
`DOCUMENT_NO_TOP_LEVEL_CABLES` (STEP 4b addition, decision pdf-0006).
"""

from decimal import Decimal

from _build import (
    cable_facet,
    cable_product_facet,
    conductor,
    connector,
    document,
    drawing_set,
    item,
    layout_page,
    location,
    model,
    part,
    pcb_facet,
    pin,
    place,
    plc_channel,
    sheet_format,
    terminal,
    wire_facet,
)
from fransys_pdf import check

from fransys_model.kernel import Severity, make_id
from fransys_model.kernel.ids import render_id
from fransys_model.layout import SheetFormat, default_sheet_format
from fransys_model.vocab import DocumentPreset, PageKind, SignalType

_PRESET = DocumentPreset.CABINET_SCHEMATIC
K = PageKind
# Trims a `CABINET_SCHEMATIC` document to COVER (+NOTES): no SCHEMATIC or list page, so `check`
# has nothing new to report beyond what a test itself sets up (spec P7, P9, P11).
_NO_SCHEMATIC_OR_LISTS = (K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM)


def test_no_findings_for_a_fully_supported_cover_and_notes():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover\n\nplain text.",
        notes="Also plain.",
        remove=_NO_SCHEMATIC_OR_LISTS,
    )
    m = model(c1, doc)
    assert check(m, {}) == ()


def test_markdown_unsupported_in_the_cover_names_cover_the_line_and_the_construct():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="ok\n\n`code`",
        notes=None,
        remove=_NO_SCHEMATIC_OR_LISTS,
    )
    m = model(c1, doc)
    (finding,) = check(m, {})
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
        remove=_NO_SCHEMATIC_OR_LISTS,
    )
    m = model(c1, doc)
    (finding,) = check(m, {})
    assert "notes" in finding.message


def test_findings_are_sorted_by_code_subjects_message():
    c1 = location("C1", "Demo cabinet")
    doc_a = document(
        "a", preset=_PRESET, subject=c1, cover="`a`", notes=None, remove=_NO_SCHEMATIC_OR_LISTS
    )
    doc_b = document(
        "b", preset=_PRESET, subject=c1, cover="`b`", notes=None, remove=_NO_SCHEMATIC_OR_LISTS
    )
    m = model(c1, doc_a, doc_b)
    findings = check(m, {})
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
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    records.append(doc)
    return model(*records), doc


def test_mixed_sheet_formats_is_an_error_naming_each_format_and_its_pages():
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    a3 = sheet_format("a3", width_mm=420, height_mm=297)
    m, doc = _cabinet_with_pages(formats=(a4, a3))
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_MIXED_SHEET_FORMATS"]
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
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_MIXED_SHEET_FORMATS"]
    assert findings == []


def test_mixed_sheet_formats_names_the_house_default_when_a_page_names_no_format():
    """A page with no explicit `sheet_format` groups under the house default
    (`default_sheet_format`), not a page-formats key error (`_geometry.mixed_sheet_formats`'s
    `default_sheet_format() if key is None else formats[key]`): the mixed-formats message
    still names it alongside the other, explicit format."""
    a4 = sheet_format("a4", width_mm=210, height_mm=297)
    m, doc = _cabinet_with_pages(formats=(None, a4))
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_MIXED_SHEET_FORMATS"]
    (finding,) = findings
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "a4" in finding.message
    assert default_sheet_format().name in finding.message


def test_no_drawings_for_a_pcb_schematic_document_with_no_drawing_set():
    """A `pcb_schematic` board has no drawing-set engine yet (spec P7): always `No drawings.`."""
    board_part = part("boarditem", description="Invented board")
    board = item("jb1", description="Invented board", part=board_part.id)
    pcb = pcb_facet("boarditem", subject=board_part.id)
    doc = document(
        "d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=board, cover="# Cover", notes=None
    )
    m = model(board_part, board, pcb, doc)
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_NO_DRAWINGS"]
    (finding,) = findings
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "no drawing set" in finding.message


def test_no_drawings_for_a_harness_with_no_cable():
    harness = item("wh1", description="Demo harness")
    doc = document(
        "d1", preset=DocumentPreset.HARNESS_DRAWING, subject=harness, cover="# Cover", notes=None
    )
    m = model(harness, doc)
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_NO_DRAWINGS"]
    (finding,) = findings
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (doc.id,)
    assert "no cable" in finding.message


def test_no_top_level_cables_for_a_system_document_over_a_model_with_no_cable():
    """Units spec U3's amended "cable drawings" bullet (STEP 4b addition, decision pdf-0006):
    a `system` document over a model with no top-level cable at all gives its cable-drawings
    section no page (`test_source.py`'s own proof) and one `DOCUMENT_NO_TOP_LEVEL_CABLES`
    INFO -- never `DOCUMENT_NO_DRAWINGS`'s ERROR, which stays for a harness document naming a
    harness with no cable (`test_no_drawings_for_a_harness_with_no_cable` above, unchanged).
    """
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(doc)
    findings = check(m, {})
    assert [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"] == []
    top_level_findings = [f for f in findings if f.code == "DOCUMENT_NO_TOP_LEVEL_CABLES"]
    (finding,) = top_level_findings
    assert finding.severity is Severity.INFO
    assert finding.subjects == (doc.id,)


def test_no_top_level_cables_finding_is_absent_once_a_top_level_cable_exists():
    """The clean twin: one top-level cable in the model (`unit=None`, harness or not, units
    spec U3's own "harness cables included") clears the INFO -- `harness_cables_for`'s
    `SYSTEM` branch (`derive.top_level_cables`) finds it, so the section has something to
    draw."""
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=None)
    doc = document("d1", preset=DocumentPreset.SYSTEM, cover="# Cover", notes=None)
    m = model(cable, cf, cable_part, cable_product, doc)
    findings = check(m, {render_id(cable.id): "<svg>cable</svg>"})
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
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=(K.CONTENTS, K.BOM),
    )
    m = model(harness, cable, cf, cable_part, cable_product, doc)
    return m, doc, cable


def test_no_drawings_finding_for_a_harness_with_a_cable_even_with_no_svgs_at_all():
    """CT2: a table page needs no rendered drawing, so a harness cable `harness_cables_for`
    finds can never itself be "missing" -- `check(m, {})` alone (no svgs entry for the cable)
    reports nothing, unlike the pre-CT2 behaviour this replaces."""
    m, _doc, _cable = _harness_with_one_cable()
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert findings == []


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
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, ds, p1, p2, doc)
    return m, doc, p1, p2


def test_no_drawings_for_a_cabinet_drawing_set_with_a_missing_key_names_it():
    m, doc, p1, p2 = _cabinet_with_drawing_set()
    svgs = {render_id(p1.id): "<svg>one</svg>"}  # p2's key is missing
    findings = [f for f in check(m, svgs) if f.code == "DOCUMENT_NO_DRAWINGS"]
    (finding,) = findings
    assert finding.subjects == (doc.id,)
    assert render_id(p2.id) in finding.message


def test_no_drawings_finding_when_every_schematic_key_is_present():
    """The clean twin: every drawing-set page's key present in `svgs` reports nothing."""
    m, _doc, p1, p2 = _cabinet_with_drawing_set()
    svgs = {render_id(p1.id): "<svg>one</svg>", render_id(p2.id): "<svg>two</svg>"}
    findings = [f for f in check(m, svgs) if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert findings == []


def test_empty_list_finding_for_a_page_kind_added_with_no_rows():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
        remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST"]
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
        remove=(K.SCHEMATIC, K.TERMINAL_LIST, K.BOM),
    )
    module = item("mod1", description="PLC module")
    module_part, template, fn, facet = plc_channel(
        "ch1", module=module.id, name="ch1", signal=SignalType.DI, channel=1
    )
    m = model(c1, doc, module, module_part, template, fn, facet)
    findings = [
        f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST" and "PLC_LIST" in f.message
    ]
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
        remove=(K.SCHEMATIC, K.PLC_LIST, K.BOM),
    )
    strip = item("x1", description="Strip one")
    t1, t1_facet = terminal("t1", strip=strip.id, group="L", index=1)
    p1 = place("p1", item=strip.id, node=c1.id)
    m = model(c1, doc, strip, t1, t1_facet, p1)
    findings = [
        f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST" and "TERMINAL_LIST" in f.message
    ]
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
        add=(K.CONNECTOR_LIST,),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    board_part = part("board1", description="Invented board")
    board = item("jb1", description="Board one", part=board_part.id)
    pcb = pcb_facet("board1", subject=board_part.id)
    conn_part, conn_template, conn_fn, conn_facet, conn_ports = connector(
        "j1", item=board.id, name="J1", markings=("1",)
    )
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
    findings = [
        f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST" and "CONNECTOR_LIST" in f.message
    ]
    assert findings == []


def test_no_empty_list_finding_for_wire_label_list_when_a_labelled_wire_exists():
    """The clean twin: one conductor with a non-`None` `wire` label reports nothing for
    `WIRE_LABEL_LIST` (`checks._list_rows`'s `WIRE_LABEL_LIST` branch)."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=(K.WIRE_LABEL_LIST,),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    a_item, a_fn, a_port = pin("p1", "P1")
    b_item, b_fn, b_port = pin("p2", "P2")
    cond = conductor("w1", a=a_port.id, b=b_port.id)
    wf = wire_facet("w1", subject=cond.id, label="W1")
    m = model(c1, doc, a_item, a_fn, a_port, b_item, b_fn, b_port, cond, wf)
    findings = [
        f
        for f in check(m, {})
        if f.code == "DOCUMENT_EMPTY_LIST" and "WIRE_LABEL_LIST" in f.message
    ]
    assert findings == []


def test_no_empty_list_finding_for_designation_list_when_an_item_exists():
    """The clean twin: one bare item (a real designation) reports nothing for
    `DESIGNATION_LIST` (`checks._list_rows`'s `DESIGNATION_LIST` branch)."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=(K.DESIGNATION_LIST,),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    demo = item("k1", description="Invented relay")
    m = model(c1, doc, demo)
    findings = [
        f
        for f in check(m, {})
        if f.code == "DOCUMENT_EMPTY_LIST" and "DESIGNATION_LIST" in f.message
    ]
    assert findings == []


def test_no_empty_list_finding_for_cable_list_when_a_cable_exists():
    """The clean twin: one cable item with a `cable` facet reports nothing for `CABLE_LIST`
    (`checks._list_rows`'s `CABLE_LIST` branch)."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=(K.CABLE_LIST,),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    cable_part = part("w1", description="Cable one part")
    cable_product = cable_product_facet("w1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=None)
    m = model(c1, doc, cable, cf, cable_part, cable_product)
    findings = [
        f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST" and "CABLE_LIST" in f.message
    ]
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
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST),
    )
    demo_part = part("relay", description="Invented relay")
    demo_item = item("k1", description="Invented relay", part=demo_part.id)
    placement = place("p1", item=demo_item.id, node=c1.id)
    m = model(c1, doc, demo_part, demo_item, placement)
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST" and "BOM" in f.message]
    assert findings == []


def test_title_block_no_room_absent_for_the_house_sheets_exact_20mm_band():
    """The boundary: `default_sheet_format()`'s 20mm band exactly fits (page-frame R2, R6)."""
    m, _doc = _cabinet_with_pages(formats=(None,))
    findings = [f for f in check(m, {}) if f.code == "TITLE_BLOCK_NO_ROOM"]
    assert findings == []


def test_title_block_no_room_is_a_warning_naming_the_sheet_format_and_its_band_height():
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
    m, doc = _cabinet_with_pages(formats=(tight,))
    findings = [f for f in check(m, {}) if f.code == "TITLE_BLOCK_NO_ROOM"]
    (finding,) = findings
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (doc.id,)
    assert "tight12" in finding.message
    assert "12" in finding.message


def test_empty_list_finding_for_wire_label_list_and_designation_list_added_with_no_rows():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=_PRESET,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=(K.WIRE_LABEL_LIST, K.DESIGNATION_LIST),
        remove=(K.SCHEMATIC, K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(c1, doc)
    findings = [f for f in check(m, {}) if f.code == "DOCUMENT_EMPTY_LIST"]
    messages = {f.message for f in findings}
    assert any("WIRE_LABEL_LIST" in message for message in messages)
    assert any("DESIGNATION_LIST" in message for message in messages)
