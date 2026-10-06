"""`lint.coherence`: is every conductor and net group drawn exactly once (docs/design/lint.md 6.8).

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
    wire,
)
from samples import connection, drawn, hid, placed

from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    ROUTE_WRONG_PORT,
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


@pytest.mark.parametrize("case", list(LinkCase))
def test_a_decision_beside_a_route_on_a_shared_page_is_surplus(case) -> None:
    """A decision beside a route on a shared page is surplus."""
    both = _check(
        routes=(wire(1, GOOD),),
        decisions=(decision(CONDUCTOR, 12, 21, case),),
        functions=ON_ONE_PAGE,
    )
    assert both == [(CONNECTION_DRAWN_TWICE, (CONDUCTOR,))]
    assert _check(routes=(wire(1, GOOD),), functions=ON_ONE_PAGE) == []


def test_a_decision_does_not_draw_a_conductor_whose_ends_share_a_page() -> None:
    """A decision does not draw a conductor whose ends share a page."""
    found = _check(decisions=(decision(CONDUCTOR, 12, 21, ECHO),), functions=ON_ONE_PAGE)
    assert found == [
        (CONNECTION_DRAWN_TWICE, (CONDUCTOR,)),
        (CONNECTION_NOT_DRAWN, (CONDUCTOR,)),
    ]


def test_a_cut_conductor_needs_exactly_one_decision() -> None:
    """A cut conductor needs exactly one decision."""
    one = decision(CONDUCTOR, 12, 21, ECHO)
    assert _check(decisions=(one,)) == []
    assert _check() == [(CONNECTION_NOT_DRAWN, (CONDUCTOR,))]
    assert _check(decisions=(one, one)) == [(CONNECTION_DRAWN_TWICE, (CONDUCTOR,))]


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


def test_a_decision_with_another_identity_covers_nothing() -> None:
    """The decision names the ports the other way round, so it is not this conductor's."""
    assert _check(decisions=(decision(CONDUCTOR, 21, 12, ECHO),)) == [
        (CONNECTION_NOT_DRAWN, (CONDUCTOR,))
    ]


def test_a_route_beside_the_decision_of_a_cut_is_surplus_and_wrong() -> None:
    """A route claims the conductor on page 1, where port 21 is not drawn."""
    found = _check(routes=(wire(1, GOOD),), decisions=(decision(CONDUCTOR, 12, 21, ECHO),))
    assert found == [
        (CONNECTION_DRAWN_TWICE, (CONDUCTOR,)),
        (ROUTE_WRONG_PORT, subjects(CONDUCTOR, port(12), port(21))),
    ]


BOTH_PAGES = (
    placed(1, x=104, y=96, page=1),
    placed(1, x=104, y=96, page=2),
    placed(2, x=104, y=304, page=1),
    placed(2, x=104, y=304, page=2),
)


@pytest.mark.parametrize(
    ("pages", "expected"),
    [
        ((1,), []),
        ((2,), []),
        ((1, 2), [CONNECTION_DRAWN_TWICE]),
        ((1, 2, 2), [CONNECTION_DRAWN_TWICE]),
        ((1, 1), [CONNECTION_DRAWN_TWICE]),
        ((), [CONNECTION_NOT_DRAWN]),
    ],
)
def test_a_conductor_between_two_terminals_needs_one_route_on_the_pages_they_share(
    pages, expected
) -> None:
    """A conductor whose ends share two pages is drawn on one of them, not on both (layout-0030)."""
    routes = tuple(wire(1, GOOD, page=page) for page in pages)
    assert _check(routes=routes, functions=BOTH_PAGES) == [
        (code, (CONDUCTOR,)) for code in expected
    ]


def test_only_the_pages_holding_both_ends_need_a_route() -> None:
    """Function 1 is drawn on pages 1 and 2, function 2 on page 1 only."""
    functions = (BOTH_PAGES[0], BOTH_PAGES[1], BOTH_PAGES[2])
    assert _check(routes=(wire(1, GOOD, page=1),), functions=functions) == []
    assert _check(routes=(wire(1, GOOD, page=1), wire(1, GOOD, page=2)), functions=functions) == [
        (CONNECTION_DRAWN_TWICE, (CONDUCTOR,)),
        (ROUTE_WRONG_PORT, subjects(CONDUCTOR, port(12), port(21))),
    ]


