"""Private to `write/`: the `Route` builder (docs/design/engine.md 7, model layout-namespace.md)."""

from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.write.keys import PREFIX
from fransys_model.kernel import make_id
from fransys_model.layout import Route, RoutePoint

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages import Layout
    from fransys_model.layout import Page


def routes(
    keys: WriteKeys, layout: Layout, page_of: Mapping[PageId, Page], stamp: str
) -> list[Route]:
    """One `Route` per stage route: a conductor's, or one leg of a net with no conductor."""
    records = []
    for route in layout.routes:
        is_conductor = route.connection in keys.conductor
        if is_conductor:
            tail = keys.conductor[route.connection]
        else:
            first, second = sorted((route.a, route.b))
            tail = (*keys.port[first], *keys.port[second])
        key = (*PREFIX, "route", *tail)
        records.append(
            Route(
                id=make_id(Route, key),
                key=key,
                page=page_of[route.drawing_set, route.page].id,
                conductor=route.connection if is_conductor else None,
                net=None if is_conductor else route.connection,
                a=route.a,
                b=route.b,
                points=tuple(RoutePoint(index=p.index, x=p.at.x, y=p.at.y) for p in route.points),
                produced_by=stamp,
            )
        )
    return records
