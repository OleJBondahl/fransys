"""The key rule of columns.md 6.2: a replica column sorts right after the column it serves."""

from fransys_layout.stages import replica_key

PARENT = ("cab", "rung-a")
BEFORE = ("cab", "rung-0")
AFTER = ("cab", "rung-b")
LONGER_AFTER = ("cab", "rung-a-2")  # a sibling whose last element merely starts like PARENT's


def test_a_replica_key_is_the_served_key_plus_terminal_and_the_terminal_key() -> None:
    assert replica_key(PARENT, ("x1", "t-3")) == ("cab", "rung-a", "terminal", "x1", "t-3")


def test_replica_columns_sort_directly_after_the_column_they_belong_to() -> None:
    """Nothing sorts between a column and its replicas; the next sibling comes after them."""
    replicas = [replica_key(PARENT, ("x1", name)) for name in ("t-9", "t-1")]
    everything = [AFTER, LONGER_AFTER, PARENT, *replicas, BEFORE]
    ordered = sorted(everything)
    assert ordered[0] == BEFORE
    assert ordered[1] == PARENT
    assert set(ordered[2:-2]) == set(replicas)
    assert ordered[-2:] == [LONGER_AFTER, AFTER] or ordered[-2:] == [AFTER, LONGER_AFTER]
    assert all(key[: len(PARENT)] == PARENT for key in ordered[1:-2])
