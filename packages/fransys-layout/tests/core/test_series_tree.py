"""`series_tree.tree_lanes`: one recursion deals a series-parallel tree into lanes (SP4)."""

import pytest

from fransys_layout.core.series_tree import TreeLane, tree_lanes
from fransys_layout.core.series_values import Parallel, Series

_ONE = {"S1": 4, "S2": 4, "S3": 4, "S4": 4, "H1": 4, "T1": 8, "T2": 8, "U1": 8}


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_series_is_one_lane_in_its_order() -> None:
    """Catches a series dealt out of order or split."""
    assert tree_lanes(Series(("S1", "S2", "H1")), _ONE) == (TreeLane(("S1", "S2", "H1")),)


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_parallel_keeps_its_first_part_and_puts_the_next_beside_it() -> None:
    """The redundancy case: T1 stays in lane 0 over U1, T2 is joined at T1."""
    lanes = tree_lanes(Series((Parallel(("T1", "T2")), "U1")), _ONE)
    assert lanes == (TreeLane(("T1", "U1")), TreeLane(("T2",), 0, "T1", "T1"))


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_nested_series_stays_whole_in_its_lane_and_the_tallest_part_stays_home() -> None:
    """Catches the inner series flattened into the parallel, or the shorter part kept home."""
    tree = Series(("S1", Parallel(("S2", Series(("S3", "S4")))), "H1"))
    lanes = tree_lanes(tree, _ONE)
    assert lanes == (TreeLane(("S1", "S3", "S4", "H1")), TreeLane(("S2",), 0, "S3", "S4"))


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_parallel_inside_a_joined_lane_joins_that_lane() -> None:
    """Catches a nested parallel joined to lane 0 instead of the lane that holds its span."""
    inner = Series(("S2", Parallel(("S3", "S4"))))
    tree = Series(("S1", Parallel((Series(("H1", "T1", "U1")), inner))))
    lanes = tree_lanes(tree, _ONE)
    assert lanes == (
        TreeLane(("S1", "H1", "T1", "U1")),
        TreeLane(("S2", "S3"), 0, "H1", "U1"),
        TreeLane(("S4",), 1, "S3", "S3"),
    )
