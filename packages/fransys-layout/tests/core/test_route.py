"""Stage 6 route_pages: the wires of whole pages, cross-links, refusals and the invariants."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Box, Options, PlacementProblem
from fransys_layout.core.outputs import Placed, Routes, Wire
from fransys_layout.core.route import route_page, route_pages
from fransys_layout.core.route_counts import collinear, demand

from .conftest import MARKER_BOX
from .cut_fixtures import elem
from .cycle_fixtures import ring_problem
from .pipeline_fixtures import cut_of, placed_of, routed_of
from .place_fixtures import card_with_coils, row_group_three
from .route_fixtures import (
    by_bundle,
    envs_of,
    link_across_box,
    link_env,
    net_points,
    pin_reached,
    reversing_pair,
    two_links_one_gap,
)

if TYPE_CHECKING:
    from fransys_layout.core.route_env import RouteEnv

PLANTED = {
    "card": card_with_coils,
    "ring": link_across_box,
    "two-rings": two_links_one_gap,
    "bundles": reversing_pair,
    "row-group": lambda: row_group_three("g"),
}


@pytest.fixture(params=sorted(PLANTED))
def planted(request: pytest.FixtureRequest) -> PlacementProblem:
    return PLANTED[request.param]()


def all_wires(routes: Routes) -> list[Wire]:
    return [w for page in routes.pages for w in page.wires]


def test_every_pin_of_every_net_is_the_end_of_a_wire_of_its_net(planted: PlacementProblem) -> None:
    reached = pin_reached(by_bundle(routed_of(planted), planted), placed_of(planted), planted)
    assert reached == {(r.sym, r.pin) for n in planted.nets for r in n.pins}


def test_nothing_is_refused_on_the_planted_pages(planted: PlacementProblem) -> None:
    routes = routed_of(planted)
    assert (routes.failed, routes.findings) == ((), ())


def test_no_two_nets_share_a_collinear_run(planted: PlacementProblem) -> None:
    routes = routed_of(planted)
    assert all(collinear(page.wires) == 0 for page in routes.pages)


def test_route_pages_twice_gives_equal_routes(planted: PlacementProblem) -> None:
    assert routed_of(planted) == routed_of(planted)


def test_demand_has_one_row_per_gap_and_the_page_counts_match_the_wires(
    planted: PlacementProblem,
) -> None:
    placement = placed_of(planted)
    routes = routed_of(planted)
    for pg, page in zip(placement.pages, routes.pages, strict=True):
        assert [d.gap for d in page.demand] == [g.id for g in pg.gaps]
        assert page.demand == demand(page.wires, pg.gaps)


def test_an_open_end_draws_nothing() -> None:
    """card_with_coils has open feet: only the three box wires are drawn."""
    wires = all_wires(routed_of(card_with_coils(3)))
    assert len(wires) == 3
    assert {w.kind for w in wires} == {"straight"}


def test_a_ring_is_closed_by_one_routed_net_whose_ends_are_its_pins() -> None:
    prob = link_across_box()
    routes = routed_of(prob)
    placement = placed_of(prob)
    ends = {end for pts in net_points(routes, "n3") for end in (pts[0], pts[-1])}
    pins = {(q.x, q.y) for pg in placement.pages for p in pg.placed for q in p.pin_xy}
    assert ends & pins
    assert {w.kind for w in all_wires(routes) if w.net == "n3"} == {"routed"}


def test_a_page_wider_than_the_page_routes_without_an_index_error() -> None:
    """Stage 5 reports a row wider than the page; the A* map is sized from the footprints."""
    base = ring_problem()
    wide = tuple(elem("a", 1500) if s.id == "a" else s for s in base.symbols)
    prob = replace(base, symbols=wide)
    placement = placed_of(prob)
    routes = routed_of(prob)
    right = max(p.footprint.x + p.footprint.w for pg in placement.pages for p in pg.placed)
    assert right > prob.area.w
    assert any(w.kind == "routed" for w in all_wires(routes))


def test_a_boxed_in_link_is_a_finding_with_no_wire_and_the_others_still_route() -> None:
    (env,) = envs_of(link_across_box())
    wall = Box(0, 0, 2000, 400)
    placed = {**env.placed, "wall": Placed("wall", 1, 0, 0, "R0", wall, wall, ())}
    page, failed, findings = route_page(replace(env, placed=placed))
    assert failed == ("n3",)
    (finding,) = findings
    assert (finding.code, finding.subject, finding.page) == ("ROUTE_FAILED", "n3", 1)
    assert "n3" in finding.text
    assert "move a symbol" in finding.text
    assert not [w for w in page.wires if w.net == "n3"]
    assert {w.net for w in page.wires} >= {"n1", "n2", "n4", "n5"}


def test_a_net_cut_into_references_is_drawn_as_references_not_routed() -> None:
    (env,) = envs_of(link_across_box())
    page, failed, findings = route_page(replace(env, cut_nets=frozenset({"n3"})))
    assert (failed, findings) == ((), ())
    assert not [w for w in page.wires if w.net == "n3"]


def test_a_link_with_an_end_on_another_page_is_a_finding_unless_it_is_cut() -> None:
    (env,) = envs_of(link_across_box())
    page, failed, findings = route_page(
        replace(env, placed={s: p for s, p in env.placed.items() if s != "s"})
    )
    assert failed == ("n3",)
    assert "another page" in next(f.text for f in findings if f.subject == "n3")
    assert not [w for w in page.wires if w.net == "n3"]


def ripple(rounds: int) -> RouteEnv:
    pins = {
        "v0": (250, 64, "S"),
        "v1": (250, 184, "N"),
        "h0": (120, 120, "E"),
        "h1": (264, 120, "W"),
    }
    opts = replace(
        Options(marker=MARKER_BOX), crossing_penalty=100, bend_penalty=1, reroute_rounds=rounds
    )
    return link_env(pins, {"v": ("v0", "v1"), "h": ("h0", "h1")}, opts)


def test_one_reroute_removes_the_crossing_the_first_pass_left() -> None:
    """The second link crosses the first (a detour costs more); ripping the first up detours it."""
    assert route_page(ripple(0))[0].counts.crossings == 1
    assert route_page(ripple(2))[0].counts.crossings == 0


def test_route_pages_is_the_public_entry_and_matches_the_stage_functions() -> None:
    prob = link_across_box()
    cut = cut_of(prob)
    placement = placed_of(prob)
    routes = route_pages(placement, cut, prob, Options(marker=MARKER_BOX))
    assert routes == routed_of(prob)
