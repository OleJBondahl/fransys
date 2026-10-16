"""Columns measured as one row: the single home of "pack these columns as a row" (layout-0279).

Stage 2 sizes its blocks and stage 4 its cuts with `row_width(one_row(...))`; neither
re-derives a width, so a block stage 2 keeps always fits the row stage 4 plans for it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pack import attachments, lane_pins, placed_columns
from .pack_row import RowSpec
from .values import PagePlan, RowPlan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .values import Block, FlowGraph, Options, PlacementProblem


def one_row(
    cols: Sequence[str],
    blocks: Sequence[Block],
    flow: FlowGraph,
    problem: PlacementProblem,
    options: Options,
) -> RowSpec:
    """The row of `cols` in the order given, over `blocks`: placed columns, attach and in_row.

    A card block lists the columns hung on it; a column no card lists stands free.
    """
    syms = {s.id: s for s in problem.symbols}
    columns = {c.id: c for c in flow.columns}
    by_id = {b.id: b for b in blocks}
    unit = blocks[0].unit if blocks else ""
    plan = PagePlan(0, unit, (RowPlan(tuple(cols), tuple(by_id), 0),), forced_end=True, groups=())
    here = tuple(columns[c] for c in cols)
    attach = attachments(here, by_id)
    pcs = placed_columns(plan, columns, by_id, attach, syms)
    in_row = frozenset(s.id for s in syms.values() if s.row_group)
    return RowSpec(
        tuple(cols),
        tuple(blocks),
        pcs,
        syms,
        in_row,
        options,
        attach,
        more_pins=lane_pins(here, by_id),
    )
