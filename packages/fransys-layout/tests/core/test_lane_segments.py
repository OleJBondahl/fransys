"""lane_segments: each lane (dy, x0, x1) in the x phase; `continuing` has one home."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import place_assemble
from fransys_layout.core.arrow_reserve import reserve
from fransys_layout.core.band import lane_offset
from fransys_layout.core.place_assemble import assemble
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_lanes import continuing, drawn_lane_ends, lane_segments, page_syms
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import place_y
from fransys_layout.core.values import Ref, RefEnd, RefKind, StandClass

from .conftest import MARKER
from .pipeline_fixtures import cut_of
from .place_fixtures import bundle_fan

if TYPE_CHECKING:
    import pytest

    from fransys_layout.core.flow_values import Fan
    from fransys_layout.core.outputs import PagePlacement
    from fransys_layout.core.place_env import PageEnv


def _page() -> tuple[PageEnv, dict[str, int], PagePlacement, Fan]:
    opts = core_options(
        marker=MARKER,
    )
    prob = bundle_fan()
    (env,) = page_envs(cut_of(prob, opts), prob, opts)
    x, _ = place_x(env)
    y, _ = place_y(env, x)
    page = assemble(env, x, y)
    (fan,) = [f for f in env.flow.fans if f.lanes == 3]
    return env, x, page, fan


def _row(page: PagePlacement, fan: Fan) -> int:
    (trunk,) = [t for t in page.trunks if t.fan == fan.id]
    return trunk.row


def test_a_lane_equals_the_trunk_lane_end_when_no_arrow_is_planned() -> None:
    env, x, page, fan = _page()
    (trunk,) = [t for t in page.trunks if t.fan == fan.id]
    segs = lane_segments(env, x, fan, trunk.row)
    grid = env.options.wiring_grid
    assert [(s[1], s[2]) if s else None for s in segs] == list(trunk.lane_ends)
    assert [s[0] for s in segs if s] == [lane_offset(j, grid) for j in range(3)]


def test_an_arrow_end_of_a_continuing_lane_grows_by_the_marker_width() -> None:
    env, x, page, fan = _page()
    r = _row(page, fan)
    plain = replace(fan, lanes=1)
    ref = Ref(fan.id, RefKind.ARROW, (RefEnd(env.plan.page, None, None, r), RefEnd(-1, None, None)))
    (bare,) = lane_segments(env, x, plain, r)
    (wide,) = lane_segments(replace(env, refs=(ref,)), x, plain, r)
    assert bare
    assert wide == (0, bare[1], bare[2] + reserve(1, env.options))
    assert reserve(1, env.options) > 0


def test_a_lane_with_no_taps_is_none() -> None:
    env, x, page, fan = _page()
    segs = lane_segments(env, x, replace(fan, lanes=4), _row(page, fan))
    assert segs[3] is None
    assert all(s is not None for s in segs[:3])


def test_continuing_is_the_same_for_the_page_symbols_and_the_placed_symbols() -> None:
    env, _, page, fan = _page()
    placed = {p.sym: p for p in page.placed}
    assert page_syms(env) == frozenset(placed)
    assert continuing(fan, page_syms(env)) == continuing(fan, placed) == frozenset()
    assert continuing(fan, set()) == {a.pole for a in (*fan.drivers, *fan.legs)}


def test_a_bundles_cross_document_stub_runs_every_lane_past_its_last_tap() -> None:
    """R1338: the stub stands for every pole, so each lane runs to the cut end (BUNDLE-LANE-END) and grows by the marker width."""
    env, x, page, fan = _page()
    r = _row(page, fan)
    (bare,) = [t.lane_ends for t in page.trunks if t.fan == fan.id]
    first, *rest = (a.pin for a in (*fan.drivers, *fan.legs))
    stub = Ref(fan.nets[0], RefKind.STUB, (RefEnd(env.plan.page, None, first, None, StandClass.TRUNK_END, tuple(rest)),))
    segs = lane_segments(replace(env, refs=(stub,)), x, fan, r)
    ends = drawn_lane_ends(replace(env, refs=(stub,)), x, fan, r).ends
    assert all(e and b and e[1] > b[1] for e, b in zip(ends, bare, strict=True))
    assert len({e[1] for e in ends if e}) == 1  # R1351: the lanes that are not the marker lane end at its x
    assert [s[2] - e[1] for s, e in zip(segs, ends, strict=True) if s and e] == [reserve(1, env.options)] * 3


def test_an_arrow_stands_a_pitch_past_the_last_placed_leg_drop_not_past_the_estimate(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUNDLE-LEGS: a leg pushed right of its estimate (a y-collision) keeps its arrow's box after the leg's drop."""
    env, x, page, fan = _page()
    r = _row(page, fan)
    pin = fan.legs[0].pin if fan.legs else fan.drivers[0].pin
    arrow = Ref(fan.id, RefKind.ARROW, (RefEnd(env.plan.page, None, pin, r), RefEnd(-1, None, None)))
    leg = Ref(fan.nets[0], RefKind.STUB, (RefEnd(env.plan.page, None, pin, r, StandClass.LEG),))
    env = replace(env, refs=(arrow, leg))
    (bare,) = [t for t in assemble(env, x, place_y(env, x)[0]).trunks if t.fan == fan.id]
    drop = max(e[1] for e in bare.lane_ends if e) + 5 * env.options.wiring_grid
    line = ((0, 0), (drop, 0), (drop, 1))
    monkeypatch.setattr(place_assemble, "leg_lines", lambda *_: {(fan.id, r, pin): line}, raising=False)
    (pushed,) = [t for t in assemble(env, x, place_y(env, x)[0]).trunks if t.fan == fan.id]
    assert max(e[1] for e in pushed.lane_ends if e) >= drop + env.options.wiring_grid
