"""Stage 9, connectivity coherence: the drawing says what the model says.

Refs: foundations.md 2.4, lint.md 6.8.

Separate from geometric lint on purpose: a good-looking page can be wrong. Everything is
identified by handle and compared by position; nothing is looked up by designation, tag or label.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from itertools import combinations, pairwise
from operator import itemgetter
from typing import TYPE_CHECKING

from fransys_layout.geometry import LayoutError
from fransys_layout.stages import LinkCase
from fransys_layout.stages.grid_path import axes_of, clean_crossing
from fransys_layout.stages.slices import by_key, page_of
from fransys_model.kernel import Finding, Severity

from ._cuts import conductor_cut, group_cuts, unpaired
from ._group_joins import cut_gaps, page_joins
from ._group_joins import identity as _identity
from ._ports import locate
from .codes import (
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    MARKER_UNPAIRED,
    ROUTE_SHORTS_NETS,
    ROUTE_WRONG_PORT,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.geometry import Point
    from fransys_layout.stages import (
        Connection,
        DrawnFunction,
        Handle,
        Layout,
        NetGroup,
        Route,
    )
    from fransys_layout.stages.grid_path import Cell

    from ._cuts import Cut
    from ._ports import Page, Ports

_MIN_POINTS = 2  # a route is at least its two ends, even `[p, p]`

# `(connection, a, b)`: a conductor, a net-group edge or a cut.
type Identity = tuple[Handle, Handle, Handle]


@dataclass(frozen=True, slots=True)
class _World:
    """What every check reads: the layout, the connectivity and where the named ports are."""

    layout: Layout
    conductors: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    ports: Ports
    claims: tuple[tuple[Route, Handle | None], ...]
    edges: dict[Handle, dict[Page, list[Route]]]
    decisions: Counter[Identity]
    function_units: Mapping[Handle, Handle | None]
    set_units: Mapping[int, Handle | None]


def check_coherence(
    layout: Layout,
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    drawn: tuple[DrawnFunction, ...],
    *,
    function_units: Mapping[Handle, Handle | None],
) -> tuple[Finding, ...]:
    """Compare drawn routes and markers with the connections they claim (design/lint.md 6.8)."""
    ports = locate(connections, net_groups, layout.placed, drawn)
    if any(len(route.points) < _MIN_POINTS for route in layout.routes):
        msg = "a route has fewer than two points"
        raise LayoutError(msg)
    conductors = {one.handle: one for one in connections}
    groups = _by_net(net_groups)
    claims = tuple((route, _claimed_net(route, conductors, groups)) for route in layout.routes)
    edges: dict[Handle, dict[Page, list[Route]]] = defaultdict(lambda: defaultdict(list))
    for route, net in claims:
        if net is not None and route.connection in groups:
            edges[route.connection][route.drawing_set, route.page].append(route)
    world = _World(
        layout=layout,
        conductors=connections,
        net_groups=net_groups,
        ports=ports,
        claims=claims,
        edges=edges,
        decisions=Counter((one.connection, one.a, one.b) for one in layout.decisions),
        function_units=function_units,
        set_units={page.drawing_set: page.unit for page in layout.pages},
    )
    findings = [
        *_routes(world),
        *_touches(world),
        *_conductors(world),
        *_groups(world),
        *_markers(world),
    ]
    return tuple(sorted(findings, key=lambda one: (one.code, one.subjects)))


def _by_net(net_groups: tuple[NetGroup, ...]) -> dict[Handle, NetGroup]:
    """Each net's group: the location parts of one net (D4, S15) as one group of all their ports."""
    found: dict[Handle, NetGroup] = {}
    for one in net_groups:
        known = found.get(one.net)
        found[one.net] = one if known is None else replace(known, ports=(*known.ports, *one.ports))
    return found


def _claimed_net(
    route: Route, conductors: Mapping[Handle, Connection], groups: Mapping[Handle, NetGroup]
) -> Handle | None:
    """The physical net of what `route` validly claims, or `None` for a claim that is not valid."""
    conductor = conductors.get(route.connection)
    if conductor is not None:
        claimed = (route.a, route.b) == (conductor.a.port, conductor.b.port)
        return conductor.physical_net if claimed else None
    group = groups.get(route.connection)
    if group is not None:
        named = {ref.port for ref in group.ports}
        if route.a < route.b and route.a in named and route.b in named:
            return group.physical_net
    return None


def _error(code: str, subjects: tuple[Handle, ...], message: str) -> Finding:
    return Finding(code=code, severity=Severity.ERROR, subjects=subjects, message=message)


def _lands(world: _World, port: Handle, page: Page, point: Point) -> bool:
    """A route end is at its port, or at the other node port its end lands on (R7 B5)."""
    return world.ports.at.get((port, page)) == point or point in world.ports.also.get(
        (port, page), frozenset()
    )


def _routes(world: _World) -> list[Finding]:
    """`ROUTE_WRONG_PORT` and `ROUTE_SHORTS_NETS`, one route at a time."""
    findings = []
    on_page = _ports_by_page(world.ports)
    for route, net in world.claims:
        page = (route.drawing_set, route.page)
        first, last = route.points[0].at, route.points[-1].at
        if (
            net is None
            or not _lands(world, route.a, page, first)
            or not _lands(world, route.b, page, last)
        ):
            findings.append(
                _error(
                    ROUTE_WRONG_PORT,
                    _identity(route),
                    "a route does not run between the ports it claims",
                )
            )
        if net is not None:
            findings.extend(_shorts(route, net, page, world.ports, on_page.get(page, ())))
    return findings


def _ports_by_page(ports: Ports) -> dict[Page, list[Handle]]:
    """The ports of `ports.net` located on each page, each list sorted, built in one pass."""
    located = sorted((port, page) for port, page in ports.at if port in ports.net)
    return {
        page: [port for port, _ in group] for page, group in by_key(located, itemgetter(1)).items()
    }


