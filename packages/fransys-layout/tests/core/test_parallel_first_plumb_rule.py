"""PARALLEL-FIRST-PLUMB: the first branch plumb under its predecessor, each next a pitch right."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from fransys_layout.core.series_values import Parallel, Series

from .flow_builders import OPTIONS, elem, net, problem
from .pipeline_fixtures import flow_of


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
