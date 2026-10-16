"""The width oracle of stage 4: items i..j measure what `row_width` of the same row measures.

Self-contained (it imports only the core), so the internal corpus test loads it by path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_layout.core import row_width
from fransys_layout.core.rowspec import one_row

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core.cut_costs import Item
    from fransys_layout.core.values import BlockList, FlowGraph, Options, PlacementProblem


def splits(seq: Sequence[Item], i: int, j: int) -> bool:
    """True when items i..j cut through a whole block at either end."""
    left = i > 0 and seq[i - 1].whole and seq[i - 1].block == seq[i].block
    right = j + 1 < len(seq) and seq[j].whole and seq[j + 1].block == seq[j].block
    return left or right


def window_misses(
    seq: Sequence[Item],
    unit: BlockList,
    env: tuple[FlowGraph, PlacementProblem, Options],
    step: int = 1,
) -> tuple[int, list[tuple[int, int, int, int]]]:
    """(windows checked, [(i, j, item width, row_width)] that disagree); starts every `step`."""
    flow, problem, options = env
    checked, bad = 0, []
    for i in range(0, len(seq), step):
        for j in range(i, len(seq)):
            if splits(seq, i, j):
                continue
            cols = tuple(it.column for it in seq[i : j + 1])
            blocks = tuple(b for b in unit.blocks if set(b.columns) & set(cols))
            want = row_width(one_row(cols, blocks, flow, problem, options))
            got = seq[j].at - seq[i].at + seq[i].lead + seq[j].tail
            checked += 1
            if got != want:
                bad.append((i, j, got, want))
    return checked, bad
