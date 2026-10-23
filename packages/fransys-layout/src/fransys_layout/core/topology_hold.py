"""Stage 1: the hold each cell after a series-parallel group carries (TAG O4, layout-0383)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .topology_fans import LaneDraft
    from .topology_tree import TreeFold


def hold_cells(lanes: Sequence[LaneDraft], folds: Sequence[TreeFold]) -> None:
    """Set `Cell.hold` on each lane's cells from the trees' holds, keyed by symbol.

    The one writer. A hold is the G above its cell and the cells stand in tree order, so a turned
    lane keeps each hold on the cell that follows the parallel.
    """
    holds = {sym: g for fold in folds for sym, g in fold.holds}
    for lane in lanes:
        lane.cells[:] = [replace(c, hold=holds.get(c.sym, c.hold)) for c in lane.cells]
