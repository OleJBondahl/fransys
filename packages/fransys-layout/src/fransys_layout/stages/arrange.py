"""Column arrangement before replication, and the in-line exits (D6).

The steps between chain discovery and `replicate.py`: the same-unit connectivity
discovery follows, the edge mates, the cut at a location change, the joined strip rows, the
rack order, and the exits of an in-line terminal.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Sequence

from fransys_layout.conventions import FACTS
from fransys_layout.geometry import OPPOSITE
from fransys_layout.stages.columns import build_column
from fransys_layout.stages.lookups import group_of
from fransys_layout.stages.slices import by_key
from fransys_layout.stages.terminal_facts import TerminalRead
from fransys_layout.stages.types import (
    EDGE_KIND,
    Cell,
    Column,
    FunctionSpec,
    Home,
    MatedFunctions,
    PortRef,
)
from fransys_model.kernel import Id

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import Connection, DrawnFunction, Handle, NetGroup
    from fransys_model.kernel import AuthoringKey

# a rack position (an int, possibly below zero) as 20 digits that sort as the number does
_POSITION_OFFSET = 2**63


def same_unit_connectivity(
    functions: tuple[FunctionSpec, ...],
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    mates: tuple[MatedFunctions, ...],
) -> tuple[tuple[Connection, ...], tuple[NetGroup, ...], tuple[MatedFunctions, ...]]:
    """Same-unit connectivity for discovery; L5: a boundary wire is two stand-in halves (U1, U2)."""
    unit_of = {spec.function: spec.unit for spec in functions}
    kept = []
    for c in connections:
        edge = EDGE_KIND in (c.a.function.kind, c.b.function.kind)  # W3: already ends at the edge
        if edge or unit_of.get(c.a.function) == unit_of.get(c.b.function):
            kept.append(c)
            continue
        for index, (end, other) in enumerate(((c.a, c.b), (c.b, c.a))):
            stub = Id(kind=EDGE_KIND, value=f"{other.port.value}-{index}")
            handle = c.handle if index == 0 else Id(kind=c.handle.kind, value=f"{c.handle.value}-b")
            kept.append(replace(c, handle=handle, a=end, b=PortRef(function=stub, port=stub)))
    connections = tuple(kept)
    net_groups = tuple(
        g for g in net_groups if len({unit_of.get(ref.function) for ref in g.ports}) <= 1
    )
    mates = tuple(m for m in mates if unit_of.get(m.a) == unit_of.get(m.b))
    return connections, net_groups, mates


def edge_mates(
    parent_of: Mapping[Id[Any], frozenset[Id[Any] | None]],
    functions: tuple[FunctionSpec, ...],
    mates: tuple[MatedFunctions, ...],
) -> tuple[MatedFunctions, ...]:
    """I2a: each pin mated across a unit boundary, as (pin, boundary pin) face to face (U1)."""
    spec_of = {spec.function: spec for spec in functions}
    found = []
    for mate in mates:
        for a, b in ((mate.a, mate.b), (mate.b, mate.a)):
            edge = spec_of.get(b)
            if edge is None or spec_of.get(a) is None:
                continue
            owner = edge.pin_function or edge.function
            if (
                owner in parent_of
                and edge.unit != spec_of[a].unit
                and spec_of[a].unit in parent_of[owner]
            ):
                found.append(MatedFunctions(a=a, b=b))
    return tuple(found)


def _location_runs(
    column: Column, spec_of: Mapping[Id[Any], FunctionSpec]
) -> tuple[dict[int, tuple[Cell, ...]], list[tuple[Id[Any] | None, list[int]]]]:
    """A column's rows by index, and its runs of rows sharing one top-level location (C21)."""

    def top(function: Id[Any]) -> Id[Any] | None:
        path = spec_of[function].location_path
        return path[0] if path else None

    rows = by_key(column.cells, lambda cell: cell.index)
    where = {}
    for index, row in rows.items():
        own = {top(c.function) for c in row if c.host is None}
        where[index] = own.pop() if len(own) == 1 else None
    hosted = {c.function: c.index for c in column.cells if c.host is None}
    for index, row in rows.items():
        if where[index] is None and all(c.host is not None for c in row):
            where[index] = where.get(hosted.get(row[0].host))
    runs: list[tuple[Id[Any] | None, list[int]]] = []
    for index in sorted(rows):
        if runs and where[index] in (runs[-1][0], None):
            runs[-1][1].append(index)
        else:
            runs.append((where[index], [index]))
    return rows, runs


