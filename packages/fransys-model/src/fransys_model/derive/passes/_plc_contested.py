"""`PLC_CHANNEL_CONTESTED`: kind-matched requests wired to one channel bind nothing (model-0211)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function

PLC_CHANNEL_CONTESTED: Final[str] = "PLC_CHANNEL_CONTESTED"


def contested_findings(
    model: Model, contested: Mapping[Id[Function], tuple[Id[Function], ...]]
) -> list[Finding]:
    """One `ERROR` per contested channel, naming its pins and every request in request order."""
    all_functions = functions(model)
    return [
        Finding(
            code=PLC_CHANNEL_CONTESTED,
            severity=Severity.ERROR,
            subjects=(channel, *requests),
            message=(
                f"channel {ref(channel)} is wired to requests "
                f"{', '.join(ref(all_functions[request]) for request in requests)}: "
                "one channel reads one signal: keep one request, "
                "or wire each request to its own channel"
            ),
        )
        for channel, requests in contested.items()
    ]
