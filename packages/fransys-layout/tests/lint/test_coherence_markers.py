"""`lint.coherence`: does a severed cut have its marker pair, and every marker its cut (lint.md
6.8).

The expected pair is the one `links` places: owner at the end on the earlier page, user at the
other, each at its port's position. Every case has a twin that must stay silent.
"""

import dataclasses

from coherence_helpers import (
    DRAWN,
    NO_UNITS,
    decision,
    group,
    layout_of,
    marker,
    named,
    port,
    subjects,
)
from samples import connection, hid, page_plan, placed

from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import MARKER_UNPAIRED
from fransys_layout.stages import LinkCase, MarkerSide

OWNER, USER = MarkerSide.OWNER, MarkerSide.USER
C1 = hid("conductor", 1)
CUT_ID = subjects(C1, port(12), port(21))
SEVERED = decision(C1, 12, 21, LinkCase.SEVERED)
SPLIT = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2))
M_OWNER = marker(C1, 12, OWNER, page=1, at=(104, 112))
M_USER = marker(C1, 21, USER, page=2, at=(104, 288))


def _check(markers, *, decisions=(SEVERED,), functions=SPLIT):
    layout = layout_of(decisions=decisions, markers=markers, functions=functions)
    return named(
        check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS)
    )


def _unpaired(*ids):
    return [(MARKER_UNPAIRED, one) for one in ids]


N7 = hid("net", 7)
THREE_PAGES = (
    placed(1, x=104, y=96, page=1),
    placed(2, x=104, y=304, page=2),
    placed(3, x=304, y=304, page=3, name="b"),
)
CHAIN = (decision(N7, 12, 21, LinkCase.SEVERED), decision(N7, 21, 32, LinkCase.SEVERED))
FIRST_OWNER = marker(N7, 12, OWNER, page=1, at=(104, 112))
MIDDLE_USER = marker(N7, 21, USER, page=2, at=(104, 288))
MIDDLE_OWNER = marker(N7, 21, OWNER, page=2, at=(104, 288))
LAST_USER = marker(N7, 32, USER, page=3, at=(304, 320))


def _chain(markers):
    layout = layout_of(decisions=CHAIN, markers=markers, functions=THREE_PAGES)
    net = group(7, ((1, 12), (2, 21), (3, 32)))
    return named(check_coherence(layout, (), (net,), DRAWN, function_units=NO_UNITS))


# One unit `U` with its own drawing set 2, and the top level's set 1. Both functions are boundary
# functions of `U`: at home on pages 1 and 2 of set 2 and, as the unit's black boxes, on pages 1
# and 2 of set 1. The cut belongs to the unit's drawing (decision layout-0078).
UNIT = hid("unit", 1)
UNIT_OF = {hid("function", 1): UNIT, hid("function", 2): UNIT}
UNIT_PAGES = (
    page_plan(("a", "b")),
    dataclasses.replace(page_plan(("a", "b")), drawing_set=2, unit=UNIT),
)
IN_UNIT = (
    placed(1, x=104, y=96, page=1),
    dataclasses.replace(placed(1, x=104, y=96, page=1), drawing_set=2),
    placed(2, x=104, y=304, page=2),
    dataclasses.replace(placed(2, x=104, y=304, page=2), drawing_set=2),
)
AT_HOME = (
    dataclasses.replace(M_OWNER, drawing_set=2),
    dataclasses.replace(M_USER, drawing_set=2),
)


def _in_unit(markers, *, function_units=UNIT_OF):
    layout = dataclasses.replace(
        layout_of(decisions=(SEVERED,), markers=markers, functions=IN_UNIT), pages=UNIT_PAGES
    )
    return named(
        check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=function_units)
    )


def _across_sets(unit_a, unit_b):
    """Function 1 on page 1 of set 2 (unit `unit_a`), function 2 on page 2 of set 3 (`unit_b`)."""
    pages = (
        dataclasses.replace(page_plan(("a",), number=1), drawing_set=2, unit=unit_a),
        dataclasses.replace(page_plan(("b",), number=2), drawing_set=3, unit=unit_b),
    )
    functions = (
        dataclasses.replace(placed(1, x=104, y=96, page=1), drawing_set=2),
        dataclasses.replace(placed(2, x=104, y=304, page=2), drawing_set=3),
    )
    layout = dataclasses.replace(
        layout_of(decisions=(SEVERED,), markers=(), functions=functions), pages=pages
    )
    return named(
        check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS)
    )


def test_an_unpaired_cut_between_two_units_is_silent_and_inside_one_unit_is_not() -> None:
    """A cut between two units' sets has no markers to miss; the same cut in one unit has."""
    # UNDO: drop the unit condition in `_markers` (coherence.py): the cross-unit cut is expected
    # to have markers and the first assertion fails
    assert _across_sets(UNIT, hid("unit", 2)) == []
    assert _across_sets(UNIT, UNIT) == _unpaired(CUT_ID, CUT_ID)
