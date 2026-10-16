"""Stage 5, y: keep the most alignments the stacks and trunks allow, one item at a time.

It knows a list of Align values in priority order and a solved-able base graph, nothing
about what an Align is: the order the builder returns is the convention.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .constraints import Graph
    from .place_align import Align


@dataclass(frozen=True, slots=True)
class Accepted:
    """The page's y with the kept alignments level, and the ones dropped, each in input order."""

    y: dict[str, int]
    kept: tuple[Align, ...]
    dropped: tuple[Align, ...]


def trial(base: Graph, aligns: Sequence[Align]) -> dict[str, int] | None:
    """The y of a copy of `base` with every line of `aligns` level; None when they cannot hold."""
    g = deepcopy(base)
    for a in aligns:
        for line in a.lines:
            first, shift = line[0]
            if not all(g.equal(first, node, shift - s) for node, s in line[1:]):
                return None
    return g.solve()


def accept(base: Graph, aligns: Sequence[Align]) -> Accepted | None:
    """All aligns at once when they hold, else one at a time; None when `base` alone fails."""
    y = trial(base, aligns)
    if y is not None:
        return Accepted(y, tuple(aligns), ())
    y = trial(base, ())
    if y is None:
        return None
    kept: list[Align] = []
    dropped: list[Align] = []
    for a in aligns:
        found = trial(base, [*kept, a])
        if found is None:
            dropped.append(a)
        else:
            kept.append(a)
            y = found
    return Accepted(y, tuple(kept), tuple(dropped))
