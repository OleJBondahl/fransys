"""The one leaf-to-root walk over a parent relation (REVIEW-M M6); every parent chain asks it."""

lazy from collections.abc import Callable, Iterator


def parent_chain[K](parent_of: Callable[[K], K | None], start: K | None) -> Iterator[K]:
    """`start`, then its parent, then that parent's parent, ... leaf first, up to a root.

    Ends at a root (`parent_of` gives `None`) or just before a node already yielded: a parent
    cycle ends the walk, every node is yielded once, and the repeated node is not yielded
    again. A `start` of `None` yields nothing. `start` is yielded before `parent_of` is asked
    about it, so a `start` `parent_of` does not know is still yielded, and `parent_of`
    decides what asking about it does (`nodes[start].parent` raises `KeyError` as the walk
    is advanced past it). The walk is lazy: a caller that stops early never asks about the
    nodes beyond.
    """
    seen: set[K] = set()
    node = start
    while node is not None and node not in seen:
        seen.add(node)
        yield node
        node = parent_of(node)
