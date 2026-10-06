"""Records for the canonical-form tests: every annotation shape, both enum value types."""

import dataclasses
from decimal import Decimal
from enum import Enum
from typing import Any

from fransys_model.kernel import (
    AuthoringKey,
    Draft,
    Id,
    Origin,
    Value,
    freeze,
    record,
    register_enum,
    value,
)


@register_enum
class Shade(Enum):
    """A string-valued enum."""

    RED = "red"
    BLUE = "blue"


@register_enum
class Level(Enum):
    """An int-valued enum: it is written as a number, not a string."""

    LOW = 1
    HIGH = 2


@record(kind="canon_owner_probe")
class CanonOwner:
    """Something an item refers to."""

    id: Id[CanonOwner]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@value
class CanonDetail:
    """A nested value holding a `Decimal`, a reference and an optional enum."""

    amount: Decimal
    owner: Id[CanonOwner]
    shade: Shade | None = None


@record(kind="canon_item_probe")
class CanonItem:
    """One field of every annotation shape."""

    id: Id[CanonItem]
    key: AuthoringKey
    name: str
    count: int
    flag: bool
    amount: Decimal
    shade: Shade
    level: Level
    tags: tuple[str, ...]
    scores: frozendict[str, int]
    owner: Id[CanonOwner]
    maybe: Id[CanonOwner] | None
    details: tuple[CanonDetail, ...]
    note: str | None = None
    ext: frozendict[str, Value] = frozendict()


@record(kind="canon_derived_probe")
class CanonDerived:
    """Holds a field that `__init__` does not take: `shout` is derived from `name`."""

    id: Id[CanonDerived]
    key: AuthoringKey
    name: str
    shout: str = dataclasses.field(init=False)
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Derive `shout`."""
        object.__setattr__(self, "shout", self.name.upper())


def derived_id(digit: str) -> Id[Any]:
    """A derived-record id made of one repeated hex digit."""
    return Id(kind="canon_derived_probe", value=digit * 32)


def owner_id(digit: str) -> Id[Any]:
    """An owner id made of one repeated hex digit."""
    return Id(kind="canon_owner_probe", value=digit * 32)


def item_id(digit: str) -> Id[Any]:
    """An item id made of one repeated hex digit."""
    return Id(kind="canon_item_probe", value=digit * 32)


def make_owner(digit: str, **fields: Any) -> Any:
    """An owner with the id and key of `digit`."""
    return CanonOwner(id=owner_id(digit), key=(digit,), **fields)


def make_item(digit: str, **overrides: Any) -> Any:
    """A valid item that refers to owner `1`, with any field overridden."""
    fields: dict[str, Any] = {
        "id": item_id(digit),
        "key": (digit,),
        "name": "pump",
        "count": 3,
        "flag": True,
        "amount": Decimal("1.50"),
        "shade": Shade.RED,
        "level": Level.HIGH,
        "tags": ("a", "b"),
        "scores": frozendict({"x": 1}),
        "owner": owner_id("1"),
        "maybe": None,
        "details": (),
    }
    return CanonItem(**{**fields, **overrides})


def draft_of(origin: Origin, *records: Any) -> Draft:
    """A draft holding `records`, all authored at `origin`."""
    draft = Draft()
    draft.extend(records, origin=origin)
    return draft


def model_of(origin: Origin, *records: Any) -> Any:
    """Freeze `records` into a model."""
    return freeze(draft_of(origin, *records))


@record(kind="facet.canon_facet_probe")
class CanonFacet:
    """A record in the `facet` namespace."""

    id: Id[CanonFacet]
    key: AuthoringKey
    subject: Id[CanonOwner]
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.canon_layout_probe")
class CanonLayout:
    """A record in the `layout` namespace, which may refer down to `core` and `facet`."""

    id: Id[CanonLayout]
    key: AuthoringKey
    owner: Id[CanonOwner]
    x: int
    ext: frozendict[str, Value] = frozendict()
