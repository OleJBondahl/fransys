"""Field case: designations that differ only by a number list in numeric order.
The bug: every list sorted designations as whole strings, so -W10 came before -W2.
Fixed by model-0149, lists sort designations in natural order, as terminal numbers already do."""

import fransys as fr
import pytest

from fransys_model.derive import bom_lines, cable_list_rows
from fransys_model.derive.harness import all_cables, top_level_cables

_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_WANTED = ("-W1", "-W2", "-W10")


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """Cables W10, W1 and W2, declared out of order, one cable each."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    for tag in ("W10", "W1", "W2"):
        with d.function(tag, f"Cable {tag}"):
            near = d.device(f"A{tag}", _PLUG, place="L0")
            far = d.device(f"B{tag}", _PLUG, place="L0")
            d.cable(tag, _CABLE, name=f"cable{tag}", place="L0").core(1, near[1], far[1])
    return fr.build(d)


def test_the_bom_lists_designations_in_numeric_order(built: fr.BuildResult) -> None:
    """The cable's BOM line prints -W1, -W2, -W10."""
    (line,) = [line for line in bom_lines(built.model) if line.mpn == _CABLE]
    assert line.designations == _WANTED


def test_the_cable_list_runs_in_numeric_order(built: fr.BuildResult) -> None:
    """The cable list rows run -W1, -W2, -W10."""
    assert tuple(row.designation for row in cable_list_rows(built.model)) == _WANTED


def test_the_cable_pages_run_in_numeric_order(built: fr.BuildResult) -> None:
    """The cable pages, top-level and model-wide, run -W1, -W2, -W10."""
    assert tuple(c.designation for c in top_level_cables(built.model)) == _WANTED
    assert tuple(c.designation for c in all_cables(built.model)) == _WANTED
