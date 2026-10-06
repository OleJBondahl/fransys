"""`geometry.flow`: items landing one after another, each at the floor the last leaves (F4)."""

from fransys_layout.geometry import flow, snap_up


def test_flow_lands_each_item_at_the_previous_far_edge_plus_its_gap() -> None:
    """Heights 10, 20, 5 from floor 0 with gaps 2, 3, 4 land at 0, 12, 35."""
    heights = [10, 20, 5]
    got = flow(heights, floor=0, gaps=[2, 3, 4], far_edge=lambda h, top: top + h)
    assert got == [(0, 0), (1, 12), (2, 35)]


def test_flow_lets_the_landing_snap_through_far_edge() -> None:
    """A landing that snaps to the grid moves the next floor with it."""
    got = flow([5, 5], floor=3, gaps=[0, 0], far_edge=lambda h, top: snap_up(top) + h)
    assert got == [(0, 3), (1, 13)]


def test_flow_with_near_edge_stops_at_the_first_item_already_past_the_floor() -> None:
    """Only-down: an item at or past its floor ends the flow, later items are not moved."""
    tops = [0, 20, 5]
    got = flow(
        tops, floor=10, gaps=[0, 0, 0], far_edge=lambda _, top: top + 4, near_edge=lambda t: t
    )
    assert got == [(0, 10)]


def test_flow_near_edge_equal_to_the_floor_already_clears() -> None:
    """An item exactly at its floor is not moved: the flow ends before it."""
    got = flow([10], floor=10, gaps=[0], far_edge=lambda _, top: top + 4, near_edge=lambda t: t)
    assert got == []
