"""`junctions`: where three or more wire directions and pins of one net meet (layout-0335)."""

from fransys_layout.core import CoreLayout, Junction, PinRef, Size, junctions
from fransys_layout.core.outputs import (
    Annotations,
    Counts,
    PagePlacement,
    PageRoutes,
    PinXY,
    Placed,
    Placement,
    Routes,
    Wire,
)
from fransys_layout.core.values import Box


def _layout(wires: list[Wire], pins: dict[str, tuple[str, int, int]]) -> CoreLayout:
    """One page; `pins` maps a symbol id to its (net, x, y) single pin `p`."""
    box = Box(0, 0, 1, 1)
    placed = tuple(
        Placed(sym, 1, x, y, "R0", box, box, (PinXY("p", x, y),)) for sym, (_, x, y) in pins.items()
    )
    page = PagePlacement(1, placed, (), (), (), ())
    routes = PageRoutes(1, tuple(wires), (), Counts(0, 0, 0, 0, 0))
    wired = frozenset((PinRef(sym, "p"), net) for sym, (net, _, _) in pins.items())
    return CoreLayout(
        Size(100, 100), (), Placement((page,)), Routes((routes,)), Annotations(), (), wired
    )


def _wire(net: str, *points: tuple[int, int]) -> Wire:
    return Wire(net, 1, points, "straight", 1)


def test_two_wires_and_a_pin_at_one_point_are_a_junction() -> None:
    wires = [_wire("n", (0, 0), (0, 8)), _wire("n", (0, 8), (16, 8))]
    found = junctions(_layout(wires, {"K": ("n", 0, 8)}))
    assert found == (Junction("n", 1, 0, 8),)


def test_three_wires_ending_at_one_point_are_a_junction() -> None:
    wires = [_wire("n", (4, 4), (4, 0)), _wire("n", (4, 4), (0, 4)), _wire("n", (4, 4), (4, 8))]
    assert junctions(_layout(wires, {})) == (Junction("n", 1, 4, 4),)


def test_a_wire_ending_on_the_inside_of_another_is_a_junction() -> None:
    wires = [_wire("n", (0, 4), (8, 4)), _wire("n", (4, 4), (4, 12))]
    assert junctions(_layout(wires, {})) == (Junction("n", 1, 4, 4),)


def test_a_bend_a_pin_at_a_wire_end_and_overlapping_wires_are_none() -> None:
    bend = _wire("n", (0, 0), (0, 8), (8, 8))
    twice = [_wire("m", (20, 0), (20, 16)), _wire("m", (20, 0), (20, 8))]
    found = junctions(_layout([bend, *twice], {"A": ("n", 8, 8), "B": ("m", 20, 0)}))
    assert found == ()


def test_wires_of_two_nets_crossing_are_not_a_junction() -> None:
    wires = [_wire("a", (0, 4), (8, 4)), _wire("b", (4, 0), (4, 8))]
    assert junctions(_layout(wires, {})) == ()
