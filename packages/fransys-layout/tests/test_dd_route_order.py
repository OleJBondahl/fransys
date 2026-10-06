"""D2 and D15 (layout deep dive): wires route in drawn order, never in handle order.

Two identical coil columns on `examples/demo-parts`: a feed terminal, a breaker, a carrier relay
coil, a side relay coil strapped to it (D2), and a zero terminal. The long wire runs from the
breaker's port 2 to the side coil's A1, the join from the carrier's A1 to the side coil's A1. A
conductor's handle is content-hashed from its authoring key, so the order the router draws two
wires in must not depend on it: the same design under another handle order draws the same page.
"""

import itertools
from typing import TYPE_CHECKING, NamedTuple

from dd_chain_fixtures import MCB, TERMINAL, build, design, route_between

from fransys_model.layout import Route, layout_of
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

RELAY = "DEMO-RLY-2CO-24"
# (carrier tag, side tag, breaker tag) per column. With these tags the handle of column 1's long
# wire sorts before its join and column 2's long wire sorts after its join (the guard in the first
# test checks it), found by a scratch search over the tags K1 to K6: the base router then draws
# column 1's long wire first, down the side coil's lane, and column 2's second, down the carrier's.
COLUMNS = (("K1", "K2", "Q1"), ("K3", "K4", "Q2"))
# `wire(..., n=12)` renames column 1's long conductor and nothing else: only its handle changes,
# and it then sorts after its join. Found by scratch search over n = 2 to 13.
RENAMED = 12

Point = tuple[int, int]


class _Column(NamedTuple):
    """One column's two wires: the routes, and their points read from the named end."""

    join: Route
    long: Route
    join_points: tuple[Point, ...]
    long_points: tuple[Point, ...]


def _build(rename: int | None = None) -> Model:
    """The two columns, built and laid out; `rename` is the `n=` key of column 1's long wire."""
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    strip = d.strip("XA", at=c)
    wire = d.wiring(colour="BU", gauge="0.75")
    for column, (carrier_tag, side_tag, breaker_tag) in enumerate(COLUMNS):
        carrier = d.item(RELAY, tag=carrier_tag, at=c, group=g).fn("coil")
        side = d.item(RELAY, tag=side_tag, at=c, group=g).fn("coil")
        wire(carrier["A1"], side["A1"])
        wire(carrier["A2"], side["A2"])
        feed, zero = (strip.terminal(TERMINAL, group=g) for _ in range(2))
        breaker = d.item(MCB, tag=breaker_tag, at=c, group=g)
        wire(feed.outer, breaker["1"])
        wire(breaker["2"], side["A1"], n=rename if column == 0 else None)
        wire(side["A2"], zero.inner)
    return build(parts, d).model


def _points_from(model: Model, route: Route, first: tuple[str, ...]) -> tuple[Point, ...]:
    """The route's points, running from the end on the function keyed `first`."""
    points = tuple((point.x, point.y) for point in route.points)
    start = functions(model)[ports(model)[route.a].function].key
    return points if start == first else points[::-1]


def _column(model: Model, carrier_tag: str, side_tag: str, breaker_tag: str) -> _Column:
    """The join and the long wire of the column whose relays and breaker carry these tags."""
    carrier, side = ((tag, "fn", "coil") for tag in (carrier_tag, side_tag))
    breaker = (breaker_tag, "fn", "element")
    join = route_between(model, (carrier, "A1"), (side, "A1"))
    long = route_between(model, (breaker, "2"), (side, "A1"))
    return _Column(
        join, long, _points_from(model, join, carrier), _points_from(model, long, breaker)
    )


def _long_first(column: _Column) -> bool:
    """Whether the long wire's conductor handle sorts before its join's."""
    long, join = column.long.conductor, column.join.conductor
    assert long is not None
    assert join is not None
    return long < join


def _lane(points: tuple[Point, ...]) -> int:
    """The x of the longest vertical run of a polyline."""
    runs = [(abs(a[1] - b[1]), a[0]) for a, b in itertools.pairwise(points) if a[0] == b[0]]
    return max(runs)[1]


def _relative(points: tuple[Point, ...], origin: Point) -> tuple[Point, ...]:
    """The points as offsets from `origin`."""
    return tuple((x - origin[0], y - origin[1]) for x, y in points)


def test_the_long_wire_of_a_side_element_net_runs_on_the_carriers_lane() -> None:
    """D2, D15: in both columns the long wire runs down the carrier's lane, drawn the same way.

    The handles of the two columns' wires sort opposite ways, so a handle-ordered router draws
    the long wire first in one column and second in the other, and the two columns differ.
    """
    # UNDO: stages/_sides.py drawn_order, sort by `(edge.connection, edge.a.port, edge.b.port)`
    model = _build()
    columns = [_column(model, *tags) for tags in COLUMNS]
    first, second = columns
    assert _long_first(first) != _long_first(second), (
        "the two columns' handles must sort opposite ways, or the test proves nothing"
    )
    for column in columns:
        origin = column.join_points[0]  # the carrier's A1 port
        assert _lane(column.long_points) == origin[0]
    relative = [
        (_relative(c.join_points, c.join_points[0]), _relative(c.long_points, c.join_points[0]))
        for c in columns
    ]
    assert relative[0] == relative[1]


def _routes(model: Model) -> dict[tuple[tuple[tuple[str, ...], str], ...], tuple[Point, ...]]:
    """Every route's points by its two ends `(function key, marking)`, read from the lower end."""
    found = {}
    for route in layout_of(model, Route).values():
        ends = sorted(
            (functions(model)[ports(model)[end].function].key, ports(model)[end].name)
            for end in (route.a, route.b)
        )
        found[tuple(ends)] = _points_from(model, route, ends[0][0])
    return found


def test_renaming_a_conductors_authoring_key_leaves_every_route_byte_identical() -> None:
    """D15: a conductor's key feeds only its handle, so renaming one moves no route.

    Column 1's long wire is renamed with `n=`; its handle then sorts after its join, where it
    sorted before, and a handle-ordered router draws the column the other way round.
    """
    # UNDO: stages/_sides.py drawn_order, sort by `(edge.connection, edge.a.port, edge.b.port)`
    before, after = _build(), _build(rename=RENAMED)
    handles = [{route.conductor for route in layout_of(m, Route).values()} for m in (before, after)]
    assert handles[0] != handles[1], "the rename must change a handle, or the test proves nothing"
    assert _long_first(_column(before, *COLUMNS[0])) != _long_first(_column(after, *COLUMNS[0])), (
        "the rename must flip the handle order of the long wire and its join, or it proves nothing"
    )
    routes = _routes(before)
    assert routes
    assert _routes(after) == routes
