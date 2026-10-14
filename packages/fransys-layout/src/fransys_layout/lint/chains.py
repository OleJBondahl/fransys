"""Lint: a chain the layout broke, as a stranded symbol or as a severed 2-port connection.

These are the review metrics C0 (`LONE_CELL`) and C0b (`CHAIN_BROKEN`).
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
from .printed import on_printed

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import (
        Column,
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        Layout,
        NetGroup,
    )
    from fransys_layout.stages.types import MatedFunctions

_NET_OF_TWO = 2
_STRANDED = "a symbol stands alone on its page although its column has more cells"


@dataclass(frozen=True, slots=True)
class _Facts:
    """What the checks need of the stage records, and nothing else."""

    cells: Mapping[tuple[str, ...], frozenset[Handle]]
    cuttable: Mapping[Handle, tuple[Handle, Handle]]
    kinds: Mapping[Handle, str]


@dataclass(frozen=True, slots=True)
class StageRecords:
    """The stage records the chain lint reads beside the `Layout`: columns, drawn, wiring, mates."""

    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    loose: tuple[FunctionSpec, ...] = ()  # layout-0218: drawn on no page (`function_is_loose`)


def mate_map(mates: tuple[MatedFunctions, ...]) -> dict[Handle, Handle]:
    """Each mated function or pin mapped to the one it is plugged into, in both directions."""
    found: dict[Handle, Handle] = {}
    for pair in mates:
        found[pair.a], found[pair.b] = pair.b, pair.a
    return found


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
    poles = {function: pole_ports(one) for function, one in by_function.items()}
    sizes = net_sizes(connections, net_groups)
    return _Facts(
        cells={
            key: frozenset(cell.function for cell in one.cells) for key, one in by_column.items()
        },
        cuttable={
            one.handle: (one.a.function, one.b.function)
            for one in connections
            if one.a.port in poles.get(one.a.function, frozenset())
            and one.b.port in poles.get(one.b.function, frozenset())
            and sizes[one.a.port] == _NET_OF_TWO
        },
        kinds={function: one.kind for function, one in by_function.items()},
    )


def _split_by_pages(
    ends: tuple[Handle, Handle],
    kinds: Mapping[Handle, str],
    pages: Mapping[Handle, set[tuple[int, int]]],
) -> bool:
    """Whether a link joins a coil and a contact that share no page: the intended IEC split."""
    coil, other = sorted(kinds[end] for end in ends)  # "coil" sorts before "contact_*"
    return (
        coil == "coil" and other.startswith("contact") and pages[ends[0]].isdisjoint(pages[ends[1]])
    )


def lone_cells(
    layout: Layout, records: StageRecords
) -> tuple[tuple[tuple[int, int], Finding], ...]:
    """Each `LONE_CELL` with the `(drawing set, page)` it is on; a function on two pages twice."""
    return _lone_cells(layout, _facts(layout, records))


def _lone_cells(layout: Layout, facts: _Facts) -> tuple[tuple[tuple[int, int], Finding], ...]:
    """Pass 1 of `lint_chains`: the lone cells by page, a column's cells in set order."""
    placed: defaultdict[tuple[int, int, tuple[str, ...]], set[Handle]] = defaultdict(set)
    for one in layout.placed:
        placed[(one.drawing_set, one.page, one.column)].add(one.function)
    found = []
    for (drawing_set, page, column), functions in placed.items():
        if len(functions) > 1 or facts.cells[column] <= functions:
            continue
        found.extend(
            (
                (drawing_set, page),
                Finding(
                    code=LONE_CELL, severity=Severity.WARNING, subjects=(one,), message=_STRANDED
                ),
            )
            for one in functions
        )
    return tuple(found)


def loose_findings(loose: tuple[FunctionSpec, ...]) -> tuple[Finding, ...]:
    """layout-0218: one `LONE_CELL` per function with nothing connected, at no page."""
    return tuple(
        Finding(
            code=LONE_CELL,
            severity=Severity.WARNING,
            subjects=(spec.function,),
            message=(
                "a symbol has nothing connected, so it is not drawn: "
                f"wire {_listed(tuple(p.name for p in spec.ports))}, or remove it if it is not used"
            ),
        )
        for spec in loose
    )


def _listed(names: tuple[str, ...]) -> str:
    """`A1`, `A1 and A2`, `1, 2 and 3`."""
    return " and ".join([", ".join(names[:-1]), names[-1]]) if len(names) > 1 else "".join(names)


def lint_chains(
    layout: Layout,
    records: StageRecords,
    *,
    printed: frozenset[int] | None = None,
) -> tuple[Finding, ...]:
    """Report `LONE_CELL` and `CHAIN_BROKEN` warnings, sorted by `(code, subjects)`.

    A lone cell on a set that is not in `printed` is left out (model-0201).
    """
    facts = _facts(layout, records)
    pages: defaultdict[Handle, set[tuple[int, int]]] = defaultdict(set)
    for one in layout.placed:
        pages[one.function].add((one.drawing_set, one.page))
    seen: set[tuple[Handle, str]] = set()
    findings = []
    for here, finding in _lone_cells(layout, facts):
        if not on_printed(here, printed):
            continue
        if (finding.subjects[0], finding.message) not in seen:
            seen.add((finding.subjects[0], finding.message))
            findings.append(finding)
    findings.extend(loose_findings(records.loose))
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
            if one.side is MarkerSide.OWNER
            and not one.star
            and one.connection in facts.cuttable
            and not _split_by_pages(facts.cuttable[one.connection], facts.kinds, pages)
        }
    )
    return tuple(sorted(findings, key=lambda finding: (finding.code, finding.subjects)))
