"""The two helpers every check shares: build a `Finding` with its fix text, and order a result."""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.codes import fix_text

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id


def finding(code: str, severity: Severity, subjects: Iterable[Id[Any]], message: str) -> Finding:
    """A `Finding` of `code` with its registered fix text."""
    return Finding(
        code=code, severity=severity, fix=fix_text(code), subjects=tuple(subjects), message=message
    )


def ordered(found: Iterable[Finding]) -> tuple[Finding, ...]:
    """`found` in the one order every check returns: code, subjects, message."""
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
