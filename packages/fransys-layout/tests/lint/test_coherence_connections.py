"""`lint.coherence`: is every conductor and net group drawn exactly once.

A conductor is drawn by one route on the pages holding both its ends (one route in all, on any
one of them), or, when no page does, cut by one decision. A net group is drawn by routes that
join its ports on each page (an edge drawn on another page joins two ports both placed here) and
cut by one decision per pair of consecutive pages. Every case has a twin that must stay silent.
"""

import dataclasses

import pytest
from coherence_helpers import (
    DRAWN,
    NO_UNITS,
    decision,
    edge,
    group,
    layout_of,
    named,
    port,
    subjects,
)
from samples import connection, drawn, hid, placed

from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
)
from fransys_layout.stages import LinkCase

GOOD = ((104, 112), (104, 288))
C1 = connection(1, 1, 2)
CONDUCTOR = hid("conductor", 1)
ECHO = LinkCase.TERMINAL_ECHO
SPLIT = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2))


def _check(*, routes=(), decisions=(), functions=SPLIT, connections=(C1,), groups=()):
    layout = layout_of(routes=routes, decisions=decisions, functions=functions)
    return named(check_coherence(layout, connections, groups, DRAWN, function_units=NO_UNITS))


ON_ONE_PAGE = (placed(1, x=104, y=96), placed(2, x=104, y=304))


def test_an_undrawn_conductor_is_called_a_conductor() -> None:
    """A conductor's finding says "conductor"; a net group's finding keeps the word "connection".

    # UNDO: lint/coherence.py, the conductor text back to "a connection"
    """
    layout = layout_of(functions=SPLIT)
    (plain,) = check_coherence(layout, (C1,), (), DRAWN, function_units=NO_UNITS)
    assert plain.message == "a conductor is neither drawn nor cut"
    assert plain.subjects == (CONDUCTOR,)
    net = group(7, ((1, 12), (2, 21)))
    (grouped,) = check_coherence(
        layout_of(functions=SPLIT), (), (net,), DRAWN, function_units=NO_UNITS
    )
    assert grouped.message == "a connection is neither drawn nor cut"


BOTH_PAGES = (
    placed(1, x=104, y=96, page=1),
    placed(1, x=104, y=96, page=2),
    placed(2, x=104, y=304, page=1),
    placed(2, x=104, y=304, page=2),
)


@pytest.mark.parametrize("functions", [(SPLIT[0],), (SPLIT[1],), ()])
def test_a_conductor_with_an_end_placed_nowhere_needs_a_decision(functions) -> None:
    """Nothing is drawn, so nothing can be shared: the decision is all there is to find."""
    assert _check(functions=functions) == [(CONNECTION_NOT_DRAWN, (CONDUCTOR,))]
    assert _check(decisions=(decision(CONDUCTOR, 12, 21, ECHO),), functions=functions) == []


# --- net groups -----------------------------------------------------------------------

NET = hid("net", 7)
THREE = group(7, ((1, 12), (2, 21), (3, 32)))
E12_21 = edge(7, 12, 21, ((104, 112), (104, 288)))
E21_32 = edge(7, 21, 32, ((104, 288), (304, 288), (304, 320)))
E12_32 = edge(7, 12, 32, ((104, 112), (104, 320), (304, 320)))
ON_A_PAGE = (placed(1, x=104, y=96), placed(2, x=104, y=304), placed(3, x=304, y=304, name="b"))


def _net(*routes, decisions=(), functions=ON_A_PAGE, net=THREE):
    return _check(
        routes=routes, decisions=decisions, functions=functions, connections=(), groups=(net,)
    )


FOUR = group(7, ((1, 12), (2, 21), (3, 32), (4, 41)))
TWO_PAGES = (
    placed(1, x=104, y=96, page=1),
    placed(2, x=104, y=304, page=1),
    placed(3, x=304, y=96, page=2, name="b"),
    placed(4, x=304, y=304, page=2, name="b"),
)
PAGE_1 = edge(7, 12, 21, ((104, 112), (104, 288)))
PAGE_2 = edge(7, 32, 41, ((304, 112), (304, 288)), page=2)
CUT = decision(NET, 12, 32, ECHO)  # port 12 is the lowest on page 1, port 32 on page 2


def _two_pages(*routes, decisions=()):
    layout = layout_of(routes=routes, decisions=decisions, functions=TWO_PAGES)
    return named(check_coherence(layout, (), (FOUR,), (*DRAWN, drawn(4)), function_units=NO_UNITS))


THREE_PAGES = (
    placed(1, x=104, y=96, page=1),
    placed(1, x=104, y=96, page=2),
    placed(1, x=104, y=96, page=3),
)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, [(CONNECTION_NOT_DRAWN, (NET,))]),
        (1, [(CONNECTION_NOT_DRAWN, (NET,))]),
        (2, []),
        (3, [(CONNECTION_DRAWN_TWICE, subjects(NET, port(12)))]),
    ],
)
def test_a_terminal_on_three_pages_has_two_cuts_of_one_identity(count, expected) -> None:
    """Port 12 is the lowest on every page, so both cuts are `(net, 12, 12)`."""
    terminal = group(7, ((1, 12),))
    cuts = tuple(decision(NET, 12, 12, ECHO) for _ in range(count))
    assert _net(decisions=cuts, functions=THREE_PAGES, net=terminal) == expected


def _drawing_set(number: int, *, x: int):
    """Functions 1 and 2 on page 1 of drawing set `number`, `x` G from the left."""
    return tuple(
        dataclasses.replace(placed(n, x=x, y=y), drawing_set=number) for n, y in ((1, 96), (2, 304))
    )


IN_TWO_DRAWING_SETS = (*_drawing_set(1, x=104), *_drawing_set(2, x=204))
DRAWING_SET_2 = ((204, 112), (204, 288))


def _in_drawing_set_2(route):
    return dataclasses.replace(route, drawing_set=2)
