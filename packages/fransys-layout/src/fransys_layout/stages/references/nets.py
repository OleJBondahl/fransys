"""R7 B4 (deep dive): a net of three or more ports is drawn as one marker per port, no wire tree.

Owner ruling: no horizontal distribution wires. A net is the conductor graph (connections
joined at shared ports). Side-element ports do not count and keep their wires to the host.
A net whose every counted port is a terminal point branches by terminal points and keeps
its wires. The reference is the net's one terminal point; with none, or two or more, the
port whose function's item designation sorts first. Every other port's marker names the
reference and its page/column; the reference's marker lists the others' page/columns.

This module finds the star nets and the steps they are built from, all pure.
"""

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Sequence

from fransys_layout.conventions import FACTS
from fransys_layout.stages.terminal_facts import TerminalRead
from fransys_layout.stages.types import PortRef
from fransys_model.kernel import UnionFind

from .types import Star

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import Column, Connection, FunctionSpec, NetGroup
    from fransys_model.kernel import Id

    from .types import Beside, LinkWorld, Page


def shown(world: LinkWorld, ref: PortRef, exempt: frozenset[tuple[Id[Any], int]]) -> list[Page]:
    """The pages of `ref`'s function that show its marker: those of a set where it is not exempt."""
    return [page for page in world.where.get(ref.function, {}) if (ref.port, page[0]) not in exempt]


def star_nets(
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    columns: tuple[Column, ...],
    adjacent: Beside | None = None,  # S12, C3: where ports are wired beside, per set
) -> tuple[Star, ...]:
    """Every net of three or more counted ports that is not branched by terminal points."""
    spec = {one.function: one for one in specs}
    owner, nets = _counted_nets(connections, specs, columns)
    found = []
    for counted, wires in nets:
        star = _net_star(counted, owner, spec, wires, adjacent)
        if star is not None:
            found.append(star)
    return tuple(sorted(found, key=lambda star: star.ref.port))


def wires_star(wires: Sequence[Connection], specs: tuple[FunctionSpec, ...]) -> Star | None:
    """S20 M12: the star of the ports of `wires`, none of which is drawn, a reference at each."""
    owner = {ref.port: ref.function for one in wires for ref in (one.a, one.b)}
    return _net_star(sorted(owner), owner, {one.function: one for one in specs}, wires, None)


def star_wires(
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    columns: tuple[Column, ...],
) -> tuple[Connection, ...]:
    """S12: every conductor between two counted ports of a net of three or more counted ports."""
    _, nets = _counted_nets(connections, specs, columns)
    return tuple(c for _, wires in nets for c in wires)


def _counted_nets(
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    columns: tuple[Column, ...],
) -> tuple[dict[Id[Any], Id[Any]], list[tuple[list[Id[Any]], list[Connection]]]]:
    """Each port's owner, and each net of three or more counted ports with its inside wires."""
    side = side_functions(columns)
    owner, nets = _joined_nets(connections, _terminal_splits(connections, specs))
    found = []
    for ports in nets:
        counted = sorted(port for port in ports if owner[port] not in side)
        if len(counted) < 3:  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
            continue
        inside = set(counted)
        found.append(
            (counted, [c for c in connections if c.a.port in inside and c.b.port in inside])
        )
    return owner, found