@pytest.mark.parametrize("functions", [(SPLIT[0],), (SPLIT[1],), ()])
def test_a_conductor_with_an_end_placed_nowhere_needs_a_decision(functions) -> None:
    """Nothing is drawn, so nothing can be shared: the decision is all there is to find."""
    assert _check(functions=functions) == [(CONNECTION_NOT_DRAWN, (CONDUCTOR,))]
    assert _check(decisions=(decision(CONDUCTOR, 12, 21, ECHO),), functions=functions) == []


def test_a_decision_for_a_conductor_nobody_gave_is_ignored() -> None:
    """A decision for a conductor nobody gave is ignored."""
    stray = decision(hid("conductor", 99), 12, 21, ECHO)
    assert _check(routes=(wire(1, GOOD),), decisions=(stray,), functions=ON_ONE_PAGE) == []


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


@pytest.mark.parametrize(
    ("edges", "expected"),
    [
        ((E12_21, E21_32), []),
        ((E12_32, E12_21), []),
        ((E12_21,), [(CONNECTION_NOT_DRAWN, (NET,))]),
        ((), [(CONNECTION_NOT_DRAWN, (NET,))]),
        ((E12_21, E21_32, E12_32), [(CONNECTION_DRAWN_TWICE, subjects(NET, port(21), port(32)))]),
        ((E12_32, E21_32, E12_21), [(CONNECTION_DRAWN_TWICE, subjects(NET, port(21), port(32)))]),
    ],
    ids=["chain", "star", "one piece missing", "no edge", "cycle", "cycle, edges reversed"],
)
def test_a_net_groups_ports_on_a_page_are_joined_into_one_tree(edges, expected) -> None:
    """A net groups ports on a page are joined into one tree."""
    assert _net(*edges) == expected


def test_an_edge_drawn_twice_is_surplus() -> None:
    """An edge drawn twice is surplus."""
    two = group(7, ((1, 12), (2, 21)))
    assert _net(E12_21, net=two) == []
    assert _net(E12_21, E12_21, net=two) == [
        (CONNECTION_DRAWN_TWICE, subjects(NET, port(12), port(21)))
    ]


def test_a_single_port_on_a_page_needs_no_edge() -> None:
    """A single port on a page needs no edge."""
    two = group(7, ((1, 12), (3, 32)))
    assert _net(functions=ON_A_PAGE[:2], net=two) == []
    assert _net(functions=ON_A_PAGE, net=two) == [(CONNECTION_NOT_DRAWN, (NET,))]


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


def test_a_net_group_failing_on_two_pages_is_one_finding() -> None:
    """A net group failing on two pages is one finding."""
    assert _two_pages(PAGE_1, PAGE_2, decisions=(CUT,)) == []
    assert _two_pages(PAGE_1, decisions=(CUT,)) == [(CONNECTION_NOT_DRAWN, (NET,))]
    assert _two_pages(PAGE_2, decisions=(CUT,)) == [(CONNECTION_NOT_DRAWN, (NET,))]
    assert _two_pages(decisions=(CUT,)) == [(CONNECTION_NOT_DRAWN, (NET,))]


def test_each_cut_of_a_net_group_needs_one_decision_at_its_lowest_ports() -> None:
    """Each cut of a net group needs one decision at its lowest ports."""
    routes = (PAGE_1, PAGE_2)
    assert _two_pages(*routes) == [(CONNECTION_NOT_DRAWN, (NET,))]
    assert _two_pages(*routes, decisions=(CUT, CUT)) == [
        (CONNECTION_DRAWN_TWICE, subjects(NET, port(12), port(32)))
    ]


