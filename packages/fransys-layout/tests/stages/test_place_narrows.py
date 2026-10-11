"""A column taller than the page at the house spacing narrows its spacing to fit.

Seven 32 G cells in one column, `PROFILE.row_spacing` 104 G, `row_gap` 32 G. At the house spacing
the column ends at 864 G, past the floor of a content box 879 G high; it narrows its spacing,
evenly, to the one that fits. Only a column that does not fit even with the blocks at the row gap
is `PAGE_OVERFULL`.
"""

import dataclasses
from itertools import pairwise

import pytest
from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import translate
from fransys_layout.stages import MarkerSide, place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.references.marker_boxes import reference_size
from fransys_layout.stages.references.types import MarkerDecision
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun


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
