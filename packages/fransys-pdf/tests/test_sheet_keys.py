"""A `SheetKey` names a page of one document: another document's key is missing (pdf-0050)."""

import dataclasses

import fransys_render
import pytest
from _build import document, drawing_set, layout_page, location, model, source

from fransys_model.derive import SheetKey, document_sheets_of, sheet_key_text
from fransys_model.kernel import render_id
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind
_REMOVE = (K.PLC_LIST, K.TERMINAL_LIST, K.BOM, K.SHEET_INDEX)


def _two_documents():
    c1, c2 = location("C1", "Demo cabinet"), location("C2", "Second cabinet")
    ds1, ds2 = drawing_set("ds1", location=c1), drawing_set("ds2", location=c2)
    pages = [
        layout_page("p1", drawing_set=ds1, number=1),
        layout_page("p2", drawing_set=ds2, number=1),
    ]
    docs = [
        document(
            key, preset=DocumentPreset.CABINET_SCHEMATIC, subject=where, cover="# Cover",
            notes=None, remove=_REMOVE,
        )
        for key, where in (("a", c1), ("b", c2))
    ]  # fmt: skip
    return (
        model(c1, c2, ds1, ds2, *pages, *docs),
        docs,
        {render_id(pages[0].id): "<svg>one</svg>"},
    )  # one printer per set (R331)


_M, (_A, _B), _SVGS = _two_documents()
_ALL = fransys_render.sheets(document_sheets_of(_M))
_SHEETS = {key: back for key, back in _ALL.items() if key.document == _A.id}  # A's pages only


def test_the_right_keys_give_the_documents_source() -> None:
    assert {key.document for key in _ALL} == {_A.id, _B.id}
    text = source(_M, _A.id, _SVGS, _SHEETS)
    assert "<svg>one</svg>" in text
    assert text.count("#page(margin: 0mm, background:") == 1


def test_a_key_of_another_document_is_a_missing_sheet() -> None:
    # A's schematic page is filed under document B's id, every other page stays A's
    moved = {
        key: dataclasses.replace(key, document=_B.id) if key.kind is K.SCHEMATIC else key
        for key in _SHEETS
    }
    of_b = {moved[key]: back for key, back in _SHEETS.items()}
    missing = SheetKey(_A.id, K.SCHEMATIC, 0)
    assert missing not in of_b
    with pytest.raises(KeyError) as raised:
        source(_M, _A.id, _SVGS, of_b)
    assert sheet_key_text(missing) in str(raised.value)
