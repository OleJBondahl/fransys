"""The key rule of columns.md 6.2: a replica column sorts right after the column it serves."""

from fransys_layout.stages import replica_key

PARENT = ("cab", "rung-a")
BEFORE = ("cab", "rung-0")
AFTER = ("cab", "rung-b")
LONGER_AFTER = ("cab", "rung-a-2")  # a sibling whose last element merely starts like PARENT's


def test_a_replica_key_is_the_served_key_plus_terminal_and_the_terminal_key() -> None:
    assert replica_key(PARENT, ("x1", "t-3")) == ("cab", "rung-a", "terminal", "x1", "t-3")
