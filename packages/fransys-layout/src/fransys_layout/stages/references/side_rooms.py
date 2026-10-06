"""S11 (layout-0090): Room's first call for a reference beside an E or W port, from `columns`.

Such a port's end is a wire only to an adjacent cell of its column or as a side element's join
to its carrier (D1's first two wire cases), both known from `columns`; an LD9 join stands at a
column's end, facing N or S. Every other conductor of the port ends in a reference, so the cell
owns that text before any page exists. Its box is the reference's first-ranked candidate (S2)
at the port's stub, sized one line high at the floor digits (S4: the lines and the set's digits
are not known yet), in the symbol's own coordinates. `sizing.with_rooms` grows the keep-out
over it for `column_widths`, and `place` does the same through `_fit_row` for its page.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping
lazy from collections.abc import Set as AbstractSet

from fransys_layout.geometry import Facing
from fransys_layout.stages.texts.candidates import (
    DEFAULT_TABLE,
    TextKind,
    box_of,
    ranked_candidates,
    stub_anchor,
)

from .marker_boxes import reference_box_width

if TYPE_CHECKING:
    from fransys_layout.geometry import Box, PortGeometry
    from fransys_layout.stages.types import (
        Cell,
        Column,
        Connection,
        DrawnFunction,
        NetGroup,
        Profile,
        SheetFormat,
    )
    from fransys_model.kernel import Id

REFERENCE_SLOT = "reference"


@dataclass(frozen=True, slots=True)
class Wiring:
    """The conductors and net groups a side port's partners are read from (S11, D10)."""

    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]


def side_reference_rooms(
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    wiring: Wiring,
    *,
    sheet: SheetFormat,
    profile: Profile,
) -> dict[Id[Any], list[tuple[str, Box]]]:
    """Per function, the `(REFERENCE_SLOT, box)` of each E or W port that carries a reference."""
    drawn_of = {one.function: one for one in drawn}
    sides = [
        (column, cell, port, g)
        for column in columns
        for cell in column.cells
        if not cell.flip
        for port, g in _side_ports(drawn_of[cell.function])
    ]
    if not sides:
        return {}
    partners = _partners({p for _, _, p, _ in sides}, wiring.connections, wiring.net_groups)
    size = (reference_box_width(sheet, profile), profile.text_height + 2 * profile.marker_padding)
    found: dict[Id[Any], list[tuple[str, Box]]] = defaultdict(list)
    for column, cell, port, g in sides:
        rows = _rows_of(column)
        carriers = {(c.function, c.carrier) for c in column.cells if c.side}
        if all(_wired_beside(cell, other, rows, carriers) for other in partners.get(port, ())):
            continue
        first = ranked_candidates(TextKind.REFERENCE, g.facing, size, DEFAULT_TABLE)[0]
        box = box_of(first, stub_anchor(g.at), size)
        if (REFERENCE_SLOT, box) not in found[cell.function]:
            found[cell.function].append((REFERENCE_SLOT, box))
    return dict(found)


def _side_ports(one: DrawnFunction) -> list[tuple[Id[Any], PortGeometry]]:
    """`one`'s ports that face E or W, as drawn at R0, with their geometry."""
    geometry = {g.name: g for g in one.geometry.ports}
    return [
        (port.port, geometry[port.symbol_port])
        for port in one.ports
        if port.symbol_port in geometry
        and geometry[port.symbol_port].facing in (Facing.E, Facing.W)
    ]


def _partners(
    ports: AbstractSet[Id[Any]],
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
) -> dict[Id[Any], set[Id[Any]]]:
    """Each of `ports`' partner functions: its conductors' other ends and its groups' others."""
    found: dict[Id[Any], set[Id[Any]]] = defaultdict(set)
    for c in connections:
        if c.a.port in ports:
            found[c.a.port].add(c.b.function)
        if c.b.port in ports:
            found[c.b.port].add(c.a.function)
    for group in net_groups:
        for ref in (ref for ref in group.ports if ref.port in ports):
            found[ref.port].update(o.function for o in group.ports if o.port != ref.port)
    return found


def _rows_of(column: Column) -> dict[Id[Any], set[int]]:
    """Each function's rows (`Cell.index`) in `column`."""
    found: dict[Id[Any], set[int]] = defaultdict(set)
    for cell in column.cells:
        found[cell.function].add(cell.index)
    return found


def _wired_beside(
    cell: Cell,
    other: Id[Any],
    rows: Mapping[Id[Any], set[int]],
    carriers: AbstractSet[tuple[Id[Any], Id[Any] | None]],
) -> bool:
    """D1: `cell`'s function and `other` are an adjacent-cell or a side-element wire."""
    adjacent = any(abs(index - cell.index) == 1 for index in rows.get(other, ()))
    return adjacent or not carriers.isdisjoint({(cell.function, other), (other, cell.function)})
