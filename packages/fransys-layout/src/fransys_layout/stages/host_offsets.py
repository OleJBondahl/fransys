"""R7.1 attachment x: an attachment sits at its host port's x (layout-0122: a host first)."""

from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID, snap_up

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.place import _Cell
    from fransys_layout.stages.types import Handle


def attachment_offsets(rows: Sequence[list[_Cell]]) -> None:
    """R7.1: an attachment sits at its host port's x, after its host's own attachment."""
    by_function = {cell.function: cell for row in rows for cell in row}
    for row in rows:
        previous = None
        for cell in row:
            _attach_at_host(cell, by_function)
            if (
                previous is not None
                and cell.host is not None
                and (previous.host, previous.port) == (cell.host, cell.port)
            ):
                # a second attachment on one host port takes the row's next free slot
                cell.dx = max(cell.dx, _next_slot(previous, cell))
            previous = cell


def _attach_at_host(cell: _Cell, by_function: Mapping[Handle, _Cell]) -> None:
    """Put `cell` at its host port's x, after the host's own attachment when it has one."""
    if cell.host is None:
        return
    host = by_function[cell.host]
    _attach_at_host(host, by_function)
    port_x = next(p.at.x for p in host.geometry.ports if p.name == cell.port)
    cell.dx = host.dx - host.axis_offset + port_x


def _next_slot(previous: _Cell, cell: _Cell, start: int | None = None) -> int:
    """The `dx` that puts `cell`'s keep-out box a wiring grid right of `previous`'s.

    `start` stands for `previous.dx` when given (0 measures the bare step).
    """
    return snap_up(
        (previous.dx if start is None else start)
        + previous.left_of_axis
        + previous.geometry.keepout.width
        + WIRING_GRID
        - cell.left_of_axis
    )
