"""What a net group's drawn edges and cuts leave undrawn or doubled, private to coherence.

Refs: lint.md 6.8.
"""

from collections import Counter
from typing import TYPE_CHECKING

from fransys_model.kernel import UnionFind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages import Handle, NetGroup, Route

    from ._cuts import Cut
    from ._ports import Page, Ports
    from .coherence import Identity


def identity(route: Route) -> Identity:
    """What a finding about a route names: its `(connection, a, b)`."""
    return route.connection, route.a, route.b


def joined(
    page: Page,
    on_page: Sequence[Handle],
    by_page: Mapping[Page, list[Route]],
) -> tuple[UnionFind[Handle], set[Identity]]:
    """The components the edges of a net group make of `on_page`, and the surplus edges."""
    components: UnionFind[Handle] = UnionFind()
    surplus: set[Identity] = set()
    for route in sorted(by_page.get(page, ()), key=identity):
        if not components.union(route.a, route.b):
            surplus.add(identity(route))
    for other, routes in by_page.items():
        for route in routes if other != page else ():
            if route.a in on_page and route.b in on_page:
                components.union(route.a, route.b)
    return components, surplus


def routed_twice(by_page: Mapping[Page, list[Route]]) -> set[Identity]:
    """The identities drawn by more than one route of a net group."""
    counts = Counter(identity(route) for routes in by_page.values() for route in routes)
    return {one for one, count in counts.items() if count > 1}


def page_joins(
    group: NetGroup, ports: Ports, by_page: Mapping[Page, list[Route]]
) -> tuple[set[Identity], bool]:
    """A group's doubled identities, and whether some page leaves its ports apart."""
    pages = {page for ref in group.ports for page in ports.pages.get(ref.function, ())}
    twice = routed_twice(by_page)
    missing = False
    for page in sorted(pages):
        on_page = [ref.port for ref in group.ports if (ref.port, page) in ports.at]
        components, surplus = joined(page, on_page, by_page)
        twice |= surplus
        missing |= len({components.find(port) for port in on_page}) > 1
    return twice, missing


def cut_gaps(cuts: Sequence[Cut], decisions: Mapping[Identity, int]) -> tuple[bool, list[Identity]]:
    """Whether a cut has fewer decisions than it needs, and the identities with too many."""
    missing = False
    extra: list[Identity] = []
    for one, count in Counter((cut.connection, cut.a, cut.b) for cut in cuts).items():
        missing |= decisions[one] < count
        if decisions[one] > count:
            extra.append(one)
    return missing, extra