def cut_locations(
    columns: tuple[Column, ...], specs: tuple[FunctionSpec, ...]
) -> tuple[Column, ...]:
    """C21: each column cut where its rows' top-level location changes; attachments follow hosts."""
    spec_of = {spec.function: spec for spec in specs}
    found = []
    for column in columns:
        rows, runs = _location_runs(column, spec_of)
        if len(runs) < 2:  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
            found.append(column)
            continue
        for number, (_, indexes) in enumerate(runs):
            cells = tuple(
                replace(cell, index=position)
                for position, index in enumerate(indexes)
                for cell in rows[index]
            )
            members = [spec_of[c.function] for c in cells if c.host is None]
            head = members[0]
            key = column.key if number == 0 else ("chain", head.designation, *head.key)
            found.append(build_column(key, cells, members))
    return tuple(found)


def _strip_rows(
    columns: tuple[Column, ...], spec_of: Mapping[Id[Any], FunctionSpec]
) -> dict[tuple[Id[Any] | None, str], tuple[AuthoringKey, int]]:
    """The first `(column key, row index)` of each strip in each group, in a non-terminal column."""
    strip_row: dict[tuple[Id[Any] | None, str], tuple[AuthoringKey, int]] = {}
    for column in columns:
        if all(spec_of[c.function].roles.terminal for c in column.cells):
            continue
        for cell in column.cells:
            one = spec_of[cell.function]
            if one.roles.terminal and one.strip_text and cell.host is None:
                strip_row.setdefault((group_of(one), one.strip_text), (column.key, cell.index))
    return strip_row


def _strip_moves(
    columns: tuple[Column, ...],
    spec_of: Mapping[Id[Any], FunctionSpec],
    strip_row: Mapping[tuple[Id[Any] | None, str], tuple[AuthoringKey, int]],
) -> tuple[dict[AuthoringKey, list[tuple[int, Cell]]], set[AuthoringKey]]:
    """Each joining terminal cell by the column key it joins, and the column keys dropped."""
    moves: dict[AuthoringKey, list[tuple[int, Cell]]] = {}
    dropped = set()
    for column in columns:
        cells = [c for c in column.cells if c.host is None]
        # C21: a column carrying attachments keeps them, so it is not joined away
        if (
            not cells
            or len(cells) != len(column.cells)
            or any(not spec_of[c.function].roles.terminal for c in column.cells)
        ):
            continue
        targets = [
            strip_row.get((group_of(spec_of[c.function]), spec_of[c.function].strip_text))
            for c in cells
        ]
        found = [t for t in targets if t is not None]
        if len(found) != len(targets) or len({t[0] for t in found}) != 1:
            continue
        dropped.add(column.key)
        for cell, (key, index) in zip(cells, found, strict=True):
            moves.setdefault(key, []).append((index, cell))
    return moves, dropped


def _with_joined(
    column: Column, joined: Sequence[tuple[int, Cell]], spec_of: Mapping[Id[Any], FunctionSpec]
) -> Column:
    """`column` with each `(row index, terminal cell)` of `joined` added as the row's next lane."""
    cells = list(column.cells)
    for index, cell in joined:
        lane = 1 + max(c.lane for c in cells if c.index == index)
        # C21: one strip row, one orientation: the joiner takes the row's flip
        strip = spec_of[cell.function].strip_text
        flip = next(
            (c.flip for c in cells if c.index == index and spec_of[c.function].strip_text == strip),
            cell.flip,
        )
        cells.append(Cell(function=cell.function, index=index, lane=lane, flip=flip))
    return replace(column, cells=tuple(cells))


