"""Field case: a reference marker on a terminal row must not wall in its neighbour's straight wire.
The bug: fr.build gave CONNECTION_NOT_DRAWN on two jumpers, as each marker box lay over a neighbour's lane.
Fixed by layout-0090, a reference marker box must leave a neighbouring straight wire a way round (CORPUS-FRAME, 2026-10-15)."""

import importlib.util
from pathlib import Path
from typing import Any

import fransys as fr
import pytest

SKID = Path(__file__).resolve().parents[2] / "examples" / "demo-skid" / "skid.py"


@pytest.fixture(scope="module")
def findings() -> list[Any]:
    spec = importlib.util.spec_from_file_location("demo_skid_field_case", SKID)
    assert spec is not None
    assert spec.loader is not None
    skid: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skid)
    skid.VALVES, skid.STARTERS = 3, 5
    design, document = skid.design()
    return list(fr.build(fr.parts("demo_parts"), design, document).findings)


def test_every_jumper_between_strip_terminals_is_drawn(findings: list[Any]):
    codes = {f.code for f in findings}
    assert "CONNECTION_NOT_DRAWN" not in codes
