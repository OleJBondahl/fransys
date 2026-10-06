"""Tests for `derive.release_order`: the one order of unit releases and history entries (FD4)."""

from fransys_model.derive import release_order


def test_the_pair_orders_numerically_within_a_version_and_across_versions() -> None:
    """`1.9 < 1.10 < 2.1`: a compare of the printed texts would put `"1.10"` before `"1.9"`."""
    assert release_order(1, 9) < release_order(1, 10) < release_order(2, 1)
    assert not release_order(1, 10) < release_order(1, 9)
    assert not release_order(2, 1) < release_order(1, 10)
    # examined: the text order really is the wrong one
    assert sorted(["1.9", "1.10"]) == ["1.10", "1.9"]


def test_sorting_on_the_key_gives_the_numeric_release_order() -> None:
    """`(2, 1), (1, 10), (1, 9)` sort to `(1, 9), (1, 10), (2, 1)` through the key."""
    releases = [(2, 1), (1, 10), (1, 9)]
    assert sorted(releases, key=lambda pair: release_order(*pair)) == [(1, 9), (1, 10), (2, 1)]


def test_the_order_is_a_pair_of_ints_not_text() -> None:
    """The key holds the two ints themselves, so no caller can compare printed text by it."""
    order = release_order(2, 10)
    assert order == (2, 10)
    assert all(type(part) is int for part in order)
