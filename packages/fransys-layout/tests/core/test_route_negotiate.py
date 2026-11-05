"""Negotiated routing (SPEC-022 C7, R606): soft rounds, history, and the final R391 check."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import PinRef
from fransys_layout.core.occupancy import Occupancy
from fransys_layout.core.outputs import Wire
from fransys_layout.core.route import _span, route_page
from fransys_layout.core.route_env import Rise
from fransys_layout.core.route_negotiate import _costliest, _crossed, _lift, negotiate

from .negotiate_fixtures import (
    WALL,
    Scene,
    seeded_page,
    seeded_scene,
    sequential_failures,
    wall_scene,
)

BLOCK = 689  # (the edge ring is hard, R1300) sequential routing fails two links; negotiating fails one
HISTORY = 985  # the history term saves a link that the soft price alone does not
STEP = 8


def _run(scene: Scene, **given: int):
    env, fresh = scene
    grid = fresh()
    env = replace(env, options=replace(env.options, **given))
    return grid, negotiate(env, grid, list(env.cross_links))


def test_links_that_block_each_other_lose_fewer_than_in_sequence() -> None:
    scene = seeded_scene(BLOCK)
    assert sequential_failures(scene) == 2
    grid, result = _run(scene)
    assert len(result.failed) == 1
    assert sum(grid.history.values()) > 0


def test_history_parts_links_that_the_price_alone_leaves_meeting() -> None:
    scene = seeded_scene(HISTORY)
    assert len(_run(scene, history_step=0)[1].failed) == 2
    grid, result = _run(scene)
    assert len(result.failed) == 1
    assert sum(grid.history.values()) > 0


def _one_gap() -> Scene:
    pins = {"a1": (24, 40, "E"), "a2": (200, 40, "W"), "b1": (24, 64, "E"), "b2": (200, 64, "W")}
    return wall_scene(pins, {"A": ("a1", "a2"), "B": ("b1", "b2")}, (5,))


def test_a_pair_with_no_legal_state_fails_the_last_and_keeps_the_other() -> None:
    grid, result = _run(_one_gap())
    assert result.failed == ("B",)
    assert list(result.routed) == ["A"]
    assert sum(grid.history.values()) > 0


def test_the_costliest_link_is_the_one_with_the_most_history() -> None:
    env, fresh = _one_gap()
    grid, result = _run((env, fresh))
    routed = [result.routed["A"], result.routed["A"]]
    assert _costliest(grid, [0, 1], routed) == 1
    cell = (WALL, 5)
    grid.add_history(cell, "h", 1_000)
    routed = [result.routed["A"], ()]
    assert _costliest(grid, [0, 1], routed) == 0


@pytest.mark.parametrize("seed", range(40))
def test_every_route_negotiate_returns_meets_no_net_against_r391(seed: int) -> None:
    env, fresh = seeded_scene(seed)
    grid, result = _run((env, fresh))
    assert grid.share_cost == 0
    for net, wires in result.routed.items():
        assert not [c for w in wires for c in grid.conflicts(net, w.points)]
    assert set(result.routed) | set(result.failed) == {ln.net for ln in env.cross_links}


def test_the_same_page_twice_gives_the_same_wires() -> None:
    assert _run(seeded_scene(BLOCK))[1] == _run(seeded_scene(BLOCK))[1]


def test_net_names_in_another_order_give_the_same_wires_up_to_the_rename() -> None:
    plain = _run(seeded_scene(BLOCK))[1]
    names = {"n0": "z9", "n1": "a1", "n2": "m5"}
    again = _run(seeded_scene(BLOCK, names))[1]
    assert list(again.routed) == [names[n] for n in plain.routed]
    assert [[w.points for w in ws] for ws in plain.routed.values()] == [[w.points for w in ws] for ws in again.routed.values()]


REPAIR = 664  # the check fails two links on the settled map; one alone and hard finds a route there, one has none


def test_a_link_the_check_failed_is_routed_alone_on_the_settled_map() -> None:
    env, fresh = seeded_scene(REPAIR)
    grid, result = _run((env, fresh))
    assert len(result.failed) == 1
    assert set(result.routed) | set(result.failed) == {ln.net for ln in env.cross_links}
    for net, wires in result.routed.items():
        assert not [c for w in wires for c in grid.conflicts(net, w.points)]


def test_route_page_negotiates_what_the_sequential_driver_gave_up_on() -> None:
    _, refused, findings = route_page(seeded_page(BLOCK))
    assert sequential_failures(seeded_scene(BLOCK)) == 2
    assert len(refused) == 1
    assert [f for f in findings if f.code != "WIRE_THROUGH_BODY"] == []  # the seeded scene has no net pins, so its own wires touch their own boxes
    assert refused[0].ends is not None
    assert len(refused[0].ends) == 2


def test_lifting_a_rise_takes_its_own_wire_off_and_leaves_the_trunk_of_its_net() -> None:
    grid = Occupancy(8, 6, STEP)
    trunk = Wire("T", 1, ((0, 8), (56, 8)), "routed")
    rise = Wire("T", 1, ((24, 8), (24, 40)), "routed")
    for w in (trunk, rise):
        grid.mark_wire(w.net, w.points)
    _lift(grid, Rise("T", PinRef("s", "1"), (24, 40), (24, 8), "routed"), (rise,))
    assert (3, 3) not in grid.used
    assert (3, 1) in grid.used
    assert (5, 1) in grid.used


def _crossings(seed: int, ripup_worst: int) -> int:
    env, fresh = seeded_scene(seed)
    grid, result = _run((env, fresh), ripup_worst=ripup_worst)
    return sum(len(_crossed(grid, net, wires)) for net, wires in result.routed.items())


@pytest.mark.parametrize("seed", [10, 88])
def test_ripup_worst_lays_the_most_crossing_links_alone_again_and_crosses_less(seed: int) -> None:
    """R664: with `ripup_worst` 0 the settled routes cross; with 3 the worst crossers are laid again, hard, and part."""
    assert _crossings(seed, 0) > 0
    assert _crossings(seed, 3) == 0


def test_a_ripup_never_adds_a_crossing() -> None:
    for seed in range(40):
        assert _crossings(seed, 3) <= _crossings(seed, 0)


def test_the_lay_order_is_the_half_perimeter_of_the_pins_shortest_first() -> None:
    env, _ = seeded_scene(5)
    spans = {ln.net: _span(env, ln) for ln in env.cross_links}
    assert spans == {"n0": 144, "n1": 96, "n2": 88}
    assert [ln.net for ln in sorted(env.cross_links, key=lambda ln: _span(env, ln))] == ["n2", "n1", "n0"]
