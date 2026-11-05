"""Tests for core/topology_orient.py: an anchored chain end decides its chain (FLOW-DOWN)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core.topology_chains import Node, chains, flipped, links_of
from fransys_layout.core.topology_orient import orient_chain, orient_chains
from fransys_layout.core.values import Pin

from .flow_builders import elem, net
from .topology_fixtures import box, read

if TYPE_CHECKING:
    from fransys_layout.core.topology_chains import Facts


def _order(path: tuple[Node, ...]) -> list[str]:
    return [n.elem for n in path]


def _three(south: str = "") -> tuple[Facts, list[tuple[Node, ...]]]:
    """Three chains `a<i>` over `b<i>`, each with a box pin on its top net, in one bundle; `south` ids meet the box's S pin."""
    syms, nets = [], []
    for i in "123":
        syms += [elem(f"a{i}"), elem(f"b{i}"), box(f"c{i}")]
        nets += [net(f"x{i}", f"a{i}.s", f"b{i}.n"), net(f"bp{i}", f"a{i}.n", f"c{i}.{'s' if i in south else 'n'}")]
    r = read(syms, nets)
    paths = sorted(chains(links_of(r.ends_by_net, r.elems, r.syms), r.elems, set()), key=lambda p: p[0].elem)
    return replace(r.facts, bundle_of={f"bp{i}": "bd" for i in "123"}), paths


def test_an_anchor_decides_the_head_against_the_box_pin_side() -> None:
    facts, paths = _three()
    path = paths[0]
    assert _order(orient_chain(path, facts)) == ["b1@n", "a1#0"]
    head = replace(facts, anchor_of={"a1": 1})
    tail = replace(facts, anchor_of={"a1": -1})
    assert _order(orient_chain(path, head))[0] == "a1#0"
    assert _order(orient_chain(path, tail))[0] == "b1@n"
    assert facts.anchor_weight > 100


@pytest.mark.rule("FLOW-DOWN")
def test_an_anchored_chain_keeps_its_anchor_against_the_bundle_it_stands_in() -> None:
    facts, paths = _three()
    free = orient_chains(paths, facts, together=True)
    assert [_order(p)[0] for p in free] == ["b1@n", "b2@n", "b3@n"]
    anchored = orient_chains(paths, replace(facts, anchor_of={"a3": 1}), together=True)
    assert [_order(p)[0] for p in anchored] == ["b1@n", "b2@n", "a3#0"]


@pytest.mark.rule("FLOW-DOWN")
def test_a_chain_wired_to_a_box_faces_the_box_against_the_bundle_it_stands_in() -> None:
    facts, paths = _three(south="2")
    oriented = orient_chains(paths, facts, together=True)
    assert [_order(p)[0] for p in oriented] == ["b1@n", "a2#0", "b3@n"]


@pytest.mark.rule("BUNDLE")
def test_a_one_pin_symbol_wired_to_a_box_turns_with_its_bundle() -> None:
    syms, nets = [], []
    for i in "123":
        syms += [elem(f"a{i}"), box(f"c{i}")]
        nets.append(net(f"bp{i}", f"a{i}.n", f"c{i}.{'s' if i == '2' else 'n'}"))
    r = read(syms, nets)
    paths = sorted(chains(links_of(r.ends_by_net, r.elems, r.syms), r.elems, set()), key=lambda p: p[0].elem)
    oriented = orient_chains(paths, replace(r.facts, bundle_of={f"bp{i}": "bd" for i in "123"}), together=True)
    assert [p[0].top for p in oriented] == [None, None, None]


def _motor(pe_bias: int = 1, bundled: str = "uvw") -> tuple[Facts, list[tuple[Node, ...]]]:
    """A motor, pins u v w pe on side N: `bundled` in one bundle, pe foot-biased by `pe_bias`."""
    pins = tuple(Pin(p, "N", dx, -16, 0, pe_bias if p == "pe" else 0, 0) for p, dx in _MOTOR_PINS)
    syms = [replace(elem("m"), pins=pins, nodes=tuple((p,) for p, _ in _MOTOR_PINS))]
    nets = []
    for p, _ in _MOTOR_PINS:
        syms.append(elem(f"s{p}"))
        nets.append(net(f"x{p}", f"s{p}.s", f"m.{p}"))
    r = read(syms, nets)
    paths: list[tuple[Node, ...]] = [(Node(f"m@{p}", p, None),) for p, _ in _MOTOR_PINS]  # one-node chains
    return replace(r.facts, bundle_of={f"x{p}": "bd" for p in bundled}), paths


_MOTOR_PINS = (("pe", -24), ("u", -8), ("v", 8), ("w", 24))


def _turned(path: tuple[Node, ...]) -> bool:
    return path[0].top is None


@pytest.mark.rule("FLOW-DOWN")
def test_a_lone_chain_never_turns_its_symbol_against_its_other_chains() -> None:
    facts, paths = _motor()
    assert len(paths) == 4
    oriented = orient_chains(paths, facts, together=True)
    assert {_turned(p) for p in oriented} == {False}


@pytest.mark.rule("FLOW-DOWN")
def test_a_symbol_in_a_bundle_gives_its_lone_chain_the_bundles_turn() -> None:
    """The bundle (u, v) sums to -2 and stays; pe sums +5, so the column sum is +3 (R540)."""
    facts, paths = _motor(pe_bias=2, bundled="uv")
    paths = [p for p in paths if p[0].elem != "m@w"]
    oriented = orient_chains(paths, facts, together=True)
    flips = {flipped(n, facts.elems[n.elem]) for p in oriented for n in p}
    assert flips == {False}
