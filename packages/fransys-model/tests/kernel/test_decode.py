"""Tests: `from_data` and `loads` on input that is not what `dumps` wrote.

Each case takes a real `dumps` output, corrupts one thing with plain `json`, and reads it
back, so the corruption does not depend on the decoder under test.
"""

import json
from typing import Any

import pytest
from canon_probes import (
    make_item,
    make_owner,
    model_of,
)

from fransys_model.kernel import (
    SCHEMA_VERSION,
    FreezeError,
    Origin,
    SchemaError,
    SchemaVersionError,
    dumps,
    from_data,
    loads,
)
from fransys_model.kernel.encode import to_data

_ORIGIN = Origin(file="decode.py", line=1, note="")


def _base() -> dict[str, Any]:
    """Plain-`json` form of a small valid model: two owners and an item."""
    model = model_of(_ORIGIN, make_owner("1"), make_owner("4"), make_item("2"))
    return json.loads(dumps(model))


def _read(data: Any) -> Any:
    return loads(json.dumps(data))


def _item(data: dict[str, Any]) -> dict[str, Any]:
    return data["tables"]["canon_item_probe"][0]


def _errors_of(data: Any) -> tuple[Any, ...]:
    with pytest.raises(FreezeError) as excinfo:
        _read(data)
    return excinfo.value.errors


@pytest.mark.parametrize("text", ["[]", "3", '"x"', "null"], ids=["array", "int", "str", "null"])
def test_the_top_level_must_be_a_mapping(text: str) -> None:
    """Anything else has no record to attach a problem to, so it raises directly."""
    with pytest.raises(SchemaError, match="not a mapping") as excinfo:
        loads(text)
    assert excinfo.value.kind == "canonical"


def test_a_missing_schema_version_is_a_schema_error() -> None:
    """The version is the first thing looked for."""
    data = _base()
    del data["schema_version"]
    with pytest.raises(SchemaError, match="schema_version") as excinfo:
        _read(data)
    assert excinfo.value.kind == "canonical"


def test_a_stored_version_1_document_is_refused_naming_both_versions() -> None:
    """A document of an older schema version is not read, and the message says why.

    Fails if the version check in `from_data` goes, or if `SCHEMA_VERSION` returns to 1.
    """
    model = model_of(_ORIGIN, make_owner("1"), make_owner("4"), make_item("2"))
    stored = dict(to_data(model))
    stored["schema_version"] = 1
    with pytest.raises(SchemaVersionError) as excinfo:
        from_data(stored)
    assert (excinfo.value.expected, excinfo.value.actual) == (SCHEMA_VERSION, 1)
    assert f"version {SCHEMA_VERSION}" in str(excinfo.value)
    assert "not 1" in str(excinfo.value)


def test_an_extra_top_level_key_is_a_schema_error() -> None:
    """A future field bumps the version instead of sneaking in."""
    data = _base()
    data["surprise"] = 1
    with pytest.raises(SchemaError, match="surprise") as excinfo:
        _read(data)
    assert excinfo.value.kind == "canonical"


@pytest.mark.parametrize(
    "alias",
    [["only-one"], "not-a-pair", [1, 2], ["a:1", "b:2", "c:3"]],
    ids=["one", "str", "ints", "three"],
)
def test_an_alias_entry_must_be_a_pair_of_strings(alias: Any) -> None:
    """A malformed alias entry has no record either, so it raises directly."""
    data = _base()
    data["aliases"] = [alias]
    with pytest.raises(SchemaError, match="alias") as excinfo:
        _read(data)
    assert excinfo.value.kind == "canonical"


def test_an_unknown_field_is_reported_by_name() -> None:
    """A field the kind does not have is an error, not something to drop."""
    data = _base()
    _item(data)["surprise"] = 1
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert "unknown fields ['surprise']" in str(error)
    assert "missing fields []" in str(error)
    assert error.kind == "canon_item_probe"


