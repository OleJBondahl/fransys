"""WP4 tests: `kernel.errors` (ROADMAP WP4, design/kernel-model.md 5.8)."""

import pytest

from fransys_model.kernel import (
    FreezeError,
    Id,
    MergeConflict,
    ModelError,
    RefError,
    SchemaError,
    SchemaVersionError,
    ValueTypeError,
)


@pytest.mark.parametrize(
    "error_cls",
    [SchemaError, ValueTypeError, RefError, MergeConflict, FreezeError, SchemaVersionError],
)
def test_error_hierarchy_as_designed(error_cls: type[ModelError]) -> None:
    """Every structural error in design/kernel-model.md 5.8 inherits `ModelError`."""
    assert issubclass(error_cls, ModelError)


def test_freeze_error_aggregates() -> None:
    """`FreezeError` holds every error `freeze()` collected, not just the first."""
    first = SchemaError("bad schema", kind="thing")
    second = ValueTypeError("bad value", path=("name",))
    aggregate = FreezeError((first, second))
    assert aggregate.errors == (first, second)


def test_ref_error_names_the_record_that_holds_the_reference() -> None:
    """The holder, the field and the missing target are all kept on the error."""
    holder = Id(kind="thing", value="a" * 32)
    target = Id(kind="thing", value="b" * 32)
    error = RefError("dangling reference", record_id=holder, field="profile.owner", target=target)
    assert (error.record_id, error.field, error.target) == (holder, "profile.owner", target)
