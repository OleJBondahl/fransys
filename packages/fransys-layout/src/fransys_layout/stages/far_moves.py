"""The cell moves V5 and the own-group V4 case share: attach a home cell, compact what left."""

from dataclasses import replace
from operator import itemgetter
from typing import TYPE_CHECKING

from fransys_layout.stages.attach import _with_attached
from fransys_layout.stages.slices import by_key
from fransys_layout.stages.types import Home

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.types import (
        Cell,
        Column,
        Connection,
        Handle,
    )
    from fransys_model.kernel import AuthoringKey

    type _Entry = tuple[Handle, str, int, Handle, str, bool]
    type _Touching = Mapping[Handle, tuple[Connection, ...]]


def _is_moving(
    far: Handle,
    mine: Handle,
    placed: Mapping[AuthoringKey, tuple[_Entry, ...]],
    leaving: Mapping[AuthoringKey, frozenset[Handle]],
) -> bool:
    """Whether the far pin's function is itself leaving, or `mine` already hosts a moved cell."""
    gone = frozenset().union(*leaving.values())
    hosting = {entry[0] for entries in placed.values() for entry in entries}
    return far in gone or mine in hosting


def _assembled(
    columns: tuple[Column, ...],
    placed: Mapping[AuthoringKey, tuple[_Entry, ...]],
    leaving: Mapping[AuthoringKey, frozenset[Handle]],
) -> tuple[Column, ...]:
    """`columns` without the cells that left, each host with its moved cells attached."""
    result = []
    for column in columns:
        kept = tuple(c for c in column.cells if c.function not in leaving.get(column.key, ()))
        if not kept:
            continue
        base = replace(column, cells=_compact(kept)) if len(kept) < len(column.cells) else column
        result.append(_moved_cells(base, placed[column.key]) if column.key in placed else base)
    return tuple(result)


def _compact(cells: tuple[Cell, ...]) -> tuple[Cell, ...]:
    """The cells with their row indexes renumbered from 0, rows in the same order."""
    rows = {index: n for n, index in enumerate(sorted({c.index for c in cells}))}
    return tuple(replace(c, index=rows[c.index]) for c in cells)


def _touching(connections: tuple[Connection, ...]) -> _Touching:
    """Each function's connections, in connection order, once each."""
    return {
        function: tuple(c for _, c in pairs)
        for function, pairs in by_key(
            ((function, c) for c in connections for function in {c.a.function, c.b.function}),
            itemgetter(0),
        ).items()
    }


def _moved_cells(host: Column, entries: Sequence[_Entry]) -> Column:
    """`host` with each entry attached as a home cell (`moved`), not a replica."""
    attached = _with_attached(host, entries)
    moving = {entry[3] for entry in entries}
    return replace(
        attached,
        cells=tuple(
            replace(cell, home=Home.MOVED) if cell.function in moving else cell
            for cell in attached.cells
        ),
    )
