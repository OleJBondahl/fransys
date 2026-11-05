"""The two helpers every check shares: build a `Finding` with its fix text, and order a result."""

from typing import TYPE_CHECKING

lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from collections.abc import Iterable


def ordered(found: Iterable[Finding]) -> tuple[Finding, ...]:
    """`found` in the one order every check returns: code, subjects, message."""
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
