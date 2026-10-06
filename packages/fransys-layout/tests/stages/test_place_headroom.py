"""`place` leaves whole routing lanes above row 0 (layout-0031) and, under them, the top
reference band every page keeps (S20 M4)."""

import dataclasses

from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import WIRING_GRID, translate
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


# M4: every page keeps a band along the content box's top (a turned reference's length plus
# one stub step), the same on every page; the columns start below it. The invented symbol's `in`
# port faces N at its keep-out top, so the band also covers a link marker standing there.
_BAND = _reference_band(SHEET, PROFILE)


def test_without_headroom_row_zero_starts_below_the_top_band() -> None:
    """M4: no lanes, and the first keep-out box of every column starts on the top band."""
    placed, _ = _two_columns()
    tops = _tops(placed)
    assert WIRING_GRID + PROFILE.text_height <= _BAND
    assert tops[hid("function", 1)] == tops[hid("function", 3)] == _BAND


def test_headroom_lanes_move_row_zero_down_by_whole_wiring_grid_steps() -> None:
    """Three lanes (layout-0031) come on top of M4's band: the top moves 3 * WIRING_GRID."""
    flush = _tops(_two_columns()[0])
    lifted = _tops(_two_columns(headroom_lanes=3)[0])
    assert lifted[hid("function", 1)] == lifted[hid("function", 3)] == _BAND + 3 * WIRING_GRID
    assert lifted[hid("function", 1)] == flush[hid("function", 1)] + 24


def test_headroom_moves_every_cell_by_the_same_amount_and_no_cell_sideways() -> None:
    """Only y changes, and by the headroom: rows keep their gaps, columns their x."""
    flush, _ = _two_columns()
    lifted, _ = _two_columns(headroom_lanes=2)
    for before, after in zip(flush, lifted, strict=True):
        assert after.function == before.function
        assert after.at.x == before.at.x
        assert after.at.y == before.at.y + 2 * WIRING_GRID


def test_equal_bands_still_share_a_top_below_the_headroom() -> None:
    """Band alignment works from the lifted rows: the two first cells of one band line up."""
    placed, _ = _two_columns(headroom_lanes=2)
    by = {one.function: one for one in placed}
    assert _keepout(by[hid("function", 2)]).y == _keepout(by[hid("function", 4)]).y
    assert _keepout(by[hid("function", 2)]).y > _keepout(by[hid("function", 1)]).y


# M11: the least height two 32 G cells need: both bands and `row_gap` between the cells.
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
    """M4 + M11: on the least height two cells need, cell 1 spans 48..80 and cell 2, narrowed to
    `row_gap`, 112..144, which ends on the floor (the content height less the bottom band) and
    fits. One lane pushes cell 2 to 120..152, past the floor, and spacing cannot narrow further.
    """
    placed, findings = _two_cells(0)
    assert findings == ()
    assert _keepout({one.function: one for one in placed}[hid("function", 2)]).y == 112
    _, findings = _two_cells(1)
    assert [f.code for f in findings] == [PAGE_OVERFULL]
    assert findings[0].subjects == (hid("function", 2),)
