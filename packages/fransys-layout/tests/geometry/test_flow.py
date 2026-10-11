"""`geometry.flow`: items landing one after another, each at the floor the last leaves (F4)."""

from fransys_layout.geometry import flow


def test_flow_near_edge_equal_to_the_floor_already_clears() -> None:
    """An item exactly at its floor is not moved: the flow ends before it."""
    got = flow([10], floor=10, gaps=[0], far_edge=lambda _, top: top + 4, near_edge=lambda t: t)
    assert got == []
