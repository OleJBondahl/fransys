"""The motor feeder case at `solve` level: SW8 row P7.2, 13 references or fewer, crossings under 9.

The generic builder carries the family (bundles, pole lanes), so there is no family module
(el-0007). The case builds once for the module (BUILD-ONCE).
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _motor_feeder_case import motor_feeder_case_drafts
from conventions_fixtures import drawn_options, house
from fransys_el import symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve
from fransys_layout.core.score_wiring import crossing_points

if TYPE_CHECKING:
    from fransys_layout.core import Options, PlacementProblem
    from fransys_model.kernel import Model

MAX_REFERENCES = 13
CROSSINGS_BELOW = 9


@pytest.fixture(scope="module")
def model() -> Model:
    return fr.build(*motor_feeder_case_drafts()).model


@pytest.fixture(scope="module")
def chosen(model: Model, problem: PlacementProblem) -> Options:
    return drawn_options(model, symbol_kit(model, LIBRARY), problem, house())


def counts(problem: PlacementProblem, chosen: Options) -> tuple[int, int]:
    score = solve(problem, chosen).score
    assert score is not None
    return sum(n for _, n in score.R), score.X


def test_the_case_meets_the_study_counts_at_solve_level(problem: PlacementProblem, chosen: Options) -> None:
    refs, crossings = counts(problem, chosen)
    assert refs <= MAX_REFERENCES, (refs, crossings)
    assert crossings < CROSSINGS_BELOW, (refs, crossings)


def routed(problem: PlacementProblem, chosen: Options) -> list[Any]:
    layout = solve(problem, chosen)
    return [w for page in layout.routes.pages for w in page.wires]


def test_the_feeder_poles_form_bundles_of_one_lane_per_pole_and_one_trunk(
    problem: PlacementProblem,
    chosen: Options,
) -> None:
    members = defaultdict(list)
    for net in problem.nets:
        if net.bundle:
            members[net.bundle.id].append(net.bundle.pole)
    assert members
    assert all(sorted(poles) == [0, 1, 2] for poles in members.values()), members
    lines = [w for w in routed(problem, chosen) if w.lane is not None]
    assert sorted(w.lane for w in lines) == [0, 1, 2]
    assert len({w.net for w in lines}) == 3


def test_the_lanes_follow_the_box_pins_they_land_on_and_no_strand_crosses(
    problem: PlacementProblem,
    chosen: Options,
) -> None:
    """Per symbol the poles ascend with the pin offsets (layout-0264); no strand crosses."""
    dx = {(s.id, p.id): p.dx for s in problem.symbols for p in s.pins}
    bundle_of = {n.id: n.bundle.id for n in problem.nets if n.bundle}
    for bundle in set(bundle_of.values()):
        at = defaultdict(list)
        for net in (n for n in problem.nets if n.bundle and n.bundle.id == bundle):
            for pin in net.pins:
                at[pin.sym].append((net.bundle.pole if net.bundle else 0, dx[pin.sym, pin.pin]))
        for symbol, pairs in at.items():
            by_pole = [d for _, d in sorted(pairs)]
            assert by_pole == sorted(by_pole), (symbol, pairs)
    crossed = [c for c in crossing_points(routed(problem, chosen), bundle_of) if bundle_of.get(c[2]) and bundle_of.get(c[2]) == bundle_of.get(c[3])]
    assert crossed == []
