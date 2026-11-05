"""Field case: a four-pin loop device wired by a screened cable to a part-less strip is laid out.
The bug (v0.21.1): the drawing set could not be laid out, a PLACEMENT_PROBLEM ERROR with "KeyError: PinRef(...)".
Fixed by layout-0391, the attach carries its net, so the set has a page and no ERROR."""

import fransys as fr
from _model_build_cover import unit_document


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Loop", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    s1 = d.device("S1", "DEMO-LOOP-4P")
    x1 = d.terminal_strip("X1", None, 2, external=True)
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=20, external=True)
    d.series((s1.loop[2], s1.loop[4]), w1, (x1[1].outer, x1[2].outer))
    return fr.build(d, unit_document(cab))


def test_the_set_is_laid_out_with_no_error() -> None:
    findings = _built().findings
    assert [f.code for f in findings if f.code == "PLACEMENT_PROBLEM"] == []
