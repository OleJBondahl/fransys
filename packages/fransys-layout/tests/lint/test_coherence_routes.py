"""`lint.coherence`: what a route claims, where it ends, and what it touches.

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
from samples import connection, drawn, hid, placed

from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
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


C2 = connection(2, 3, 3)  # names ports 31 and 32
ROUTE_2 = wire(2, ((304, 288), (304, 320)), a=31, b=32)


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


def _shorts(y: int, points, *, x: int = 104) -> list:
    """Function 3 stands so that its port 31 sits at `(x, y)`; net 9 is that port alone."""
    functions = (*PLACED[:2], placed(3, x=x, y=y + 16, name="b"))
    findings = _check((wire(1, points),), net_groups=(group(9, ((3, 31),)),), functions=functions)
    return [one for one in findings if one[0] == ROUTE_SHORTS_NETS]


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
