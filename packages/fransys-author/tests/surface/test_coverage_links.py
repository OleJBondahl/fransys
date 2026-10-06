"""EA7 links: each call writes exactly the records the engine call writes."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Device, design

from fransys_model.vocab import Conductor, ConductorKind, NetClass
lazy from fransys_model.kernel import Draft


def _pins(d):
    e = d._engine
    k1 = e.item("TEST-RLY-2CO", tag="K1", name="K1")
    k2 = e.item("TEST-RLY-2CO", tag="K2", name="K2")
    return k1.fn("coil")["A1"], k1.fn("coil")["A2"], k2.fn("coil")["A1"]


def _records(d) -> list:
    return d.draft().records()


def _both(parts: Draft, surface_call, engine_call) -> list:
    d, e = design(parts), design(parts)
    surface_call(d, *_pins(d))
    engine_call(e._engine, *_pins(e))
    assert _records(d) == _records(e)
    return _records(d)


def test_earth_is_one_pe_net(parts: Draft) -> None:
    _both(
        parts,
        lambda d, a, b, c: d.earth(a, b, c),
        lambda e, a, b, c: e.net("PE", a, b, c, cls="pe"),
    )


def test_earth_needs_a_pin(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="at least one pin"):
        design(parts).earth()


def test_a_terminal_given_to_earth_is_its_inner_port(parts: Draft) -> None:
    d, e = design(parts), design(parts)
    d.earth(d._engine.strip("X1").terminal("TEST-TB"))
    e._engine.net("PE", e._engine.strip("X1").terminal("TEST-TB").inner, cls="pe")
    assert _records(d) == _records(e)


@pytest.mark.parametrize("kind", [NetClass.CONTROL, NetClass.SIGNAL, NetClass.GENERIC])
def test_net_writes_the_engine_net(parts: Draft, kind: NetClass) -> None:
    _both(
        parts,
        lambda d, a, b, *_: d.net("S1", a, b, kind=kind),
        lambda e, a, b, *_: e.net("S1", a, b, cls=kind.value),
    )


def test_net_defaults_to_control(parts: Draft) -> None:
    _both(
        parts,
        lambda d, a, b, *_: d.net("S1", a, b),
        lambda e, a, b, *_: e.net("S1", a, b, cls="control"),
    )


def test_net_refuses_the_pe_kind_and_points_to_earth(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    with pytest.raises(AuthorError, match=r"use d\.earth"):
        d.net("PE", a, b, kind=NetClass.PE)


def test_net_refuses_the_power_kind_and_points_to_a_supplys_rails(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    with pytest.raises(AuthorError, match=r"use a supply's rails \(d\.ac_supply, d\.dc_supply\)"):
        d.net("L1", a, b, kind=NetClass.POWER)


def test_net_kind_is_a_netclass_not_a_string(parts: Draft) -> None:
    d = design(parts)
    a, b, _ = _pins(d)
    with pytest.raises(AuthorError, match=r"a kind is a name: NetClass\.X"):
        d.net("S1", a, b, kind="control")  # ty: ignore[invalid-argument-type] -- the bad kind is the test


@pytest.mark.parametrize(
    ("call", "engine_kind", "conductor_kind"),
    [("busbar", "bus", ConductorKind.BUSBAR), ("rail_bond", "rail", ConductorKind.RAIL)],
)
def test_busbar_and_rail_bond_write_the_engine_link(
    parts: Draft, call: str, engine_kind: str, conductor_kind: ConductorKind
) -> None:
    got = _both(
        parts,
        lambda d, a, b, *_: getattr(d, call)(a, b),
        lambda e, a, b, *_: e.link(a, b, kind=engine_kind),
    )
    assert next(r for r in got if isinstance(r, Conductor)).kind is conductor_kind


@pytest.mark.parametrize("call", ["busbar", "rail_bond"])
def test_the_same_pin_twice_raises_the_engines_error(parts: Draft, call: str) -> None:
    d = design(parts)
    a, _, _ = _pins(d)
    with pytest.raises(AuthorError, match="two different ports"):
        getattr(d, call)(a, a)


def _connectors(d):
    return d._engine.item("TEST-CONN-2P", tag="X1", name="X1"), d._engine.item(
        "TEST-CONN-2P", tag="X2", name="X2"
    )


def test_mate_of_two_devices_is_the_engine_mate(parts: Draft) -> None:
    d, e = design(parts), design(parts)
    x1, x2 = _connectors(d)
    d.mate(Device("X1", x1), Device("X2", x2))
    y1, y2 = _connectors(e)
    e._engine.mate(y1, y2)
    assert _records(d) == _records(e)


def test_mate_of_two_functions_is_the_engine_mate(parts: Draft) -> None:
    from fransys_author.surface import Fn

    d, e = design(parts), design(parts)
    x1, x2 = _connectors(d)
    d.mate(Fn("X1", x1.as_function()), Fn("X2", x2.as_function()))
    y1, y2 = _connectors(e)
    e._engine.mate(y1.as_function(), y2.as_function())
    assert _records(d) == _records(e)


def test_mate_with_a_string_raises_naming_the_type(parts: Draft) -> None:
    d = design(parts)
    x1, _ = _connectors(d)
    with pytest.raises(AuthorError, match=r"d\.mate .* got str"):
        d.mate(Device("X1", x1), "X2")  # ty: ignore[invalid-argument-type] -- the bad handle is the test


def test_harness_writes_the_engine_harness_and_returns_a_device(parts: Draft) -> None:
    d, e = design(parts), design(parts)
    w5 = d.harness("W5")
    e._engine.harness(name="W5", tag="W5")
    assert isinstance(w5, Device)
    assert _records(d) == _records(e)


def test_harness_refuses_a_prefixed_tag(parts: Draft) -> None:
    with pytest.raises(AuthorError, match=r"write W5; harness\(\) adds the -"):
        design(parts).harness("-W5")


def test_harness_refuses_a_repeated_tag(parts: Draft) -> None:
    d = design(parts)
    d.harness("W5")
    with pytest.raises(AuthorError, match="already used"):
        d.harness("W5")


def test_harness_inside_a_function_lands_in_its_group(parts: Draft) -> None:
    d, e = design(parts), design(parts)
    with d.function("M1", "Pump"):
        d.harness("W5")
    group = e._engine.group("M1", "Pump")
    e._engine.harness(name="M1/W5", tag="W5", group=group)
    assert _records(d) == _records(e)
