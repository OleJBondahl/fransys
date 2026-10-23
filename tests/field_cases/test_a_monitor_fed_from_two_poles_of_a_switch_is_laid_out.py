"""Field case: a monitor whose measuring function is fed from two poles of a switch.

The engineering shape: a two-pole DC switch. Each pole runs through its own fuse to a
connector function of a monitor; the connector pins join the ports of an inner `measure`
function (`joins`), so the monitor's measuring ports Lp1 and Lm1 stand on the two nets.

The bug (v0.21.1): the drawing set cannot be laid out. PLACEMENT_PROBLEM ERROR "TrunkError:
Lp1 is on pole 2, but the bundle has 3 lanes and 2 nets", raised in `route_trunk._check_poles`.
v0.20 laid it out. The correct behaviour: the set has a page and no ERROR.

Covered by: BUNDLE (R283), the bundle's poles and nets - layout core.
Decision: layout-0392 (a bundle has one lane per pole in use).
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BK, RD

sys.path.insert(0, str(Path(__file__).parent / "data"))  # the invented monitor part


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Monitor", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    s1 = d.device("S1", "DEMO-SWITCH-DC-2P")
    f2, f5 = d.device("F2", "DEMO-FUSE-DC-160"), d.device("F5", "DEMO-FUSE-DC-160")
    a4 = d.device("A4", "DEMO-MONITOR-JOINS")
    d.series(s1.main.pole(1), f2.element, wire=(RD, 0.5))
    d.detail.wire(f2.element[2], a4.LA[1], wire=(RD, 0.5))
    d.series(s1.main.pole(2), f5.element, wire=(BK, 0.5))
    d.detail.wire(f5.element[2], a4.LB[1], wire=(BK, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Monitor\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_the_set_is_laid_out_with_no_error() -> None:
    errors = [f.message for f in _built().findings if f.severity == fr.Severity.ERROR]
    assert errors == []
