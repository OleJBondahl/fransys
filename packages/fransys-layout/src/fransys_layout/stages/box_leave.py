"""Layout-0206: a boxed connector's hidden pin views leave their columns, the box over them."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, snap_up

from .connector_boxes import CELL_ROWS, box_size, cell_width
from .middle import compact

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id

    from .box_views import BoxSpec
    from .types import Column, Connection, DrawnFunction, NetGroup


def wired_ends(
    connections: Sequence[Connection], net_groups: Sequence[NetGroup]
) -> frozenset[Id[Any]]:
    """Every function a conductor or a net group still ends on."""
    ends = [ref.function for c in connections for ref in (c.a, c.b)]
    return frozenset((*ends, *(ref.function for g in net_groups for ref in g.ports)))


def box_columns(
    columns: Sequence[Column],
    specs: Sequence[BoxSpec],
    connections: Sequence[Connection],
    net_groups: Sequence[NetGroup],
) -> tuple[Column, ...]:
    """`columns` without the boxed pin views no wire ends on, bar one per box in each column.

    A view with a cell or a wire stays: the wire runs to a symbol. The one left carries the box.
    """
    owner = {port: spec for spec in specs for port in spec.ports}
    wired = wired_ends(connections, net_groups)
    return tuple(_trimmed(column, owner, wired) for column in columns)


def _trimmed(column: Column, owner: Mapping[Id[Any], BoxSpec], wired: frozenset[Id[Any]]) -> Column:
    held = {c.host for c in column.cells if c.host} | {c.carrier for c in column.cells if c.carrier}
    kept: set[Id[Any]] = set()
    gone: set[Id[Any]] = set()
    for cell in sorted(column.cells, key=lambda cell: (cell.index, cell.lane)):
        spec = owner.get(cell.function)
        if spec is None:
            continue
        if (
            cell.function in wired
            or cell.function in held
            or cell.function in {p for p, _ in spec.cells}
            or spec.function not in kept
        ):
            kept.add(spec.function)
        else:
            gone.add(cell.function)
    return compact(column, frozenset(gone)) if gone else column


def narrowed(
    drawn: Sequence[DrawnFunction],
    specs: Sequence[BoxSpec],
    text_height: int,
    columns: Sequence[Column],
) -> tuple[DrawnFunction, ...]:
    """`drawn` with each boxed pin view's keep-out as wide as its cell, centred on its pin.

    The view draws nothing, so the columns hold the box's width and not a symbol's. A cell-less
    box's kept views share its width, so the boxes of neighbouring columns clear one another.
    """
    kept = {cell.function for column in columns for cell in column.cells}
    wide = {port: CELL_ROWS * WIRING_GRID for spec in specs for port in spec.ports}
    bare: set[Id[Any]] = set()
    for spec in specs:
        if not spec.cells:
            shown = [port for port in spec.ports if port in kept]
            box = box_size(spec.lines, [], text_height=text_height)[0]
            share = max(CELL_ROWS * WIRING_GRID, snap_up(-(-box // max(len(shown), 1))))
            wide.update(dict.fromkeys(shown, share))
            bare.update(spec.ports)
    wide.update({port: cell_width(mark, text_height) for s in specs for port, mark in s.cells})
    return tuple(
        _narrow(one, wide[one.function], boxed=one.function in bare)
        if one.function in wide
        else one
        for one in drawn
    )


def _narrow(one: DrawnFunction, width: int, *, boxed: bool) -> DrawnFunction:
    geometry = one.geometry
    body = replace(geometry.body, x=geometry.ports[0].at.x - width // 2, width=width)
    return replace(one, boxed=boxed, geometry=replace(geometry, body=body, keepout=body, slots=()))
