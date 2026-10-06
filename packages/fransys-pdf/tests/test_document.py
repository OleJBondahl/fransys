"""`document_pages`: the preset's pages plus additions and removals, NOTES dropped without
notes text (spec P10; `document_pages` was the scaffold's until this part)."""

from _build import document, location, model
from fransys_pdf import document_pages

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
    assert document_pages(m, doc.id) == (
        K.COVER,
        K.NOTES,
        K.SCHEMATIC,
        K.PLC_LIST,
        K.TERMINAL_LIST,
        K.BOM,
    )


def test_notes_dropped_when_there_is_no_notes_text():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover", notes=None
    )
    m = model(c1, doc)
    assert K.NOTES not in document_pages(m, doc.id)


def test_notes_dropped_even_when_explicitly_added_with_no_notes_text():
    """`remove`'s NOTES rule from a missing notes file, not from the authored `add`/`remove`."""
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=c1,
        cover="# Cover",
        notes=None,
        add=(K.NOTES,),
    )
    m = model(c1, doc)
    assert K.NOTES not in document_pages(m, doc.id)


def test_add_and_remove_are_honoured():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=c1,
        cover="# Cover",
        notes="notes",
        add=(K.PLC_LIST,),
        remove=(K.CONTENTS,),
    )
    m = model(c1, doc)
    assert document_pages(m, doc.id) == (
        K.COVER,
        K.NOTES,
        K.HARNESS_DRAWING,
        K.PLC_LIST,
        K.BOM,
    )
