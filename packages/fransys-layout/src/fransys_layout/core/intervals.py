"""Spans on one axis take levels on the other: the one routine of jogs, joins, markers and tiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def levels(spans: Sequence[tuple[int, int]], order: Sequence[int]) -> tuple[int, ...]:
    """Level of each span: overlapping spans never share one; the earlier in `order` lies lower.

    `order` lists span indices, the one nearest the origin first. A span takes one level above
    the highest earlier span it overlaps; touching ends overlap (a shared corner draws a T).
    """
    level = [0] * len(spans)
    for pos, i in enumerate(order):
        lo, hi = spans[i]
        earlier = (level[j] for j in order[:pos] if spans[j][0] <= hi and lo <= spans[j][1])
        level[i] = max(earlier, default=-1) + 1
    return tuple(level)
