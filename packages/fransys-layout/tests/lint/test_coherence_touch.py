"""`lint.coherence`: two physical nets touching on a page (`ROUTE_SHORTS_NETS`, design/lint.md 6.8).

The routes are hand-made and need not end at their ports; only each claim (connection, a, b)
must be valid. The functions stand far off, so no route lies on a placed port and only the
touching half of the check can fire. Every case has a near-identical twin that must stay silent.
"""

import dataclasses

import pytest
from coherence_helpers import NO_UNITS, edge, group, layout_of, port, subjects, wire
from samples import connection, drawn, hid, placed

from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import ROUTE_SHORTS_NETS
from fransys_model.kernel import Severity

FAR = tuple(placed(n, x=2000, y=2000 + 100 * n, name="b") for n in range(1, 7))
FAR_DRAWN = tuple(drawn(n) for n in range(1, 7))
CONNECTIONS = (connection(1, 1, 2), connection(2, 3, 4), connection(3, 5, 6))  # nets 1, 2, 3

CROSS_A = ((104, 112), (104, 288))  # vertical
CROSS_B = ((48, 200), (304, 200))  # horizontal, crossing CROSS_A at (104, 200)


def _route(number, points, *, page=1, drawing_set=1):
    """Conductor `number`'s route: a valid claim (ports `20n - 8` and `20n + 1`), any points."""
    route = wire(number, points, a=20 * number - 8, b=20 * number + 1, page=page)
    return dataclasses.replace(route, drawing_set=drawing_set)


def _who(*numbers):
    """The subjects of a finding about the routes of conductors `numbers`."""
    return subjects(
        *(h for n in numbers for h in (hid("conductor", n), port(20 * n - 8), port(20 * n + 1)))
    )


def _at(x, y, *, page=1, drawing_set=1):
    """The message of a touch at `(x, y)`."""
    return f"two physical nets touch on page {page} of drawing set {drawing_set} at ({x}, {y})"


def _all(routes, *, connections=CONNECTIONS, net_groups=()):
    layout = layout_of(routes=routes, functions=FAR)
    findings = check_coherence(layout, connections, net_groups, FAR_DRAWN, function_units=NO_UNITS)
    return [one for one in findings if one.code == ROUTE_SHORTS_NETS]


def _touches(routes, **kwargs):
    """The `ROUTE_SHORTS_NETS` findings of `routes` as `(subjects, message)`, in check order."""
    return [(one.subjects, one.message) for one in _all(routes, **kwargs)]


def _between(a, b, cell, *, page=1, drawing_set=1):
    """What nets 1 and 2 drawn as `a` and `b` yield, in either route order; `cell` None: silent."""
    routes = (
        _route(1, a, page=page, drawing_set=drawing_set),
        _route(2, b, page=page, drawing_set=drawing_set),
    )
    expected = (
        [] if cell is None else [(_who(1, 2), _at(*cell, page=page, drawing_set=drawing_set))]
    )
    assert _touches(routes) == expected
    assert _touches(routes[::-1]) == expected


@pytest.mark.parametrize(
    ("a", "b", "cell"),
    [
        (CROSS_A, ((104, 200), (104, 400)), (104, 200)),
        (CROSS_A, ((104, 400), (104, 200)), (104, 200)),  # the other one drawn the other way
        (CROSS_A, CROSS_A, (104, 112)),
        (CROSS_A, ((104, 160), (104, 240)), (104, 160)),  # inside the other's segment
        (((104, 112), (304, 112)), ((200, 112), (400, 112)), (200, 112)),
        (((104, 112), (304, 112)), ((104, 112), (304, 112)), (104, 112)),
        (CROSS_A, ((104, 296), (104, 400)), None),  # in line, one step apart
        (CROSS_A, ((112, 112), (112, 288)), None),  # side by side, one step apart
        (((104, 112), (304, 112)), ((104, 120), (304, 120)), None),
        (((104, 112), (200, 112)), ((208, 112), (304, 112)), None),
    ],
    ids=[
        "vertical, in part",
        "vertical, in part, reversed",
        "vertical, whole",
        "vertical, inside",
        "horizontal, in part",
        "horizontal, whole",
        "vertical in line apart",
        "vertical side by side",
        "horizontal side by side",
        "horizontal in line apart",
    ],
)
def test_two_nets_drawing_the_same_segment_touch_once(a, b, cell) -> None:
    """A segment both draw, in whole or in part, is one finding however many cells it covers."""
    _between(a, b, cell)


