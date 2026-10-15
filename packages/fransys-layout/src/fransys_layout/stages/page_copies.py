"""A function stands on every page a far end of its wires stands on (layout-0216, cross-page).

The caller names the wire ends `(own, far)` whose `own` function takes the copies; a page that
seats `far` but no copy of `own`, in a drawing set that already draws `own`, gets one, attached
at the far pin. The wire then has both ends on that page and is routed there, not cut.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.stages.attach import _entry, _with_attached

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages.types import Column, DrawnFunction, Handle, PagePlan, PortRef

    type _Entry = tuple[Handle, str, int, Handle, str, bool]
    type _Page = tuple[int, int]


def with_page_copies(
    plans: tuple[PagePlan, ...],
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    ends: Sequence[tuple[PortRef, PortRef]],
) -> tuple[Column, ...]:
    """`columns` with a copy of each `own` attached at its `far` pin on a page that lacks one."""
    seated, hosts = _seats(plans, columns)
    sets = {(page[0], f) for page, functions in seated.items() for f in functions}
    drawn_of = {one.function: one for one in drawn}
    found: dict[object, list[_Entry]] = {}
    for own, far in sorted(ends, key=lambda pair: (pair[0].port, pair[1].port)):
        for page in sorted(seated):
            host = hosts.get((page, far.function))
            if host is None or own.function in seated[page] or (page[0], own.function) not in sets:
                continue
            flipped = any(c.flip for c in host.cells if c.function == far.function)
            entry = _entry(
                drawn_of[own.function], own, drawn_of[far.function], far, far_flipped=flipped
            )
            # model-0220: a host takes a copy at each pin; a pin holds one attached cell
            if entry is not None and not any(
                c.host == far.function and c.port == entry[4] for c in host.cells
            ):
                found.setdefault(host.key, []).append(entry)
                seated[page].add(own.function)
    return tuple(
        _marked(_with_attached(column, found[column.key]), column)
        if column.key in found
        else column
        for column in columns
    )


def _seats(
    plans: tuple[PagePlan, ...], columns: tuple[Column, ...]
) -> tuple[dict[_Page, set[Handle]], dict[tuple[_Page, Handle], Column]]:
    """The functions each page seats, and the column each hosts a function's own cell in."""
    by_key = {column.key: column for column in columns}
    seated: dict[_Page, set[Handle]] = {}
    hosts: dict[tuple[_Page, Handle], Column] = {}
    for plan in plans:
        page = (plan.drawing_set, plan.number)
        for planned in plan.columns:
            column = by_key[planned.column]
            seated.setdefault(page, set()).update(cell.function for cell in column.cells)
            for cell in column.cells:
                if cell.host is None and not cell.side:
                    hosts.setdefault((page, cell.function), column)
    return seated, hosts


def _marked(attached: Column, before: Column) -> Column:
    """`attached` with each cell `before` lacked marked as a copy at its wire."""
    old = {(cell.function, cell.host) for cell in before.cells}
    return replace(
        attached,
        cells=tuple(
            cell if (cell.function, cell.host) in old else replace(cell, at_wire=True)
            for cell in attached.cells
        ),
    )
