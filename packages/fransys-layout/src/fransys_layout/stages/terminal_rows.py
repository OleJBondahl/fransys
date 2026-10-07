"""S20 M12 (ADDENDUM 19 fix 3): the terminals of one strip wired to each other stand in one row.

A chain is the terminals of one strip (one group) whose ports on one side are wired to each
other, connected through those conductors: a run of jumpered terminals. It stands in one row of
one column, one lane per terminal in the strip's terminal-list order (`tie_key`), so its links
are wires on one line below the row (bottom ports) or above it (top ports), never references.
`terminal_chains` is the one definition of the set; `join_terminal_rows` builds the rows.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.columns import build_column
from fransys_layout.stages.lookups import group_of
from fransys_layout.stages.types import Cell, Column, Home
from fransys_model.kernel import Id, UnionFind, value

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_layout.stages.types import Connection, DrawnFunction, FunctionSpec


@value
class TerminalChains:
    """The chains of one run, derived once before the columns are joined (ADDENDUM 20 Q3)."""

    sets: tuple[tuple[Id[Any], ...], ...] = ()
    links: tuple[Id[Any], ...] = ()


NO_CHAINS = TerminalChains()


def terminal_chains(
    specs: tuple[FunctionSpec, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
) -> TerminalChains:
    """The chains: sets of two or more terminals of one strip linked through same-side wires."""
    spec_of = {spec.function: spec for spec in specs}
    facing = _facings(drawn)
    joined: UnionFind[Id[Any]] = UnionFind()
    linked: set[Id[Any]] = set()
    links: set[Id[Any]] = set()
    for one in connections:
        a, b = spec_of.get(one.a.function), spec_of.get(one.b.function)
        if a is None or b is None or a.function == b.function:
            continue
        if not (a.roles.terminal and b.roles.terminal and a.strip_text):
            continue
        side = facing.get(one.a.port)
        if _strip(a) != _strip(b) or side is None or side != facing.get(one.b.port):
            continue
        joined.union(a.function, b.function)
        linked.update((a.function, b.function))
        links.add(one.handle)
    groups: dict[Id[Any], set[Id[Any]]] = {}
    for function in linked:
        groups.setdefault(joined.find(function), set()).add(function)
    sets = tuple(sorted((tuple(sorted(g)) for g in groups.values()), key=lambda g: g[0]))
    return TerminalChains(sets=sets, links=tuple(sorted(links)))


def _strip(spec: FunctionSpec) -> tuple[Any, ...]:
    """The terminal's strip tag, its own group, its unit and its location (one column's key)."""
    return spec.strip_text, group_of(spec), spec.unit, spec.location_path


def _facings(drawn: tuple[DrawnFunction, ...]) -> dict[Id[Any], str]:
    """Each drawn port's facing in its symbol."""
    found: dict[Id[Any], str] = {}
    for one in drawn:
        face = {g.name: g.facing.value for g in one.geometry.ports}
        found.update((p.port, face[p.symbol_port]) for p in one.ports if p.symbol_port in face)
    return found


def _marked(cell: Cell) -> bool:
    """A cell a bare row cell would change: a side element, a mirrored pole or a replica."""
    return cell.side or cell.mirror or cell.home is Home.ELSEWHERE


def join_terminal_rows(
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    chains: TerminalChains,
    *,
    tie_key: Mapping[Id[Any], tuple[str, ...]],
    fits: Callable[[Column], bool],
) -> tuple[Column, ...]:
    """`columns` with each chain's terminal-only columns made one column of one row."""
    spec_of = {spec.function: spec for spec in specs}
    result: list[Column] = list(columns)
    for chain in chains.sets:
        homes = [c for c in result if any(cell.function in chain for cell in c.cells)]
        held = [cell for c in homes for cell in c.cells]
        if any(cell.function not in chain or _marked(cell) for cell in held):
            continue
        if sorted(cell.function for cell in held) != sorted(chain):
            continue  # a member with no cell, or in two cells (a replica)
        order = sorted(chain, key=lambda f: (tie_key.get(f, ()), spec_of[f].key))
        head = spec_of[order[0]]
        cells = tuple(Cell(function=f, index=0, lane=lane) for lane, f in enumerate(order))
        built = build_column(
            ("chain", head.designation, *head.key), cells, [spec_of[f] for f in order]
        )
        if not fits(built):
            continue
        at = result.index(homes[0])  # no home stands before the first, so the place is unmoved
        result = [c for c in result if c not in homes]
        result.insert(at, built)
    return tuple(result)
