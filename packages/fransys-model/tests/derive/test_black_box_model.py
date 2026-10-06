"""Tests for `derive.black_box`: `is_black_box_item`, `drawing_set_is_replica_only`
(units spec U1), against a hand-built nested-unit black-box shape and a clean twin.
"""

import itertools
from typing import TYPE_CHECKING, Any

import pytest

from fransys_model.derive import drawing_set_is_replica_only, is_black_box_item
from fransys_model.kernel import Draft, Id, Origin, SchemaError, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Orientation,
    Page,
    PageRole,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.core import Function, Item, Unit, UnitRelease
from fransys_model.vocab.enums import FunctionKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Model

PRODUCED_BY = "test-engine 0.0.0"

# Placements on `ds_mixed`, asserted before the replica-only check runs on it.
MIXED_PLACEMENT_COUNT = 2

# Placements on `ds_pure`, asserted before the replica-only check runs on it (so the check is
# never confused with the vacuous "no placements at all" case `ds_empty` covers separately).
PURE_PLACEMENT_COUNT = 1


def _ids() -> Callable[[str], Id[Any]]:
    """A fresh id maker: distinct `kind`s may safely reuse the same numeric value."""
    counter = itertools.count(1)

    def make(kind: str) -> Id[Any]:
        return Id(kind=kind, value=f"{next(counter):032x}")

    return make


def _key(id_: Id[Any], *tail: str) -> tuple[str, ...]:
    return (str(id_.value)[:8], *tail)


def _release(name: str) -> UnitRelease:
    key = ("unit_release", name, "1", "1")
    return UnitRelease(
        id=make_id(UnitRelease, key), key=key, name=name, version=1, revision=1, interface="1"
    )


def _unit(new_id: Callable[[str], Id[Any]], *, name: str, parent: Id[Unit] | None) -> Unit:
    id_ = new_id("unit")
    return Unit(id=id_, key=_key(id_), release=_release(name).id, parent=parent)


def _item(new_id: Callable[[str], Id[Any]], *, designation: str, unit: Id[Unit] | None) -> Item:
    id_ = new_id("item")
    return Item(
        id=id_,
        key=_key(id_),
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="an invented item",
        unit=unit,
    )


def _function(new_id: Callable[[str], Id[Any]], *, item: Id[Item]) -> Function:
    id_ = new_id("function")
    return Function(
        id=id_, key=_key(id_), item=item, template=None, name="fn", kind=FunctionKind.GENERIC
    )


def _drawing_set(
    new_id: Callable[[str], Id[Any]], *, unit: Id[Unit] | None, number: int
) -> DrawingSet:
    id_ = new_id("layout.drawing_set")
    return DrawingSet(
        id=id_, key=_key(id_), location=None, unit=unit, number=number, produced_by=PRODUCED_BY
    )


def _page(new_id: Callable[[str], Id[Any]], *, drawing_set: Id[DrawingSet], number: int) -> Page:
    id_ = new_id("layout.page")
    return Page(
        id=id_,
        key=_key(id_),
        drawing_set=drawing_set,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by=PRODUCED_BY,
    )


def _placement(
    new_id: Callable[[str], Id[Any]], *, function: Id[Function], page: Id[Page]
) -> SymbolPlacement:
    id_ = new_id("layout.symbol_placement")
    return SymbolPlacement(
        id=id_,
        key=_key(id_),
        function=function,
        page=page,
        x=0,
        y=0,
        orientation=Orientation.R0,
        poles=1,
        symbol="generic",
        library_version="0.0.0",
        produced_by=PRODUCED_BY,
    )