def _net_star(
    counted: Sequence[Id[Any]],
    owner: Mapping[Id[Any], Id[Any]],
    spec: Mapping[Id[Any], FunctionSpec],
    wires: Sequence[Connection],
    adjacent: Beside | None,
) -> Star | None:
    """The star of one net's `counted` ports, or None when no drawing set has it in two clusters."""
    points = [port for port in counted if spec[owner[port]].roles.terminal]
    # C15(iii): B4's exemption was for branching by BRIDGED points (jumpers, which are no
    # connections here); terminal points joined by wires never qualify
    ref = reference(counted, points, wires, spec, owner)
    pairs = adjacent.pairs if adjacent is not None else {}
    beside = [(c, pairs.get((c.a.port, c.b.port), frozenset())) for c in wires]
    kept = [(c, sets) for c, sets in beside if sets]  # a conductor is routed where it is beside
    if not _is_star(counted, kept, adjacent.sets if adjacent is not None else None):
        return None  # in every drawing set its ports are all wired side by side
    clusters = _port_clusters(counted, [c for c, _ in kept])
    return Star(
        ports=tuple(PortRef(function=owner[port], port=port) for port in counted),
        ref=PortRef(function=owner[ref], port=ref),
        conductors=frozenset(c.handle for c in wires) - {c.handle for c, _ in kept},
        by_designation=len(points) != 1,
        cluster=tuple(sorted(clusters.items())),
        set_cluster=_set_clusters(counted, kept),
        wires=frozenset(c.handle for c in wires),
    )


def side_functions(columns: tuple[Column, ...]) -> frozenset[Id[Any]]:
    """The side elements: functions drawn beside their host, not counted in a star."""
    return frozenset(cell.function for column in columns for cell in column.cells if cell.side)


def with_orphans(
    stars: tuple[Star, ...],
    net_groups: tuple[NetGroup, ...],
    side: frozenset[Id[Any]],
) -> tuple[Star, ...]:
    """D9: a port of a declared net that the router leaves with no wire joins the net's markers."""
    found = list(stars)
    in_star = {ref.port for star in found for ref in star.ports}
    for group in net_groups:
        alone = [ref for ref in group.ports if ref.port not in in_star]
        home = next(
            (
                i
                for i, star in enumerate(found)
                if {r.port for r in star.ports} & {r.port for r in group.ports}
            ),
            None,
        )
        if len(alone) != 1 or home is None or alone[0].function in side:
            continue
        star = found[home]
        found[home] = replace(
            star,
            ports=tuple(sorted((*star.ports, alone[0]), key=lambda ref: ref.port)),
            cluster=tuple(sorted((*star.cluster, (alone[0].port, alone[0].port)))),
        )
        in_star.add(alone[0].port)
    return tuple(found)


def without_starred(
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    stars: tuple[Star, ...],
) -> tuple[tuple[Connection, ...], tuple[NetGroup, ...]]:
    """`connections` and `net_groups` without what the star markers draw."""
    dropped = {handle for star in stars for handle in star.conductors}
    in_star = {ref.port for star in stars for ref in star.ports}
    return (
        tuple(c for c in connections if c.handle not in dropped),
        # C15, ROUTE-FAN: a star port is drawn by the star's markers, so a declared net keeps
        # only its other, wire-drawn ports, and no group is left with fewer than two
        tuple(
            replace(g, ports=wired)
            for g in net_groups
            if len(wired := tuple(r for r in g.ports if r.port not in in_star)) > 1
        ),
    )


def _terminal_splits(
    connections: tuple[Connection, ...], specs: tuple[FunctionSpec, ...]
) -> dict[Id[Any], Id[Any]]:
    """R7 B5: an in-line one-port terminal splits its net by its second wire, handle to port."""
    split: dict[Id[Any], Id[Any]] = {}
    by_port: dict[Id[Any], list[Id[Any]]] = defaultdict(list)
    for c in connections:
        for end in {c.a.port, c.b.port}:
            by_port[end].append(c.handle)
    for one in specs:
        ports = {p.port for p in one.ports}
        wires = sorted({h for p in ports for h in by_port.get(p, ())})
        if FACTS["inline_terminal"].func(TerminalRead(one.roles.terminal, len(ports), len(wires))):
            split[wires[1]] = one.ports[0].port
    return split


