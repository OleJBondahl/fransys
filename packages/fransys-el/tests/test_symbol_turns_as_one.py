"""FLOW-DOWN, R537: every symbol's cells share one turn, over the builds the tests already have."""

from __future__ import annotations

import importlib
from collections import defaultdict
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from _model_build_cover import unit_document
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.drawn_netlist import POWER_KEYS
from fransys_el.placement_anchors import stood
from fransys_el.placement_options import options
from ring_cases import bank_model, box_kit

from electrical_symbols import LIBRARY, power_symbol_key
from fransys_layout.core import build_flow

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ("machine_panel", "panel_di16p", "remote_io", "distribution_board", "mcc")


def _flow(model, kit) -> Any:
    problem, _ = build(model, kit, house(), LIBRARY)
    return build_flow(problem, options(house(), LIBRARY))


def _kinds(model, kit) -> set[str]:
    """The `PowerKind` values of the anchors the problem of `model` carries."""
    problem, _ = build(model, kit, house(), LIBRARY)
    assert len(problem.anchors) == len(list(stood(model, kit)))
    return {kind for *_, kind in stood(model, kit)}


def _motor_with_pe() -> Any:
    """A starter feeding a motor by three bundled poles, with a lone PE wire to a terminal."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Starter"):
        x = d.terminal_strip("X3", "DEMO-TB-2.5", 4)
        ol = d.device("F13", "DEMO-OVERLOAD-3P")
        m = d.device("M1", "DEMO-MOTOR-4KW")
        for i, a in enumerate("135"):
            d.series(x[i + 1].outer, ol.main[a], wire=(BU, 2.5))
            d.series(ol.main[str(int(a) + 1)], m.motor["UVW"[i]], wire=(BU, 2.5))
        d.earth(m.motor["PE"], x[4].outer)
    model = fr.build(d, unit_document(cab)).model
    return model, symbol_kit(model, LIBRARY)


def _bank() -> Any:
    model = bank_model(8)
    return model, box_kit(model)


def _corpus(name: str) -> Any:
    """A standard placement-corpus design (R538: the whole class over the builds the tests have)."""
    module = importlib.import_module(f"placement_corpus.standard.{name}")
    model = fr.build(*module.design()).model
    return model, symbol_kit(model, LIBRARY)


def _turns(flow: Any) -> dict[str, set[str]]:
    turns: dict[str, set[str]] = defaultdict(set)
    for column in flow.columns:
        for lane in column.lanes:
            for cell in lane.cells:
                turns[cell.sym].add(cell.orient)
    return turns


BUILDS = [
    _motor_with_pe,
    _bank,
    *(pytest.param(lambda n=n: _corpus(n), id=n, marks=pytest.mark.private_input) for n in CORPUS),
]


# R813: layout trusts `problem.anchors`; each is a port that the drawn netlist joins as a power rail
@pytest.mark.parametrize("make", BUILDS)
def test_every_anchor_of_a_build_is_a_port_the_drawn_netlist_joins_as_power(make) -> None:
    kinds = _kinds(*make())
    assert {power_symbol_key(k) for k in kinds} <= POWER_KEYS


@pytest.mark.rule("FLOW-DOWN")
@pytest.mark.parametrize("make", BUILDS)
def test_every_symbols_cells_share_one_turn(make) -> None:
    turns = _turns(_flow(*make()))
    assert turns
    assert {sym: t for sym, t in turns.items() if len(t) > 1} == {}


def test_the_motor_stands_in_four_chains_of_one_symbol() -> None:
    flow = _flow(*_motor_with_pe())
    cells = [c for col in flow.columns for lane in col.lanes for c in lane.cells if c.sym.startswith("M1 ")]
    assert len(cells) == 4
