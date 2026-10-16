"""Stage 6 plants: gaps the router reports and does not fix, each a strict xfail with its cause.

A fix moves the plant to a plain test; stage 5 or stage 1 owns each one, never the router.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Options, build_flow, route_pages

from .pipeline_fixtures import cut_of, placed_from
from .route_fixtures import jog_stair, reversing_pair, with_crossed

OPTIONS = Options()


@pytest.mark.xfail(
    strict=True, reason="stage 1 does not fill Fan.crossed (layout-0275): a reversing pair is plain"
)
def test_stage_one_marks_the_reversed_pole_order_of_a_reversing_pair() -> None:
    flow = build_flow(reversing_pair((2, 1, 0)), OPTIONS)
    assert {f.id: f.crossed for f in flow.fans}["f:bL"] == (("K2", (2, 1, 0)),)


@pytest.mark.xfail(
    strict=True, reason="stage 5 leaves no y room under a crossed trunk for its levels"
)
def test_a_crossed_trunk_routes_without_a_finding_on_the_placement_as_stage_five_made_it() -> None:
    prob = reversing_pair((2, 1, 0))
    cut = with_crossed(cut_of(prob), "f:bL", (("K2", (2, 1, 0)),))
    routes = route_pages(placed_from(cut, prob, OPTIONS), cut, prob, OPTIONS)
    assert routes.findings == ()


def test_a_jog_stair_as_stage_five_placed_it_has_room_for_every_turn() -> None:
    """Shifted sideways only (as a column gap would), the stair's pins stay one grid apart."""
    prob = jog_stair()
    cut = cut_of(prob)
    placement = placed_from(cut, prob, OPTIONS)
    wide = replace(
        placement,
        pages=tuple(
            replace(
                pg,
                placed=tuple(
                    replace(
                        p,
                        pin_xy=tuple(replace(q, x=q.x + 90) for q in p.pin_xy),
                        footprint=replace(p.footprint, x=p.footprint.x + 90),
                    )
                    if p.sym.startswith("v")
                    else p
                    for p in pg.placed
                ),
            )
            for pg in placement.pages
        ),
    )
    assert route_pages(wide, cut, prob, OPTIONS).findings == ()
