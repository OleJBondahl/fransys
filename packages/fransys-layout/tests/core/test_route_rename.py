"""Stage 6 reads no id text beyond the natural key: respelling every id, or reversing the
unordered input tuples, changes nothing in the routes but the spelling (as test_place_rename
does for stage 5)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from options_fixtures import core_options

from fransys_layout.core.place import place_pages
from fransys_layout.core.route import route_page, route_pages

from .conftest import MARKER
from .cut_respell import back_of, id_sets, make_maps, respell_cut, respell_problem
from .pipeline_fixtures import cut_of
from .place_fixtures import two_edge_card
from .route_fixtures import jog_stair, link_env, reversing_pair, with_crossed
from .test_cut_rename import SPELLINGS, card_that_wraps

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import Placement, PlacementProblem
    from fransys_layout.core.outputs import Routes
    from fransys_layout.core.values import CutResult

OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    driver_first=True,
    arrow_sides=("E", "W"),
)
STEP = OPTIONS.wiring_grid


class Case(NamedTuple):
    """A builder, an edit of its cut, the symbols moved after placement, and its feature."""

    build: Callable[[], PlacementProblem]
    edit: Callable[[CutResult], CutResult]
    moved: tuple[tuple[str, int, int], ...]
    feature: Callable[[Routes], bool]


def _jogs(routes: Routes) -> bool:
    return (
        sum(len(w.points) == 4 for p in routes.pages for w in p.wires if w.kind == "straight") >= 3
    )


def _crossed(routes: Routes) -> bool:
    return any(len(w.points) == 4 for p in routes.pages for w in p.wires if w.kind == "drop")


def _links(routes: Routes) -> bool:
    return any(w.kind == "routed" for p in routes.pages for w in p.wires)


def _same(cut: CutResult) -> CutResult:
    return cut


def _crossed_cut(cut: CutResult) -> CutResult:
    return with_crossed(cut, "f:bL", (("K2", (2, 1, 0)),))


def _ring() -> PlacementProblem:
    from .route_fixtures import link_across_box

    return link_across_box()


CASES: dict[str, Case] = {
    "two_edge_card": Case(lambda: two_edge_card(16, 96), _same, (), lambda r: len(r.pages) >= 1),
    "two_rows": Case(card_that_wraps, _same, (), lambda r: len(r.pages[0].wires) > 3),
    "jog_stair": Case(jog_stair, _same, tuple((f"v{k}", 90, 40) for k in range(3)), _jogs),
    "crossed_bundle": Case(reversing_pair, _crossed_cut, (("K2", 0, 3 * STEP),), _crossed),
    "cross_link_ring": Case(_ring, _same, (), _links),
}


def moved(pl: Placement, shifts: dict[str, tuple[int, int]]) -> Placement:
    """The placement with some symbols moved (body, footprint and pins), as a router input."""

    def shift(p: Any) -> Any:
        dx, dy = shifts.get(p.sym, (0, 0))
        return replace(
            p,
            x=p.x + dx,
            y=p.y + dy,
            body=replace(p.body, x=p.body.x + dx, y=p.body.y + dy),
            footprint=replace(p.footprint, x=p.footprint.x + dx, y=p.footprint.y + dy),
            pin_xy=tuple(replace(q, x=q.x + dx, y=q.y + dy) for q in p.pin_xy),
        )

    pages = tuple(replace(pg, placed=tuple(shift(p) for p in pg.placed)) for pg in pl.pages)
    return replace(pl, pages=pages)


def canon_routes(routes: Routes, back: Callable[[str | None], str | None]) -> tuple[Any, ...]:
    """The routes as plain tuples with every id mapped back; wires sorted, no finding text."""
    pages = tuple(
        (
            p.page,
            tuple(sorted((back(w.net), w.points, w.kind, w.lanes) for w in p.wires)),
            tuple((d.tracks) for d in p.demand),
            p.counts,
        )
        for p in routes.pages
    )
    finds = tuple(sorted((f.code, f.page, back(f.subject)) for f in routes.findings))
    return pages, tuple(sorted(back(r.net) or "" for r in routes.failed)), finds


def routed(case: Case, cut: CutResult, prob: PlacementProblem, ids: dict[str, str]) -> Routes:
    """Stages 5 and 6 on a cut, with the case's symbols moved by their (possibly respelled) ids."""
    shifts = {ids.get(sym, sym): (dx, dy) for sym, dx, dy in case.moved}
    return route_pages(moved(place_pages(cut, prob, OPTIONS), shifts), cut, prob, OPTIONS)


def _checked(name: str) -> tuple[Case, PlacementProblem, CutResult, tuple[Any, ...]]:
    case = CASES[name]
    prob = case.build()
    cut = case.edit(cut_of(prob, OPTIONS))
    routes = routed(case, cut, prob, {})
    assert case.feature(routes), name
    assert routes.failed == ()
    return case, prob, cut, canon_routes(routes, back_of({}))


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("form", SPELLINGS)
def test_routes_do_not_depend_on_how_ids_are_spelled(name: str, form: str) -> None:
    case, prob, cut, want = _checked(name)
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    got = routed(case, respell_cut(cut, maps), respell_problem(prob, maps), maps)
    assert canon_routes(got, back_of(maps)) == want


@pytest.mark.parametrize("name", CASES)
def test_routes_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    case, prob, cut, want = _checked(name)
    flow = cut.flow
    flipped = replace(
        flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1]
    )
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    got = routed(case, replace(cut, flow=flipped), reversed_prob, {})
    assert canon_routes(got, back_of({})) == want


def crossed_pair(first: str, second: str) -> dict[str, tuple[Any, ...]]:
    """Two cross-links of equal bounding box, an X: the one routed first shapes the other."""
    pins = {
        "p0": (40, 40, "E"),
        "p1": (200, 200, "W"),
        "q0": (40, 200, "E"),
        "q1": (200, 40, "W"),
    }
    opts = replace(OPTIONS, crossing_penalty=40, reroute_rounds=0)
    env = link_env(pins, {first: ("p0", "p1"), second: ("q0", "q1")}, opts)
    page = route_page(env)[0]
    return {w.net: w.points for w in page.wires}


def test_links_of_equal_size_are_routed_in_natural_order_not_string_order() -> None:
    """n9 and n10 tie on size: natural order puts n9 first, as n1 and n2 do (string order, n10)."""
    spelled = crossed_pair("n9", "n10")
    plain = crossed_pair("n1", "n2")
    back = {"n9": "n1", "n10": "n2"}
    assert {back[n]: pts for n, pts in spelled.items()} == plain