def _model() -> tuple[Model, dict[str, Id[Any]]]:
    """`top` nests `child`; `child`'s boundary function is replicated on `top`'s own drawing
    set (the black-box shape) alongside `top`'s own home function (the clean twin), plus a
    replica-only set, an all-home set and an empty one.
    """
    new_id = _ids()
    origin = Origin(file="test_black_box_model.py", line=1, note="fixture")
    top = _unit(new_id, name="pump-cabinet", parent=None)
    child = _unit(new_id, name="relay-board", parent=top.id)
    boundary_item = _item(new_id, designation="B1", unit=child.id)
    home_item = _item(new_id, designation="K1", unit=top.id)
    loose_item = _item(new_id, designation="X1", unit=None)
    boundary_fn = _function(new_id, item=boundary_item.id)
    home_fn = _function(new_id, item=home_item.id)
    ds_mixed = _drawing_set(new_id, unit=top.id, number=1)
    ds_pure = _drawing_set(new_id, unit=top.id, number=2)
    ds_home_only = _drawing_set(new_id, unit=top.id, number=3)
    ds_empty = _drawing_set(new_id, unit=top.id, number=4)
    mixed_page = _page(new_id, drawing_set=ds_mixed.id, number=1)
    pure_page = _page(new_id, drawing_set=ds_pure.id, number=1)
    home_only_page = _page(new_id, drawing_set=ds_home_only.id, number=1)
    home_placement = _placement(new_id, function=home_fn.id, page=mixed_page.id)
    boundary_placement_mixed = _placement(new_id, function=boundary_fn.id, page=mixed_page.id)
    boundary_placement_pure = _placement(new_id, function=boundary_fn.id, page=pure_page.id)
    home_only_placement = _placement(new_id, function=home_fn.id, page=home_only_page.id)
    draft = Draft()
    for record in (
        _release("pump-cabinet"),
        _release("relay-board"),
        top,
        child,
        boundary_item,
        home_item,
        loose_item,
        boundary_fn,
        home_fn,
        ds_mixed,
        ds_pure,
        ds_home_only,
        ds_empty,
        mixed_page,
        pure_page,
        home_only_page,
        home_placement,
        boundary_placement_mixed,
        boundary_placement_pure,
        home_only_placement,
    ):
        draft.add(record, origin=origin)
    model = freeze(draft)
    ids = {
        "top": top.id,
        "boundary_item": boundary_item.id,
        "home_item": home_item.id,
        "loose_item": loose_item.id,
        "ds_mixed": ds_mixed.id,
        "ds_pure": ds_pure.id,
        "ds_home_only": ds_home_only.id,
        "ds_empty": ds_empty.id,
    }
    return model, ids


def test_a_boundary_items_replica_is_black_box_at_its_parents_drawing_set() -> None:
    """`boundary_item`'s own unit (`child`) differs from `top`: black-box content."""
    model, ids = _model()
    assert is_black_box_item(model, ids["boundary_item"], ids["top"]) is True


def test_a_home_item_is_not_black_box_at_its_own_units_drawing_set() -> None:
    """The clean twin: `home_item`'s own unit is `top`, the same as the drawing set's."""
    model, ids = _model()
    assert is_black_box_item(model, ids["home_item"], ids["top"]) is False


def test_an_item_with_no_unit_is_never_black_box() -> None:
    """`loose_item.unit is None`, so it is never black-box content, whatever the comparison."""
    model, ids = _model()
    assert is_black_box_item(model, ids["loose_item"], ids["top"]) is False
    assert is_black_box_item(model, ids["loose_item"], None) is False


def test_a_boundary_item_is_black_box_at_a_top_level_drawing_set_too() -> None:
    """A `unit=None` (top-level) drawing set holding a nested unit's boundary still counts."""
    model, ids = _model()
    assert is_black_box_item(model, ids["boundary_item"], None) is True


def test_an_unknown_item_raises() -> None:
    """The refusal every query gives for an identity id the model does not hold."""
    model, _ids = _model()
    bad = Id(kind="item", value="9" * 32)
    with pytest.raises(SchemaError) as excinfo:
        is_black_box_item(model, bad, None)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("item", bad)


def test_a_mixed_drawing_set_is_not_replica_only() -> None:
    """`ds_mixed` holds one home placement and one black-box replica: not replica-only."""
    model, ids = _model()
    on_mixed = [
        placement
        for placement in layout_of(model, SymbolPlacement).values()
        if layout_of(model, Page)[placement.page].drawing_set == ids["ds_mixed"]
    ]
    assert len(on_mixed) == MIXED_PLACEMENT_COUNT
    assert drawing_set_is_replica_only(model, ids["ds_mixed"]) is False


def test_a_drawing_set_of_only_black_box_replicas_is_replica_only() -> None:
    """`ds_pure` holds only `boundary_fn`'s replica: replica-only, and not merely empty."""
    model, ids = _model()
    on_pure = [
        placement
        for placement in layout_of(model, SymbolPlacement).values()
        if layout_of(model, Page)[placement.page].drawing_set == ids["ds_pure"]
    ]
    assert len(on_pure) == PURE_PLACEMENT_COUNT
    assert drawing_set_is_replica_only(model, ids["ds_pure"]) is True


def test_a_drawing_set_of_only_home_content_is_not_replica_only() -> None:
    """The clean twin at the whole-set level: `ds_home_only` holds no black-box content at all."""
    model, ids = _model()
    assert drawing_set_is_replica_only(model, ids["ds_home_only"]) is False


def test_an_empty_drawing_set_is_replica_only() -> None:
    """No placement at all: vacuously true, since it has no placement that is not black-box."""
    model, ids = _model()
    assert drawing_set_is_replica_only(model, ids["ds_empty"]) is True


def test_an_unknown_drawing_set_raises() -> None:
    """The same refusal, for a `layout.drawing_set` id the model does not hold."""
    model, _ids = _model()
    bad = Id(kind="layout.drawing_set", value="9" * 32)
    with pytest.raises(SchemaError) as excinfo:
        drawing_set_is_replica_only(model, bad)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("layout.drawing_set", bad)
