"""The wires of a chain stood beside its host (layout-0174): each one a horizontal join.

A beside column's end ports join the host column's ports by short horizontals, whatever way
either faces. Unlike `joins`' own runs, the two ends stand in different rows, so `place` lowers
the shallower row of each wire in turn, top to bottom (`place._align_joins` does the same sums).
A wire the room or the order of rows refuses stays references, with `JOIN_UNALIGNED`.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Facing
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun, join_offset

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.stacking import JoinEnd
    from fransys_layout.stages.types import Connection
    from fransys_model.kernel import AuthoringKey, Id

    from .joins import Spot
    from .types import Page

type _Wire = tuple[Connection, Spot, Spot]


def beside_runs(
    wires: Sequence[_Wire],
    hosts: Mapping[AuthoringKey, AuthoringKey],
    rooms: Mapping[Page, int],
) -> tuple[list[_Wire], list[JoinedRun], list[tuple[JoinEnd, JoinEnd]]]:
    """The wires of beside columns with their runs, and the end pairs of those refused.

    `wires` are each wire with a `Spot` per end on one page.
    """
    found = sorted(
        (_branch_first(wire, hosts) for wire in wires if _is_beside(wire, hosts)),
        key=lambda wire: (wire[1].page, wire[2].end.offset, wire[1].end.offset),
    )
    shift: dict[tuple[Page, AuthoringKey], int] = defaultdict(int)
    last: dict[tuple[Page, AuthoringKey], int] = {}
    joined: list[_Wire] = []
    runs: list[JoinedRun] = []
    refused: list[tuple[JoinEnd, JoinEnd]] = []
    for c, branch, host in ((w[0], w[1], w[2]) for w in found):
        ends = [(branch, shift[branch.page, branch.column]), (host, shift[host.page, host.column])]
        y = join_offset(spot.end.offset + moved + _drop(spot) for spot, moved in ends)
        deep = any(
            spot.end.height + moved + y - spot.end.offset - moved - _drop(spot) > rooms[spot.page]
            for spot, moved in ends
        )
        in_order = all(last.get((s.page, s.column), -1) < s.end.row for s, _ in ends)
        if deep or not in_order:
            refused.append((branch.end, host.end))
            continue
        for spot, _ in ends:
            shift[spot.page, spot.column] = y - spot.end.offset - _drop(spot)
            last[spot.page, spot.column] = spot.end.row
        joined.append((c, branch, host))
        runs.append(_run(branch, host))
    return joined, runs, refused


def _is_beside(wire: _Wire, hosts: Mapping[AuthoringKey, AuthoringKey]) -> bool:
    """Whether one end stands in a beside column and the other in that column's host's."""
    _, x, y = wire
    return hosts.get(x.column) == y.column or hosts.get(y.column) == x.column


def _branch_first(wire: _Wire, hosts: Mapping[AuthoringKey, AuthoringKey]) -> _Wire:
    """The wire with its beside column's end first."""
    c, x, y = wire
    return wire if hosts.get(x.column) == y.column else (c, y, x)


def _drop(spot: Spot) -> int:
    """How far the run's y stands past a pin of a crowded cell, leaving the pin's way (layout-0174).

    A level join would run through the cell's other pin ends, so it leaves the pin by one grid.
    """
    if not spot.crowded:
        return 0
    return {Facing.S: WIRING_GRID, Facing.N: -WIRING_GRID}.get(spot.facing, 0)


def _run(branch: Spot, host: Spot) -> JoinedRun:
    """The run as `place` aligns it: both ends, each port with its column, in column order."""
    ordered = sorted((branch, host), key=lambda spot: (spot.index, spot.end.port))
    ends = tuple(
        JoinedEnd(column=spot.column, port=spot.end.port, drop=_drop(spot)) for spot in ordered
    )
    return JoinedRun(drawing_set=branch.page[0], page=branch.page[1], ends=ends, aside=True)


def joined_pairs(joined: Sequence[_Wire]) -> dict[tuple[Id[Any], Id[Any]], set[int]]:
    """Each joined wire's two ports with the drawing set it is beside in."""
    return {(c.a.port, c.b.port): {x.page[0]} for c, x, _ in joined}
