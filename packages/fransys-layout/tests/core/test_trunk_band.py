"""Stage 5, y: a foreign box meeting any lane of a trunk's band pushes the trunk, not lane 0 only.

Probe: restricting `_pushes` to the first lane segment makes the lane-2 test fail.
"""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core import place_foreign
from fransys_layout.core.clearance import Keep
from fransys_layout.core.constraints import Graph
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_foreign import _pushes, hard_order
from fransys_layout.core.place_lanes import lane_segments
from fransys_layout.core.place_levels import Span
from fransys_layout.core.place_trunk import trunk_node
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import place_y
from fransys_layout.core.values import Box

from .conftest import MARKER
from .pipeline_fixtures import cut_of
from .place_fixtures import bundle_fan


def _page(monkeypatch: pytest.MonkeyPatch, side: str, keep_of):
    """(env, x, y, span, trunk node, keep): `_foreign` returns the keep for the span's own row."""
    opts = core_options(
        marker=MARKER,
    )
    prob = bundle_fan()
    (env,) = page_envs(cut_of(prob, opts), prob, opts)
    x, _ = place_x(env)
    y, _ = place_y(env, x)
    (fan,) = [f for f in env.flow.fans if f.lanes == 3]
    row = next(r for r in range(len(env.plan.rows)) if lane_segments(env, x, fan, r)[0])
    segs = lane_segments(env, x, fan, row)
    ends = [s for s in segs if s]
    span = Span(fan.id, row, min(s[1] for s in ends), max(s[2] for s in ends), 3, side)
    trunk = trunk_node(fan.id, row)
    keep = keep_of(segs, y[trunk])
    own = [row]
    monkeypatch.setattr(place_foreign, "_foreign", lambda *a: iter([keep] if list(a[3]) == own else []))
    return env, x, y, span, trunk, keep


def _on_lane(j: int):
    def at(segs, ty):
        dy, x0, x1 = segs[j]
        return Keep("", Box(x0, ty + dy - 1, x1 - x0, 2), "footprint", "foreign")

    return at


def _across(segs, ty):
    """One keep tall enough to meet every lane."""
    (d0, x0, _), (d2, _, x1) = segs[0], segs[2]
    return Keep("", Box(x0, ty + d0 - 1, x1 - x0, d2 - d0 + 2), "footprint", "foreign")


def _away(segs, ty):
    dy, x0, x1 = segs[2]
    return Keep("", Box(x0, ty + dy + 20, x1 - x0, 2), "footprint", "foreign")


def _expected(side: str, trunk: str, keep: Keep, wire_dy: tuple[int, int]) -> tuple[str, str, int]:
    """The push that stands the lane line `wire` off the keep: the lane's own dy counts."""
    wire, dy = wire_dy
    if side == "above":
        return (trunk, "", wire - keep.box.y + dy)
    return ("", trunk, keep.box.y + keep.box.h + wire - dy)


@pytest.mark.rule("KEEP-OUT")
@pytest.mark.parametrize(
    ("keep_of", "needs"), [(_on_lane(0), (0, 0)), (_on_lane(2), (2, 2)), (_across, (2, 0))], ids=["lane 0", "lane 2", "every lane"]
)
@pytest.mark.parametrize("side", ["above", "below"])
def test_a_keep_under_any_one_lane_pushes_the_trunk(monkeypatch: pytest.MonkeyPatch, side: str, keep_of, needs) -> None:
    """The push counts the lane's own offset; a keep meeting several lanes is pushed for the lane that needs the most."""
    env, x, y, span, trunk, keep = _page(monkeypatch, side, keep_of)
    fan = next(f for f in env.flow.fans if f.lanes == 3)
    dy = lane_segments(env, x, fan, span.row)[needs[0] if side == "above" else needs[1]][0]
    assert _pushes(env, x, y, span, {}) == [_expected(side, trunk, keep, (env.options.wire_min, dy))]


@pytest.mark.parametrize("side", ["above", "below"])
def test_a_keep_that_touches_no_lane_gives_no_push(monkeypatch: pytest.MonkeyPatch, side: str) -> None:
    env, x, y, span, _, _ = _page(monkeypatch, side, _away)
    assert _pushes(env, x, y, span, {}) == []


@pytest.mark.rule("KEEP-OUT")
@pytest.mark.parametrize("side", ["above", "below"])
@pytest.mark.parametrize("held", ["below", "above"])
def test_the_hard_order_decides_the_side_of_the_push_not_the_trunks_side(monkeypatch: pytest.MonkeyPatch, side: str, held: str) -> None:
    """A box the base graph holds below the trunk is pushed under it, one held above is pushed over it, whatever the span's side (R1512).

    Probe: restoring the `span.side` direction in `_pushes` fails the held-below case on a `below` span: the push closes a ring.
    """
    env, x, y, span, trunk, keep = _page(monkeypatch, side, _on_lane(0))
    g = Graph()
    chain = (trunk, "mid", keep.node) if held == "below" else (keep.node, "mid", trunk)
    g.after(chain[0], chain[1], 8)
    g.after(chain[1], chain[2], 16)
    fan = next(f for f in env.flow.fans if f.lanes == 3)
    dy = next(seg for seg in lane_segments(env, x, fan, span.row) if seg)[0]
    trunk_above = held == "below"
    want = (
        (trunk, keep.node, env.options.wire_min - keep.box.y + dy)
        if trunk_above
        else (keep.node, trunk, keep.box.y + keep.box.h + env.options.wire_min - dy)
    )
    assert _pushes(env, x, y, span, hard_order(g, trunk)) == [want]
