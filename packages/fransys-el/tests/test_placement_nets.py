"""`nets_of`: each drawn wiring net with its bundle and whether it crosses a unit."""
# NET_POTENTIAL_CONFLICT 2 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 2 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# WIRE_ROW_UNRESOLVED 6 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

import re
from dataclasses import replace

import pytest
from conventions_fixtures import house
from fransys_el import placement_nets, skipped_findings
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_ids import net_key
from fransys_el.placement_nets import net_ports, nets_of
from fransys_el.placement_syms import syms_of
from placement_fixtures import kit_for, planted_model, sid

from electrical_symbols import LIBRARY
from fransys_layout.core import Bundle, Net, PinRef, Sym, natural_key
from fransys_model.derive import physical_nets, port_is_unused
from fransys_model.kernel import Severity, id_namespace


@pytest.fixture(scope="module")
def crossed() -> tuple[Env, tuple[Sym, ...]]:
    """The planted model with its two 3-pole breakers crossed, built once for the module."""
    model = planted_model(crossed=True)
    env = make_env(model, kit_for(model), house(), LIBRARY)
    return env, syms_of(env)


def _net_with(nets: tuple[Net, ...], pin: PinRef) -> Net:
    """The one net that has `pin` among its pins."""
    return next(n for n in nets if pin in n.pins)


def _bundles(nets: tuple[Net, ...], sym: str) -> list[Bundle]:
    """The bundles of the nets with a pin on symbol `sym`; a net without one is left out."""
    return [n.bundle for n in nets if n.bundle and any(p.sym == sym for p in n.pins)]


def test_power_nets_are_no_nets(demo: tuple[Env, tuple[Sym, ...]]) -> None:
    """The net on the 24 V supply's plus is drawn by anchors, so it is no net; the minus is."""
    env, syms = demo
    nets = nets_of(env, syms)[0]
    plus, minus = (PinRef(sid(env.model, "G1.output"), name) for name in ("plus", "minus"))
    assert not any(plus in n.pins for n in nets)
    assert any(minus in n.pins for n in nets)


@pytest.mark.parametrize(
    "fixture",
    [
        pytest.param("planted", id="planted"),
        pytest.param("crossed", id="crossed_phases_1_and_2"),
    ],
)
def test_three_pole_nets_carry_poles_0_1_2_in_one_bundle(fixture: str, request: pytest.FixtureRequest) -> None:
    """The three breaker-to-breaker nets share one bundle and take poles 0, 1, 2 in order, crossed or not."""
    env, syms = request.getfixturevalue(fixture)
    bundles = _bundles(nets_of(env, syms)[0], sid(env.model, "Q2.element"))
    assert [b.pole for b in bundles] == [0, 1, 2]
    assert len({b.id for b in bundles}) == 1


def test_net_without_a_bundle_has_none(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A net outside any three-pole group has no bundle; a breaker pole net has one."""
    env, syms = planted
    nets = nets_of(env, syms)[0]
    assert _net_with(nets, PinRef(sid(env.model, "1.terminal"), "n")).bundle is None
    assert _net_with(nets, PinRef(sid(env.model, "Q1.element"), "1.out")).bundle is not None


def test_net_spanning_two_units_crosses(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A net with a pin in the unit and one outside it crosses units; a one-unit net does not."""
    env, syms = planted
    nets = nets_of(env, syms)[0]
    assert _net_with(nets, PinRef(sid(env.model, "U1-1.terminal"), "n")).crosses_unit is True
    assert _net_with(nets, PinRef(sid(env.model, "Q1.element"), "1.out")).crosses_unit is False


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


def test_a_two_end_net_with_an_undrawn_end_is_one_skipped_and_one_error(
    planted: tuple[Env, tuple[Sym, ...]],
) -> None:
    """Ruling 86: an undrawn net of two ends is one ERROR; a lone port is no net."""
    env, syms = planted
    two = next(p for p in physical_nets(env.model) if len(p.ports) == 2 and not all(port_is_unused(env.model, q) for q in p.ports))
    cut = replace(env, undrawn=env.undrawn | {two.ports[1]})
    _, skipped = nets_of(cut, syms)
    assert [(s.what, s.id) for s in skipped] == [("net", net_key(env.model, two.ports))]
    found = skipped_findings(env.model, skipped)
    assert [(f.code, f.severity) for f in found] == [("NET_NOT_DRAWN", Severity.ERROR)]
    assert nets_of(env, syms)[1] == ()


def _spelled(salt: str) -> tuple[list[str], list[str | None]]:
    """The net ids and bundle ids of the planted model (no strip, no unit: no KI-461 short) built under `salt`, 32-hex Id texts removed."""
    with id_namespace(salt):
        model = planted_model(strip=False, unit=False)
        env = make_env(model, kit_for(model), house(), LIBRARY)
        nets = nets_of(env, syms_of(env))[0]
    strip = re.compile(r"[0-9a-f]{32}")
    return [strip.sub("#", n.id) for n in nets], [strip.sub("#", n.bundle.id) if n.bundle else None for n in nets]


def test_net_and_bundle_ids_lead_with_order_text_and_do_not_move_with_the_salt() -> None:
    """R1615: one model under two Id salts spells every net and bundle id alike but for the Id text, and none leads with it."""
    (nets_a, bundles_a), (nets_b, bundles_b) = _spelled("a"), _spelled("b")
    assert nets_a == nets_b
    assert bundles_a == bundles_b
    assert any(bundles_a)
    assert all(not text.startswith("#") for text in (*nets_a, *filter(None, bundles_a)))


def test_a_bundle_is_the_one_every_port_of_the_net_agrees_on(planted: tuple[Env, tuple[Sym, ...]], monkeypatch: pytest.MonkeyPatch) -> None:
    """R1623: a net with one port outside its bundle has none; the lead port's bundle does not decide."""
    env, syms = planted
    net = next(n for n in nets_of(env, syms)[0] if n.bundle)
    lead = net_ports(env.model)[net.id]
    other = next(p for p in physical_nets(env.model) if lead in p.ports and len(p.ports) > 1).ports
    odd = next(p for p in other if p != lead)
    real = placement_nets.bundle_of
    monkeypatch.setattr(placement_nets, "bundle_of", lambda m, p, f: None if p == odd else real(m, p, f))
    assert next(n for n in nets_of(env, syms)[0] if n.id == net.id).bundle is None
