"""`facts_of`: keep-whole sets, units with their boundary, and mates."""

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys_el.placement_env import Env, make_env, pin_ref
from fransys_el.placement_facts import facts_of
from fransys_el.placement_syms import syms_of
from fransys_el.symbol_kit import symbol_kit
from placement_fixtures import kit_for, planted_model, sid

from electrical_symbols import LIBRARY
from fransys_layout.core import Facts, Sym, Unit
from fransys_model.derive import item_designation, mate_ports, port_function, unit_boundary_pins
from fransys_model.kernel import render_id
from fransys_model.vocab import functions, units
lazy from fransys_model.kernel import Model


def _built(model: Model) -> tuple[Env, tuple[Sym, ...], Facts]:
    """The env, syms and facts of `model`."""
    env = make_env(model, kit_for(model), house(), LIBRARY)
    syms = syms_of(env)
    return env, syms, facts_of(env, syms)[0]


@pytest.fixture(scope="module")
def planted() -> tuple[Env, tuple[Sym, ...], Facts]:
    """The planted model's env, syms and facts, built once for the module."""
    return _built(planted_model())


@pytest.fixture(scope="module")
def add_on() -> tuple[Env, tuple[Sym, ...], Facts]:
    """A relay with one add-on block nested under it, built once for the module."""
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    k1b = d.device("K1B", "DEMO-RLY-2CO-24", parent=k1)
    d.detail.wire(k1.coil["A2"], k1b.coil["A1"], wire=0.75)
    return _built(fr.build(d).model)


def test_coil_and_add_on_block_are_one_keep_whole_set(
    add_on: tuple[Env, tuple[Sym, ...], Facts],
) -> None:
    """A coil and its add-on block stand in one set; every set has two symbols or more."""
    env, _, facts = add_on
    assert all(len(s) >= 2 for s in facts.keep_whole)
    together = [
        s for s in facts.keep_whole if {sid(env.model, "K1.coil"), sid(env.model, "K1B.coil")} <= s
    ]
    assert len(together) == 1


def test_a_lone_symbol_is_in_no_keep_whole_set(
    planted: tuple[Env, tuple[Sym, ...], Facts],
) -> None:
    """The sensor box has no child, so no set holds it; the relay's coil is in none either."""
    env, _, facts = planted
    assert all(len(s) > 1 for s in facts.keep_whole)  # a set of one symbol is no set
    assert not any(sid(env.model, "S1.sw") in s for s in facts.keep_whole)
    assert not any(sid(env.model, "B1.sig") in s for s in facts.keep_whole)


def test_units_carry_parent_and_boundary(planted: tuple[Env, tuple[Sym, ...], Facts]) -> None:
    """Each unit has its parent and the pins its boundary functions drew."""
    env, _, facts = planted
    expected = tuple(
        Unit(
            u.value,
            None if record.parent is None else record.parent.value,
            tuple(
                pin_ref(env, p) for p in unit_boundary_pins(env.model, u) if p not in env.undrawn
            ),
        )
        for u, record in units(env.model).items()
    )
    assert facts.units == expected
    assert facts.units
    assert all(unit.boundary for unit in facts.units)


def test_mates_are_the_mated_ports_drawn_as_pins(
    planted: tuple[Env, tuple[Sym, ...], Facts],
) -> None:
    """Each mate pair of the model comes out as the pair of its pin refs."""
    env, _, facts = planted
    expected = tuple((pin_ref(env, a), pin_ref(env, b)) for a, b in mate_ports(env.model))
    assert facts.mates == expected
    assert facts.mates


def test_functions_without_a_symbol_are_skipped_and_named() -> None:
    """A kit without the add-on block's functions: each is ``Skipped`."""
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    d.device("K1B", "DEMO-RLY-2CO-24", parent=k1)
    model = fr.build(d).model
    own = {f for f, r in functions(model).items() if item_designation(model, r.item) == "K1B"}
    assert len(own) == 3
    kit = frozendict({f: p for f, p in kit_for(model).items() if f not in own})
    env = make_env(model, kit, house(), LIBRARY)
    _, skipped = facts_of(env, syms_of(env))
    assert [(s.what, s.id, s.reason) for s in skipped] == [
        ("function", text, "function_without_symbol") for text in sorted(map(render_id, own))
    ]


def test_a_boxed_connector_is_drawn_by_its_pins_and_an_unwired_one_is_unwired() -> None:
    """el-0053: a header's drawn pins join its parent's set; one with no pin drawn is unwired."""
    d = fr.design("demo_parts")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    j1 = d.device("J1", "DEMO-CONN-4P", parent=k1)
    d.device("J2", "DEMO-CONN-4P", parent=k1)
    d.detail.wire(j1["1"], k1.coil["A1"], wire=0.75)
    d.detail.wire(j1["3"], k1.coil["A2"], wire=0.75)
    model = fr.build(d).model
    env = make_env(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    facts, skipped = facts_of(env, syms_of(env))
    by_item = {item_designation(model, r.item): f for f, r in functions(model).items()}
    pins = {env.owner[p] for p in env.pins if port_function(model, p) == by_item["J1"]}
    assert len(pins) == 2  # pins 1 and 3 are drawn
    box = [s for s in facts.keep_whole if sid(model, "K1.coil") in s]
    assert len(box) == 1
    assert pins <= box[0]
    assert [(s.id, s.reason) for s in skipped if s.what == "function"] == [
        (render_id(by_item["J2"]), "function_unwired")
    ]
