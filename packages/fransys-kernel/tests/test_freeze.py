"""Tests: `kernel.freeze`. Aliases are in
test_freeze_aliases."""

from typing import Any

import pytest
from freeze_probes import (
    draft_of,
    errors_of,
    make_holder,
    make_owner,
    owner_id,
)

from fransys_kernel import (
    Draft,
    FreezeError,
    Id,
    Origin,
    SchemaError,
    ValueTypeError,
    describe,
    freeze,
)


def test_a_schema_error_names_the_record_and_a_value_error_too(origin: Origin) -> None:
    """Shape problems and legality problems both carry the record that holds them."""
    bad_shape = make_holder("2", owner="not-an-id")
    bad_value = make_holder("3", ext=frozendict({"x": 1.5}))
    errors = errors_of(draft_of(origin, bad_shape, bad_value, make_owner("1")))
    kinds = {type(error): error.record_id for error in errors}
    assert kinds == {SchemaError: bad_shape.id, ValueTypeError: bad_value.id}


def test_an_id_holding_an_illegal_value_does_not_reach_the_model(origin: Origin) -> None:
    """A record's own id is checked too: `bytes` in `Id.value` is a `ValueTypeError`."""
    smuggled: Any = b"bytes"
    bad = make_owner("1")
    object.__setattr__(bad, "id", Id(kind="freeze_owner_probe", value=smuggled))
    (error,) = errors_of(draft_of(origin, bad))
    assert isinstance(error, ValueTypeError)
    assert error.path == ("id", "value")


def test_a_freeze_error_renders_through_the_draft_it_came_from(origin: Origin) -> None:
    """`describe` turns the collected ids into the origins the author wrote."""
    bad = Origin(file="pumps.py", line=12, note="pump1")
    draft = Draft()
    draft.add(make_holder("2", owner=owner_id("9")), origin=bad)
    draft.add(make_owner("1"), origin=origin)
    with pytest.raises(FreezeError) as excinfo:
        freeze(draft)
    text = describe(excinfo.value, draft)
    assert "record: pumps.py:12 (2)" in text
    assert "field: owner" in text
