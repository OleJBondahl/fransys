"""Far ends drawn at the pin they serve (drawing conventions V5), the step after `attach_replicas`.

A contact, or a coil on a PLC output channel, whose one wire reaches a single pin in another
group's column moves its home there, above an N pin or below an S pin, if the column still fits.
"""

from functools import partial
from typing import TYPE_CHECKING, NamedTuple

from fransys_layout.geometry import GENERIC_BOX_KEY, WIRING_GRID
from fransys_layout.geometry.box_reach import Reach, Row, extent, spread
from fransys_layout.geometry.symbols import channel_pitch
from fransys_layout.stages.attach import _entry
from fransys_layout.stages.box_reach import rows_of
from fransys_layout.stages.far_moves import (
    _assembled,
    _is_moving,
    _moved_cells,
    _touching,
)
from fransys_layout.stages.lookups import group_of
from fransys_layout.stages.own_group import own_group_homes

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_layout.stages.types import (
        Column,
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        PortRef,
        Profile,
        SheetFormat,
    )
    from fransys_model.kernel import AuthoringKey

    type _Entry = tuple[Handle, str, int, Handle, str, bool]
    type _Touching = Mapping[Handle, tuple[Connection, ...]]


class _Facts(NamedTuple):
    drawn_of: Mapping[Handle, DrawnFunction]
    touching: Mapping[Handle, tuple[Connection, ...]]
    groups: Mapping[Handle, object]


class FarInputs(NamedTuple):
    """What V5 reads besides the columns: the drawn run, its wires, each function's group."""

    drawn: tuple[DrawnFunction, ...]
    connections: tuple[Connection, ...]
    groups: Mapping[Handle, object]


def group_map(functions: Sequence[FunctionSpec]) -> dict[Handle, object]:
    """layout-0103: a function's group, by its hint or the last of its path."""
    return {spec.function: group_of(spec) for spec in functions}


def move_far_ends(
    columns: tuple[Column, ...],
    homes: tuple[Column, ...],
    far: FarInputs,
    fits: Callable[[Column], bool],
) -> tuple[Column, ...]:
    """V5: move a lone contact or output coil's home to its far pin, unless `fits` says no."""
    home_keys = {column.key for column in homes}
    home_of = {
        cell.function: column
        for column in columns
        if column.key in home_keys
        for cell in column.cells
        if not cell.replica
    }
    facts = _Facts({one.function: one for one in far.drawn}, _touching(far.connections), far.groups)
    placed: dict[AuthoringKey, tuple[_Entry, ...]] = {}
    leaving: dict[AuthoringKey, frozenset[Handle]] = {}
    for column in columns:
        if column.key not in home_keys or column.key in placed:
            continue
        for cell in column.cells:
            hosted = _far_host(cell.function, column, home_of, facts)
            if hosted is None or _is_moving(hosted[1][0], hosted[1][3], placed, leaving):
                continue
            host, entry = hosted
            entries = (*placed.get(host.key, ()), entry)
            if fits(_moved_cells(host, entries)):
                placed[host.key] = entries
                leaving[column.key] = leaving.get(column.key, frozenset()) | {cell.function}
    return own_group_homes(
        _assembled(columns, placed, leaving), facts.drawn_of, facts.touching, fits
    )


def _far_host(
    terminal: Handle, column: Column, home_of: Mapping[Handle, Column], facts: _Facts
) -> tuple[Column, _Entry] | None:
    """V5: the host column and entry of a lone far end, `None` unless every rule holds."""
    drawn_of, touching, groups = facts
    wires = touching.get(terminal, ())
    if len(wires) != 1:
        return None
    own, other = (wires[0].a, wires[0].b)
    if other.function == terminal:
        own, other = other, own
    host = home_of.get(other.function)
    if host is None:
        return None
    far = drawn_of[other.function]
    # layout-0103: a box's column also holds the contacts that chain discovery put under it
    own_column = (
        host.key == column.key
        and drawn_of[terminal].roles.contact
        and _is_channel(far, other)
        and groups.get(terminal) != groups.get(other.function)
    )
    if (host.group, host.drawing_set_key) == (
        column.group,
        column.drawing_set_key,
    ) and not own_column:
        return None
    mine = drawn_of[terminal]
    # one pin: no other wire at it (a PLC module's box is one function, its channels pins)
    if len(_wires_at(far, other, touching)) != 1 or not _serves(mine, far, other):
        return None
    entry = _entry(mine, own, far, other)
    return None if entry is None else (host, entry)


def _is_channel(far: DrawnFunction, end: PortRef) -> bool:
    """Whether `end` is a PLC channel's pin: the whole function is one, or the port is flagged."""
    return far.roles.plc_channel or any(p.channel for p in far.ports if p.port == end.port)


def _serves(mine: DrawnFunction, far: DrawnFunction, end: PortRef) -> bool:
    """A contact serves any pin; a coil serves a PLC output channel only."""
    return mine.roles.contact or (mine.roles.coil and _is_channel(far, end))


def sheet_fits(
    drawn: tuple[DrawnFunction, ...], profile: Profile, sheet: SheetFormat
) -> Callable[[Column], bool]:
    """layout-0074: a column fits when its rows, `row_spacing` apart, stand inside the sheet."""
    room = sheet.content_height - _HEADROOM_LANES * WIRING_GRID
    return partial(
        _fits, {one.function: one for one in drawn}, profile.row_spacing, room, sheet.content_width
    )


def _fits(
    drawn_of: Mapping[Handle, DrawnFunction], spacing: int, room: int, width: int, column: Column
) -> bool:
    """A column fits: its rows at `spacing` in `room`, its box and contacts in `width`."""
    heights: dict[int, int] = {}
    for cell in column.cells:
        keepout = drawn_of[cell.function].geometry.keepout
        heights[cell.index] = max(heights.get(cell.index, 0), keepout.height)
    return (
        sum(heights.values()) + spacing * (len(heights) - 1) <= room
        and _span(drawn_of, column) <= width
    )


def _span(drawn_of: Mapping[Handle, DrawnFunction], column: Column) -> int:
    """V5: the width of a generic box with its contacts under all pins (the keep-out's own span)."""
    box = next((drawn_of[c.function] for c in column.cells if c.host is None), None)
    if box is None or box.geometry.key != GENERIC_BOX_KEY:
        return 0
    held: dict[str, list[Row]] = {}
    for cell in column.cells:
        if cell.host == box.function:  # layout-0122: a moved chain hosts on its feeder, not here
            held.setdefault(cell.port, []).extend(
                rows_of(drawn_of[cell.function], [drawn_of[cell.function].geometry.keepout])
            )
    if not held:
        return 0
    reach = tuple(Reach(name=name, rows=tuple(rows)) for name, rows in held.items())
    ports = sorted(box.geometry.ports, key=lambda p: (p.at.x, p.facing.value))
    base = {p.name: ("", i) for i, p in enumerate(ports)}  # sides are not yet turned: one row
    low, high = extent(spread(base, reach, channel_pitch()), reach)
    return high - low


_HEADROOM_LANES = 4  # the engine's top (3) and bottom (1) headroom lanes


def _wires_at(far: DrawnFunction, end: PortRef, touching: _Touching) -> tuple[Connection, ...]:
    """The wires at the far pin: at its port on a PLC module's box, else on the whole function."""
    wires = touching[end.function]
    if not _is_channel(far, end):
        return wires
    return tuple(c for c in wires if end.port in (c.a.port, c.b.port))
