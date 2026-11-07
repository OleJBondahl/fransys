"""`derive.sheets` and the one page number each sheet prints: `pdf_page`, label `p<n>` (PAGES-INDEX P1)."""

from typing import TYPE_CHECKING

from derive_helpers import numbered_drawing_set
from derive_helpers import numbered_page as _page
from plant import Plant

from fransys_model.derive import (
    DiagramSheet,
    page_destination,
    page_title_forms,
    pdf_page,
    sheet_index_rows,
    sheet_title_text,
    sheets,
)
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import Document, DocumentPreset, PageKind
lazy from fransys_model.vocab.core import Unit

if TYPE_CHECKING:
    from fransys_model.layout import DrawingSet

_PLANT = Plant()
_UNIT = _PLANT.unit("u", name="u")


def _set(number: int) -> DrawingSet:
    return numbered_drawing_set(_UNIT, number)


def _diagram(number: int, unit: Id[Unit] | None) -> DiagramSheet:
    return DiagramSheet(unit=unit, number=number)


def _document(preset: DocumentPreset, unit: Id[Unit] | None) -> Document:
    key = ("document", preset.value)
    return Document(
        id=make_id(Document, key), key=key, preset=preset,
        location=None, item=None, cover="c", notes=None, unit=unit,
    )  # fmt: skip


def _fixture():
    s1, s2 = _set(1), _set(2)
    pages = (_page(s1, 1), _page(s1, 2), _page(s2, 3))
    diagrams = (_diagram(2, _UNIT), _diagram(1, _UNIT), _diagram(1, None))
    plant = Plant()
    plant.add(*_PLANT.records, s1, s2, *pages)
    plant.add(_document(DocumentPreset.CABINET_SCHEMATIC, _UNIT), _document(DocumentPreset.SYSTEM, None))
    return plant.model(), pages, diagrams


def test_diagram_sheets_come_first_then_pages_and_each_prints_its_form() -> None:
    model, pages, diagrams = _fixture()
    record = _document(DocumentPreset.CABINET_SCHEMATIC, _UNIT)
    kinds = (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC)
    found = sheets(model, record.id, kinds, diagrams)
    assert found == (diagrams[1], diagrams[0], *pages)
    numbers = [pdf_page(model, s) for s in found]
    assert numbers[2:] == [2, 3, 4]  # the cover is 1, the pages follow it in order
    assert pdf_page(model, diagrams[2]) == 2  # the absolute diagram sheet is the SYSTEM document's, after its cover
    assert [page_destination(model, s) for s in found] == [f"p{n}" for n in numbers]
    assert sheet_title_text(model, found[4], "Pump 1") == "4: Pump 1"
    assert sheet_title_text(model, found[4], "") == "4"


def test_a_dropped_kind_contributes_no_sheet_and_system_reads_the_absolute_diagram() -> None:
    model, pages, diagrams = _fixture()
    unit_doc = _document(DocumentPreset.CABINET_SCHEMATIC, _UNIT)
    assert sheets(model, unit_doc.id, (PageKind.SCHEMATIC,), diagrams) == pages
    assert sheets(model, unit_doc.id, (PageKind.BLOCK_DIAGRAM,), diagrams) == diagrams[1::-1]
    system = _document(DocumentPreset.SYSTEM, None)
    assert sheets(model, system.id, (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC), diagrams) == (diagrams[2],)


def test_the_index_rows_list_diagram_sheets_first_and_none_for_fewer_than_two_sheets() -> None:
    model, pages, diagrams = _fixture()
    record = _document(DocumentPreset.CABINET_SCHEMATIC, _UNIT)
    both = (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC)
    rows = sheet_index_rows(model, record.id, both, diagrams)
    assert [(r.title, r.destination) for r in rows[:2]] == [("Block diagram", f"p{rows[0].page}"), ("Block diagram", f"p{rows[1].page}")]
    assert (rows[2].title, rows[2].page, rows[2].destination) == (page_title_forms(model, pages[0])[0], 2, "p2")
    assert [r.page for r in rows[2:]] == [2, 3, 4]
    system = _document(DocumentPreset.SYSTEM, None)
    assert sheet_index_rows(model, system.id, both, diagrams) == ()  # one diagram sheet, no pages: one sheet
