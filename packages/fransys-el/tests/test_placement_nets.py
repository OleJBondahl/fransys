"""`nets_of`: each drawn net with its rail, its bundle and whether it crosses a unit."""

import pytest
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_nets import nets_of
from fransys_el.placement_options import Conventions
from fransys_el.placement_syms import syms_of
from placement_fixtures import demo_model, kit_for, planted_model, sid

from fransys_layout.core import Bundle, Net, PinRef, Sym, natural_key


@pytest.fixture(scope="module")
def demo() -> tuple[Env, tuple[Sym, ...]]:
    """The demo model's env and syms, built once for the module."""
    model = demo_model()
    env = make_env(model, kit_for(model), Conventions())
    return env, syms_of(env)


@pytest.fixture(scope="module")
def planted() -> tuple[Env, tuple[Sym, ...]]:
    """The planted model's env and syms, built once for the module."""
    model = planted_model()
    env = make_env(model, kit_for(model), Conventions())
    return env, syms_of(env)


@pytest.fixture(scope="module")
def crossed() -> tuple[Env, tuple[Sym, ...]]:
    """The planted model with its two 3-pole breakers crossed, built once for the module."""
    model = planted_model(crossed=True)
    env = make_env(model, kit_for(model), Conventions())
    return env, syms_of(env)


def _net_with(nets: tuple[Net, ...], pin: PinRef) -> Net:
    """The one net that has `pin` among its pins."""
    return next(n for n in nets if pin in n.pins)


def _bundles(nets: tuple[Net, ...], sym: str) -> list[Bundle]:
    """The bundles of the nets with a pin on symbol `sym`; a net without one is left out."""
    return [n.bundle for n in nets if n.bundle and any(p.sym == sym for p in n.pins)]


def test_supply_rail_net_is_ranked_and_supply(demo: tuple[Env, tuple[Sym, ...]]) -> None:
    """The net on the 24 V supply's plus has a rank and draws as SUPPLY; the minus net does not."""
    env, syms = demo
    nets = nets_of(env, syms)[0]
    plus = _net_with(nets, PinRef(sid(env.model, "G1.output"), "plus"))
    assert plus.rail is not None
    assert plus.rail.rank is not None
    assert plus.rail.power == "SUPPLY"
    minus = _net_with(nets, PinRef(sid(env.model, "G1.output"), "minus"))
    assert minus.rail is not None
    assert minus.rail.power != "SUPPLY"


def test_unranked_unpowered_net_has_no_rail(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A terminal-to-terminal net with no rank and no power has no rail; a ranked net does."""
    env, syms = planted
    nets = nets_of(env, syms)[0]
    assert _net_with(nets, PinRef(sid(env.model, "2.terminal"), "n")).rail is None
    assert _net_with(nets, PinRef(sid(env.model, "1.terminal"), "n")).rail is not None


def test_three_pole_nets_carry_poles_0_1_2_in_one_bundle(
    planted: tuple[Env, tuple[Sym, ...]],
) -> None:
    """The three breaker-to-breaker nets share one bundle and take poles 0, 1, 2 in order."""
    env, syms = planted
    bundles = _bundles(nets_of(env, syms)[0], sid(env.model, "Q2.element"))
    assert [b.pole for b in bundles] == [0, 1, 2]
    assert len({b.id for b in bundles}) == 1


def test_crossed_three_pole_nets_keep_their_bundle(crossed: tuple[Env, tuple[Sym, ...]]) -> None:
    """Crossing phases 1 and 2 keeps all three nets in one bundle with poles 0, 1, 2."""
    env, syms = crossed
    bundles = _bundles(nets_of(env, syms)[0], sid(env.model, "Q2.element"))
    assert [b.pole for b in bundles] == [0, 1, 2]
    assert len({b.id for b in bundles}) == 1


def test_net_without_a_bundle_has_none(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A net outside any three-pole group has no bundle; a breaker pole net has one."""
    env, syms = planted
    nets = nets_of(env, syms)[0]
    assert _net_with(nets, PinRef(sid(env.model, "2.terminal"), "n")).bundle is None
    assert _net_with(nets, PinRef(sid(env.model, "Q1.element"), "1.out")).bundle is not None


def test_net_spanning_two_units_crosses(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A net with a pin in the unit and one outside it crosses units; a one-unit net does not."""
    env, syms = planted
    nets = nets_of(env, syms)[0]
    assert _net_with(nets, PinRef(sid(env.model, "U1-1.terminal"), "n")).crosses_unit is True
    assert _net_with(nets, PinRef(sid(env.model, "2.terminal"), "n")).crosses_unit is False


def test_every_net_has_two_or_more_pins(demo: tuple[Env, tuple[Sym, ...]]) -> None:
    """A net is kept only with two drawn ends; the demo model has some."""
    env, syms = demo
    nets = nets_of(env, syms)[0]
    assert nets
    assert all(len(n.pins) >= 2 for n in nets)


def test_nets_are_ordered_by_first_pin(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """The nets come in the natural order of their first pin."""
    env, syms = planted
    nets = nets_of(env, syms)[0]
    keys = [(natural_key(n.pins[0].sym), natural_key(n.pins[0].pin)) for n in nets]
    assert keys == sorted(keys)
    assert len(nets) > 1
