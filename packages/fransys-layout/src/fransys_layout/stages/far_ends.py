"""Far ends drawn at the pin they serve, the step after `attach_replicas`.

A contact whose one wire, or a coil whose one channel wire (A1 or A2, layout-0208), reaches a
single pin in another group's column moves its home there, above an N pin or below an S pin. A
contact moves if the column still fits; a channel's coil always does, and a column too tall for
its sheet continues as the next column (LC1, layout-0208 R1).
"""

from functools import partial
from typing import TYPE_CHECKING, NamedTuple

from fransys_layout.geometry import OPPOSITE, WIRING_GRID, draw_order
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
from fransys_layout.stages.types import Home

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
    free: frozenset[Handle]


class FarInputs(NamedTuple):
    """What far ends read besides the columns: the drawn run, its wires, each function's group.

    `free`: the caller's channel pins whose box side is not yet fixed; a coil takes its own side.
    """

    drawn: tuple[DrawnFunction, ...]
    connections: tuple[Connection, ...]
    groups: Mapping[Handle, object]
    free: frozenset[Handle] = frozenset()


def group_map(functions: Sequence[FunctionSpec]) -> dict[Handle, object]:
    """layout-0103: a function's group, by its hint or the last of its path."""
    return {spec.function: group_of(spec) for spec in functions}


def move_far_ends(
    columns: tuple[Column, ...],
    homes: tuple[Column, ...],
    far: FarInputs,
    fits: Callable[[Column], bool],
) -> tuple[Column, ...]:
    """Move a lone contact's home to its far pin unless `fits` says no; an output coil's always."""
    home_keys = {column.key for column in homes}
    home_of = {
        cell.function: column
        for column in columns
        if column.key in home_keys
        for cell in column.cells
        if cell.home is not Home.ELSEWHERE
    }
    facts = _Facts(
        {one.function: one for one in far.drawn},
        _touching(far.connections),
        far.groups,
        far.free,
    )
    placed: dict[AuthoringKey, tuple[_Entry, ...]] = {}
    leaving: dict[AuthoringKey, frozenset[Handle]] = {}
    for column in columns:
        if column.key not in home_keys:
            continue
        for cell in column.cells:
            hosted = _far_host(cell.function, column, home_of, facts)
            if hosted is None or _is_moving(hosted[1][0], hosted[1][3], placed, leaving):
                continue
            host, entry = hosted
            entries = (*placed.get(host.key, ()), entry)
            if facts.drawn_of[cell.function].roles.coil or fits(_moved_cells(host, entries)):
                placed[host.key] = entries
                leaving[column.key] = leaving.get(column.key, frozenset()) | {cell.function}
    return own_group_homes(
        _assembled(columns, placed, leaving), facts.drawn_of, facts.touching, fits
    )


def _far_host(
    terminal: Handle, column: Column, home_of: Mapping[Handle, Column], facts: _Facts
) -> tuple[Column, _Entry] | None:
    """The host column and entry of a lone far end, `None` unless every rule holds."""
    drawn_of, touching, groups, free = facts
    ends = _lone_end(terminal, drawn_of, touching.get(terminal, ()))
    if ends is None:
        return None
    own, other = ends
    host = home_of.get(other.function)
    if host is None:
        return None
    far = drawn_of[other.function]
    mine = drawn_of[terminal]
    # layout-0103: a box's column also holds the far ends that chain discovery put by it
    own_column = (
        host.key == column.key
        and is_channel(far, other.port)
        and groups.get(terminal) != groups.get(other.function)
    )
    if (host.group, host.drawing_set_key) == (
        column.group,
        column.drawing_set_key,
    ) and not own_column:
        return None
    # layout-0208: a far end that hosts a replica (a coil's feed terminal) keeps it in its column
    if host.key != column.key and any(cell.host == terminal for cell in column.cells):
        return None
    # one pin: no other wire at it (a PLC module's box is one function, its channels pins)
    if len(_wires_at(far, other, touching)) != 1 or not _serves(mine, far, other):
        return None
    # layout-0208: a coil takes a free pin's side from its own wired terminal
    free_side = mine.roles.coil and other.port in free
    entry = _free_entry(mine, own, far, other) if free_side else _entry(mine, own, far, other)
    return None if entry is None else (host, entry)


