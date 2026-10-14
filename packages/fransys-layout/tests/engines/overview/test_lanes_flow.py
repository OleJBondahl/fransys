"""The lanes view's general stage search and cell stacking, on plain values (LO3, LO5, LO6)."""

from fransys_layout.engines.overview.lanes.flow import stack, stages


def test_the_stage_is_the_depth_over_the_flow_pairs_from_the_sources() -> None:
    """LO3: breaks if the depth follows all lines instead of the flow pairs a source reaches."""
    flow = [("a", "b"), ("b", "c"), ("c", "d")]
    lines = [*flow, ("a", "d")]
    assert stages(list("abcd"), flow, lines, ["a"], []) == {"a": 0, "b": 1, "c": 2, "d": 3}


def test_a_box_the_flow_misses_takes_the_shortest_depth_over_all_lines() -> None:
    """LO3: breaks if a box off the flow is left unstaged or staged by the longest line."""
    lines = [("a", "b"), ("b", "c"), ("a", "c"), ("c", "d")]
    assert stages(list("abcd"), [("a", "b")], lines, ["a"], []) == {"a": 0, "b": 1, "c": 1, "d": 2}


def test_the_last_boxes_take_the_deepest_stage_even_a_source() -> None:
    """LO3: breaks if a last box stays where the search put it, a source included."""
    flow = [("a", "b"), ("b", "c")]
    found = stages(list("abcd"), flow, flow, ["a"], ["a", "d"])
    assert found == {"a": 1, "b": 0, "c": 1, "d": 1}


def test_a_box_nothing_reaches_takes_stage_one() -> None:
    """LO3: breaks if an isolated box takes stage 0 or the deepest stage."""
    found = stages(list("abcz"), [("a", "b"), ("b", "c")], [("a", "b"), ("b", "c")], ["a"], [])
    assert found == {"a": 0, "b": 1, "c": 2, "z": 1}


def test_a_cell_stacks_its_boxes_by_the_key_then_the_order_given() -> None:
    """LO5: breaks if a cell ignores the key, loses a box, or breaks a tie other than by order."""
    cell_of = {"b": (0, 1), "a": (0, 1), "c": (1, 0)}
    same = {"a": 0, "b": 0, "c": 0}
    assert stack(["a", "b", "c"], cell_of, same) == {(0, 1): ["a", "b"], (1, 0): ["c"]}
    assert stack(["b", "a", "c"], cell_of, same)[0, 1] == ["b", "a"]
    assert stack(["a", "b", "c"], cell_of, {"a": 2, "b": 1, "c": 0})[0, 1] == ["b", "a"]
