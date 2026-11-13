"""`syms_of`: the `Sym` of each picked function, its row, table, box, stand, unit and errors."""
# NET_POTENTIAL_CONFLICT 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# WIRE_ROW_UNRESOLVED 6 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

import dataclasses

import pytest
from fransys_el.placement_kit import ProblemError
from fransys_el.placement_syms import syms_of
from placement_fixtures import leads, sid
lazy from fransys_el.placement_env import Env

from fransys_layout.core import Box, PinRef, Sym
from fransys_model.derive import stands
from fransys_model.derive.order import functions_in_order
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Function


def _sym(syms: tuple[Sym, ...], text: str) -> Sym:
    """The sym whose id is `text`."""
    return next(s for s in syms if s.id == text)


def _lead(env: Env, key: str) -> Id[Function]:
    """The lead function whose pick uses the symbol `key`."""
    return next(f for f, pick in leads(env.kit).items() if pick.key == key)


def test_strip_terminals_share_a_row_group(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """Each wired terminal has its strip's row group and a row footprint; a spare is no symbol."""
    env, syms = planted
    terminals = [_sym(syms, sid(env.model, t)) for t in ("1.terminal", "U1-1.terminal")]
    groups = {t.row_group for t in terminals}
    assert None not in groups
    assert len(groups) == 2
    assert all(t.row_footprint is not None for t in terminals)
    assert not {sid(env.model, "2.terminal"), sid(env.model, "3.terminal")} & {s.id for s in syms}
    coil = _sym(syms, sid(env.model, "K1.coil"))
    assert coil.row_group is None
    assert coil.row_footprint is None


def test_coil_has_a_contact_table(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A relay coil and an actuated group's lead switch have a contact table; a sensor has none."""
    env, _ = planted
    tables: dict[str, Box] = {}
    syms_of(env, tables)
    assert sid(env.model, "K1.coil") in tables
    assert sid(env.model, "S1.sw") in tables
    assert sid(env.model, "B1.sig") not in tables


def test_generic_box_sensor_has_a_box_spec(planted: tuple[Env, tuple[Sym, ...]]) -> None:
    """A two-wire sensor drawn as a generic box has a box spec; a breaker pole has none."""
    env, syms = planted
    sensor = _sym(syms, sid(env.model, "B1.sig"))
    assert sensor.box is not None
    assert sorted(sensor.box.order) == sorted(p.id for p in sensor.pins)
    assert set(sensor.views) == {"R0"}
    assert _sym(syms, sid(env.model, "Q1.element")).box is None


def test_stand_pins_are_exactly_the_rail_ports(demo: tuple[Env, tuple[Sym, ...]]) -> None:
    """Some pin carries an end bias, and no unbiased pin sits on a railed port."""
    env, syms = demo
    railed = {env.pins[port] for port in stands(env.model)}
    marked = [p for s in syms for p in s.pins if p.end_bias != 0]
    assert {p.end_bias for p in marked} == {-1}
    for sym in syms:
        for pin in sym.pins:
            if pin.end_bias == 0:
                assert PinRef(sym.id, pin.id) not in railed


@pytest.mark.parametrize("change", [lambda _: {"key": "no-such-symbol"}, lambda pick: {"ports": dict.fromkeys(pick.ports, "no-such-port")}])
def test_a_pick_the_library_lacks_raises_problem_with_fix(planted: tuple[Env, tuple[Sym, ...]], change) -> None:
    """A pick naming no library symbol, or mapping a port to a name its symbol lacks, makes `syms_of` raise `ProblemError` with a fix."""
    env, _ = planted
    lead = _lead(env, "coil")
    kit = dict(env.kit)
    kit[lead] = dataclasses.replace(env.kit[lead], **change(env.kit[lead]))
    with pytest.raises(ProblemError) as info:
        syms_of(dataclasses.replace(env, kit=kit))
    assert info.value.fix


def test_nested_unit_sym_differs_and_syms_keep_the_kit_order(
    planted: tuple[Env, tuple[Sym, ...]],
) -> None:
    """A sym inside a nested unit carries that unit's id, and syms come in function order (model-0396)."""
    env, syms = planted
    nested = _sym(syms, sid(env.model, "U1-1.terminal"))
    top = _sym(syms, sid(env.model, "1.terminal"))
    assert nested.unit != ""
    assert nested.unit != top.unit
    assert [s.id for s in syms] == [env.ids[lead] for lead in functions_in_order(env.model, env.kit)]
