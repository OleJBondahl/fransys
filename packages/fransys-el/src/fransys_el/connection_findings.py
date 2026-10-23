"""`CONNECTION_TO_UNDRAWN` (R267; layout-0044, moved here): a conductor with an end nothing draws.

An end is undrawn when its function was left out of the problem (`Skipped`, no symbol). The
function's own `FUNCTION_NOT_DRAWN` says why; this one names the wire that lost an end.
"""

from typing import TYPE_CHECKING

from fransys_layout import FINDING_CODES
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import ConductorKind, conductors, ports

from .placement_skips import FUNCTION_WITHOUT_SYMBOL
from .write_ids import id_texts

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Model

    from .placement_skips import Skipped

__all__ = ["undrawn_connection_findings"]

_INFO = {info.code: info for info in FINDING_CODES}


def undrawn_connection_findings(model: Model, skipped: Iterable[Skipped]) -> tuple[Finding, ...]:
    """One `CONNECTION_TO_UNDRAWN` per conductor with an end on a function the builder skipped."""
    texts = id_texts(model)
    undrawn = {
        texts[s.id] for s in skipped if s.reason == FUNCTION_WITHOUT_SYMBOL and s.id in texts
    }
    if not undrawn:
        return ()
    table = ports(model)
    found = []
    for conductor in conductors(model).values():
        if conductor.kind is ConductorKind.JUMPER:
            continue
        lost = [end for end in (conductor.a, conductor.b) if table[end].function in undrawn]
        if lost:
            found.append(
                Finding(
                    code="CONNECTION_TO_UNDRAWN",
                    severity=Severity.WARNING,
                    subjects=tuple(lost),
                    message="a connection has an end that is not drawn",
                    fix=_INFO["CONNECTION_TO_UNDRAWN"].filled(),
                )
            )
    return tuple(found)
