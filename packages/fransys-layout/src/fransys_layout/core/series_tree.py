"""The lanes of one series-parallel tree (SERIES-PARALLEL SP4): one recursion over its parts.

A Series stacks its parts in one lane, in order. A Parallel keeps its tallest part in the lane it
stands in, the first of equals, and gives each other part a lane of its own, in the given order,
joined at the first and the last leaf of that tallest part. A part's height is the sum of a
Series and the tallest of a Parallel, from the leaf heights the caller measures once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .series_values import Parallel, Series

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .series_values import SeriesPart


@dataclass(frozen=True, slots=True)
class TreeLane:
    """Leaves head to foot; a joined lane names its lane and the first and last leaf it spans."""

    leaves: tuple[str, ...]
    parent: int | None = None
    head: str | None = None
    foot: str | None = None


type Dealt = tuple[tuple[str, ...], tuple[TreeLane, ...]]


def tree_lanes(tree: Series, height: Mapping[str, int]) -> tuple[TreeLane, ...]:
    """Lane 0 holds the tree's tallest path; every other lane is joined to an earlier one."""
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


def part_height(part: SeriesPart, height: Mapping[str, int]) -> int:
    """A leaf's measured height, a Series' sum, a Parallel's tallest part."""
    if isinstance(part, str):
        return height[part]
    found = [part_height(p, height) for p in part.parts]
    return sum(found) if isinstance(part, Series) else max(found)


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
    heights = [part_height(p, height) for p in part.parts]
    tall = heights.index(max(heights))
    tallest: Dealt = _lane(part.parts[tall], height, at, index)
    own, lanes = tallest[0], list(tallest[1])
    for i, p in enumerate(part.parts):
        if i != tall:
            mine = index + len(lanes)
            found: Dealt = _lane(p, height, mine, mine + 1)
            lanes += [TreeLane(found[0], at, own[0], own[-1]), *found[1]]
    return own, tuple(lanes)
