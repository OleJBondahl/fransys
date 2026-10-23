"""`layout.sheet`: a cable or block sheet freezes, round-trips and has one kind tuple."""

import pytest

from fransys_model.kernel import (
    Draft,
    Origin,
    SchemaError,
    dumps,
    freeze,
    loads,
    lookup_kind,
    make_id,
)
from fransys_model.layout import (
    AUTHORED_KINDS,
    CABLE_KINDS,
    DERIVED_KINDS,
    DIAGRAM_KINDS,
    LIBRARY_KINDS,
    OVERVIEW_KINDS,
    SHEET_KINDS,
    LayoutSheet,
    SheetKind,
    derived_layout_ids,
)

_ORIGIN = Origin(file="test_sheets.py", line=1, note="fixture")
_ALL = (
    AUTHORED_KINDS,
    DERIVED_KINDS,
    CABLE_KINDS,
    DIAGRAM_KINDS,
    OVERVIEW_KINDS,
    LIBRARY_KINDS,
    SHEET_KINDS,
)


def _sheet(kind: SheetKind, number: int = 1) -> LayoutSheet:
    key = ("sheet", kind.value, str(number))
    return LayoutSheet(
        id=make_id(LayoutSheet, key),
        key=key,
        sheet_kind=kind,
        document="doc",
        number=number,
        sheet_format=None,
        produced_by="sheets-test",
    )


def test_sheet_kind_values() -> None:
    """The two values are the stored strings."""
    assert {kind.value for kind in SheetKind} == {"cable", "block"}


@pytest.mark.parametrize("kind", list(SheetKind))
def test_a_sheet_round_trips_and_its_id_derives_from_its_key(kind: SheetKind) -> None:
    """Freeze, write canonical JSON, load: the same sheet comes back."""
    sheet = _sheet(kind)
    draft = Draft()
    draft.extend([sheet], origin=_ORIGIN)
    model = freeze(draft)
    assert loads(dumps(model)) == model
    assert sheet.id == make_id(LayoutSheet, sheet.key)
    assert derived_layout_ids(model, kinds=SHEET_KINDS) == (sheet.id,)


def test_the_kind_is_registered_and_listed_in_exactly_one_tuple() -> None:
    """`layout.sheet` resolves to the record and only `SHEET_KINDS` holds it."""
    assert lookup_kind("layout.sheet") is LayoutSheet
    assert sum(LayoutSheet in kinds for kinds in _ALL) == 1
    assert LayoutSheet in SHEET_KINDS


def test_no_drawn_kind_is_a_layout_kind() -> None:
    """R234: the page drawings are in-memory values; no `layout.drawn_*` record kind exists."""
    names = [vars(kind)["__kind__"] for kinds in _ALL for kind in kinds]
    assert names
    assert not [n for n in names if "drawn_" in n]
    with pytest.raises(SchemaError):
        lookup_kind("layout.drawn_symbol")
