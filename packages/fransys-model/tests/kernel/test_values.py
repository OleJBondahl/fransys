"""WP1 tests: `kernel.values` (ROADMAP WP1, design/kernel-records.md 5.1)."""

from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any

import pytest

from fransys_model.kernel import (
    AuthoringKey,
    FieldSpec,
    Id,
    Model,
    Value,
    ValueTypeError,
    check_value,
    record,
    register_enum,
    value,
)


def test_check_value_accepts_every_allowed_type_nested(label_cls: type) -> None:
    """Every design/kernel-records.md 5.1 leaf type is accepted, nested inside tuples, `frozendict`
    and values."""

    class Colour(Enum):
        RED = "red"

    register_enum(Colour)
    nested = frozendict(
        {
            "a": "x",
            "b": 1,
            "c": True,
            "d": None,
            "e": Decimal("1.5"),
            "f": Colour.RED,
            "g": Id(kind="thing", value="0" * 32),
            "h": (1, 2, 3),
            "i": frozendict({"nested": "value"}),
            "j": label_cls(text="hi"),
        }
    )
    check_value(nested)


@pytest.mark.parametrize(
    "bad_value",
    [
        1.5,
        [1, 2],
        {"a": 1},
        {1, 2},
        b"bytes",
        lambda: None,
    ],
)
def test_check_value_rejects_disallowed_top_level_types(bad_value: object) -> None:
    """`float`, `list`, `dict`, `set`, `bytes` and callables are rejected outright."""
    with pytest.raises(ValueTypeError):
        check_value(bad_value)


def test_check_value_rejects_unregistered_enum() -> None:
    """An `Enum` subclass never passed through `register_enum` is rejected."""

    class Unregistered(Enum):
        A = "a"

    with pytest.raises(ValueTypeError):
        check_value(Unregistered.A)


def test_check_value_rejects_frozendict_with_non_str_key() -> None:
    """`frozendict` is only allowed with `str` keys."""
    with pytest.raises(ValueTypeError):
        check_value(frozendict({1: "a"}))


def test_check_value_rejects_dict_hidden_three_levels_deep() -> None:
    """A plain `dict` nested inside tuples/`frozendict` is rejected, not just at the top level."""
    hidden = frozendict({"a": (1, frozendict({"b": {"c": "plain dict"}}))})
    with pytest.raises(ValueTypeError):
        check_value(hidden)


def test_check_value_error_carries_path_to_offending_value() -> None:
    """The raised error's `path` names where the disallowed value was found."""
    hidden = frozendict({"a": (1, frozendict({"b": 1.5}))})
    with pytest.raises(ValueTypeError) as excinfo:
        check_value(hidden)
    assert excinfo.value.path == ("a", "1", "b")


@pytest.mark.parametrize(
    "bad_value",
    [frozenset({1}), bytearray(b"x"), object(), range(3), 1 + 2j],
    ids=["frozenset", "bytearray", "object", "range", "complex"],
)
def test_check_value_rejects_other_types_outside_the_closed_set(bad_value: object) -> None:
    """Immutable-looking types are still rejected when they are not in kernel-records.md 5.1."""
    with pytest.raises(ValueTypeError):
        check_value(bad_value)


class _Name(str):  # noqa: SLOT000 -- deliberate fixture the kernel must reject
    pass


class _Pair(tuple):  # noqa: SLOT001 -- deliberate fixture the kernel must reject
    pass


class _Quantity(Decimal):
    pass


class _Table(frozendict):
    pass


_Point = namedtuple("_Point", "x y")  # noqa: PYI024 -- deliberate fixture the kernel must reject


@pytest.mark.parametrize(
    "subclassed",
    [_Name("x"), _Pair((1, 2)), _Quantity("1.5"), _Table({"a": 1}), _Point(1, 2)],
    ids=["str", "tuple", "Decimal", "frozendict", "namedtuple"],
)
def test_check_value_rejects_subclasses_of_allowed_types(subclassed: object) -> None:
    """A subclass could carry mutable state of its own, so only the exact types pass."""
    with pytest.raises(ValueTypeError):
        check_value(subclassed)


def test_check_value_rejects_unregistered_str_enum() -> None:
    """A `str`-mixin enum is an enum first: it must not slip through as a `str`."""

    class Mode(StrEnum):
        A = "a"

    with pytest.raises(ValueTypeError):
        check_value(Mode.A)


def test_check_value_accepts_registered_str_enum() -> None:
    """Registration is what admits an enum, whatever its mixin."""

    @register_enum
    class Mode(StrEnum):
        A = "a"

    check_value(Mode.A)


def test_check_value_rejects_mutable_dataclass() -> None:
    """A non-frozen dataclass is mutable, and was never declared with `@value`."""

    @dataclass
    class Mutable:
        text: str

    with pytest.raises(ValueTypeError):
        check_value(Mutable(text="x"))


def test_check_value_rejects_dataclass_class_object() -> None:
    """The class itself is not a value record, only its instances are."""
    with pytest.raises(ValueTypeError):
        check_value(Id)


def test_check_value_rejects_mutable_field_inside_a_value_record() -> None:
    """Annotations do not stop a list being passed, so the fields are checked at freeze."""

    @value
    class Holder:
        items: tuple[int, ...]

    smuggled: Any = [1]
    with pytest.raises(ValueTypeError) as excinfo:
        check_value(frozendict({"outer": Holder(items=smuggled)}))
    assert excinfo.value.path == ("outer", "items")


