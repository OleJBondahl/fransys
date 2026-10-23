"""The tag echo's text and a reference's digit count are pure functions of values (model-0342)."""

import pytest

from fransys_model.derive.drawing_text import reference_digits, tag_echo_text
from fransys_model.derive.order import echo_entry_key


def test_partners_print_once_in_set_page_column_order() -> None:
    entries = [(1, 2, 3, "p2.C"), (1, 1, 5, "p1.E"), (1, 2, 3, "p2.C"), (0, 9, 1, "p9.A")]
    assert tag_echo_text(entries) == "p9.A p1.E p2.C"


def test_the_key_is_set_rank_then_page_then_column_then_text() -> None:
    assert echo_entry_key((2, 3, 4, "x")) == (2, 3, 4, "x")
    assert min([(1, 1, 2, "b"), (1, 1, 2, "a")], key=echo_entry_key)[3] == "a"


@pytest.mark.parametrize(("count", "digits"), [(0, 2), (99, 2), (100, 3), (1000, 4)])
def test_digits_are_the_highest_numbers_with_a_floor_of_two(count: int, digits: int) -> None:
    assert reference_digits(count) == digits


def test_the_floor_can_be_raised() -> None:
    assert reference_digits(5, floor=3) == 3
