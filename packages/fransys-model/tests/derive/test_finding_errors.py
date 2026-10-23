"""Tests: the findings policy fact, an `ERROR` refuses (SURFACE-COHERENCE, owner 2026-09-22)."""

from fransys_model.derive import error_count, errors_of, refuses
from fransys_model.kernel import Finding, Severity


def _finding(severity: Severity) -> Finding:
    return Finding(code="X", severity=severity, subjects=(), message="m", fix="Write: x")


def test_an_error_refuses_and_is_counted():
    error = _finding(Severity.ERROR)
    warning = _finding(Severity.WARNING)
    found = (warning, error, _finding(Severity.INFO), error)
    assert refuses(found)
    assert error_count(found) == 2
    assert errors_of(found) == (error, error)


def test_no_error_neither_refuses_nor_counts():
    found = (_finding(Severity.WARNING), _finding(Severity.INFO))
    assert not refuses(found)
    assert error_count(found) == 0
    assert errors_of(found) == ()
    assert not refuses(())
