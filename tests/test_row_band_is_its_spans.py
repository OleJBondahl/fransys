"""R408, R409: a row's solved band is the extent of the spans standing in it, one measure.

The y solve keeps a row by `row_extent.extent` (feet plus rooms) and the spans measure by it too,
so on every placed page, in every round, a row's spans reach exactly from its top to its bottom,
and every symbol's footprint with its room stands inside its row's band.
Six cases: the skid and the five corpus designs, built as `test_drawn_symbols_placed_by_core`
builds them. A build takes up to about 20 s, so each case is built once, in a module fixture.
"""

import importlib

import pytest
from test_drawn_symbols_placed_by_core import BUILDS, CASE_PARAMS

# `place` is also a name inside fransys_layout.core, so the module comes by name
place_module = importlib.import_module("fransys_layout.core.place")


def _row_misses(env, page) -> list[tuple]:
    """(page, row, band height, hull of the row's spans) of each row the spans do not fill.

    A row's spans are its columns' and its card blocks': a fan block also holds its trunk in
    another row, so its own columns measure it.
    """
    out = []
    for r, (top, bottom) in enumerate(page.bands):
        keys = [c for c, pc in env.pcs.items() if pc.row == r and c in page.spans]
        keys += [b for b in env.plan.rows[r].blocks if env.blocks[b].anchor and b in page.spans]
        if keys:
            hull = (min(page.spans[k][0] for k in keys), max(page.spans[k][1] for k in keys))
            if hull != (0, bottom - top):
                out.append((page.page, r, bottom - top, hull))
    return out


def _room_misses(env, page) -> list[tuple]:
    """(page, symbol) of each placed symbol whose footprint and room leave its row's band.

    Read from the footprints and rooms, never from the shared extent, so a room that the solve
    and the spans both dropped still shows here.
    """
    rows = {c.sym: pc.row for pc in env.pcs.values() for ln in pc.lanes for c in ln}
    rows |= {
        env.blocks[b].anchor: r
        for r, row in enumerate(env.plan.rows)
        for b in row.blocks
        if env.blocks[b].anchor
    }
    out = []
    for p in page.placed:
        room, (top, bottom) = env.rooms.get(p.sym), page.bands[rows[p.sym]]
        if (
            room
            and not top
            <= p.footprint.y - room.up
            <= p.footprint.y + p.footprint.h + room.down
            <= bottom
        ):
            out.append((page.page, p.sym))
    return out


@pytest.fixture(scope="module", params=CASE_PARAMS)
def misses(request: pytest.FixtureRequest) -> list[tuple]:
    """The misses of every page the solve placed, in every round of the build."""
    found: list[tuple] = []
    real = place_module.assemble

    def spy(env, *args):
        page = real(env, *args)
        found.extend(_row_misses(env, page))
        found.extend(_room_misses(env, page))
        return page

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(place_module, "assemble", spy)
        BUILDS[request.param]()
    return found


@pytest.mark.rule("PAGE-CUT")
def test_every_row_band_is_the_extent_of_its_spans(misses: list[tuple]) -> None:
    assert misses == []
