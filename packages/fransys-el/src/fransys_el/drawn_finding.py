"""One `Finding` of a code in this package's registry, with the code's own fix text."""

from typing import TYPE_CHECKING

lazy from fransys_model.kernel import Finding

from .codes import FINDING_CODES

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from fransys_model.kernel import Id

__all__ = ["drawn_finding"]

_INFO = {info.code: info for info in FINDING_CODES}


def drawn_finding(code: str, subjects: Sequence[Id[Any]], message: str) -> Finding:
    """The finding of `code` naming `subjects`."""
    return _INFO[code].finding(subjects, message)
