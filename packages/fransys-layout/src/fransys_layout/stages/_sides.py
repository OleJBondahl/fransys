"""D2 and D15 (layout deep dive): the order wires are drawn in, and the carrier's-lane target.

A side element stands beside its carrier function and is joined to it by short wires, the
joins. Every other wire of that net must reach the carrier's port and run down the carrier's
lane, whichever of the net's ports the router would meet first. So a join is drawn before any
other wire (`drawn_order`), and a wire to a side element's port is drawn to the carrier's port
instead, then spliced onto the join (`retarget`, `joined`, `_splice`).

`route` owns the search and the cells; this module owns which wire goes first and where it
aims. Nothing here reads a file, a clock or a random source.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_layout.geometry import Point

    from .space import End
    from .types import Handle, PlacedFunction, PortRef

# Every located end, by where `located` puts it: the port, and the node port it lands on (R7 B5).
type Ends = dict[tuple[Handle, str], End]


@dataclass(frozen=True, slots=True)
class Edge:
    """One wire to draw: a conductor, or one edge of a net group's spanning tree."""

    connection: Handle
    physical_net: Handle
    a: PortRef
    b: PortRef
    subjects: tuple[Handle, ...]


@dataclass(frozen=True, slots=True)
class Join:
    """A drawn wire between a carrier's port and a port of its side element, carrier first."""

    carrier: PortRef
    side: PortRef
    points: tuple[Point, ...]


def located(ref: PortRef) -> tuple[Handle, str]:
    """Where an end is located: its port, and the node port it lands on when not its own (R7 B5)."""
    return ref.port, ref.symbol_port


def drawn_order(
    edges: Iterable[Edge], ends: Ends, placed_of: Mapping[Handle, PlacedFunction]
) -> list[Edge]:
    """D15: the edges in drawn order (`drawn_key`, then the handle triple), never handle order."""
    return sorted(
        edges,
        key=lambda edge: (
            *drawn_key(edge.a, edge.b, ends, placed_of),
            edge.connection,
            edge.a.port,
            edge.b.port,
        ),
    )


def drawn_key(
    a: PortRef, b: PortRef, ends: Ends, placed_of: Mapping[Handle, PlacedFunction]
) -> tuple[int, tuple[int, int], tuple[int, int]]:
    """D15: a wire's drawn-order key (join first, upper end, lower end), top-down, left to right."""
    upper, lower = sorted((_place(ends, a), _place(ends, b)))
    return (0 if _joins(a, b, placed_of) else 1), upper, lower


def _is_join(edge: Edge, placed_of: Mapping[Handle, PlacedFunction]) -> bool:
    """Whether `edge` joins a carrier to its side element, or two side elements of one carrier."""
    return _joins(edge.a, edge.b, placed_of)


def _joins(a: PortRef, b: PortRef, placed_of: Mapping[Handle, PlacedFunction]) -> bool:
    """`_is_join` for the two ends of a wire that may not be an `Edge` yet."""
    return any(_carrier(ref, placed_of) is not None for ref in (a, b)) and (
        _home(a, placed_of) == _home(b, placed_of)
    )


def joins_of(
    edge: Edge, points: tuple[Point, ...], placed_of: Mapping[Handle, PlacedFunction]
) -> list[Join]:
    """The joins a drawn `edge` makes: one when an end is a side element of the other's function."""
    return [
        Join(carrier=near, side=far, points=run)
        for near, far, run in ((edge.a, edge.b, points), (edge.b, edge.a, points[::-1]))
        if _carrier(far, placed_of) == near.function
    ]


def retarget(
    edge: Edge, joins: Iterable[Join], ends: Ends, placed_of: Mapping[Handle, PlacedFunction]
) -> tuple[Edge, Join | None, Join | None]:
    """D2: `edge` aimed at carrier ports; of several joins the first placed, then lowest handle."""
    if _is_join(edge, placed_of):
        return edge, None, None
    joins = tuple(joins)
    first, second = (_join_to(ref, joins, ends, placed_of) for ref in (edge.a, edge.b))
    return (
        replace(
            edge,
            a=edge.a if first is None else first.carrier,
            b=edge.b if second is None else second.carrier,
        ),
        first,
        second,
    )


def joined(mid: tuple[Point, ...], first: Join | None, second: Join | None) -> tuple[Point, ...]:
    """The polyline of the original edge: `mid`, with each retargeted end's join spliced on."""
    points = mid
    if first is not None:
        points = _splice(first.points[::-1], points)
    if second is not None:
        points = _splice(points, second.points)
    return points


def _splice(first: Sequence[Point], second: Sequence[Point]) -> tuple[Point, ...]:
    """Two polylines meeting at one point as one: fold-back overlap cancelled, corners only."""
    joined_points: list[Point] = []
    for point in (*first, *second):
        joined_points = [*joined_points, point]
        while (shorter := _cancel(joined_points)) is not None:
            joined_points = shorter
    return tuple(joined_points)


def _cancel(points: Sequence[Point]) -> list[Point] | None:
    """`points` without its last repeated point, or the middle of its last three on a line."""
    match points[-3:]:
        case [*_, one, two] if one == two:
            return [*points[:-1]]
        case [one, two, three] if _collinear(one, two, three):
            return [*points[:-2], three]
        case _:
            return None


def _collinear(one: Point, two: Point, three: Point) -> bool:
    """Whether three points share a vertical or a horizontal line."""
    return one.x == two.x == three.x or one.y == two.y == three.y


def _carrier(ref: PortRef, placed_of: Mapping[Handle, PlacedFunction]) -> Handle | None:
    """The carrier of the side element `ref` ends on, when that carrier is on this page."""
    carrier = placed_of[ref.function].carrier
    return carrier if carrier in placed_of else None


def _home(ref: PortRef, placed_of: Mapping[Handle, PlacedFunction]) -> Handle:
    """The function whose cell `ref` is drawn in: a side element's carrier, else its own."""
    carrier = _carrier(ref, placed_of)
    return ref.function if carrier is None else carrier


def _place(ends: Ends, ref: PortRef) -> tuple[int, int]:
    """Where an end stands as `(y, x)`, so a smaller place is higher, then further left."""
    where = ends[located(ref)].at
    return where.y, where.x


def _join_to(
    ref: PortRef, joins: tuple[Join, ...], ends: Ends, placed_of: Mapping[Handle, PlacedFunction]
) -> Join | None:
    """The join `ref` is retargeted to, `None` when it is not a side element's port with one."""
    if _carrier(ref, placed_of) is None:
        return None
    found = sorted(
        (join for join in joins if join.side == ref),
        key=lambda join: (_place(ends, join.carrier), join.carrier.port),
    )
    return found[0] if found else None
