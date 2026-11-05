"""`document_page_kinds`: the preset's pages, NOTES dropped without
notes text (`document_page_kinds` was the scaffold's until this part)."""

from _build import document, location, model

from fransys_model.derive import document_page_kinds
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind


def test_default_pages_with_notes_text():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        notes="Some notes.",
    )
    m = model(c1, doc)
    assert document_page_kinds(m, doc.id) == (
        K.COVER,
        K.NOTES,
        K.SHEET_INDEX,
        K.SCHEMATIC,
        K.PLC_LIST,
        K.TERMINAL_LIST,
        K.CONNECTOR_LIST,
        K.BOM,
    )


def test_notes_dropped_when_there_is_no_notes_text():
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover", notes=None)
    m = model(c1, doc)
    assert K.NOTES not in document_page_kinds(m, doc.id)


def test_every_preset_takes_the_sheet_index():
    for preset in DocumentPreset:
        c1 = None if preset is DocumentPreset.SYSTEM else location("C1", "Demo cabinet")
        doc = document("d1", preset=preset, subject=c1, cover="# Cover", notes="n")
        assert K.SHEET_INDEX in document_page_kinds(model(*[r for r in (c1, doc) if r is not None]), doc.id), preset
