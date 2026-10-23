"""The motor feeder case at `solve` level: SW8 row P7.2, 13 references or fewer, crossings under 9.

The generic builder carries the family (bundles, pole lanes), so there is no family module
(el-0007). The case builds once for the module (BUILD-ONCE).
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve
from fransys_layout.core.score_wiring import crossing_points

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT / "tests") not in sys.path:
    # `--import-mode=importlib` never puts a folder on `sys.path`.
    sys.path.insert(0, str(_ROOT / "tests"))

from _motor_feeder_case import motor_feeder_case_drafts  # noqa: E402 -- after the path insert

if TYPE_CHECKING:
    from fransys_layout.core import PlacementProblem

MAX_REFERENCES = 13
CROSSINGS_BELOW = 9


@pytest.fixture(scope="module")
def problem() -> PlacementProblem:
    model = fr.build(*motor_feeder_case_drafts()).model
    built, _ = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    return built


def counts(problem: PlacementProblem) -> tuple[int, int]:
    score = solve(problem, options(house(), LIBRARY)).score
    assert score is not None
    return sum(n for _, n in score.R), score.X


def test_the_case_meets_the_study_counts_at_solve_level(problem: PlacementProblem) -> None:
    refs, crossings = counts(problem)
    assert refs <= MAX_REFERENCES, (refs, crossings)
    assert crossings < CROSSINGS_BELOW, (refs, crossings)


def routed(problem: PlacementProblem) -> list:
    layout = solve(problem, options(house(), LIBRARY))
    return [w for page in layout.routes.pages for w in page.wires]


def test_the_feeder_poles_form_bundles_of_one_lane_per_pole_and_one_trunk(
    problem: PlacementProblem,
) -> None:
    members = defaultdict(list)
    for net in problem.nets:
        if net.bundle:
            members[net.bundle.id].append(net.bundle.pole)
    assert members
    assert all(sorted(poles) == [0, 1, 2] for poles in members.values()), members
    trunks = [w for w in routed(problem) if w.lanes > 1]
    assert [w.lanes for w in trunks] == [3]


def test_the_lanes_follow_the_box_pins_they_land_on_and_no_strand_crosses(
    problem: PlacementProblem,
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
    crossed = [
        c
        for c in crossing_points(routed(problem))
        if bundle_of.get(c[2]) and bundle_of.get(c[2]) == bundle_of.get(c[3])
    ]
    assert crossed == []
