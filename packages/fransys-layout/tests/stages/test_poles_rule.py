"""The pole rule of `resolve`: `poles_and_pairs` (layout-0026, layout-0106).

Every case is hand-made `(line, load)` name pairs in the order the vocab's `function_poles` gives
them; `read/functions.py` reads the model and passes these values.
"""

from fransys_layout.stages import PolePair
from fransys_layout.stages.resolve import poles_and_pairs


def test_a_pole_is_one_pair_with_the_line_end_first() -> None:
    assert poles_and_pairs([("A2", "A1")]) == (1, (PolePair(index=0, first="A2", second="A1"),))


def test_poles_that_share_a_port_are_one_pole_without_a_pair() -> None:
    assert poles_and_pairs([("A", "B"), ("B", "C")]) == (1, ())


def test_pairs_follow_the_order_given_not_the_names() -> None:
    assert poles_and_pairs([("9", "10"), ("13", "14")]) == (
        2,
        (
            PolePair(index=0, first="9", second="10"),
            PolePair(index=1, first="13", second="14"),
        ),
    )


def test_a_pair_keeps_its_place_among_poles_of_other_sizes() -> None:
    poles = [("A1", "A2"), ("A2", "A3"), ("B1", "B2")]
    assert poles_and_pairs(poles) == (2, (PolePair(index=1, first="B1", second="B2"),))


def test_no_poles_is_one_pole_and_no_pair() -> None:
    assert poles_and_pairs([]) == (1, ())
