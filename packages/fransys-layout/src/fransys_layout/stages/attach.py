"""Replica attachment and the hub order, the steps after replication (D6).

`replicate.py` adds the replica columns; here a replica terminal is attached to its host's
column (R7 B8) and a hub column is keyed between its branches (C11).
"""

from dataclasses import replace
from operator import itemgetter
from typing import TYPE_CHECKING

from fransys_layout.geometry import OPPOSITE
from fransys_layout.stages.columns import is_rack_key
from fransys_layout.stages.slices import by_key
from fransys_layout.stages.types import Cell, Column

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_layout.stages.types import (
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        PortRef,
    )
    from fransys_model.kernel import AuthoringKey

    type _Entry = tuple[Handle, str, int, Handle, str, bool]


def attach_replicas(
    columns: tuple[Column, ...],
    homes: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
) -> tuple[Column, ...]:
    """R7 B8, L9: a replica terminal with one wire in its group to an N or S port is attached."""
    home_keys = {column.key for column in homes}
    drawn_of = {one.function: one for one in drawn}
    home_of = {
        cell.function: column
        for column in columns
        if column.key in home_keys
        for cell in column.cells
    }
    # each function's connections, in connection order, once each
    touching = {
        function: tuple(c for _, c in pairs)
        for function, pairs in by_key(
            ((function, c) for c in connections for function in {c.a.function, c.b.function}),
            itemgetter(0),
        ).items()
    }
    found: dict[AuthoringKey, list[tuple[Handle, str, int, Handle, str, bool]]] = {}
    drop = set()
    for column in columns:
        if column.key in home_keys or len(column.cells) != 1:
            continue
        attached = _replica_host(column, home_of, drawn_of, touching)
        if attached is None:
            continue
        home_key, entry = attached
        found.setdefault(home_key, []).append(entry)
        drop.add(column.key)
    result = []
    for column in columns:
        if column.key in drop:
            continue
        if column.key not in found:
            result.append(column)
            continue
        result.append(_with_attached(column, found[column.key]))
    return attach_feeders(tuple(result), drawn)


def attach_feeders(
    columns: tuple[Column, ...], drawn: tuple[DrawnFunction, ...]
) -> tuple[Column, ...]:
    """layout-0107: a feeder box takes the row above the box it feeds, pin over pin (R7 B8)."""
    drawn_of = {one.function: one for one in drawn}
    feeder_of = {feed.feeder: feed for one in drawn if one.fed_by for feed in one.fed_by}
    home_of = {cell.function: column for column in columns for cell in column.cells}
    found: dict[AuthoringKey, list[tuple[Handle, str, int, Handle, str, bool]]] = {}
    drop = set()
    for column in columns:
        feed = feeder_of.get(column.cells[0].function) if len(column.cells) == 1 else None
        host = home_of.get(feed.fed) if feed is not None else None
        if feed is None or host is None or host is column:
            continue
        if (host.group, host.unit) != (column.group, column.unit):
            continue
        feeder = drawn_of[column.cells[0].function]
        mate = next(
            a
            for a, b in ((p.fed, p.feeder) for p in feed.ports)
            if _symbol_of(feeder, b) == feeder.primary_out
        )
        symbol = _symbol_of(drawn_of[feed.fed], mate)
        x = next(g.at.x for g in drawn_of[feed.fed].geometry.ports if g.name == symbol)
        found.setdefault(host.key, []).append((feed.fed, "n", x, feeder.function, symbol, False))
        drop.add(column.key)
    return tuple(
        _with_attached(column, found[column.key], replica=False) if column.key in found else column
        for column in columns
        if column.key not in drop
    )


def _symbol_of(one: DrawnFunction, port: Handle) -> str:
    """The symbol port `port` is drawn at on `one`."""
    return next(p.symbol_port for p in one.ports if p.port == port)


def _replica_host(
    column: Column,
    home_of: Mapping[Handle, Column],
    drawn_of: Mapping[Handle, DrawnFunction],
    touching: Mapping[Handle, tuple[Connection, ...]],
) -> tuple[AuthoringKey, tuple[Handle, str, int, Handle, str, bool]] | None:
    """R7 B8, V4: a replica terminal's host column key and attachment entry, `None` with no host."""
    terminal = column.cells[0].function
    hosts = [
        (other, own)
        for other, own in _wire_ends(terminal, touching.get(terminal, ()))
        if other.function in home_of
        and home_of[other.function].group == column.group
        and home_of[other.function].unit == column.unit  # never into another unit's set
    ]
    if not hosts:
        return None
    other, own = _first_pin(hosts, home_of.__getitem__)
    found = _entry(drawn_of[terminal], own, drawn_of[other.function], other)
    return None if found is None else (home_of[other.function].key, found)


