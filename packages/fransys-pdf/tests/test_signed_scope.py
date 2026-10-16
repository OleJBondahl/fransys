"""The subject label keeps the BARE label (pdf-0005 item 4); the Scope cell differs (model-0301).

Owner ruling: "the subject label keeps the bare location label: C1 Demo cabinet, no +". A
follow-up asked for a signed scope (`+C1 Demo cabinet`); it was retracted as an error
against this ruling (model-0054 section 6). These tests are the regression guard: a location's
label, an item document's designation and a harness page's scope print with no sign in the
Scope cell and the document heading, and each test fails if a sign is added.
"""

from dataclasses import replace

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
    project,
)
from fransys_pdf._geometry import document_heading

from fransys_model.derive import SheetKey, document_row, document_sheets_of, subject_label
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind


def _nested_cabinet():
    """`+ER+C1`: the cabinet `C1` inside the room `ER`."""
    room = location("ER", "Electrical room")
    cabinet = replace(location("C1", "Demo cabinet"), parent=room.id)
    return room, cabinet


def _schematic_background(*nodes):
    """The first drawing page's background SVG of a cabinet schematic at the last of `nodes`."""
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
    return fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.SCHEMATIC, 0)].svg


def test_a_location_documents_subject_label_is_the_bare_label():
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    m = model(c1, doc)
    record = document_row(m, doc.id)
    assert subject_label(m, record.id) == "C1 Demo cabinet"
    assert document_heading(m, record).endswith("— C1 Demo cabinet")


def test_a_nested_locations_subject_label_stays_as_main_printed_it():
    room, cabinet = _nested_cabinet()
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=cabinet, cover="# Cover")
    m = model(room, cabinet, doc)
    assert subject_label(m, doc.id) == "C1 Demo cabinet"


def test_an_item_documents_subject_label_has_no_sign():
    demo_part = part("relay", description="Invented relay")
    board = item("a1", description="", part=demo_part.id)
    doc = document("d1", preset=DocumentPreset.PCB_SCHEMATIC, subject=board, cover="# Cover")
    m = model(demo_part, board, doc)
    assert subject_label(m, doc.id) == "A1 Invented relay"


def test_a_drawing_pages_scope_cell_reads_the_signed_location_path():
    c1 = location("C1", "Demo cabinet")
    svg = _schematic_background(c1)
    assert ">Scope</text>" in svg
    assert ">+C1</text>" in svg


def test_a_harness_drawing_pages_scope_cell_reads_the_bare_harness():
    harness = item("h1", description="Harness one")
    demo_part = part("cab1", description="Invented 4-core cable")
    product = cable_product_facet("cab1", subject=demo_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=demo_part.id, parent=harness.id)
    facet = cable_facet("w1", subject=cable.id, length_mm=1500)
    doc = document("d1", preset=DocumentPreset.HARNESS_DRAWING, subject=harness, cover="# Cover")
    m = model(project(), harness, demo_part, product, cable, facet, doc)
    svg = fransys_render.sheets(document_sheets_of(m))[SheetKey(doc.id, K.HARNESS_DRAWING, 0)].svg
    assert ">Scope</text>" in svg
    assert ">H1</text>" in svg
