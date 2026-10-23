"""Each further branch of a parallel stands parallel_pitch right of the one before, or further."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core.series_values import Parallel, Series

from .flow_builders import OPTIONS, elem, net, problem
from .pipeline_fixtures import flow_of

if TYPE_CHECKING:
    from fransys_layout.core.values import PlacementProblem


def _branches(count: int, widths: dict[str, int]) -> PlacementProblem:
    """S1, (P1 || P2 || ...), B: one pole per branch."""
    names = [f"P{i}" for i in range(1, count + 1)]
    nets = [
        net("a", "S1.s", *(f"{n}.n" for n in names)),
        net("b", *(f"{n}.s" for n in names), "B.n"),
    ]
    syms = [elem(n, widths.get(n, 16)) for n in ("S1", *names, "B")]
    prob = problem(syms, nets)
    tree = Series(("S1", Parallel(tuple(names)), "B"))
    return replace(prob, facts=replace(prob.facts, series=(tree,)))


def _offsets(prob: PlacementProblem) -> list[int]:
    return [ln.offset for ln in flow_of(prob).columns[0].lanes]


def test_the_second_branch_stands_a_pitch_right_of_the_first_when_the_edge_rule_is_smaller() -> (
    None
):
    """Edge rule: 8 half-width + 8 gap + 8 own half-width = 24, under the 48 pitch."""
    assert OPTIONS.parallel_pitch == 48
    assert _offsets(_branches(2, {})) == [0, 48]


def test_the_third_branch_stands_a_pitch_right_of_the_second() -> None:
    assert _offsets(_branches(3, {})) == [0, 48, 96]


def test_the_edge_rule_wins_when_the_branch_before_is_wider_than_the_pitch() -> None:
    """P2 is 80 wide, at 56: P3 clears 56 + 40 + 8 + 8 = 112, past 56 + 48 = 104."""
    assert _offsets(_branches(3, {"P2": 80})) == [0, 56, 112]
