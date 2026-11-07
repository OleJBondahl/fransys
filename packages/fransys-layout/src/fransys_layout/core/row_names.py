"""The words a finding about a row prints: its drawing set and the symbols standing in it.

The symbols come as each block's card first, then the cells of the row's columns.
The ids stay core ids; the layer that turns a finding into consumer text names each by its designation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .flow_values import Block, Column
    from .values import PagePlan


def row_where(plan: PagePlan, index: int, blocks: Mapping[str, Block], columns: Mapping[str, Column]) -> str:
    """`[set U, ]page P, row I (devices a, b)`: where a row stands (the root set is named by no set) and what stands in it."""
    row = plan.rows[index]
    anchors = [a for b in row.blocks if (a := blocks[b].anchor)]
    cells = [cell.sym for c in row.columns for lane in columns[c].lanes for cell in lane.cells]
    syms = ", ".join(dict.fromkeys([*anchors, *cells]))
    where = f"set {plan.unit}, " if plan.unit else ""
    return f"{where}page {plan.page}, row {index} (devices {syms})"