def _shorts(
    route: Route, net: Handle, page: Page, ports: Ports, candidates: Iterable[Handle]
) -> list[Finding]:
    """One `ROUTE_SHORTS_NETS` per port of another physical net that lies on the route."""
    return [
        _error(
            ROUTE_SHORTS_NETS,
            (*_identity(route), port),
            "a route touches a port of another physical net",
        )
        for port in candidates
        if ports.net[port] != net
        and any(
            _on_segment(ports.at[port, page], one.at, other.at)
            for one, other in pairwise(route.points)
        )
    ]


def _touches(world: _World) -> list[Finding]:
    """One `ROUTE_SHORTS_NETS` per pair of routes of different physical nets that touch."""
    claimed = [(net, route) for route, net in world.claims if net is not None]
    by_page = by_key(claimed, lambda claim: page_of(claim[1]))
    findings = []
    for page in sorted(by_page):
        on_cell: dict[Cell, list[tuple[Handle, Route, frozenset[str]]]] = defaultdict(list)
        for net, route in by_page[page]:
            for cell, axes in axes_of(tuple(one.at for one in route.points)).items():
                on_cell[cell].append((net, route, axes))
        first: dict[tuple[Identity, Identity], Cell] = {}
        for cell in sorted(on_cell):
            for (net, route, axes), (other_net, other, other_axes) in combinations(
                on_cell[cell], 2
            ):
                if net != other_net and not clean_crossing(axes, other_axes):
                    pair = sorted((_identity(route), _identity(other)))
                    first.setdefault((pair[0], pair[1]), cell)
        findings.extend(
            _error(
                ROUTE_SHORTS_NETS,
                (*one, *other),
                f"two physical nets touch on page {page[1]} of drawing set {page[0]} at {cell}",
            )
            for (one, other), cell in sorted(first.items())
        )
    return findings


def _on_segment(at: Point, start: Point, end: Point) -> bool:
    """Whether `at` lies on the closed segment from `start` to `end`, ends included."""
    return (
        (end.x - start.x) * (at.y - start.y) == (end.y - start.y) * (at.x - start.x)
        and min(start.x, end.x) <= at.x <= max(start.x, end.x)
        and min(start.y, end.y) <= at.y <= max(start.y, end.y)
    )


def _conductors(world: _World) -> list[Finding]:
    """`CONNECTION_NOT_DRAWN` and `CONNECTION_DRAWN_TWICE` for the conductors."""
    on: dict[Identity, Counter[Page]] = defaultdict(Counter)
    for route in world.layout.routes:
        on[_identity(route)][route.drawing_set, route.page] += 1
    findings = []
    for conductor in world.conductors:
        identity = (conductor.handle, conductor.a.port, conductor.b.port)
        shared = set(world.ports.pages.get(conductor.a.function, ())) & set(
            world.ports.pages.get(conductor.b.function, ())
        )
        routes, decisions = on[identity], world.decisions[identity]
        drawn = sum(routes[page] for page in shared)
        wanted_routes, wanted_decisions = (1, 0) if shared else (0, 1)
        if decisions < wanted_decisions or drawn < wanted_routes:
            findings.append(
                _error(
                    CONNECTION_NOT_DRAWN,
                    (conductor.handle,),
                    "a conductor is neither drawn nor cut",
                )
            )
        if (
            decisions > wanted_decisions
            or drawn > wanted_routes
            or any(page not in shared for page in routes)
        ):
            findings.append(_twice((conductor.handle,)))
    return findings


def _not_drawn(subjects: tuple[Handle, ...]) -> Finding:
    return _error(CONNECTION_NOT_DRAWN, subjects, "a connection is neither drawn nor cut")


def _twice(subjects: tuple[Handle, ...]) -> Finding:
    return _error(CONNECTION_DRAWN_TWICE, subjects, "a connection is drawn more than once")


def _groups(world: _World) -> list[Finding]:
    """`CONNECTION_NOT_DRAWN` and `CONNECTION_DRAWN_TWICE` for the net groups."""
    findings = []
    for group in world.net_groups:
        twice, missing = page_joins(group, world.ports, world.edges.get(group.net, {}))
        findings.extend(_twice(one) for one in sorted(twice))
        cuts_missing, extra = cut_gaps(group_cuts(group, world.ports), world.decisions)
        findings.extend(_twice(one) for one in extra)
        if missing or cuts_missing:
            findings.append(_not_drawn((group.net,)))
    return findings


def _markers(world: _World) -> list[Finding]:
    """`MARKER_UNPAIRED`: a severed decision's expected markers, and every marker nobody expects."""
    severed = frozenset(
        (one.connection, one.a, one.b)
        for one in world.layout.decisions
        if one.case is LinkCase.SEVERED
    )
    cuts: list[Cut] = [
        cut
        for one in world.conductors
        if (
            cut := conductor_cut(
                one,
                world.ports,
                function_units=world.function_units,
                set_units=world.set_units,
            )
        )
        is not None
    ]
    for group in world.net_groups:
        cuts.extend(group_cuts(group, world.ports))
    # T7.1: a cut between two units' drawing sets is cross-unit and has no markers, though a net
    # group drawn in two sets shares its identity with its severed cuts (layout-0127)
    cuts = [
        cut
        for cut in cuts
        if world.set_units.get(cut.owner[1][0]) == world.set_units.get(cut.user[1][0])
    ]
    return [
        _error(MARKER_UNPAIRED, subjects, "a marker has no partner, or a severed cut lacks one")
        for subjects in unpaired(tuple(cuts), severed, world.layout.markers, world.ports)
    ]
