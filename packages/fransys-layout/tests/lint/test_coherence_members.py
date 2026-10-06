"""`lint.members`: every placed member of a net has a route or a marker in its set (layout-0071).

A net is the ports its conductors join plus the ports of each net group. For a net of two or
more ports, each member port placed in a drawing set needs, on any page of that set, a route
ending at it or a marker naming it; a port that is the net's only member in its set is not
excused. Another set covers nothing. Decisions are not read. Every case has a twin that must
stay silent. All data is invented.

Function `n` has ports `10n + 1` and `10n + 2`; the net here is ports 12, 21 and 31 (and 42).
"""

import dataclasses

import pytest
from coherence_helpers import (
    DRAWN,
    decision,
    edge,
    group,
    layout_of,
    marker,
    named,
    port,
    subjects,
    wire,
)
from samples import connection, drawn, hid, placed

from fransys_layout.geometry import LayoutError
from fransys_layout.lint._ports import locate
from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN
from fransys_layout.lint.members import check_members
from fransys_layout.stages import LinkCase, MarkerSide
from fransys_model.kernel import Severity

GOOD = ((104, 112), (104, 288))
USER = MarkerSide.USER

# One physical net (net 1) of ports 12, 21 and 31: conductors 1 (12-21) and 2 (12-31).
C1 = connection(1, 1, 2)
C2 = dataclasses.replace(connection(2, 1, 3), physical_net=hid("net", 1))
CONDUCTORS = (C1, C2)
# Functions 1 and 2 on page 1; function 3, the third member, alone on page 2.
PUMP = (
    placed(1, x=104, y=96, page=1),
    placed(2, x=104, y=304, page=1),
    placed(3, x=304, y=304, page=2, name="b"),
)
# Where the third member's marker stands is not this check's business: only its port and page.
ON_PAGE_2 = marker(hid("conductor", 2), 31, USER, page=2, at=(304, 288))
# A bare member names the conductors that end at it: port 31 ends conductor 2. A net group has
# no conductor, so its bare member names the port alone.
NOT_DRAWN_31 = [(CONNECTION_NOT_DRAWN, subjects(port(31), hid("conductor", 2)))]
NOT_DRAWN_31_GROUP = [(CONNECTION_NOT_DRAWN, (port(31),))]


def _members(*, routes=(), markers=(), functions=PUMP, connections=CONDUCTORS, groups=()):
    layout = layout_of(routes=routes, markers=markers, functions=functions)
    return check_members(layout, connections, groups, (*DRAWN, drawn(4)))


def test_a_lone_member_on_a_page_with_no_route_or_marker_is_not_drawn() -> None:
    """The pump-1 shape: port 31 is alone on page 2, the other members are joined on page 1.

    # UNDO: lint/members.py, skip a member that is the only placed member of its net on its page
    """
    found = _members(routes=(wire(1, GOOD),))
    assert named(found) == NOT_DRAWN_31
    assert found[0].severity is Severity.ERROR


def test_the_finding_names_the_conductor_in_its_subjects_and_its_text() -> None:
    """Port 31 ends conductor 2: both are subjects, and the text says which thing is undrawn.

    A net group's member has no conductor: its finding keeps the port alone and the old text.

    # UNDO: lint/members.py, subjects `(port,)` again, or the message back to "a connection"
    """
    (found,) = _members(routes=(wire(1, GOOD),))
    assert hid("conductor", 2) in found.subjects
    assert port(31) in found.subjects
    assert found.message == "the conductor at this port is neither drawn nor cut in drawing set 1"
    (in_group,) = _members(routes=(edge(7, 12, 21, GOOD),), connections=(), groups=(NET,))
    assert in_group.subjects == (port(31),)
    assert in_group.message == "a connection is neither drawn nor cut in drawing set 1"


@pytest.mark.parametrize("star", ["", "ref", "branch"])
def test_a_marker_naming_the_port_on_its_page_covers_it(star) -> None:
    """A marker of any kind, star markers included, covers its port on its page.

    # UNDO: lint/members.py, drop the marker cover (or count only markers whose `star` is empty)
    """
    covering = dataclasses.replace(ON_PAGE_2, star=star)
    assert named(_members(routes=(wire(1, GOOD),), markers=(covering,))) == []


