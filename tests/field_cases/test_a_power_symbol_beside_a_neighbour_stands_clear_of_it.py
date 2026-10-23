"""Field case: the earth symbol of a supply's PE pin stands clear of the breaker beside the supply.

The engineering shape: 230 V AC from a terminal strip through a two-pole breaker into a protection
class I 24 V supply, whose PE pin is wired to the strip's PE terminal.

The bug: the supply's PE pin sits at its top edge, a step from the breaker that feeds it. The earth
symbol was posed straight out from the pin only, so it overlapped the breaker's body
(an OVERLAP finding). A card box's anchored outlines were also left out of its footprint, so
a card pin at the page top had its symbol cut by the frame (the seven cases cover that one).

The rule (decision el-0050, R360): an anchored item takes the first of its poses that meets no
body, no other anchored item and not the page frame, and the owner's footprint holds the first pose.
"""

from typing import TYPE_CHECKING

import fransys as fr
import fransys_el.placement_anchors as poses
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _build(folder: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    with d.function("SUP", "Incoming supply 230 V AC"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
        line, neutral, pe = x0.run("L", 1), x0.run("N", 1), x0.run("PE", 1)
        ac = d.ac_supply("230V", 230, line[1], n=neutral[1])
        q0 = d.device("Q0", "DEMO-MCB-2P")
        g1 = d.device("G1", "DEMO-PSU-24-PE")
        d.series(ac.L1, q0.pole_1, g1.input, q0.pole_2, ac.N, wire=(BK, 1.5))
        d.earth(pe[1], g1["PE"])
        d.dc_supply("24VDC", g1.output)
    cover = folder / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, d.location("CAB", "Cabinet"), cover=cover
    )
    return fr.build(d, doc)


def _overlaps(built: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(built) if f.code == "OVERLAP"]


def test_the_earth_symbol_of_the_supply_meets_no_neighbour(tmp_path: Path) -> None:
    assert _overlaps(_build(tmp_path)) == []


def test_with_only_the_straight_pose_the_earth_symbol_meets_the_breaker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Planted: offering the straight pose alone brings the overlap back, so the check can fail."""
    monkeypatch.setattr(poses, "_APPROACHES", ((0, 1),))
    assert _overlaps(_build(tmp_path))
