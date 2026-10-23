"""The lanes of one series-parallel tree (SERIES-PARALLEL SP4): one recursion over its parts.

A Series stacks its parts in one lane, in order. A Parallel keeps its first part in the lane it
stands in, whatever its height, and gives each other part a lane of its own, in the given order,
joined at the first and the last leaf of that first part. A part's height is the sum of a Series
(with the wire between its parts) and the tallest of a Parallel, from the leaf heights the caller
measures once.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .series_values import Parallel, Series

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .series_values import SeriesPart


@dataclass(frozen=True, slots=True)
class TreeLane:
    """Leaves head to foot; a joined lane names its lane and the first and last leaf it spans."""

    leaves: tuple[str, ...]
    parent: int | None = None
    head: str | None = None
    foot: str | None = None


type Dealt = tuple[tuple[str, ...], tuple[TreeLane, ...]]


def anchor_signs(series: Iterable[Series]) -> dict[str, int]:
    """Each anchored series' end leaf and its side: plus at a head, minus at a tail (FLOW-DOWN)."""
    return {
        leaves_of(s)[0 if s.anchor == "head" else -1]: 1 if s.anchor == "head" else -1
        for s in series
        if s.anchor
    }


def tree_lanes(tree: Series, height: Mapping[str, int]) -> tuple[TreeLane, ...]:
    """Lane 0 holds the tree's first path; every other lane is joined to an earlier one."""
    own, rest = _lane(tree, height, 0, 1)
    return (TreeLane(own), *rest)


def leaves_of(part: SeriesPart) -> tuple[str, ...]:
    """Every leaf of `part`, in tree order."""
    if isinstance(part, str):
        return (part,)
    return tuple(leaf for p in part.parts for leaf in leaves_of(p))


def has_parallel(part: SeriesPart) -> bool:
    """Whether a Parallel stands anywhere in `part`."""
    if isinstance(part, str):
        return False
    return isinstance(part, Parallel) or any(has_parallel(p) for p in part.parts)


def part_height(part: SeriesPart, height: Mapping[str, int], wire_min: int) -> int:
    """A leaf's height, a Series' sum plus `wire_min` between its parts, a Parallel's tallest."""
    if isinstance(part, str):
        return height[part]
    found = [part_height(p, height, wire_min) for p in part.parts]
    if isinstance(part, Series):
        return sum(found) + wire_min * (len(found) - 1)
    return max(found)


def tree_holds(tree: Series, height: Mapping[str, int], wire_min: int) -> dict[str, int]:
    """Leaf -> how far the leaf after a Parallel sits below it: the tallest part less the first.

    The leaf is the first one that follows the Parallel in the lane it stands in; a Parallel with
    nothing after it in its lane, and a Parallel as tall as its first part, give no entry.
    """
    return dict(_holds(tree, (height, wire_min), None))


def _holds(
    part: SeriesPart, sizes: tuple[Mapping[str, int], int], after: str | None
) -> Counter[str]:
    """The holds `part` puts on leaves; `after` is the leaf that follows it, if any."""
    if isinstance(part, str):
        return Counter[str]()
    if isinstance(part, Series):
        follow = [leaves_of(p)[0] for p in part.parts[1:]] + [after]
        return _total(_holds(p, sizes, n) for p, n in zip(part.parts, follow, strict=True))
    extra = part_height(part, *sizes) - part_height(part.parts[0], *sizes)
    own: Counter[str] = Counter()
    if after is not None and extra:
        own[after] = extra
    kept = (_holds(p, sizes, after if i == 0 else None) for i, p in enumerate(part.parts))
    return _total([own, *kept])


def _total(parts: Iterable[Counter[str]]) -> Counter[str]:
    total: Counter[str] = Counter()
    for found in parts:
        total += found
    return total


def _lane(part: SeriesPart, height: Mapping[str, int], at: int, index: int) -> Dealt:
    """The leaves `part` puts in lane `at`, and the lanes beside them, numbered from `index`."""
    if isinstance(part, str):
        return (part,), ()
    if isinstance(part, Parallel):
        return _parallel(part, height, at, index)
    leaves: tuple[str, ...] = ()
    lanes: tuple[TreeLane, ...] = ()
    for p in part.parts:
        own, beside = _lane(p, height, at, index + len(lanes))
        leaves, lanes = leaves + own, lanes + beside
    return leaves, lanes


def _parallel(part: Parallel, height: Mapping[str, int], at: int, index: int) -> Dealt:
    home: Dealt = _lane(part.parts[0], height, at, index)
    own, lanes = home[0], list(home[1])
    for p in part.parts[1:]:
        mine = index + len(lanes)
        found: Dealt = _lane(p, height, mine, mine + 1)
        lanes += [TreeLane(found[0], at, own[0], own[-1]), *found[1]]
    return own, tuple(lanes)
