"""HL13, HL18: which columns each middle interface's line reaches, or that it leaves.

The one answer both the middle groups and the leaving lines read (designer's P3 condition 1).
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from .middle import MiddleUnit, owners_of

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey, Id

    from .types import Column

type _SetKey = tuple[Id[Any] | None, Id[Any] | None]


def line_reach(
    columns: Sequence[Column], units: Sequence[MiddleUnit]
) -> tuple[dict[Id[Any], tuple[AuthoringKey, ...]], tuple[MiddleUnit, ...]]:
    """Per line interface, the columns of its drawing set that its line reaches; the units.

    Reached: a column that held its or its plug's views and keeps a cell, or holds a far end. An
    interface reached nowhere leaves (HL18), its views' columns its anchor; every unit stays.
    """
    owners = owners_of(units)
    homes: dict[Id[Any], dict[AuthoringKey, _SetKey]] = {}
    reach: dict[Id[Any], dict[AuthoringKey, None]] = {}
    for column in columns:
        held, keeps = _held(column, owners)
        for interface in held:
            homes.setdefault(interface, {})[column.key] = column.drawing_set_key
            if keeps:
                reach.setdefault(interface, {})[column.key] = None
    far = _far(units)
    for column in columns:
        for interface in dict.fromkeys(
            i for cell in column.cells for i in far.get(cell.function, ())
        ):
            if column.drawing_set_key in homes.get(interface, {}).values():
                reach.setdefault(interface, {})[column.key] = None
    leaving = frozenset(i for i in homes if i not in reach)
    found = {i: tuple(keys) for i, keys in reach.items()}
    found.update({i: tuple(homes[i]) for i in leaving})
    return found, tuple(_marked(unit, leaving) for unit in units)


def _held(
    column: Column, owners: Mapping[Id[Any], list[tuple[Id[Any], Id[Any]]]]
) -> tuple[list[Id[Any]], bool]:
    """The interfaces whose views `column` holds outside their unit, and whether a cell stays."""
    held: dict[Id[Any], None] = {}
    keeps = False
    for cell in column.cells:
        mine = [
            interface for unit, interface in owners.get(cell.function, ()) if unit != column.unit
        ]
        held.update(dict.fromkeys(mine))
        keeps = keeps or not mine
    return list(held), keeps


def _far(units: Sequence[MiddleUnit]) -> dict[Id[Any], list[Id[Any]]]:
    """Each far-end function, to the line interfaces whose lines end at it.

    A line between two top-level units reaches neither: each end leaves (HL20, condition 2).
    """
    top = {
        f
        for unit in units
        if unit.top
        for one in unit.interfaces
        for f in (one.edge.function, one.plug, *one.views, *one.plug_views)
    }
    far: dict[Id[Any], list[Id[Any]]] = {}
    for unit in units:
        for one in unit.interfaces:
            for function in one.far if one.edge.line else ():
                if not (unit.top and function in top):
                    far.setdefault(function, []).append(one.edge.function)
    return far


def _marked(unit: MiddleUnit, leaving: frozenset[Id[Any]]) -> MiddleUnit:
    """`unit` with each line interface its line reaches nowhere marked leaving."""
    return replace(
        unit,
        interfaces=tuple(
            replace(one, leaving=True) if one.edge.function in leaving else one
            for one in unit.interfaces
        ),
    )
