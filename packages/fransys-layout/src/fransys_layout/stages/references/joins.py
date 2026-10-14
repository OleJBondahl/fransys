"""A horizontal join and "wired beside" are one rule, decided before `place`.

Two ends of a conductor of a star net are a wire, not two markers, where they are wired beside
each other in a drawing set: adjacent cells of one column (the first wire case, `columns`
alone), or lanes of one row (a terminal chain, `terminal_rows`), or ports of the net in
columns of one page at any distance, facing the same way, that leave their pins outward (the
turn test, `turns_back`) and that the
one offset function `join_y` puts on one y -- a run at the columns' ends (N at their first
rows, S at their last), which `place` aligns, or neighbours anywhere in their columns already
on one y with no column moved (ruling 2026-09-27); a lone pair of ends facing opposite ways that
do not turn back is one plain wire, with nothing to align (layout-0180).
A run it cannot align keeps its
references and gives `JOIN_UNALIGNED` (`WARNING`), and so does a wire from an end of a joined run
to a neighbour its turn test skipped, or a turned wire with an end under an
attached part. A power run whose straight wire is not free keeps its symbols and gives no
finding (layout-0190). A port's row, offset and facing are `place`'s
own (`place.page_stack`, amended 2026-09-27): no second rule for a port's y lives here.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Sequence

from fransys_layout.geometry import Facing
from fransys_layout.stages._chain_beside import beside_hosts
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun, JoinEnd, StackedPort, join_y
from fransys_model.kernel import Finding, Id, Severity, UnionFind

from .beside_runs import beside_pairs, beside_runs, joined_pairs
from .clear_runs import always_clear, run_clearance
from .nets import star_wires
from .types import Beside, Joins

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.stacking import PageStack
    from fransys_layout.stages.terminal_rows import TerminalChains
    from fransys_layout.stages.types import (
        Cell,
        Column,
        Connection,
        DrawnFunction,
        FunctionSpec,
        PagePlan,
    )
    from fransys_model.kernel import AuthoringKey

    from .clear_runs import Clear
    from .types import Page, Seating

JOIN_UNALIGNED = "JOIN_UNALIGNED"


@dataclass(frozen=True, slots=True)
class Spot:
    """Where one port stands on its page, as `place` stacks it: column, row, offset."""

    page: Page
    index: int
    column: AuthoringKey
    cell: int
    last: int
    facing: Facing
    end: JoinEnd
    body: tuple[int, int]
    shifted: bool = False  # An attached part stands above this port's function in its column
    crowded: bool = False  # Another pin of the cell ends at the same offset, facing the same way
    boxed: bool = False  # The pin stands on a generic box's edge, which a run never lies along


def joined_runs(
    connections: tuple[Connection, ...],
    functions: tuple[FunctionSpec, ...],
    seating: Seating,
    *,
    chains: TerminalChains,
    power: frozenset[Id[Any]] = frozenset(),
) -> Joins:
    """Every star-net conductor's ends wired beside, decided on `place`'s own stacking."""
    columns, drawn, stacks = seating.columns, seating.drawn, seating.stacks
    spots = port_spots(columns, seating.plans, drawn, stacks)
    rooms = {page: stack.room for page, stack in stacks.items()}
    clear = run_clearance(spots, drawn, power)
    wires = star_wires(connections, functions, columns)
    hosts = beside_hosts(columns)
    candidates = _same_page((*wires, *beside_pairs(connections, wires, spots, hosts)), spots)
    side, side_runs, refused = beside_runs(candidates, hosts, rooms)
    asked = {c.handle for c, x, y in candidates if _beside_wire(x, y, hosts)}
    rest = tuple(c for c in wires if c.handle not in asked)
    base = _wired_beside(rest, spots, rooms, chains, clear)
    return _with_beside(base, joined_pairs(side), side_runs, refused)


def port_spots(
    columns: tuple[Column, ...],
    plans: tuple[PagePlan, ...],
    drawn: tuple[DrawnFunction, ...],
    stacks: Mapping[Page, PageStack],
) -> dict[Id[Any], tuple[Spot, ...]]:
    """Every drawn port's `Spot`s: one per planned column a cell of its function stands in."""
    at = {
        planned.column: ((plan.drawing_set, plan.number), planned.index)
        for plan in plans
        for planned in plan.columns
    }
    drawn_of: dict[Id[Any], DrawnFunction] = {}
    for one in drawn:
        drawn_of.setdefault(one.function, one)  # the first drawn function of an id
    found: dict[Id[Any], list[Spot]] = defaultdict(list)
    for column in columns:
        if column.key not in at:
            continue
        page, index = at[column.key]
        where = (page, index, column.key)
        for cell in column.cells:
            for port, spot in _cell_spots(
                stacks[page], column, cell, drawn_of[cell.function], where
            ):
                found[port].append(spot)
    return {port: tuple(spots) for port, spots in found.items()}


