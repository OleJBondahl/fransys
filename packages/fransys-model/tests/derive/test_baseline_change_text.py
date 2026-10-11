"""`change_identity` renders the three identity shapes of a `Change` bullet (reports-0004)."""

from fransys_model.derive.baseline import change_identity


def test_a_unit_is_its_instance_and_name() -> None:
    assert change_identity("units", ("u1", "Pump")) == "`u1` (Pump)"


def test_a_conductor_is_between_its_two_ends() -> None:
    assert change_identity("conductors", ("a", "b")) == "between `a` and `b`"


def test_a_mate_is_between_its_two_ends() -> None:
    assert change_identity("mates", ("a", "b")) == "between `a` and `b`"


def test_any_other_section_is_one_backticked_subject() -> None:
    assert change_identity("items", ("x",)) == "`x`"
