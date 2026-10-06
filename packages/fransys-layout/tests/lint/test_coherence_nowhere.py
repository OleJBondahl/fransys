"""`lint.members.check_nowhere`: a net drawn nowhere is `CONNECTION_NOT_DRAWN` (layout-0080).

`check_members` lets a `(port, set)` pair in `exempt` draw nothing. The guard is the net under
that: a net of two or more ports with a member placed in some set and no route end or marker on
any of its members, in any set, is one finding, subjects its placed member ports. Every case has
a twin that must stay silent. All data is invented.

Function `n` has ports `10n + 1` and `10n + 2`; the net here is ports 12 and 21 (and 31).
"""

import dataclasses

import pytest
from coherence_helpers import DRAWN, edge, group, layout_of, marker, named, port, wire
from samples import connection, hid, placed

from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN
from fransys_layout.lint.members import check_members, check_nowhere
from fransys_layout.stages import MarkerSide
from fransys_model.kernel import Severity

C1 = connection(1, 1, 2)  # port 12 to port 21
FUNCTIONS = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=1))
NOWHERE = [(CONNECTION_NOT_DRAWN, (port(12), port(21)))]
EXEMPT_BOTH = frozenset({(port(12), 1), (port(21), 1)})
GOOD = ((104, 112), (104, 288))


def _nowhere(*, routes=(), markers=(), functions=FUNCTIONS, connections=(C1,), groups=()):
    layout = layout_of(routes=routes, markers=markers, functions=functions)
    return check_nowhere(layout, connections, groups, DRAWN)


def test_a_net_whose_placed_members_are_all_exempt_and_bare_is_drawn_nowhere() -> None:
    """Both ports are exempt in set 1 (the members check is silent) and nothing covers them.

    # UNDO: lint/members.py, `check_nowhere` returns nothing (delete the guard)
    """
    layout = layout_of(functions=FUNCTIONS)
    assert check_members(layout, (C1,), (), DRAWN, EXEMPT_BOTH) == ()
    found = check_nowhere(layout, (C1,), (), DRAWN)
    assert named(found) == NOWHERE
    assert found[0].severity is Severity.ERROR


@pytest.mark.parametrize("cover", ["route", "marker", "star marker", "marker in another set"])
def test_a_cover_on_any_member_in_any_set_is_no_nowhere(cover) -> None:
    """A route end, a marker (a star's too), or a marker of another set on one member.

    # UNDO: lint/members.py, `check_nowhere` drops the marker cover (or the route cover)
    """
    on_12 = marker(hid("conductor", 1), 12, MarkerSide.USER, page=1, at=(104, 112))
    if cover == "route":
        drawn_as = {"routes": (wire(1, GOOD),)}
    elif cover == "marker":
        drawn_as = {"markers": (on_12,)}
    elif cover == "star marker":
        drawn_as = {"markers": (dataclasses.replace(on_12, star="branch"),)}
    else:
        drawn_as = {"markers": (dataclasses.replace(on_12, drawing_set=2),)}
    assert named(_nowhere(**drawn_as)) == []
    assert named(_nowhere()) == NOWHERE


def test_a_net_of_one_port_is_no_nowhere() -> None:
    """A net group holding one port, placed and bare, is no net.

    # UNDO: lint/members.py, `check_nowhere` drops the "two or more ports" condition
    """
    alone = group(7, ((1, 12),))
    assert named(_nowhere(connections=(), groups=(alone,))) == []


def test_a_net_with_no_placed_member_is_no_nowhere() -> None:
    """Nothing of the net is placed in any set: there is nothing to draw.

    # UNDO: lint/members.py, `check_nowhere` reports a net with no placed member
    """
    assert named(_nowhere(functions=())) == []


def test_the_subjects_are_the_placed_members_only_sorted() -> None:
    """Port 31 (function 3) is in the net but not placed: not a subject.

    # UNDO: lint/members.py, name every port of the net (placed or not) as a subject
    """
    net = group(7, ((1, 12), (2, 21), (3, 31)))
    found = _nowhere(connections=(), groups=(net,))
    assert named(found) == NOWHERE
    assert found[0].subjects == tuple(sorted(found[0].subjects))


def test_two_conductors_bridged_by_a_net_group_are_one_net_drawn_nowhere() -> None:
    """Conductors 12-21 and 22-31 are two trees until a group joins 21 and 22: one finding.

    # UNDO: lint/members.py, `_nets` leaves the second tree apart (skips the group's union)
    """
    bridge = group(7, ((2, 21), (2, 22)))
    functions = (*FUNCTIONS, placed(3, x=304, y=304, page=1, name="b"))
    found = _nowhere(functions=functions, connections=(C1, connection(3, 2, 3)), groups=(bridge,))
    assert named(found) == [(CONNECTION_NOT_DRAWN, (port(12), port(21), port(22), port(31)))]


def test_a_net_group_net_with_an_edge_is_covered_too() -> None:
    """A spanning-tree edge of a net group ends at its ports: a route cover, no finding.

    # UNDO: lint/members.py, `check_nowhere` reads conductors' routes only
    """
    net = group(7, ((1, 12), (2, 21)))
    edges = (edge(7, 12, 21, GOOD),)
    assert named(_nowhere(routes=edges, connections=(), groups=(net,))) == []
    assert named(_nowhere(connections=(), groups=(net,))) == NOWHERE


def test_a_net_the_members_check_already_reported_is_not_reported_again() -> None:
    """Bare and not exempt: `check_members` names both ports; the guard adds nothing to them.

    # UNDO: lint/members.py, `check_nowhere` ignores `reported`
    """
    layout = layout_of(functions=FUNCTIONS)
    reported = check_members(layout, (C1,), (), DRAWN)
    assert named(reported) == [
        (CONNECTION_NOT_DRAWN, (hid("conductor", 1), port(12))),
        (CONNECTION_NOT_DRAWN, (hid("conductor", 1), port(21))),
    ]
    assert check_nowhere(layout, (C1,), (), DRAWN, reported) == ()
    assert named(check_nowhere(layout, (C1,), (), DRAWN)) == NOWHERE
