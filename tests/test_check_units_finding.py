"""`check_units` reports each unconnected, undeclared boundary of a cabinet (model-0320).

Two cabinets, the first declaring its two field-terminal boundaries unused, the second not:
the check gives one BOUNDARY_UNCONNECTED error per terminal of the second and nothing else.
"""

import sys
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import PROJECT, pump_cabinet  # noqa: E402 - path set above

from fransys_model.checks.units import BOUNDARY_UNCONNECTED, check_units  # noqa: E402 - path set above
from fransys_model.kernel import Severity  # noqa: E402 - path set above


def test_check_units_reports_each_unconnected_boundary_of_the_undeclared_cabinet():
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
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
    model = fr.build(parts, d.draft()).model
    findings = check_units(model)
    assert [(f.code, f.severity) for f in findings] == [
        (BOUNDARY_UNCONNECTED, Severity.ERROR),
        (BOUNDARY_UNCONNECTED, Severity.ERROR),
    ]
