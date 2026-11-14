"""Stage 6: a bundle trunk is one line per lane, each of its own net and its own ends."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.outputs import Placed, Wire
from fransys_layout.core.route import through_bodies
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
            facts=Facts(far_ends=()),
        )
    )
    trunk = trunk_of(env, "f:n")
    (line,) = [w for w in trunk_wires(env, trunk).wires if w.kind == "trunk"]
    assert (line.net, line.lane) == ("n", None)


def _hits(env):
    """The finding codes the trunk's wires raise, once each."""
    return sorted({f.code for f in through_bodies(env, trunk_wires(env, env.trunks[0]).wires)})


def _with_body(env, box: Box):
    body = Placed("X", env.page, box.x, box.y, "R0", box, box, ())
    return replace(env, placed={**env.placed, "X": body})


def test_a_lane_line_through_a_footprint_is_a_warning_and_still_drawn() -> None:
    """RL-W1: a footprint on the line's y warns WIRE_THROUGH_BODY (R486); beside it none."""
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    env = replace(env, trunks=(replace(trunk, lane_ends=((100, 148),) * 3),))
    clear = _hits(_with_body(env, Box(110, trunk.y + 100, 8, 8)))
    assert clear == []
    hit = _hits(_with_body(env, Box(110, trunk.y - 4, 8, 8)))
    assert hit == ["WIRE_THROUGH_BODY"]
    margin = Placed("X", env.page, 110, trunk.y - 4, "R0", Box(110, trunk.y + 100, 8, 8), Box(110, trunk.y - 4, 8, 8), ())
    assert _hits(replace(env, placed={**env.placed, "X": margin})) == []  # R1146: a keep-out margin only is looks, not this error


def test_a_footprint_edge_on_the_line_is_a_hit() -> None:
    """Edges are closed (layout-0394): a body whose edge lies on the line's y is passed; a point touch at a lane end is looks (R1164)."""
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    env = replace(env, trunks=(replace(trunk, lane_ends=((100, 148),) * 3),))
    for box in (Box(110, trunk.y, 8, 8), Box(110, trunk.y - 8, 8, 8)):
        assert _hits(_with_body(env, box)) == ["WIRE_THROUGH_BODY"]
    assert _hits(_with_body(env, Box(148, trunk.y - 4, 8, 8))) == []


def test_the_fans_own_attached_symbol_on_the_line_is_not_a_hit() -> None:
    """R515: own = the symbols the fan attaches to; a foreign body on the same line is a hit."""
    xs = [100, 124, 148]
    env, trunk, _ = synthetic((0, 1, 2), xs, above=False)
    env = replace(env, trunks=(replace(trunk, lane_ends=((100, 148),) * 3),))
    box = Box(110, trunk.y, 8, 8)
    away = Box(110, trunk.y + 100, 8, 8)
    own = replace(env, placed={"K": Placed("K", env.page, box.x, box.y, "R0", away, box, ())})
    assert _hits(own) == []
    assert _hits(_with_body(own, box)) == ["WIRE_THROUGH_BODY"]
    # R533: the own exemption is the keep-out margin only; the own body on the line is hit
    on_the_line = replace(env, placed={"K": Placed("K", env.page, box.x, box.y, "R0", box, box, ())})
    assert _hits(on_the_line) == ["WIRE_THROUGH_BODY"]


def test_a_wire_of_any_kind_through_a_body_is_a_hit_not_only_a_trunk() -> None:
    """R1290 (iv), KI-626: a straight or join wire over a foreign body raises WIRE_THROUGH_BODY; beside it none."""
    env, _, _ = synthetic((0, 1, 2), [100, 124, 148], above=False)
    wall = _with_body(env, Box(110, 96, 8, 8))
    for kind in ("straight", "join"):
        run = Wire("n", env.page, ((100, 100), (148, 100)), kind)
        assert [f.code for f in through_bodies(wall, [run])] == ["WIRE_THROUGH_BODY"]
        assert through_bodies(env, [run]) == []