def test_check_value_error_path_covers_top_level_and_non_str_key() -> None:
    """The path is empty at the top level and stops at the mapping for a bad key."""
    with pytest.raises(ValueTypeError) as top:
        check_value([1])
    assert top.value.path == ()
    with pytest.raises(ValueTypeError) as keyed:
        check_value((1, frozendict({1: "a"})))
    assert keyed.value.path == ("1",)


def test_check_value_error_message_names_path_and_type() -> None:
    """A human reading the message sees where the value is and what it was."""
    with pytest.raises(ValueTypeError, match=r"a\.0: float is not an allowed value type"):
        check_value(frozendict({"a": (1.5,)}))


def test_check_value_rejects_registered_enum_with_non_leaf_member_value() -> None:
    """Enums serialise by value, so registering one must not let a float into the model."""

    @register_enum
    class Ratio(Enum):
        HALF = 0.5

    with pytest.raises(ValueTypeError, match=r"Ratio\.HALF has a float value"):
        check_value(Ratio.HALF)


@pytest.mark.parametrize(
    "decorator",
    [dataclass(frozen=True), dataclass(frozen=True, slots=True)],
    ids=["frozen-unslotted", "frozen-slotted"],
)
def test_check_value_rejects_a_dataclass_that_was_not_declared_with_value(decorator: Any) -> None:
    """Only `@value` classes are values: frozen and slotted is not enough without registration."""

    @decorator
    class Plain:
        text: str

    with pytest.raises(ValueTypeError, match="not an allowed value type"):
        check_value(Plain(text="x"))


def test_check_value_rejects_a_record_instance_used_as_a_value() -> None:
    """A table record is held by `Id`; nesting the record itself would duplicate its fact."""

    @record(kind="nested_record_probe")
    class Nested:
        id: Id[Nested]
        key: AuthoringKey
        ext: frozendict[str, Value] = frozendict()

    instance = Nested(id=Id(kind="nested_record_probe", value="0" * 32), key=("a",))
    with pytest.raises(ValueTypeError, match="not an allowed value type"):
        check_value((instance,))


@pytest.mark.parametrize("text", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_check_value_rejects_non_finite_decimal(text: str) -> None:
    """NaN is unequal to itself and sNaN raises on compare, so a quantity must be finite."""
    with pytest.raises(ValueTypeError, match=r"q\.0: Decimal .* is not finite") as excinfo:
        check_value(frozendict({"q": (Decimal(text),)}))
    assert excinfo.value.path == ("q", "0")


@pytest.mark.parametrize("text", ["0", "-0", "1.50", "-2.25", "1E+3"])
def test_check_value_accepts_finite_decimal(text: str) -> None:
    """Every finite `Decimal` is a quantity, whatever its exponent."""
    check_value(Decimal(text))


@pytest.mark.parametrize(
    "container",
    [
        Model(
            schema_version=1,
            tables=frozendict(),
            aliases=frozendict(),
            origins=frozendict(),
            hashes=frozendict(),
            digests=frozendict(),
            digest="",
        ),
        FieldSpec(name="a", ref_kind=None),
    ],
    ids=["Model", "FieldSpec"],
)
def test_check_value_rejects_the_kernel_containers_that_are_not_values(container: Any) -> None:
    """Decision 0012: immutable, but never something a record nests, so not a value class."""
    with pytest.raises(ValueTypeError, match="not an allowed value type"):
        check_value(container)


def test_check_value_accepts_an_int_at_the_bit_limit_and_refuses_one_past_it() -> None:
    """Canonical JSON must be able to write every int, and CPython will not write a huge one."""
    largest = 2**2048 - 1
    for accepted in (largest, -largest, True):
        check_value(accepted)
    for refused in (2**2048, -(2**2048)):
        with pytest.raises(ValueTypeError, match="2049 bits"):
            check_value(refused)


def test_check_value_error_for_a_huge_int_carries_its_path() -> None:
    """The offending int is found inside a mapping and a tuple."""
    with pytest.raises(ValueTypeError) as excinfo:
        check_value(frozendict({"a": (1, 2**3000)}))
    assert excinfo.value.path == ("a", "1")


def test_check_value_refuses_an_enum_member_with_a_huge_int_value() -> None:
    """An enum is written by value, so its int value has the same limit."""

    @register_enum
    class Huge(Enum):
        BIG = 2**3000

    with pytest.raises(ValueTypeError, match="bits"):
        check_value(Huge.BIG)


@pytest.mark.parametrize("text", ["1E+1000", "1E-1000", "0E+1000", "-1E+1000", "1.5E-1000"])
def test_check_value_accepts_a_decimal_at_the_exponent_limit(text: str) -> None:
    """Up to 1000 places from the point either way."""
    check_value(Decimal(text))


@pytest.mark.parametrize("text", ["1E+1001", "1E-1001", "0E-1001", "1E+999999999", "-1E-999999999"])
def test_check_value_refuses_a_decimal_beyond_the_exponent_limit(text: str) -> None:
    """`format(d, "f")` would spell it out digit by digit: a 12-byte input would fill memory."""
    with pytest.raises(ValueTypeError, match="exponent"):
        check_value(Decimal(text))


def test_check_value_refuses_a_huge_int_key_without_printing_it() -> None:
    """`repr` of a 5000-digit int raises `ValueError`; the refusal must be a `ValueTypeError`."""
    with pytest.raises(ValueTypeError, match="key is a int, not a str"):
        check_value(frozendict({10**5000: 1}))
