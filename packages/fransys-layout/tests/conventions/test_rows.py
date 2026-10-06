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
    keyed,
    not_,
    problems,
    rank_key,
    validate,
)

FACTS = {
    "big": Fact("big", "drawing", "", None, lambda s: s["n"] > 5),
    "red": Fact("red", "drawing", "", None, lambda s: s["c"] == "red"),
    "colour": Fact("colour", "drawing", "", ("red", "blue"), lambda s: s["c"]),
}


def _table(*rows: Row) -> Table:
    return Table("t", "first match", rows)


def test_first_match_takes_the_first_row_whose_condition_holds() -> None:
    """Two overlapping rows: the earlier wins, and swapping them changes the result."""
    a, b = Row("A", "big", "a"), Row("B", "red", "b")
    both = {"n": 9, "c": "red"}
    assert first_match(_table(a, b), both, FACTS) == a
    assert first_match(_table(b, a), both, FACTS) == b


def test_no_row_holding_gives_none() -> None:
    """A subject no row matches gets None."""
    assert first_match(_table(Row("A", "big", "a")), {"n": 1, "c": "x"}, FACTS) is None


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


def test_rank_key_is_one_digit_per_criterion_in_order() -> None:
    """0 where the fact reads the preferred value; a flipped preference flips the key."""
    order = Order("o", (Criterion("C1", "big", prefer=True), Criterion("C2", "colour", "red")))
    assert rank_key(order, {"n": 9, "c": "red"}, FACTS) == (0, 0)
    assert rank_key(order, {"n": 1, "c": "red"}, FACTS) == (1, 0)
    flipped = Order("o", (Criterion("C1", "big", prefer=False), Criterion("C2", "colour", "red")))
    assert rank_key(flipped, {"n": 9, "c": "red"}, FACTS) == (1, 0)


def test_keyed_builds_a_dict_from_value_atoms() -> None:
    """Rows of one fact's value atoms become a value-to-decision dict."""
    table = Table(
        "t", "keyed lookup", (Row("A", ("colour", "red"), 1), Row("B", ("colour", "blue"), 2))
    )
    assert keyed(table, "colour") == {"red": 1, "blue": 2}


def test_an_unknown_fact_name_fails_at_validate() -> None:
    """A planted unknown name is reported with its table and row id."""
    table = _table(Row("A", all_("big", "no_such_fact"), "a"))
    assert problems(table, FACTS) == ["t A: unknown fact 'no_such_fact'"]
    with pytest.raises(ValueError, match="unknown fact 'no_such_fact'"):
        validate(table, FACTS)


def test_a_misspelt_value_fails_at_validate() -> None:
    """A value outside the fact's set, in a row or a criterion, is reported."""
    row_table = _table(Row("A", ("colour", "gren"), "a"))
    assert problems(row_table, FACTS) == ["t A: value 'gren' is outside the set of fact 'colour'"]
    order = Order("o", (Criterion("C1", "colour", "gren"),))
    assert problems(order, FACTS) == ["o C1: value 'gren' is outside the set of fact 'colour'"]
    with pytest.raises(ValueError, match="gren"):
        validate(order, FACTS)


def test_a_value_atom_on_a_boolean_fact_fails() -> None:
    """A boolean fact has no value set, so a value atom on it is reported."""
    assert problems(_table(Row("A", ("big", "x"), "a")), FACTS) == [
        "t A: value 'x' is outside the set of fact 'big'"
    ]


def test_a_bad_policy_is_reported() -> None:
    """A table names one of the three hit policies."""
    assert problems(Table("t", "last match", ()), FACTS) == ["t: policy 'last match'"]


def test_a_valid_table_validates() -> None:
    """A clean table raises nothing."""
    validate(_table(Row("A", ("colour", "red"), "a")), FACTS)
