"""S20 M11: a column taller than the page at the house spacing narrows its spacing to fit.

Seven 32 G cells in one column, `PROFILE.row_spacing` 104 G, `row_gap` 32 G. At the house spacing
the column ends at 864 G, past the floor of a content box 879 G high; M11 narrows its spacing,
evenly, to the one that fits. Only a column that does not fit even with the blocks at the row gap
is `PAGE_OVERFULL`.
"""

import dataclasses
from itertools import pairwise

import pytest
from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import WIRING_GRID, translate
from fransys_layout.stages import MarkerSide, place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import PAGE_OVERFULL, _reference_band, page_stack
from fransys_layout.stages.references.marker_boxes import reference_size
from fransys_layout.stages.references.types import MarkerDecision
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun
from fransys_layout.stages.texts.stand import page_texts


def _seven(content_height):
    numbers = tuple(range(1, 8))
    return place(
        page_plan(("a",)),
        (column("a", numbers),),
        tuple(drawn(n) for n in numbers),
        PageStacking(
            profile=PROFILE, sheet=dataclasses.replace(SHEET, content_height=content_height)
        ),
    )


def _keepouts(placed):
    boxes = [translate(p.geometry.keepout, dx=p.at.x, dy=p.at.y) for p in placed]
    return sorted(boxes, key=lambda box: box.y)


def _gaps(placed):
    return [b.y - (a.y + a.height) for a, b in pairwise(_keepouts(placed))]


def test_a_column_taller_than_its_page_narrows_its_spacing_evenly_and_ends_inside() -> None:
    """At 879 G the seven blocks stand closer than 104 G, all alike, and the foot is inside."""
    # UNDO: stages/place.py `_narrowed`: return `narrowed` unchanged (the house spacing stays);
    #   the page ends at 864 G, past the floor, and reports PAGE_OVERFULL
    placed, findings = _seven(879)
    gaps = _gaps(placed)
    assert findings == ()
    assert len(gaps) == 6
    assert all(PROFILE.row_gap <= gap < PROFILE.row_spacing for gap in gaps), gaps
    assert max(gaps) - min(gaps) < WIRING_GRID, gaps  # evenly: the grid is the only difference
    assert _keepouts(placed)[-1].y + _keepouts(placed)[-1].height < 879


def _reference(port: int) -> MarkerDecision:
    """A one-line star reference at port `port` (of function `port // 10`), as `test_stack_room`."""
    return MarkerDecision(
        connection=hid("conductor", port),
        function=hid("function", port // 10),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        star="ref",
        lines=1,
        size=reference_size(SHEET, PROFILE, lines=1),
        partner=hid("port", 91),
        partner_set=1,
        partner_page=2,
        out=0,
    )


def test_a_narrowing_column_keeps_the_room_of_its_stacked_pair() -> None:
    """The floor is per gap (ADDENDUM 18 (b)): the pair holding a reference stays a band apart.

    A reference at port 12 asks M9 for a band between ports 12 and 21. At 560 G the column
    narrows hard: every other gap goes under the band, the pair's gap does not.
    """
    # UNDO: stages/place.py `_stack_page`: `make_room(..., gaps_of=_gaps_of(profile, {}), ...)`
    #   (M9's room made at the house gaps, not the narrowed ones): the pair is squeezed
    sheet = dataclasses.replace(SHEET, content_height=560)
    plan, numbers = page_plan(("a",)), tuple(range(1, 8))
    reserved = page_texts((_reference(12),), frozenset(), sheet=sheet, profile=PROFILE)[1, 1]
    stack = page_stack(
        plan,
        (column("a", numbers),),
        tuple(drawn(n) for n in numbers),
        PageStacking(profile=PROFILE, sheet=sheet, texts=reserved),
    )
    key = plan.columns[0].column
    offsets = [stack.ports[key, hid("port", 10 * n + 1)].offset for n in numbers]
    gaps = [b - a - 32 for a, b in pairwise(offsets)]  # a cell's keep-out is 32 G high
    band = _reference_band(sheet, PROFILE)
    assert gaps[0] >= band, gaps  # the pair of ports 12 and 21 keeps its room
    assert all(gap < band for gap in gaps[1:]), gaps  # premise: the column did narrow
    assert offsets[-1] + 32 <= stack.room, (offsets, stack.room)


@pytest.mark.parametrize("height", [880, 800, 720])
def test_a_join_that_lowers_a_column_is_counted_by_the_fit(height: int) -> None:
    """ADDENDUM 18 (c): a join adds height, so the fit counts it and narrows the joined columns.

    Column `a` has 5 cells, `b` has 7. The run of `a`'s fifth cell and `b`'s third cell stands at
    the deeper of the two, which lowers `b`. The fit counts that: the joined columns narrow
    together, both end inside and the run stands on one y.
    """
    # UNDO: stages/place.py `_stacked`: `_align_joins` after the loop, not before `_narrowed`
    #   (the fit does not count the join); or `runs = []` (the joined columns narrow alone):
    #   `b` ends below the floor and the page reports PAGE_OVERFULL
    a, b = ("invented", "a"), ("invented", "b")
    ends = (JoinedEnd(column=a, port=hid("port", 51)), JoinedEnd(column=b, port=hid("port", 81)))
    run = JoinedRun(drawing_set=1, page=1, ends=ends)
    placed, findings = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3, 4, 5)), column("b", (6, 7, 8, 9, 10, 11, 12))),
        tuple(drawn(n) for n in range(1, 13)),
        PageStacking(profile=PROFILE, sheet=dataclasses.replace(SHEET, content_height=height)),
        joins=(run,),
    )
    at = {p.function: p.at.y for p in placed}
    assert at[hid("function", 5)] == at[hid("function", 8)]
    assert findings == ()


def test_a_column_that_fits_at_the_house_spacing_keeps_it() -> None:
    """On a tall page the house spacing stands: only the column that would end below narrows."""
    placed, findings = _seven(1200)
    assert findings == ()
    assert all(gap == PROFILE.row_spacing for gap in _gaps(placed)), _gaps(placed)


def test_a_column_too_tall_at_the_row_gap_is_still_overfull() -> None:
    """Below the least spacing the column cannot fit: its blocks stand at the row gap and report."""
    placed, findings = _seven(400)
    assert [f.code for f in findings] == [PAGE_OVERFULL]
    assert all(gap == PROFILE.row_gap for gap in _gaps(placed)), _gaps(placed)
