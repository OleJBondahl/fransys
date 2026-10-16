"""The stage 6 connectivity oracle: planted pages, hand-built envs and a stripped net."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import PinRef
from fransys_layout.core.outputs import Counts, PageRoutes
from fransys_layout.core.values import Ref, RefEnd, RefKind

from .pipeline_fixtures import cut_of, placed_of, routed_of
from .route_fixtures import by_bundle, env_view, oracle_on, row_wrap_env, three_end_env
from .route_oracle import connected_or_referenced
from .test_route import PLANTED


@pytest.mark.parametrize("name", sorted(PLANTED))
def test_the_oracle_holds_for_every_net_of_every_planted_page(name: str) -> None:
    """Every net of a planted problem is drawn whole, or ends in a planned Ref, on each page."""
    prob = PLANTED[name]()
    routes = by_bundle(routed_of(prob), prob)
    placement = placed_of(prob)
    refs = cut_of(prob).spec.reference_plan
    nodes = {s.id: s.nodes for s in prob.symbols}
    for net in prob.nets:
        for page in routes.pages:
            assert connected_or_referenced(routes, placement, refs, net, page.page, nodes)


def test_a_three_end_link_is_one_connected_tree() -> None:
    """A cross-link with three ends in one row is drawn as one connected tree."""
    assert oracle_on(three_end_env(), "t")


def test_a_net_across_two_rows_with_no_ref_is_drawn_whole() -> None:
    """A two-pin net across two rows with no planned Ref must be drawn whole."""
    assert oracle_on(row_wrap_env(), "x")


def test_the_oracle_fails_when_a_nets_wires_are_missing() -> None:
    """Dropping every wire of net n3 from a planted page makes the oracle say it is not whole."""
    prob = PLANTED["ring"]()
    routes = routed_of(prob)
    placement = placed_of(prob)
    refs = cut_of(prob).spec.reference_plan
    nodes = {s.id: s.nodes for s in prob.symbols}
    net = next(n for n in prob.nets if n.id == "n3")
    stripped = replace(
        routes,
        pages=tuple(
            replace(page, wires=tuple(w for w in page.wires if w.net != "n3"))
            for page in routes.pages
        ),
    )
    assert connected_or_referenced(routes, placement, refs, net, 1, nodes)
    assert not connected_or_referenced(stripped, placement, refs, net, 1, nodes)


def test_a_piece_that_ends_in_a_planned_ref_counts_as_joined() -> None:
    """Two unwired pins are joined only when each piece ends in a planned Ref on this page."""
    env = row_wrap_env()
    empty = PageRoutes(1, (), (), Counts(0, 0, 0, 0, 0))
    routes, placement, net = env_view(env, empty, "x")
    both = (
        Ref(
            "x",
            RefKind.ARROW,
            (RefEnd(1, None, PinRef("a", "p")), RefEnd(1, None, PinRef("z", "p"))),
        ),
    )
    only_a = (Ref("x", RefKind.ARROW, (RefEnd(1, None, PinRef("a", "p")),)),)
    assert connected_or_referenced(routes, placement, both, net, 1)
    assert not connected_or_referenced(routes, placement, only_a, net, 1)
    assert not connected_or_referenced(routes, placement, (), net, 1)
