"""Tests for core/topology_elements.py: elements of a symbol and the roles of a net's ends."""

from __future__ import annotations

from dataclasses import replace

from turn_fixtures import refit

from fransys_layout import core
from fransys_layout.core.topology_elements import NetEnd, elements, net_ends, wired_pins
from fransys_layout.core.values import BoxSpec, Net, Pin, PinRef
lazy from fransys_layout.core.sym_values import Sym

from .flow_builders import OPTIONS, elem, free, net, poles, problem


def _ends(syms: list[Sym], nets: list[Net], net_id: str) -> tuple[NetEnd, ...]:
    """The ends of one net, with elements read from the symbols as stage 1 reads them."""
    prob = problem(syms, nets)
    wired = wired_pins(prob)
    elem_of_pin = {
        PinRef(sym.id, pin): e
        for sym in prob.symbols
        for e in elements(sym, wired)
        for pin in (e.n_pin, e.s_pin)
        if pin is not None
    }
    by_id = {sym.id: sym for sym in prob.symbols}
    found = next(n for n in prob.nets if n.id == net_id)
    return net_ends(found, elem_of_pin, by_id)


def test_poles_with_equal_pin_dx_become_one_element_per_pole() -> None:
    m = poles("m", 3)
    wired = {PinRef(m.id, p.id): "x" for p in m.pins}
    pairs = [(e.form, e.n_pin, e.s_pin) for e in elements(m, wired)]
    assert pairs == [("pole", "n0", "s0"), ("pole", "n1", "s1"), ("pole", "n2", "s2")]


def test_free_sided_symbol_gets_one_element_for_its_one_node() -> None:
    h = free("h")
    wired = {PinRef(h.id, p.id): "bus" for p in h.pins}
    (only,) = elements(h, wired)
    assert (only.form, only.n_pin, only.s_pin) == ("free", "n", "s")


def test_a_single_is_one_element() -> None:
    a = elem("a", stand_s="GROUND")
    (only,) = elements(a, {})
    assert (only.form, only.n_pin, only.s_pin) == ("single", None, "s")


def test_net_end_roles_top_bottom_side_through_and_boxpin() -> None:
    top = _ends([elem("a"), elem("b")], [net("x", "a.n", "b.n"), net("y", "a.s", "b.s")], "x")
    bottom = _ends([elem("a"), elem("b")], [net("x", "a.n", "b.n"), net("y", "a.s", "b.s")], "y")
    through = _ends([elem("a"), elem("b")], [net("x", "a.n", "a.s", "b.n")], "x")
    side_pin = replace(elem("a"), pins=(Pin("e", "E", 8, 0, 0),), nodes=(("e",),))
    side = _ends([side_pin, elem("b")], [net("x", "a.e", "b.n")], "x")
    box = replace(elem("c"), box=BoxSpec(("n", "s"), "S", 16, 16))
    boxed = _ends([elem("a"), box], [net("x", "c.s", "a.n")], "x")
    assert [e.site for e in top] == ["top", "top"]
    assert [e.site for e in bottom] == ["bottom", "bottom"]
    assert [e.site for e in through] == ["through", "top"]
    assert [e.site for e in side] == ["side", "top"]
    assert [e.site for e in boxed] == ["top", "boxpin"]


def test_net_ends_come_back_in_natural_key_order_whatever_the_input_order() -> None:
    forward = _ends([elem("h1"), elem("h2"), elem("h10")], [net("x", "h1.s", "h2.s", "h10.s")], "x")
    reverse = _ends([elem("h10"), elem("h2"), elem("h1")], [net("x", "h10.s", "h2.s", "h1.s")], "x")
    assert [e.pin.sym for e in forward] == ["h1", "h2", "h10"]
    assert forward == reverse


def test_elements_come_back_in_natural_key_order_whatever_the_pin_order() -> None:
    u = replace(
        elem("u"),
        pins=(Pin("p10", "S", 16, 16, 1, 1), Pin("p2", "S", 0, 16, 0, 1)),
        nodes=(("p2",), ("p10",)),
    )
    forward = elements(u, {})
    reverse = elements(refit(u, pins=tuple(reversed(u.pins))), {})
    assert [e.key for e in forward] == ["u@p2", "u@p10"]
    assert forward == reverse


def test_solve_carries_the_wired_pins_and_the_surface_does_not_export_the_function() -> None:
    prob = problem([elem("a"), elem("b")], [net("x", "a.n", "b.n")])
    assert "wired_pins" not in core.__all__
    assert dict(core.solve(prob, OPTIONS).wired) == {PinRef("a", "n"): "x", PinRef("b", "n"): "x"}
