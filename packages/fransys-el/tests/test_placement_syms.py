"""`syms_of`: the `Sym` of each picked function, its row, table, box, stand, unit and errors."""

import dataclasses

import pytest
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_kit import ProblemError
from fransys_el.placement_options import Conventions
from fransys_el.placement_syms import syms_of
from placement_fixtures import demo_model, kit_for, planted_model, sid

from fransys_layout.core import PinRef, Sym, natural_key
from fransys_model.derive import stands
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Function


@pytest.fixture(scope="module")
def planted() -> tuple[Env, tuple[Sym, ...]]:
    """The planted model's env and syms, built once for the module."""
    model = planted_model()
    env = make_env(model, kit_for(model), Conventions())
    return env, syms_of(env)


@pytest.fixture(scope="module")
def demo() -> tuple[Env, tuple[Sym, ...]]:
    """The demo model's env and syms, built once for the module."""
    model = demo_model()
    env = make_env(model, kit_for(model), Conventions())
    return env, syms_of(env)


def _sym(syms: tuple[Sym, ...], text: str) -> Sym:
    """The sym whose id is `text`."""
    return next(s for s in syms if s.id == text)


def _lead(env: Env, key: str) -> Id[Function]:
    """The lead function whose pick uses the symbol `key`."""
    return next(f for f, pick in env.kit.items() if pick.key == key)


def test_strip_terminals_share_a_row_group(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """The three terminals of one strip share a row group and have a row footprint."""
    env, syms = planted
    terminals = [
        _sym(syms, t)
        for t in (
            sid(env.model, "1.terminal"),
            sid(env.model, "2.terminal"),
            sid(env.model, "3.terminal"),
        )
    ]
    groups = {t.row_group for t in terminals}
    assert None not in groups
    assert len(groups) == 1
    assert all(t.row_footprint is not None for t in terminals)
    coil = _sym(syms, sid(env.model, "K1.coil"))
    assert coil.row_group is None
    assert coil.row_footprint is None


def test_coil_has_a_contact_table(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A relay coil with contacts has a contact table; its footprint is taller than its body."""
    env, syms = planted
    coil = _sym(syms, sid(env.model, "K1.coil"))
    assert coil.table is not None
    assert coil.footprint.h > coil.body.h
    assert _sym(syms, sid(env.model, "S1.sw")).table is None


def test_generic_box_sensor_has_a_box_spec(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A two-wire sensor drawn as a generic box has a box spec; a breaker pole has none."""
    env, syms = planted
    sensor = _sym(syms, sid(env.model, "B1.sig"))
    assert sensor.box is not None
    assert sorted(sensor.box.order) == sorted(p.id for p in sensor.pins)
    assert sensor.orientations == frozenset({"R0"})
    assert _sym(syms, sid(env.model, "Q1.element")).box is None


def test_stand_pins_are_exactly_the_rail_ports(demo: tuple[Env, tuple[Sym, ...]]) -> None:
    """Some pin carries a power stand, and no unmarked pin sits on a railed port."""
    env, syms = demo
    railed = {env.pins[port] for port in stands(env.model)}
    marked = [p for s in syms for p in s.pins if p.stand is not None]
    assert any(p.stand in {"SUPPLY", "GROUND", "PE"} for p in marked)
    for sym in syms:
        for pin in sym.pins:
            if pin.stand is None:
                assert PinRef(sym.id, pin.id) not in railed


def test_unknown_symbol_key_raises_problem(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A pick naming no library symbol makes `syms_of` raise `ProblemError`."""
    env, _ = planted
    lead = _lead(env, "coil")
    kit = dict(env.kit)
    kit[lead] = dataclasses.replace(env.kit[lead], key="no-such-symbol")
    with pytest.raises(ProblemError):
        syms_of(dataclasses.replace(env, kit=kit))


def test_unknown_port_name_raises_problem_with_fix(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A pick mapping a port to a name its symbol lacks raises `ProblemError` with a fix."""
    env, _ = planted
    lead = _lead(env, "coil")
    pick = env.kit[lead]
    bad = dataclasses.replace(pick, ports=dict.fromkeys(pick.ports, "no-such-port"))
    kit = dict(env.kit)
    kit[lead] = bad
    with pytest.raises(ProblemError) as info:
        syms_of(dataclasses.replace(env, kit=kit))
    assert info.value.fix


def test_nested_unit_sym_differs_and_syms_sort_naturally(
    planted: tuple[Env, tuple[Sym, ...]],
) -> None:
    """A sym inside a nested unit carries that unit's id, and syms come in natural id order."""
    env, syms = planted
    nested = _sym(syms, sid(env.model, "U1-1.terminal"))
    top = _sym(syms, sid(env.model, "1.terminal"))
    assert nested.unit != ""
    assert nested.unit != top.unit
    ids = [s.id for s in syms]
    assert ids == sorted(ids, key=natural_key)
