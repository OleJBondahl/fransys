"""`lint.coherence`: what a route claims, where it ends, and what it touches (design/lint.md 6.8).

Every case has a near-identical twin that must stay silent.
"""

import dataclasses

import pytest
from coherence_helpers import (
    DRAWN,
    NO_UNITS,
    PLACED,
    edge,
    group,
    layout_of,
    named,
    port,
    subjects,
    wire,
)
from samples import connection, drawn, hid, placed, through_geometry

from fransys_layout.geometry import Facing, Point, PortGeometry
from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    ROUTE_SHORTS_NETS,
    ROUTE_WRONG_PORT,
)

GOOD = ((104, 112), (104, 288))
C1 = connection(1, 1, 2)
CONDUCTOR = hid("conductor", 1)
WRONG_ID = subjects(CONDUCTOR, port(12), port(21))


def _check(routes, connections=(C1,), net_groups=(), functions=PLACED, functions_drawn=DRAWN):
    layout = layout_of(routes=routes, functions=functions)
    return named(
        check_coherence(layout, connections, net_groups, functions_drawn, function_units=NO_UNITS)
    )


@pytest.mark.parametrize(
    ("points", "wrong"),
    [
        (GOOD, False),
        (((104, 80), (104, 288)), True),  # starts at port 11, function 1's other port
        (((104, 112), (104, 320)), True),  # ends at port 22, function 2's other port
        (((104, 288), (104, 112)), True),  # runs b to a
    ],
)
def test_a_route_must_run_from_a_to_b(points, wrong) -> None:
    """A route must run from a to b."""
    assert _check((wire(1, points),)) == ([(ROUTE_WRONG_PORT, WRONG_ID)] if wrong else [])


def test_a_route_may_be_a_point_where_both_ports_share_a_cell() -> None:
    """Function 2's `in` sits on function 1's `out`, so `[p, p]` joins them."""
    functions = (placed(1, x=104, y=96), placed(2, x=104, y=128))
    assert _check((wire(1, ((104, 112), (104, 112))),), functions=functions) == []
    assert _check((wire(1, GOOD),), functions=functions) == [(ROUTE_WRONG_PORT, WRONG_ID)]


C2 = connection(2, 3, 3)  # names ports 31 and 32
ROUTE_2 = wire(2, ((304, 288), (304, 320)), a=31, b=32)


@pytest.mark.parametrize(
    ("a", "b", "points"),
    [
        (21, 12, GOOD[::-1]),  # the ports swapped, the ends where the claim puts them
        (21, 12, GOOD),
        (12, 31, ((104, 112), (304, 288))),  # a right, b another conductor's port
        (31, 21, ((304, 288), (104, 288))),  # b right, a another conductor's port
        (11, 21, ((104, 80), (104, 288))),
        (12, 22, ((104, 112), (104, 320))),
    ],
    ids=[
        "swapped, ends follow",
        "swapped",
        "b is another's",
        "a is another's",
        "a unnamed",
        "b unnamed",
    ],
)
def test_a_route_claiming_other_ports_than_its_conductor_covers_nothing(a, b, points) -> None:
    """The claim is wrong however well the route ends, and the route is not judged for shorts."""
    findings = _check((wire(1, points, a=a, b=b), ROUTE_2), (C1, C2))
    assert findings == [
        (CONNECTION_NOT_DRAWN, (CONDUCTOR,)),
        (ROUTE_WRONG_PORT, subjects(CONDUCTOR, port(a), port(b))),
    ]
    assert _check((wire(1, GOOD), ROUTE_2), (C1, C2)) == []


def test_a_route_claiming_no_known_handle_is_a_finding_not_a_raise() -> None:
    """A route claiming no known handle is a finding not a raise."""
    stray = wire(9, GOOD)
    assert _check((wire(1, GOOD), stray)) == [
        (ROUTE_WRONG_PORT, subjects(hid("conductor", 9), port(12), port(21)))
    ]
    assert _check((wire(1, GOOD),)) == []


def test_a_route_without_a_valid_claim_is_not_tested_for_shorts() -> None:
    """Conductor 9 is unknown, so its route runs through port 31 of net 2 unjudged."""
    route_2 = wire(2, ((304, 288), (304, 320)), a=31, b=32)
    through = ((104, 112), (104, 200), (304, 200), (304, 288))
    connections = (C1, connection(2, 3, 3))
    stray = wire(9, through)
    assert _check((wire(1, GOOD), route_2, stray), connections) == [
        (ROUTE_WRONG_PORT, subjects(hid("conductor", 9), port(12), port(21)))
    ]
    valid = wire(1, through)
    assert (ROUTE_SHORTS_NETS, subjects(CONDUCTOR, port(12), port(21), port(31))) in _check(
        (valid, route_2), connections
    )


def test_a_route_on_a_page_where_its_ends_are_not_placed_is_wrong_and_surplus() -> None:
    """The route sits on page 2; the functions are on page 1, where nothing is drawn."""
    assert _check((wire(1, GOOD, page=2),)) == [
        (CONNECTION_DRAWN_TWICE, (CONDUCTOR,)),
        (CONNECTION_NOT_DRAWN, (CONDUCTOR,)),
        (ROUTE_WRONG_PORT, WRONG_ID),
    ]