@pytest.mark.parametrize(
    ("a", "b", "cell"),
    [
        (((104, 112), (104, 200), (200, 200)), ((48, 200), (304, 200)), (104, 200)),
        (((104, 112), (104, 200), (200, 200)), ((48, 208), (304, 208)), None),  # a step beside
        (((48, 112), (104, 112), (104, 200)), ((104, 48), (104, 288)), (104, 112)),
        (((48, 112), (104, 112), (104, 200)), ((112, 48), (112, 288)), None),
    ],
    ids=["on a horizontal", "beside a horizontal", "on a vertical", "beside a vertical"],
)
def test_a_corner_on_the_other_nets_wire_touches(a, b, cell) -> None:
    """One net's corner on the other's wire; one grid step (8 G) beside it, nothing."""
    _between(a, b, cell)


@pytest.mark.parametrize(
    ("a", "b", "cell"),
    [
        (((104, 112), (104, 200)), CROSS_B, (104, 200)),  # ends on a horizontal
        (((104, 112), (104, 192)), CROSS_B, None),  # one step short
        (((48, 200), (104, 200)), CROSS_A, (104, 200)),  # ends on a vertical
        (((48, 200), (96, 200)), CROSS_A, None),
        (((104, 112), (104, 200)), ((104, 200), (104, 400)), (104, 200)),  # ends meet in line
        (((104, 112), (104, 200)), ((104, 208), (104, 400)), None),
        (((104, 112), (104, 200)), ((104, 200), (200, 200)), (104, 200)),  # ends meet in an L
        (((104, 112), (104, 200)), ((112, 200), (200, 200)), None),
    ],
    ids=[
        "on a horizontal",
        "short of a horizontal",
        "on a vertical",
        "short of a vertical",
        "in line",
        "in line apart",
        "in an L",
        "in an L apart",
    ],
)
def test_a_route_end_on_the_other_nets_wire_touches(a, b, cell) -> None:
    """A route end counts as touching: its cell has both axes."""
    _between(a, b, cell)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (CROSS_A, CROSS_B),
        (CROSS_A, ((48, 200), (304, 200), (304, 288))),  # one bends far off
        (((104, 112), (104, 288), (200, 288)), CROSS_B),
        (CROSS_A, ((48, 200), (152, 200), (152, 240), (48, 240))),  # crosses twice
    ],
    ids=["plain", "b bends", "a bends", "twice"],
)
def test_crossing_at_right_angles_through_both_straights_is_allowed(a, b) -> None:
    """One route passes the cell only along `h`, the other only along `v`."""
    _between(a, b, None)


@pytest.mark.parametrize(
    ("a", "b", "cell"),
    [
        (((104, 112), (104, 200), (200, 200)), CROSS_B, (104, 200)),  # a turns on the cell
        # a turns left and runs along b to b's start: the smallest shared cell is that end
        (((104, 112), (104, 200), (48, 200)), CROSS_B, (48, 200)),
        (CROSS_A, ((48, 200), (104, 200), (104, 300)), (104, 200)),  # b turns on the cell
        (((104, 112), (104, 200)), CROSS_B, (104, 200)),  # a ends on the cell
        (((104, 200), (104, 288)), CROSS_B, (104, 200)),  # a starts on the cell
        (((104, 112), (104, 192), (200, 192)), CROSS_B, None),  # a turns one step above it
    ],
    ids=["a turns right", "a turns left", "b turns", "a ends", "a starts", "a turns one step off"],
)
def test_a_corner_or_an_end_on_the_crossing_cell_is_a_touch(a, b, cell) -> None:
    """The crossing of `CROSS_A` and `CROSS_B` is allowed only while both go straight through."""
    _between(a, b, cell)


SAME_NET = (
    CONNECTIONS[0],
    dataclasses.replace(CONNECTIONS[1], physical_net=hid("net", 1)),
    CONNECTIONS[2],
)


@pytest.mark.parametrize(
    ("a", "b", "cell"),
    [
        (CROSS_A, ((104, 200), (104, 400)), (104, 200)),  # overlap in part
        (CROSS_A, CROSS_A, (104, 112)),  # overlap whole
        (CROSS_A, ((104, 200), (200, 200)), (104, 200)),  # a T
        (((104, 112), (104, 200)), ((104, 200), (104, 400)), (104, 200)),  # ends meet
    ],
    ids=["overlap in part", "overlap whole", "T", "ends meet"],
)
def test_two_routes_of_one_physical_net_may_overlap_and_meet(a, b, cell) -> None:
    """Conductors 1 and 2 on one net are silent; on two nets the same routes are a finding."""
    routes = (_route(1, a), _route(2, b))
    assert _touches(routes, connections=SAME_NET) == []
    assert _touches(routes) == [(_who(1, 2), _at(*cell))]


