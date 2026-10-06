"""V5: a generic box's pins stand far enough apart for their attached contacts (model-0129)."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, generic_box_geometry
from fransys_layout.geometry.box_reach import Reach, Row, extent

from .box_fed import fed_geometry
from .partition import column_widths
from .place import axis_offset
from .room import grow_keepout
from .sizing import grown, label_boxes, with_rooms

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry.symbols import SymbolGeometry

    from .types import Column, ColumnWidth, DrawnFunction, Handle, LabelRequest, Profile


def sized_columns(
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    own_set: tuple[LabelRequest, ...],
    rooms: Mapping[Handle, list[tuple[str, Box]]],
    profile: Profile,
) -> tuple[tuple[DrawnFunction, ...], tuple[ColumnWidth, ...]]:
    """C8(b), S11, V5: the boxes widened for their contacts, and the columns' widths over them."""
    boxes = with_rooms(label_boxes(drawn, own_set, profile), rooms)
    drawn = _with_reach(drawn, columns, boxes)
    boxed = {one.function for one in drawn if one.reach}
    counted = tuple(  # a contact under a box's pin is inside the box's grown keep-out
        replace(c, cells=tuple(x for x in c.cells if x.host not in boxed) or c.cells)
        for c in columns
    )
    return drawn, column_widths(
        counted, grown(drawn, own_set, profile, rooms=rooms), profile=profile
    )


def rows_of(one: DrawnFunction, boxes: Sequence[Box]) -> tuple[Row, ...]:
    """The contact's body and texts as rows, each side measured from its pin axis."""
    axis = axis_offset(one)
    return tuple(
        Row(top=b.y, bottom=b.y + b.height, left=axis - b.x, right=b.x + b.width - axis)
        for b in (one.geometry.body, *boxes)
    )


def _with_reach(
    drawn: tuple[DrawnFunction, ...],
    columns: tuple[Column, ...],
    boxes: Mapping[Handle, list[tuple[str, Box]]],
) -> tuple[DrawnFunction, ...]:
    """Each generic box redrawn with its pins a channel pitch apart, widened per text row."""
    by_function = {one.function: one for one in drawn}
    room: dict[Handle, dict[str, tuple[Row, ...]]] = {}
    for column in columns:
        for cell in column.cells:
            if cell.host is None or by_function[cell.function].feeds is not None:
                continue  # a feeder is no contact: _feeder_rows gives it its own pin
            rows = rows_of(by_function[cell.function], [b for _, b in boxes.get(cell.function, ())])
            held = room.setdefault(cell.host, {})
            held[cell.port] = (*held.get(cell.port, ()), *rows)
    for one in drawn:
        if one.feeds is not None:
            host, port = _feeder_port(one, by_function[one.feeds])
            held = room.setdefault(host, {})
            held[port] = (
                *held.get(port, ()),
                *rows_of(one, [b for _, b in boxes.get(one.function, ())]),
            )
    return tuple(_widened(one, room.get(one.function)) for one in drawn)


def _feeder_port(feeder: DrawnFunction, host: DrawnFunction) -> tuple[Handle, str]:
    """layout-0124: the fed box and its symbol port that stands over the feeder's axis pin."""
    (feed,) = (f for f in host.fed_by if f.feeder == feeder.function)
    mine = {p.port: p.symbol_port for p in feeder.ports}
    theirs = {p.port: p.symbol_port for p in host.ports}
    mate = next(p.fed for p in feed.ports if mine[p.feeder] == feeder.primary_out)
    return host.function, theirs[mate]


def _widened(one: DrawnFunction, room: Mapping[str, tuple[Row, ...]] | None) -> DrawnFunction:
    """`one` redrawn with `room`'s pins apart; any other function untouched."""
    if not room or not one.geometry.generic_box:
        return one
    reach = tuple(Reach(name=name, rows=rows) for name, rows in sorted(room.items()))
    names = tuple(
        p.name for p in sorted(one.geometry.ports, key=lambda p: (p.at.x, p.facing.value))
    )
    sides = tuple(g.facing.value for name in names for g in one.geometry.ports if g.name == name)
    geometry = (
        fed_geometry(one, names, sides, reach)
        if one.fed_by
        else generic_box_geometry(names, sides, reach)
    )
    return replace(one, reach=reach, geometry=_with_hung(geometry, room))


def _with_hung(geometry: SymbolGeometry, room: Mapping[str, tuple[Row, ...]]) -> SymbolGeometry:
    """The box's keep-out grown sideways over the contacts that hang under its pins."""
    pins = {p.name: p.at.x for p in geometry.ports}
    reach = tuple(Reach(name=name, rows=rows) for name, rows in room.items())
    low, high = extent(pins, reach)
    keepout = geometry.keepout
    return grow_keepout(
        geometry, [Box(x=low, y=keepout.y, width=high - low, height=keepout.height)]
    )
