"""Tests: the kernel's argument refusals (evolve, merge, alias, findings, JSON reading, origins)."""

from typing import Any

import pytest
from freeze_probes import draft_of, make_owner, owner_id

from fransys_kernel import (
    Finding,
    Id,
    Origin,
    SchemaError,
    Severity,
    evolve,
    freeze,
    merge,
    read_json,
    require_origin,
)

_BASE = Origin(file="base.py", line=1, note="")
_CALL = Origin(file="pass.py", line=9, note="numbering")


def _model() -> Any:
    return freeze(draft_of(_BASE, make_owner("1"), make_owner("2")))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"put": 5}, "put takes an iterable of records, not a int"),
        ({"put": (object(),)}, "is not a @record instance"),
        ({"remove": 5}, "remove takes an iterable of ids, not a int"),
        ({"remove": ("x",)}, "remove takes ids, not a str"),
    ],
)
def test_evolve_refuses_a_put_or_remove_that_is_not_an_iterable_of_the_right_thing(
    kwargs: dict[str, Any], message: str
) -> None:
    """Each wrong argument raises a `SchemaError` that says what was passed."""
    with pytest.raises(SchemaError, match=message):
        evolve(_model(), origin=_CALL, **kwargs)


def test_evolve_refuses_two_different_records_put_under_one_id() -> None:
    """Repeats of one record collapse, but the same id with other content is refused."""
    first, second = make_owner("3"), make_owner("3", ext={"a": 1})
    with pytest.raises(SchemaError, match="name one id twice"):
        evolve(_model(), put=(first, second), origin=_CALL)


def test_evolve_needs_an_origin_to_attribute_what_it_puts() -> None:
    """A put without an `Origin` is refused."""
    with pytest.raises(SchemaError, match="needs an origin"):
        evolve(_model(), put=(make_owner("3"),), origin=None)


def test_evolve_refuses_to_remove_an_id_no_record_holds() -> None:
    """Removing a missing id is a `SchemaError` naming that id."""
    with pytest.raises(SchemaError, match="no record with this id to remove"):
        evolve(_model(), remove=(owner_id("9"),))


def test_merge_refuses_a_part_that_is_neither_a_draft_nor_a_model() -> None:
    """`merge` names the type it was given."""
    with pytest.raises(SchemaError, match="not a str"):
        merge("nope")  # ty: ignore[invalid-argument-type] -- the refusal under test


def test_draft_alias_refuses_retiring_an_id_in_favour_of_itself_or_of_two_ids() -> None:
    """An alias needs a different id of one kind, and one retired id leads to one id."""
    draft = draft_of(_BASE, make_owner("1"), make_owner("2"))
    with pytest.raises(SchemaError, match="different id of the same kind"):
        draft.alias(owner_id("1"), owner_id("1"))
    draft.alias(owner_id("8"), owner_id("1"))
    with pytest.raises(SchemaError, match="two different ids"):
        draft.alias(owner_id("8"), owner_id("2"))


def test_finding_refuses_a_bad_code_and_a_subject_that_is_not_an_id() -> None:
    """The code must be `UPPER_SNAKE` and every subject an `Id`."""
    with pytest.raises(SchemaError, match="not UPPER_SNAKE"):
        Finding(code="lower", severity=Severity.ERROR, subjects=(), message="m")
    with pytest.raises(SchemaError, match="subject must be an Id"):
        Finding(code="OK_CODE", severity=Severity.ERROR, subjects=("x",), message="m")  # ty: ignore[invalid-argument-type] -- the refusal under test


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{", "not valid JSON"),
        ('{"a": 1, "a": 2}', "duplicate key in one object"),
        ("1" * 6000, "cannot be read"),
        ("[" * 100000, "nested too deeply"),
    ],
)
def test_read_json_refuses_text_that_is_not_canonical(text: str, message: str) -> None:
    """Malformed, repeated-key, oversized and over-nested text each raise `SchemaError`."""
    with pytest.raises(SchemaError, match=message):
        read_json(text)


def test_require_origin_refuses_an_id_with_no_origin() -> None:
    """A missing origin raises rather than returning a placeholder."""
    with pytest.raises(SchemaError, match="no origin is known"):
        require_origin({}, Id(kind="freeze_owner_probe", value="a" * 32))
