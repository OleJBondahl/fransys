"""Tests for core/topology_orient.py: an anchored chain end decides its chain (FLOW-DOWN)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core.topology_chains import Node, chains, links_of
from fransys_layout.core.topology_orient import ANCHOR_WEIGHT, orient_chain, orient_chains

from .flow_builders import elem, net
from .topology_fixtures import box, read

if TYPE_CHECKING:
    from fransys_layout.core.topology_chains import Facts


def _order(path: tuple[Node, ...]) -> list[str]:
    return [n.elem for n in path]


def _three() -> tuple[Facts, list[tuple[Node, ...]]]:
    """Three chains `a<i>` over `b<i>`, each with a box pin on its top net, in one bundle."""
    syms, nets = [], []
    for i in "123":
        syms += [elem(f"a{i}"), elem(f"b{i}"), box(f"c{i}")]
        nets += [net(f"x{i}", f"a{i}.s", f"b{i}.n"), net(f"bp{i}", f"a{i}.n", f"c{i}.n")]
    r = read(syms, nets)
    paths = sorted(chains(links_of(r.ends_by_net), r.elems, set()), key=lambda p: p[0].elem)
    return replace(r.facts, bundle_of={f"bp{i}": "bd" for i in "123"}), paths


def test_an_anchor_decides_the_head_against_the_box_pin_side() -> None:
    facts, paths = _three()
    path = paths[0]
    assert _order(orient_chain(path, facts)) == ["b1@n", "a1#0"]
    head = replace(facts, anchor_of={"a1": 1})
    tail = replace(facts, anchor_of={"a1": -1})
    assert _order(orient_chain(path, head))[0] == "a1#0"
    assert _order(orient_chain(path, tail))[0] == "b1@n"
    assert ANCHOR_WEIGHT > 100


@pytest.mark.rule("FLOW-DOWN")
def test_an_anchored_chain_keeps_its_anchor_against_the_bundle_it_stands_in() -> None:
    facts, paths = _three()
    free = orient_chains(paths, facts, together=True)
    assert [_order(p)[0] for p in free] == ["b1@n", "b2@n", "b3@n"]
    anchored = orient_chains(paths, replace(facts, anchor_of={"a3": 1}), together=True)
    assert [_order(p)[0] for p in anchored] == ["b1@n", "b2@n", "a3#0"]
