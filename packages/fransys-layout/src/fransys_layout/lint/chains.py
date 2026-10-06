"""Lint: a chain the layout broke, as a stranded symbol or as a severed 2-port connection.

These are the designer's review metrics C0 (`LONE_CELL`) and C0b (`CHAIN_BROKEN`).
`lint_geometry` cannot host them: they read no `drawn` functions, no columns and no
connections, and which ports are wired and which cells a column holds are not in a `Layout`.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_layout.geometry import LayoutError
from fransys_layout.stages import MarkerSide
from fransys_layout.stages._polelinks import net_sizes, pole_ports
from fransys_model.kernel import Finding, Severity

from .codes import CHAIN_BROKEN, LONE_CELL

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import (
        Column,
        Connection,
        DrawnFunction,
        Handle,
        Layout,
        NetGroup,
    )
    from fransys_layout.stages.types import MatedFunctions

_NET_OF_TWO = 2


def mate_map(mates: tuple[MatedFunctions, ...]) -> dict[Handle, Handle]:
    """Each mated function or pin mapped to the one it is plugged into, in both directions."""
    found: dict[Handle, Handle] = {}
    for pair in mates:
        found[pair.a], found[pair.b] = pair.b, pair.a
    return found


@dataclass(frozen=True, slots=True)
class _Facts:
    """What the checks need of the stage records, and nothing else."""

    cells: Mapping[tuple[str, ...], frozenset[Handle]]
    unwired: frozenset[Handle]
    cuttable: Mapping[Handle, tuple[Handle, Handle]]


@dataclass(frozen=True, slots=True)
class StageRecords:
    """The stage records the chain lint reads beside the `Layout`: columns, drawn, wiring, mates."""

    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    mates: tuple[MatedFunctions, ...] = ()


def _facts(layout: Layout, records: StageRecords) -> _Facts:
    """Read the stage records, the only place that knows their shapes; raises `LayoutError`."""
    connections, net_groups = records.connections, records.net_groups
    by_function = {one.function: one for one in records.drawn}
    by_column = {one.key: one for one in records.columns}
    if any(one.function not in by_function for one in layout.placed):
        msg = "a placed function has no drawn function"
        raise LayoutError(msg)
    if any(one.column not in by_column for one in layout.placed):
        msg = "a placed function's column has no stage column"
        raise LayoutError(msg)
    wired = {
        *(end.port for one in connections for end in (one.a, one.b)),
        *(end.port for one in net_groups for end in one.ports),
        *(one.port for one in layout.markers),
    }
    on_wire = {
        function
        for function, one in by_function.items()
        if not wired.isdisjoint(p.port for p in one.ports)
    }
    mate_of = mate_map(records.mates)
    poles = {function: pole_ports(one) for function, one in by_function.items()}
    sizes = net_sizes(connections, net_groups)
    return _Facts(
        cells={
            key: frozenset(cell.function for cell in one.cells) for key, one in by_column.items()
        },
        unwired=frozenset(
            function
            for function in by_function
            if function not in on_wire and mate_of.get(function) not in on_wire
        ),
        cuttable={
            one.handle: (one.a.function, one.b.function)
            for one in connections
            if one.a.port in poles.get(one.a.function, frozenset())
            and one.b.port in poles.get(one.b.function, frozenset())
            and sizes[one.a.port] == _NET_OF_TWO
        },
    )


def lint_chains(
    layout: Layout,
    records: StageRecords,
    *,
    open_ends: frozenset[Handle] = frozenset(),
) -> tuple[Finding, ...]:
    """Report `LONE_CELL` and `CHAIN_BROKEN` warnings, sorted by `(code, subjects)`."""
    facts = _facts(layout, records)
    placed: defaultdict[tuple[int, int, tuple[str, ...]], set[Handle]] = defaultdict(set)
    for one in layout.placed:
        placed[(one.drawing_set, one.page, one.column)].add(one.function)
    findings = []
    seen: set[tuple[Handle, str]] = set()
    for (_, _, column), functions in placed.items():
        cut = len(functions) == 1 and not facts.cells[column] <= functions
        for function in functions:
            if cut:
                message = "a symbol stands alone on its page although its column has more cells"
            elif function in facts.unwired and function not in open_ends:
                message = "a symbol has no drawn conductor at all"
            else:
                continue
            if (function, message) in seen:
                continue
            seen.add((function, message))
            findings.append(
                Finding(
                    code=LONE_CELL,
                    severity=Severity.WARNING,
                    subjects=(function,),
                    message=message,
                )
            )
    findings.extend(
        Finding(
            code=CHAIN_BROKEN,
            severity=Severity.WARNING,
            subjects=(handle, *facts.cuttable[handle]),
            message="a connection between two cells was cut into a marker pair",
        )
        for handle in {
            one.connection
            for one in layout.markers
            if one.side is MarkerSide.OWNER and not one.star and one.connection in facts.cuttable
        }
    )
    return tuple(sorted(findings, key=lambda finding: (finding.code, finding.subjects)))
