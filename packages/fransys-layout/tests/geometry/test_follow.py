"""`geometry.follow`: a chain of states cut at a repeat (cleanup step 2, F6)."""

from fransys_layout.geometry import follow


def test_follow_stops_at_a_planted_cycle_and_leaves_the_repeat_out() -> None:
    """A ring ends at its last new state; a cycle that skips the start also ends."""
    ring = {"a": "b", "b": "c", "c": "a"}
    assert follow("a", ring.get) == ["a", "b", "c"]
    tail = {"a": "b", "b": "c", "c": "b"}
    assert follow("a", tail.get) == ["a", "b", "c"]
