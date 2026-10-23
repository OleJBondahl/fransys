"""Tests: `kernel.draft`."""

from typing import Any

import pytest

from fransys_kernel import (
    Draft,
    Id,
    Origin,
    SchemaError,
    freeze,
)

_A = Id(kind="thing", value="a" * 32)
_B = Id(kind="thing", value="b" * 32)
_C = Id(kind="thing", value="c" * 32)


def test_add_refuses_an_id_that_is_not_an_id(thing_cls: Any, origin: Origin) -> None:
    """A stray `str` id must not leak an `AttributeError`."""
    with pytest.raises(SchemaError, match="id of its own kind") as excinfo:
        Draft().add(thing_cls(id="not-an-id", key=("a",), name="pump"), origin=origin)
    assert excinfo.value.kind == thing_cls.__qualname__


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (_A, _A),
        (_A, Id(kind="link", value="a" * 32)),
    ],
    ids=["same-id", "different-kind"],
)
def test_alias_refuses_a_retirement_that_makes_no_sense(old: Id[Any], new: Id[Any]) -> None:
    """An id retires in favour of a different id of its own kind."""
    with pytest.raises(SchemaError, match="different id of the same kind") as excinfo:
        Draft().alias(old, new)
    assert excinfo.value.kind == old.kind


def _thing(thing_cls: Any, letter: str, name: str = "pump") -> Any:
    return thing_cls(id=Id(kind="thing", value=letter * 32), key=(letter,), name=name)


def test_tables_is_the_layout_of_a_frozen_models_tables(thing_cls: Any, origin: Origin) -> None:
    """`tables()` lays records out as `kind -> id -> record`, in the order `freeze` gives."""
    draft = Draft()
    draft.extend([_thing(thing_cls, "b"), _thing(thing_cls, "a")], origin=origin)
    assert draft.tables() == freeze(draft).tables
    assert list(draft.tables()["thing"]) == [_A, _B]


def test_tables_is_a_snapshot_a_later_add_does_not_reach(thing_cls: Any, origin: Origin) -> None:
    """A record added after `tables()` is not in the snapshot taken before it."""
    draft = Draft()
    draft.add(_thing(thing_cls, "a"), origin=origin)
    snapshot = draft.tables()
    draft.add(_thing(thing_cls, "b"), origin=origin)
    assert list(snapshot["thing"]) == [_A]
    assert len(draft.tables()["thing"]) == 2


def test_tables_refuses_a_write_and_applies_no_alias(thing_cls: Any, origin: Origin) -> None:
    """The result cannot be mutated, and a retired id still holds its own record."""
    draft = Draft()
    draft.extend([_thing(thing_cls, "a"), _thing(thing_cls, "b")], origin=origin)
    draft.alias(_A, _B)
    snapshot = draft.tables()
    with pytest.raises(TypeError):
        snapshot["thing"][_C] = _thing(thing_cls, "c")  # ty: ignore[invalid-assignment] -- the refusal under test
    assert set(snapshot["thing"]) == {_A, _B}
