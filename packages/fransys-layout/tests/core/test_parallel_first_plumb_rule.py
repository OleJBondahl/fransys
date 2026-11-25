"""PARALLEL-FIRST-PLUMB: the first branch plumb under its predecessor, each next a pitch right."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations, pairwise
from typing import Any

import pytest
from turn_fixtures import views_of

from fransys_layout.core.series_values import Parallel, Series
from fransys_layout.core.values import Box, BoxSpec, Pin

from .flow_builders import OPTIONS, elem, net, problem
from .pipeline_fixtures import flow_of, placed_of, routed_of
from .place_fixtures import all_pins
from .topology_fixtures import box


def _flow(order: tuple[str, ...], widths: dict[str, int] | None = None) -> Any:
    """S1, (P1 || two-pole P2a-P2b || P3), B, with the branches in `order`."""
    nets = [
        net("a", "S1.s", "P1.n", "P2a.n", "P3.n"),
        net("m", "P2a.s", "P2b.n"),
        net("b", "P1.s", "P2b.s", "P3.s", "B.n"),
    ]
    wide = widths or {}
    syms = [elem(n, wide.get(n, 16)) for n in ("S1", "P1", "P2a", "P2b", "P3", "B")]
    prob = problem(syms, nets)
    branches = {"P1": "P1", "P2": Series(("P2a", "P2b")), "P3": "P3"}
    tree = Series(("S1", Parallel(tuple(branches[k] for k in order)), "B"))
    return flow_of(replace(prob, facts=replace(prob.facts, series=(tree,))))


@pytest.mark.rule("PARALLEL-FIRST-PLUMB")
def test_every_parallel_first_branch_plumbs_and_each_next_stands_pitch_right() -> None:
    """Catches a first branch off its predecessor's lane, a next branch closer than the pitch."""
    lanes = _flow(("P1", "P2", "P3")).columns[0].lanes
    assert [c.sym for c in lanes[0].cells][:2] == ["S1", "P1"]
    assert [ln.offset for ln in lanes] == [0, OPTIONS.parallel_pitch, 2 * OPTIONS.parallel_pitch]
    assert {c.sym: c.hold for ln in lanes for c in ln.cells}["B"] == 40


@pytest.mark.rule("PARALLEL-FIRST-PLUMB")
def test_a_next_branch_clears_a_wider_branch_before_it_by_the_edge_rule() -> None:
    """P2a is 80 wide, so P2 sits at 56 and P3 clears 56 + 40 + 8 + 8 = 112, past 56 + 48 = 104."""
    lanes = _flow(("P1", "P2", "P3"), {"P2a": 80}).columns[0].lanes
    assert [ln.offset for ln in lanes] == [0, 56, 112]


@pytest.mark.rule("PARALLEL-FIRST-PLUMB")
@pytest.mark.parametrize("loads", [("A", "B"), ("A", "B", "C")])
def test_the_first_load_of_a_fan_off_a_box_pin_stands_plumb_under_the_pin(loads: tuple[str, ...]) -> None:
    """Catches a fan's first load (by designation) standing right of its box pin, as a free run past the card."""
    syms = [box("X"), *(elem(n) for n in loads)]
    nets = [net("x", "X.s", *(f"{n}.n" for n in loads)), *(net(f"y{n}", f"{n}.s") for n in loads)]
    pins = all_pins(placed_of(problem(syms, nets)))
    assert pins[("A", "n")][0] == pins[("X", "s")][0]


def _overlap(a: tuple[Any, Any], b: tuple[Any, Any]) -> bool:
    """Whether two axis-parallel segments lie on one line and share a stretch of positive length."""
    for axis in (0, 1):
        if len({a[0][axis], a[1][axis], b[0][axis], b[1][axis]}) == 1:
            (lo1, hi1), (lo2, hi2) = (sorted((s[0][1 - axis], s[1][1 - axis])) for s in (a, b))
            return bool(lo1 < hi2 and lo2 < hi1)
    return False


@pytest.mark.rule("PARALLEL-FIRST-PLUMB")
@pytest.mark.parametrize("loads", [("A", "B"), ("A", "B", "C")])
def test_the_plumbed_first_leg_of_a_fan_is_drawn_once(loads: tuple[str, ...]) -> None:
    """The box wire of the first leg is the fan's own drop: no two wires of the net run over one another."""
    syms = [box("X"), *(elem(n) for n in loads)]
    nets = [net("x", "X.s", *(f"{n}.n" for n in loads)), *(net(f"y{n}", f"{n}.s") for n in loads)]
    wires = [w.points for page in routed_of(problem(syms, nets)).pages for w in page.wires if w.net == "x"]
    segments = [(p, q) for pts in wires for p, q in pairwise(pts)]
    assert not [1 for a, b in combinations(segments, 2) if _overlap(a, b)]


def _supply_box() -> Any:
    """A box with pins p and m on its S edge."""
    area = Box(-16, -16, 32, 32)
    pins = (Pin("p", "S", -8, 16, 0), Pin("m", "N", 8, -16, 1))
    return replace(
        elem("X"), pins=pins, nodes=(("p",), ("m",)), views=views_of(area, area, area, pins, ("R0", "R180")), box=BoxSpec(("p", "m"), 16, 16)
    )


@pytest.mark.rule("PARALLEL-FIRST-PLUMB")
def test_a_plumbed_first_leg_whose_net_the_ring_cut_takes_goes_with_its_fan() -> None:
    """Catches a net cut out of its fan that leaves its first leg attached to the box pin, which closes the ring through the box."""
    syms = [_supply_box(), elem("A"), elem("B"), elem("C")]
    nets = [net("p", "X.p", "A.n", "B.n"), net("m", "A.s", "X.m", "C.n"), net("z", "B.s"), net("w", "C.s")]
    flow_of(problem(syms, nets))
