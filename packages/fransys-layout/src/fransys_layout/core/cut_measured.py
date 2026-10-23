"""Stage 7's input to the cut: sizes read off a placement, in place of stage 4's estimates.

`Measured` is a value: the tracks each column pair's gap holds and the height of each block.
`cut_pages(..., measured=m)` packs rows with the reserves and cuts them with the heights;
`measured=None` leaves the cut as it was (layout-0298).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .cut_costs import Item
    from .values import Block


@dataclass(frozen=True, slots=True)
class Measured:
    """What stage 7 measured off the placement.

    reserves: (left, right column) to tracks; heights: whole block id to its extent in G;
    columns: column id to the extent of that column's own rows.
    """

    reserves: Mapping[tuple[str, str], int] = field(default_factory=dict)
    heights: Mapping[str, int] = field(default_factory=dict)
    columns: Mapping[str, int] = field(default_factory=dict)
    rises: Mapping[str, int] = field(default_factory=dict)


def measured_blocks(
    seq: Sequence[Item], by_id: Mapping[str, Block], measured: Measured, limit: float
) -> tuple[tuple[Item, ...], dict[str, Block]]:
    """The items and blocks with a measured block's height in place of the estimate.

    A column that is not part of a whole block takes its own measured height, never its block's,
    and is short when that is under limit. A whole block's row is its block extent.
    """
    own, rises = measured.columns, measured.rises
    items = tuple(
        replace(
            it, height=own[it.column], short=own[it.column] < limit, rise=rises.get(it.column, 0)
        )
        if not it.whole and it.column in own
        else it
        for it in seq
    )
    heights = measured.heights
    blocks = {
        k: replace(b, height_est=heights[k], rise=rises.get(k, 0)) if k in heights else b
        for k, b in by_id.items()
    }
    return items, blocks
