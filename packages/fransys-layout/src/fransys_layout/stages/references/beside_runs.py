"""The wires of a chain stood beside its host (layout-0174): each one a horizontal join.

A beside column's end ports join the host column's ports by short horizontals, whatever way
either faces. Unlike `joins`' own runs, the two ends stand in different rows, so `place` lowers
the shallower row of each wire in turn, top to bottom (`place._align_joins` does the same sums).
A wire the room or the order of rows refuses stays references, with `JOIN_UNALIGNED`.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Facing
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun

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
        # The host stays where it stands: the branch lowers to its pin, or, standing deeper
        # already, joins by an L (layout-0174)
        y = host.end.offset + _drop(host)
        level = branch.end.offset + shift[branch.page, branch.column] + _drop(branch) <= y
        if level and not _fits(branch, y, rooms, last):
            refused.append((branch.end, host.end))
            continue
        if level:
            shift[branch.page, branch.column] = y - branch.end.offset - _drop(branch)
            last[branch.page, branch.column] = branch.end.row
        joined.append((c, branch, host))
        runs.append(_run(branch, host))
    return joined, runs, refused


def beside_pairs(
    connections: Sequence[Connection],
    star: Sequence[Connection],
    spots: Mapping[Id[Any], Sequence[Spot]],
    hosts: Mapping[AuthoringKey, AuthoringKey],
) -> tuple[Connection, ...]:
    """The conductors outside a star net that join a beside column to its host's (CBF1).

    A two-port host net is no star, yet its beside conductor is a short horizontal like any other.
    """
    if not hosts:
        return ()
    taken = {c.handle for c in star}
    return tuple(
        c
        for c in connections
        if c.handle not in taken
        and any(
            _is_beside((c, x, y), hosts)
            for x in spots.get(c.a.port, ())
            for y in spots.get(c.b.port, ())
            if x.page == y.page
        )
    )


def _fits(
    branch: Spot, y: int, rooms: Mapping[Page, int], last: Mapping[tuple[Page, AuthoringKey], int]
) -> bool:
    """Whether the branch, lowered to `y`, stays in its page's room and its rows' order."""
    lowered = branch.end.height + y - branch.end.offset - _drop(branch)
    return (
        lowered <= rooms[branch.page]
        and last.get((branch.page, branch.column), -1) < branch.end.row
    )


def _is_beside(wire: _Wire, hosts: Mapping[AuthoringKey, AuthoringKey]) -> bool:
    """Whether one end stands in a beside column and the other in that column's host's."""
    _, x, y = wire
    return hosts.get(x.column) == y.column or hosts.get(y.column) == x.column


def _branch_first(wire: _Wire, hosts: Mapping[AuthoringKey, AuthoringKey]) -> _Wire:
    """The wire with its beside column's end first."""
    c, x, y = wire
    return wire if hosts.get(x.column) == y.column else (c, y, x)


def _drop(spot: Spot) -> int:
    """How far the run's y stands past a crowded or box pin, leaving the pin's way (layout-0174).

    A level join would run through the cell's other pin ends, or along a box's edge (JOIN-VERTICAL),
    so it leaves the pin by one grid.
    """
    if not (spot.crowded or spot.boxed):
        return 0
    return {Facing.S: WIRING_GRID, Facing.N: -WIRING_GRID}.get(spot.facing, 0)


def _run(branch: Spot, host: Spot) -> JoinedRun:
    """The run as `place` aligns it: both ends, each port with its column, in column order."""
    ordered = sorted((branch, host), key=lambda spot: (spot.index, spot.end.port))
    ends = tuple(
        JoinedEnd(column=spot.column, port=spot.end.port, drop=_drop(spot), anchor=spot is host)
        for spot in ordered
    )
    return JoinedRun(drawing_set=branch.page[0], page=branch.page[1], ends=ends, aside=True)


def joined_pairs(joined: Sequence[_Wire]) -> dict[tuple[Id[Any], Id[Any]], set[int]]:
    """Each joined wire's two ports with the drawing set it is beside in."""
    return {(c.a.port, c.b.port): {x.page[0]} for c, x, _ in joined}