def _cell_spots(
    stack: PageStack,
    column: Column,
    cell: Cell,
    one: DrawnFunction,
    where: tuple[Page, int, Any],
) -> list[tuple[Id[Any], Spot]]:
    """The `Spot` of each stacked port of one cell, with the port's id."""
    own = [
        (port, stacked)
        for port in one.ports
        if (stacked := stack.ports.get((column.key, port.port))) is not None
    ]
    if not own:
        return []
    body = (min(s.offset for _, s in own), max(s.offset for _, s in own))
    shifted = _under_attachment(column, cell)
    height, last = stack.heights[column.key], stack.last[column.key]
    return [
        (
            port.port,
            Spot(
                *where,
                cell.index,
                last,
                stacked.facing,
                JoinEnd(port=port.port, row=stacked.row, offset=stacked.offset, height=height),
                body,
                shifted,
                _crowded(own, port.port, stacked),
                one.geometry.generic_box,
            ),
        )
        for port, stacked in own
    ]


def _crowded(own: Sequence[tuple[Any, StackedPort]], port: Id[Any], one: StackedPort) -> bool:
    """Whether another pin of the cell ends at `one`'s offset facing the same way."""
    return any(
        (other.offset, other.facing) == (one.offset, one.facing) and found.port != port
        for found, other in own
    )


def _under_attachment(column: Column, cell: Cell) -> bool:
    """Whether a cell above `cell` in `column` is an attachment hosted by `cell`'s function."""
    return any(c.host == cell.function and c.index < cell.index for c in column.cells)


def _wired_beside(
    wires: tuple[Connection, ...],
    spots: Mapping[Id[Any], tuple[Spot, ...]],
    rooms: Mapping[Page, int],
    chains: TerminalChains,
    clear: Clear = always_clear,
) -> Joins:
    """The sets where each wire has its two ends wired beside each other, as `Joins.runs`."""
    beside: dict[tuple[Id[Any], Id[Any]], set[int]] = defaultdict(set)
    at_ends: list[tuple[Connection, Spot, Spot]] = []
    level: list[tuple[Connection, Spot, Spot]] = []
    turned: list[tuple[Connection, Spot, Spot]] = []
    for c, x, y, alone in _with_alone(_same_page(wires, spots)):
        if _plain_wire(x, y, alone=alone):
            beside[c.a.port, c.b.port].add(x.page[0])
        elif _chain_link(c, x, y, chains):
            level.append((c, x, y))
        elif _neighbours(x, y):
            (at_ends if _at_ends(x, y) else level).append((c, x, y))
        elif _turned_away(x, y):
            turned.append((c, x, y))
    runs, findings = [], []
    for found, case in ((at_ends, True), (level, False)):
        for page, run, members, finding in _decided(found, rooms, clear, at_ends=case):
            if finding is None:
                _add(beside, members)
                runs.append(_joined(page, run))
            else:
                findings.append(finding)
    findings += turned_findings(turned, runs)
    sets = {port: frozenset(spot.page[0] for spot in found) for port, found in spots.items()}
    pairs = {pair: frozenset(found) for pair, found in beside.items()}
    return Joins(Beside(pairs=pairs, sets=sets), tuple(runs), tuple(findings))


def _decided(
    candidates: Sequence[tuple[Connection, Spot, Spot]],
    rooms: Mapping[Page, int],
    clear: Clear,
    *,
    at_ends: bool,
) -> list[tuple[Page, tuple[Spot, ...], list[tuple[Connection, int]], Finding | None]]:
    """Each run with its wires, and `JOIN_UNALIGNED` if `join_y` refuses it; `clear` drops it."""
    out = []
    for page, run, members in _runs(candidates):
        ends = tuple(spot.end for spot in run)
        y = join_y(ends, rooms[page])
        aligned = y is not None if at_ends else {end.offset for end in ends} == {y}
        if (not aligned and not at_ends) or (aligned and not clear(page, run, at_ends=at_ends)):
            continue  # a blocked power wire is no join: its ends take their symbols, nothing to fix
        out.append((page, run, members, None if aligned else _unaligned(ends)))
    return out


def _same_page(
    wires: tuple[Connection, ...], spots: Mapping[Id[Any], tuple[Spot, ...]]
) -> list[tuple[Connection, Spot, Spot]]:
    """Each wire with every pair of its two ends' `Spot`s on one page."""
    return [
        (c, x, y)
        for c in wires
        for x in spots.get(c.a.port, ())
        for y in spots.get(c.b.port, ())
        if x.page == y.page
    ]


def _runs(
    candidates: Sequence[tuple[Connection, Spot, Spot]],
) -> list[tuple[Page, tuple[Spot, ...], list[tuple[Connection, int]]]]:
    """The join candidates joined through shared ends on one page: each run's page, ends, wires."""
    joined: UnionFind[tuple[Id[Any], Page]] = UnionFind()
    for _, x, y in candidates:
        joined.union((x.end.port, x.page), (y.end.port, y.page))
    ends: dict[tuple[Id[Any], Page], set[Spot]] = defaultdict(set)
    members: dict[tuple[Id[Any], Page], list[tuple[Connection, int]]] = defaultdict(list)
    for c, x, y in candidates:
        key = joined.find((x.end.port, x.page))
        ends[key].update((x, y))
        members[key].append((c, x.page[0]))
    runs = [(key[1], tuple(sorted(ends[key], key=lambda s: s.end.port)), key) for key in ends]
    runs.sort(key=lambda run: (run[0], run[1][0].end.port))
    return [(page, run, members[key]) for page, run, key in runs]


