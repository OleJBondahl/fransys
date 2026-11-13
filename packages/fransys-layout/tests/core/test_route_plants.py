"""Stage 6 plants: gaps the router reports and does not fix, each a strict xfail with its cause.

A fix moves the plant to a plain test; stage 5 or stage 1 owns each one, never the router.
"""

from __future__ import annotations

from dataclasses import replace

from options_fixtures import core_options

from fransys_layout.core.route import route_pages

from .conftest import MARKER
from .pipeline_fixtures import cut_of, placed_from
from .route_fixtures import jog_stair

OPTIONS = core_options(
    marker=MARKER,
)


def test_a_jog_stair_shifted_after_stage_five_has_no_row_so_each_jog_is_refused() -> None:
    """Shifted sideways only, the stair's pins stay one grid apart: no row, nothing drawn (R454)."""
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
    routes = route_pages(wide, cut, prob, OPTIONS)
    assert routes.failed
    assert all(r.ends is not None and len(r.ends) == 2 for r in routes.failed)
