"""A raised or reported finding carries its own fix, and the report prints that fix (API-FINDINGS).

`BuildErrors.findings` and the rows of `fr.report` are the same findings: each ERROR holds the
pasteable fix the report prints, so a reader of the exception needs no registry lookup.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


def _build(tmp_path: Path) -> fr.BuildResult:
    @fr.unit("unit", revision=1, interface_version=1, date="2026-09-26", text="First", by="XX")
    def assembly(u: fr.Design) -> _Open:
        u.location("L0", "Harness 0")
        with u.function("HAR", "Harness"):
            box = u.harness(name="w0", place="L0")
            near = u.device("P0A", "DEMO-CONN-2P", parent=box, place="L0")
            far = u.device("P0B", "DEMO-CONN-2P", parent=box, place="L0")
            u.cable("W0", "DEMO-CBL-4G1.5", parent=box, name="w0c", place="L0").core(
                1, near[1], far[1]
            )
        return _Open()

    d = fr.design("demo_parts")
    d.add(assembly, "UNIT")
    cover = tmp_path / "unit.md"
    cover.write_text("# Harness\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "unit", cover=cover))


def test_every_raised_finding_has_a_fix_and_the_report_prints_it(tmp_path: Path) -> None:
    result = _build(tmp_path)
    with pytest.raises(fr.BuildErrors) as raised:
        fr.write(result, tmp_path / "out")
    errors = raised.value.findings
    assert errors
    report = fr.report(result)
    for finding in errors:
        assert finding.severity is Severity.ERROR
        assert "Write:" in finding.fix or finding.fix.startswith("No call clears this:")
        assert f"  fix: {finding.fix}" in report.splitlines()
        assert f"  fix: {finding.fix}" in str(raised.value)
