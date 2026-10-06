"""Records shared by the freeze tests: an owner, things that hold it, the cardinality kinds."""

import dataclasses
from typing import Any

import pytest

from fransys_model.kernel import (
    AuthoringKey,
    Draft,
    FreezeError,
    Id,
    Origin,
    SchemaError,
    Value,
    ValueTypeError,
    freeze,
    record,
    value,
)


@record(kind="freeze_owner_probe")
class Owner:
    """Something a holder refers to."""

    id: Id[Owner]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@value
class Holds:
    """A nested value holding one declared reference and one of any kind."""

    owner: Id[Owner]
    who: Id[Any] | None = None


@record(kind="freeze_holder_probe")
class Holder:
    """Holds an owner every way a record can: directly, nested, in a tuple, optional, `Value`."""

    id: Id[Holder]
    key: AuthoringKey
    owner: Id[Owner]
    nested: Holds
    many: tuple[Id[Owner], ...]
    maybe: Id[Owner] | None
    anything: Value = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="freeze_single_probe", singleton=True)
class Single:
    """At most one per model."""

    id: Id[Single]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@record(kind="freeze_unique_probe", subject="subject", unique=True)
class Facet:
    """At most one per subject."""

    id: Id[Facet]
    key: AuthoringKey
    subject: Id[Owner]
    ext: frozendict[str, Value] = frozendict()


@record(kind="freeze_pair_probe")
class Pair:
    """Refuses two equal owners in `__post_init__`, as `OrderHint` refuses `before == after`."""

    id: Id[Pair]
    key: AuthoringKey
    first: Id[Owner]
    second: Id[Owner]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse two equal owners."""
        if self.first == self.second:
            msg = "a pair needs two different owners"
            raise SchemaError(msg, kind="freeze_pair_probe")


@record(kind="freeze_refuser_probe")
class Refuser:
    """Refuses two equal owners with a `ValueTypeError`, not the `SchemaError` DESIGN names."""

    id: Id[Refuser]
    key: AuthoringKey
    first: Id[Owner]
    second: Id[Owner]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse two equal owners."""
        if self.first == self.second:
            msg = "a refuser needs two different owners"
            raise ValueTypeError(msg, path=("first",))


@record(kind="freeze_derived_probe")
class Derived:
    """Holds an id in a field that `__init__` does not take: it is derived from `owner`."""

    id: Id[Derived]
    key: AuthoringKey
    owner: Id[Owner]
    twin: Id[Owner] = dataclasses.field(init=False)
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Derive `twin`."""
        object.__setattr__(self, "twin", self.owner)


@record(kind="freeze_derived_before_probe")
class DerivedBefore:
    """Holds a derived `init=False` field BEFORE a plain reference field that follows it."""

    id: Id["DerivedBefore"]
    key: AuthoringKey
    twin: Id[Owner] = dataclasses.field(init=False)
    owner: Id[Owner]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Derive `twin`."""
        object.__setattr__(self, "twin", self.owner)


def owner_id(digit: str) -> Id[Any]:
    """An owner id made of one repeated hex digit."""
    return Id(kind="freeze_owner_probe", value=digit * 32)


def holder_id(digit: str) -> Id[Any]:
    """A holder id made of one repeated hex digit."""
    return Id(kind="freeze_holder_probe", value=digit * 32)


def make_owner(digit: str, **fields: Any) -> Any:
    """An owner with the id and key of `digit`."""
    return Owner(id=owner_id(digit), key=(digit,), **fields)


def make_holder(digit: str, **overrides: Any) -> Any:
    """A valid holder of owner `1`, with any field overridden."""
    fields: dict[str, Any] = {
        "id": holder_id(digit),
        "key": (digit,),
        "owner": owner_id("1"),
        "nested": Holds(owner=owner_id("1")),
        "many": (owner_id("1"),),
        "maybe": None,
    }
    return Holder(**{**fields, **overrides})


def make_facet(digit: str, subject: str) -> Any:
    """A facet `digit` for the owner `subject`."""
    return Facet(
        id=Id(kind="freeze_unique_probe", value=digit * 32), key=(digit,), subject=owner_id(subject)
    )


def draft_of(origin: Origin, *records: Any) -> Draft:
    """A draft holding `records`, all authored at `origin`."""
    draft = Draft()
    draft.extend(records, origin=origin)
    return draft


def errors_of(draft: Draft) -> tuple[Any, ...]:
    """Freeze `draft`, which must fail, and return the errors it collected."""
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    return excinfo.value.errors
