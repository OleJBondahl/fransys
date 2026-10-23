"""The unit-with-outline case at solve level (SW8 row P7.4, el-0009): no facade, no markers.

The generic builder carries the family: `Facts.units` holds the unit, `Net.crosses_unit` is set,
so every crossing net ends in a stub at the unit's boundary pins and the unit's terminals stand
on their column. The case builds once for the module.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _unit_outline_case import TERMINALS, unit_outline_case_drafts
from conventions_fixtures import house
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, PlacementProblem


def _terms(layout: CoreLayout, which: str) -> dict[str, int]:
    assert layout.score is not None
    return dict(layout.score.P if which == "P" else layout.score.R)


def _layout(problem: PlacementProblem) -> CoreLayout:
    return solve(problem, options(house(), LIBRARY))


@pytest.fixture(scope="module")
def problem() -> PlacementProblem:
    model = fr.build(*unit_outline_case_drafts()).model
    built, _ = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    return built


@pytest.fixture(scope="module")
def layout(problem: PlacementProblem) -> CoreLayout:
    return _layout(problem)


def test_every_net_crosses_the_one_unit(problem: PlacementProblem) -> None:
    assert [u.parent for u in problem.facts.units] == [None]
    assert len(problem.nets) == TERMINALS
    assert all(n.crosses_unit for n in problem.nets)


def test_each_crossing_net_ends_in_two_stubs(layout: CoreLayout) -> None:
    assert dict(_terms(layout, "R")) == {"stub": 2 * TERMINALS}


def test_the_unit_terminals_stand_on_their_column(layout: CoreLayout) -> None:
    got = _terms(layout, "P")
    assert (got["junction_off_line"], got["loose"]) == (0, 0), got


def test_without_crosses_unit_the_stubs_are_gone(problem: PlacementProblem) -> None:
    """Planted: the family fact off gives no stub, so the stub count above can fail."""
    plain = replace(problem, nets=tuple(replace(n, crosses_unit=False) for n in problem.nets))
    assert "stub" not in dict(_terms(_layout(plain), "R"))


def test_terminals_off_their_column_are_counted(
    problem: PlacementProblem, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Planted: with no straight vertical wire anywhere, the terminals fall off, so 0 can fail."""
    monkeypatch.setattr("fransys_layout.core.score_placement._straight", lambda _scene: set())
    assert _terms(_layout(problem), "P")["junction_off_line"] > 0