def _joined(page: Page, run: tuple[Spot, ...]) -> JoinedRun:
    """The run as `place` aligns it: its ends, each port with its column, in column order."""
    ordered = sorted(run, key=lambda spot: (spot.index, spot.end.port))
    ends = tuple(JoinedEnd(column=spot.column, port=spot.end.port) for spot in ordered)
    return JoinedRun(drawing_set=page[0], page=page[1], ends=ends)


def _add(
    beside: Mapping[tuple[Id[Any], Id[Any]], set[int]], members: Sequence[tuple[Connection, int]]
) -> None:
    """Each of a joined run's wires beside in its drawing set."""
    for c, drawing_set in members:
        beside[c.a.port, c.b.port].add(drawing_set)


def _neighbours(x: Spot, y: Spot) -> bool:
    """Two ends in different columns of one page, facing one way, each leaving its pin outward."""
    if x.column == y.column or x.facing is not y.facing:
        return False
    return not (turns_back(x, y) or turns_back(y, x))


def _turned_away(x: Spot, y: Spot) -> bool:
    """Two ends of different columns, facing one way, where one turns back past its device."""
    return x.column != y.column and x.facing is y.facing and (turns_back(x, y) or turns_back(y, x))


def _with_alone(
    pairs: Sequence[tuple[Connection, Spot, Spot]],
) -> list[tuple[Connection, Spot, Spot, bool]]:
    """Each pair with whether neither end has another wire to a port of its page (a lone pair)."""
    seen = Counter(key for _, x, y in pairs for key in ((x.page, x.end.port), (y.page, y.end.port)))
    return [
        (c, x, y, seen[x.page, x.end.port] == 1 and seen[y.page, y.end.port] == 1)
        for c, x, y in pairs
    ]


def _plain_wire(x: Spot, y: Spot, *, alone: bool) -> bool:
    """Ends needing no alignment: column neighbours, or a lone pair facing apart (no turn back)."""
    if x.column == y.column:
        return abs(x.cell - y.cell) == 1
    return alone and x.facing is not y.facing and not (turns_back(x, y) or turns_back(y, x))


def turned_findings(
    turned: Sequence[tuple[Connection, Spot, Spot]], runs: Sequence[JoinedRun]
) -> list[Finding]:
    """`JOIN_UNALIGNED` for a turned wire with an end joined or under an attachment."""
    joined = {(run.drawing_set, run.page, end.port) for run in runs for end in run.ends}
    return [
        _unaligned((x.end, y.end))
        for _, x, y in turned
        if x.shifted or y.shifted or {(*x.page, x.end.port), (*y.page, y.end.port)} & joined
    ]


def turns_back(own: Spot, other: Spot) -> bool:
    """Whether a wire from `own`'s pin to `other`'s comes back past `own`'s device."""
    if own.facing is Facing.N:
        return other.end.offset > own.body[1]
    if own.facing is Facing.S:
        return other.end.offset < own.body[0]
    return False


def _chain_link(c: Connection, x: Spot, y: Spot, chains: TerminalChains) -> bool:
    """A link of a terminal chain: two lanes of one row, facing one way (ADDENDUM 19 fix 3)."""
    return (
        x.column == y.column
        and x.cell == y.cell
        and x.facing is y.facing
        and c.handle in chains.links
    )


def _at_ends(x: Spot, y: Spot) -> bool:
    """Two ends at the same end of their columns, N in the first rows or S in the last."""
    if x.facing is Facing.N:
        return x.end.row == 0 and y.end.row == 0
    if x.facing is Facing.S:
        return x.end.row == x.last and y.end.row == y.last
    return False


def _unaligned(run: tuple[JoinEnd, ...]) -> Finding:
    """One run `place` cannot align, drawn as references instead."""
    return Finding(
        code=JOIN_UNALIGNED,
        severity=Severity.INFO,
        subjects=tuple(end.port for end in run),
        message="a horizontal join's row could not be aligned; drawn as references instead",
    )


def _beside_wire(x: Spot, y: Spot, hosts: Mapping[AuthoringKey, AuthoringKey]) -> bool:
    """Whether a wire joins a beside column to its host's: `beside_runs` decides it alone."""
    return hosts.get(x.column) == y.column or hosts.get(y.column) == x.column


def _with_beside(
    base: Joins,
    aside: Mapping[tuple[Id[Any], Id[Any]], set[int]],
    runs: Sequence[JoinedRun],
    refused: Sequence[tuple[JoinEnd, JoinEnd]],
) -> Joins:
    """`base` with the wires of beside columns: their pairs, their runs first, their refusals."""
    pairs = {**base.beside.pairs, **{pair: frozenset(sets) for pair, sets in aside.items()}}
    beside = Beside(pairs=pairs, sets=base.beside.sets, aside=frozenset(aside))
    findings = (*base.findings, *(_unaligned(pair) for pair in refused))
    return Joins(beside, (*runs, *base.runs), findings)
