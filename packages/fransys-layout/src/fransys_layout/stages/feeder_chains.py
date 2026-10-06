"""layout-0122: the column above a feeder stands above the feeder in the box's column."""

from typing import TYPE_CHECKING

from fransys_layout.stages.slices import by_key

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.types import Cell, Handle


def chain_of(cells: Sequence[Cell]) -> tuple[Cell, ...] | None:
    """The cells above a column's feeder, `()` for none, `None` when the feeder is not its bottom.

    The feeder is the bottom cell when it alone holds the last row; each row above it holds
    cells of one index, which the move keeps in their lanes.
    """
    last = max(cell.index for cell in cells)
    bottom = [cell for cell in cells if cell.index == last]
    return tuple(cell for cell in cells if cell.index < last) if len(bottom) == 1 else None


def chain_rows(
    members: Sequence[Handle], chains: Mapping[Handle, tuple[Cell, ...]]
) -> list[list[Cell]]:
    """The chain rows of `members` (left to right), bottom-aligned, cells left to right per row."""
    stacks = [
        [row for _, row in sorted(by_key(chains.get(member, ()), lambda c: c.index).items())]
        for member in members
    ]
    depth = max((len(stack) for stack in stacks), default=0)
    rows: list[list[Cell]] = [[] for _ in range(depth)]
    for stack in stacks:
        for step, row in enumerate(stack, start=depth - len(stack)):
            rows[step].extend(sorted(row, key=lambda c: c.lane))
    return rows