def _wire_ends(terminal: Handle, wires: Sequence[Connection]) -> list[tuple[PortRef, PortRef]]:
    """Each wire of `terminal` as (far end, own end), in connection order."""
    return [(c.b, c.a) if c.a.function == terminal else (c.a, c.b) for c in wires]


def _first_pin(
    ends: Sequence[tuple[PortRef, PortRef]], column_of: Callable[[Handle], Column]
) -> tuple[PortRef, PortRef]:
    """V4: the far end in the lowest-keyed column, where a terminal is drawn once per page."""
    return min(ends, key=lambda pair: column_of(pair[0].function).key)


def _entry(mine: DrawnFunction, own: PortRef, far: DrawnFunction, other: PortRef) -> _Entry | None:
    """The attachment entry at the far pin's port, `None` unless it faces N or S."""
    symbol = next(p.symbol_port for p in far.ports if p.port == other.port)
    geometry = next(g for g in far.geometry.ports if g.name == symbol)
    facing = geometry.facing.value
    if facing not in ("n", "s"):
        return None
    own_symbol = next(p.symbol_port for p in mine.ports if p.port == own.port)
    own_facing = next(g.facing.value for g in mine.geometry.ports if g.name == own_symbol)
    return (
        other.function,
        facing,
        geometry.at.x,
        mine.function,
        symbol,
        own_facing != OPPOSITE[geometry.facing].value,
    )


def _with_attached(
    column: Column,
    attached: Sequence[tuple[Handle, str, int, Handle, str, bool]],
    *,
    replica: bool = True,
) -> Column:
    """R7 B8: `column` with each attached replica above its N host or below its S host (L9)."""
    rows = by_key(column.cells, lambda cell: cell.index)
    cells = []
    index = 0
    for key in sorted(rows):
        row = rows[key]
        hosts = {cell.function for cell in row}
        above = sorted(a for a in attached if a[0] in hosts and a[1] == "n")
        below = sorted(a for a in attached if a[0] in hosts and a[1] == "s")
        for group in (above, None, below):
            if group is None:
                cells.extend(replace(cell, index=index) for cell in row)
                index += 1
                continue
            if not group:
                continue
            cells.extend(
                Cell(
                    function=terminal,
                    index=index,
                    lane=lane,
                    flip=flip,
                    host=host,
                    port=symbol,
                    replica=replica,
                )
                for lane, (host, _, _, terminal, symbol, flip) in enumerate(
                    sorted(group, key=lambda a: a[2])
                )
            )
            index += 1
    return replace(column, cells=tuple(cells))


def hub_order(
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    connections: tuple[Connection, ...],
    replicas: frozenset[AuthoringKey],
) -> tuple[tuple[Column, ...], frozenset[AuthoringKey]]:
    """C11: a hub column is keyed right after its lowest-keyed branch; `replicas` rename with it."""
    spec_of = {spec.function: spec for spec in specs}
    home = {
        cell.function: column for column in columns for cell in column.cells if not cell.replica
    }
    partners: dict[Handle, set[Handle]] = {}
    for c in connections:
        partners.setdefault(c.a.function, set()).add(c.b.function)
        partners.setdefault(c.b.function, set()).add(c.a.function)
    rekey = {}
    for column in columns:
        for cell in column.cells:
            if cell.host is not None or cell.function not in spec_of:
                continue
            kind = spec_of[cell.function].kind
            branches = sorted(
                {
                    home[f].key
                    for f in partners.get(cell.function, ())
                    if f in home
                    and home[f].key != column.key
                    and home[f].group == column.group
                    and spec_of.get(f) is not None
                    and spec_of[f].kind == kind
                }
            )
            # F1: a rack module's column keeps its slot: the authored order wins
            if len(branches) >= 2 and column.key not in rekey and not is_rack_key(column.key):  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
                # the column key is appended: two hubs of a ring share a lowest branch
                rekey[column.key] = (*branches[0], "hub", *column.key)
    return (
        tuple(
            replace(column, key=rekey[column.key]) if column.key in rekey else column
            for column in columns
        ),
        frozenset(rekey.get(key, key) for key in replicas),
    )
