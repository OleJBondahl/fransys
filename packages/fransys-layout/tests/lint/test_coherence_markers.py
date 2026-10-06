"""`lint.coherence`: does a severed cut have its marker pair, and every marker its cut (lint.md
6.8).

The expected pair is the one `links` places: owner at the end on the earlier page, user at the
other, each at its port's position. Every case has a twin that must stay silent.
"""

import dataclasses

import pytest
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
from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN, MARKER_UNPAIRED
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


def test_an_owner_and_a_user_marker_pair_a_severed_cut() -> None:
    """An owner and a user marker pair a severed cut."""
    assert _check((M_OWNER, M_USER)) == []


@pytest.mark.parametrize(
    ("markers", "missing"),
    [((M_USER,), 1), ((M_OWNER,), 1), ((), 2)],
    ids=["no owner", "no user", "none"],
)
def test_each_missing_marker_of_a_severed_cut_is_unpaired(markers, missing) -> None:
    """Each missing marker of a severed cut is unpaired."""
    assert _check(markers) == _unpaired(*[CUT_ID] * missing)


def test_a_marker_that_is_there_twice_is_unpaired_once() -> None:
    """A marker that is there twice is unpaired once."""
    assert _check((M_OWNER, M_USER, M_OWNER)) == _unpaired(CUT_ID)


@pytest.mark.parametrize(
    ("wrong", "stray"),
    [
        (dataclasses.replace(M_USER, page=3), subjects(C1, port(21))),
        (dataclasses.replace(M_USER, drawing_set=2), subjects(C1, port(21))),
        (marker(C1, 21, USER, page=2, at=(104, 290)), subjects(C1, port(21))),
        (marker(C1, 21, USER, page=2, at=(112, 288)), subjects(C1, port(21))),
        (marker(C1, 21, OWNER, page=2, at=(104, 288)), subjects(C1, port(21))),
        (marker(C1, 12, USER, page=2, at=(104, 288)), subjects(C1, port(12))),
        (
            marker(hid("conductor", 9), 21, USER, page=2, at=(104, 288)),
            subjects(hid("conductor", 9), port(21)),
        ),
    ],
    ids=["page", "drawing_set", "y", "x", "side", "port", "connection"],
)
def test_a_marker_that_differs_from_the_expected_one_is_missing_and_stray(wrong, stray) -> None:
    """A marker that differs from the expected one is missing and stray."""
    assert _check((M_OWNER, wrong)) == sorted(_unpaired(CUT_ID, stray))


def test_a_marker_needs_no_partner_text_to_be_expected() -> None:
    """`partner_page` is text, not connectivity."""
    texted = dataclasses.replace(M_USER, partner_page=9)
    assert _check((M_OWNER, texted)) == []


@pytest.mark.parametrize("case", [LinkCase.TERMINAL_ECHO, LinkCase.TAG_ECHO])
def test_markers_beside_an_echo_have_no_cut_to_belong_to(case) -> None:
    """Markers beside an echo have no cut to belong to."""
    echo = decision(C1, 12, 21, case)
    assert _check((M_OWNER, M_USER), decisions=(echo,)) == _unpaired(
        subjects(C1, port(12)), subjects(C1, port(21))
    )
    assert _check((), decisions=(echo,)) == []


def test_markers_with_no_decision_at_all_are_stray() -> None:
    """Markers with no decision at all are stray."""
    found = _check((M_OWNER, M_USER), decisions=())
    assert found == [
        (CONNECTION_NOT_DRAWN, (C1,)),
        *_unpaired(subjects(C1, port(12)), subjects(C1, port(21))),
    ]


def test_the_owner_is_on_the_earlier_page_whichever_end_is_a() -> None:
    """Function 1 (port 12) is drawn on page 2 and function 2 (port 21) on page 1."""
    functions = (placed(1, x=104, y=96, page=2), placed(2, x=104, y=304, page=1))
    owner = marker(C1, 21, OWNER, page=1, at=(104, 288))
    user = marker(C1, 12, USER, page=2, at=(104, 112))
    assert _check((owner, user), functions=functions) == []
    swapped = (
        marker(C1, 21, USER, page=1, at=(104, 288)),
        marker(C1, 12, OWNER, page=2, at=(104, 112)),
    )
    assert _check(swapped, functions=functions) == sorted(
        _unpaired(CUT_ID, CUT_ID, subjects(C1, port(12)), subjects(C1, port(21)))
    )


def test_pages_are_ordered_by_drawing_set_first() -> None:
    """Function 2 is on page 1 of drawing set 2, which comes after page 1 of drawing set 1."""
    functions = (
        placed(1, x=104, y=96, page=1),
        dataclasses.replace(placed(2, x=104, y=304), drawing_set=2),
    )
    user = dataclasses.replace(marker(C1, 21, USER, page=1, at=(104, 288)), drawing_set=2)
    assert _check((M_OWNER, user), functions=functions) == []
    assert _check(
        (M_OWNER, dataclasses.replace(user, drawing_set=1)), functions=functions
    ) == sorted(_unpaired(CUT_ID, subjects(C1, port(21))))


