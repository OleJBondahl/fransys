from fransys_pdf import PRESET_PAGES, page_kinds

from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind


def test_every_preset_starts_with_cover_notes_and_ends_with_bom():
    for pages in PRESET_PAGES.values():
        assert pages[:2] == (K.COVER, K.NOTES)
        assert pages[-1] is K.BOM


def test_default_pages():
    assert page_kinds(DocumentPreset.CABINET_SCHEMATIC) == (
        K.COVER,
        K.NOTES,
        K.SCHEMATIC,
        K.PLC_LIST,
        K.TERMINAL_LIST,
        K.BOM,
    )
    assert page_kinds(DocumentPreset.HARNESS_DRAWING) == (
        K.COVER,
        K.NOTES,
        K.CONTENTS,
        K.HARNESS_DRAWING,
        K.BOM,
    )
    assert page_kinds(DocumentPreset.PCB_SCHEMATIC) == (
        K.COVER,
        K.NOTES,
        K.SCHEMATIC,
        K.CONNECTOR_LIST,
        K.BOM,
    )


def test_added_pages_land_in_canonical_order_not_call_order():
    got = page_kinds(DocumentPreset.PCB_SCHEMATIC, add=(K.PLC_LIST, K.CONTENTS))
    assert got == (K.COVER, K.NOTES, K.CONTENTS, K.SCHEMATIC, K.PLC_LIST, K.CONNECTOR_LIST, K.BOM)


def test_remove_and_duplicate_add():
    got = page_kinds(DocumentPreset.HARNESS_DRAWING, add=(K.BOM,), remove=(K.CONTENTS, K.BOM))
    assert got == (K.COVER, K.NOTES, K.HARNESS_DRAWING)
