"""`series_tree.tree_lanes`: one recursion deals a series-parallel tree into lanes (SP4)."""

import pytest

from fransys_layout.core.series_tree import TreeLane, tree_holds, tree_lanes
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
def test_a_nested_series_stays_whole_in_its_lane_and_the_first_part_stays_home() -> None:
    """Catches the inner series flattened into the parallel, or a later part kept home."""
    tree = Series(("S1", Parallel(("S2", Series(("S3", "S4")))), "H1"))
    lanes = tree_lanes(tree, _ONE)
    assert lanes == (TreeLane(("S1", "S2", "H1")), TreeLane(("S3", "S4"), 0, "S2", "S2"))


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


_H = {"S1": 10, "B": 10, "A": 40, "C": 80, "D": 60, "E": 20, "F": 30}
_W = 5


@pytest.mark.rule("SERIES-PARALLEL")
def test_the_leaf_after_a_parallel_is_held_by_tallest_less_first() -> None:
    """Short first part 40, tall second 80: B below the parallel is held 80 - 40 = 40."""
    tree = Series(("S1", Parallel(("A", "C")), "B"))
    assert tree_holds(tree, _H, _W) == {"B": 40}


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_first_part_that_is_tallest_gives_no_hold() -> None:
    """Catches a hold of zero or of the other part's height recorded."""
    assert tree_holds(Series(("S1", Parallel(("C", "A")), "B")), _H, _W) == {}


@pytest.mark.rule("SERIES-PARALLEL")
def test_three_branches_hold_by_the_tallest_of_all() -> None:
    """Parts 40, 80, 60: B is held 80 - 40 = 40, not by the last part."""
    tree = Series(("S1", Parallel(("A", "C", "D")), "B"))
    assert tree_holds(tree, _H, _W) == {"B": 40}


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_parallel_with_nothing_after_it_in_its_lane_gives_no_hold() -> None:
    """A Parallel last in the tree has no follower; one ending a later branch has none either."""
    assert tree_holds(Series(("S1", Parallel(("A", "C")))), _H, _W) == {}
    tree = Series(("S1", Parallel(("A", Series(("E", Parallel(("A", "C"))))))))
    assert tree_holds(tree, _H, _W) == {}


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_nested_parallel_mid_way_down_the_home_branch_holds_its_follower() -> None:
    """Inner (E 20, F 30) between S1 and D in the home branch: D is held 30 - 20 = 10.

    The home branch is 10 + 30 + 60 + 2 * 5 = 110 against C = 80, so the outer gives no hold.
    """
    tree = Series((Parallel((Series(("S1", Parallel(("E", "F")), "D")), "C")), "B"))
    assert tree_holds(tree, _H, _W) == {"D": 10}


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_nested_parallel_ending_the_home_branch_adds_to_the_outer_hold() -> None:
    """Home branch Series(S1, Parallel(E 20, F 30)) = 10 + 5 + 30 = 45; C = 80, outer hold 35.

    The inner hold 30 - 20 = 10 also falls on B, the home lane's next leaf: 35 + 10 = 45.
    """
    tree = Series((Parallel((Series(("S1", Parallel(("E", "F")))), "C")), "B"))
    assert tree_holds(tree, _H, _W) == {"B": 45}


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_series_branch_with_more_cells_is_held_with_the_wires_between_its_cells() -> None:
    """First branch A (40) is one cell; the tallest is Series(E 20, F 30, E 20) of 3 cells.

    Its height is 70 + 2 * 5 = 80 as stack_lane builds it, so B is held 80 - 40 = 40 and stands
    wire_min (5) below the tallest branch's bottom.
    """
    tree = Series((Parallel(("A", Series(("E", "F", "E")))), "B"))
    assert tree_holds(tree, _H, _W) == {"B": 40}