@pytest.mark.parametrize("end", ["a", "b"])
def test_a_route_ending_at_the_port_on_its_page_covers_it(end) -> None:
    """Port 31 is routed on page 2 to port 42 of function 4, at either end of the route.

    # UNDO: lint/members.py, check routes on page 1 only (or drop the route cover)
    """
    joined = dataclasses.replace(
        connection(3, 4, 3), physical_net=hid("net", 1)
    )  # a = port 42, b = port 31
    functions = (*PUMP, placed(4, x=304, y=96, page=2, name="b"))
    ends = {"a": (42, 31, ((304, 112), (304, 288))), "b": (31, 42, ((304, 288), (304, 112)))}
    a, b, points = ends[end]
    route = wire(3, points, a=a, b=b, page=2)
    found = _members(
        routes=(wire(1, GOOD), route), functions=functions, connections=(*CONDUCTORS, joined)
    )
    assert named(found) == []
    assert named(
        _members(routes=(wire(1, GOOD),), functions=functions, connections=(*CONDUCTORS, joined))
    ) == [
        (CONNECTION_NOT_DRAWN, subjects(port(31), hid("conductor", 2), hid("conductor", 3))),
        (CONNECTION_NOT_DRAWN, subjects(port(42), hid("conductor", 3))),
    ]


# One net group of ports 12, 21 and 31 (a declared net, no conductors); the edge joins 12-21.
NET = group(7, ((1, 12), (2, 21), (3, 31)))
NET_MARKER = marker(hid("net", 7), 31, USER, page=2, at=(304, 288))


def test_a_net_group_member_alone_on_a_page_needs_a_route_or_a_marker() -> None:
    """A net group's ports count as one net, joined; a lone member is found without a cover.

    # UNDO: lint/members.py, take only conductors into account (leave the net groups' ports out)
    """
    edges = (edge(7, 12, 21, GOOD),)
    assert named(_members(routes=edges, connections=(), groups=(NET,))) == NOT_DRAWN_31_GROUP
    assert named(_members(routes=edges, markers=(NET_MARKER,), connections=(), groups=(NET,))) == []


# Function 3 is also placed on page 1, where a marker or a route covers port 31.
ON_BOTH = (*PUMP, placed(3, x=304, y=304, page=1, name="b"))
ROUTE_31 = wire(2, ((104, 112), (104, 200), (304, 200), (304, 288)), a=12, b=31, page=1)
MARKER_31 = marker(hid("conductor", 2), 31, USER, page=1, at=(304, 288))


def test_a_marker_on_another_page_of_the_same_set_covers_the_port() -> None:
    """Port 31 has a marker on page 1 only: a star draws one branch per port per set (layout-0070).

    Its replica on page 2 of the set needs nothing more; the twin has no marker and is found.

    # UNDO: lint/members.py, judge a marker per page again (`(one.port, page)` instead of the set)
    """
    routes = (wire(1, GOOD),)
    assert named(_members(routes=routes, markers=(MARKER_31,), functions=ON_BOTH)) == []
    assert named(_members(routes=routes, functions=ON_BOTH)) == NOT_DRAWN_31


def test_a_route_on_another_page_of_the_same_set_covers_the_port() -> None:
    """Conductor 2 is drawn once, on page 1: port 31 is bare by design on page 2 of the set.

    # UNDO: lint/members.py, judge a route per page again (`(end, (set, page))` instead of the set)
    """
    routes = (wire(1, GOOD), ROUTE_31)
    assert named(_members(routes=routes, functions=ON_BOTH)) == []


@pytest.mark.parametrize("what", ["route", "marker"])
def test_a_route_or_marker_in_another_drawing_set_covers_nothing(what) -> None:
    """The same route or marker in set 2 covers nothing of set 1: port 31 is found, once.

    The pump station's shape: a wire in one set is no cover for the port's placement in another.

    # UNDO: lint/members.py, make the cover match the port alone, ignoring its drawing set
    """
    if what == "route":
        elsewhere = {"routes": (wire(1, GOOD), dataclasses.replace(ROUTE_31, drawing_set=2))}
    else:
        elsewhere = {
            "routes": (wire(1, GOOD),),
            "markers": (dataclasses.replace(MARKER_31, drawing_set=2),),
        }
    assert named(_members(functions=ON_BOTH, **elsewhere)) == NOT_DRAWN_31


def test_a_port_placed_in_two_sets_has_one_finding_per_set_that_names_it() -> None:
    """Port 31 is bare in set 1 (page 2) and in set 2: two findings, told apart by the message.

    # UNDO: lint/members.py, drop the set from the finding's message
    """
    in_set_2 = dataclasses.replace(placed(3, x=304, y=304, page=1, name="b"), drawing_set=2)
    found = _members(routes=(wire(1, GOOD),), functions=(*PUMP, in_set_2))
    assert named(found) == NOT_DRAWN_31 * 2
    assert len({one.message for one in found}) == 2
    assert [one.message[-1] for one in found] == ["1", "2"]


