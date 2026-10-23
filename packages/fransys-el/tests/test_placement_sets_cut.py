"""A net a drawing set cuts keeps its in-set pins and names them in `cut` (UNIT-SCOPE, CUT-ENDS)."""

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.placement_sets import DrawingScope, _carriers, restrict

from electrical_symbols import LIBRARY
from fransys_layout.core import PinRef


def _problem():
    d = fr.design("demo_parts", place="CAB")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    third = d.device("K3", "DEMO-RLY-2CO-24")
    d.detail.wire(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    d.detail.wire(first.coil["A2"], third.coil["A1"], wire=(BU, 0.5))
    model = fr.build(d).model
    return build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)[0]


def _shared(problem):
    return max(problem.nets, key=lambda n: len({p.sym for p in n.pins}))


def _scoped(problem, ids):
    return restrict(problem, DrawingScope(None, None, frozenset(ids)))


def test_a_net_cut_to_two_symbols_keeps_both_pins_and_marks_one_as_cut() -> None:
    problem = _problem()
    net = _shared(problem)
    syms = sorted({p.sym for p in net.pins})
    assert len(syms) == 3
    (kept,) = (n for n in _scoped(problem, syms[:2]).nets if n.id == net.id)
    assert {p.sym for p in kept.pins} == set(syms[:2])
    assert [c.pin for c in kept.cut] == list(kept.pins[:1])


def test_a_net_cut_to_one_symbol_is_kept_with_its_pin_as_the_cut_end() -> None:
    problem = _problem()
    net = _shared(problem)
    lone = min(p.sym for p in net.pins)
    scoped = _scoped(problem, [lone])
    (kept,) = (n for n in scoped.nets if n.id == net.id)
    assert kept.pins == tuple(c.pin for c in kept.cut)
    assert {p.sym for p in kept.pins} == {lone}
    assert [s.id for s in scoped.symbols] == [lone]


def test_a_net_whole_in_the_set_has_no_cut() -> None:
    problem = _problem()
    net = _shared(problem)
    scoped = _scoped(problem, sorted({p.sym for p in net.pins}))
    assert all(n.cut == () for n in scoped.nets)
    assert net in scoped.nets


def test_a_net_cut_with_three_in_set_pins_names_one_carrier_the_first() -> None:
    pins = tuple(PinRef(sym, "1") for sym in ("K1", "K2", "K3"))
    assert _carriers(pins, (), ()) == (PinRef("K1", "1"),)


def test_a_unit_boundary_pin_is_the_carrier_before_a_lower_pin() -> None:
    pins = tuple(PinRef(sym, "1") for sym in ("K1", "K2", "K3"))
    assert _carriers(pins, [PinRef("K2", "1")], ()) == (PinRef("K2", "1"),)


def test_a_pin_no_conductor_leaves_is_never_the_carrier() -> None:
    pins = tuple(PinRef(sym, "1") for sym in ("K1", "K2"))
    assert _carriers(pins, (), [PinRef("K1", "1")]) == (PinRef("K2", "1"),)
    assert _carriers(pins, (), pins) == ()