def test_a_conductor_and_a_net_edge_of_one_physical_net_may_overlap() -> None:
    """The edge of net group 1 joins ports 31 and 41; group 2 is another physical net."""
    one_net = (CONNECTIONS[0],)
    same = (_route(1, CROSS_A), edge(1, 31, 41, ((104, 200), (104, 400))))
    assert _touches(same, connections=one_net, net_groups=(group(1, ((3, 31), (4, 41))),)) == []
    other = (_route(1, CROSS_A), edge(2, 31, 41, ((104, 200), (104, 400))))
    assert _touches(other, connections=one_net, net_groups=(group(2, ((3, 31), (4, 41))),)) == [
        (subjects(*_who(1), hid("net", 2), port(31), port(41)), _at(104, 200))
    ]


@pytest.mark.parametrize(
    ("page", "drawing_set", "a", "b", "cell"),
    [
        (2, 3, CROSS_A, ((104, 200), (104, 400)), (104, 200)),  # a shared segment
        (4, 2, ((104, 112), (104, 200), (200, 200)), CROSS_B, (104, 200)),  # a corner
        (
            1,
            1,
            ((104, 288), (104, 120), (304, 120), (304, 200)),
            ((104, 288), (304, 288), (304, 200)),
            (104, 288),  # touching at (104, 288) and (304, 200): the smaller in (x, y) order
        ),
    ],
    ids=["shared segment", "corner", "two cells"],
)
def test_the_message_names_page_drawing_set_and_the_smallest_touched_cell(
    page, drawing_set, a, b, cell
) -> None:
    """The touch point is the smallest cell in `(x, y)` order, not in `(y, x)` order."""
    _between(a, b, cell, page=page, drawing_set=drawing_set)


def test_a_route_without_a_valid_claim_is_not_judged_for_touching() -> None:
    """Conductor 1's route claims its ports swapped, so it covers nothing; its twin claims right."""
    swapped = dataclasses.replace(_route(1, CROSS_A), a=port(21), b=port(12))
    assert _touches((swapped, _route(2, CROSS_A))) == []
    assert _touches((_route(1, CROSS_A), _route(2, CROSS_A))) == [(_who(1, 2), _at(104, 112))]


def test_a_finding_is_an_error_coded_route_shorts_nets() -> None:
    """The touch is the same code and severity as a port on a route."""
    (one,) = _all((_route(1, CROSS_A), _route(2, CROSS_A)))
    assert (one.code, one.severity) == ("ROUTE_SHORTS_NETS", Severity.ERROR)


@pytest.mark.parametrize(
    ("page_b", "set_b", "touches"),
    [(1, 1, True), (2, 1, False), (1, 2, False)],
    ids=["same page", "another page", "another drawing set"],
)
def test_routes_on_different_pages_never_touch(page_b, set_b, touches) -> None:
    """Identical geometry, but only the route pair on one `(drawing_set, page)` touches."""
    routes = (_route(1, CROSS_A), _route(2, CROSS_A, page=page_b, drawing_set=set_b))
    assert _touches(routes) == ([(_who(1, 2), _at(104, 112))] if touches else [])


TRIANGLE = (
    _route(1, ((104, 112), (104, 288))),
    _route(2, ((104, 200), (304, 200))),  # ends on 1's wire, and on 3's end
    _route(3, ((104, 112), (304, 112), (304, 200))),  # starts on 1's end
)


def test_three_mutually_touching_routes_give_three_findings_in_check_order() -> None:
    """One finding per pair, sorted by subjects, whatever the order of the routes."""
    expected = [
        (_who(1, 2), _at(104, 200)),
        (_who(1, 3), _at(104, 112)),
        (_who(2, 3), _at(304, 200)),
    ]
    assert _touches(TRIANGLE) == expected
    assert _touches(TRIANGLE[::-1]) == expected


def test_a_triangle_with_one_corner_pulled_apart_has_two_findings() -> None:
    """Route 3 starts one step right of route 1's end, so the pair 1 and 3 is silent."""
    apart = _route(3, ((112, 112), (304, 112), (304, 200)))
    assert _touches((TRIANGLE[0], TRIANGLE[1], apart)) == [
        (_who(1, 2), _at(104, 200)),
        (_who(2, 3), _at(304, 200)),
    ]
