"""Field case: a reference marker on a terminal row must not wall in its neighbour's straight wire.

The engineering shape: a strip of terminals in a row at wire pitch, each terminal fed straight
down from the one above (a row jumper) while a net reference marker stands on one of them.
Reduced from the demo skid (examples/demo-skid, decision 0199) at 5 starters and 3 valves.

The bug: `fr.build` gave ROUTE_FAILED and CONNECTION_NOT_DRAWN (errors) on two jumpers. The
marker's turned box has two places, one each side of its pin, and at that pitch each lay over
the lane of a neighbouring terminal's straight wire, which then had no way round.

Reported by CORPUS-FRAME, reproduced 2026-10-15. Fixing decision: layout-0090.
"""

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
    assert "ROUTE_FAILED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes
