"""A set's restriction names its cut nets and the nets it drops for want of a carrier (R520 B1)."""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from conventions_fixtures import house
from fransys_el.restrict import restriction
from fransys_el.scopes import DrawingScope
from hypothesis import given
from hypothesis import strategies as st
from test_placement_sets_annexes import _problem

from fransys_model import derive
from fransys_model.vocab.tables import functions


def _split():
    problem = _problem()
    ids = [s.id for s in problem.symbols]
    scope = DrawingScope(None, None, frozenset(ids[:2]))
    crossing = [n for n in problem.nets if {p.sym for p in n.pins} & scope.symbols and {p.sym for p in n.pins} - scope.symbols]
    return problem, scope, crossing


def test_a_cut_net_with_a_carrier_is_cut_and_not_dropped() -> None:
    problem, scope, crossing = _split()
    assert len(crossing) == 2  # the ring: K2-K3 and K3-K1
    result = restriction(problem, scope, options=house().options, tags={})
    assert result.dropped == frozenset()
    assert [n.id for n in result.problem.nets if n.cut] == [n.id for n in crossing]


def test_a_cut_net_whose_inside_pins_are_bare_is_dropped_and_not_cut() -> None:
    problem, scope, crossing = _split()
    bare = [p for p in crossing[0].pins if p.sym in scope.symbols]
    result = restriction(problem, scope, bare, options=house().options, tags={})
    assert result.dropped == {crossing[0].id}
    assert crossing[0].id not in {n.id for n in result.problem.nets}


def test_a_scope_holding_every_symbol_cuts_and_drops_nothing() -> None:
    problem = _problem()
    result = restriction(problem, DrawingScope(None, None, frozenset(s.id for s in problem.symbols)), options=house().options, tags={})
    assert result.dropped == frozenset()


_cached_problem = cache(_problem)


@given(data=st.data())
def test_a_scope_keeps_every_net_it_touches_cut_exactly_when_it_crosses_or_names_it_dropped(data: st.DataObject) -> None:
    """SG-EL C2 half 2: each net with a pin in the scope is kept or dropped, never both nor neither."""
    problem = _cached_problem()
    ids = [s.id for s in problem.symbols]
    scope = DrawingScope(None, None, frozenset(data.draw(st.sets(st.sampled_from(ids), min_size=1))))
    inside = [(n, [p for p in n.pins if p.sym in scope.symbols]) for n in problem.nets]
    bare = data.draw(st.sets(st.sampled_from([p for _, ins in inside for p in ins])))
    result = restriction(problem, scope, bare, options=house().options, tags={})
    kept = {n.id: n for n in result.problem.nets}
    for net, ins in inside:
        crosses = len(ins) < len(net.pins)
        assert (net.id in kept) != (net.id in result.dropped) or not ins  # 1 kept xor dropped
        if net.id in kept:
            assert bool(kept[net.id].cut) == crosses  # 2 cut exactly when it crosses
        if net.id in result.dropped:
            assert crosses  # 3 a dropped net crosses, its inside pins all bare
            assert set(ins) <= bare
    if scope.symbols == frozenset(ids):
        assert result.dropped == frozenset()  # 4 the whole scope cuts and drops nothing
        assert not any(n.cut for n in result.problem.nets)


_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01", "text": "x", "by": "AB"}


class _Strip(NamedTuple):
    X1: Any


class _Lamp(NamedTuple):
    H1: Any


@fr.unit("demo-cut-inner", **_REL)
def _inner(u: Any) -> _Strip:
    strip = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    run = strip.run("SIG", 1)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5")
    x2.run("SPARE", 1)  # no wire reaches it: a spare terminal
    lamp = u.device("P1", "DEMO-LAMP-24")
    u.series(lamp.lamp["1"], x2.run("A", 1)[1].inner, wire=("WH", 0.75))
    u.series(lamp.lamp["2"], x2.run("0V", 1)[1].inner, wire=("WH", 0.75))
    return _Strip(run)


@fr.unit("demo-cut-outer", **_REL)
def _outer(u: Any) -> _Lamp:
    h2 = u.device("H1", "DEMO-LAMP-24")
    x7 = u.terminal_strip("X3", "DEMO-TB-2.5")
    inner = u.add(_inner, "U2")
    u.series(h2.lamp["2"], x7.run("0V", 1)[1].inner, wire=("WH", 0.75))
    u.series(h2.lamp["1"], inner.X1[1].outer, wire=("WH", 0.75))
    return _Lamp(h2)


@fr.unit("demo-cut-box", **_REL)
def _box(u: Any) -> _Strip:
    run = u.terminal_strip("X4", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    lamp = u.device("P2", "DEMO-LAMP-24")
    x6 = u.terminal_strip("X6", "DEMO-TB-2.5")
    u.series(lamp.lamp["1"], x6.run("A", 1)[1].inner, wire=("WH", 0.75))
    u.series(lamp.lamp["2"], x6.run("0V", 1)[1].inner, wire=("WH", 0.75))
    return _Strip(run)


@pytest.mark.rule("WHERE-WIRED")
@pytest.mark.rule("SPARE-TERMINALS")
def test_a_terminal_a_cut_reaches_is_drawn_with_its_reference_and_a_spare_is_listed_only() -> None:
    """layout-0463: a nested unit's strip and a unit's boundary strip wired from outside are drawn in the unit's set; a spare is not."""
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    d.add(_outer, "U1")
    box = d.add(_box, "U3", place="C1")
    outside = d.device("H9", "DEMO-LAMP-24", place="C1")
    ret = d.terminal_strip("X9", "DEMO-TB-2.5", place="C1")
    d.series(outside.lamp["1"], box.X1[1].outer, wire=("WH", 0.75))
    d.series(outside.lamp["2"], ret.run("0V", 1)[1].inner, wire=("WH", 0.75))
    docs = [unit_document(name) for name in ("demo-cut-outer", "demo-cut-inner", "demo-cut-box")]
    result = fr.build(d, *docs)
    fr.write(result, root / "out", intermediates=root / "inter")
    codes = [f.code for f in result.findings]
    assert "CONNECTION_NOT_DRAWN" not in codes
    reached = {
        derive.item_designation(result.model, f.item): derive.function_is_reached(result.model, f.id) for f in functions(result.model).values()
    }
    spare = [r for k, r in reached.items() if "SPARE" in k]
    assert spare == [False]
    assert all(r for k, r in reached.items() if "SIG" in k)
