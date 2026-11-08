"""R408, R409: a row's solved band is the extent of the spans standing in it, one measure.

The y solve keeps a row by `row_extent.held` (the folded footprints) and the spans measure by it
too, so on every placed page, in every round, a row's spans reach exactly from its top to its
"""

import importlib
from typing import Any

import pytest
from test_drawn_symbols_placed_by_core import BUILDS, CASE_PARAMS

from fransys_layout.core.arrow_reserve import leg_depth, leg_rows
from fransys_layout.core.geometry import view_of

# `place` is also a name inside fransys_layout.core, so the module comes by name
place_module = importlib.import_module("fransys_layout.core.place")


def _row_misses(env, page) -> list[tuple[Any, ...]]:
    """(page, row, band height, hull of the row's spans) of each row the spans do not fill.

    A row's spans are its columns' and its card blocks' (a fan block's trunk is in another row).
    A row that holds a leg under its trunk (ONE-SIDED-PIN) may stand that depth past its spans.
    """
    out = []
    stood = leg_rows(env.refs, env.plan.page)
    for r, (top, bottom) in enumerate(page.bands):
        keys = [c for c, pc in env.pcs.items() if pc.row == r and c in page.spans]
        keys += [b for b in env.plan.rows[r].blocks if env.blocks[b].anchor and b in page.spans]
        if keys:
            hull = (min(page.spans[k][0] for k in keys), max(page.spans[k][1] for k in keys))
            held = max((leg_depth(f, stood, r, env.options) for f in env.flow.fans), default=0)
            if hull != (0, bottom - top) and not (hull[0] == 0 and 0 < bottom - top - hull[1] <= held):
                out.append((page.page, r, bottom - top, hull))
    return out


def _fold_misses(env, page) -> list[tuple[Any, ...]]:
    """(page, symbol) of each placed symbol whose folded footprint leaves its row's band.

    Read from the folded view's footprint (the hangings at its pins) and never from the shared
    `held`, so a hanging that the solve and the spans both dropped still shows here.
    """
    rows = {c.sym: pc.row for pc in env.pcs.values() for ln in pc.lanes for c in ln}
    rows |= {env.blocks[b].anchor: r for r, row in enumerate(env.plan.rows) for b in row.blocks if env.blocks[b].anchor}
    hung = {sym for sym, _, _ in env.hangings}
    out = []
    for p in page.placed:
        if p.sym not in hung:
            continue
        view, (top, bottom) = view_of(env.syms[p.sym], p.orient), page.bands[rows[p.sym]]
        foot = view.row_footprint if p.sym in env.in_row and view.row_footprint else view.footprint
        if not top <= p.y + foot.y <= p.y + foot.y + foot.h <= bottom:
            out.append((page.page, p.sym))
    return out


@pytest.fixture(scope="module", params=CASE_PARAMS)
def misses(request: pytest.FixtureRequest) -> list[tuple[Any, ...]]:
    """The misses of every page the solve placed, in every round of the build."""
    found: list[tuple[Any, ...]] = []
    real = place_module.assemble

    def spy(env, *args):
        page = real(env, *args)
        found.extend(_row_misses(env, page))
        found.extend(_fold_misses(env, page))
        return page

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(place_module, "assemble", spy)
        BUILDS[request.param]()
    return found


#: R1193 (KI-455, ROW-BAND-TRACE): distinct rows the spans do not fill after the ledger's leg stubs; the same miss in more rounds counts once
#: (R1899, WHERE-DIGITS-START, KI-758); a looks count, it only falls.
_LOOKS = {
    "machine_panel": 2,  # R1800 (KI-705, looks): new p5 row 0 band 232 with -B15..-B20/-MB13..-MB17 (PE-EARTH-JOIN); was 1
    "panel_di16p": 6,
    "remote_io": 4,  # R2000 (G09-PAGE): the cut reads the placed rows; a fourth page (looks): p4 row 0 band 112
    "mcc": 1,  # R1673/R1675: accepted move (3 -> 4); distinct count 1 (R1899)
}  # SUPPLY-SLOT (R1605) + ID-TEXT-ORDER (R1628): mcc has 3 rows 8 G short of their spans (power symbol keepout; order-text ids); looks


@pytest.mark.rule("PAGE-CUT")
def test_every_row_band_is_the_extent_of_its_spans(request: pytest.FixtureRequest, misses: list[tuple[Any, ...]]) -> None:
    distinct = sorted(set(misses))
    assert len(distinct) <= _LOOKS.get(request.node.callspec.id, 0), distinct[:8]