@pytest.mark.parametrize(
    ("field", "broken", "phrase", "expected_kind"),
    [
        ("owner", "not-an-id", "field `owner`: 'not-an-id' is not `kind:value`", "id"),
        ("shade", "green", "field `shade`: 'green' is not a member of Shade", "canonical"),
        ("amount", "abc", "field `amount`: 'abc' is not a decimal number", "canonical"),
        ("level", 99, "field `level`: 99 is not a member of Level", "canonical"),
        ("level", True, "field `level`: True is not a member of Level", "canonical"),
        ("amount", " 1", "not in canonical form", "canonical"),
        ("amount", "1_0", "not in canonical form", "canonical"),
        ("amount", "١٢٣", "not in canonical form", "canonical"),
        ("amount", "1.50", "is not in canonical form, which is '1.5'", "canonical"),
        ("amount", "1E+3", "is not in canonical form, which is '1000'", "canonical"),
        ("amount", "-0", "is not in canonical form, which is '0'", "canonical"),
    ],
    ids=[
        "id-text",
        "enum-value",
        "decimal-text",
        "int-enum-value",
        "bool-for-int-enum",
        "decimal-space",
        "decimal-underscore",
        "decimal-arabic-digits",
        "decimal-trailing-zero",
        "decimal-exponent",
        "decimal-negative-zero",
    ],
)
def test_text_that_does_not_convert_is_collected_with_its_field(
    field: str, broken: Any, phrase: str, expected_kind: str
) -> None:
    """A bad id, an enum value that is not a member, a `Decimal` that does not parse.

    `expected_kind` pins decode.py:173's `kind=exc.kind`: `"id"` comes from `ids.parse_id`
    unchanged, everything else is decode's own `_KIND` (`"canonical"`).
    """
    data = _base()
    _item(data)[field] = broken
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert phrase in str(error)
    assert error.kind == expected_kind


@pytest.mark.parametrize(
    "ext",
    [
        {"x": {"$oops": 1}},
        {"x": {"$map": 1}},
        {"x": {"$map": {}, "$id": "a:1"}},
        {"x": {"a": 1}},
        {"x": {}},
    ],
    ids=["unknown-tag", "map-not-a-mapping", "two-tags", "untagged-mapping", "empty-mapping"],
)
def test_a_mapping_at_an_undeclared_position_must_be_exactly_one_known_tag(ext: Any) -> None:
    """Under `ext` a JSON object is `$map` or `$id`, nothing else."""
    data = _base()
    _item(data)["ext"] = ext
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert error.kind == "canonical"


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        ("{", "not valid JSON"),
        ('{"a": 1, "a": 2}', "duplicate"),
        ('{"schema_version": 1.5}', "number"),
        ('{"schema_version": NaN}', "not canonical"),
        ('{"schema_version": 1e3}', "number"),
    ],
    ids=["syntax", "duplicate-key", "float", "nan", "exponent"],
)
def test_json_that_is_not_canonical_is_a_schema_error_not_a_stdlib_error(
    text: str, phrase: str
) -> None:
    """Syntax errors, repeated keys, floats and NaN are refused as `SchemaError`."""
    with pytest.raises(SchemaError, match=phrase):
        loads(text)


def test_an_int_over_the_bit_limit_is_reported_by_freeze_with_its_field() -> None:
    """A long but readable int reaches `freeze()`, whose `check_value` names the field."""
    text = json.dumps(_base()).replace('"count": 3', '"count": ' + "1" * 700)
    with pytest.raises(FreezeError) as excinfo:
        loads(text)
    (error,) = excinfo.value.errors
    assert "count" in str(error)
    assert "bits" in str(error)


def test_deeply_nested_data_is_a_schema_error_not_a_recursion_error() -> None:
    """`from_data` takes data that never went through the JSON parser."""
    nested: Any = ()
    for _ in range(5000):
        nested = (nested,)
    data = _base()
    _item(data)["ext"] = {"x": nested}
    with pytest.raises(SchemaError, match="nested too deeply") as excinfo:
        from_data(data)
    assert excinfo.value.kind == "canonical"
