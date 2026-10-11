"""`derive.pole_prefix`: the one printed prefix of each pole of a repeated symbol."""

from fransys_model.derive.drawing_text import pole_prefix


def test_a_single_pole_has_no_prefix() -> None:
    """One pole, or none, prints its ports bare."""
    assert pole_prefix(0, 1) == ""
    assert pole_prefix(0, 0) == ""


def test_the_first_pole_of_several_is_numbered_from_one() -> None:
    """Pole index 0 of a two-pole symbol is `1.`."""
    assert pole_prefix(0, 2) == "1."


def test_later_poles_follow_the_same_count() -> None:
    """Pole index 1 of a three-pole symbol is `2.`."""
    assert pole_prefix(1, 3) == "2."