def test_a_decision_at_other_ports_than_the_cuts_covers_nothing() -> None:
    """Ports 21 and 41 are on the two pages but are not the lowest on either."""
    routes = (PAGE_1, PAGE_2)
    other = decision(NET, 21, 41, ECHO)
    assert _two_pages(*routes, decisions=(other,)) == [(CONNECTION_NOT_DRAWN, (NET,))]
    assert _two_pages(*routes, decisions=(CUT, other)) == []


def test_a_decision_for_a_group_drawn_on_one_page_is_ignored() -> None:
    """A decision for a group drawn on one page is ignored."""
    two = group(7, ((1, 12), (2, 21)))
    assert _net(E12_21, decisions=(decision(NET, 12, 21, ECHO),), net=two) == []


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


@pytest.mark.parametrize(
    ("routes", "expected"),
    [
        ((wire(1, GOOD), _in_drawing_set_2(wire(1, DRAWING_SET_2))), [CONNECTION_DRAWN_TWICE]),
        ((wire(1, GOOD),), []),
        ((_in_drawing_set_2(wire(1, DRAWING_SET_2)),), []),
        (
            (wire(1, GOOD), _in_drawing_set_2(wire(1, DRAWING_SET_2)), wire(1, GOOD)),
            [CONNECTION_DRAWN_TWICE],
        ),
        ((), [CONNECTION_NOT_DRAWN]),
    ],
    ids=["both", "drawing set 1 only", "drawing set 2 only", "drawing set 1 twice", "none"],
)
def test_page_1_of_two_drawing_sets_are_two_pages(routes, expected) -> None:
    """A conductor on page 1 of each drawing set is drawn on one of the two, not on both."""
    assert _check(routes=routes, functions=IN_TWO_DRAWING_SETS) == [
        (code, (CONDUCTOR,)) for code in expected
    ]


def test_a_route_is_judged_against_the_placement_of_its_own_drawing_set() -> None:
    """The drawing set 2 route uses the drawing set 1 coordinates, which are not its ports."""
    routes = (_in_drawing_set_2(wire(1, GOOD)),)
    assert _check(routes=routes, functions=IN_TWO_DRAWING_SETS) == [
        (ROUTE_WRONG_PORT, subjects(CONDUCTOR, port(12), port(21)))
    ]


def test_a_net_group_edge_is_drawn_on_one_of_the_pages_across_drawing_sets() -> None:
    """Page 1 of drawing set 2 is not page 1 of drawing set 1: two pages, one edge (layout-0030)."""
    two = group(7, ((1, 12), (2, 21)))
    cut = decision(NET, 12, 12, ECHO)  # ports 12 and 21 are on both pages: the lowest is 12
    first = edge(7, 12, 21, GOOD)
    second = _in_drawing_set_2(edge(7, 12, 21, DRAWING_SET_2))

    def found(*routes):
        return _net(*routes, decisions=(cut,), functions=IN_TWO_DRAWING_SETS, net=two)

    surplus = [(CONNECTION_DRAWN_TWICE, subjects(NET, port(12), port(21)))]
    assert found(first) == []
    assert found(second) == []
    assert found() == [(CONNECTION_NOT_DRAWN, (NET,))]
    assert found(first, second) == surplus
    assert found(first, second, second) == surplus


def test_an_edge_drawn_on_another_page_joins_two_ports_placed_on_this_one() -> None:
    """A tree of three ports: the edge drawn on page 2 joins 12 and 21, which page 1 also holds."""
    three = group(7, ((1, 12), (2, 21), (3, 32)))
    cut = decision(NET, 12, 12, ECHO)
    on_page_2 = edge(7, 12, 21, GOOD, page=2)
    rest = edge(7, 21, 32, ((104, 288), (304, 288), (304, 320)))
    functions = (*ON_A_PAGE, placed(1, x=104, y=96, page=2), placed(2, x=104, y=304, page=2))
    assert _net(on_page_2, rest, decisions=(cut,), functions=functions, net=three) == []
    assert _net(rest, decisions=(cut,), functions=functions, net=three) == [
        (CONNECTION_NOT_DRAWN, (NET,))
    ]
