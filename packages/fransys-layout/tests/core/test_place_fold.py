"""The page env folds the page's hangings into its symbols; a Placed shows the bare footprint."""

from __future__ import annotations

from fransys_layout.core.geometry import shift
from fransys_layout.core.place import place_pages
from fransys_layout.core.place_env import page_envs

from .solve_fixtures import tag_on_the_wire


def test_the_env_holds_the_tag_in_k00s_footprint_and_keeps_the_bare_symbols() -> None:
    prob, cut, _, opts = tag_on_the_wire()
    env = page_envs(cut, prob, opts)[0]
    folded, bare = env.syms["k00"], env.bare["k00"]
    assert folded.footprint.y < bare.footprint.y  # the tag stands above the top pin
    assert folded.footprint != bare.footprint
    assert env.syms["k02"].views["R0"].keepout == env.bare["k02"].views["R0"].keepout


def test_a_placed_symbol_shows_the_bare_footprint_about_its_origin() -> None:
    prob, cut, _, opts = tag_on_the_wire()
    env = page_envs(cut, prob, opts)[0]
    placed = {p.sym: p for pg in place_pages(cut, prob, opts).pages for p in pg.placed}["k00"]
    assert placed.footprint == shift(env.bare["k00"].views[placed.orient].footprint, placed.x, placed.y)
