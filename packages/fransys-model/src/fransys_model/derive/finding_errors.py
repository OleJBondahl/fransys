"""The one fact of the findings policy: an `ERROR` finding refuses (owner 2026-09-22).

The facade's `write` and `release` and the part-library loader all refuse on it; each
reads these three functions and never compares `Severity.ERROR` itself.
"""

lazy from collections.abc import Iterable

from fransys_model.kernel import Finding, Severity


def errors_of(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """The `ERROR` findings of `findings`, in their own order."""
    return tuple(finding for finding in findings if finding.severity is Severity.ERROR)


def error_count(findings: Iterable[Finding]) -> int:
    """How many of `findings` are `ERROR`."""
    return len(errors_of(findings))


def refuses(findings: Iterable[Finding]) -> bool:
    """True when `findings` holds an `ERROR`: the build writes nothing, a library does not load."""
    return any(finding.severity is Severity.ERROR for finding in findings)
