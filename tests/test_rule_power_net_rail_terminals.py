"""POWER-NET (layout-0099 V3): no rail terminal stands a power symbol, in every case.

Six cases: the demo skid and the standard placement corpus (machine_panel, panel_di16p, remote_io,
distribution_board, mcc). Four have rail terminals; distribution_board and mcc have none and assert
that. The seventh case, pump-station, lives in the examples repository and is not covered here.
"""

import importlib.util
from pathlib import Path
from typing import Any

import fransys as fr
import pytest

from fransys_model.derive import is_rail_terminal, stands, terminal_items
from fransys_model.derive.lookups import item_of_port

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
    return run.build(case, circuit).model


#: case -> whether the model has a rail terminal. distribution_board and mcc have none, so for them
#: the test states the opposite fact (no rail terminal) and nothing is drawn for it to bar.
HAS_RAIL = {
    "demo-skid": True,
    "machine_panel": True,
    "panel_di16p": True,
    "remote_io": True,
    "distribution_board": False,
    "mcc": False,
}


@pytest.mark.rule("POWER-NET")
@pytest.mark.parametrize(
    "case",
    [
        c if c == "demo-skid" else pytest.param(c, marks=pytest.mark.private_input)  # R462
        for c in HAS_RAIL
    ],
)
def test_no_rail_terminal_is_drawn_or_stands_a_power_symbol(case: str) -> None:
    model = _model(case)
    rail = {i for i in terminal_items(model) if is_rail_terminal(model, i)}
    assert bool(rail) is HAS_RAIL[case], f"{case}: the case's rail terminals changed"
    assert not {p for p in stands(model) if item_of_port(model, p) in rail}
