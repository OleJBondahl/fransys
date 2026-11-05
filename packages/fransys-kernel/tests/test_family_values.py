"""Tests: the family libraries' value classes are kernel values (decision model-0370).

Registered in `values.py` from the libraries' own `__all__`; stored by the one rule in
`encode`/`decode`: enums by member name, a union or base-class slot with its class tag, a
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

import pytest
from canon_probes import Shade, draft_of
from elecdef import Quantity, Unit

from fransys_kernel import (
    AuthoringKey,
    Id,
    Origin,
    Value,
    ValueTypeError,
    dumps,
    freeze,
    loads,
    make_id,
    record,
    to_data,
)
from fransys_kernel.errors import FreezeError
from fransys_kernel.registry import register_value_class
from fransys_kernel.values import check_value


@dataclass(frozen=True)
class Cat:
    name: str


@dataclass(frozen=True)
class Dog:
    name: str


@dataclass(frozen=True)
class Tags:
    shades: frozenset[Shade]


@dataclass(frozen=True)
class Carrier:
    pet: Cat | Dog | None


@dataclass(frozen=True)
class Unregistered:
    name: str


for _cls in (Cat, Dog, Tags, Carrier):
    register_value_class(_cls)


@record(kind="family_value_probe")
class Holder:
    """One slot per shape under test."""

    id: Id[Holder]
    key: AuthoringKey
    carrier: Carrier | None = None
    tags: Tags | None = None
    quantity: Quantity | None = None
    ext: frozendict[str, Value] = frozendict()


def _roundtrip(origin: Origin, **fields: Any) -> tuple[Holder, Any]:
    item = Holder(id=make_id(Holder, ("1",)), key=("1",), **fields)
    model = freeze(draft_of(origin, item))
    back = loads(dumps(model))
    return cast("Holder", back.tables["family_value_probe"][item.id]), cast("frozendict[str, Any]", to_data(model))["tables"]["family_value_probe"][0]


def test_a_family_dataclass_and_enum_are_values() -> None:
    check_value(Quantity(Decimal(1), Unit.A))


def test_a_dataclass_no_registry_knows_is_still_refused() -> None:
    """Fails if `check_value` accepts any dataclass, not only the registered ones."""
    with pytest.raises(ValueTypeError, match="Unregistered is not an allowed value type"):
        check_value(Unregistered("x"))


def test_a_frozenset_of_registered_enums_is_a_value_and_one_of_strings_is_too() -> None:
    check_value(frozenset(Shade))
    check_value(frozenset({"a"}))


def test_a_tuple_valued_enum_is_stored_by_member_name(origin: Origin) -> None:
    quantity = Quantity(Decimal("1.50"), Unit.A)
    back, data = _roundtrip(origin, quantity=quantity)
    assert data["quantity"] == {"unit": "A", "value": "1.5"}
    assert back.quantity == quantity


def test_a_frozenset_is_a_list_in_canonical_order(origin: Origin) -> None:
    """The list is sorted by its JSON text, whatever order the set iterates in."""
    back, data = _roundtrip(origin, tags=Tags(frozenset({Shade.RED, Shade.BLUE})))
    assert data["tags"] == {"shades": ("blue", "red")}
    assert back.tags == Tags(frozenset(Shade))


@pytest.mark.parametrize("pet", [Cat("x"), Dog("x"), None])
def test_a_union_decodes_to_the_arm_that_was_written(origin: Origin, pet: Cat | Dog | None) -> None:
    """`Cat` and `Dog` have one shape: reading the first arm would turn every `Dog` into a `Cat`."""
    back, data = _roundtrip(origin, carrier=Carrier(pet))
    assert back.carrier == Carrier(pet)
    if pet is not None:
        assert data["carrier"]["pet"]["$class"].endswith(type(pet).__name__)


def test_a_union_value_with_no_tag_or_an_unknown_one_is_refused(origin: Origin) -> None:
    item = Holder(id=make_id(Holder, ("1",)), key=("1",), carrier=Carrier(Cat("x")))
    text = dumps(freeze(draft_of(origin, item)))
    with pytest.raises(FreezeError, match="1 error") as unknown:
        loads(text.replace(".Cat", ".Cow"))
    assert "names no registered class" in str(unknown.value.errors[0])
    with pytest.raises(FreezeError, match="1 error") as untagged:
        loads(text.replace('"$class"', '"class"'))
    assert "unknown fields" in str(untagged.value.errors[0])
