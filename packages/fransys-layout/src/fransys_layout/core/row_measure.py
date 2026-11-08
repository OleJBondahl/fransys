"""The measure of each placed row: its devices, its height and width in G and the term that set its height (R1939).

The one home of the figures PAGE_OVERFLOW reads (`widen.overflows` names its culprit row from these) and of
`CoreLayout.rows`, so a finding's text and the value the consumer reads cannot disagree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .arrow_reserve import block_reserves
from .outputs import RowMeasure
from .row_names import row_devices
from .values import RowTerm

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .arrow_reserve import RowReserve
    from .flow_values import Block, Column, CutResult
    from .outputs import PagePlacement, Placement
    from .values import Box, Options, PagePlan, PlacementProblem

__all__ = ("page_rows", "row_measures", "row_term")

type _Reserves = Mapping[str | tuple[str, str], RowReserve]


def _reach(boxes: Iterable[tuple[int, int]]) -> int:
    """The height from the highest top to the lowest bottom of the (top, bottom) pairs; 0 for none."""
    found = list(boxes)
    return max(b for _, b in found) - min(t for t, _ in found) if found else 0


def _span(box: Box) -> tuple[int, int]:
    return box.y, box.y + box.h


def row_term(page: PagePlacement, index: int, devices: tuple[str, ...], row_blocks: tuple[Block, ...], reserves: _Reserves) -> tuple[int, RowTerm]:
    """The one term function: (reach, term) of the tallest reach in row `index`; a tie goes to the earlier `RowTerm` member."""
    footprints = {p.sym: p.footprint for p in page.placed}
    cards = {b.anchor for b in row_blocks if b.is_card}
    cells = [_span(footprints[s]) for s in devices if s in footprints and s not in cards]
    held = [_span(footprints[s]) for s in devices if s in footprints and s in cards]
    base = [*cells, *held]
    hung = [_span(h) for s in devices for h in page.hangings.get(s, ())]
    lines = [(t.y - t.room[0], t.y + t.room[1]) for t in page.trunks if t.row == index]
    drop = max((reserves[key].y for b in row_blocks if (key := b.anchor or b.id) in reserves), default=0)
    reach = (
        (RowTerm.BODY, _reach(cells)),
        (RowTerm.CARD, _reach(held)),
        (RowTerm.MARKER_ROOM, _reach([*base, *hung])),
        (RowTerm.STUB, _reach([*base, *lines])),
        (RowTerm.ANNEX, _reach(base) + drop),
    )
    r, _, term = max((r, -i, term) for i, (term, r) in enumerate(reach))  # the first of equals wins: an absent term never does
    return r, term


def page_rows(page: PagePlacement, plan: PagePlan, env: tuple[Mapping[str, Block], Mapping[str, Column], _Reserves]) -> tuple[RowMeasure, ...]:
    """The rows with blocks of one planned page, measured from its placement (height, width) in G, in row order."""
    blocks, columns, reserves = env
    out = []
    for index, row in enumerate(plan.rows):
        if row.blocks:
            devices = row_devices(plan, index, blocks, columns)
            reach, term = row_term(page, index, devices, tuple(blocks[b] for b in row.blocks), reserves)
            out.append(RowMeasure(page.page, index, devices, *page.rows[index], term, reach))
    return tuple(out)


def row_measures(placement: Placement, cut: CutResult, problem: PlacementProblem, options: Options) -> tuple[RowMeasure, ...]:
    """The rows of every page, page by page: `CoreLayout.rows`."""
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    columns = {c.id: c for c in cut.flow.columns}
    env = (blocks, columns, block_reserves(cut, problem.annexes, options))
    return tuple(m for page, plan in zip(placement.pages, cut.spec.pages, strict=True) for m in page_rows(page, plan, env))
