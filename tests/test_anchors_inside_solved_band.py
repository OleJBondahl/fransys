"""MEASURE (layout-0374, 0377): the solved spans cover anchors through the owners' rooms.

On the demo skid and the corpus designs, every anchored outline lies inside its owner's solved span.
"""

import pytest
from test_drawn_symbols_placed_by_core import CASE_PARAMS, _drawn_and_layouts


@pytest.fixture(scope="module", params=CASE_PARAMS)
def layouts(request: pytest.FixtureRequest):
    return _drawn_and_layouts(request.param)[1]


@pytest.mark.rule("PAGE-CUT")
def test_every_anchored_outline_lies_inside_its_rows_solved_spans(layouts) -> None:
    """The spans of the row holding an anchor's pin, from its top, hold the anchored outline."""
    out = []
    for layout in layouts:
        pages = {pg.page: pg for pg in layout.placement.pages}
        plans = {pl.page: pl for pl in layout.pages}
        for a in layout.annotations.anchored:
            pg, pin_y = pages[a.page], a.lead[0][1]
            r = next((i for i, (t, b) in enumerate(pg.bands) if t <= pin_y <= b), -1)
            keys = (*plans[a.page].rows[r].columns, *plans[a.page].rows[r].blocks)
            mine = [pg.spans[k] for k in keys if k in pg.spans]
            lo, hi = (
                pg.bands[r][0] + min(m[0] for m in mine),
                pg.bands[r][0] + max(m[1] for m in mine),
            )
            if a.outline.y < lo or a.outline.y + a.outline.h > hi:
                out.append((a.page, a.sym, a.pin, a.outline, (lo, hi)))
    assert out == []
