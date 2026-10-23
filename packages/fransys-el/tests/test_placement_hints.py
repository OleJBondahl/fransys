"""`hints_of`: authored chains, draw-in targets and order hints resolved to symbols and groups."""

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_hints import hints_of
from fransys_el.placement_kit import ProblemError
from fransys_el.placement_syms import syms_of
from placement_fixtures import kit_for, sid

from electrical_symbols import LIBRARY
lazy from fransys_layout.core import Hints, Sym
lazy from fransys_model.kernel import Model


def _built(model: Model) -> tuple[Env, tuple[Sym, ...]]:
    """The env and syms of `model`."""
    env = make_env(model, kit_for(model), house(), LIBRARY)
    return env, syms_of(env)


@pytest.fixture(scope="module")
def hinted() -> tuple[Env, tuple[Sym, ...], Hints]:
    """A chain authored out of alphabetical order, and a coil drawn in its own group."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    with d.function("CTRL", "Relay control"):
        s1 = d.device("S1", "DEMO-PB-NO")
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
    with d.function("POWER", "Breaker"):
        q1 = d.device("Q1", "DEMO-MCB-3P")
    d.series(dc.plus, s1.sw, k1.coil, dc.minus, wire=2.5)
    d.detail.wire(g1.output["+"], q1.element["1"], wire=2.5)
    d.layout.chain(s1.sw, k1.coil, q1.element)
    with d.function("PUMP", "Draw target") as pump:
        pass
    d.layout.draw_in(k1.coil, pump)
    env, syms = _built(fr.build(d).model)
    return env, syms, hints_of(env, syms)


@pytest.fixture(scope="module")
def dangling_order() -> Model:
    """A design whose order hint names a group no symbol is drawn in."""
    d = fr.design("demo_parts")
    with d.function("CTRL", "Relay control") as ctrl:
        d.device("S1", "DEMO-PB-NO")
    with d.function("EMPTY", "No symbol is drawn here") as empty:
        pass
    d.layout.order(ctrl, empty)
    return fr.build(d).model


def test_chain_follows_entry_index_order(hinted: tuple[Env, tuple[Sym, ...], Hints]) -> None:
    """The chain lists its symbols source first, not in the alphabetical order of their ids."""
    env, _, hints = hinted
    expected = (sid(env.model, "S1.sw"), sid(env.model, "K1.coil"), sid(env.model, "Q1.element"))
    assert expected != tuple(sorted(expected))
    assert hints.chains == (expected,)


def test_draw_in_pairs_a_symbol_with_its_group(
    hinted: tuple[Env, tuple[Sym, ...], Hints],
) -> None:
    """Only the hinted coil is drawn in the target group; the other symbols are not in it."""
    env, _, hints = hinted
    assert hints.draw_in == ((sid(env.model, "K1.coil"), "PUMP"),)


def test_sides_are_left_empty(hinted: tuple[Env, tuple[Sym, ...], Hints]) -> None:
    """Side hints are not read by the builder yet, so `sides` is empty."""
    _, _, hints = hinted
    assert hints.sides == ()
    assert hints.draw_in


def test_order_hint_naming_an_undrawn_group_raises(dangling_order: Model) -> None:
    """An order hint whose group has no drawn symbol raises `ProblemError` with a fix."""
    env, syms = _built(dangling_order)
    with pytest.raises(ProblemError) as info:
        hints_of(env, syms)
    assert info.value.fix
