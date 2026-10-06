"""D15 and D2 (layout deep dive): the order wires are drawn in, and the carrier's-lane target.

The unit tests of `stages._sides` and of `route` on invented functions from `samples`: a
carrier (function 1) with a side element (function 2, `carrier` set) beside it, and a far
function 3 whose port is wired to the side element's `in`.
"""

import dataclasses

from routing import route
from samples import PROFILE, SHEET, drawn, hid, placed

from fransys_layout.geometry import Facing, Point
from fransys_layout.stages import Connection, NetGroup, PortRef, Role
from fransys_layout.stages._sides import Edge, _splice, drawn_order, located
from fransys_layout.stages.space import End

# Ports of function `n`: `in` is `10 n + 1` (top, N), `out` is `10 n + 2` (bottom, S).
IN, OUT = 1, 2


def _ref(function: int, side: int) -> PortRef:
    return PortRef(function=hid("function", function), port=hid("port", function * 10 + side))


def _wire(number: int, one: tuple[int, int], other: tuple[int, int], net: int = 5) -> Connection:
    """Conductor `number` on net `net` between `(function, IN or OUT)` ends."""
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", net),
        role=Role.CONTROL,
        a=_ref(*one),
        b=_ref(*other),
    )


def _points(route_) -> list[tuple[int, int]]:
    return [(p.at.x, p.at.y) for p in route_.points]


