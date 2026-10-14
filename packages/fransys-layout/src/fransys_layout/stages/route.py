"""Stage 7, route: one orthogonal polyline per connection on a page."""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    Box,
    LayoutError,
    Point,
    on_wiring_grid,
    pad,
    port_page_at,
    union,
)
from fransys_model.kernel import Finding, Severity, UnionFind

from . import lookups
from ._sides import Edge, drawn_key, drawn_order, joined, joins_of, located, retarget
from .content import content_box
from .grid_path import Field, axes_of, cells_of, grid_path, reserve_exits
from .sideways import sideways_ends
from .space import Blocks, End, Obstacle, Shape, Space, span, unowned
from .types import Route, RoutePoint
from .wrap import wrap_strips

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ._sides import Ends, Join
    from .space import Cell
    from .types import (
        Connection,
        DrawnFunction,
        Handle,
        LinkMarker,
        NetGroup,
        PlacedFunction,
        PortRef,
        Profile,
        SheetFormat,
    )

ROUTE_FAILED = "ROUTE_FAILED"


@dataclass(frozen=True, slots=True)
class _Page:
    """What every edge of one page shares: ports, owned obstacles (layout-0038), tunables."""

    ends: Ends
    space: Space
    content: Box
    profile: Profile
    soft: tuple[Shape, ...] = ()  # the boxed connectors' rectangles inside `space`
    wrap_gap: int | None = None  # see `PageRoom.wrap_gap`


@dataclass(frozen=True, slots=True)
class PageRoom:
    """The room a page's wires route in: label boxes, link markers, sheet and costs."""

    reserved: tuple[Box, ...]
    profile: Profile
    sheet: SheetFormat
    markers: tuple[LinkMarker, ...] = ()
    aside: frozenset[Handle] = frozenset()  # conductors of a beside column (layout-0174)
    blocks: Blocks = field(default_factory=Blocks)  # the shapes of the boxes over moved pin views
    wrap_gap: int | None = None  # how near a run is to a side to count as along it; None = off


@dataclass(frozen=True, slots=True)
class _Taken:
    """The cells the routes drawn so far took: by net, by net and axes, and each port's exit."""

    used: Mapping[Cell, frozenset[Handle]]
    along: Mapping[Cell, dict[Handle, frozenset[str]]]
    port_exits: Mapping[Cell, dict[Handle, frozenset[str]]]


def route(
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    room: PageRoom,
) -> tuple[tuple[Route, ...], tuple[Finding, ...]]:
    """Route one page's functions: edges in drawn order."""
    if not placed:
        return (), ()
    placed_of = lookups.placed_of(placed, "route")
    drawn_of = lookups.drawn_of(drawn, "route")
    owner_of = lookups.owner_of(drawn)
    drawing_set, page = _one_page(placed)
    edges, ends = _edges(connections, net_groups, placed_of, drawn_of)
    page_inputs = _Page(
        ends=ends,
        space=_space(placed, room, owner_of),
        content=content_box(room.sheet),
        profile=room.profile,
        wrap_gap=room.wrap_gap,
        soft=room.blocks.soft,
    )
    used: dict[Cell, frozenset[Handle]] = {}
    # Each net's axes per cell; seeded with every port's first step (layout-0064)
    port_exits = reserve_exits(
        (edge.physical_net, ends[located(ref)]) for edge in edges for ref in (edge.a, edge.b)
    )
    # `along` accumulates the axes of every route drawn so far, `port_exits` never changes: a
    # snapshot of just the reserved exit cells (layout-0088), each also a hard obstacle for
    # every net but its own (`_draw`), so a detour drawn before a port's own edge can no
    # longer even cross that port's first step.
    along: dict[Cell, dict[Handle, frozenset[str]]] = {
        cell: dict(nets) for cell, nets in port_exits.items()
    }
    routes = []
    failures = []
    joins: list[Join] = []
    for edge in drawn_order(edges, ends, placed_of):
        beside = edge.connection in room.aside
        aim = (edge, None, None) if beside else retarget(edge, joins, ends, placed_of)
        points = _wired(edge, aim, page_inputs, _Taken(used, along, port_exits), beside=beside)
        if points is None:
            failures.append(
                Finding(
                    code=ROUTE_FAILED,
                    severity=Severity.ERROR,
                    subjects=edge.subjects,
                    message="no orthogonal path on the wiring grid joins the two ports",
                )
            )
            continue
        routes.append(
            Route(
                connection=edge.connection,
                physical_net=edge.physical_net,
                drawing_set=drawing_set,
                page=page,
                a=edge.a.port,
                b=edge.b.port,
                points=tuple(RoutePoint(index=index, at=at) for index, at in enumerate(points)),
            )
        )
        for cell in cells_of(points):
            used[cell] = used.get(cell, frozenset()) | {edge.physical_net}
        for cell, axes in axes_of(points).items():
            nets = along.setdefault(cell, {})
            nets[edge.physical_net] = nets.get(edge.physical_net, frozenset()) | axes
        joins.extend(joins_of(edge, points, placed_of))
    return (
        tuple(sorted(routes, key=lambda one: (one.connection, one.a, one.b))),
        tuple(sorted(failures, key=lambda one: (one.code, one.subjects))),
    )


