"""Field case: a four-pin loop device wired by a screened cable to a part-less strip.

The engineering shape: one device with a function of four generic pins. Pins 2 and 4 are a
series element: they run through a two-pair screened cable to two terminals of an external
strip that has no part.

The bug (v0.21.1): the drawing set cannot be laid out. PLACEMENT_PROBLEM ERROR "could not be
laid out, so it has no page: KeyError: PinRef(sym=..., pin='n')", raised in
`topology_split.net_in` while the core cuts cycles of the flow. v0.20 laid it out. The correct
behaviour: the set has a page and no ERROR.

Covered by: F26 / XF-NETS (UNIT-SCOPE) - layout core.
Decision: layout-0391 (the attach carries its net).
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr

sys.path.insert(0, str(Path(__file__).parent / "data"))  # the invented four-pin loop part


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Loop", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    s1 = d.device("S1", "DEMO-LOOP-4P")
    x1 = d.terminal_strip("X1", None, 2, external=True)
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=20, external=True)
    d.series((s1.loop[2], s1.loop[4]), w1, (x1[1].outer, x1[2].outer))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Loop\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_the_set_is_laid_out_with_no_error() -> None:
    findings = _built().findings
    assert [f.code for f in findings if f.code == "PLACEMENT_PROBLEM"] == []
