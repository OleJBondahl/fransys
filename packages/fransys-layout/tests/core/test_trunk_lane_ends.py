"""Trunk.lane_ends: each lane's first and last tap, the hull of its own poles' attachments."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from fransys_layout.core import PinRef
from fransys_layout.core.clearance import Keep
from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.outputs import PinXY, Placed
from fransys_layout.core.place_lanes import Stand, _lane_ends, taps_x
from fransys_layout.core.values import Box

from .place_fixtures import bundle_fan, walk_stand
from .route_fixtures import envs_of


def _ends(*args, **kwargs):
    """The drawn (x0, x1) of each lane: `_lane_ends` less its stands."""
    return _lane_ends(*args, **kwargs).ends


def tap(pole: int, x: int) -> tuple[Attach, int]:
    return Attach("c", 0, 0, PinRef("S", f"p{pole}_{x}"), pole, net="n"), x


def fan_of(lanes: int) -> Fan:
    return Fan("f", tuple("LMN"[:lanes]), (), (), None, lanes, "below")


def test_each_lane_ends_at_its_own_first_and_last_tap() -> None:
    taps = [tap(0, 6), tap(0, 6), tap(0, 20), tap(1, 8), tap(1, 30), tap(2, 10), tap(2, 40)]
    ends = _ends(fan_of(3), taps)
    assert ends == ((6, 20), (8, 30), (10, 40))
    assert (min(v for _, v in taps), max(v for _, v in taps)) == (6, 40)


def test_a_lane_with_no_tap_in_the_row_has_no_ends() -> None:
    assert _ends(fan_of(3), [tap(0, 6), tap(2, 40)]) == ((6, 6), None, (40, 40))


def test_a_plain_fan_has_one_pair_equal_to_the_hull() -> None:
    taps = [tap(0, 9), tap(1, 3), tap(0, 50)]
    assert _ends(fan_of(1), taps) == ((3, 50),)
    stepped = Stand(3, poles=(frozenset(), frozenset({0})), legs=6)  # an arrow with legs steps out by their reach and a grid
    assert _ends(fan_of(1), taps, {0}, (0, 1), stepped) == ((3, 59),)
    assert _ends(fan_of(1), taps, {0}, (0, 1), stepped._replace(legs=0)) == ((3, 50),)
    assert _ends(fan_of(1), taps, {0}, (0, 1), stepped._replace(right=55)) == ((3, 53),)  # R1010: never past the content box
    assert _ends(fan_of(1), taps, {0}, (0, 1), stepped._replace(right=40)) == ((3, 50),)  # a hull already past it stays


def test_a_placed_bundle_trunk_holds_one_entry_per_lane_inside_its_hull() -> None:
    (env,) = envs_of(bundle_fan())
    (trunk,) = [t for t in env.trunks if t.lanes == 3]
    assert len(trunk.lane_ends) == 3
    pairs = [e for e in trunk.lane_ends if e is not None]
    assert pairs
    assert min(a for a, _ in pairs) == trunk.x0
    assert max(b for _, b in pairs) == trunk.x1


def test_a_lane_whose_net_continues_runs_on_to_the_arrow_end_and_a_branching_lane_stops() -> None:
    taps = [tap(0, 6), tap(0, 20), tap(1, 8), tap(1, 30), tap(2, 10), tap(2, 40)]
    right = _ends(fan_of(3), taps, {0, 1}, (0, 1), Stand(3, poles=(frozenset(), frozenset({0, 1}))))
    assert right == ((6, 46), (8, 46), (10, 40))
    both = _ends(fan_of(3), taps, {1}, (1, 1), Stand(3, poles=(frozenset({1}), frozenset({1}))))
    assert both == ((6, 20), (0, 46), (10, 40))
    stepped = _ends(fan_of(3), taps, {0, 1}, (0, 1), Stand(3, poles=(frozenset(), frozenset({0})), legs=3))
    assert stepped == ((6, 49), (8, 30), (10, 40))
    left = _ends(fan_of(3), taps, {0, 1}, (1, 0), Stand(3, poles=(frozenset({0}), frozenset()), legs=3))
    assert left == ((0, 20), (8, 30), (10, 40))
    assert _ends(fan_of(3), taps, {0, 1}, (0, 0)) == ((6, 20), (8, 30), (10, 40))


def test_an_arrowed_end_moves_out_only_past_the_footprint_its_marker_hits() -> None:
    poles = (frozenset(), frozenset({0}))
    near, far = Keep("", Box(18, -10, 20, 20), "footprint", "S"), Keep("", Box(60, -10, 20, 20), "footprint", "S")
    taps = [tap(0, 6), tap(0, 20)]
    assert _ends(fan_of(1), taps, stand=walk_stand(3, 0, (far,), poles)) == ((6, 20),)
    assert _ends(fan_of(1), taps, stand=walk_stand(3, 0, (far, near), poles)) == ((6, 39),)  # R906: the next grid line, the closed edge being a hit
    assert _ends(fan_of(1), taps, stand=walk_stand(3, 0, (near,), (poles[1], poles[0]))) == ((6, 20),)


def test_an_arrowed_end_is_reachable_along_clear_track_or_stays_at_its_own_symbols() -> None:
    poles = (frozenset(), frozenset({0}))
    own, foreign = Keep("", Box(18, -10, 20, 20), "footprint", "S"), Keep("", Box(40, -10, 20, 20), "footprint", "T")
    taps = [tap(0, 6), tap(0, 20)]
    stand = walk_stand(3, 0, (own, foreign), poles)
    assert _ends(fan_of(1), taps, stand=stand) == ((6, 20),)  # R936: no end past foreign T; the end stays at S
    assert _ends(fan_of(1), taps, stand=stand._replace(keeps=(own,))) == ((6, 39),)
    from .pipeline_fixtures import solved_of
    from .test_trunk_tracks import wrapped_box_fans

    codes = {f.code for f in solved_of(wrapped_box_fans(10, 300)).findings}
    assert codes & {"WIDER_THAN_PAGE", "OVERLAP"}  # R938: the overfull fixture's fallback is never silent


def test_a_lane_of_a_bundle_stops_its_arrow_step_out_at_the_content_box() -> None:
    taps = [tap(0, 6), tap(0, 50), tap(1, 8), tap(1, 30)]
    stepped = Stand(3, poles=(frozenset(), frozenset({0})), legs=40)
    assert _ends(fan_of(2), taps, {0, 1}, (0, 1), stepped) == ((6, 96), (8, 30))
    assert _ends(fan_of(2), taps, {0, 1}, (0, 1), stepped._replace(right=70))[0] == (6, 68)  # R1010: the last grid step inside it


def test_an_arrowed_end_steps_off_a_foreign_attachment_column() -> None:
    poles = (frozenset(), frozenset({0}))
    column, taps = Keep("", Box(24, -10, 0, 20), "wire", "T"), [tap(0, 6), tap(0, 20)]
    assert _ends(fan_of(1), taps, stand=walk_stand(3, 0, (), poles)) == ((6, 20),)
    assert _ends(fan_of(1), taps, stand=walk_stand(3, 0, (column,), poles)) == ((6, 27),)  # R1023: crossed by the track, cleared by the marker


def test_an_arrowed_end_does_not_walk_past_a_foreign_column_that_ends_on_its_line() -> None:
    poles = (frozenset(), frozenset({0}))
    ends_on_line = Keep("", Box(24, -10, 0, 10), "wire", "T")  # a T, not a right-angle crossing: the end stays at its own symbols
    assert _ends(fan_of(1), [tap(0, 6), tap(0, 20)], stand=walk_stand(3, 0, (ends_on_line,), poles)) == ((6, 20),)


def test_a_placed_symbol_without_the_attached_pin_raises() -> None:
    env: Any = SimpleNamespace(pcs={"c": SimpleNamespace(row=0)})
    fan = replace(fan_of(1), drivers=(tap(0, 6)[0],))
    box = Box(0, 0, 4, 4)
    placed = {"S": Placed("S", 1, 0, 0, "R0", box, box, (PinXY("p0_6", 6, 3),))}
    assert taps_x(env, {}, fan, 0, placed) == ((fan.drivers[0], 6, 3),)
    with pytest.raises(CoreError, match="S lacks pin p0_6"):
        taps_x(env, {}, fan, 0, {"S": replace(placed["S"], pin_xy=())})


def test_a_lane_walks_on_its_band_row_not_its_index_when_its_run_is_reversed() -> None:
    """R1338 G1: lane 0 ends on lane 1's start, so it stands on row 1 (`lane_rows`); the walk tests that y, not lane 0's."""
    poles = (frozenset(), frozenset({0}))
    foot = Keep("", Box(22, 5, 10, 10), "footprint", "T")  # meets a marker at y 3, not one at y 0
    assert _ends(fan_of(2), [tap(0, 6), tap(0, 20), tap(1, 20), tap(1, 40)], (), (0, 0), walk_stand(3, 0, (foot,), poles)) == (
        (6, 33),
        (20, 40),
    )


@pytest.mark.rule("BUNDLE-LANE-END")
@pytest.mark.parametrize("area", [24, 40, 64, 200])
@pytest.mark.parametrize("lanes", [1, 2])
def test_no_lane_end_lies_past_its_last_tap_without_a_standing_arrow(area: int, lanes: int) -> None:
    """R1488: wherever the arrow of a lane end found no stand, the lane ends at its own last tap, whatever the content box and the keeps."""
    from fransys_layout.core import Size
    from fransys_layout.core.stand_fit import Limits

    taps = [tap(0, 6), tap(0, 20), tap(1, 8), tap(1, 30)][: 2 * lanes]
    keeps = (Keep("", Box(22, -10, 30, 20), "footprint", "S"), Keep("", Box(2, -10, 4, 20), "footprint", "S"))
    stand = walk_stand(3, 0, keeps, (frozenset({0}), frozenset({0})), limits=Limits(Size(area, 100)))
    got = _lane_ends(fan_of(lanes), taps, {0, 1}, (1, 1), stand)
    hull = {j: (min(v for a, v in taps if a.pole == j), max(v for a, v in taps if a.pole == j)) for j in range(lanes)}
    for j, (end, stood) in enumerate(zip(got.ends, got.stood, strict=True)):
        assert end is not None
        assert stood[0] or end[0] == hull[j][0], (j, end, stood)
        assert stood[1] or end[1] == hull[j][1], (j, end, stood)
    assert not all(all(s) for s in got.stood) or area == 200  # a narrow content box leaves an arrow with no stand


def test_a_lane_steps_out_past_its_hull_only_if_its_pole_belongs_to_the_cut_end() -> None:
    """R1676: a continuing lane that is no pole of the cut end stops at its last attachment."""
    taps = [tap(0, 6), tap(0, 20), tap(1, 8), tap(1, 30)]
    stand = Stand(3, poles=(frozenset(), frozenset({0})))
    assert _ends(fan_of(2), taps, {0, 1}, (0, 1), stand) == ((6, 36), (8, 30))


def test_a_continuing_lane_runs_to_the_marker_lane_x_and_a_branch_only_lane_stops_at_its_last_attachment() -> None:
    """R1676, R1682: of the lanes besides the marker's, only a pole of its cut end is levelled to its x; the third lane stops at its tap."""
    taps = [tap(0, 6), tap(0, 20), tap(1, 8), tap(1, 30), tap(2, 10), tap(2, 40)]
    stand = Stand(3, poles=(frozenset(), frozenset({0, 1})), leads=(frozenset(), frozenset({0})))
    assert _ends(fan_of(3), taps, {0, 1, 2}, (0, 1), stand) == ((6, 46), (8, 46), (10, 40))