GROUP = group(7, ((1, 12), (2, 21)))
NET = hid("net", 7)


@pytest.mark.parametrize(
    ("route", "wrong"),
    [
        (edge(7, 12, 21, GOOD), False),
        (edge(7, 21, 12, GOOD), True),  # not in handle order
        (edge(7, 12, 31, ((104, 112), (304, 288))), True),  # port 31 is not in the group
        (edge(7, 12, 12, ((104, 112), (104, 112))), True),  # one port twice
    ],
)
def test_a_net_route_claims_two_distinct_ports_of_its_group_in_handle_order(route, wrong) -> None:
    """A net route is valid for two distinct ports of its group given in handle order."""
    findings = _check((route, ROUTE_2), (C2,), (GROUP,))
    if not wrong:
        assert findings == []
        return
    assert findings == [
        (CONNECTION_NOT_DRAWN, (NET,)),
        (ROUTE_WRONG_PORT, subjects(NET, route.a, route.b)),
    ]


def test_a_net_route_needs_both_ports_in_its_group_and_is_then_not_judged_for_shorts() -> None:
    """The port outside the group is named, and at the route's end, by another conductor."""
    outside_b = edge(7, 12, 31, ((104, 112), (304, 288)))
    assert _check((outside_b, ROUTE_2), (C2,), (GROUP,)) == [
        (CONNECTION_NOT_DRAWN, (NET,)),
        (ROUTE_WRONG_PORT, subjects(NET, port(12), port(31))),
    ]
    # port 12 belongs to conductor 4 (net 4), not to this group of ports 21 and 31
    conductor_4 = connection(4, 1, 1)
    route_4 = wire(4, ((104, 80), (104, 112)), a=11, b=12)
    outside_a = edge(7, 12, 21, GOOD)
    other_group = group(7, ((2, 21), (3, 31)))
    assert _check((outside_a, route_4), (conductor_4,), (other_group,)) == [
        (CONNECTION_NOT_DRAWN, (NET,)),
        (ROUTE_WRONG_PORT, subjects(NET, port(12), port(21))),
    ]


def _shorts(y: int, points, *, x: int = 104) -> list:
    """Function 3 stands so that its port 31 sits at `(x, y)`; net 9 is that port alone."""
    functions = (*PLACED[:2], placed(3, x=x, y=y + 16, name="b"))
    findings = _check((wire(1, points),), net_groups=(group(9, ((3, 31),)),), functions=functions)
    return [one for one in findings if one[0] == ROUTE_SHORTS_NETS]


@pytest.mark.parametrize("points", [GOOD, GOOD[::-1]], ids=["a to b", "b to a"])
@pytest.mark.parametrize(
    ("y", "touched"),
    [(96, False), (111, False), (112, True), (200, True), (288, True), (289, False), (304, False)],
)
def test_a_route_touches_a_port_on_a_segment_or_at_an_end(y, touched, points) -> None:
    """A route touches a port on a segment or at an end."""
    found = _shorts(y, points)
    assert found == (
        [(ROUTE_SHORTS_NETS, subjects(CONDUCTOR, port(12), port(21), port(31)))] if touched else []
    )


HORIZONTAL = ((104, 112), (304, 112))
DETOUR = ((104, 112), (104, 200), (304, 200), (304, 288), (104, 288))


@pytest.mark.parametrize(
    "points", [HORIZONTAL, HORIZONTAL[::-1]], ids=["left to right", "right to left"]
)
@pytest.mark.parametrize(
    ("x", "touched"),
    [(96, False), (103, False), (104, True), (200, True), (304, True), (305, False), (312, False)],
)
def test_a_port_on_a_horizontal_route_is_touched_between_its_ends(x, touched, points) -> None:
    """The box bounds hold on x as they do on y."""
    assert bool(_shorts(112, points, x=x)) is touched


def test_a_port_on_any_segment_of_the_route_is_touched() -> None:
    """Port 31 is on the first of four segments, and on none of the others."""
    assert bool(_shorts(150, DETOUR)) is True
    assert bool(_shorts(150, DETOUR, x=112)) is False


def test_a_port_is_where_its_symbol_port_is_from_the_placed_origin() -> None:
    """Function 1's `out` is 16 G right of its origin, so the route ends at x = 120."""
    ports = (
        PortGeometry(name="in", at=Point(x=0, y=-16), facing=Facing.N),
        PortGeometry(name="out", at=Point(x=16, y=16), facing=Facing.S),
    )
    geometry = dataclasses.replace(through_geometry(), ports=ports)
    wide = dataclasses.replace(placed(1, x=104, y=96), geometry=geometry)
    functions = (wide, *PLACED[1:])
    assert _check((wire(1, ((120, 112), (104, 288))),), functions=functions) == []
    assert _check((wire(1, ((88, 112), (104, 288))),), functions=functions) == [
        (ROUTE_WRONG_PORT, WRONG_ID)
    ]
    assert _check((wire(1, ((104, 112), (104, 288))),), functions=functions) == [
        (ROUTE_WRONG_PORT, WRONG_ID)
    ]


