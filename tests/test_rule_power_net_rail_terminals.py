"""POWER-NET (layout-0099 V3): no rail terminal stands a power symbol, in every case.

Six cases: the demo skid and the standard placement corpus (machine_panel, panel_di16p, remote_io,
distribution_board, mcc). Four have rail terminals; distribution_board and mcc have none and assert
"""

import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

import fransys as fr
import pytest

from fransys_model.derive import ConductorEnd, conductor_ends, far_pins, is_rail_terminal, required_drawn, stands, terminal_items
from fransys_model.derive.facts.conductor_facts import is_bridge
from fransys_model.derive.lookups import item_of_port
from fransys_model.vocab.tables import conductors, ports

_ROOT = Path(__file__).parent.parent
_SKID = _ROOT / "examples" / "demo-skid" / "skid.py"
_RUN = _ROOT / "internal" / "placement_corpus" / "run.py"


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _model(case: str) -> fr.Model:
    if case == "demo-skid":
        design, document = _load(_SKID, "demo_skid_rule").design()
        return fr.build(design, document).model
    run = _load(_RUN, "corpus_run_rule")
    (circuit,) = (c for c in run.circuits("standard") if c[0] == case)
    model = run.build(case, circuit).model
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


@pytest.mark.rule("DRAWN-LEDGER")
@pytest.mark.parametrize("case", _CASES)
def test_the_end_rows_equal_far_pins_and_read_each_conductor_twice(case: str) -> None:
    model = _model(case)
    ends = [r for r in required_drawn(model, tuple(ports(model))) if isinstance(r, ConductorEnd)]
    assert [(e.port, e.far) for e in ends] == list(far_pins(model, tuple(ports(model))))
    assert Counter(e.conductor for e in ends) == dict.fromkeys(
        (c for c in conductors(model) if not is_bridge(model, c)), 2
    )  # a bridge is no wire (R885)
    assert all({e.port, e.far} == set(conductor_ends(model, e.conductor)) for e in ends)


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
