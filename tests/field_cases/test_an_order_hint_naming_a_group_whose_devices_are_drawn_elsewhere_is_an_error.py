"""Field case: a relay made in group MOD whose every function is wired by a `d.series` written in group RUN, and `d.layout.order(mod, run)`.
The bug: the placement core refused with PLACEMENT_PROBLEM ("No call clears this"), because MOD draws no symbol.
Fixed by model-0441 (R1841): the model check ORDER_GROUP_DRAWS_NOTHING names MOD and RUN and the fix."""

import fransys as fr
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document
from fransys.colours import BU


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Hints", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    with d.function("MOD", "Module") as mod:
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
    with d.function("RUN", "Run") as run:
        g1 = d.device("G1", "DEMO-PSU-24")
        h1 = d.device("H1", "DEMO-LAMP-24")
        d.series(g1.output["+"], k1.coil, g1.output["-"], wire=(BU, 0.5))
        d.series(g1.output["+"], k1.co_1.no, h1.lamp, g1.output["-"], wire=(BU, 0.5))
        d.series(g1.output["+"], k1.co_2.no, h1.lamp, g1.output["-"], wire=(BU, 0.5))
    d.layout.order(mod, run)
    return fr.build(d, cabinet_document(cab))


def test_an_order_hint_naming_a_group_drawn_elsewhere_gives_the_model_error_and_no_placement_problem() -> None:
    result = _build()
    assert "PLACEMENT_PROBLEM" not in {f.code for f in result.findings}
    expect_codes(result, "ORDER_GROUP_DRAWS_NOTHING")
    (found,) = [f for f in result.findings if f.code == "ORDER_GROUP_DRAWS_NOTHING"]
    assert found.severity is fr.Severity.ERROR
    assert "=MOD" in found.message
    assert "=RUN" in found.message
    assert "drop the hint" in found.message
