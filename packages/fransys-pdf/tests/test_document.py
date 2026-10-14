"""`document_pages`: the preset's pages plus additions and removals, NOTES dropped without
notes text (`document_pages` was the scaffold's until this part)."""

from _build import document, location, model
from fransys_pdf import document_pages

from fransys_model.kernel import from_data, to_data
from fransys_model.vocab import DocumentPreset, PageKind, documents

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
        K.SHEET_INDEX,
        K.SCHEMATIC,
        K.PLC_LIST,
        K.TERMINAL_LIST,
        K.CONNECTOR_LIST,
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
        K.SHEET_INDEX,
        K.HARNESS_DRAWING,
        K.PLC_LIST,
        K.BOM,
    )


def test_every_preset_takes_the_sheet_index_and_remove_drops_it():
    for preset in DocumentPreset:
        c1 = None if preset is DocumentPreset.SYSTEM else location("C1", "Demo cabinet")
        doc = document("d1", preset=preset, subject=c1, cover="# Cover", notes="n")
        assert K.SHEET_INDEX in document_pages(
            model(*[r for r in (c1, doc) if r is not None]), doc.id
        ), preset
        dropped = document(
            "d1", preset=preset, subject=c1, cover="# Cover", notes="n", remove=(K.SHEET_INDEX,)
        )
        assert K.SHEET_INDEX not in document_pages(
            model(*[r for r in (c1, dropped) if r is not None]), dropped.id
        ), preset


def test_a_document_that_removes_the_sheet_index_survives_a_data_round_trip():
    c1 = location("C1", "Demo cabinet")
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=c1,
        cover="# Cover",
        remove=(K.SHEET_INDEX,),
    )
    again = from_data(to_data(model(c1, doc)))
    assert documents(again)[doc.id].remove == (K.SHEET_INDEX,)
