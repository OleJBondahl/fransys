"""A raised or reported finding carries its own fix, and the report prints that fix (API-FINDINGS).

`BuildFailedError.findings` and the rows of `fr.report` are the same findings: each ERROR holds the
pasteable fix the report prints, so a reader of the exception needs no registry lookup.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _expected_codes import expect_codes

from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from pathlib import Path


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.harness("W1")
    return fr.build(d)


def test_every_raised_finding_has_a_fix_and_the_report_prints_it(tmp_path: Path) -> None:
    result = _build()
    expect_codes(result, "MATES_DISABLED")
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.write(result, tmp_path / "out")
    errors = raised.value.findings
    assert errors
    report = fr.report(result)
    for finding in errors:
        assert finding.severity is Severity.ERROR
        assert "Write:" in finding.fix or finding.fix.startswith("No call clears this:")
        assert f"  fix: {finding.fix}" in report.splitlines()
        assert f"  fix: {finding.fix}" in str(raised.value)
