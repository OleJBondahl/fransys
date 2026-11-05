"""`check_units` reports each unconnected, undeclared boundary of a cabinet (model-0320).

Two cabinets, the first declaring its two field-terminal boundaries unused, the second not:
the check gives one BOUNDARY_UNCONNECTED error per terminal of the second and nothing else.
"""

import fransys as fr
import fransys_parts
from _expected_codes import expect_codes
from fransys_author.design import Design
from scale_units_fixture import PROJECT, pump_cabinet

from fransys_model.checks.units import BOUNDARY_UNCONNECTED, check_units
from fransys_model.kernel import Severity


def test_check_units_reports_each_unconnected_boundary_of_the_undeclared_cabinet():
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    container = d.unit("scale-container", revision=1, interface="1")
    container.revision(1, date="2026-01-01", text="First release", created="XX")
    for i in (1, 2):
        field = pump_cabinet(container.scope(f"pump{i}", at=er), name=f"C{i}")
        if i == 1:
            for terminal in field:
                container.unused(terminal)
    result = fr.build(parts, d.draft())
    expect_codes(result, BOUNDARY_UNCONNECTED)
    findings = check_units(result.model)
    assert [(f.code, f.severity) for f in findings] == [(BOUNDARY_UNCONNECTED, Severity.ERROR)] * 2
