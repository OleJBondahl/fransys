"""HL11 to HL13: a middle unit's line interfaces leave their columns, then take their edges."""

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import TYPE_CHECKING, Any

from .connector_boxes import box_size
from .edges import TOP, InterfaceEdge, edges

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey, Id

    from .types import Column


@dataclass(frozen=True)
class MiddleInterface:
    """One interface of a middle unit: its pin views, its plug and the two boxes' texts."""

    edge: InterfaceEdge
    views: tuple[Id[Any], ...]
    plug: Id[Any] | None
    plug_views: tuple[Id[Any], ...]
    lines: tuple[str, ...]
    plug_lines: tuple[str, ...]
    far: frozenset[Id[Any]] = frozenset()  # the functions at its line's other ends, and their views
    conductors: frozenset[Id[Any]] = frozenset()  # what its line carries
    leaving: bool = False  # its line reaches no column of its set: it leaves (HL18), condition 1


@dataclass(frozen=True)
class MiddleUnit:
    """A unit with a harness line at an interface (HL12), and the conductors its lines carry."""

    unit: Id[Any]
    interfaces: tuple[MiddleInterface, ...]
    carried: frozenset[Id[Any]]
    title: str = ""
    top: bool = False


@dataclass(frozen=True)
class MiddleGroup:
    """A middle unit with its edges decided: the top-edge interfaces, each one's columns, bands."""

    unit: MiddleUnit
    top: frozenset[Id[Any]]
    reach: Mapping[Id[Any], tuple[AuthoringKey, ...]]
    upper: frozenset[AuthoringKey] = frozenset()
    lower: frozenset[AuthoringKey] = frozenset()


def _band(
    top: frozenset[Id[Any]], reach: Mapping[Id[Any], tuple[AuthoringKey, ...]], *, upper: bool
) -> frozenset[AuthoringKey]:
    """The columns of one band: those its edge's interfaces reach."""
    return frozenset(
        key for function, keys in reach.items() if (function in top) is upper for key in keys
    )


def group_index(groups: Sequence[MiddleGroup]) -> dict[AuthoringKey, tuple[MiddleGroup, ...]]:
    """Each band column's groups, so a page finds its groups by its own columns.

    Two groups may share a column (HL20): two top-level units' leaving lines anchor in one.
    """
    index: dict[AuthoringKey, tuple[MiddleGroup, ...]] = {}
    for group in groups:
        for key in dict.fromkeys((*group.upper, *group.lower)):
            index[key] = (*index.get(key, ()), group)
    return index


def _compact(column: Column, gone: frozenset[Id[Any]]) -> Column:
    """`column` without the cells in `gone`, its rows renumbered from 0 with no gap."""
    kept = [cell for cell in column.cells if cell.function not in gone]
    rows = {index: n for n, index in enumerate(sorted({cell.index for cell in kept}))}
    return replace(column, cells=tuple(replace(cell, index=rows[cell.index]) for cell in kept))


def strip_columns(
    columns: Sequence[Column],
    units: Sequence[MiddleUnit],
    reach: Mapping[Id[Any], tuple[AuthoringKey, ...]],
) -> tuple[tuple[Column, ...], dict[Id[Any], tuple[AuthoringKey, ...]]]:
    """Every column without the middle units' line views outside their own drawing; the reach.

    A column left with no cell is dropped, and so is its key from the reach.
    """
    owners = owners_of(units)
    out = [kept for kept in (_strip_one(c, owners) for c in columns) if kept.cells]
    keys = frozenset(column.key for column in out)
    kept_reach = {f: tuple(k for k in found if k in keys) for f, found in reach.items()}
    return tuple(out), kept_reach


def owners_of(units: Sequence[MiddleUnit]) -> dict[Id[Any], list[tuple[Id[Any], Id[Any]]]]:
    """Each stripped pin view's (unit, interface) pairs: a line interface's and its plug's.

    A leaving interface keeps its views: their column anchors its group on its page.
    """
    owners: dict[Id[Any], list[tuple[Id[Any], Id[Any]]]] = {}
    for unit in units:
        for one in unit.interfaces:
            if one.edge.line and not one.leaving:
                for view in {*one.views, *one.plug_views}:
                    owners.setdefault(view, []).append((unit.unit, one.edge.function))
    return owners


def _strip_one(column: Column, owners: Mapping[Id[Any], list[tuple[Id[Any], Id[Any]]]]) -> Column:
    """`column` without every other unit's stripped views."""
    gone = frozenset(
        cell.function
        for cell in column.cells
        if any(unit != column.unit for unit, _ in owners.get(cell.function, ()))
    )
    return _compact(column, gone) if gone else column


def _flow(one: MiddleInterface, columns: Sequence[Column], unit: Id[Any]) -> bool | None:
    """A no-line interface's edge by its column's flow: at the column's bottom end, the top."""
    for column in columns:
        if column.unit == unit:
            continue
        at = [cell.index for cell in column.cells if cell.function in one.views]
        if at:
            return max(at) == max(cell.index for cell in column.cells)
    return None


def _homes(
    one: MiddleInterface, columns: Sequence[Column], unit: Id[Any]
) -> tuple[AuthoringKey, ...]:
    """A no-line interface's columns: those holding its replica outside its unit (HL11)."""
    views = frozenset(one.views)
    return tuple(
        column.key
        for column in columns
        if column.unit != unit and any(cell.function in views for cell in column.cells)
    )


def middle_groups(
    units: Sequence[MiddleUnit],
    columns: Sequence[Column],
    reach: Mapping[Id[Any], tuple[AuthoringKey, ...]],
    widths: Mapping[AuthoringKey, int],
    text_height: int,
) -> tuple[MiddleGroup, ...]:
    """HL13: each middle unit's edges, by `edges`, with the flows and band widths filled in."""
    groups = []
    for unit in units:
        filled = [
            replace(
                one.edge,
                flow=None if one.edge.line else _flow(one, columns, unit.unit),
                width=_band_width(one, reach, widths, text_height),
            )
            for one in unit.interfaces
        ]
        split = edges(filled)
        top = frozenset(function for function, edge in split.items() if edge is TOP)
        mine = {
            one.edge.function: reach.get(one.edge.function, ())
            if one.edge.line
            else _homes(one, columns, unit.unit)
            for one in unit.interfaces
        }
        upper, lower = _band(top, mine, upper=True), _band(top, mine, upper=False)
        groups.append(MiddleGroup(unit=unit, top=top, reach=mine, upper=upper, lower=lower))
    return tuple(groups)


def _band_width(
    one: MiddleInterface,
    reach: Mapping[Id[Any], tuple[AuthoringKey, ...]],
    widths: Mapping[AuthoringKey, int],
    text_height: int,
) -> Fraction:
    """HL13's even measure: its box, or the columns its line reaches, whichever is wider."""
    box = box_size(one.lines, [], text_height=text_height)[0]
    columns = sum(widths.get(key, 0) for key in reach.get(one.edge.function, ()))
    return Fraction(max(box, columns))