def _aside(edge: Edge, page: _Page, *, above: bool = True) -> _Page:
    """`page` with a beside edge's ends facing along x (`sideways_ends`)."""
    return replace(page, ends=sideways_ends(edge, page.ends, above=above))


def _wired(
    edge: Edge,
    aim: tuple[Edge, Join | None, Join | None],
    page: _Page,
    taken: _Taken,
    *,
    beside: bool,
) -> tuple[Point, ...] | None:
    """One edge's polyline; a beside wire whose sideways pin is boxed in tries the other pin."""
    if not beside:
        return _polyline(edge, aim, page, taken)
    points = _polyline(edge, aim, _aside(edge, page), taken)
    if points is None:  # ROUTE-016: the pin that leaves sideways had a text against its lane
        points = _polyline(edge, aim, _aside(edge, page, above=False), taken)
    return points


def _marker_owner(marker: LinkMarker, owner_of: Mapping[Handle, Handle]) -> Handle:
    """The port a marker's box is owned by; a port no drawn function claims is a fault."""
    if marker.port not in owner_of:
        msg = "a link marker's port is not among the drawn functions' ports"
        raise LayoutError(msg)
    return marker.port


def _one_page(placed: tuple[PlacedFunction, ...]) -> tuple[int, int]:
    """The drawing set and page every placed function is on; a mixed set is an assembly fault."""
    drawing_set, page = placed[0].drawing_set, placed[0].page
    if any((function.drawing_set, function.page) != (drawing_set, page) for function in placed):
        msg = "route was given placed functions from more than one page"
        raise LayoutError(msg)
    return drawing_set, page


