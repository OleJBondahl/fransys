"""`route` over one page's facts as keywords: the tests state each fact, this builds `PageRoom`."""

from fransys_layout.stages import route as route_page
from fransys_layout.stages.route import PageRoom


def route(connections, net_groups, placed, drawn, **room):
    """`stages.route` with `PageRoom`'s fields as keywords."""
    return route_page(connections, net_groups, placed, drawn, PageRoom(**room))
