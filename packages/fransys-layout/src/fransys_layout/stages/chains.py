"""Stage 2, chain discovery: current paths from connectivity alone (deep-dive prototype, R4).

Every function no authored chain claims takes part.

1. Series poles. A pole is a `PolePair` of a function, or a function's two ports when it has
   none but its symbol has a through path (a coil, a diode). `in` is the pole's N-facing
   symbol port, `out` its S-facing one. A terminal pole has no direction. A mated pin pair
   (equal-named ports of two mated functions) is a direction-free pole too.
2. Nets: conductors (`Connection`) and declared nets (`NetGroup`), never internal links.
3. Side elements (D1, layout-0060). A pole whose two ends sit on the same two nets as another
   pole is that pole's side element, of one function or of two: a suppressor beside a coil,
   K2's pole 1 strapped to K1's. The carrier is the child item's coil, else the pole whose
   item designation sorts first, then its port; a side pole of the carrier's own function is
   drawn in that function's cell. A one-port terminal (a printed pass-through) is a side
   element of a pole on its net, a non-terminal pole first. Side ports do not count toward a
   net's size. A function is a carrier or a side element, never both, and the side element of
   one carrier function only; one the picks make both, or a side element of two carriers, is a
   side element nowhere (`_side_nowhere`): it keeps its own cell, its conductors and nets stay. A
   side element stands beside its carrier's cell in the row where that cell is drawn, also
   when the pole it straps lies in a later column of the carrier. A carrier pole that only its
   own side poles share nets with is unwired; when it is a one-pole chain of a non-terminal
   whose function stands in a longer chain or is a side element, it is dropped with them
   (`_drop_unwired_poles`).
4. Chains: a net of exactly two pole ports links them; any other net ends the chain. A chain
   runs top to bottom in the direction most of its non-terminal poles give. S13 (layout-0090):
   a changeover whose two throws each end at a terminal with no other wire links neither
   terminal: its chain stops at the pole, both terminals hang under it (`_attach`), the throw
   on its through path in the second row, and the chain bundles as if that terminal stood in it.
5. Bundles: chains with one sequence of `(item, kind)` (every terminal alike), passing an
   `(item, kind)` with more than one pole. A bundle is one column; its rows are the chain
   positions, and a row holds the distinct functions at that position in pole order, side
   elements after them.

A function in several columns (a connector whose pins sit in different chains) stays in the
first column by key only.
"""

import dataclasses
from collections import defaultdict
from typing import TYPE_CHECKING
lazy from collections.abc import Set as AbstractSet

from fransys_layout.conventions import FACTS

from ._chain_cells import build_cells
from ._chain_poles import build_poles
from ._chain_reach import start_reach, vote_columns
from ._chain_sides import build_nets, find_sides
from ._chain_walk import bundle_chains, drop_unwired_poles, find_links, walk_chains
from .attach import _entry
from .columns import build_column
from .slices import by_key
from .terminal_facts import TerminalRead
from .types import Cell, PortRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import (
        Column,
        Connection,
        DrawnFunction,
        FunctionSpec,
        Handle,
        MatedFunctions,
        NetGroup,
    )

# A terminal attached to a host's port (`_attach`): its row on that side of the host (0 the
# nearest, 1 the second, S13), the port's x, the terminal's function key and handle, the host's
# symbol port, and whether the terminal is drawn flipped.
type _Attachment = tuple[int, int, AuthoringKey, Handle, str, bool]


@dataclasses.dataclass(frozen=True, slots=True)
class ChainRecords:
    """Chain discovery reads connectivity alone: these records and nothing else (stage 2, R4)."""

    functions: tuple[FunctionSpec, ...]
    drawn: tuple[DrawnFunction, ...]
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    mates: tuple[MatedFunctions, ...]
    # units U1, I2a: a pin mated across a unit boundary, `a` in the parent's set, `b` the child
    # unit's boundary pin. The pair is a mate pole whose `b` end is a stand-in port on no net, so
    # the chain stops at the unit edge; `b` is drawn face to face under `a` as a replica cell,
    # its black box, while its home stays in the child's chain.
    edge_mates: tuple[MatedFunctions, ...] = ()
    # V1: the item-box ports whose side V1 fixes; the part they reach stands on that side
    fixed: frozenset[Handle] = frozenset()


@dataclasses.dataclass(frozen=True, slots=True)
class _AttachReads:
    """What `_attach` reads of a terminal's wire; `second` holds ports attached in row two (S13)."""

    specs: Mapping[Handle, FunctionSpec]
    drawn_of: Mapping[Handle, DrawnFunction]
    members: Mapping[Handle, Sequence[Handle]]
    net_of: Mapping[Handle, Handle]
    port_function: Mapping[Handle, Handle]
    connections: tuple[Connection, ...]
    second: AbstractSet[Handle]


