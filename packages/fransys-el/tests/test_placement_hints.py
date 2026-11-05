"""`hints_of`: draw-in targets and order hints resolved to symbols and groups."""

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_hints import hints_of
from fransys_el.placement_kit import ProblemError
from fransys_el.placement_syms import syms_of
from placement_fixtures import kit_for

from electrical_symbols import LIBRARY
lazy from fransys_layout.core import Hints, Sym
lazy from fransys_model.kernel import Model


def _built(model: Model) -> tuple[Env, tuple[Sym, ...]]:
    """The env and syms of `model`."""
    env = make_env(model, kit_for(model), house(), LIBRARY)
    return env, syms_of(env)


@pytest.fixture(scope="module")
def hinted() -> tuple[Env, tuple[Sym, ...], Hints]:
    """A coil drawn in its own group, and a wired series."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    with d.function("CTRL", "Relay control"):
        s1 = d.device("S1", "DEMO-PB-NO")
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
    with d.function("POWER", "Breaker"):
        q1 = d.device("Q1", "DEMO-MCB-3P")
    d.series(dc.plus, s1.sw, k1.coil, dc.minus, wire=2.5)
    d.series(g1.output["+"], q1.element["1"], wire=2.5)
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


def test_order_hint_naming_an_undrawn_group_raises(dangling_order: Model) -> None:
    """An order hint whose group has no drawn symbol raises `ProblemError` with a fix."""
    env, syms = _built(dangling_order)
    with pytest.raises(ProblemError) as info:
        hints_of(env, syms)
    assert info.value.fix
