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
    same = _grid()  # two runs of one net are not collinear overlaps
    same.mark_wire("a", ((0, 8), (40, 8)))
    same.mark_wire("a", ((16, 8), (56, 8)))
    assert same.collinear() == 0


def test_columns_used_counts_nets_strictly_inside_the_gap_and_its_band() -> None:
    grid = _grid()
    for net, x in (("a", 40), ("b", 40), ("c", 48), ("d", 36), ("e", 64)):
        grid.mark_wire(net, ((x, 0), (x, 24)))
    assert grid.columns_used(Gap("g", 1, "L", "R", 36, 64, 1)) == 3
    assert grid.columns_used(Gap("g", 1, "L", "R", 36, 64, 1, 100, 200)) == 0
    assert grid.columns_used(Gap("g", 1, "L", "R", 36, 64, 1, 10, 200)) == 3


def test_cells_between_covers_both_ends_of_a_run() -> None:
    assert cells_between((8, 16), (32, 16), STEP) == [(1, 2), (2, 2), (3, 2), (4, 2)]


def test_a_wire_end_on_another_nets_run_is_a_touch_in_both_directions() -> None:
    """R439: a trunk ending on a foreign drop, and the drop passing a trunk end, both touch."""
    drop, trunk = ((24, 8), (24, 80)), ((24, 40), (64, 40))
    grid = _grid()
    grid.mark_wire("drop", drop)
    assert bool(grid.conflicts("trunk", trunk))
    grid = _grid()
    grid.mark_wire("trunk", trunk)
    assert bool(grid.conflicts("drop", drop))


def test_a_port_end_blocks_every_other_net_and_none_of_its_own() -> None:
    """R472: a pin's end is foreign to a wire of another net, whether or not it has a wire."""
    grid = _grid()
    grid.mark_end("x", (16, 16))
    assert grid.touched((2, 2), "n")
    assert grid.blocked((2, 2), "h", "n")
    assert not grid.touched((2, 2), "x")
    assert bool(grid.conflicts("n", ((0, 16), (40, 16))))
    assert not grid.conflicts("x", ((0, 16), (40, 16)))


def test_unmarking_a_wire_leaves_the_nets_other_wire_and_the_pin_ends() -> None:
    grid = _grid()
    grid.mark_end("x", (0, 40))
    grid.mark_wire("x", ((0, 8), (40, 8), (40, 24)))
    grid.mark_wire("x", ((0, 56), (24, 56)))
    grid.unmark_wire("x", ((0, 8), (40, 8), (40, 24)))
    keep = _grid()
    keep.mark_end("x", (0, 40))
    keep.mark_wire("x", ((0, 56), (24, 56)))
    assert grid.used == keep.used
    assert grid.ends == keep.ends
    assert {k: v for k, v in grid.runs.items() if v} == {k: v for k, v in keep.runs.items() if v}


def test_a_box_is_closed_on_its_far_edge_as_clearance_counts_it() -> None:
    """R535 R-C: a wire along the far edge is blocked, one cell outside is free; one predicate."""
    from fransys_layout.core.clearance import Keep, clear

    box = Box(16, 8, 16, 8)  # edges on grid lines: x 16..32, y 8..16
    grid = _grid()
    grid.mark_closed(box)
    assert grid.blocked((4, 1), "h", "n"), "far edge column"
    assert grid.blocked((2, 2), "v", "n"), "far edge row"
    assert grid.blocked((2, 1), "h", "n"), "near edge"
    assert not grid.blocked((5, 1), "h", "n"), "one cell outside"
    assert not grid.blocked((2, 3), "h", "n"), "one cell outside"
    keep = [Keep("", box, "footprint", "o")]
    for i in range(12):
        for j in range(8):
            point = Box(i * STEP, j * STEP, 0, 0)
            if clear(point, keep, {}):
                assert (i, j) in grid.hard, (i, j)


