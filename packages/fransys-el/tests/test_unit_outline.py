"""The unit-with-outline case at solve level (SW8 row P7.4, el-0009): no facade, no markers.

The generic builder carries the family: `Facts.units` holds the unit, `Net.crosses_unit` is set,
so every crossing net ends in a stub at the unit's boundary pins and the unit's terminals stand
"""

from dataclasses import replace
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _unit_outline_case import TERMINALS, unit_outline_case_drafts
from conventions_fixtures import drawn_options, house, unwired
from fransys_el import symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, Options, PlacementProblem
    from fransys_model.kernel import Model


def _terms(layout: CoreLayout, which: str) -> dict[str, int]:
    assert layout.score is not None
    return dict(layout.score.P if which == "P" else layout.score.R)


def _layout(problem: PlacementProblem, chosen: Options) -> CoreLayout:
    return solve(problem, chosen)


@pytest.fixture(scope="module")
def model() -> Model:
    return fr.build(*unit_outline_case_drafts()).model


@pytest.fixture(scope="module")
def chosen(model: Model, problem: PlacementProblem) -> Options:
    return drawn_options(model, symbol_kit(model, LIBRARY), problem, house())


@pytest.fixture(scope="module")
def layout(problem: PlacementProblem, chosen: Options) -> CoreLayout:
    return _layout(problem, chosen)


def test_every_net_crosses_the_one_unit(problem: PlacementProblem) -> None:
    assert [u.parent for u in problem.facts.units] == [None]
    assert len(problem.nets) == TERMINALS
    assert all(n.crosses_unit for n in problem.nets)


def test_each_crossing_net_with_no_wire_drawn_ends_in_two_stubs(problem: PlacementProblem, chosen: Options) -> None:
    """R407 where no wire is drawn: with no far end given, every net stubs at both pins."""
    bare = unwired(problem)
    layout = _layout(bare, chosen)
    unplaced = sum(f.code == "MARKER_UNPLACED" for f in layout.findings)
    assert dict(_terms(layout, "R"))["stub"] > 0, "R920: a stub on a fixed lead steps straight out, so it stands"
    assert dict(_terms(layout, "R"))["stub"] + unplaced == 2 * TERMINALS


def test_a_crossing_net_drawn_to_its_far_end_on_the_page_ends_in_no_stub(problem: PlacementProblem, layout: CoreLayout) -> None:
    """MARKER-FREE-SIDE: the wire is the reference; the case has far ends, and no stub stands."""
    assert problem.facts.far_ends
    assert "stub" not in dict(_terms(layout, "R"))
    assert any(page.wires for page in layout.routes.pages)


def test_the_unit_terminals_stand_on_their_column(layout: CoreLayout) -> None:
    got = _terms(layout, "P")
    assert (got["junction_off_line"], got["loose"]) == (0, 0), got


def test_without_crosses_unit_the_stubs_are_gone(problem: PlacementProblem, chosen: Options) -> None:
    """Planted: the family fact off gives no stub, so the stub count above can fail."""
    plain = replace(problem, nets=tuple(replace(n, crosses_unit=False) for n in problem.nets))
    assert "stub" not in dict(_terms(_layout(plain, chosen), "R"))


def test_terminals_off_their_column_are_counted(problem: PlacementProblem, chosen: Options, monkeypatch: pytest.MonkeyPatch) -> None:
    """Planted: with no straight vertical wire anywhere, the terminals fall off, so 0 can fail."""
    monkeypatch.setattr("fransys_layout.core.score_placement._straight", lambda _scene: set())
    assert _terms(_layout(problem, chosen), "P")["junction_off_line"] > 0
