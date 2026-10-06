"""Private to `engine.py`: a connection is drawn on exactly one page (route.md 6.5, layout-0030).

Both ends of a connection may be placed on several pages, as two replicated terminals wired to
each other are. The engine routes it once, on the common page that holds most of its ends at home
(not as replicas); a tie takes the earliest page.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .references.types import Seated
    from .types import Column, Connection, Handle, NetGroup, Route

type Page = tuple[int, int]
type Homes = dict[tuple[Handle, Page], bool]


def _homes(
    placed: tuple[Seated, ...],
    replicas: frozenset[AuthoringKey],
    attached: frozenset[tuple[Handle, AuthoringKey]] = frozenset(),
) -> Homes:
    """R7 B8: whether each `(function, page)` is at home: no replica column, no attached replica."""
    return {
        (one.function, (one.drawing_set, one.page)): one.column not in replicas
        and (one.function, one.column) not in attached
        for one in placed
    }


def _choose(pages: Iterable[Page], ends: tuple[Handle, Handle], at_home: Homes) -> Page:
    """The page where most of `ends` are at home, the earliest of equals."""
    return min(pages, key=lambda page: (-sum(at_home[end, page] for end in ends), page))


def _conductor_pages(connections: tuple[Connection, ...], at_home: Homes) -> dict[Handle, Page]:
    """The page each conductor with more than one common page is routed on."""
    pages_of: dict[Handle, set[Page]] = defaultdict(set)
    for function, page in at_home:
        pages_of[function].add(page)
    chosen = {}
    for one in connections:
        ends = (one.a.function, one.b.function)
        common = pages_of[ends[0]] & pages_of[ends[1]]
        if len(common) > 1:
            chosen[one.handle] = _choose(common, ends, at_home)
    return chosen


def _wired_ends(
    connections: tuple[Connection, ...], at_home: Homes, routed_on: Mapping[Handle, Page]
) -> frozenset[tuple[Any, int, int]]:
    """`(port, drawing set, page)` of every end of a connection drawn on that page."""
    pages_of: dict[Handle, set[Page]] = defaultdict(set)
    for function, page in at_home:
        pages_of[function].add(page)
    return frozenset(
        (end.port, *page)
        for one in connections
        for page in pages_of[one.a.function] & pages_of[one.b.function]
        if routed_on.get(one.handle, page) == page
        for end in (one.a, one.b)
    )


def page_wiring(
    connections: tuple[Connection, ...],
    columns: tuple[Column, ...],
    seats: tuple[Seated, ...],
    replicas: frozenset[AuthoringKey],
    net_groups: tuple[NetGroup, ...] = (),
) -> tuple[Homes, dict[Handle, Page], frozenset[tuple[Any, int, int]]]:
    """The one definition of "wired on this page": homes, conductor pages, wired ends (S10)."""
    # I4 (designer's (A)): a star reference on a port a drawn wire also reaches leaves
    # the wire sideways, so the wire never crosses it (D9: a hub pin or a member's port alike)
    attached = frozenset(
        (cell.function, column.key) for column in columns for cell in column.cells if cell.replica
    )
    at_home = _homes(seats, replicas, attached)
    routed_on = _conductor_pages(connections, at_home)
    wired = _wired_ends(connections, at_home, routed_on) | _net_wired(net_groups, at_home)
    return at_home, routed_on, wired


def _net_wired(net_groups: tuple[NetGroup, ...], at_home: Homes) -> frozenset[tuple[Any, int, int]]:
    """`(port, set, page)` of each net-group port with a mate on its page: wired (S20 M7)."""
    pages_of: dict[Handle, list[Page]] = defaultdict(list)
    for function, page in at_home:
        pages_of[function].append(page)
    found = set()
    for group in net_groups:
        on_page: dict[Page, set[Handle]] = defaultdict(set)
        for ref in group.ports:
            for page in pages_of[ref.function]:
                on_page[page].add(ref.port)
        found.update(
            (port, *page) for page, ports in on_page.items() if len(ports) > 1 for port in ports
        )
    return frozenset(found)


def keep_chosen_edges(
    routes: Sequence[Route], net_groups: tuple[NetGroup, ...], at_home: Homes
) -> list[Route]:
    """Drop a net-group edge routed on several pages from all but the chosen page."""
    function_of = {ref.port: ref.function for group in net_groups for ref in group.ports}
    nets = {group.net for group in net_groups}
    pages_of: dict[tuple[Handle, Handle, Handle], list[Page]] = defaultdict(list)
    for one in routes:
        pages_of[one.connection, one.a, one.b].append((one.drawing_set, one.page))
    return [
        one
        for one in routes
        if one.connection not in nets
        or (one.drawing_set, one.page)
        == _choose(
            pages_of[one.connection, one.a, one.b],
            (function_of[one.a], function_of[one.b]),
            at_home,
        )
    ]
