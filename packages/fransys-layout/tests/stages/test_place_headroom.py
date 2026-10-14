"""`place` leaves whole routing lanes above row 0 (layout-0031) and, under them, the top
reference band every page keeps."""

import dataclasses

from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import translate
from fransys_layout.stages import place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import PAGE_OVERFULL, _reference_band


def _keepout(placed):
    return translate(placed.geometry.keepout, dx=placed.at.x, dy=placed.at.y)


def _tops(placed):
    return {one.function: _keepout(one).y for one in placed}


def _two_columns(*, headroom_lanes=None, sheet=SHEET):
    options = {} if headroom_lanes is None else {"headroom_lanes": headroom_lanes}
    return place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3, 4))),
        tuple(drawn(n) for n in (1, 2, 3, 4)),
        PageStacking(profile=PROFILE, sheet=sheet, **options),
    )


# Every page keeps a band along the content box's top (a turned reference's length plus
# one stub step), the same on every page; the columns start below it. The invented symbol's `in`
# port faces N at its keep-out top, so the band also covers a link marker standing there.
_BAND = _reference_band(SHEET, PROFILE)


# The least height two 32 G cells need: both bands and `row_gap` between the cells.
_TWO_LEAST = 2 * _BAND + 2 * 32 + PROFILE.row_gap


def _two_cells(headroom_lanes):
    return place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), drawn(2)),
        PageStacking(
            profile=PROFILE,
            sheet=dataclasses.replace(SHEET, content_height=_TWO_LEAST),
            headroom_lanes=headroom_lanes,
        ),
    )


def test_headroom_is_part_of_the_page_height_a_column_that_fits_without_it_may_not() -> None:
    """On the least height two cells need, cell 1 spans 56..88 and cell 2, narrowed to
    `row_gap`, 120..152, which ends on the floor (the content height less the bottom band) and
    fits. One lane pushes cell 2 to 128..160, past the floor, and spacing cannot narrow further.
    """
    placed, findings = _two_cells(0)
    assert findings == ()
    assert _keepout({one.function: one for one in placed}[hid("function", 2)]).y == 120
    _, findings = _two_cells(1)
    assert [f.code for f in findings] == [PAGE_OVERFULL]
    assert findings[0].subjects == (hid("function", 2),)
