"""layout-0334: the router searches no cell past the content box; such a wire is refused."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core import Size
from fransys_layout.core.route import route_page

from .route_fixtures import link_env

if TYPE_CHECKING:
    from fransys_layout.core.outputs import PageRoutes, Refused
    from fransys_layout.core.values import Finding

SOUTH = {"a": (40, 200, "S"), "z": (120, 200, "S")}
AREA = Size(160, 200)


def _route(area: Size | None) -> tuple[PageRoutes, tuple[Refused, ...], tuple[Finding, ...]]:
    return route_page(replace(link_env(SOUTH, {"n": ["a", "z"]}), area=area))


def test_the_unbounded_route_turns_one_lane_below_the_pins() -> None:
    routes, refused, _ = _route(None)
    assert (refused, max(y for w in routes.wires for _, y in w.points)) == ((), 208)


def test_a_bounded_route_draws_nothing_past_the_content_box_and_names_the_net() -> None:
    routes, refused, findings = _route(AREA)
    assert [r.net for r in refused] == ["n"]
    assert all(y <= AREA.h for w in routes.wires for _, y in w.points)
    assert [f.code for f in findings] == ["ROUTE_FAILED"]
