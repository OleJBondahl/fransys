"""WP12 acceptance skeletons: `lint.coherence` (ROADMAP WP12, foundations.md 2.4, lint.md 6.8).

The check exists because a label-keyed router once cross-wired two fans while the
geometric score improved. Each code has an input that triggers it.
"""

import dataclasses

from coherence_helpers import DRAWN, NO_UNITS, group, layout_of, wire
from samples import connection, drawn, hid, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    MARKER_UNPAIRED,
    ROUTE_SHORTS_NETS,
    ROUTE_WRONG_PORT,
)
from fransys_layout.stages import (
    LinkCase,
    LinkDecision,
    LinkMarker,
    MarkerSide,
)


def _marker(side: MarkerSide, *, page: int, port: int) -> LinkMarker:
    """A marker at its port: 12 is `out` of function 1 (y = 96), 21 is `in` of function 2."""
    return LinkMarker(
        connection=hid("conductor", 1),
        port=hid("port", port),
        side=side,
        drawing_set=1,
        page=page,
        at=Point(x=104, y={12: 112, 21: 288}[port]),
        box=Box(x=104, y={12: 108, 21: 284}[port], width=24, height=8),
        partner_page=3 - page,
    )


def test_a_correctly_drawn_connection_is_coherent() -> None:
    """The wire runs from port 12 at (104, 112) to port 21 at (104, 288): no findings."""
    layout = layout_of(routes=(wire(1, ((104, 112), (104, 288))),))
    assert check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS) == ()


def test_a_connection_with_no_route_is_reported() -> None:
    """The model has a conductor the page does not show."""
    findings = check_coherence(
        layout_of(), (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS
    )
    assert [f.code for f in findings] == [CONNECTION_NOT_DRAWN]
    assert findings[0].subjects == (hid("conductor", 1),)


def test_a_connection_drawn_twice_is_reported() -> None:
    """Exactly once: two routes for one conductor are as wrong as none."""
    route = wire(1, ((104, 112), (104, 288)))
    findings = check_coherence(
        layout_of(routes=(route, route)), (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS
    )
    assert [f.code for f in findings] == [CONNECTION_DRAWN_TWICE]


def test_a_route_ending_at_the_wrong_port_is_reported() -> None:
    """The cross-wiring case: the wire claims port 21 but ends at function 3's port."""
    crossed = wire(1, ((104, 112), (104, 200), (304, 200), (304, 288)))
    findings = check_coherence(
        layout_of(routes=(crossed,)), (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS
    )
    assert ROUTE_WRONG_PORT in [f.code for f in findings]


def test_a_route_touching_a_port_of_another_net_is_reported() -> None:
    """The wire of net 1 passes through port 31 of function 3, which is on net 2."""
    shorting = wire(1, ((104, 112), (104, 200), (304, 200), (304, 288), (104, 288)))
    connections = (connection(1, 1, 2), connection(2, 3, 3))
    findings = check_coherence(
        layout_of(routes=(shorting,)), connections, (), DRAWN, function_units=NO_UNITS
    )
    assert ROUTE_SHORTS_NETS in [f.code for f in findings]


def test_a_severed_connection_with_its_marker_pair_is_coherent() -> None:
    """One owner and one user marker stand in for the route."""
    functions = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2))
    layout = layout_of(
        functions=functions,
        decisions=(
            LinkDecision(
                connection=hid("conductor", 1),
                a=hid("port", 12),
                b=hid("port", 21),
                case=LinkCase.SEVERED,
            ),
        ),
        markers=(
            _marker(MarkerSide.OWNER, page=1, port=12),
            _marker(MarkerSide.USER, page=2, port=21),
        ),
    )
    assert check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS) == ()


def test_a_severed_connection_with_one_marker_is_reported() -> None:
    """A missing user marker is `MARKER_UNPAIRED`."""
    functions = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2))
    layout = layout_of(
        functions=functions,
        decisions=(
            LinkDecision(
                connection=hid("conductor", 1),
                a=hid("port", 12),
                b=hid("port", 21),
                case=LinkCase.SEVERED,
            ),
        ),
        markers=(_marker(MarkerSide.OWNER, page=1, port=12),),
    )
    findings = check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS)
    assert [f.code for f in findings] == [MARKER_UNPAIRED]


def test_a_tag_echo_needs_no_route() -> None:
    """A connection covered by an echo decision is drawn by the echo, not by a wire."""
    same_item = (drawn(1), dataclasses.replace(drawn(2), item=hid("item", 1)), drawn(3))
    functions = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2))
    layout = layout_of(
        functions=functions,
        decisions=(
            LinkDecision(
                connection=hid("conductor", 1),
                a=hid("port", 12),
                b=hid("port", 21),
                case=LinkCase.TAG_ECHO,
            ),
        ),
    )
    assert (
        check_coherence(layout, (connection(1, 1, 2),), (), same_item, function_units=NO_UNITS)
        == ()
    )


def test_two_fans_with_swapped_routes_fail() -> None:
    """The named regression: two identical sub-circuits, routes swapped between them.

    Function pairs (1, 2) and (3, 4) are equal in every way but their ids. Each wire
    claims its own conductor and ports but is drawn between the other pair's ports.
    """
    functions = (
        placed(1, x=104, y=96),
        placed(2, x=104, y=304),
        placed(3, x=304, y=96, name="b"),
        placed(4, x=304, y=304, name="b"),
    )
    swapped = (
        wire(1, ((304, 112), (304, 288)), a=12, b=21),
        wire(2, ((104, 112), (104, 288)), a=32, b=41),
    )
    findings = check_coherence(
        layout_of(routes=swapped, functions=functions),
        (connection(1, 1, 2), connection(2, 3, 4)),
        (),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        function_units=NO_UNITS,
    )
    assert {f.code for f in findings} >= {ROUTE_WRONG_PORT}


def test_a_terminal_echo_needs_no_route() -> None:
    """A connection covered by a terminal-echo decision is accepted with no wire."""
    functions = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=2))
    layout = layout_of(
        functions=functions,
        decisions=(
            LinkDecision(
                connection=hid("conductor", 1),
                a=hid("port", 12),
                b=hid("port", 21),
                case=LinkCase.TERMINAL_ECHO,
            ),
        ),
    )
    assert check_coherence(layout, (connection(1, 1, 2),), (), DRAWN, function_units=NO_UNITS) == ()


def test_a_net_group_joined_into_one_tree_is_coherent() -> None:
    """Two ports of one net on one page and one route between them: nothing to report."""
    tree = dataclasses.replace(
        wire(7, ((104, 112), (104, 288))), connection=hid("net", 7), physical_net=hid("net", 7)
    )
    net = group(7, ((1, 12), (2, 21)))
    assert (
        check_coherence(layout_of(routes=(tree,)), (), (net,), DRAWN, function_units=NO_UNITS) == ()
    )


def test_a_net_group_left_in_two_pieces_is_reported() -> None:
    """Three ports and one route: port 32 is not joined, so the net is not drawn."""
    tree = dataclasses.replace(
        wire(7, ((104, 112), (104, 288))), connection=hid("net", 7), physical_net=hid("net", 7)
    )
    net = group(7, ((1, 12), (2, 21), (3, 32)))
    findings = check_coherence(
        layout_of(routes=(tree,)), (), (net,), DRAWN, function_units=NO_UNITS
    )
    assert [f.code for f in findings] == [CONNECTION_NOT_DRAWN]
    assert findings[0].subjects == (hid("net", 7),)