def join_strip_rows(
    columns: tuple[Column, ...], specs: tuple[FunctionSpec, ...]
) -> tuple[Column, ...]:
    """C15(i): a terminals-only column joins another's rows as the next lane (X3:PE by X3 U V W)."""
    spec_of = {spec.function: spec for spec in specs}
    moves, dropped = _strip_moves(columns, spec_of, _strip_rows(columns, spec_of))
    result = []
    for column in columns:
        if column.key in dropped:
            continue
        if column.key in moves:
            result.append(_with_joined(column, moves[column.key], spec_of))
            continue
        result.append(column)
    return tuple(result)


def rack_order(columns: tuple[Column, ...], specs: tuple[FunctionSpec, ...]) -> tuple[Column, ...]:
    """F1: a rack's modules run in authored order, keyed by the lowest slot (layout-0077)."""
    spec_of = {spec.function: spec for spec in specs}

    def slot(column: Column) -> tuple[str, str] | None:
        found = []
        for cell in column.cells:
            spec = spec_of.get(cell.function)
            if (
                spec is None
                or spec.rack_position is None
                or cell.home is Home.ELSEWHERE
                or cell.host
            ):
                continue
            group = group_of(spec)
            if group == column.group:
                found.append((spec.rack, f"{spec.rack_position + _POSITION_OFFSET:020d}"))
        return min(found, default=None)

    return tuple(
        column if (at := slot(column)) is None else replace(column, key=("rack", *at, *column.key))
        for column in columns
    )


def _wires_at(connections: tuple[Connection, ...]) -> dict[Id[Any], int]:
    """The number of connections with an end on each model port."""
    wires_at: dict[Id[Any], int] = {}
    for c in connections:
        for port in {c.a.port, c.b.port}:
            wires_at[port] = wires_at.get(port, 0) + 1
    return wires_at


def _is_inline_exit(
    ref: PortRef,
    other: PortRef,
    spec_of: Mapping[Handle, FunctionSpec],
    index: Mapping[Handle, tuple[AuthoringKey, int]],
    wired: int,
) -> bool:
    """Whether `ref` is an in-line terminal end with `other` further down its own column."""
    spec = spec_of.get(ref.function)
    here, there = index.get(ref.function), index.get(other.function)
    return (
        spec is not None
        and bool(
            FACTS["inline_terminal"].func(TerminalRead(spec.roles.terminal, len(spec.ports), wired))
        )
        and here is not None
        and there is not None
        and here[0] == there[0]
        and there[1] > here[1]
    )


def _opposite_port(d: DrawnFunction, ref: PortRef) -> str:
    """The symbol port facing away from the one `ref` is bound to."""
    bound = next(p.symbol_port for p in d.ports if p.port == ref.port)
    facing = next(g.facing for g in d.geometry.ports if g.name == bound)
    return next(g.name for g in d.geometry.ports if g.facing == OPPOSITE[facing])


def inline_exits(
    connections: tuple[Connection, ...],
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    drawn: tuple[DrawnFunction, ...],
) -> tuple[Connection, ...]:
    """R7 B5: an in-line one-port terminal's lower wire lands on the port opposite the bound one."""
    spec_of = {spec.function: spec for spec in specs}
    drawn_by = {one.function: one for one in drawn}
    index = {
        cell.function: (column.key, cell.index)
        for column in columns
        for cell in column.cells
        if not cell.side
    }
    wires_at = _wires_at(connections)
    found = []
    for connection in connections:
        ends = []
        for ref, other in ((connection.a, connection.b), (connection.b, connection.a)):
            if _is_inline_exit(ref, other, spec_of, index, wires_at[ref.port]):
                opposite = _opposite_port(drawn_by[ref.function], ref)
                ends.append(replace(ref, symbol_port=opposite))
            else:
                ends.append(ref)
        found.append(replace(connection, a=ends[0], b=ends[1]))
    return tuple(found)
