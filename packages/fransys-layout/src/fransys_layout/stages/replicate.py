"""Replication of terminals and boundary functions, and the replica drops (layout-0021).

Terminal replication runs between `columns` and `column_widths`; the replica drops run after
`partition`. Attaching a replica to its host's column and the hub order are in `attach.py`.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_layout.geometry import LayoutError
from fransys_layout.stages.boundary_specs import boundary_replica, unit_specs
from fransys_layout.stages.columns import replica_key
from fransys_layout.stages.idle_copies import without_idle_copies
from fransys_layout.stages.page_copies import with_page_copies
from fransys_layout.stages.references.nets import star_wires
from fransys_layout.stages.types import Cell, Column, Home

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages.pagerun import PageInputs
    from fransys_layout.stages.types import (
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        PagePlan,
        PortRef,
    )
    from fransys_model.kernel import AuthoringKey


@dataclass(frozen=True, slots=True)
class UnitBoundary:
    """One unit's boundary, as `replicate_boundaries` reads it."""

    functions: tuple[Handle, ...]
    parent: Handle | None
    parent_key: AuthoringKey | None


def replicate_terminals(
    columns: tuple[Column, ...],
    functions: tuple[FunctionSpec, ...],
    connections: tuple[Connection, ...],
) -> tuple[Column, ...]:
    """One replica column per terminal and group a connection needs (layout-0076, 0081)."""
    specs = {spec.function: spec for spec in functions}
    home = {cell.function: column for column in columns for cell in column.cells}
    askers: defaultdict[tuple[Handle, Handle | None], dict[Handle, Column]] = defaultdict(dict)
    for wire in connections:
        a, b = _checked(wire.a, specs, home), _checked(wire.b, specs, home)
        a_is_terminal = specs[a.function].roles.terminal
        b_is_terminal = specs[b.function].roles.terminal
        if a_is_terminal and b_is_terminal:
            # A terminal ending its column (a group split) heads the next group's column
            # as a replica, when the other terminal heads that column
            split = _split_pair(a, b, home) or _split_pair(b, a, home)
            if split is None:
                continue
            terminal, other = split
        elif a_is_terminal == b_is_terminal:
            continue
        else:
            terminal, other = (a, b) if a_is_terminal else (b, a)
        served = home[other.function]
        terminal_home = home[terminal.function]
        if served.drawing_set_key != terminal_home.drawing_set_key:
            continue
        if served.group != terminal_home.group:
            askers[terminal.function, served.group][other.function] = served
    replicas = []
    for (terminal, _), asking in askers.items():
        served = asking[min(asking)]
        replicas.append(
            Column(
                key=replica_key(served.key, specs[terminal].key),
                cells=(Cell(function=terminal, index=0, home=Home.ELSEWHERE),),
                group=served.group,
                role=served.role,
                location=served.location,
                unit=served.unit,
            )
        )
    return tuple(
        sorted(
            (*_without_rail_homes(columns, functions), *replicas),
            key=lambda column: (column.key, tuple(cell.function for cell in column.cells)),
        )
    )


def _checked(
    ref: PortRef, specs: Mapping[Handle, FunctionSpec], home: Mapping[Handle, Column]
) -> PortRef:
    if ref.function not in specs or ref.function not in home:
        msg = "a connection names a function that is in no column or has no spec"
        raise LayoutError(msg)
    return ref


def _split_pair(
    one: PortRef, other: PortRef, home: Mapping[Handle, Column]
) -> tuple[PortRef, PortRef] | None:
    """`(one, other)` when `one` is the last cell of its column and `other` the first of its."""
    mine, theirs = home[one.function], home[other.function]
    if mine.key == theirs.key:
        return None
    tail = next((c for c in mine.cells if c.function == one.function), None)
    at_end = tail is not None and not any(
        c.lane == tail.lane and c.index > tail.index and c.host is None for c in mine.cells
    )  # the end of its lane (a strip row's later lane)
    head = next((c for c in theirs.cells if c.function == other.function), None)
    at_head = (
        head is not None
        and not any(
            c.lane == head.lane and c.index < head.index and c.host is None for c in theirs.cells
        )
        and any(
            c.index > head.index and c.host is None and c.lane == head.lane for c in theirs.cells
        )
    )  # the head of its lane (lanes start at different rows) with a chain below it
    # in that lane (X1:PE heading the feed row has none, Q1 below is other lanes')
    return (one, other) if at_end and at_head else None