def _edges(
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    placed_of: Mapping[Handle, PlacedFunction],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> tuple[list[Edge], Ends]:
    """Every edge to draw, in no order (`drawn_order` orders them), with its ports located."""
    ends: Ends = {}
    edges = []
    for conductor in connections:
        if any(ref.function not in placed_of for ref in (conductor.a, conductor.b)):
            continue
        for ref in (conductor.a, conductor.b):
            ends[located(ref)] = port_end(ref, placed_of, drawn_of)
        edges.append(
            Edge(
                connection=conductor.handle,
                physical_net=conductor.physical_net,
                a=conductor.a,
                b=conductor.b,
                subjects=(conductor.handle,),
            )
        )
    for group in net_groups:
        on_page = [ref for ref in group.ports if ref.function in placed_of]
        for ref in on_page:
            ends[located(ref)] = port_end(ref, placed_of, drawn_of)
        for first, second in _tree(on_page, ends, placed_of):
            edges.append(
                Edge(
                    connection=group.net,
                    physical_net=group.physical_net,
                    a=first,
                    b=second,
                    subjects=(group.net, first.port, second.port),
                )
            )
    return edges, ends


def port_end(
    ref: PortRef,
    placed_of: Mapping[Handle, PlacedFunction],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> End:
    """Where a model port sits on the page and which way it points."""
    function = drawn_of.get(ref.function)
    if function is None:
        msg = "a function to route from is not among the drawn functions"
        raise LayoutError(msg)
    name = ref.symbol_port or next(
        (port.symbol_port for port in function.ports if port.port == ref.port), None
    )
    if name is None:
        msg = "a port to route from is not among its function's drawn ports"
        raise LayoutError(msg)
    placed = placed_of[ref.function]
    port = next((port for port in placed.geometry.ports if port.name == name), None)
    if port is None:
        msg = "a drawn port is not a port of the symbol the function is placed with"
        raise LayoutError(msg)
    at = port_page_at(placed.at, port)
    if not on_wiring_grid(at):
        msg = "a placed port is off the wiring grid, so no route can end on it"
        raise LayoutError(msg)
    return End(at=at, facing=port.facing)


def _tree(
    on_page: Sequence[PortRef], ends: Ends, placed_of: Mapping[Handle, PlacedFunction]
) -> list[tuple[PortRef, PortRef]]:
    """The net's spanning tree over this page's ports: joins first, then shortest."""
    pairs = [(one, other) for index, one in enumerate(on_page) for other in on_page[index + 1 :]]
    trees: UnionFind[Handle] = UnionFind(ref.port for ref in on_page)
    chosen = []
    for one, other in sorted(pairs, key=lambda pair: _order(pair, ends, placed_of)):
        if trees.union(one.port, other.port):
            chosen.append((one, other))
    return chosen


def _order(
    pair: tuple[PortRef, PortRef], ends: Ends, placed_of: Mapping[Handle, PlacedFunction]
) -> tuple[int, int, tuple[int, int], tuple[int, int], Handle, Handle]:
    """What orders a candidate edge of a spanning tree."""
    one, other = pair
    group, upper, lower = drawn_key(one, other, ends, placed_of)
    distance = abs(ends[located(one)].at.x - ends[located(other)].at.x) + abs(
        ends[located(one)].at.y - ends[located(other)].at.y
    )
    return group, distance, upper, lower, one.port, other.port


def _space(
    placed: tuple[PlacedFunction, ...],
    room: PageRoom,
    owner_of: Mapping[Handle, Handle],
) -> Space:
    """The page's obstacles: keep-outs, labels, blocks and markers."""
    return Space(
        shapes=tuple(Shape(owner=one.function, box=lookups.placed_keepout(one)) for one in placed)
        + tuple(Shape(owner=None, box=box) for box in room.reserved)
        + room.blocks.hard
        + room.blocks.soft
        + tuple(
            Shape(owner=_marker_owner(marker, owner_of), box=marker.box) for marker in room.markers
        ),
        sides=room.blocks.sides,
    )


def _polyline(
    edge: Edge, aim: tuple[Edge, Join | None, Join | None], page: _Page, taken: _Taken
) -> tuple[Point, ...] | None:
    """One edge's polyline: to the carrier's port along its join when it can, else direct."""
    aimed, first, second = aim
    if first is not None or second is not None:
        mid = _draw(aimed, page, taken.used, taken.along, taken.port_exits)
        if mid is not None:
            return joined(mid, first, second)
    return _draw(edge, page, taken.used, taken.along, taken.port_exits)


def _draw(
    edge: Edge,
    page: _Page,
    used: Mapping[Cell, frozenset[Handle]],
    along: Mapping[Cell, dict[Handle, frozenset[str]]] | None = None,
    port_exits: Mapping[Cell, dict[Handle, frozenset[str]]] | None = None,
) -> tuple[Point, ...] | None:
    """One edge's polyline: all rectangles blocked, then all opened."""
    found = _search(edge, page, used, along, port_exits)
    if found is None and page.soft:
        found = _search(edge, _all_rectangles_open(page), used, along, port_exits)
    if found is None:
        return None
    ends = [page.ends[located(one)].at for one in (edge.a, edge.b)]
    own = {edge.a.function, edge.a.port, edge.b.function, edge.b.port}
    strips = wrap_strips(found, page.space.shapes, own, ends, (page.content, page.wrap_gap))
    if not strips:
        return found
    closed = replace(page, space=replace(page.space, shapes=(*page.space.shapes, *unowned(strips))))
    return _search(edge, closed, used, along, port_exits) or found


def _all_rectangles_open(page: _Page) -> _Page:
    """Last resort (trial): every boxed rectangle open."""
    shapes = tuple(s for s in page.space.shapes if s not in page.soft)
    return replace(page, space=replace(page.space, shapes=shapes))


def _search(
    edge: Edge,
    page: _Page,
    used: Mapping[Cell, frozenset[Handle]],
    along: Mapping[Cell, dict[Handle, frozenset[str]]] | None = None,
    port_exits: Mapping[Cell, dict[Handle, frozenset[str]]] | None = None,
) -> tuple[Point, ...] | None:
    """One edge's polyline: padded box, then one widening."""
    start, goal = page.ends[located(edge.a)], page.ends[located(edge.b)]
    if start.at == goal.at:
        return (start.at, goal.at)
    padded = pad(span(start.at, goal.at), page.profile.route_margin)
    free = frozenset(cell for cell, nets in used.items() if edge.physical_net in nets)
    busy = frozenset(
        cell for cell, nets in used.items() if any(net != edge.physical_net for net in nets)
    )
    axes: dict[Cell, frozenset[str]] = {}
    for cell, nets in (along or {}).items():
        foreign = [a for net, a in nets.items() if net != edge.physical_net]
        if foreign:
            axes[cell] = frozenset().union(*foreign)
    foreign_exits = tuple(
        Obstacle(box=Box(x=cell[0], y=cell[1], width=0, height=0), lanes=())
        for cell, nets in (port_exits or {}).items()
        if edge.physical_net not in nets
    )
    widened = union(padded, page.content)
    for region in (padded,) if widened == padded else (padded, widened):
        points = grid_path(
            start,
            goal,
            Field(
                region=region,
                obstacles=(
                    *page.space.obstacles(_own_ends(edge, page.ends), region),
                    *foreign_exits,
                ),
                free=free,
                busy=busy,
                turn_penalty=page.profile.route_turn_penalty,
                crossing_penalty=page.profile.route_crossing_penalty,
                axes=axes,
                sides=page.space.sides,
            ),
        )
        if points is not None:
            return points
    return None


def _own_ends(edge: Edge, ends: Ends) -> dict[Handle, tuple[End, ...]]:
    """The edge's own ends by owner: only its two endpoint ports carry lanes (`Space.obstacles`)."""
    own: dict[Handle, tuple[End, ...]] = {}
    for ref in (edge.a, edge.b):
        for owner in (ref.function, ref.port):
            own[owner] = (*own.get(owner, ()), ends[located(ref)])
    return own