def test_the_cut_stands_at_the_earliest_page_of_a_terminal() -> None:
    """Function 2 is drawn on pages 2 and 3; the user marker belongs on page 2."""
    functions = (*SPLIT, placed(2, x=104, y=304, page=3))
    assert _check((M_OWNER, M_USER), functions=functions) == []
    late = marker(C1, 21, USER, page=3, at=(104, 288))
    assert _check((M_OWNER, late), functions=functions) == sorted(
        _unpaired(CUT_ID, subjects(C1, port(21)))
    )


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


def test_a_middle_page_of_a_net_group_holds_a_user_and_an_owner_marker_at_one_port() -> None:
    """A middle page of a net group holds a user and an owner marker at one port."""
    assert _chain((FIRST_OWNER, MIDDLE_USER, MIDDLE_OWNER, LAST_USER)) == []
    assert _chain((FIRST_OWNER, MIDDLE_USER, LAST_USER)) == _unpaired(
        subjects(N7, port(21), port(32))
    )
    assert _chain((FIRST_OWNER, MIDDLE_OWNER, LAST_USER)) == _unpaired(
        subjects(N7, port(12), port(21))
    )


def test_the_cut_stands_at_the_earliest_page_however_the_placements_are_listed() -> None:
    """Function 1 is drawn on pages 3 and 2, listed in that order; function 2 on page 1."""
    functions = (
        placed(1, x=104, y=96, page=3),
        placed(1, x=104, y=96, page=2),
        placed(2, x=104, y=304, page=1),
    )
    owner = marker(C1, 21, OWNER, page=1, at=(104, 288))
    user = marker(C1, 12, USER, page=2, at=(104, 112))
    assert _check((owner, user), functions=functions) == []
    late = marker(C1, 12, USER, page=3, at=(104, 112))
    assert _check((owner, late), functions=functions) == sorted(
        _unpaired(CUT_ID, subjects(C1, port(12)))
    )


def test_a_net_groups_cut_names_its_ports_in_handle_order_not_page_order() -> None:
    """Port 32 is on page 1 and port 12 on page 2: the cut is `(net, 12, 32)`, owner at port 32."""
    functions = (placed(3, x=304, y=304, page=1, name="b"), placed(1, x=104, y=96, page=2))
    cut = decision(N7, 12, 32, LinkCase.SEVERED)
    owner = marker(N7, 32, OWNER, page=1, at=(304, 320))
    user = marker(N7, 12, USER, page=2, at=(104, 112))
    layout = layout_of(decisions=(cut,), markers=(owner, user), functions=functions)
    net = group(7, ((1, 12), (3, 32)))
    assert named(check_coherence(layout, (), (net,), DRAWN, function_units=NO_UNITS)) == []
    backwards = decision(N7, 32, 12, LinkCase.SEVERED)
    layout = layout_of(decisions=(backwards,), markers=(owner, user), functions=functions)
    assert named(check_coherence(layout, (), (net,), DRAWN, function_units=NO_UNITS)) == [
        (CONNECTION_NOT_DRAWN, (N7,)),
        *_unpaired(subjects(N7, port(12)), subjects(N7, port(32))),
    ]


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


def test_a_units_cut_stands_at_its_own_pages_not_at_a_boundary_functions_replica() -> None:
    """Both ends belong to `U`: the pair stands at set 2, not at the earlier replica pages."""
    # UNDO: pass `function_units={}` in `_markers`, or take `pages_a[0]`/`pages_b[0]` in
    # `conductor_cut` again: the pair is expected at the replicas and this fails
    assert _in_unit(AT_HOME) == []


def test_markers_at_the_replica_pages_of_boundary_functions_are_unpaired() -> None:
    """The earliest pages are the replicas in set 1: markers there are not the expected pair."""
    # UNDO: pass `function_units={}` in `_markers`: the cut moves to the replicas, this fails
    assert _in_unit((M_OWNER, M_USER)) == sorted(
        _unpaired(CUT_ID, CUT_ID, subjects(C1, port(12)), subjects(C1, port(21)))
    )


def test_a_model_with_no_unit_cuts_at_the_earliest_pages() -> None:
    """The twin: without the ends' units the replica pages of set 1 hold the cut, as before."""
    # UNDO: in `conductor_cut` take each end's unit from its last page's set instead of from
    # `function_units`: the ends then look like `U`'s and the first assertion fails
    assert _in_unit((M_OWNER, M_USER), function_units=NO_UNITS) == []
    assert _in_unit(AT_HOME, function_units=NO_UNITS) == sorted(
        _unpaired(CUT_ID, CUT_ID, subjects(C1, port(12)), subjects(C1, port(21)))
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
    """T7.1: a cut between two units' sets has no markers to miss; the same cut in one unit has."""
    # UNDO: drop the unit condition in `_markers` (coherence.py): the cross-unit cut is expected
    # to have markers and the first assertion fails
    assert _across_sets(UNIT, hid("unit", 2)) == []
    assert _across_sets(UNIT, UNIT) == _unpaired(CUT_ID, CUT_ID)
