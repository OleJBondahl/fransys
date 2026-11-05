"""One page order, one diagram sheet order and one installed test (render-0015, model-0270)."""

from typing import TYPE_CHECKING

from derive_helpers import numbered_drawing_set
from derive_helpers import numbered_page as _page
from plant import Plant

from fransys_model.derive import (
    DiagramSheet,
    diagram_sheet_order_key,
    document_pages,
    item_installed,
    ordered_pages,
)
lazy from fransys_model.vocab.core import Unit

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.layout import DrawingSet

_PLANT = Plant()
_UNIT = _PLANT.unit("u", name="u")


def _set(number: int) -> DrawingSet:
    return numbered_drawing_set(_UNIT, number)


def _model(*records):
    plant = Plant()
    plant.add(*_PLANT.records, *records)
    return plant.model()


def test_pages_come_in_set_then_page_order() -> None:
    s1, s2 = _set(1), _set(2)
    pages = (_page(s2, 1), _page(s1, 5), _page(s2, 3), _page(s1, 2))
    model = _model(s1, s2, *pages)
    found = ordered_pages(model)
    assert [p.id for p in found] == [pages[3].id, pages[1].id, pages[0].id, pages[2].id]


def test_pages_can_leave_out_a_replica_only_set(monkeypatch) -> None:
    s1, s2 = _set(1), _set(2)
    pages = (_page(s1, 1), _page(s2, 1))
    model = _model(s1, s2, *pages)
    monkeypatch.setattr(document_pages, "is_replica_only_undrawn", lambda _m, s: s.number == 2)
    assert [p.id for p in ordered_pages(model, include_replica_only=False)] == [pages[0].id]
    assert [p.id for p in ordered_pages(model)] == [pages[0].id, pages[1].id]


def test_diagram_sheets_run_absolute_reading_first_then_by_number() -> None:
    def sheet(number: int, unit: Id[Unit] | None) -> DiagramSheet:
        return DiagramSheet(unit=unit, number=number)

    a, b, c = sheet(2, _UNIT), sheet(1, _UNIT), sheet(3, None)
    assert sorted((a, b, c), key=diagram_sheet_order_key) == [c, b, a]


def test_item_installed_reads_the_item_record() -> None:
    plant = Plant()
    on, off = plant.item("on"), plant.item("off", installed=False)
    model = plant.model()
    assert item_installed(model, on) is True
    assert item_installed(model, off) is False
