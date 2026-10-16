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


def _apply(g: Graph, aligns: Sequence[Align]) -> bool:
    """Level every line of `aligns` in `g`; False when one cannot hold (`g` is then spoiled)."""
    for a in aligns:
        for line in a.lines:
            first, shift = line[0]
            if not all(g.equal(first, node, shift - s) for node, s in line[1:]):
                return False
    return True


def trial(base: Graph, aligns: Sequence[Align]) -> dict[str, int] | None:
    """The y of a copy of `base` with every line of `aligns` level; None when they cannot hold."""
    g = deepcopy(base)
    return g.solve() if _apply(g, aligns) else None


def accept(base: Graph, aligns: Sequence[Align]) -> Accepted | None:
    """All aligns at once when they hold, else one at a time; None when `base` alone fails."""
    y = trial(base, aligns)
    if y is not None:
        return Accepted(y, tuple(aligns), ())
    y = trial(base, ())
    if y is None:
        return None
    kept_graph = base
    kept: list[Align] = []
    dropped: list[Align] = []
    for a in aligns:
        g = deepcopy(kept_graph)
        found = g.solve() if _apply(g, (a,)) else None
        if found is None:
            dropped.append(a)
        else:
            kept.append(a)
            kept_graph, y = g, found
    return Accepted(y, tuple(kept), tuple(dropped))
