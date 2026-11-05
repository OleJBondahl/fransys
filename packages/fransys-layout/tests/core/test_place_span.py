"""Stage 5, spans: one solved measure per column and block (layout-0374, amending layout-0298)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core import Box
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_span import solved_spans

from .pipeline_fixtures import cut_of, placed_from
from .test_widen import PLAIN, fan_legs, fan_rows

if TYPE_CHECKING:
    from fransys_layout.core.outputs import Placed


def test_a_columns_span_holds_the_band_of_the_trunk_attached_to_it() -> None:
    prob = fan_rows()
    page = placed_from(cut_of(prob, PLAIN), prob, PLAIN).pages[0]
    foot = {p.sym: p.footprint for p in page.placed}
    trunk = next(t for t in page.trunks if t.row == 1)
    row_top = page.bands[1][0]  # spans are offsets inside the item's solved row
    top, bottom = page.spans["c:k2"]
    # the span holds the step the solve keeps above a trunk line (trunk_room, R409)
    assert top == trunk.y - PLAIN.wiring_grid - row_top < foot["k2"].y - row_top
    assert bottom == foot["k2"].y + foot["k2"].h - row_top


def test_a_columns_span_is_never_its_blocks_extent() -> None:
    prob = fan_rows()
    page = placed_from(cut_of(prob, PLAIN), prob, PLAIN).pages[0]
    block_top, block_bottom = page.spans["fan:c:k1"]
    top, bottom = page.spans["c:k3"]
    assert (bottom - top) * 2 < block_bottom - block_top
    assert block_top <= top
    assert bottom <= block_bottom


def test_a_block_span_follows_a_trunk_moved_up() -> None:
    prob = fan_legs()
    cut = cut_of(prob, PLAIN)
    page = placed_from(cut, prob, PLAIN).pages[0]
    env = page_envs(cut, prob, PLAIN)[0]
    placed: dict[str, Placed] = {p.sym: p for p in page.placed}
    high = replace(page.trunks[0], y=-40)
    before = solved_spans(env, placed, page.trunks)["fan:c:k1"]
    after = solved_spans(env, placed, (high, *page.trunks[1:]))["fan:c:k1"]
    assert after == (-40 - PLAIN.wiring_grid, before[1])
    assert after[0] < before[0]


def test_a_symbols_reach_holds_its_column_and_block_spans_out() -> None:
    prob = fan_legs()
    cut = cut_of(prob, PLAIN)
    page = placed_from(cut, prob, PLAIN).pages[0]
    env = page_envs(cut, prob, PLAIN)[0]
    placed: dict[str, Placed] = {p.sym: p for p in page.placed}
    bare = solved_spans(env, placed, page.trunks)
    k1 = placed["k1"]
    f = k1.footprint
    wide = replace(k1, footprint=Box(f.x, f.y - 80, f.w, f.h + 144))
    held = solved_spans(env, {**placed, "k1": wide}, page.trunks)
    assert held["c:k1"][0] < bare["c:k1"][0]
    assert held["c:k1"][1] == bare["c:k1"][1] + 64
    assert held["fan:c:k1"][0] <= bare["fan:c:k1"][0]
    assert held != bare
    assert solved_spans(env, placed, page.trunks) == bare


def test_a_spans_band_is_the_room_the_solve_held_for_its_trunk() -> None:
    """ROW-ON-GRID: the span reads `Trunk.room`, so a deeper room the solve held reaches the cut."""
    prob = fan_legs()
    cut = cut_of(prob, PLAIN)
    page = placed_from(cut, prob, PLAIN).pages[0]
    env = page_envs(cut, prob, PLAIN)[0]
    assert page.trunks
    placed: dict[str, Placed] = {p.sym: p for p in page.placed}
    before = solved_spans(env, placed, page.trunks)["fan:c:k1"]
    deep = replace(page.trunks[0], room=(page.trunks[0].room[0], page.trunks[0].room[1] + 400))
    after = solved_spans(env, placed, (deep, *page.trunks[1:]))["fan:c:k1"]
    assert after[1] == page.trunks[0].y + deep.room[1] > before[1]
