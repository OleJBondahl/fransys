"""ROUTE-FIX E: the occupancy grid is the page's one obstacle index; counts read its marks."""

from fransys_layout.core import Box
from fransys_layout.core.occupancy import Occupancy, cells_between
from fransys_layout.core.outputs import Gap

STEP = 8


def _grid() -> Occupancy:
    return Occupancy(12, 8, STEP)


def test_a_box_is_hard_for_every_net_and_axis() -> None:
    grid = _grid()
    grid.mark_box(Box(16, 8, 16, 8))
    assert grid.blocked((2, 1), "h", "n")
    assert grid.blocked((3, 1), "v", "n")
    assert not grid.blocked((4, 1), "h", "n")


def test_another_nets_wire_blocks_its_own_axis_and_is_crossed_on_the_other() -> None:
    grid = _grid()
    grid.mark_wire("x", ((16, 8), (16, 40)))
    assert grid.blocked((2, 2), "v", "n")
    assert not grid.blocked((2, 2), "h", "n")
    assert grid.crossing((2, 2), "h", "n") == 1
    assert grid.crossing((2, 2), "v", "n") == 0
    assert not grid.blocked((2, 2), "v", "x")
    assert grid.crossing((2, 2), "h", "x") == 0


def test_removing_a_net_clears_its_cells_and_its_runs() -> None:
    grid = _grid()
    grid.mark_wire("x", ((0, 8), (40, 8)))
    grid.mark_wire("y", ((8, 8), (32, 8)))
    assert grid.collinear() == 1
    grid.remove_net("y")
    assert grid.collinear() == 0
    assert grid.free(Box(0, 16, 8, 8))
    assert not grid.free(Box(0, 8, 8, 8))


def test_free_is_false_over_a_box_or_a_wire_cell_and_true_elsewhere() -> None:
    grid = _grid()
    grid.mark_box(Box(0, 0, 16, 16))
    grid.mark_wire("x", ((40, 0), (40, 24)))
    assert not grid.free(Box(8, 8, 16, 8))
    assert not grid.free(Box(32, 8, 16, 8))
    assert grid.free(Box(56, 8, 16, 8))


def test_collinear_counts_two_nets_overlapping_on_one_line_not_touching_ends() -> None:
    grid = _grid()
    grid.mark_wire("a", ((0, 8), (40, 8)))
    grid.mark_wire("b", ((40, 8), (72, 8)))
    assert grid.collinear() == 0
    grid.mark_wire("c", ((32, 8), (56, 8)))
    assert grid.collinear() == 2


def test_columns_used_counts_distinct_x_strictly_inside_the_gap_and_its_band() -> None:
    grid = _grid()
    for net, x in (("a", 40), ("b", 40), ("c", 48), ("d", 36), ("e", 64)):
        grid.mark_wire(net, ((x, 0), (x, 24)))
    assert grid.columns_used(Gap("g", 1, "L", "R", 36, 64, 1)) == 2
    assert grid.columns_used(Gap("g", 1, "L", "R", 36, 64, 1, 100, 200)) == 0
    assert grid.columns_used(Gap("g", 1, "L", "R", 36, 64, 1, 10, 200)) == 2


def test_cells_between_covers_both_ends_of_a_run() -> None:
    assert cells_between((8, 16), (32, 16), STEP) == [(1, 2), (2, 2), (3, 2), (4, 2)]


def test_collinear_ignores_two_runs_of_one_net() -> None:
    grid = _grid()
    grid.mark_wire("a", ((0, 8), (40, 8)))
    grid.mark_wire("a", ((16, 8), (56, 8)))
    assert grid.collinear() == 0


def test_a_wire_end_on_another_nets_run_is_a_touch_in_both_directions() -> None:
    """R439: a trunk ending on a foreign drop, and the drop passing a trunk end, both touch."""
    drop, trunk = ((24, 8), (24, 80)), ((24, 40), (64, 40))
    grid = _grid()
    grid.mark_wire("drop", drop)
    assert grid.touches("trunk", trunk)
    grid = _grid()
    grid.mark_wire("trunk", trunk)
    assert grid.touches("drop", drop)


def test_a_port_end_blocks_every_other_net_and_none_of_its_own() -> None:
    """R472: a pin's end is foreign to a wire of another net, whether or not it has a wire."""
    grid = _grid()
    grid.mark_end("x", (16, 16))
    assert grid.touched((2, 2), "n")
    assert grid.blocked((2, 2), "h", "n")
    assert not grid.touched((2, 2), "x")
    assert grid.touches("n", ((0, 16), (40, 16)))
    assert not grid.touches("x", ((0, 16), (40, 16)))
