"""The demo skid's readability counts may fall and never rise (DEMO-SKID K3).

`examples/demo-skid` is built once for the module. Its unit row of `fr.readability` is held to the
table below; no count is computed here. No byte golden: the drawings are meant to change. When a
layout change lowers a count, lower the number in the same branch.

Mapping of the spec's names to the readability fields: markers are `stars` (net references),
`contact_images` (coil images) and `page_cuts` (the readability reference set), crossings are
`wire_crossings`, excess bends are `wire_bends`, detour is `wire_length_mm`, pages are the unit's
`pages`; `loose_symbols` counts the two unwired analogue cards.
"""

import importlib.util
from decimal import Decimal
from pathlib import Path
from typing import Any

import fransys as fr
import pytest

SKID = Path(__file__).resolve().parent.parent / "examples" / "demo-skid" / "skid.py"

# Values at main c5ea722c1, V=16 valves, M=3 starters.
RATCHET: dict[str, int | Decimal] = {
    "stars": 4,
    "contact_images": 1,
    "wire_crossings": 3,
    "wire_bends": 18,
    "wire_length_mm": Decimal("2392.5"),
    "pages": 6,
    "page_cuts": 0,
    "loose_symbols": 2,  # AI1 and AI2: unwired analogue cards (READABILITY-LOOSE)
}


def risen(unit: Any, table: dict[str, int | Decimal]) -> dict[str, tuple[Any, Any]]:
    """Each field of `unit` above its table value, as `(now, allowed)`."""
    return {k: (getattr(unit, k), v) for k, v in table.items() if getattr(unit, k) > v}


@pytest.fixture(scope="module")
def skid_unit() -> Any:
    spec = importlib.util.spec_from_file_location("demo_skid_design", SKID)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    design, document = module.design()
    report = fr.readability(fr.build(fr.parts("demo_parts"), design, document))
    (unit,) = report.units
    return unit


def test_no_count_of_the_skid_rises(skid_unit: Any):
    assert risen(skid_unit, RATCHET) == {}


def test_the_check_names_a_count_above_its_value(skid_unit: Any):
    lowered = {**RATCHET, "stars": RATCHET["stars"] - 1}
    assert set(risen(skid_unit, lowered)) == {"stars"}