def _free_entry(mine: DrawnFunction, own: PortRef, far: DrawnFunction, other: PortRef) -> _Entry:
    """layout-0208: at a pin of no fixed side the far end stands unflipped, the pin turns to it.

    Its order key is the pin's marking rank, the box's pin order (layout-0264).
    """
    pin = next(p for p in far.ports if p.port == other.port)
    own_symbol = next(p.symbol_port for p in mine.ports if p.port == own.port)
    own_facing = next(g.facing for g in mine.geometry.ports if g.name == own_symbol)
    return (
        other.function,
        OPPOSITE[own_facing].value,
        pin.order,
        mine.function,
        pin.symbol_port,
        False,
    )


def _lone_end(
    terminal: Handle, drawn_of: Mapping[Handle, DrawnFunction], wires: Sequence[Connection]
) -> tuple[PortRef, PortRef] | None:
    """The (own, far) ends of a far end's one wire; a coil's one wire to a channel (layout-0208)."""
    ends = [(c.b, c.a) if c.b.function == terminal else (c.a, c.b) for c in wires]
    if drawn_of[terminal].roles.coil:
        ends = [
            (own, other) for own, other in ends if is_channel(drawn_of[other.function], other.port)
        ]
    return ends[0] if len(ends) == 1 else None


def is_channel(far: DrawnFunction, port: Handle) -> bool:
    """Whether `port` of `far` is a channel pin: its function is one, or the port is flagged."""
    return far.roles.plc_channel or any(p.channel for p in far.ports if p.port == port)


def _serves(mine: DrawnFunction, far: DrawnFunction, end: PortRef) -> bool:
    """A contact serves any pin; a coil serves a PLC output channel only."""
    return mine.roles.contact or (mine.roles.coil and is_channel(far, end.port))


def sheet_fits(
    drawn: tuple[DrawnFunction, ...], profile: Profile, sheet: SheetFormat, headroom_lanes: int
) -> Callable[[Column], bool]:
    """layout-0074: a column fits when its rows, `row_spacing` apart, stand inside the sheet."""
    room = sheet.inner_height - headroom_lanes * WIRING_GRID
    return partial(
        _fits, {one.function: one for one in drawn}, profile.row_spacing, room, sheet.inner_width
    )


def _fits(
    drawn_of: Mapping[Handle, DrawnFunction], spacing: int, room: int, width: int, column: Column
) -> bool:
    """A column fits: its rows at `spacing` in `room`, its box and contacts in `width`.

    A home moving within its own column counts once, at its new row (layout-0208 R1).
    """
    moved = {c.function for c in column.cells if c.host is not None and c.home is Home.MOVED}
    heights: dict[int, int] = {}
    for cell in column.cells:
        if cell.host is None and cell.function in moved:
            continue
        keepout = drawn_of[cell.function].geometry.keepout
        heights[cell.index] = max(heights.get(cell.index, 0), keepout.height)
    return (
        sum(heights.values()) + spacing * (len(heights) - 1) <= room
        and _span(drawn_of, column) <= width
    )


def _span(drawn_of: Mapping[Handle, DrawnFunction], column: Column) -> int:
    """The width of a generic box with its contacts under all pins (the keep-out's own span)."""
    box = next((drawn_of[c.function] for c in column.cells if c.host is None), None)
    if box is None or not box.geometry.generic_box:
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
    ports = sorted(box.geometry.ports, key=lambda p: draw_order(p.at.x, p.facing.value))
    base = {p.name: ("", i) for i, p in enumerate(ports)}  # sides are not yet turned: one row
    low, high = extent(spread(base, reach, channel_pitch()), reach)
    return high - low


def _wires_at(far: DrawnFunction, end: PortRef, touching: _Touching) -> tuple[Connection, ...]:
    """The wires at the far pin: at its port on a PLC module's box, else on the whole function."""
    wires = touching[end.function]
    if not is_channel(far, end.port):
        return wires
    return tuple(c for c in wires if end.port in (c.a.port, c.b.port))