def test_unmarking_a_wire_keeps_another_wires_mark_on_a_shared_cell() -> None:
    """A cell shared with another net, and one doubled by the same net, loses one mark only."""
    grid = _grid()
    grid.mark_wire("x", ((0, 8), (40, 8)))
    grid.mark_wire("y", ((16, 0), (16, 24)))
    grid.mark_wire("x", ((8, 8), (24, 8)))
    grid.unmark_wire("x", ((0, 8), (40, 8)))
    assert grid.used[(2, 1)] == [("y", "v"), ("x", "h")]
    assert grid.used[(1, 1)] == [("x", "h")]
    assert (0, 1) not in grid.used


def test_a_hard_cell_is_open_to_a_wire_of_its_owner_only() -> None:
    grid = _grid()
    grid.mark_closed(Box(16, 8, 16, 8), frozenset({"S"}))
    assert grid.hard[(2, 1)] == {"S"}
    assert grid.hard[(4, 2)] == {"S"}, "far edges included"
    assert not grid.blocked((2, 1), "h", "n", frozenset({"S"}))
    assert grid.blocked((2, 1), "h", "n", frozenset({"T"}))
    assert grid.blocked((2, 1), "h", "n")


def test_present_counts_only_other_nets_on_the_same_axis() -> None:
    grid = _grid()
    grid.mark_wire("x", ((16, 8), (16, 40)))
    grid.mark_wire("y", ((16, 8), (16, 40)))
    assert grid.present((2, 2), "v", "n") == 2
    assert grid.present((2, 2), "v", "x") == 1
    assert grid.present((2, 2), "h", "n") == 0


def test_history_accumulates_and_outlives_remove_net() -> None:
    grid = _grid()
    grid.mark_wire("x", ((16, 8), (16, 40)))
    grid.add_history((2, 2), "v", 3)
    grid.add_history((2, 2), "v", 4)
    grid.remove_net("x")
    assert grid.history == {((2, 2), "v"): 7}
    assert grid.present((2, 2), "v", "n") == 0


def test_share_cost_lets_a_path_enter_a_cell_another_net_holds_on_its_axis() -> None:
    grid = _grid()
    grid.mark_wire("x", ((16, 8), (16, 40)))
    assert grid.blocked((2, 2), "v", "n")
    grid.share_cost = 5
    assert not grid.blocked((2, 2), "v", "n")
    assert grid.present((2, 2), "v", "n") == 1


def test_a_soft_round_prices_another_nets_end_and_keeps_a_port_end_blocked() -> None:
    grid = _grid()
    grid.mark_wire("x", ((16, 8), (16, 40)))
    grid.mark_end("port", (40, 8))
    assert grid.blocked((2, 1), "h", "n")
    grid.share_cost = 5
    assert not grid.blocked((2, 1), "h", "n")
    assert grid.contested((2, 1), "h", "n") == 1
    assert grid.blocked((5, 1), "h", "n")


def test_conflicts_list_a_corner_on_another_nets_wire_and_a_run_along_it() -> None:
    grid = _grid()
    grid.mark_wire("x", ((16, 8), (16, 40)))
    assert grid.conflicts("n", ((0, 24), (16, 24), (16, 56))) == [
        ((2, 3), "h"),
        ((2, 3), "v"),
        ((2, 3), "v"),
        ((2, 4), "v"),
        ((2, 5), "v"),
    ]
    assert not grid.conflicts("n", ((0, 24), (40, 24)))


def test_unmarking_a_wire_its_net_lost_to_remove_net_is_a_no_op() -> None:
    """A net with a rise and a link: the link's lift took the rise's marks, and the rise's lift reverses nothing."""
    grid = _grid()
    grid.mark_wire("x", ((0, 8), (40, 8), (40, 24)))
    grid.remove_net("x")
    grid.unmark_wire("x", ((0, 8), (40, 8), (40, 24)))
    assert not grid.used
    assert not grid.ends
