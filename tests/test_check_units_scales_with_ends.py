"""`check_units` does work in proportion to the ends it checks, not ends times units (model-0067).

The count of `_Plant.crosses` calls stands in for time: it is exact and needs no wall clock.
Doubling the instances doubles the ends and the units, so linear work is 2x; the old loop of
every end over every unit was 4x.
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

from scale_units_fixture import (  # noqa: E402
    PROJECT,
    build_scale,
    pump_cabinet,
)

from fransys_model.kernel import Severity  # noqa: E402
from fransys_model.vocab.validators import units as validators  # noqa: E402


def _crosses_calls(monkeypatch, model):
    """How many times `check_units(model)` calls `_Plant.crosses`, counted from zero."""
    calls = 0
    original = validators._Plant.crosses

    def counting(self, subtree, item, other):
        nonlocal calls
        calls += 1
        return original(self, subtree, item, other)

    monkeypatch.setattr(validators._Plant, "crosses", counting)
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
    d = fransys_author.Design(parts)
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
    findings = validators.check_units(fr.build(parts, d.draft()).model)
    assert [(f.code, f.severity) for f in findings] == [
        ("BOUNDARY_UNCONNECTED", Severity.ERROR),
        ("BOUNDARY_UNCONNECTED", Severity.ERROR),
    ]
    tail = " of unit pump2/unit is not connected across it and has no declared UnusedBoundary"
    assert sorted(f.message for f in findings) == [
        f"boundary function pump2/X2/terminal/1/fn/terminal{tail}",
        f"boundary function pump2/X2/terminal/2/fn/terminal{tail}",
    ]
