"""`sorted_pair` is the one home of the order-independent pair key."""

from fransys_author._keys import sorted_pair


def test_sorted_pair_is_order_independent():
    a, b = ("x", "1"), ("a", "2")
    assert sorted_pair(a, b) == sorted_pair(b, a) == [b, a]
