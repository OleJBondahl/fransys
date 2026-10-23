"""Stage 4 guard: every block stands in a row of a page (layout-0288, third half of the home chain).

NO_CELL puts every drawn symbol in a cell (stage 1), NO_BLOCK puts every box in one block (stage 2),
and this puts every block in at least one row, a whole block in exactly one. A block in no row is
BLOCK_NOT_PLACED. A box of a refused chain is seated like any card (R348), so it never lands here.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .cut_dp import wraps
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .values import Block, BlockList, Options, PagePlan


def unplaced(
    blocks: Sequence[BlockList],
    pages: Sequence[PagePlan],
    page_w: int,
    options: Options,
) -> tuple[Finding, ...]:
    """A finding per block in no row, and per whole block in more than one row.

    A fan wider than the page wraps at a column, so it stands in several rows (layout-0309).
    """
    rows = Counter(b for p in pages for r in p.rows for b in r.blocks)
    found = (
        _finding(b, rows[b.id], wide=wraps(b, page_w, options)) for bl in blocks for b in bl.blocks
    )
    return tuple(f for f in found if f is not None)


def _finding(block: Block, rows: int, *, wide: bool) -> Finding | None:
    if rows == 0 or (block.keep_whole and rows > 1 and not wide):
        text = f"stage 4: {block.id} stands in {rows} rows of the pages; a block needs one"
        return Finding("BLOCK_NOT_PLACED", text, None, block.id)
    return None
