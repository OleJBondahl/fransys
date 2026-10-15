"""Tests for `kernel.values`."""

from collections import namedtuple

import pytest

from fransys_kernel import (
    ValueTypeError,
    check_value,
)

_Point = namedtuple("_Point", "x y")  # noqa: PYI024 -- deliberate fixture the kernel must reject


def test_check_value_error_message_names_path_and_type() -> None:
    """A human reading the message sees where the value is and what it was."""
    with pytest.raises(ValueTypeError, match=r"a\.0: float is not an allowed value type"):
        check_value(frozendict({"a": (1.5,)}))


def test_check_value_refuses_a_huge_int_key_without_printing_it() -> None:
    """`repr` of a 5000-digit int raises `ValueError`; the refusal must be a `ValueTypeError`."""
    with pytest.raises(ValueTypeError, match="key is a int, not a str"):
        check_value(frozendict({10**5000: 1}))
