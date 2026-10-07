"""A home terminal wired only inside its own group stands at its first pin outside its column (V4).

The terminal's pins are all in one group and drawing set, one of them in its own column. It moves
to the lowest-keyed other column, over an N pin or under an S pin; the other pins keep their wire.
"""

from typing import TYPE_CHECKING

from fransys_layout.stages.attach import _entry, _first_pin, _wire_ends
from fransys_layout.stages.far_moves import _assembled, _moved_cells
from fransys_layout.stages.types import Home

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from fransys_layout.stages.types import (
        Cell,
        Column,
        Connection,
        DrawnFunction,
        Handle,
        PortRef,
    )
    from fransys_model.kernel import AuthoringKey

    type _Entry = tuple[Handle, str, int, Handle, str, bool]
    type _Home = Mapping[Handle, tuple[Column, Cell]]
    type _Pair = tuple[Column, Cell, PortRef, PortRef]  # the far end's column and cell, it, mine

_MIN_WIRES = 3  # two wires are a chain link: they move seven tests, V4 keeps them home


def own_group_homes(
    columns: tuple[Column, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    touching: Mapping[Handle, tuple[Connection, ...]],
    fits: Callable[[Column], bool],
) -> tuple[Column, ...]:
    """V4: move each own-group home terminal to its first far pin, unless `fits` says no."""
    home = {
        c.function: (col, c) for col in columns for c in col.cells if c.home is not Home.ELSEWHERE
    }
    busy = {c.host for col in columns for c in col.cells if c.host is not None}
    placed: dict[AuthoringKey, tuple[_Entry, ...]] = {}
    leaving: dict[AuthoringKey, frozenset[Handle]] = {}
    gone: set[Handle] = set()
    for column, terminal, host, found in _stars(columns, home, drawn_of, touching):
        entries = (*placed.get(host.key, ()), found)
        if terminal in busy or found[0] in gone or not fits(_moved_cells(host, entries)):
            continue
        placed[host.key] = entries
        leaving[column.key] = leaving.get(column.key, frozenset()) | {terminal}
        busy.add(found[0])
        gone.add(terminal)
    return _assembled(columns, placed, leaving)


def _stars(
    columns: tuple[Column, ...],
    home: _Home,
    drawn_of: Mapping[Handle, DrawnFunction],
    touching: Mapping[Handle, tuple[Connection, ...]],
) -> Iterator[tuple[Column, Handle, Column, _Entry]]:
    """Each home terminal cell's column, handle, host column and entry, where V4 applies."""
    for column in columns:
        for cell in column.cells:
            if cell.home is not Home.HERE or cell.host is not None:
                continue
            if not drawn_of[cell.function].roles.terminal:
                continue
            star = _own_star(cell, column, home, drawn_of, touching.get(cell.function, ()))
            if star is not None:
                yield column, cell.function, *star


def _own_star(
    cell: Cell,
    column: Column,
    home: _Home,
    drawn_of: Mapping[Handle, DrawnFunction],
    wires: tuple[Connection, ...],
) -> tuple[Column, _Entry] | None:
    """The host column and entry, `None` unless every pin is in `column`'s group and set."""
    pairs = _pairs(cell, home, wires)
    if pairs is None or not _all_in_set(column, pairs):
        return None
    outside = tuple(pair for pair in pairs if pair[0].key != column.key)
    if len(outside) == len(pairs) or not outside:
        return None  # a pin must stand in the own column, and one outside it
    other, own = _first_pin([(pair[2], pair[3]) for pair in outside], lambda f: home[f][0])
    host, far = home[other.function]
    if far.host is not None:
        return None
    found = _entry(drawn_of[cell.function], own, drawn_of[other.function], other)
    return None if found is None else (host, found)


def _pairs(cell: Cell, home: _Home, wires: tuple[Connection, ...]) -> tuple[_Pair, ...] | None:
    """Each wire's far end with its home, `None` with fewer than two wires or an unhomed end."""
    ends = _wire_ends(cell.function, wires)
    if len(ends) < _MIN_WIRES or any(other.function not in home for other, _ in ends):
        return None
    return tuple((*home[other.function], other, own) for other, own in ends)


def _all_in_set(column: Column, pairs: tuple[_Pair, ...]) -> bool:
    """Whether every far end's column is in `column`'s group and drawing set."""
    mine = (column.group, column.drawing_set_key)
    return all((far.group, far.drawing_set_key) == mine for far, *_ in pairs)
