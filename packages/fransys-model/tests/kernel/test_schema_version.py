"""The kernel stamps and checks the schema version a domain registered (model-0251)."""

import pytest
from canon_probes import make_item, make_owner, model_of

from fransys_model.kernel import (
    Draft,
    Origin,
    SchemaError,
    SchemaVersionError,
    freeze,
    from_data,
    register_schema_version,
    registry,
    to_data,
)
from fransys_model.vocab import SCHEMA_VERSION

_ORIGIN = Origin(file="t.py", line=1, note="")


def test_vocab_registers_its_version_and_freeze_stamps_it() -> None:
    """Fails if `vocab` stops registering, or `freeze` stamps a number of its own."""
    assert registry.registered_schema_version() == SCHEMA_VERSION
    assert freeze(Draft()).schema_version == SCHEMA_VERSION


def test_freeze_stamps_the_registered_number_not_a_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if the kernel keeps a number of its own: a registered +1 reaches model and data."""
    base = freeze(Draft())
    monkeypatch.setattr(registry, "_schema_version", SCHEMA_VERSION + 1)
    model = freeze(Draft())
    assert model.schema_version == SCHEMA_VERSION + 1
    assert model.digest != base.digest
    assert to_data(model)["schema_version"] == SCHEMA_VERSION + 1


def test_from_data_refuses_the_old_version_once_a_new_one_is_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if `from_data` compares to a number other than the registered one."""
    stored = dict(to_data(model_of(_ORIGIN, make_owner("1"), make_item("2"))))
    monkeypatch.setattr(registry, "_schema_version", SCHEMA_VERSION + 1)
    with pytest.raises(SchemaVersionError) as excinfo:
        from_data(stored)
    assert (excinfo.value.expected, excinfo.value.actual) == (SCHEMA_VERSION + 1, SCHEMA_VERSION)


def test_a_second_version_is_refused_and_the_same_one_is_a_no_op() -> None:
    """Fails if a domain may change the number after it registered one."""
    register_schema_version(SCHEMA_VERSION)
    with pytest.raises(SchemaError, match="already registered"):
        register_schema_version(SCHEMA_VERSION + 1)


@pytest.mark.parametrize("bad", [0, -1, True, "19"])
def test_a_version_must_be_an_int_of_one_or_more(bad: object) -> None:
    """Fails if a bool, a string or a number below 1 is accepted."""
    with pytest.raises(SchemaError, match="int of 1 or more"):
        register_schema_version(bad)  # ty: ignore[invalid-argument-type] -- the bad value is the test


def test_no_registered_version_stops_freeze_and_from_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fails if the kernel falls back to a number when no domain registered one."""
    monkeypatch.setattr(registry, "_schema_version", None)
    with pytest.raises(SchemaError, match="no schema version is registered"):
        freeze(Draft())
    with pytest.raises(SchemaError, match="no schema version is registered"):
        from_data({"schema_version": 1, "aliases": [], "tables": {}})
