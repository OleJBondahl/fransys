"""Rows, orders and the evaluator: load-time checks, hit policies, and their can-fail cases."""

import pytest

from fransys_layout.conventions import (
    Criterion,
    Fact,
    Order,
    Row,
    Table,
    all_,
    any_,
    first_match,
    not_,
    problems,
    validate,
)

FACTS = {
    "big": Fact("big", "drawing", "", None, lambda s: s["n"] > 5),
    "red": Fact("red", "drawing", "", None, lambda s: s["c"] == "red"),
    "colour": Fact("colour", "drawing", "", ("red", "blue"), lambda s: s["c"]),
}


def _table(*rows: Row) -> Table:
    return Table("t", "first match", rows)


def test_all_any_not_and_value_atoms() -> None:
    """The combinators and the `(fact, value)` atom decide as named."""
    rows = (
        Row("A", all_("big", ("colour", "red")), "a"),
        Row("B", any_(not_("big"), ("colour", "blue")), "b"),
    )
    table = _table(*rows)
    a, b = rows
    assert first_match(table, {"n": 9, "c": "red"}, FACTS) == a
    assert first_match(table, {"n": 1, "c": "red"}, FACTS) == b
    assert first_match(table, {"n": 9, "c": "blue"}, FACTS) == b
    assert first_match(table, {"n": 9, "c": "green"}, FACTS) is None


def test_a_misspelt_value_fails_at_validate() -> None:
    """A value outside the fact's set, in a row or a criterion, is reported."""
    row_table = _table(Row("A", ("colour", "gren"), "a"))
    assert problems(row_table, FACTS) == ["t A: value 'gren' is outside the set of fact 'colour'"]
    order = Order("o", (Criterion("C1", "colour", "gren"),))
    assert problems(order, FACTS) == ["o C1: value 'gren' is outside the set of fact 'colour'"]
    with pytest.raises(ValueError, match="gren"):
        validate(order, FACTS)


def test_a_bad_policy_is_reported() -> None:
    """A table names one of the three hit policies."""
    assert problems(Table("t", "last match", ()), FACTS) == ["t: policy 'last match'"]
