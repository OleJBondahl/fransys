"""WP5 acceptance skeletons: `kernel.model` (ROADMAP WP5, design/kernel-model.md 5.5)."""

from typing import Any

import pytest

from fransys_model.kernel import Draft, FreezeError, Id, Model, Origin, freeze


def _walk(obj: object) -> list[object]:
    """Every object reachable from `obj` through `frozendict`/tuple/dataclass fields."""
    seen: list[object] = [obj]
    if isinstance(obj, frozendict):
        for key, val in obj.items():
            seen.extend(_walk(key))
            seen.extend(_walk(val))
    elif isinstance(obj, tuple):
        for item in obj:
            seen.extend(_walk(item))
    elif hasattr(obj, "__dataclass_fields__"):
        for field_name in getattr(obj, "__dataclass_fields__", {}):
            seen.extend(_walk(getattr(obj, field_name)))
    return seen


def test_frozen_model_contains_no_mutable_object() -> None:
    """Walking a `Model` finds nothing mutable: no `list`, `dict`, `set`, `bytearray`."""
    model = freeze(Draft())
    mutable_types = (list, dict, set, bytearray)
    assert isinstance(model, Model)
    assert not any(isinstance(node, mutable_types) for node in _walk(model))


def test_the_walk_does_see_a_mutable_object_hidden_in_a_structure() -> None:
    """The check above is not vacuous: the same walk finds a list buried three levels deep."""
    hidden = frozendict({"a": (1, frozendict({"b": [2]}))})
    assert any(isinstance(node, list) for node in _walk(hidden))


def test_freeze_refuses_a_mutable_value_smuggled_into_a_record(
    thing_cls: Any, origin: Origin
) -> None:
    """Nothing mutable gets into a `Model`: it is refused at freeze, not walked for after."""
    smuggled: Any = ["x"]
    draft = Draft()
    draft.add(
        thing_cls(
            id=Id(kind="thing", value="1" * 32), key=("a",), name="p", ext=frozendict(x=smuggled)
        ),
        origin=origin,
    )
    with pytest.raises(FreezeError):
        freeze(draft)


def test_a_model_with_records_contains_no_mutable_object(thing_cls: Any, origin: Origin) -> None:
    """The walk reaches the records, their keys and `ext`, and the origins: none is mutable."""
    draft = Draft()
    first = Id(kind="thing", value="1" * 32)
    draft.add(thing_cls(id=first, key=("a", "b"), name="pump"), origin=origin)
    draft.alias(Id(kind="thing", value="2" * 32), first)
    model = freeze(draft)
    nodes = _walk(model)
    assert origin in nodes
    assert ("a", "b") in nodes
    assert not any(isinstance(node, (list, dict, set, bytearray)) for node in nodes)
