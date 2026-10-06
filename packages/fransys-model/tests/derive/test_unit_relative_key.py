"""FD2 tests: an item's designation identity is its key with its unit's own prefix dropped."""

import pytest

from fransys_model.derive.unit_relative_key import unit_relative_key
from fransys_model.kernel import Draft, Id, Model, Origin, Record, SchemaError, freeze, make_id
from fransys_model.vocab.core import Item, Unit, UnitRelease

_ORIGIN = Origin(file="test_unit_relative_key.py", line=1, note="hand-built")


def _model(records: list[Record]) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _release(name: str) -> UnitRelease:
    key = ("unit_release", name, "1", "1")
    return UnitRelease(
        id=make_id(UnitRelease, key), key=key, name=name, version=1, revision=1, interface="1"
    )


def _unit(prefix: tuple[str, ...], release: UnitRelease) -> Unit:
    key = (*prefix, "unit")
    return Unit(id=make_id(Unit, key), key=key, release=release.id, parent=None)


def _item(
    key: tuple[str, ...], *, unit: Id[Unit] | None = None, parent: Id[Item] | None = None
) -> Item:
    return Item(
        id=make_id(Item, key),
        key=key,
        part=None,
        parent=parent,
        position=None,
        tag=None,
        description="Invented",
        unit=unit,
    )


def test_an_item_with_no_unit_returns_its_own_key_unchanged() -> None:
    item = _item(("standalone", "k1"))
    model = _model([item])
    assert unit_relative_key(model, item.id) == ("standalone", "k1")


def test_an_item_under_a_units_scope_drops_the_units_own_prefix() -> None:
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    item = _item(("cab", "k1"), unit=unit.id)
    model = _model([release, unit, item])
    assert unit_relative_key(model, item.id) == ("k1",)


def test_an_item_nested_under_a_board_inside_the_unit_still_drops_only_the_units_prefix() -> None:
    release = _release("cab-release")
    unit = _unit(("cab",), release)
    board = _item(("cab", "brd"), unit=unit.id)
    item = _item(("cab", "brd", "k1"), unit=unit.id, parent=board.id)
    model = _model([release, unit, board, item])
    assert unit_relative_key(model, item.id) == ("brd", "k1")


def test_two_instances_of_one_release_give_the_same_key() -> None:
    """FD2's own acceptance: "key for key" (units spec U7)."""
    release = _release("shared-release")
    unit1 = _unit(("cab1",), release)
    unit2 = _unit(("cab2",), release)
    item1 = _item(("cab1", "k1"), unit=unit1.id)
    item2 = _item(("cab2", "k1"), unit=unit2.id)
    model = _model([release, unit1, unit2, item1, item2])
    assert unit_relative_key(model, item1.id) == unit_relative_key(model, item2.id) == ("k1",)


def test_an_unknown_item_raises_a_schema_error_naming_it() -> None:
    model = _model([])
    unknown = make_id(Item, ("nowhere",))
    with pytest.raises(SchemaError) as excinfo:
        unit_relative_key(model, unknown)
    assert excinfo.value.kind == "item"
    assert excinfo.value.record_id == unknown