@pytest.mark.parametrize("case", list(LinkCase))
def test_a_decision_alone_does_not_cover_a_port(case) -> None:
    """Function 2 is not placed: port 12 is the one placed member of a two-port net.

    Port 21 is not placed and gives nothing; port 12 has a decision but no route or marker.

    # UNDO: lint/members.py, treat a `LinkDecision` of the connection as a cover
    """
    lone = (PUMP[0],)
    cover = decision(hid("conductor", 1), 12, 21, case)
    layout = layout_of(decisions=(cover,), functions=lone)
    found = check_members(layout, (C1,), (), DRAWN)
    assert named(found) == [(CONNECTION_NOT_DRAWN, subjects(port(12), hid("conductor", 1)))]


def test_a_net_of_one_port_gives_nothing() -> None:
    """A net group holding one port, placed and bare, is no net.

    # UNDO: lint/members.py, drop the "two or more ports" condition
    """
    alone = group(7, ((3, 31),))
    assert named(_members(connections=(), groups=(alone,))) == []


def test_ports_that_are_not_placed_give_nothing() -> None:
    """No function of the net is placed, so no port needs a route or a marker.

    # UNDO: lint/members.py, report a member of the net that is placed on no page
    """
    assert named(_members(functions=(), connections=(C1,))) == []


def test_findings_come_sorted_by_subjects_whatever_the_input_order() -> None:
    """Ports 42 and 11 are each alone on a page, on the net of conductor 1 (a = 42, b = 11).

    Conductor order is 42 then 11 and so is the placement order; the findings are 11, 42.

    # UNDO: lint/members.py, return the findings in the order the ports are visited (no sort)
    """
    across = dataclasses.replace(connection(1, 4, 1), physical_net=hid("net", 1))
    functions = (placed(4, x=104, y=304, page=2), placed(1, x=104, y=96, page=1))
    found = _members(functions=functions, connections=(across,))
    assert named(found) == [
        (CONNECTION_NOT_DRAWN, subjects(port(11), hid("conductor", 1))),
        (CONNECTION_NOT_DRAWN, subjects(port(42), hid("conductor", 1))),
    ]
    assert found == tuple(sorted(found, key=lambda one: (one.code, one.subjects)))
    assert found == _members(functions=tuple(reversed(functions)), connections=(across,))


def test_a_black_box_pin_placement_needs_nothing_in_its_set() -> None:
    """Port 31 stands in set 1 exempt (a black-box pin): no finding; exempt in set 2, one.

    # UNDO: lint/members.py, ignore `exempt` (drop the `(one.port, drawing_set) not in exempt` test)
    """
    layout = layout_of(routes=(wire(1, GOOD),), functions=PUMP)
    pin = frozenset({(port(31), 1)})
    elsewhere = frozenset({(port(31), 2)})
    assert named(check_members(layout, CONDUCTORS, (), (*DRAWN, drawn(4)), pin)) == []
    assert named(check_members(layout, CONDUCTORS, (), (*DRAWN, drawn(4)), elsewhere)) == (
        NOT_DRAWN_31
    )


def test_a_marker_on_a_terminals_other_side_does_not_cover_its_bare_side() -> None:
    """The pump-1 shape: terminal 3 has an outer port 32 with a marker (its own net, with 41).

    Its inner port 31 (the net of 12 and 21) is a bare member on page 2: found, 31 only. The two
    sides of a terminal are two nets, so a marker of one is no cover for the other.

    # UNDO: lint/members.py, let any covered port of a terminal cover its other ports
    """
    outer = connection(4, 3, 4)  # 32 - 41, its own net
    on_outer = marker(hid("conductor", 4), 32, USER, page=2, at=(304, 320))
    layout = layout_of(routes=(wire(1, GOOD),), markers=(on_outer,), functions=PUMP)
    terminal = (drawn(1), drawn(2), drawn(3, kind="terminal"), drawn(4))
    found = check_members(layout, (*CONDUCTORS, outer), (), terminal)
    assert named(found) == NOT_DRAWN_31


def test_a_port_in_a_conductor_and_in_a_net_group_of_another_net_is_no_fault() -> None:
    """Port 12 is in conductor 1 (net 1) and in a net group of net 7, with port 31.

    Before the stars are taken out the connectivity may say this; `locate` refuses it. The
    net is 12, 21 and 31: port 31 is alone on page 2 and found.

    # UNDO: lint/members.py, call `_ports.locate` on the given connectivity again
    """
    both = group(7, ((1, 12), (3, 31)))
    layout = layout_of(routes=(wire(1, GOOD),), functions=PUMP)
    with pytest.raises(LayoutError):
        locate((C1,), (both,), layout.placed, DRAWN)
    assert named(check_members(layout, (C1,), (both,), DRAWN)) == NOT_DRAWN_31_GROUP
