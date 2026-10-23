"""`first_free` fills the lowest gap, from `start`."""

from fransys_kernel import first_free


def test_empty_gives_start() -> None:
    assert first_free(set()) == 1


def test_gap_is_filled_before_the_end() -> None:
    assert first_free({1, 2, 4}) == 3


def test_no_gap_gives_the_next_after_the_run() -> None:
    assert first_free({1, 2, 3}) == 4


def test_start_zero_and_numbers_below_start_ignored() -> None:
    assert first_free({0, 1}, start=0) == 2
    assert first_free({1, 2}, start=3) == 3
    assert first_free({5}, start=0) == 0
