"""`derive.sheets` and the sheet texts: `3`, `2.3`, `B1`, `B1 / 2`, label `b1` (PAGES-INDEX P1)."""

from plant import Plant

from fransys_model.derive import (
    page_destination,
    page_title_forms,
    sheet_counter_text,
    sheet_index_rows,
    sheet_text,
    sheet_title_text,
    sheets,
)
from fransys_model.kernel import Id, make_id
from fransys_model.layout import DiagramSheet, DrawingSet, Page, PageRole
from fransys_model.vocab import Document, DocumentPreset, PageKind

_PLANT = Plant()
_UNIT: Id = _PLANT.unit("u", name="u")


def _set(number: int) -> DrawingSet:
    key = ("drawing_set", str(number))
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, unit=_UNIT, number=number,
        produced_by="test",
    )  # fmt: skip


def _page(drawing_set: DrawingSet, number: int) -> Page:
    key = ("page", f"{drawing_set.number}.{number}")
    return Page(
        id=make_id(Page, key), key=key, drawing_set=drawing_set.id, number=number,
        role=PageRole.CONTROL, sheet_format=None, groups=(), produced_by="test",
    )  # fmt: skip


def _diagram(number: int, unit: Id | None) -> DiagramSheet:
    key = ("diagram_sheet", f"{unit}.{number}")
    return DiagramSheet(
        id=make_id(DiagramSheet, key), key=key, unit=unit, number=number, produced_by="test"
    )


def _document(preset: DocumentPreset, unit: Id | None) -> Document:
    key = ("document", preset.value)
    return Document(
        id=make_id(Document, key), key=key, preset=preset,
        location=None, item=None, add=(), remove=(), cover="c", notes=None, unit=unit,
    )  # fmt: skip


def _fixture():
    s1, s2 = _set(1), _set(2)
    pages = (_page(s1, 1), _page(s1, 2), _page(s2, 3))
    diagrams = (_diagram(2, _UNIT), _diagram(1, _UNIT), _diagram(1, None))
    plant = Plant()
    plant.add(*_PLANT.records, s1, s2, *pages, *diagrams)
    plant.add(
        _document(DocumentPreset.PCB_SCHEMATIC, _UNIT), _document(DocumentPreset.SYSTEM, None)
    )
    return plant.model(), pages, diagrams


def test_diagram_sheets_come_first_then_pages_and_each_prints_its_form() -> None:
    model, pages, diagrams = _fixture()
    record = _document(DocumentPreset.PCB_SCHEMATIC, _UNIT)
    kinds = (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC)
    found = sheets(model, record.id, kinds)
    assert found == (diagrams[1], diagrams[0], *pages)
    assert [sheet_text(model, s) for s in found] == ["B1", "B2", "1", "2", "2.3"]
    assert [page_destination(model, s) for s in found] == ["b1", "b2", "p1.1", "p1.2", "p2.3"]
    assert sheet_counter_text(found[0], 2) == "B1 / 2"
    assert sheet_counter_text(found[2], 3) == "1 / 3"
    assert sheet_title_text(model, found[4], "Pump 1") == "Sheet 2.3: Pump 1"


def test_a_dropped_kind_contributes_no_sheet_and_system_reads_the_absolute_diagram() -> None:
    model, pages, diagrams = _fixture()
    unit_doc = _document(DocumentPreset.PCB_SCHEMATIC, _UNIT)
    assert sheets(model, unit_doc.id, (PageKind.SCHEMATIC,)) == pages
    assert sheets(model, unit_doc.id, (PageKind.BLOCK_DIAGRAM,)) == diagrams[1::-1]
    system = _document(DocumentPreset.SYSTEM, None)
    assert sheets(model, system.id, (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC)) == (diagrams[2],)


def test_the_index_rows_list_diagram_sheets_first_and_none_for_fewer_than_two_sheets() -> None:
    model, pages, _ = _fixture()
    record = _document(DocumentPreset.PCB_SCHEMATIC, _UNIT)
    both = (PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC)
    rows = sheet_index_rows(model, record.id, both)
    assert [(r.sheet, r.title, r.destination) for r in rows[:3]] == [
        ("B1", "Block diagram", "b1"),
        ("B2", "Block diagram", "b2"),
        ("1", page_title_forms(model, pages[0])[0], "p1.1"),
    ]
    assert [r.sheet for r in rows] == ["B1", "B2", "1", "2", "2.3"]
    assert sheet_index_rows(model, record.id, (PageKind.BLOCK_DIAGRAM,))[0].sheet == "B1"
    system = _document(DocumentPreset.SYSTEM, None)
    assert sheet_index_rows(model, system.id, both) == ()  # one diagram sheet, no pages: one sheet
