"""Stage 4 guard: every block stands in a row of a page (layout-0288, third half of the home chain).

NO_CELL puts every drawn symbol in a cell (stage 1), NO_BLOCK puts every box in one block (stage 2),
and this puts every block in at least one row, a whole block in exactly one. A block in no row is
BLOCK_NOT_PLACED; a box of a chain that stage 1 refused (CHAIN_REFUSED) is CHAIN_NOT_DRAWN,
so it is never dropped unreported.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .order_bare import is_bare, is_chain_box
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .values import Block, BlockList, FlowGraph, PagePlan


def unplaced(
    blocks: Sequence[BlockList], pages: Sequence[PagePlan], flow: FlowGraph
) -> tuple[Finding, ...]:
    """A finding per block in no row, and per whole block in more than one row."""
    rows = Counter(b for p in pages for r in p.rows for b in r.blocks)
    found = (_finding(b, rows[b.id], flow) for bl in blocks for b in bl.blocks)
    return tuple(f for f in found if f is not None)


def _finding(block: Block, rows: int, flow: FlowGraph) -> Finding | None:
    if rows == 0 and is_bare(block) and is_chain_box(block.anchor, flow):
        text = f"{block.id}: a box of a refused chain is not drawn; see CHAIN_REFUSED"
        return Finding("CHAIN_NOT_DRAWN", text, None, block.id)
    if rows == 0 or (block.keep_whole and rows > 1):
        text = f"stage 4: {block.id} stands in {rows} rows of the pages; a block needs one"
        return Finding("BLOCK_NOT_PLACED", text, None, block.id)
    return None
