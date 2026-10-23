"""The tree stage writes the hold of the cell after a parallel once: tallest part less the first."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core.pack import cell_node
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import place_y
from fransys_layout.core.series_values import Parallel, Series

from .flow_builders import elem, net, problem
from .pipeline_fixtures import flow_of
from .test_place_x import env_of

if TYPE_CHECKING:
    from fransys_layout.core.series_values import SeriesPart
    from fransys_layout.core.values import FlowGraph, PlacementProblem


def _circuit(first: SeriesPart, second: SeriesPart) -> PlacementProblem:
    """S1, (first || second), B; the branches are P1 and the two-pole P2a-P2b."""
    nets = [
        net("a", "S1.s", "P1.n", "P2a.n"),
        net("m", "P2a.s", "P2b.n"),
        net("b", "P1.s", "P2b.s", "B.n"),
    ]
    syms = [elem(n) for n in ("S1", "P1", "P2a", "P2b", "B")]
    prob = problem(syms, nets)
    tree = Series(("S1", Parallel((first, second)), "B"))
    return replace(prob, facts=replace(prob.facts, series=(tree,)))


def _holds(flow: FlowGraph) -> dict[str, int]:
    return {c.sym: c.hold for col in flow.columns for ln in col.lanes for c in ln.cells}


def test_the_cell_after_a_shorter_first_branch_holds_the_height_difference() -> None:
    """P1 is 32 G, P2a-P2b is 32 + 8 + 32 = 72: B holds 40."""
    flow = flow_of(_circuit("P1", Series(("P2a", "P2b"))))
    assert _holds(flow) == {"S1": 0, "P1": 0, "B": 40, "P2a": 0, "P2b": 0}
    assert [c.sym for c in flow.columns[0].lanes[0].cells] == [
        "S1",
        "P1",
        "B",
    ]  # source_first turned


def test_the_cell_after_a_tallest_first_branch_holds_nothing() -> None:
    flow = flow_of(_circuit(Series(("P2a", "P2b")), "P1"))
    assert _holds(flow) == {"S1": 0, "P2a": 0, "P2b": 0, "B": 0, "P1": 0}
    assert [c.sym for c in flow.columns[0].lanes[0].cells] == ["S1", "P2a", "P2b", "B"]


def _bottom_and_top(prob: PlacementProblem) -> tuple[int, int]:
    env = env_of(prob)
    x, _ = place_x(env)
    y, findings = place_y(env, x)
    assert findings == ()
    lanes = {tuple(c.sym for c in ln): i for i, ln in enumerate(env.pcs["c:S1"].lanes)}
    tall = lanes[("P2a", "P2b")]
    home = lanes[next(k for k in lanes if "B" in k)]
    fp = env.syms["P2b"].footprint
    bottom = y[cell_node("c:S1", tall, 1)] + fp.y + fp.h
    home_cells = env.pcs["c:S1"].lanes[home]
    top = y[cell_node("c:S1", home, len(home_cells) - 1)] + env.syms["B"].footprint.y
    return bottom, top


def test_the_cell_after_a_shorter_first_branch_stands_wire_min_below_the_tallest_branch() -> None:
    """The real y: B clears the two-pole branch by wire_min, not the one-pole branch."""
    prob = _circuit("P1", Series(("P2a", "P2b")))
    bottom, top = _bottom_and_top(prob)
    assert top - bottom >= env_of(prob).options.wire_min
