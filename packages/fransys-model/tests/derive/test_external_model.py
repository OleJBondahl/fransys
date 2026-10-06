"""Tests for `derive.external` and the `Item.external` field (external-items spec Y1, Y4).

The flag is a fact on one item; the derivation reads the `parent` chain, so the terminals of
an external strip are external without carrying it. `installed` is a separate fact.
"""

from typing import TYPE_CHECKING

import pytest

from fransys_model.derive import external
from fransys_model.kernel import Draft, Id, Origin, SchemaError, dumps, freeze, loads, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_ORIGIN = Origin(file="test_external_model.py", line=1, note="fixture")

# The records `_plant` builds: the strip, its two terminals and the plain item.
PLANT_RECORDS = 4


def _item(
    key: str, *, parent: Id[Item] | None = None, flag: bool = False, installed: bool = True
) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None,
        parent=parent,
        position=None,
        tag=key.upper(),
        description="an invented item",
        external=flag,
        installed=installed,
    )


def _model(*records: Item) -> Model:
    draft = Draft()
    for record in records:
        draft.add(record, origin=_ORIGIN)
    return freeze(draft)


def _plant(*, strip_external: bool) -> tuple[Model, dict[str, Id[Item]]]:
    """An X1 strip with terminals X1:1 and X1:2, and a plain item K1; the strip's flag varies."""
    strip = _item("x1", flag=strip_external)
    records = (
        strip,
        _item("x1-1", parent=strip.id),
        _item("x1-2", parent=strip.id),
        _item("k1"),
    )
    ids = {record.key[0]: record.id for record in records}
    return _model(*records), ids


def test_an_external_strip_and_its_terminals_are_external_a_plain_item_is_not() -> None:
    model, ids = _plant(strip_external=True)
    assert len(ids) == PLANT_RECORDS
    assert external(model, ids["x1"]) is True
    assert external(model, ids["x1-1"]) is True  # by the parent chain, without carrying the flag
    assert external(model, ids["x1-2"]) is True
    assert external(model, ids["k1"]) is False
    assert items(model)[ids["x1-1"]].external is False


def test_a_strip_that_is_not_external_makes_no_terminal_external() -> None:
    model, ids = _plant(strip_external=False)
    assert len(ids) == PLANT_RECORDS
    assert [external(model, item) for item in ids.values()] == [False] * len(ids)


def test_installed_and_external_are_independent() -> None:
    reserved = _item("r1", installed=False)
    supplied = _item("s1", flag=True)
    both = _item("b1", flag=True, installed=False)
    model = _model(reserved, supplied, both)
    assert external(model, reserved.id) is False
    assert external(model, supplied.id) is True
    assert external(model, both.id) is True
    assert items(model)[both.id].installed is False


def test_the_flag_survives_a_canonical_dumps_loads_round_trip() -> None:
    for strip_external in (True, False):
        model, ids = _plant(strip_external=strip_external)
        text = dumps(model)
        assert text.count('"external": ') == len(ids)  # one key per item record
        again = loads(text)
        assert again.digest == model.digest
        assert items(again)[ids["x1"]].external is strip_external
        assert external(again, ids["x1-1"]) is strip_external


def test_the_flag_changes_the_model_digest() -> None:
    flagged, _ = _plant(strip_external=True)
    plain, _ = _plant(strip_external=False)
    assert flagged.digest != plain.digest


def test_an_unknown_item_is_refused() -> None:
    model, _ = _plant(strip_external=True)
    with pytest.raises(SchemaError):
        external(model, make_id(Item, ("nope",)))


def test_a_parent_cycle_ends_the_walk_instead_of_looping() -> None:
    a_id, b_id = make_id(Item, ("a",)), make_id(Item, ("b",))
    model = _model(_item("a", parent=b_id), _item("b", parent=a_id))
    assert external(model, a_id) is False