def test_a_port_beside_the_route_is_not_touched() -> None:
    """A port beside the route is not touched."""
    assert _shorts(200, GOOD, x=112) == []


@pytest.mark.parametrize(("y", "touched"), [(200, True), (216, False)])
def test_a_port_on_a_diagonal_segment_is_touched_only_on_the_line(y, touched) -> None:
    """From (104, 112) to (304, 288): (204, 200) is on it, (204, 216) is inside its box only."""
    assert bool(_shorts(y, ((104, 112), (304, 288)), x=204)) is touched


def test_a_route_through_a_port_of_another_net_shorts_it() -> None:
    """Conductor 1 detours through port 31, which is on conductor 2's net.

    Port 31 is where conductor 2's route starts, so the two routes also touch there (a corner
    on an end): the second finding is the touching half, named by both routes' claims.
    """
    detour = wire(1, ((104, 112), (104, 200), (304, 200), (304, 288), (104, 288)))
    route_2 = wire(2, ((304, 288), (304, 320)), a=31, b=32)
    connections = (C1, connection(2, 3, 3))
    assert _check((detour, route_2), connections) == sorted(
        [
            (ROUTE_SHORTS_NETS, subjects(CONDUCTOR, port(12), port(21), port(31))),
            (
                ROUTE_SHORTS_NETS,
                subjects(CONDUCTOR, port(12), port(21), hid("conductor", 2), port(31), port(32)),
            ),
        ]
    )
    assert _check((wire(1, GOOD), route_2), connections) == []


def test_a_port_of_the_routes_own_net_is_no_short() -> None:
    """The detour crosses port 31, which here is on net 1, the net of conductor 1."""
    detour = wire(1, ((104, 112), (104, 200), (304, 200), (304, 288), (104, 288)))
    assert _check((detour,), net_groups=(group(1, ((3, 31),)),)) == []
    assert _check((detour,), net_groups=(group(2, ((3, 31),)),)) == [
        (ROUTE_SHORTS_NETS, subjects(CONDUCTOR, port(12), port(21), port(31)))
    ]


def test_the_model_decides_the_net_a_route_is_judged_by_not_the_route() -> None:
    """The route says it is net 99, the net of port 31; conductor 1 says net 1."""
    detour = dataclasses.replace(
        wire(1, ((104, 112), (104, 200), (304, 200), (304, 288), (104, 288))),
        physical_net=hid("net", 99),
    )
    found = _check((detour,), net_groups=(group(99, ((3, 31),)),))
    assert found == [(ROUTE_SHORTS_NETS, subjects(CONDUCTOR, port(12), port(21), port(31)))]


def test_a_port_named_by_no_connection_is_not_judged() -> None:
    """The detour crosses port 31, which no conductor or net names."""
    detour = wire(1, ((104, 112), (104, 200), (304, 200), (304, 288), (104, 288)))
    assert _check((detour,)) == []


def _fans(routes):
    """Two sub-circuits with equal authoring keys and different handles."""
    fans = (
        placed(1, x=104, y=96),
        placed(2, x=104, y=304),
        placed(3, x=304, y=96, name="b"),
        placed(4, x=304, y=304, name="b"),
    )
    equal = (
        drawn(1),
        drawn(2),
        dataclasses.replace(drawn(3), key=drawn(1).key),
        dataclasses.replace(drawn(4), key=drawn(2).key),
    )
    return _check(routes, (C1, connection(2, 3, 4)), functions=fans, functions_drawn=equal)


def test_two_fans_with_equal_keys_and_swapped_routes_report_every_defect() -> None:
    """The regression that motivated the check: each wire is drawn between the other fan's ports.

    The four functions are equal in every field the check reads, so only identity by handle
    can tell the routes apart.
    """
    swapped = (
        wire(1, ((304, 112), (304, 288)), a=12, b=21),
        wire(2, ((104, 112), (104, 288)), a=32, b=41),
    )
    c1, c2 = hid("conductor", 1), hid("conductor", 2)
    assert _fans(swapped) == sorted(
        [
            (ROUTE_WRONG_PORT, subjects(c1, port(12), port(21))),
            (ROUTE_WRONG_PORT, subjects(c2, port(32), port(41))),
            (ROUTE_SHORTS_NETS, subjects(c1, port(12), port(21), port(32))),
            (ROUTE_SHORTS_NETS, subjects(c1, port(12), port(21), port(41))),
            (ROUTE_SHORTS_NETS, subjects(c2, port(32), port(41), port(12))),
            (ROUTE_SHORTS_NETS, subjects(c2, port(32), port(41), port(21))),
        ]
    )


def test_two_fans_drawn_where_they_belong_are_coherent() -> None:
    """Two fans drawn where they belong are coherent."""
    straight = (
        wire(1, ((104, 112), (104, 288)), a=12, b=21),
        wire(2, ((304, 112), (304, 288)), a=32, b=41),
    )
    assert _fans(straight) == []
