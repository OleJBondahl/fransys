"""Columns stand in the order of the box pins they land on (LEGACY-REVIEW R11, layout-0264).

A column wired to the pins of a generic box, above or below it, stands left to right in the
order of those pins' marking ranks (`DrawnPort.order`). Two steps use the one table:
`lanes_in_pin_order` turns the strands of a bundle column, and `in_pin_order` moves whole
groups and the columns inside one. Neither crosses a role, and a group keeps its columns.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.boxes import turning_ports
from fransys_layout.stages.types import Home

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from ._packing import Unit
    from .types import Column, Connection, DrawnFunction, Handle, Role

type Side = tuple[Handle, str | None]  # a box and the side its pin stands on, `None` if it turns
type Landing = Mapping[Handle, Mapping[Side, int]]  # function -> side -> lowest pin rank
type ColumnLanding = Mapping[AuthoringKey, Mapping[Side, int]]
type Power = tuple[Mapping[Any, int], Mapping[Any, str], Mapping[Any, str]]


def function_landing(
    drawn: Sequence[DrawnFunction], connections: Sequence[Connection], power: Power
) -> dict[Handle, dict[Side, int]]:
    """Each function's lowest marking rank on each box side it is wired to.

    A side is `(box, facing)` for a pin whose side the box fixed (a power or item pin) and
    `(box, None)` for a pin that turns toward its partners: the sides of those are not known yet.
    """
    drawn_of = {one.function: one for one in drawn}
    where = {}
    for one in drawn:
        if one.geometry.generic_box:
            turning = turning_ports(one, power)
            facing = {g.name: g.facing.value for g in one.geometry.ports}
            for p in one.ports:
                side = None if p.port in turning else facing.get(p.symbol_port)
                where[p.port] = ((one.function, side), p.order)
    found: dict[Handle, dict[Side, int]] = {}
    for c in connections:
        for own, far in ((c.a, c.b), (c.b, c.a)):
            if far.port not in where or drawn_of[far.function] is drawn_of.get(own.function):
                continue
            side, rank = where[far.port]
            at = found.setdefault(own.function, {})
            at[side] = min(at.get(side, rank), rank)
    return found


def column_landing(
    columns: Sequence[Column], landing: Landing
) -> dict[AuthoringKey, dict[Side, int]]:
    """Each column's lowest rank on each box, over the cells it draws itself."""
    found: dict[AuthoringKey, dict[Side, int]] = {}
    for column in columns:
        for cell in column.cells:
            if cell.host is not None or cell.home is Home.ELSEWHERE:
                continue
            at = found.setdefault(column.key, {})
            for box, rank in landing.get(cell.function, {}).items():
                at[box] = min(at.get(box, rank), rank)
    return {key: at for key, at in found.items() if at}


def lanes_in_pin_order(columns: tuple[Column, ...], landing: Landing) -> tuple[Column, ...]:
    """A bundle column's strands (its lanes) turn into the order of the pins they land on."""
    return tuple(_turned(column, landing) for column in columns)


def _turned(column: Column, landing: Landing) -> Column:
    if any(cell.host is not None or cell.side for cell in column.cells):
        return column
    rows: dict[int, list[int]] = {}
    for cell in column.cells:
        rows.setdefault(cell.index, []).append(cell.lane)
    width = max((len(lanes) for lanes in rows.values()), default=0)
    if width < 2 or sorted(set().union(*rows.values())) != list(range(width)):  # noqa: PLR2004 -- two strands is the least a bundle has
        return column
    strand = _strand_ranks(column, landing, width, rows)
    if strand is None:
        return column
    place = {lane: new for new, lane in enumerate(sorted(strand, key=strand.__getitem__))}
    if all(lane == new for lane, new in place.items()):
        return column
    cells = (
        replace(cell, lane=place[cell.lane]) if len(rows[cell.index]) == width else cell
        for cell in column.cells
    )
    return replace(column, cells=tuple(cells))


def _strand_ranks(
    column: Column, landing: Landing, width: int, rows: Mapping[int, Sequence[int]]
) -> dict[int, int] | None:
    """Each lane's rank on the one box every lane lands on, distinct ranks, else `None`."""
    ranks: dict[Side, dict[int, int]] = {}
    for cell in column.cells:
        if len(rows[cell.index]) != width:
            continue
        for box, rank in landing.get(cell.function, {}).items():
            at = ranks.setdefault(box, {})
            at[cell.lane] = min(at.get(cell.lane, rank), rank)
    whole = [at for at in ranks.values() if len(at) == width and len(set(at.values())) == width]
    return whole[0] if len(whole) == 1 and len(ranks) == 1 else None


def in_pin_order(units: Sequence[Unit], landing: ColumnLanding) -> list[Unit]:
    """The units with landing columns reordered into pin order, inside a unit and between units.

    A unit or column that lands on two boxes stays; so does everything of another role.
    """
    inside = [_inside(unit, landing) for unit in units]
    keyed = {}
    for at, unit in enumerate(inside):
        boxes = {box for key in unit.columns for box in landing.get(key, {})}
        if len(boxes) == 1:
            (box,) = boxes
            keyed[at] = (unit.role, box, min(landing[k][box] for k in unit.columns if k in landing))
    result = list(inside)
    for slots in _slots(keyed):
        for slot, at in zip(slots, sorted(slots, key=lambda i: keyed[i][2]), strict=True):
            result[slot] = inside[at]
    return result


def _slots(keyed: Mapping[int, tuple[Role, Side, int]]) -> list[list[int]]:
    """The unit positions that share a role and a box, each list in position order."""
    groups: dict[tuple[Role, Side], list[int]] = {}
    for at, (role, box, _) in keyed.items():
        groups.setdefault((role, box), []).append(at)
    return [at for at in groups.values() if len(at) > 1]


def _inside(unit: Unit, landing: ColumnLanding) -> Unit:
    """`unit` with the columns that land on its one box in pin order, in their own places."""
    boxes = {box for key in unit.columns for box in landing.get(key, {})}
    if len(boxes) != 1:
        return unit
    (box,) = boxes
    slots = [at for at, key in enumerate(unit.columns) if box in landing.get(key, {})]
    ordered = sorted((unit.columns[at] for at in slots), key=lambda key: landing[key][box])
    columns = list(unit.columns)
    for at, key in zip(slots, ordered, strict=True):
        columns[at] = key
    return replace(unit, columns=tuple(columns))
