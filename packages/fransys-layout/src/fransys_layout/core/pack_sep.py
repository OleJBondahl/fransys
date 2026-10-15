"""Separation of two placed columns by overlapping y, with hard and soft boxes (layout-0271).

A cell's hard box is its body grown by its keep-out; its soft box is its footprint. Hard may
overlap nothing, soft may overlap soft. `Options.tag_stagger` False makes soft count as hard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .geometry import cell_anchor, cell_footprint, rotate_box, shift, stack_lane, union

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .pack import PlacedColumn
    from .values import Box, Cell, Options, Sym


class PlacedCell(NamedTuple):
    """A cell's footprint rows (top, bottom) and hard and soft boxes, in column x and stacked y."""

    top: int
    bottom: int
    hard: Box
    soft: Box


def hard_soft(sym: Sym, cell: Cell, *, in_row: bool, tag_stagger: bool) -> tuple[Box, Box]:
    """The hard and soft boxes of a cell at its orientation, relative to its origin."""
    fp = cell_footprint(sym, cell, in_row=in_row)
    if not tag_stagger:
        return fp, fp
    hard = union(rotate_box(sym.body, cell.orient), rotate_box(sym.keepout, cell.orient))
    return hard, union(fp, hard)


def placed_cells(
    pc: PlacedColumn, syms: Mapping[str, Sym], in_row: frozenset[str], options: Options
) -> list[PlacedCell]:
    """Every cell of the column with its boxes against lane 0's wire x and its stacked y."""
    out: list[PlacedCell] = []
    for cells, offset in zip(pc.lanes, pc.offsets, strict=True):
        ys, _ = stack_lane(syms, cells, options, in_row)
        for cell, y in zip(cells, ys, strict=True):
            sym = syms[cell.sym]
            row = cell.sym in in_row
            hard, soft = hard_soft(sym, cell, in_row=row, tag_stagger=options.tag_stagger)
            dx = offset - cell_anchor(sym, cell)[0]
            out.append(
                PlacedCell(y + soft.y, y + soft.y + soft.h, shift(hard, dx, y), shift(soft, dx, y))
            )
    return out


def _reach(a: PlacedCell, b: PlacedCell) -> int:
    """How far b's left stands right of a's right: hard against anything, soft against soft free."""
    return max(
        a.hard.x + a.hard.w - b.hard.x,
        a.soft.x + a.soft.w - b.hard.x,
        a.hard.x + a.hard.w - b.soft.x,
    )


def separation(
    a: PlacedColumn,
    b: PlacedColumn,
    syms: Mapping[str, Sym],
    in_row: frozenset[str],
    options: Options,
) -> int:
    """Wire-x distance of b from a, on the grid, over the cell pairs whose y spans overlap."""
    gap = options.column_gap_min
    slack = options.row_gap
    sep = gap
    cells_b = placed_cells(b, syms, in_row, options)
    for ca in placed_cells(a, syms, in_row, options):
        for cb in cells_b:
            if ca.top - slack < cb.bottom and cb.top - slack < ca.bottom:
                sep = max(sep, _reach(ca, cb) + gap)
    return -(-sep // options.wiring_grid) * options.wiring_grid
