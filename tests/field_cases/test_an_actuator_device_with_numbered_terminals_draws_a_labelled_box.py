"""Field case: a device whose only function is an `actuator` with four numbered terminals.
The bug: the core picked the motor-3ph-pe symbol and refused the page (PLACEMENT_PROBLEM ERROR, "port 3: no free port on symbol").
Fixed by el-0062 (R477 8.1, R479), an actuator row matches only the 3-phase port shape; any other shape draws the labelled box."""

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document

from electrical_symbols import GENERIC_BOX_KEY


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Valve", number="R-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-23", text="First issue", created="XX")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    q1 = d.device("Q1", "DEMO-ACT-4T")
    for n in range(1, 5):
        w1.core(n, x1[n], q1.actuator[n])
    return fr.build(d, unit_document(cab))


def test_the_actuator_device_draws_as_a_labelled_box_with_no_error() -> None:
    result = _built()
    errors = [f.message for f in result.findings if f.severity == fr.Severity.ERROR]
    assert errors == []
    symbols = [s for drawing in drawn_pages(result.model).values() for s in drawing.symbols]
    texts = [t.text for drawing in drawn_pages(result.model).values() for t in drawing.texts]
    assert [s.key for s in symbols if s.key == GENERIC_BOX_KEY] == [GENERIC_BOX_KEY]
    assert "-Q1" in texts
