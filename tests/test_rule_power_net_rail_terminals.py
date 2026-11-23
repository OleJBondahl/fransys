"""POWER-NET (layout-0099 V3): no rail terminal stands a power symbol, in every case.

Six cases: the demo skid and the standard placement corpus (machine_panel, panel_di16p, remote_io,
distribution_board, mcc). Four have rail terminals; distribution_board and mcc have none and assert
"""

import functools
import importlib
import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any
lazy from collections.abc import Sequence

import fransys as fr
import pytest
from hypothesis import given
from hypothesis import strategies as st
from plant import Plant

from fransys_model.derive import ConductorEnd, FunctionSymbol, conductor_ends, is_rail_terminal, required_drawn, stands, terminal_items
from fransys_model.derive.facts.conductor_facts import drawn_conductors, is_bridge, is_rail_bond
from fransys_model.derive.lookups import item_of_port
from fransys_model.vocab.tables import conductors, ports

_ROOT = Path(__file__).parent.parent
_SKID = _ROOT / "examples" / "demo-skid" / "skid.py"


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.cache
def _model(case: str) -> fr.Model:
    if case == "mated":  # the pool's one model with a MateEnd (mates are refused at the check, so no consumer case has one)
        plant = Plant()
        plant.item("plug", designation="X1")
        plant.item("socket", designation="X2")
        plant.pin("plug", "J1", "1")
        plant.pin("socket", "J1", "1")
        plant.mate(Plant.function_id("plug", "J1"), Plant.function_id("socket", "J1"))
        return plant.model()
    if case == "demo-skid":
        design, document = _load(_SKID, "demo_skid_rule").design()
        return fr.build(design, document).model
    model = importlib.import_module("placement_corpus.run").observed(case).result.model  # internal/ is not exported
    assert isinstance(model, fr.Model)
    return model


#: case -> whether the model has a rail terminal. distribution_board and mcc have none, so for them
#: the test states the opposite fact (no rail terminal) and nothing is drawn for it to bar.
HAS_RAIL = {
    "demo-skid": True,
    "machine_panel": True,  # RAIL-FLAG (R921): the first input card is its 0V rail; the groups left unflagged are KI-283
    "panel_di16p": True,
    "remote_io": True,
    "distribution_board": False,
    "mcc": False,
}


_CASES = [c if c == "demo-skid" else pytest.param(c, marks=pytest.mark.private_input) for c in HAS_RAIL]  # R462


@pytest.mark.rule("POWER-NET")
@pytest.mark.parametrize("case", _CASES)
def test_no_rail_terminal_is_drawn_or_stands_a_power_symbol(case: str) -> None:
    model = _model(case)
    rail = {i for i in terminal_items(model) if is_rail_terminal(model, i)}
    assert bool(rail) is HAS_RAIL[case], f"{case}: the case's rail terminals changed"
    assert not {p for p in stands(model) if item_of_port(model, p) in rail}


@pytest.fixture(scope="module")
def pool_model(request: pytest.FixtureRequest) -> fr.Model:
    return _model(request.param)


def _ends(model: fr.Model, scope: Sequence[Any]) -> list[Any]:
    return [r for r in required_drawn(model, scope) if not isinstance(r, FunctionSymbol)]


@pytest.mark.rule("DRAWN-LEDGER")
@pytest.mark.parametrize("pool_model", [*_CASES, "mated"], indirect=True)
@given(data=st.data())
def test_the_required_ends_are_local_unordered_and_read_each_conductor_by_its_ends(pool_model: fr.Model, data: st.DataObject) -> None:
    """C1: each end at a scope port is one row; a function symbol is one row whatever the scope."""
    model = pool_model
    scope = data.draw(st.lists(st.sampled_from(tuple(ports(model))), unique=True, max_size=60))
    cut = data.draw(st.integers(0, len(scope)))
    ends = _ends(model, scope)
    assert Counter(ends) == Counter(_ends(model, scope[:cut]) + _ends(model, scope[cut:]))  # 1 locality
    assert Counter(ends) == Counter(_ends(model, data.draw(st.permutations(scope))))  # 2 order
    for e in (e for e in ends if isinstance(e, ConductorEnd)):  # 3 each end names its conductor's two ports
        assert {e.port, e.far} == set(conductor_ends(model, e.conductor))
        assert not is_bridge(model, e.conductor)  # a bridge is no wire (R885)
    rows = Counter(e.conductor for e in ends if isinstance(e, ConductorEnd))
    for c in conductors(model):  # 4 both ends in scope, two rows
        assert rows[c] == (0 if is_bridge(model, c) else sum(p in scope for p in conductor_ends(model, c)))
    symbols = [r for r in required_drawn(model, scope) if isinstance(r, FunctionSymbol)]
    assert symbols == [r for r in required_drawn(model, ()) if isinstance(r, FunctionSymbol)]  # 5 the same for every scope
    assert len(symbols) == len(set(symbols))


def _strip_model(*, rail: bool) -> fr.Model:
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 3).run("L", 3, bridged=True, rail=rail)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", 3).run("L", 3, bridged=True, rail=rail)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    return fr.build(d).model


@pytest.mark.rule("POWER-NET")
def test_a_group_is_a_rail_only_when_it_is_flagged() -> None:
    """R885: the same bridged strips are rail terminals flagged, plain terminals unflagged."""
    flagged, plain = _strip_model(rail=True), _strip_model(rail=False)
    assert {i for i in terminal_items(flagged) if is_rail_terminal(flagged, i)}
    assert not {i for i in terminal_items(plain) if is_rail_terminal(plain, i)}


# INK_WITHOUT_CONDUCTOR: a falling stock of this file's builds on KI-974 (docs/KNOWN-ISSUES.toml, el-0130).


@pytest.mark.rule("POWER-NET")
@pytest.mark.private_input
def test_a_conductor_between_two_flagged_rails_of_one_potential_is_a_bond_and_draws_no_wire() -> None:
    """R3310: remote_io with its 0V runs flagged builds with no ERROR and no dangling end; its core between two 0V rails is a bond."""
    run = importlib.import_module("placement_corpus.run")  # internal/ is not exported
    (_, module, _, values) = next(c for c in run.circuits("standard") if c[0] == "remote_io")
    result = run.build("remote_io_0v_rails", ("remote_io_0v_rails", module, {"rail_0v": True}, values))
    model = result.model
    bonds = {c for c in conductors(model) if is_rail_bond(model, c)}
    assert bonds
    assert not bonds & drawn_conductors(model)
    assert not [f.code for f in result.findings if f.severity.name == "ERROR" or f.code == "DANGLING_WIRE_END"]
