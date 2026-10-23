"""Stage 6: a bundle trunk is one line per lane, each of its own net and its own ends."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.outputs import Placed
from fransys_layout.core.route_trunk import trunk_wires
from fransys_layout.core.values import Box

from .cut_fixtures import AREA
from .flow_builders import net, poles
from .place_fixtures import bundle_fan
from .route_fixtures import envs_of
from .test_route_trunk import STEP, synthetic, trunk_of


def test_fan_nets_are_ordered_by_pole() -> None:
    """Lane j's net is fan.nets[j] whatever the order the nets are declared in."""

    prob = bundle_fan()
    shuffled = replace(prob, nets=tuple(reversed(prob.nets)))
    for p in (prob, shuffled):
        (env,) = envs_of(p)
        fan = env.fans["f:bd1"]
        assert fan.nets == ("bn0", "bn1", "bn2")
        by_pole = {n.bundle.pole: n.id for n in p.nets if n.bundle}
        assert fan.nets == tuple(by_pole[j] for j in range(3))


def test_a_three_lane_trunk_draws_three_lines_of_three_nets_with_their_own_ends() -> None:
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    ends = ((100, 148), (124, 148), None)
    env = replace(env, trunks=(replace(trunk, lane_ends=ends),))
    lines = [w for w in trunk_wires(env, env.trunks[0]).wires if w.kind == "trunk"]
    assert [(w.net, w.lane, w.points) for w in lines] == [
        ("L0", 0, ((100, trunk.y), (148, trunk.y))),
        ("L1", 1, ((124, trunk.y + STEP), (148, trunk.y + STEP))),
    ]


def test_a_lane_with_ends_on_one_x_draws_no_line() -> None:
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    ends = ((100, 100), (124, 148), (100, 148))
    env = replace(env, trunks=(replace(trunk, lane_ends=ends),))
    lines = [w for w in trunk_wires(env, env.trunks[0]).wires if w.kind == "trunk"]
    assert [w.net for w in lines] == ["L1", "L2"]


def test_a_single_lane_fan_is_one_plain_line() -> None:
    (env,) = envs_of(
        PlacementProblem(
            AREA,
            (poles("A", 1), poles("B", 1), poles("C", 1)),
            (net("n", "A.s0", "B.n0", "C.n0"),),
            facts=Facts(),
        )
    )
    trunk = trunk_of(env, "f:n")
    (line,) = [w for w in trunk_wires(env, trunk).wires if w.kind == "trunk"]
    assert (line.net, line.lane) == ("n", None)


def _with_body(env, box: Box):
    body = Placed("X", env.page, box.x, box.y, "R0", box, box, ())
    return replace(env, placed={**env.placed, "X": body})


def test_a_lane_line_through_a_footprint_is_a_warning_and_still_drawn() -> None:
    """RL-W1: a footprint on the line's y warns TRUNK_THROUGH_BODY (R486); beside it none."""
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    env = replace(env, trunks=(replace(trunk, lane_ends=((100, 148),) * 3),))
    clear = trunk_wires(_with_body(env, Box(110, trunk.y + 100, 8, 8)), env.trunks[0])
    assert [f.code for f in clear.findings] == []
    hit = trunk_wires(_with_body(env, Box(110, trunk.y - 4, 8, 8)), env.trunks[0])
    assert [f.code for f in hit.findings] == ["TRUNK_THROUGH_BODY"]
    assert hit.wires != ()