def discover_chains(
    records: ChainRecords,
    *,
    rank_of: Mapping[Handle, int] | None = None,
    tie_key: Mapping[Handle, tuple[str, ...]] | None = None,
) -> tuple[Column, ...]:
    """Find the chains and bundles, one column each; `tie_key` breaks end ties (D1, model-0052)."""
    functions, connections = records.functions, records.connections
    rank_of, tie_key = rank_of or {}, tie_key or {}
    specs = {spec.function: spec for spec in functions}
    drawn_of = {d.function: d for d in records.drawn if d.function in specs}
    state = build_poles(functions, drawn_of, connections, records.mates, records.edge_mates)
    nets = build_nets(state, connections, records.net_groups)
    found = find_sides(state, nets, specs, tie_key, drawn_of)
    links = find_links(state, nets, specs, connections)
    walks = walk_chains(state, links, specs, rank_of, tie_key)
    drop_unwired_poles(walks, state, nets, found)
    bundle_chains(walks, state, links, specs)
    reach = start_reach(state, nets, specs, drawn_of, found.side_info)
    reach.fixed = records.fixed
    vote_columns(reach, walks, connections)
    built = build_cells(state, walks, found, reach, specs)
    reads = _AttachReads(
        specs, drawn_of, nets.members, nets.net_of, state.port_function, connections, links.detached
    )
    built = _attach(built, reads)
    return _finish_columns(built, specs)


def _finish_columns(
    built: Sequence[list[Cell]], specs: Mapping[Handle, FunctionSpec]
) -> tuple[Column, ...]:
    """One `Column` per list of cells, sorted by key and then by the cells' functions."""
    columns = []
    for cells in built:
        # keyed by its first placed non-attachment function: unique, a function is placed
        # once; R5 rule 4: within a group, columns run by the top function's designation
        top = specs[next(c for c in cells if c.host is None and not c.replica).function]
        first_key = ("chain", top.designation, *top.key)
        # C11: a column's group and location are its own cells', not its attachments' (nor
        # an edge pin's, a replica whose home is in its own unit)
        own_specs = [specs[c.function] for c in cells if c.host is None and not c.replica]
        columns.append(build_column(first_key, tuple(cells), own_specs))
    columns.sort(key=lambda column: (column.key, tuple(cell.function for cell in column.cells)))
    return tuple(columns)


def _leaves_its_set(terminal: FunctionSpec, host: FunctionSpec) -> bool:
    """Layout-0076: the terminal would stand in a top-level drawing set not its own (0081)."""
    (unit, location), (host_unit, host_location) = terminal.drawing_set_key, host.drawing_set_key
    return unit is None and host_unit is None and location != host_location


def _attach(built: Sequence[list[Cell]], reads: _AttachReads) -> list[list[Cell]]:
    """R7.1: a one-terminal column wired to one N or S port becomes a cell of its host (S13)."""
    specs, drawn_of, members = reads.specs, reads.drawn_of, reads.members
    net_of, second = reads.net_of, reads.second
    connections, port_function = reads.connections, reads.port_function
    home = {cell.function for cells in built for cell in cells}
    found: dict[tuple[Handle, str], list[_Attachment]] = defaultdict(list)
    drop: set[int] = set()
    for position, cells in enumerate(built):
        if len(cells) != 1 or not specs[cells[0].function].roles.terminal:
            continue
        terminal = cells[0].function
        own = [p.port for p in specs[terminal].ports]
        # C10: a terminal's own conductors decide, else (net group only) its net
        direct = [
            (c.b.port if c.a.port == q else c.a.port)
            for q in own
            for c in connections
            if q in (c.a.port, c.b.port)
        ]
        others = direct or [p for q in own for p in members[net_of[q]] if p not in own]
        if not FACTS["terminal_point"].func(
            TerminalRead(specs[terminal].roles.terminal, len(own), len(others))
        ):
            continue
        target = others[0]
        host = port_function.get(target)  # None: an authored chain holds the other end
        drawn_host = drawn_of.get(host)
        if host is None or drawn_host is None or host == terminal:
            continue
        if _leaves_its_set(specs[terminal], specs[host]):
            continue
        wired = next(q for q in own if target in members[net_of[q]])
        entry = _entry(
            drawn_of[terminal],
            PortRef(function=terminal, port=wired),
            drawn_host,
            PortRef(function=host, port=target),
        )
        if entry is None:
            continue
        _, facing, x, _, symbol, flip = entry
        row = int(target in second)
        found[host, facing].append((row, x, specs[terminal].key, terminal, symbol, flip))
        drop.add(position)
    columns = [list(cells) for position, cells in enumerate(built) if position not in drop]
    for host, _ in sorted(found, key=lambda k: specs[k[0]].key):
        if host not in home and host in specs:
            columns.append([Cell(function=host, index=0)])
            home.add(host)
    return [_stack_attachments(cells, found) for cells in columns]


def _attached_rows(
    row: Sequence[Cell], found: Mapping[tuple[Handle, str], list[_Attachment]], facing: str
) -> list[list[Cell]]:
    """R7.1: the attachment rows on the `facing` side of `row`, nearest first (S13)."""
    entries = [(c.function, a) for c in row for a in sorted(found.get((c.function, facing), ()))]
    return [
        [
            Cell(function=t, index=0, lane=k, flip=f, host=h, port=s)
            for k, (h, (_, _, _, t, s, f)) in enumerate(e for e in entries if e[1][0] == tier)
        ]
        for tier in sorted({a[0] for _, a in entries})
    ]


def _stack_attachments(
    cells: Sequence[Cell], found: Mapping[tuple[Handle, str], list[_Attachment]]
) -> list[Cell]:
    """R7.1: one column's `cells` with its attachment rows above and below each row with any."""
    rows = by_key(cells, lambda cell: cell.index)
    out: list[Sequence[Cell]] = []
    for index in sorted(rows):
        row = rows[index]
        out.extend(reversed(_attached_rows(row, found, "n")))
        out.append(row)
        out.extend(_attached_rows(row, found, "s"))
    return [dataclasses.replace(cell, index=i) for i, row in enumerate(out) for cell in row]