def _side_page(*connections: Connection):
    """Route the carrier 1 at x = 104, its side element 2 at x = 160 and function 3 far to the left.

    The far function's `out` is at (56, 104), up and to the left of the carrier's `in` (104, 184)
    and the side element's `in` (160, 184).
    """
    functions = (
        placed(1, x=104, y=200),
        dataclasses.replace(placed(2, x=160, y=200, name="b"), carrier=hid("function", 1)),
        placed(3, x=56, y=88, name="c"),
    )
    routes, findings = route(
        connections,
        (),
        functions,
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert findings == ()
    return {(r.a, r.b): r for r in routes}


LONG = ((3, OUT), (2, IN))
JOIN = ((1, IN), (2, IN))
LONG_ENDS = (hid("port", 21), hid("port", 32))
# The far wire rides the carrier's lane (x = 104) and the join, not the side element's lane.
ON_THE_CARRIER = [(160, 184), (160, 176), (104, 176), (104, 112), (56, 112), (56, 104)]
DIRECT = [(160, 184), (160, 112), (56, 112), (56, 104)]


def test_a_wire_to_a_side_port_runs_on_the_carriers_lane_and_ends_on_the_side_port() -> None:
    """D2: drawn to the carrier's `in`, spliced onto the join; `Route.a` and `Route.b` unchanged."""
    # UNDO: stages/_sides.py retarget, return `edge, None, None` at once (skip the retarget)
    routes = _side_page(_wire(1, *JOIN), _wire(2, *LONG))
    long = routes[LONG_ENDS]
    assert _points(long) == ON_THE_CARRIER
    assert _points(long)[0] == (160, 184)  # the side element's own port
    assert (long.a, long.b) == LONG_ENDS


def test_a_join_is_drawn_before_a_wire_with_a_lower_upper_end_and_an_earlier_handle() -> None:
    """D15: the join has the later handle and the lower place, and still goes first."""
    # UNDO: stages/_sides.py drawn_order, key group `1` for every edge (drop the join group)
    routes = _side_page(_wire(9, *JOIN), _wire(2, *LONG))
    assert _points(routes[LONG_ENDS]) == ON_THE_CARRIER


def test_a_wire_to_a_side_port_with_no_join_is_drawn_direct() -> None:
    """D2: nothing may look joined that the model does not join."""
    # UNDO: stages/_sides.py retarget, resolve to the first join whatever its side port
    routes = _side_page(_wire(2, *LONG))
    assert _points(routes[LONG_ENDS]) == DIRECT


def test_a_join_to_another_port_of_the_side_element_leaves_the_wire_direct() -> None:
    """D2: the join to the side element's `out` says nothing about a wire to its `in`."""
    # UNDO: stages/_sides.py _join_to, drop the `join.side == ref` filter
    routes = _side_page(_wire(3, (1, IN), (2, OUT)), _wire(2, *LONG))
    # Direct, it still rides the free cells that join leaves the carrier by, and ends on `in`.
    assert _points(routes[LONG_ENDS]) == [(160, 184), (160, 176), (56, 176), (56, 104)]


def _page(functions, connections, groups=()):
    """Route `functions` (function `n` is `drawn(n)`) with `connections` and net `groups`."""
    routes, findings = route(
        connections,
        groups,
        functions,
        tuple(drawn(int(one.function.value, 16)) for one in functions),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert findings == ()
    return {(r.a, r.b): r for r in routes}


def _side(number: int, carrier: int, *, x: int, y: int, name: str):
    """Function `number` placed as a side element of function `carrier`."""
    return dataclasses.replace(
        placed(number, x=x, y=y, name=name), carrier=hid("function", carrier)
    )


def test_a_wire_between_two_side_ports_runs_on_both_carriers_lanes() -> None:
    """D2: both ends retargeted, both joins spliced, `Route.a` and `Route.b` unchanged."""
    # UNDO: stages/_sides.py joined, `if second is not None:` -> `if False and second is not None:`
    routes = _page(
        (
            placed(1, x=104, y=200),
            _side(2, 1, x=160, y=200, name="b"),
            placed(3, x=296, y=136, name="c"),
            _side(4, 3, x=352, y=136, name="d"),
        ),
        (_wire(1, (1, IN), (2, IN)), _wire(2, (3, IN), (4, IN)), _wire(3, (2, IN), (4, IN))),
    )
    both = routes[hid("port", 21), hid("port", 41)]
    # Out of the side port `2.in` (160, 184) and into `4.in` (352, 120), each by its join's hop
    # over its carrier's port (104, 184) and (296, 120): the hops fold into the run between.
    assert _points(both) == [(160, 184), (160, 176), (280, 176), (280, 112), (352, 112), (352, 120)]
    assert (both.a, both.b) == (hid("port", 21), hid("port", 41))


def test_of_two_joins_to_one_side_port_the_wire_aims_at_the_carrier_port_placed_first() -> None:
    """D2: the carrier's `in` (y 184) is above its `out` (y 216), so the far wire aims at `in`."""
    # UNDO: stages/_sides.py _join_to, add `reverse=True,` after the `key=` line of `sorted(`
    routes = _side_page(_wire(1, *JOIN), _wire(4, (1, OUT), (2, IN)), _wire(2, *LONG))
    # Aimed at `in` (104, 184), it comes down x = 56 and along y = 176 to the join's hop; aimed
    # at `out` it would leave that hop for the other join's way round, up x = 88.
    assert _points(routes[LONG_ENDS]) == [(160, 184), (160, 176), (56, 176), (56, 104)]


def _far_page(carrier: int | None):
    """The `_side_page` wires with function 2 the side element of `carrier` (`None`: no carrier)."""
    side = placed(2, x=160, y=200, name="b")
    if carrier is not None:
        side = dataclasses.replace(side, carrier=hid("function", carrier))
    return _page(
        (placed(1, x=104, y=200), side, placed(3, x=56, y=88, name="c")),
        (_wire(1, *JOIN), _wire(2, *LONG)),
    )


def test_a_carrier_that_is_not_on_the_page_leaves_the_side_element_an_ordinary_function() -> None:
    """D2 and D15: a carrier the page does not place makes no join and no retarget."""
    # UNDO: stages/_sides.py _carrier, `return carrier if carrier in placed_of else None` ->
    # `return carrier` leaves this test green: the missing check only changes the drawn order,
    # which test_a_wire_of_a_side_element_whose_carrier_is_not_on_the_page_is_not_a_join pins.
    assert _far_page(carrier=99) == _far_page(carrier=None)
    assert _points(_far_page(carrier=99)[LONG_ENDS]) == DIRECT


def _tree_page(far_x: int, far_y: int):
    """The `_side_page` layout with function 3 at `(far_x, far_y)` and no conductors.

    One net group holds the carrier's `in`, the side element's `in` and function 3's `out`.
    The result is `{(port a, port b): points}` with the ports as numbers.
    """
    group = NetGroup(
        net=hid("net", 5),
        physical_net=hid("net", 5),
        role=Role.CONTROL,
        ports=(_ref(1, IN), _ref(2, IN), _ref(3, OUT)),
    )
    functions = (
        placed(1, x=104, y=200),
        _side(2, 1, x=160, y=200, name="b"),
        placed(3, x=far_x, y=far_y, name="c"),
    )
    routes = _page(functions, (), (group,))
    return {(int(a.value, 16), int(b.value, 16)): _points(one) for (a, b), one in routes.items()}


def test_a_net_group_tree_that_joins_the_carrier_draws_the_far_edge_to_the_carrier_port() -> None:
    """D2, pinned: the tree is the join 1.in-2.in (56) and 3.out-1.in (128); no retarget happens."""
    # UNDO: stages/route.py _order, `return distance, ...` -> `return -distance, ...`
    assert _tree_page(56, 88) == {
        (11, 21): [(104, 184), (104, 176), (160, 176), (160, 184)],
        (11, 32): [(104, 184), (104, 112), (56, 112), (56, 104)],
    }


def test_a_net_group_tree_draws_the_join_edge_even_when_3_out_is_nearer_to_both_ports() -> None:
    """D2: 3.out is 40 from both `in` ports and they are 56 apart; the join is a tree edge all the
    same, because a side element's wire to its carrier is what every other wire follows.

    This replaces the known limit layout-0073 first pinned here (the tree dropped the join edge).
    """
    # UNDO: stages/route.py _order, `return group, distance, ...` -> `return 0, distance, ...`
    assert (11, 21) in _tree_page(128, 152)
    assert _tree_page(128, 152)[11, 21] == [(104, 184), (104, 176), (160, 176), (160, 184)]


def test_a_net_group_edge_to_a_side_port_follows_the_join_in_the_tree() -> None:
    """D2: 3.out is nearer the side `in` (40) than the carrier's (48), and they are 56 apart.

    The tree is the join and the edge 2.in to 3.out, and that edge is drawn to the carrier's
    port and spliced onto the join, the same as the wire of a conductor: it runs on the carrier's
    lane and ends on the side port.
    """
    # UNDO: stages/route.py _tree, do not seed the join edges into the tree before the sort
    assert _tree_page(136, 152) == {
        (11, 21): [(104, 184), (104, 176), (160, 176), (160, 184)],
        (21, 32): [(160, 184), (160, 176), (136, 176), (136, 168)],
    }


def test_two_equally_long_tree_edges_are_ordered_by_drawn_position_not_by_handle() -> None:
    """D15: 2.in and 1.in are 96 apart, and 3.out is 112 from each. The ports' handles sort
    1, 2, 3 but 1.in stands right of 2.in: the left one is upper in drawn order, so 2.in keeps
    the edge to 3.out and the handle order does not."""
    # UNDO: stages/route.py _order, return `distance, one.port, other.port` (handle tie-break)
    group = NetGroup(
        net=hid("net", 5),
        physical_net=hid("net", 5),
        role=Role.CONTROL,
        ports=(_ref(1, IN), _ref(2, IN), _ref(3, OUT)),
    )
    routes = _page(
        (placed(1, x=200, y=200), placed(2, x=104, y=200, name="b"), placed(3, x=152, y=104)),
        (),
        (group,),
    )
    assert sorted((int(a.value, 16), int(b.value, 16)) for a, b in routes) == [(11, 21), (21, 32)]


def _shared_net_page(first: int, second: int):
    """Wire `first` from 1.out to 2.out, wire `second` from 1.out to 3.out, all on one net.

    Function 2 stands high, so its wire has the higher upper end and is drawn first, whatever
    the handles are. The wire to function 3 then rides its trunk; drawn alone it would not.
    """
    functions = (
        placed(1, x=104, y=96),
        placed(2, x=296, y=80, name="b"),
        placed(3, x=200, y=192, name="c"),
    )
    routes, _ = route(
        (_wire(first, (1, OUT), (2, OUT)), _wire(second, (1, OUT), (3, OUT))),
        (),
        functions,
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    return {(r.a, r.b): _points(r) for r in routes}


def test_the_wire_with_the_higher_upper_end_is_drawn_first_whatever_the_handles() -> None:
    """D15: the two handle orders give one page, with the low wire riding the high wire's trunk."""
    # UNDO: stages/_sides.py drawn_order, sort by `(edge.connection, edge.a.port, edge.b.port)`
    one, other = _shared_net_page(1, 2), _shared_net_page(2, 1)
    assert one == other
    assert one[hid("port", 12), hid("port", 32)] == [
        (104, 112),
        (104, 120),
        (184, 120),
        (184, 216),
        (200, 216),
        (200, 208),
    ]


# --- drawn_order ---------------------------------------------------------------------


def _order(
    edges: list[Edge], at: dict[int, tuple[int, int]], *, sides: dict[int, int] | None = None
):
    """The `connection` numbers of `edges` in drawn order; `at` maps a function to its `(x, y)`."""
    sides = sides or {}
    placed_of = {
        hid("function", n): dataclasses.replace(
            placed(n, x=0, y=0), carrier=hid("function", sides[n]) if n in sides else None
        )
        for n in at
    }
    ends = {
        (hid("port", n * 10 + IN), ""): End(at=Point(x=x, y=y), facing=Facing.S)
        for n, (x, y) in at.items()
    }
    assert all(located(ref) in ends for edge in edges for ref in (edge.a, edge.b))
    return [int(edge.connection.value, 16) for edge in drawn_order(edges, ends, placed_of)]


def _edge(number: int, one: int, other: int) -> Edge:
    """An edge from function `one`'s `in` to function `other`'s `in`, named by `number`."""
    return Edge(
        connection=hid("conductor", number),
        physical_net=hid("net", 1),
        a=_ref(one, IN),
        b=_ref(other, IN),
        subjects=(hid("conductor", number),),
    )


def test_edges_with_the_same_two_ends_are_ordered_by_handle() -> None:
    """D15: a handle breaks a tie between edges with the same two drawn ends."""
    # UNDO: stages/_sides.py drawn_order, drop `edge.connection` from the key
    at = {1: (0, 0), 2: (8, 0)}
    assert _order([_edge(5, 1, 2), _edge(3, 1, 2)], at) == [3, 5]


def test_a_handle_never_orders_edges_with_different_ends() -> None:
    """D15: the same upper end and different lower ends: the lower end decides, not the handle."""
    # UNDO: stages/_sides.py drawn_order, put `edge.connection` before the two places in the key
    at = {1: (0, 0), 2: (0, 80), 3: (0, 40)}
    assert _order([_edge(1, 1, 2), _edge(2, 1, 3)], at) == [2, 1]


def test_the_upper_end_orders_top_to_bottom_then_left_to_right() -> None:
    """D15: places are `(y, x)`, so a higher end goes first, then the one further left."""
    # UNDO: stages/_sides.py _place, return `(x, y)`
    at = {1: (40, 0), 2: (8, 0), 3: (24, 40), 4: (80, 80)}
    assert _order([_edge(1, 1, 4), _edge(2, 2, 4), _edge(3, 3, 4)], at) == [2, 1, 3]


def test_a_join_goes_before_every_other_edge_even_with_a_lower_place_and_a_later_handle() -> None:
    """D15: function 2 is a side element of 1; the wire 1-2 is drawn before the higher wire."""
    # UNDO: stages/_sides.py drawn_order, key group `1` for every edge (drop the join group)
    at = {1: (0, 80), 2: (8, 80), 3: (0, 0), 4: (0, 8)}
    assert _order([_edge(1, 3, 4), _edge(9, 1, 2)], at, sides={2: 1}) == [9, 1]


def test_a_wire_between_two_ports_of_one_ordinary_function_is_not_a_join() -> None:
    """D15: only a side element makes a join, so the lower of two ordinary wires stays second."""
    # UNDO: stages/_sides.py is_join, drop the `any(... _carrier ...)` half
    at = {1: (0, 80), 3: (0, 0), 4: (0, 8)}
    assert _order([_edge(9, 1, 1), _edge(1, 3, 4)], at) == [1, 9]


def test_a_wire_of_a_side_element_whose_carrier_is_not_on_the_page_is_not_a_join() -> None:
    """D15: function 1 names carrier 99, which `at` does not place, so 1 is an ordinary function."""
    # UNDO: stages/_sides.py _carrier, `return carrier if carrier in placed_of else None`
    #       -> `return carrier`
    at = {1: (0, 80), 3: (0, 0), 4: (0, 8)}
    assert _order([_edge(9, 1, 1), _edge(1, 3, 4)], at, sides={1: 99}) == [1, 9]


# --- splice --------------------------------------------------------------------------


def _pts(*pairs: tuple[int, int]) -> list[Point]:
    return [Point(x=x, y=y) for x, y in pairs]


def _pairs(points) -> list[tuple[int, int]]:
    return [(p.x, p.y) for p in points]


def test_splice_of_two_runs_that_turn_at_the_meeting_point_keeps_the_corner() -> None:
    """The meeting point is written once, and it is a corner."""
    got = _splice(_pts((0, 0), (0, 8)), _pts((0, 8), (8, 8)))
    assert _pairs(got) == [(0, 0), (0, 8), (8, 8)]


def test_splice_of_two_runs_that_cancel_entirely_leaves_one_point_not_two() -> None:
    """No repeated point, even when everything folds away."""
    # UNDO: stages/_sides.py _cancel, drop the repeated-point case
    got = _splice(_pts((0, 0), (0, 8)), _pts((0, 8), (0, 0)))
    assert _pairs(got) == [(0, 0)]


def test_splice_of_two_runs_that_continue_straight_drops_the_middle_point() -> None:
    """No collinear middle point is kept."""
    # UNDO: stages/_sides.py _cancel, drop the collinear case
    got = _splice(_pts((0, 0), (0, 8)), _pts((0, 8), (0, 16)))
    assert _pairs(got) == [(0, 0), (0, 16)]


def test_splice_cancels_a_fold_of_equal_length_completely() -> None:
    """Down to 16 and straight back up to 0 leaves only what comes after."""
    # UNDO: stages/_sides.py _cancel, drop the collinear case
    got = _splice(_pts((0, 0), (0, 16)), _pts((0, 16), (0, 0), (8, 0)))
    assert _pairs(got) == [(0, 0), (8, 0)]


def test_splice_cancels_a_shorter_fold_and_keeps_the_rest_of_the_longer_run() -> None:
    """Down to 16 and back up to 8: the run is 0 to 8, then along."""
    got = _splice(_pts((0, 0), (0, 16)), _pts((0, 16), (0, 8), (24, 8)))
    assert _pairs(got) == [(0, 0), (0, 8), (24, 8)]


def test_splice_cancels_a_fold_that_goes_back_past_the_start_of_the_first_run() -> None:
    """The second run retraces the first and goes on past its start."""
    got = _splice(_pts((0, 8), (0, 16)), _pts((0, 16), (0, 0), (8, 0)))
    assert _pairs(got) == [(0, 8), (0, 0), (8, 0)]


def test_splice_of_a_mid_path_and_a_join_that_fold_back_gives_the_straight_wire() -> None:
    """The far wire to the carrier and the join back out to the side element: one straight run."""
    mid = _pts((160, 56), (160, 176), (104, 176), (104, 184))
    join = _pts((104, 184), (104, 176), (160, 176), (160, 184))
    assert _pairs(_splice(mid, join)) == [(160, 56), (160, 184)]
