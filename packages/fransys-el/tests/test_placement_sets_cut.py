"""A net a drawing set cuts keeps its in-set pins and names them in `cut` (UNIT-SCOPE, CUT-ENDS)."""

from typing import NamedTuple

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.placement_sets import DrawingScope, _carried, _carriers, drawing_scopes, frame_titles, restriction

from electrical_symbols import LIBRARY
from fransys_layout.core import Facts, PinRef, Unit
from fransys_model.derive.tag_text import external_note


def _problem():
    d = fr.design("demo_parts", place="CAB")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    third = d.device("K3", "DEMO-RLY-2CO-24")
    d.series(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    d.series(first.coil["A2"], third.coil["A1"], wire=(BU, 0.5))
    d.earth(first.coil["A1"])
    d.earth(second.coil["A2"])
    d.earth(third.coil["A2"])
    model = fr.build(d).model
    return build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)[0]


def _shared(problem):
    return max(problem.nets, key=lambda n: len({p.sym for p in n.pins}))


def _scoped(problem, ids):
    return restriction(problem, DrawingScope(None, None, frozenset(ids)), options=house().options, tags={}).problem


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


def test_a_scopes_frames_reach_the_restricted_problems_hints_whole_or_cut() -> None:
    problem = _problem()
    cut = sorted({p.sym for p in _shared(problem).pins})[:2]
    frames = (("unit:u", frozenset(cut[:1])),)
    for ids in ([s.id for s in problem.symbols], cut):
        assert (
            restriction(problem, DrawingScope(None, None, frozenset(ids), frames=frames), options=house().options, tags={}).problem.hints.frames
            == frames
        )


def test_an_own_edge_boundary_pin_with_an_in_unit_wire_keeps_its_far_end_in_another_unit() -> None:
    """el-0108: the wire inside the unit does not carry the conductor that leaves it, so the cut still sees the far end and stubs the pin."""
    x, k, h = PinRef("X", "in"), PinRef("K", "in"), PinRef("H", "in")
    facts = Facts(units=(Unit("u", None, (x,)),), far_ends=((x, k), (x, h)))
    kept = _carried(facts, DrawingScope(None, None, frozenset({"X", "K"})), frozenset({"H"}), {"X": "u", "K": "u", "H": "v"}).far_ends
    assert kept == ((x, k), (x, h))


class _Open(NamedTuple):
    pass


@fr.unit("demo-ext", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _ext(u):
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    x90 = u.terminal_strip("X90", None, 3, external=True)
    u.series(x90[1].outer, k1.coil["A1"], wire=("WH", 0.5))
    u.earth(k1.coil["A2"])
    return _Open()


def test_an_external_root_is_framed_by_others_in_each_set_with_no_unit_above_it() -> None:
    d = fr.design("demo_parts")
    d.location("CAB", "Cabinet")
    d.add(_ext, "U1", place="CAB")
    model = fr.build(d).model
    kit = symbol_kit(model, LIBRARY)
    titles = frame_titles(model, kit)
    by_others = {k for k, (es, text) in titles.items() if es == "unit-outline-by-others" and text == external_note()}
    assert len(by_others) == 1
    framed = [dict(s.frames) for s in drawing_scopes(model, kit) if s.frames]
    assert framed
    assert all(set(f) <= set(titles) for f in framed)
    assert any(len(f[k]) == 3 for f in framed for k in by_others if k in f)
