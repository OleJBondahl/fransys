"""WP4 tests: `kernel.findings` (ROADMAP WP4, design/kernel-model.md 5.8)."""

import dataclasses
from typing import Any

import pytest

from fransys_model.kernel import Finding, Id, SchemaError, Severity, check_value


def _mutate(obj, name: str, new_value: object) -> None:
    """Attribute assignment via an unannotated parameter, so `ty` won't statically reject it."""
    setattr(obj, name, new_value)


def _finding(code: str = "NET_UNREALISED", subjects: tuple[Id, ...] = ()) -> Finding:
    return Finding(
        code=code, severity=Severity.WARNING, subjects=subjects, message="net not physically joined"
    )


def test_finding_is_a_value_record() -> None:
    """`Finding` is a frozen `@value` record: no identity, no mutation after construction."""
    finding = _finding(subjects=(Id(kind="thing", value="0" * 32),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        _mutate(finding, "message", "changed")


def test_finding_passes_check_value() -> None:
    """`Severity` is a registered enum, so a `Finding` is an allowed value."""
    check_value(_finding(subjects=(Id(kind="thing", value="0" * 32),)))


def test_finding_stores_subjects_in_id_order() -> None:
    """The order a validator found the subjects in never shows: equal findings compare equal."""
    low = Id(kind="a", value="1")
    mid = Id(kind="a", value="2")
    high = Id(kind="b", value="0")
    shuffled = _finding(subjects=(high, low, mid))
    assert shuffled.subjects == (low, mid, high)
    assert shuffled == _finding(subjects=(mid, high, low))


@pytest.mark.parametrize("code", ["NET_UNREALISED", "A", "PLC_2_MODULE", "X9"])
def test_finding_accepts_an_upper_snake_code(code: str) -> None:
    """Codes are stable `UPPER_SNAKE` strings."""
    assert _finding(code=code).code == code


@pytest.mark.parametrize(
    "code",
    ["", "net_unrealised", "Net_Unrealised", "1ABC", "_ABC", "A-B", "A B", "NET.UNREALISED"],
    ids=["empty", "lower", "mixed", "digit-first", "underscore-first", "dash", "space", "dot"],
)
def test_finding_refuses_a_code_that_is_not_upper_snake(code: str) -> None:
    """A malformed code is structural, so it raises rather than becoming a finding."""
    with pytest.raises(SchemaError, match="not UPPER_SNAKE") as excinfo:
        _finding(code=code)
    assert excinfo.value.kind == "Finding"


def test_finding_stores_a_repeated_subject_once() -> None:
    """A repeat carries no meaning, so findings differing only by one compare equal."""
    subject = Id(kind="thing", value="0" * 32)
    assert _finding(subjects=(subject, subject)) == _finding(subjects=(subject,))


@pytest.mark.parametrize(
    "subjects",
    [("not-an-id",), (Id(kind="thing", value="0" * 32), "zzz"), "abc"],
    ids=["str", "mixed", "bare-str"],
)
def test_finding_refuses_a_subject_that_is_not_an_id(subjects: Any) -> None:
    """A stray value would pass `check_value` and then break `describe`, so it raises here."""
    with pytest.raises(SchemaError, match="must be an Id") as excinfo:
        _finding(subjects=subjects)
    assert excinfo.value.kind == "Finding"
