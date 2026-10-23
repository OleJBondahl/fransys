"""Tests for the two chain conventions Options carries: the end bias weight and the flip turn."""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core.topology_chains import (
    Facts,
    Node,
    cells_of,
    chains,
    links_of,
)
from fransys_layout.core.topology_orient import orient_chain

from .flow_builders import OPTIONS, elem, net
from .topology_fixtures import read
from .turn_fixtures import views_of


def _facts(r, **changes) -> Facts:
    opts = replace(OPTIONS, **changes)
    return Facts(r.elems, r.syms, r.ends_by_net, r.net_of, opts.end_bias_weight, opts.flip_turn)


def test_end_bias_weight_decides_how_far_a_biased_pin_pulls_the_chain_end() -> None:
    r = read([elem("a", stand_n="GROUND"), elem("b")], [net("x", "a.s", "b.n")])
    (path,) = chains(links_of(r.ends_by_net), r.elems, set())
    house = orient_chain(path, _facts(r))
    other = orient_chain(path, _facts(r, end_bias_weight=0))
    assert [n.elem for n in house] == ["b@n", "a#0"]
    assert [n.elem for n in other] == ["a#0", "b@n"]


def test_flip_turn_is_the_orientation_of_a_flipped_cell() -> None:
    base = elem("a", stand_n="SUPPLY", stand_s="GROUND")
    mirrored = replace(
        base,
        views=views_of(base.body, base.keepout, base.footprint, base.pins, ("R0", "R180", "MR0")),
    )
    r = read([mirrored], [])
    path = (Node("a#0", "s", "n"),)
    house = cells_of(path, r.elems, r.syms, OPTIONS.flip_turn)
    other = cells_of(path, r.elems, r.syms, "MR0")
    assert [c.orient for c in house] == ["R180"]
    assert [c.orient for c in other] == ["MR0"]
