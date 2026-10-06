"""The member check: every placed member of a net has a route or a marker in its set (layout-0071).

A net is the ports its conductors join plus the ports of each net group. For a net of two or
more ports, each member port placed in drawing set `s` needs a cover on any page of `s`: a route
ending at it or a marker naming it. The cover is judged per drawing set, the granularity the star
rule has (layout-0070: one branch per port per set, on its first page there; layout-0030: a
conductor is drawn once). A route or marker in another drawing set covers nothing, nor does a
route or marker of another port, so the two sides of a terminal are judged apart.
`check_coherence` compares the members that share a page, so a member that is the only one of
its net in its set passes it; this check does not excuse it. Decisions are not read: a cut
decision is no drawing.

Pump station: `-X3:PE:1` is beside the hub in set 1, where the wire is drawn; in set 3 its outer
port carries the cable's stub marker, but its inner port needs its own star branch. The route in
set 1 and the marker on the outer port cover neither.

The connectivity may come from before the star nets were taken out, when one port can sit in a
conductor and in a net group of another physical net; nothing here validates it, so where a port
is placed is read from `layout.placed` and `drawn` directly, not from `_ports.locate`.
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.stages.lookups import nets_from_pairs
from fransys_model.kernel import Finding, Severity

from .codes import CONNECTION_NOT_DRAWN

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages import Connection, DrawnFunction, Handle, Layout, NetGroup


_NET_MIN = 2  # a net is two or more ports


def check_members(
    layout: Layout,
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    drawn: tuple[DrawnFunction, ...],
    exempt: frozenset[tuple[Handle, int]] = frozenset(),  # `(port, drawing set)`
) -> tuple[Finding, ...]:
    """`CONNECTION_NOT_DRAWN` for each `(port, drawing set)` of a net member with no cover."""
    root_of, size = _nets(connections, net_groups)
    covered = {(end, route.drawing_set) for route in layout.routes for end in (route.a, route.b)}
    covered.update((one.port, one.drawing_set) for one in layout.markers)
    sets: dict[Handle, set[int]] = defaultdict(set)
    for one in layout.placed:
        sets[one.function].add(one.drawing_set)
    bare = set()
    for function in drawn:
        for drawing_set in sets.get(function.function, ()):
            bare.update(
                (one.port, drawing_set)
                for one in function.ports
                if one.port in root_of
                and size[root_of[one.port]] >= _NET_MIN
                and (one.port, drawing_set) not in covered
                and (one.port, drawing_set) not in exempt
            )
    at_port: dict[Handle, list[Connection]] = defaultdict(list)
    for one in connections:
        at_port[one.a.port].append(one)
        at_port[one.b.port].append(one)
    return tuple(
        _finding(port, drawing_set, at_port.get(port, ())) for port, drawing_set in sorted(bare)
    )


def _finding(port: Handle, drawing_set: int, conductors: Sequence[Connection]) -> Finding:
    """The finding for `port` in `drawing_set`, naming the conductors that end at it."""
    what = "the conductor at this port" if conductors else "a connection"
    return Finding(
        code=CONNECTION_NOT_DRAWN,
        severity=Severity.ERROR,
        subjects=(port, *(one.handle for one in conductors)),
        message=f"{what} is neither drawn nor cut in drawing set {drawing_set}",
    )


def check_nowhere(
    layout: Layout,
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    drawn: tuple[DrawnFunction, ...],
    reported: tuple[Finding, ...] = (),
) -> tuple[Finding, ...]:
    """`CONNECTION_NOT_DRAWN` for each net drawn nowhere, the guard under the exemptions."""
    root_of, size = _nets(connections, net_groups)
    covered = {end for route in layout.routes for end in (route.a, route.b)}
    covered.update(one.port for one in layout.markers)
    drawn_roots = {root_of[port] for port in covered if port in root_of}
    drawn_roots.update(
        root_of[port] for one in reported for port in one.subjects if port in root_of
    )
    placed = {one.function for one in layout.placed}
    members: dict[Handle, set[Handle]] = defaultdict(set)
    for function in drawn:
        if function.function in placed:
            for one in function.ports:
                if one.port in root_of and size[root_of[one.port]] >= _NET_MIN:
                    members[root_of[one.port]].add(one.port)
    return tuple(
        sorted(
            (
                Finding(
                    code=CONNECTION_NOT_DRAWN,
                    severity=Severity.ERROR,
                    subjects=tuple(sorted(ports)),
                    message="a net is drawn nowhere: no route, marker, stub or echo in any set",
                )
                for root, ports in members.items()
                if root not in drawn_roots
            ),
            key=lambda one: one.subjects,
        )
    )


def _nets(
    connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...]
) -> tuple[dict[Handle, Handle], dict[Handle, int]]:
    """The root of each port the conductors and net groups join, and the size of each net."""
    ends = [(one.a.port, one.b.port) for one in connections]
    for group in net_groups:
        ports = [ref.port for ref in group.ports]
        ends.extend(pairwise(ports))
    groups = nets_from_pairs(ends).groups()
    return (
        {port: root for root, ports in groups.items() for port in ports},
        {root: len(ports) for root, ports in groups.items()},
    )
