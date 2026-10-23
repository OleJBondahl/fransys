"""The placed-column type: a column as it stands on a page, and which columns hang on a card.

pack_sep.py gives the separation of two placed columns, pack_row.py the row graph over them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .geometry import pin_of
from .values import Cell

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from .sym_values import Sym
    from .values import Block, Column, PagePlan

Attached = dict[str, tuple[str, str, int]]
LanePins = dict[str, tuple[tuple[str, int], ...]]


@dataclass(frozen=True, slots=True)
class PlacedColumn:
    """A column as it stands on the page: lanes of cells after any edge flip, and its row."""

    id: str
    lanes: tuple[tuple[Cell, ...], ...]
    offsets: tuple[int, ...]
    row: int
    flipped: bool


def cell_node(col: str, lane: int, index: int) -> str:
    """The graph node of one cell."""
    return f"cell:{col}:{lane}:{index}"


def flip_column(column: Column, *, flip: bool) -> PlacedColumn:
    """An attached column on the other edge stands reversed, each cell turned where allowed."""
    offsets = tuple(ln.offset for ln in column.lanes)
    if not flip:
        lanes = tuple(ln.cells for ln in column.lanes)
        return PlacedColumn(column.id, lanes, offsets, 0, flipped=False)
    lanes = tuple(
        tuple(
            Cell(c.sym, "R180" if c.orient == "R0" else "R0", c.bottom_pin, c.top_pin)
            for c in reversed(ln.cells)
        )
        for ln in column.lanes
    )
    return PlacedColumn(column.id, lanes, tuple(-o for o in offsets), 0, flipped=True)


def attachments(cols: tuple[Column, ...], blocks: Mapping[str, Block]) -> Attached:
    """Attached column to (box, pin, lane offset) from its box-pin ends.

    Only a column a card block lists: a spilled column (CARD_OVERFULL) places as a free column.
    """
    holder = {c: b.anchor for b in blocks.values() if b.is_card for c in b.columns}
    out: Attached = {}
    for c in cols:
        first = next(_boxpin_ends(c, holder), None)
        if first is not None:
            out[c.id] = first
    return out


def _boxpin_ends(c: Column, holder: Mapping[str, str | None]) -> Iterator[tuple[str, str, int]]:
    """(box, pin, lane offset) of each box-pin end of a column on its holding card."""
    for lane, end in enumerate((*c.heads, *c.feet)):
        if end.kind == "boxpin" and end.pin is not None and holder.get(c.id) == end.pin.sym:
            yield end.pin.sym, end.pin.pin, c.lanes[lane % len(c.lanes)].offset


def lane_pins(cols: tuple[Column, ...], blocks: Mapping[str, Block]) -> LanePins:
    """The further box pins a column's other lanes stand on, past the one `attachments` names.

    A two-lane column stands on both card pins, so the pin pitch is the lane offset. A further
    pin at an offset the column already stands on is left to the card's pitch (R391).
    """
    holder = {c: b.anchor for b in blocks.values() if b.is_card for c in b.columns}
    out: LanePins = {}
    for c in cols:
        ends = list(_boxpin_ends(c, holder))
        seen = {ends[0][1]} if ends else set()
        offsets = {ends[0][2]} if ends else set()
        more = []
        for _, pin, off in ends[1:]:
            if pin not in seen and off not in offsets:
                seen.add(pin)
                offsets.add(off)
                more.append((pin, off))
        if more:
            out[c.id] = tuple(more)
    return out


def placed_columns(
    plan: PagePlan,
    columns: Mapping[str, Column],
    blocks: Mapping[str, Block],
    attach: Attached,
    syms: Mapping[str, Sym],
) -> dict[str, PlacedColumn]:
    """Flip an attached column whose pin's used edge is not the pin's own side."""
    out: dict[str, PlacedColumn] = {}
    for r, row in enumerate(plan.rows):
        edges = {p: e for b in row.blocks for p, e in blocks[b].pin_edges}
        for col in row.columns:
            flip = False
            if col in attach:
                box, pin, _ = attach[col]
                side = pin_of(syms[box], pin).side
                flip = edges.get(pin, side) != side
            pc = flip_column(columns[col], flip=flip)
            out[col] = PlacedColumn(pc.id, pc.lanes, pc.offsets, r, flipped=pc.flipped)
    return out
