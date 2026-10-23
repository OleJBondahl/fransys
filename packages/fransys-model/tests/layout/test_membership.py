"""`layout.membership`: one holder, one subject, a valid frame cell, resolved ids."""

from dataclasses import replace

import pytest
from layout_examples import (
    PRODUCED_BY,
    drawing_set,
    drawn_function,
    function_id,
    group_node,
    page,
    sheet_format,
)

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Id,
    Origin,
    Record,
    SchemaError,
    dumps,
    freeze,
    loads,
    lookup_kind,
    make_id,
)
from fransys_model.layout import (
    SHEET_KINDS,
    FrameCell,
    LayoutSheet,
    Membership,
    SheetKind,
    Shown,
    layout_of,
)

_KEY = ("examples", "membership", "1")
_SHEET_KEY = ("examples", "sheet", "1")
_SHEET = LayoutSheet(
    id=make_id(LayoutSheet, _SHEET_KEY),
    key=_SHEET_KEY,
    sheet_kind=SheetKind.BLOCK,
    document="doc",
    number=1,
    sheet_format=None,
    produced_by=PRODUCED_BY,
)


def _membership(
    *,
    on_page: bool,
    on_sheet: bool,
    shown: Shown | None = None,
    **subjects: bool,
) -> Membership:
    function, port, conductor, item = (
        subjects.get(name, False) for name in ("function", "port", "conductor", "item")
    )
    return Membership(
        id=make_id(Membership, _KEY),
        key=_KEY,
        page=page().id if on_page else None,
        sheet=_SHEET.id if on_sheet else None,
        function=function_id("c") if function else None,
        port=Id(kind="port", value="1" * 32) if port else None,
        conductor=Id(kind="conductor", value="2" * 32) if conductor else None,
        item=Id(kind="item", value="3" * 32) if item else None,
        rank=0,
        shown=shown,
        cell=FrameCell(column=3, row="B"),
        produced_by=PRODUCED_BY,
    )


def _freeze(*extra: Record):
    draft = Draft()
    base = (*drawn_function(), group_node(), sheet_format(), drawing_set(), page(), _SHEET)
    draft.extend((*base, *extra), origin=Origin(file="test_membership.py", line=1, note="fixture"))
    return freeze(draft)


@pytest.mark.parametrize("holder", ["page", "sheet"])
def test_a_membership_round_trips_with_either_holder(holder: str) -> None:
    """A page holder and a sheet holder both freeze and read back equal."""
    rec = _membership(
        on_page=holder == "page", on_sheet=holder == "sheet", function=True, port=False
    )
    model = _freeze(rec)
    assert loads(dumps(model)) == model
    assert lookup_kind("layout.membership") is Membership
    assert Membership in SHEET_KINDS


@pytest.mark.parametrize(("on_page", "on_sheet"), [(False, False), (True, True)])
def test_a_membership_has_exactly_one_holder(*, on_page: bool, on_sheet: bool) -> None:
    """Neither and both of page and sheet are refused, naming the record."""
    with pytest.raises(SchemaError, match="membership has exactly one of page and sheet"):
        _membership(on_page=on_page, on_sheet=on_sheet, function=True, port=False)


@pytest.mark.parametrize(("function", "port"), [(False, False), (True, True)])
def test_a_membership_has_exactly_one_subject(*, function: bool, port: bool) -> None:
    """Neither and two of function, port and conductor are refused."""
    with pytest.raises(SchemaError, match="exactly one of function, port, conductor and item"):
        _membership(on_page=True, on_sheet=False, function=function, port=port)


@pytest.mark.parametrize(("column", "row"), [(0, "A"), (-1, "A"), (1, "a"), (1, "AB"), (1, "")])
def test_a_frame_cell_refuses_a_bad_column_or_row(column: int, row: str) -> None:
    with pytest.raises(SchemaError, match="frame cell"):
        FrameCell(column=column, row=row)


def test_a_membership_with_a_missing_holder_or_subject_is_refused_by_freeze() -> None:
    """The ids resolve at freeze: a dangling sheet or function is a FreezeError."""
    ok = _membership(on_page=False, on_sheet=True, function=True, port=False)
    with pytest.raises(FreezeError):
        _freeze(replace(ok, sheet=Id(kind="layout.sheet", value="9" * 32)))
    with pytest.raises(FreezeError):
        _freeze(replace(ok, function=function_id("z")))


def test_a_conductor_only_subject_is_accepted() -> None:
    """A conductor end is a subject by its conductor id alone."""
    rec = _membership(on_page=True, on_sheet=False, function=False, port=False, conductor=True)
    assert rec.conductor is not None
    assert rec.function is None
    assert rec.port is None


def test_a_port_and_conductor_subject_is_refused() -> None:
    """Two subjects, port and conductor, raise the exactly-one error."""
    with pytest.raises(
        SchemaError, match="a membership has exactly one of function, port, conductor and item"
    ):
        _membership(on_page=True, on_sheet=False, function=False, port=True, conductor=True)


def test_an_item_only_subject_is_accepted() -> None:
    """A unit outline or a connector box is a subject by its item id alone."""
    rec = _membership(on_page=True, on_sheet=False, function=False, port=False, item=True)
    assert rec.item is not None
    assert (rec.function, rec.port, rec.conductor) == (None, None, None)


@pytest.mark.parametrize("other", ["function", "port", "conductor"])
def test_an_item_with_another_subject_is_refused(other: str) -> None:
    """An item beside any other subject is two subjects."""
    subjects: dict[str, bool] = {"function": False, "port": False, other: True}
    with pytest.raises(SchemaError, match="exactly one of function, port, conductor and item"):
        _membership(on_page=True, on_sheet=False, item=True, **subjects)  # ty: ignore[invalid-argument-type] - ty widens **dict[str, bool] against the Shown parameter


@pytest.mark.parametrize("shown", [None, Shown.DRAWN, Shown.REFERENCE])
def test_shown_and_rank_are_kept(shown: Shown | None) -> None:
    """`shown` is as set, drawn, reference or None; `rank` is the reading order."""
    rec = _membership(on_page=True, on_sheet=False, function=False, port=True, shown=shown)
    assert rec.shown is shown
    assert rec.rank == 0


def test_a_membership_of_a_unit_outline_item_freezes_and_round_trips() -> None:
    """R196(b): the item subject (a unit outline) resolves at freeze and reads back equal."""
    item_id = drawn_function()[0].id
    rec = replace(
        _membership(on_page=True, on_sheet=False, function=True), function=None, item=item_id
    )
    model = _freeze(rec)
    assert loads(dumps(model)) == model
    assert layout_of(model, Membership)[rec.id].item == item_id
