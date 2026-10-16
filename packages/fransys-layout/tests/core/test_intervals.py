"""intervals.levels: overlapping spans take distinct levels, the earlier in order lower."""

from fransys_layout.core.intervals import levels


def test_disjoint_spans_share_level_zero() -> None:
    assert levels([(0, 4), (6, 9), (11, 12)], [0, 1, 2]) == (0, 0, 0)


def test_touching_ends_overlap_and_take_two_levels() -> None:
    assert levels([(0, 5), (5, 9)], [0, 1]) == (0, 1)


def test_a_span_takes_one_above_the_highest_overlapping_earlier_span() -> None:
    spans = [(0, 10), (2, 4), (3, 12)]
    assert levels(spans, [0, 1, 2]) == (0, 1, 2)
    assert levels(spans, [1, 2, 0]) == (2, 0, 1)


def test_the_order_decides_which_of_two_overlapping_spans_lies_lower() -> None:
    assert levels([(0, 8), (4, 12)], [1, 0]) == (1, 0)


def test_a_chain_uses_as_many_levels_as_its_deepest_overlap() -> None:
    """a-b and b-c overlap, a-c do not: two levels when b comes first."""
    assert levels([(0, 4), (3, 8), (7, 12)], [1, 0, 2]) == (1, 0, 1)
