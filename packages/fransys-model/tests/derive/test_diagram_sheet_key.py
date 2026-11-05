"""`diagram_sheet_key`: `diagram:<unit render id or empty>:<n>`, one key per (unit, number)."""

from fransys_model.derive import DiagramSheet, diagram_sheet_key
from fransys_model.kernel import make_id, render_id
from fransys_model.vocab import Unit


def _unit(name: str):
    return make_id(Unit, (name,))


def test_the_absolute_reading_has_an_empty_unit_part() -> None:
    assert diagram_sheet_key(DiagramSheet(unit=None, number=3)) == "diagram::3"


def test_a_unit_reading_prints_the_units_render_id() -> None:
    unit = _unit("u")
    assert diagram_sheet_key(DiagramSheet(unit=unit, number=2)) == f"diagram:{render_id(unit)}:2"


def test_distinct_unit_and_number_give_distinct_keys() -> None:
    sheets = [DiagramSheet(unit=u, number=n) for u in (None, _unit("a"), _unit("b")) for n in (1, 2)]
    assert len({diagram_sheet_key(s) for s in sheets}) == len(sheets)
