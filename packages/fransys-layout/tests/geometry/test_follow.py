"""`geometry.follow`: a chain of states cut at a repeat (cleanup step 2, F6)."""

from fransys_layout.geometry import follow


def test_follow_walks_to_the_end_of_a_chain() -> None:
    """The start comes first and the walk stops where `step` gives `None`."""
    nxt = {"a": "b", "b": "c"}
    assert follow("a", nxt.get) == ["a", "b", "c"]
    assert follow("c", nxt.get) == ["c"]


def test_follow_stops_at_a_planted_cycle_and_leaves_the_repeat_out() -> None:
    """A ring ends at its last new state; a cycle that skips the start also ends."""
    ring = {"a": "b", "b": "c", "c": "a"}
    assert follow("a", ring.get) == ["a", "b", "c"]
    tail = {"a": "b", "b": "c", "c": "b"}
    assert follow("a", tail.get) == ["a", "b", "c"]


def test_follow_cuts_on_the_key_not_the_state() -> None:
    """Two states with one key count as a repeat; the first one is kept."""
    nxt = {(1, "x"): (2, "y"), (2, "y"): (1, "z"), (1, "z"): (3, "w")}
    assert follow((1, "x"), nxt.get, key=lambda state: state[0]) == [(1, "x"), (2, "y")]