def replicate_boundaries(
    columns: tuple[Column, ...],
    units: tuple[UnitBoundary, ...],
    functions: tuple[FunctionSpec, ...],
    homes: tuple[Column, ...],
) -> tuple[Column, ...]:
    """Every column, plus one black-box replica per boundary function of every unit.

    A function with pin views is its pin cells' replicas, else its own spec's (model-0188).
    """
    specs = {spec.function: spec for spec in functions}
    pins: dict[Handle, list[FunctionSpec]] = {}
    for spec in functions:
        if spec.pin_function is not None:
            pins.setdefault(spec.pin_function, []).append(spec)
    home = {
        cell.function: column
        for column in homes
        for cell in column.cells
        if cell.home is not Home.ELSEWHERE
    }
    # A boundary pin already drawn face to face under its mate in the parent's set
    faced = {
        (cell.function, column.unit)
        for column in columns
        for cell in column.cells
        if cell.home is Home.ELSEWHERE
    }
    replicas = []
    for unit in units:
        for spec in unit_specs(unit.functions, specs, pins):
            if (spec.function, unit.parent) in faced:
                continue
            home_column = home.get(spec.function)
            if home_column is None:
                msg = "a unit's boundary names a function that is in no column"
                raise LayoutError(msg)
            replicas.append(boundary_replica(spec, unit.parent, unit.parent_key, home_column))
    return tuple(
        sorted(
            (*_without_rail_homes(columns, functions), *replicas),
            key=lambda column: (column.key, tuple(cell.function for cell in column.cells)),
        )
    )


def _without_rail_homes(
    columns: tuple[Column, ...], functions: tuple[FunctionSpec, ...]
) -> tuple[Column, ...]:
    """Columns without the home cells of boundary rail terminals (the parent draws them)."""
    rails = {spec.function for spec in functions if spec.home is Home.ELSEWHERE}
    kept = (
        replace(
            column,
            cells=tuple(
                c for c in column.cells if c.home is Home.ELSEWHERE or c.function not in rails
            ),
        )
        for column in columns
    )
    return tuple(column for column in kept if column.cells)


def drop_replicas(plans: tuple[PagePlan, ...], columns: tuple[Column, ...]) -> tuple[PagePlan, ...]:
    """Drop each replica column whose page already holds its terminal, after `partition`."""
    by_key = {column.key: column for column in columns}
    result = []
    for plan in plans:
        if any(planned.column not in by_key for planned in plan.columns):
            msg = "a plan names a column that is not a column of the run"
            raise LayoutError(msg)
        held = {
            cell.function
            for planned in plan.columns
            for cell in by_key[planned.column].cells
            if cell.home is not Home.ELSEWHERE
        }
        kept = []
        for planned in plan.columns:
            if by_key[planned.column].away:
                terminal = by_key[planned.column].cells[0].function
                if terminal in held:
                    continue
                held.add(terminal)
            kept.append(planned)
        result.append(replace(plan, columns=tuple(kept)))
    return tuple(result)


def drop_attached_replicas(
    plans: tuple[PagePlan, ...], columns: tuple[Column, ...]
) -> tuple[Column, ...]:
    """An attached replica on a page that already holds its terminal is dropped."""
    page_of = {
        planned.column: plan_index
        for plan_index, plan in enumerate(plans)
        for planned in plan.columns
    }
    held: dict[int | None, set[Handle]] = {}
    for column in columns:
        if column.key in page_of:
            for cell in column.cells:
                if cell.home is not Home.ELSEWHERE:
                    held.setdefault(page_of[column.key], set()).add(cell.function)
    result = []
    for column in columns:
        page = page_of.get(column.key)
        kept = []
        for cell in column.cells:
            if cell.home is Home.ELSEWHERE:
                if cell.function in held.get(page, ()):
                    continue  # home or an earlier replica already on this page
                held.setdefault(page, set()).add(cell.function)
            kept.append(cell)
        same = len(kept) == len(column.cells)
        result.append(column if same else replace(column, cells=tuple(kept)))
    return tuple(result)


def planned_columns(
    plans: tuple[PagePlan, ...],
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    inputs: PageInputs,
) -> tuple[tuple[PagePlan, ...], tuple[Column, ...]]:
    """The planned pages and columns: replicas dropped, then each terminal on each wire's page.

    layout-0216: a terminal stands on every page a wire of it ends on, never a reference there,
    and a copy that then draws no wire goes; a star net's wires wait for the copies at each wire.
    """
    plans = drop_replicas(plans, columns)
    terminals = {spec.function for spec in inputs.functions if spec.roles.terminal}
    starred = {c.handle for c in star_wires(inputs.connections, inputs.functions, columns)}
    ends = [
        (own, far)
        for c in inputs.connections
        if c.handle not in starred
        for own, far in ((c.a, c.b), (c.b, c.a))
        if own.function in terminals and far.function not in terminals
    ]
    columns = with_page_copies(plans, drop_attached_replicas(plans, columns), drawn, ends)
    return without_idle_copies(plans, columns, _links(inputs, terminals, starred))


def _links(
    inputs: PageInputs, terminals: AbstractSet[Handle], starred: AbstractSet[Handle]
) -> list[tuple[Handle, Handle]]:
    """Each wire of a terminal under the drop: none the caller keeps whole, none of a star."""
    held = {
        f for c in inputs.connections if c.handle in starred for f in (c.a.function, c.b.function)
    }
    return [
        (own.function, far.function)
        for c in inputs.connections
        for own, far in ((c.a, c.b), (c.b, c.a))
        if own.function in terminals - held - inputs.whole
    ]
