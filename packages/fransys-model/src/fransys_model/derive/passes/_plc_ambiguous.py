"""`PLC_REQUEST_AMBIGUOUS`: a request whose wiring ties several channels binds none (model-0211)."""

from typing import TYPE_CHECKING, Final

from fransys_model.derive.designation import item_label
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.facets.plc import PlcChannelFacet
from fransys_model.vocab.tables import facets_of, functions

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function
    from fransys_model.vocab.facets.plc import PlcRequestFacet

PLC_REQUEST_AMBIGUOUS: Final[str] = "PLC_REQUEST_AMBIGUOUS"


def _label(model: Model, function: Function) -> str:
    """The item's label (`item_label`: numbering has not run yet) and the function's name."""
    return f"{item_label(model, function.item)}/{function.name}"


def ambiguous_findings(
    model: Model,
    requests: Sequence[PlcRequestFacet],
    ambiguous: Mapping[Id[Function], tuple[Id[Function], ...]],
) -> list[Finding]:
    """One `ERROR` per request in `ambiguous`, naming its tied channels by item and number."""
    if not ambiguous:
        return []
    all_functions = functions(model)
    number = {
        function.id: facet.channel
        for facet in facets_of(model, PlcChannelFacet).values()
        for function in all_functions.values()
        if function.template == facet.subject
    }
    found: list[Finding] = []
    for request in requests:
        channels = ambiguous.get(request.subject)
        if channels is None:
            continue
        names = ", ".join(
            f"{item_label(model, all_functions[c].item)}:{number[c]}" for c in channels
        )
        found.append(
            Finding(
                code=PLC_REQUEST_AMBIGUOUS,
                severity=Severity.ERROR,
                subjects=(request.id, request.subject, *channels),
                message=(
                    f"{_label(model, all_functions[request.subject])} asks for "
                    f"{request.signal.value} as {request.signal_name!r}, but its wiring ties "
                    f"channels {names}: wire it to one channel directly, or free the others"
                ),
            )
        )
    return found
