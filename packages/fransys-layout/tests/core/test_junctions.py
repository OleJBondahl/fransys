"""`page_junctions`: where three or more wire directions and pins of one net meet (layout-0335)."""

from options_fixtures import core_options

from fransys_layout.core import Box, PinRef
from fransys_layout.core.clearance import Keep
from fransys_layout.core.junctions import page_junctions
from fransys_layout.core.outputs import Junction, PinXY, Placed, Wire
from fransys_layout.core.route_env import RouteEnv

from .conftest import MARKER

_OPTIONS = core_options(
    marker=MARKER,
)


def _junctions(
    wires: list[Wire], pins: dict[str, tuple[str, int, int]], *, netted: bool = True, keeps: tuple[Keep, ...] = ()
) -> tuple[Junction, ...]:
    """One page; `pins` maps a symbol id to its (net, x, y) pin `p`; `netted` gives it its net."""
    box = Box(0, 0, 1, 1)
    placed = {sym: Placed(sym, 1, x, y, "R0", box, box, (PinXY("p", x, y),)) for sym, (_, x, y) in pins.items()}
    net_of = {PinRef(sym, "p"): net for sym, (net, _, _) in pins.items()} if netted else {}
    env = RouteEnv(1, placed, (), net_of, {}, {}, (), (), (), (), frozenset(), _OPTIONS, obstacles=keeps)
    return page_junctions(env, wires)


def _wire(net: str, *points: tuple[int, int]) -> Wire:
    return Wire(net, 1, points, "straight")


def test_two_wires_and_a_pin_at_one_point_are_a_junction() -> None:
    wires = [_wire("n", (0, 0), (0, 8)), _wire("n", (0, 8), (16, 8))]
    assert _junctions(wires, {"K": ("n", 0, 8)}) == (Junction("n", 1, 0, 8),)


def test_a_pin_the_env_gives_no_net_counts_for_nothing() -> None:
    """The pins come from `env.net_of`: with none, two wires at a pin make no junction."""
    wires = [_wire("n", (0, 0), (0, 8)), _wire("n", (0, 8), (16, 8))]
    assert _junctions(wires, {"K": ("n", 0, 8)}, netted=False) == ()


def test_three_wires_ending_at_one_point_are_a_junction() -> None:
    wires = [_wire("n", (4, 4), (4, 0)), _wire("n", (4, 4), (0, 4)), _wire("n", (4, 4), (4, 8))]
    assert _junctions(wires, {}) == (Junction("n", 1, 4, 4),)


def test_a_wire_ending_on_the_inside_of_another_is_a_junction() -> None:
    wires = [_wire("n", (0, 4), (8, 4)), _wire("n", (4, 4), (4, 12))]
    assert _junctions(wires, {}) == (Junction("n", 1, 4, 4),)


def test_a_bend_a_pin_at_a_wire_end_and_overlapping_wires_are_none() -> None:
    bend = _wire("n", (0, 0), (0, 8), (8, 8))
    twice = [_wire("m", (20, 0), (20, 16)), _wire("m", (20, 0), (20, 8))]
    found = _junctions([bend, *twice], {"A": ("n", 8, 8), "B": ("m", 20, 0)})
    assert found == ()


def test_wires_of_two_nets_crossing_are_not_a_junction() -> None:
    wires = [_wire("a", (0, 4), (8, 4)), _wire("b", (4, 0), (4, 8))]
    assert _junctions(wires, {}) == ()


def test_a_bundle_conductor_gets_its_dot_at_a_t_like_any_wire() -> None:
    """RL-W1: a lane line is a wire of its member net; its T has a dot, another's has none."""
    line = Wire("L2", 1, ((0, 8), (48, 8)), "trunk", lane=1)
    own = Wire("L2", 1, ((24, 0), (24, 8)), "drop")
    other = Wire("L1", 1, ((36, 0), (36, 4)), "drop")
    assert _junctions([line, own, other], {}) == (Junction("L2", 1, 24, 8),)


def test_an_anchor_lead_through_a_wire_end_is_a_junction() -> None:
    """layout-0451: the lead from a pin to its power symbol's port is a segment; a wire ending on it makes a T."""
    wires = [_wire("n", (0, 0), (0, 8)), _wire("n", (0, 8), (16, 8))]
    keep = Keep("", Box(0, 0, 1, 1), "anchor", "K", "n", (0, 16))
    assert _junctions(wires, {"K": ("n", 0, 0)}, keeps=(keep,)) == (Junction("n", 1, 0, 8),)
    assert _junctions(wires, {"K": ("n", 0, 0)}) == ()
