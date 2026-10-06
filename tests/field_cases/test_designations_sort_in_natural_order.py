"""Field case: designations that differ only by a number list in numeric order.

The engineering shape: three looms tagged W1, W2 and W10, each holding one cable of the same
type, so the cables print `-W1`, `-W2` and `-W10`. A reader expects the BOM, the cable list and
the cable pages to run -W1, -W2, -W10, as terminal numbers already do (`L1:2` before `L1:10`).

The bug: every list sorted designations as whole strings, so `-W10` came before `-W2`.

Raised by a consumer, 2026-10-06. Fixed by decision model-0149.
"""

import fransys as fr
import pytest

from fransys_model.derive import bom_lines, cable_list_rows
from fransys_model.derive.harness import all_cables, top_level_cables

_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_WANTED = ("-W1", "-W2", "-W10")


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """Looms W10, W1 and W2, declared out of order, one cable each."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    for tag in ("W10", "W1", "W2"):
        with d.function(tag, f"Loom {tag}"):
            loom = d.harness(tag, place="L0")
            near = d.device("J1", _PLUG, parent=loom, place="L0")
            far = d.device("J2", _PLUG, parent=loom, place="L0")
            d.cable(tag, _CABLE, parent=loom, name=f"cable{tag}", place="L0").core(
                1, near[1], far[1]
            )
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
