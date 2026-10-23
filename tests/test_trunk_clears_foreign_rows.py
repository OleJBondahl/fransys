"""A trunk with no driver above it sits below the foreign boxes its drops pass (R369).

The 16-input and the machine panel of the placement corpus share a net whose trunks hang on
sensors in a late row. Without the clearance each trunk stood at the page top and the sensors had
no free path to it (ROUTE_FAILED); place_foreign now keeps it under the earlier rows' boxes.
"""

import importlib.util
from collections import Counter
from pathlib import Path

import pytest

_RUN = Path(__file__).parent.parent / "internal" / "placement_corpus" / "run.py"


def _codes(case: str) -> Counter[str]:
    spec = importlib.util.spec_from_file_location("corpus_run_r369", _RUN)
    assert spec is not None
    assert spec.loader is not None
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    (circuit,) = (c for c in run.circuits("standard") if c[0] == case)
    return Counter(f.code for f in run.build(case, circuit).findings)


@pytest.mark.private_input  # reads internal/ (R462)
@pytest.mark.parametrize("case", ["panel_di16p", "machine_panel"])
def test_every_sensor_reaches_its_trunk(case: str) -> None:
    assert _codes(case)["ROUTE_FAILED"] == 0
