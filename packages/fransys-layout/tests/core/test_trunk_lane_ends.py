"""Trunk.lane_ends: each lane's first and last tap, the hull of its own poles' attachments."""

from __future__ import annotations

from fransys_layout.core import PinRef
from fransys_layout.core.place_assemble import _lane_ends
from fransys_layout.core.values import Attach, Fan

from .place_fixtures import bundle_fan
from .route_fixtures import envs_of


def tap(pole: int, x: int) -> tuple[Attach, int]:
    return Attach("c", 0, 0, PinRef("S", f"p{pole}_{x}"), pole, net="n"), x


def fan_of(lanes: int) -> Fan:
    return Fan("f", tuple("LMN"[:lanes]), (), (), None, lanes, "below")


def test_each_lane_ends_at_its_own_first_and_last_tap() -> None:
    taps = [tap(0, 6), tap(0, 6), tap(0, 20), tap(1, 8), tap(1, 30), tap(2, 10), tap(2, 40)]
    ends = _lane_ends(fan_of(3), taps)
    assert ends == ((6, 20), (8, 30), (10, 40))
    assert (min(v for _, v in taps), max(v for _, v in taps)) == (6, 40)


def test_a_lane_with_no_tap_in_the_row_has_no_ends() -> None:
    assert _lane_ends(fan_of(3), [tap(0, 6), tap(2, 40)]) == ((6, 6), None, (40, 40))


def test_a_plain_fan_has_one_pair_equal_to_the_hull() -> None:
    taps = [tap(0, 9), tap(1, 3), tap(0, 50)]
    assert _lane_ends(fan_of(1), taps) == ((3, 50),)


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
    right = _lane_ends(fan_of(3), taps, {0, 1}, (0, 1), 3)
    assert right == ((6, 43), (8, 43), (10, 40))
    both = _lane_ends(fan_of(3), taps, {1}, (1, 1), 3)
    assert both == ((6, 20), (3, 43), (10, 40))
    assert _lane_ends(fan_of(3), taps, {0, 1}, (0, 0)) == ((6, 20), (8, 30), (10, 40))
