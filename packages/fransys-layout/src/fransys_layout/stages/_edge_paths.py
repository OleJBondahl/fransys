"""Stage 7, route: one edge's polyline on a page, the search and its retries (route.py)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, Point, pad, union

from ._sides import Edge, joined, located
from .grid_path import Field, axes_of, cells_of, grid_path
from .sideways import sideways_ends
from .space import Obstacle, Shape, Space, span, unowned
from .wrap import wrap_strips

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._sides import Ends, Join
    from .space import Cell, End
    from .types import Handle, Profile


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
class _Taken:
    """The cells the routes drawn so far took: by net, by net and axes, and each port's exit."""

    used: dict[Cell, frozenset[Handle]]
    along: dict[Cell, dict[Handle, frozenset[str]]]
    port_exits: dict[Cell, dict[Handle, frozenset[str]]]

    def take(self, edge: Edge, points: tuple[Point, ...]) -> None:
        """Record the cells and axes a drawn route takes for its net."""
        for cell in cells_of(points):
            self.used[cell] = self.used.get(cell, frozenset()) | {edge.physical_net}
        for cell, axes in axes_of(points).items():
            nets = self.along.setdefault(cell, {})
            nets[edge.physical_net] = nets.get(edge.physical_net, frozenset()) | axes


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
    if found is None and port_exits:
        # layout-0223: a port boxed in by its neighbours' exit cells may still cross them straight.
        found = _search(edge, page, used, along, None)
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
