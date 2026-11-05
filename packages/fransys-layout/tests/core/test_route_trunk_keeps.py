"""route_trunk reads the one keep set, `hard_keeps`: bodies, never the soft footprint room (layout-0495, R1239)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fransys_layout.core import Box
from fransys_layout.core.clearance import Keep, pin_points, through
from fransys_layout.core.outputs import PinXY, Placed
from fransys_layout.core.route_env import hard_keeps


def _placed(sym: str, body: Box, foot: Box) -> Placed:
    return Placed(sym, 1, 0, 0, "R0", body, foot, ())


ENV: Any = SimpleNamespace(
    placed={
        "A": _placed("A", Box(0, 0, 10, 10), Box(-4, -4, 18, 18)),
        "B": _placed("B", Box(100, 0, 10, 10), Box(96, -4, 18, 18)),
    },
    obstacles=(),
)


def _bodies_hit(env: Any, own: frozenset[str], xs: tuple[int, int], ys: tuple[int, int]) -> tuple[str, ...]:
    probe = Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    return tuple(dict.fromkeys(k.owner for k in through(probe, hard_keeps(env), (), own, pin_points(env.placed))))


def test_a_probe_in_a_foreign_footprint_but_off_its_body_hits_nothing() -> None:
    assert _bodies_hit(ENV, frozenset(), (-3, -3), (0, 5)) == ()


def test_the_own_body_still_counts() -> None:
    assert _bodies_hit(ENV, frozenset({"A"}), (5, 5), (0, 5)) == ("A",)
    assert _bodies_hit(ENV, frozenset(), (5, 5), (0, 5)) == ("A",)


def test_the_keep_set_is_the_bodies_and_the_obstacles() -> None:
    marker = Keep("", Box(50, 0, 4, 4), "marker", "M")
    env: Any = SimpleNamespace(placed=ENV.placed, obstacles=(marker,))
    assert [(k.owner, k.box, k.kind) for k in hard_keeps(env)] == [
        ("A", Box(0, 0, 10, 10), "body"),
        ("B", Box(100, 0, 10, 10), "body"),
        ("M", Box(50, 0, 4, 4), "marker"),
    ]


def test_the_merged_set_carries_the_pin_points_a_run_may_end_on() -> None:
    """R1239: a run along a body's edge that ends at the body's own pin is no hit; without the pin points it is."""
    placed = {"A": Placed("A", 1, 0, 0, "R0", Box(0, 0, 10, 10), Box(-4, -4, 18, 18), (PinXY("1", 0, 10),))}
    env: Any = SimpleNamespace(placed=placed, obstacles=())
    probe = Box(0, 4, 0, 6)  # the left edge, from y 4 to the pin at y 10
    assert through(probe, hard_keeps(env), ((0, 10),), frozenset(), pin_points(env.placed)) == ()
    assert [k.owner for k in through(probe, hard_keeps(env), ((0, 10),), frozenset(), {})] == ["A"]
