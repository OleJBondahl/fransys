"""A series that starts at a pin on the same page hangs from it as a wire (layout-0224).

A column whose first pin faces N, wired to an S pin of another column that stands below that
pin's own device, would turn back round it and become a reference pair. A lone conductor
between the two is drawn instead: `place` lowers the hanging column until its first pin stands
`HANG` below the source pin (the `JoinedRun` anchor and drop of `beside_runs`), so the wire
leaves downward and enters downward, with no turn. A hop the page room refuses stays a pair.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Facing
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun

from .joins import port_spots, turns_back
from .nets import side_functions, star_wires
from .turned import lone_pair

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.terminal_rows import TerminalChains
    from fransys_layout.stages.types import Connection, FunctionSpec
    from fransys_model.kernel import Id

    from .joins import Spot
    from .types import Joins, Page, Seating

HANG = 4 * WIRING_GRID  # the hanging pin stands this far below the pin it hangs from


def hung_joins(
    joins: Joins,
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    seating: Seating,
    chains: TerminalChains,
) -> Joins:
    """`joins` with each lone conductor that can hang as a wire: a run, a pair, a `hung` wire."""
    claimed = _claimed(joins, connections, specs, seating)
    runs: list[JoinedRun] = []
    hung: dict[tuple[Id[Any], Id[Any]], frozenset[int]] = {}
    for c, host, branch in _hangable(connections, seating, chains):
        keys = {c.a.port, c.b.port, host.column, branch.column}
        if keys & claimed:
            continue
        runs.append(_run(host, branch))
        claimed |= keys
        hung[c.a.port, c.b.port] = frozenset({host.page[0]})
    if not runs:
        return joins
    beside = replace(joins.beside, pairs={**joins.beside.pairs, **hung}, hung=frozenset(hung))
    return replace(joins, beside=beside, runs=(*joins.runs, *runs))


def _claimed(
    joins: Joins,
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    seating: Seating,
) -> set[Any]:
    """The ports of existing run ends and star wires, and the columns of existing runs."""
    claimed: set[Any] = set()
    for run in joins.runs:
        claimed |= {end.port for end in run.ends} | {end.column for end in run.ends}
    for c in star_wires(connections, specs, seating.columns):
        claimed |= {c.a.port, c.b.port}
    return claimed


def _hangable(
    connections: tuple[Connection, ...], seating: Seating, chains: TerminalChains
) -> list[tuple[Connection, Spot, Spot]]:
    """Each lone turn-back conductor that can hang, with its host (S pin) and branch (N pin)."""
    spots = port_spots(seating.columns, seating.plans, seating.drawn, seating.stacks)
    rooms = {page: stack.room for page, stack in seating.stacks.items()}
    side = side_functions(seating.columns)
    found = []
    for c in connections:
        pair = lone_pair(c, spots, side, chains)
        if pair is None:
            continue
        host, branch = sorted(pair, key=lambda spot: spot.facing is not Facing.S)
        if _hangs(host, branch, rooms):
            found.append((c, host, branch))
    return found


def _hangs(host: Spot, branch: Spot, rooms: Mapping[Page, int]) -> bool:
    """Whether `branch`, the first pin of its column, can be lowered below `host`'s pin."""
    if host.facing is not Facing.S or branch.facing is not Facing.N:
        return False
    if host.column == branch.column or branch.end.row != 0 or branch.shifted or host.shifted:
        return False
    if host.boxed or branch.boxed:
        return False  # a box pin takes a drop of its own (`beside_runs._drop`)
    if not (turns_back(branch, host) or turns_back(host, branch)):
        return False
    lowered = branch.end.height + host.end.offset + HANG - branch.end.offset
    return lowered <= rooms[branch.page]


def _run(host: Spot, branch: Spot) -> JoinedRun:
    """The run as `place` aligns it: the host's pin stays, the branch lowers below it."""
    ordered = sorted((host, branch), key=lambda spot: (spot.index, spot.end.port))
    ends = tuple(
        JoinedEnd(
            column=spot.column,
            port=spot.end.port,
            drop=HANG if spot is host else 0,
            anchor=spot is host,
        )
        for spot in ordered
    )
    return JoinedRun(drawing_set=host.page[0], page=host.page[1], ends=ends)
