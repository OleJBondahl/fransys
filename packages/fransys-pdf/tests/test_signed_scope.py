"""The title block's subject label keeps the BARE label (page-frame R10, pdf-0005 item 4).

Owner ruling: "the subject label keeps the bare location label: C1 Demo cabinet, no +". A
follow-up asked for a signed scope (`+C1 Demo cabinet`); the designer retracted it as an error
against this ruling (model-0054 section 6). These tests are the regression guard: a location's
label, an item document's designation and a harness page's scope print with no sign in the
Scope cell and the document heading, and each test fails if a sign is added.
"""

from dataclasses import replace

from _build import (
    document,
    drawing_set,
    item,
    layout_page,
    location,
    model,
    part,
    project,
    sheet_format,
)
from fransys_pdf import source
from fransys_pdf._drawings import _cable_page
from fransys_pdf._geometry import document_heading, preamble, subject_label

from fransys_model.derive import HarnessCable
from fransys_model.kernel.ids import render_id
from fransys_model.vocab import DocumentPreset, PageKind, documents

K = PageKind


def _nested_cabinet():
    """`+ER+C1`: the cabinet `C1` inside the room `ER`."""
    room = location("ER", "Electrical room")
    cabinet = replace(location("C1", "Demo cabinet"), parent=room.id)
    return room, cabinet


def _schematic_source(*nodes):
    """`source` of a cabinet schematic at the last node of `nodes`, with one drawing page."""
    subject = nodes[-1]
    ds = drawing_set("ds1", location=subject)
    page = layout_page("p1", drawing_set=ds, number=1)
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=subject,
        cover="# Cover",
        notes=None,
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
    )
    m = model(*nodes, project(), ds, page, doc)
    return source(m, doc.id, {render_id(page.id): "<svg>one</svg>"})


def test_a_location_documents_subject_label_is_the_bare_label():
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    m = model(c1, doc)
    record = documents(m)[doc.id]
    assert subject_label(m, record) == "C1 Demo cabinet"
    assert document_heading(m, record).endswith("— C1 Demo cabinet")


def test_a_nested_locations_subject_label_stays_as_main_printed_it():
    room, cabinet = _nested_cabinet()
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=cabinet, cover="# Cover")
    m = model(room, cabinet, doc)
    assert subject_label(m, documents(m)[doc.id]) == "C1 Demo cabinet"


def test_an_item_documents_subject_label_has_no_sign():
    demo_part = part("relay", description="Invented relay")
    board = item("a1", description="", part=demo_part.id)
    doc = document("d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=board, cover="# Cover")
    m = model(demo_part, board, doc)
    assert subject_label(m, documents(m)[doc.id]) == "A1 Invented relay"


def test_a_drawing_pages_scope_cell_reads_the_bare_location():
    c1 = location("C1", "Demo cabinet")
    text = _schematic_source(c1)
    assert 'text(size: 8pt, "Scope"), text(size: 10pt, text("C1"))' in text
    assert '"+C1"' not in text


def test_a_harness_drawing_pages_scope_cell_reads_the_bare_harness():
    harness = item("h1", description="Harness one")
    cable_item = item("w1", description="Cable one")
    doc = document("d1", preset=DocumentPreset.HARNESS_DRAWING, subject=harness, cover="# Cover")
    m = model(project(), harness, doc)
    sheet = sheet_format("wide", width_mm=150, height_mm=200, frame_columns=1, frame_rows=1)
    cable = HarnessCable(
        cable=cable_item.id,
        designation="-W1",
        mpn=None,
        description=None,
        core_count=None,
        gauge_mm2=None,
        shielded=None,
        length_mm=None,
        cores=(),
        ends=(),
    )
    text = preamble(sheet) + _cable_page(m, documents(m)[doc.id], sheet, cable)
    assert 'text(size: 8pt, "Scope"), text(size: 10pt, text("H1"))' in text
