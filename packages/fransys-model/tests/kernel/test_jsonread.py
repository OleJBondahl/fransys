"""WP6 tests: `kernel.jsonread`, `read_json`'s own refusals (design/kernel-model.md 5.6).

`canonical.loads`/`decode.from_data` exercise `read_json` through the public API
(`test_decode.py`); this module exercises `read_json`'s own raise sites directly. Every one
of these six sites shares `kind="canonical"`, so no locator tells them apart from each other;
the input alone selects the scenario, and only `SchemaError` plus `.kind == "canonical"` are
asserted, never the message text (a mutation that only changes wording is an accepted prose
survivor, per decision model-0095; a mutation that disables a check still fails a test here,
since the input then either parses without raising or raises a different exception type).
"""

import pytest

from fransys_model.kernel import SchemaError
from fransys_model.kernel.jsonread import read_json


def test_invalid_syntax_is_a_schema_error_kind_canonical() -> None:
    """Not valid JSON at all."""
    with pytest.raises(SchemaError) as excinfo:
        read_json("{")
    assert excinfo.value.kind == "canonical"


def test_deeply_nested_json_is_a_schema_error_kind_canonical() -> None:
    """The parser's own recursion limit, not a bare `RecursionError`."""
    with pytest.raises(SchemaError) as excinfo:
        read_json("[" * 5000 + "]" * 5000)
    assert excinfo.value.kind == "canonical"


def test_a_duplicate_key_is_a_schema_error_kind_canonical() -> None:
    """Canonical form never repeats a key in one object."""
    with pytest.raises(SchemaError) as excinfo:
        read_json('{"a": 1, "a": 2}')
    assert excinfo.value.kind == "canonical"


def test_a_too_long_integer_is_a_schema_error_kind_canonical() -> None:
    """CPython's limit on the digits of an int, not a bare `ValueError`."""
    with pytest.raises(SchemaError) as excinfo:
        read_json("1" * 5000)
    assert excinfo.value.kind == "canonical"


@pytest.mark.parametrize("text", ["1.5", "1e3"], ids=["fraction", "exponent"])
def test_a_fraction_or_exponent_is_a_schema_error_kind_canonical(text: str) -> None:
    """Canonical JSON has no such numbers: a `Decimal` is written as a string."""
    with pytest.raises(SchemaError) as excinfo:
        read_json(text)
    assert excinfo.value.kind == "canonical"


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-Infinity"])
def test_a_json5_constant_is_a_schema_error_kind_canonical(text: str) -> None:
    """`NaN`/`Infinity` are not canonical JSON."""
    with pytest.raises(SchemaError) as excinfo:
        read_json(text)
    assert excinfo.value.kind == "canonical"
