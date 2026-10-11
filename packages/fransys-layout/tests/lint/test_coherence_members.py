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

from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN
from fransys_layout.lint.members import check_members
from fransys_layout.stages import LinkCase, MarkerSide

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


# One net group of ports 12, 21 and 31 (a declared net, no conductors); the edge joins 12-21.
NET = group(7, ((1, 12), (2, 21), (3, 31)))
NET_MARKER = marker(hid("net", 7), 31, USER, page=2, at=(304, 288))


# Function 3 is also placed on page 1, where a marker or a route covers port 31.
ON_BOTH = (*PUMP, placed(3, x=304, y=304, page=1, name="b"))
ROUTE_31 = wire(2, ((104, 112), (104, 200), (304, 200), (304, 288)), a=12, b=31, page=1)
MARKER_31 = marker(hid("conductor", 2), 31, USER, page=1, at=(304, 288))


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
