"""Tests for core/topology_chains.py: links, chains, cycle breaking, head choice, cell flips."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core.topology_chains import (
    Node,
    cells_of,
    chains,
    group_columns,
    links_of,
    orient_chain,
)

from .flow_builders import elem, free, net
from .topology_fixtures import Read, box, read

if TYPE_CHECKING:
    from fransys_layout.core.values import Power, Sym

NO_DEALT: set[str] = set()


def _order(path: tuple[Node, ...]) -> list[str]:
    return [n.elem for n in path]


def _flip(path: tuple[Node, ...]) -> tuple[Node, ...]:
    return tuple(Node(n.elem, n.bottom, n.top) for n in reversed(path))


def _stood(sym_id: str) -> Sym:
    """A pole with both pins on stands, so it is one element whatever the nets."""
    return elem(sym_id, stand_n="SUPPLY", stand_s="GROUND")


def test_links_are_two_end_nets_of_different_roles_or_without_a_through_element() -> None:
    syms = [elem(s) for s in "abcdefgij"] + [free("h")]
    nets = [
        net("series", "a.s", "b.n"),
        net("side", "c.s", "d.s"),
        net("fan", "e.s", "f.s", "h.n", "h.s"),
        net("three", "g.n", "i.n", "j.n"),
    ]
    got = links_of(read(syms, nets).ends_by_net)
    assert sorted(got) == ["series", "side"]


def test_a_chain_is_the_union_of_links_from_one_extreme_to_the_other() -> None:
    syms = [elem("a", stand_n="SUPPLY"), elem("b"), elem("c", stand_s="GROUND")]
    r = read(syms, [net("x", "a.s", "b.n"), net("y", "b.s", "c.n")])
    (path,) = chains(links_of(r.ends_by_net), r.elems, NO_DEALT)
    assert _order(path) == ["a#0", "b#0", "c#0"]
    assert [(n.top, n.bottom) for n in path] == [("n", "s")] * 3


def test_a_lone_element_is_a_chain_of_one_and_a_dealt_element_starts_none() -> None:
    r = read([_stood("a"), _stood("b")], [])
    assert [_order(p) for p in chains({}, r.elems, NO_DEALT)] == [["a#0"], ["b#0"]]
    assert [_order(p) for p in chains({}, r.elems, {"a#0"})] == [["b#0"]]


def test_a_cycle_is_broken_at_the_natural_last_net() -> None:
    syms = [elem("a"), elem("b"), elem("c")]
    nets = [net("n2", "a.s", "b.n"), net("n9", "b.s", "c.n"), net("n10", "c.s", "a.n")]
    r = read(syms, nets)
    (path,) = chains(links_of(r.ends_by_net), r.elems, NO_DEALT)
    assert _order(path) == ["a#0", "b#0", "c#0"]


def _two(box_pin: str | None = None, stand_n: Power | None = None) -> tuple[Read, tuple[Node, ...]]:
    """The chain a over b; a box pin on a's top net when box_pin is "n" or "s"."""
    syms = [elem("a", stand_n=stand_n), elem("b")]
    nets = [net("x", "a.s", "b.n")]
    if box_pin is not None:
        syms.append(box("c"))
        nets.append(net("bp", "a.n", f"c.{box_pin}"))
    r = read(syms, nets)
    (path,) = chains(links_of(r.ends_by_net), r.elems, NO_DEALT)
    return r, path


def test_head_is_the_extreme_whose_box_pin_is_on_the_south_side_weight_six() -> None:
    r, path = _two("s")
    assert _order(orient_chain(path, r.facts)) == ["a#0", "b@n"]
    assert _order(orient_chain(_flip(path), r.facts)) == ["a#0", "b@n"]
    r, path = _two("n")
    assert _order(orient_chain(path, r.facts)) == ["b@n", "a#0"]
    assert _order(orient_chain(_flip(path), r.facts)) == ["b@n", "a#0"]


def test_head_is_the_extreme_with_the_supply_stand_weight_three() -> None:
    r, path = _two(stand_n="SUPPLY")
    assert _order(orient_chain(_flip(path), r.facts)) == ["a#0", "b@n"]
    r, path = _two(stand_n="GROUND")
    assert _order(orient_chain(path, r.facts)) == ["b@n", "a#0"]


def test_head_follows_the_pin_side_when_nothing_else_decides_and_a_tie_keeps_the_first() -> None:
    r = read([elem("a"), elem("b")], [net("x", "a.s", "b.n")])
    up = (Node("a@s", "n", "s"), Node("b@n", "n", "s"))
    assert orient_chain(up, r.facts) == up
    assert orient_chain(_flip(up), r.facts) == up
    down = (Node("a@s", "s", "n"), Node("b@n", "s", "n"))
    assert orient_chain(down, r.facts) == _flip(down)
    tie = (Node("a@s", "s", "n"), Node("b@n", "n", "s"))
    assert orient_chain(tie, r.facts) == tie


def test_a_cell_is_r180_when_an_s_pin_points_at_the_head_and_a_hub_never_flips() -> None:
    r = read([_stood("a"), _stood("b"), free("h")], [])
    path = (Node("a#0", "n", "s"), Node("b#0", "s", "n"), Node("h#0", "s", "n"))
    cells = cells_of(path, r.elems, r.syms)
    assert [c.orient for c in cells] == ["R0", "R180", "R0"]
    assert [(c.top_pin, c.bottom_pin) for c in cells] == [("n", "s"), ("s", "n"), ("s", "n")]


def test_a_cell_stays_r0_when_the_symbol_has_no_r180() -> None:
    fixed = replace(_stood("a"), orientations=frozenset({"R0"}))
    r = read([fixed], [])
    (cell,) = cells_of((Node("a#0", "s", "n"),), r.elems, r.syms)
    assert cell.orient == "R0"


def test_chains_sharing_a_symbol_are_one_column() -> None:
    r = read([_stood("a"), _stood("b")], [])
    one = (Node("a#0", "n", "s"),)
    two = (Node("b#0", "n", "s"),)
    assert group_columns((one, two, one), r.elems) == ((0, 2), (1,))