def _joined_nets(
    connections: tuple[Connection, ...], split: Mapping[Id[Any], Id[Any]]
) -> tuple[dict[Id[Any], Id[Any]], list[list[Id[Any]]]]:
    """The conductor graph: each port's function, each net's ports; `split` wires at stand-ins."""
    joined: UnionFind[Id[Any]] = UnionFind()
    owner: dict[Id[Any], Id[Any]] = {}
    for connection in connections:
        for ref in (connection.a, connection.b):
            owner[ref.port] = ref.function
        if connection.handle in split:
            end = connection.b if connection.a.port == split[connection.handle] else connection.a
            joined.union(end.port, connection.handle)
            continue
        joined.union(connection.a.port, connection.b.port)
    nets: dict[Id[Any], list[Id[Any]]] = defaultdict(list)
    for port in owner:
        nets[joined.find(port)].append(port)
    for stand_in, port in split.items():  # the terminal's port counts in both halves
        nets[joined.find(stand_in)].append(port)
    return owner, list(nets.values())


def reference(
    counted: Sequence[Id[Any]],
    points: Sequence[Id[Any]],
    wires: Sequence[Connection],
    spec: Mapping[Id[Any], FunctionSpec],
    owner: Mapping[Id[Any], Id[Any]],
) -> Id[Any]:
    """C16, D9: reference port: terminal point, hub, a coil's, else lowest designation."""
    if len(points) == 1:
        return points[0]
    degree = {port: sum(port in (c.a.port, c.b.port) for c in wires) for port in counted}
    return min(
        counted,
        key=lambda port: (
            -degree[port],
            not spec[owner[port]].roles.coil,
            spec[owner[port]].designation,
            port,
        ),
    )


def _port_clusters(
    counted: Sequence[Id[Any]], kept: Sequence[Connection]
) -> dict[Id[Any], Id[Any]]:
    """C3: each counted port to the first port of its cluster, ports joined by a `kept` wire."""
    joined: UnionFind[Id[Any]] = UnionFind(counted)
    for c in kept:
        joined.union(c.a.port, c.b.port)
    return {port: joined.find(port) for port in counted}


def _set_clusters(
    counted: Sequence[Id[Any]], kept: Sequence[tuple[Connection, frozenset[int]]]
) -> tuple[tuple[int, Id[Any], Id[Any]], ...]:
    """layout-0070: `_port_clusters` per set, `(set, port, first)` for each non-first port."""
    found = []
    for drawing_set in sorted({s for _, sets in kept for s in sets}):
        wires = [c for c, sets in kept if drawing_set in sets]
        found.extend(
            (drawing_set, port, first)
            for port, first in _port_clusters(counted, wires).items()
            if first != port
        )
    return tuple(found)


_STAR_CLUSTERS = 2  # a net is a star from two clusters (ports not wired side by side)


def _is_star(
    counted: Sequence[Id[Any]],
    kept: Sequence[tuple[Connection, frozenset[int]]],
    sets_of: Mapping[Id[Any], frozenset[int]] | None,
) -> bool:
    """layout-0070 (D9 per set): whether the net's ports form two or more clusters in some set."""
    if sets_of is None:
        return len(set(_port_clusters(counted, [c for c, _ in kept]).values())) >= _STAR_CLUSTERS
    stands = {port: sets_of.get(port, frozenset()) for port in counted}
    for drawing_set in sorted({s for sets in stands.values() for s in sets}):
        here = [port for port in counted if drawing_set in stands[port]]
        wires = [c for c, sets in kept if drawing_set in sets]
        if len(set(_port_clusters(here, wires).values())) >= _STAR_CLUSTERS:
            return True
    return False


def branch_pages(
    pages: Sequence[tuple[int, int]],
    port: Id[Any],
    ref: Id[Any],
    in_cluster: tuple[tuple[int, Id[Any], Id[Any]], ...],
) -> list[tuple[int, int]]:
    """layout-0070: the `(set, page)`s where `port` takes a branch marker."""
    first = {(s, p): f for s, p, f in in_cluster}
    home: dict[int, tuple[int, int]] = {}
    for page in pages:
        home.setdefault(page[0], page)
    return [
        page
        for drawing_set, page in home.items()
        if (drawing_set, port) not in first and port != first.get((drawing_set, ref), ref)
    ]
