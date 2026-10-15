"""Tests: `kernel.draft`."""

from typing import Any

import pytest

from fransys_kernel import (
    Draft,
    Id,
    Origin,
    SchemaError,
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
