"""An ERROR or WARNING `Finding` carries its own fix; an INFO note may have none (AD9)."""

import pytest

from fransys_kernel import Finding, SchemaError, Severity


@pytest.mark.parametrize("severity", [Severity.ERROR, Severity.WARNING])
def test_an_error_or_warning_without_a_fix_is_refused(severity: Severity) -> None:
    with pytest.raises(SchemaError, match="NO_FIX"):
        Finding(code="NO_FIX", severity=severity, subjects=(), message="m")


@pytest.mark.parametrize("severity", [Severity.ERROR, Severity.WARNING])
def test_an_error_or_warning_with_a_fix_is_kept(severity: Severity) -> None:
    one = Finding(code="HAS_FIX", severity=severity, subjects=(), message="m", fix="Write: x")
    assert one.fix == "Write: x"


def test_an_info_note_needs_no_fix() -> None:
    assert Finding(code="NOTE", severity=Severity.INFO, subjects=(), message="m").fix == ""
