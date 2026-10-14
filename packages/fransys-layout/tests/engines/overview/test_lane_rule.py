"""Which lane a box with no function group stands in, on plain values (LO4)."""

from fransys_layout.engines.overview.read.lane_rule import lane_rule

SHARED = 9


def test_a_grouped_box_keeps_its_lane_and_a_strip_with_no_group_takes_the_shared_one() -> None:
    """LO4: breaks if a group's lane is overwritten or a strip joins its neighbours' lane."""
    found = lane_rule(["g", "s"], {"g": 1, "s": None}, {"s"}, [("g", "s")], SHARED)
    assert found == {"g": 1, "s": SHARED}


def test_a_box_with_no_group_takes_the_lane_most_neighbours_stand_in() -> None:
    """LO4: breaks if the box takes the first neighbour's lane, or the lowest lane."""
    group = {"p": 2, "q": 2, "r": 0, "x": None}
    pairs = [("x", "p"), ("x", "q"), ("x", "r")]
    assert lane_rule(list("pqrx"), group, set(), pairs, SHARED)["x"] == 2


def test_a_tie_goes_to_the_earlier_lane() -> None:
    """LO4: breaks if a tie goes to the later lane."""
    group = {"p": 3, "r": 1, "x": None}
    assert lane_rule(list("prx"), group, set(), [("x", "p"), ("x", "r")], SHARED)["x"] == 1


def test_a_neighbour_in_the_shared_lane_does_not_vote_and_no_vote_means_shared() -> None:
    """LO4: breaks if a strip's shared lane pulls a box in, or a lone box gets a group lane."""
    group = {"s": None, "g": 0, "x": None, "y": None}
    pairs = [("x", "s"), ("x", "g"), ("y", "s")]
    found = lane_rule(list("sgxy"), group, {"s"}, pairs, SHARED)
    assert (found["x"], found["y"]) == (0, SHARED)


def test_a_lane_spreads_over_three_passes_and_no_further() -> None:
    """LO4: breaks if the passes are not three, or a box sees only the grouped boxes."""
    group = {"a": None, "b": None, "c": None, "d": None, "g": 0}
    pairs = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "g")]
    found = lane_rule(list("abcdg"), group, set(), pairs, SHARED)
    assert found["d"] == 0
    assert found["a"] == SHARED
