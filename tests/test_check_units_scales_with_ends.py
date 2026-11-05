"""`check_units` does work in proportion to the ends it checks, not ends times units (model-0067).

The count of `end_crosses` calls stands in for time: it is exact and needs no wall clock.
Doubling the instances doubles the ends and the units, so linear work is 2x; the old loop of
"""

import fransys as fr
import fransys_parts
from _expected_codes import expect_codes
from fransys_author.design import Design
from scale_units_fixture import (
    PROJECT,
    build_scale,
    pump_cabinet,
)

from fransys_model.checks import units as validators
from fransys_model.derive.facts import unit_crossings
from fransys_model.derive.numbering_pins import name_findings
from fransys_model.kernel import Severity


def _crosses_calls(monkeypatch, model):
    """How many times `check_units(model)` calls `end_crosses`, counted from zero."""
    calls = 0
    original = unit_crossings.end_crosses

    def counting(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(unit_crossings, "end_crosses", counting)
    validators.check_units(model)
    return calls


def test_check_units_calls_grow_linearly_with_the_instances(monkeypatch):
    small = _crosses_calls(monkeypatch, build_scale(10).model)
    large = _crosses_calls(monkeypatch, build_scale(20).model)
    assert small > 0
    assert large <= 2.5 * small


def test_the_findings_of_three_instances_with_one_unused_declaration_missing():
    """Pump 2's two field terminals are boundaries left unconnected and undeclared; nothing else."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    container = d.unit("scale-container", revision=1, interface="1")
    container.revision(1, date="2026-01-01", text="First release", created="XX")
    for i in (1, 2, 3):
        field = pump_cabinet(container.scope(f"pump{i}", at=er), name=f"C{i}")
        if i != 2:
            for terminal in field:
                container.unused(terminal)
    result = fr.build(parts, d.draft())
    expect_codes(result, "BOUNDARY_UNCONNECTED")
    model = result.model
    findings = name_findings(model, validators.check_units(model))
    assert [f.severity for f in findings] == [Severity.ERROR, Severity.ERROR]
    tail = " of demo-pump-cabinet rev 1.2 is not connected across it and has no declared UnusedBoundary"
    assert sorted(f.message for f in findings) == [
        f"boundary function -X2:1{tail}",
        f"boundary function -X2:2{tail}",
    ]
